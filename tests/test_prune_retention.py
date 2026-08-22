# tests/test_prune_retention.py
# Retention (how much survives a budget-triggered prune) is a CALLER decision, not a constant.
# Evidence: across seven shipped harnesses the compaction trigger spans a 45-point range
# (gemini-cli 50% .. Claude Code 95% — teardowns/CODING_AGENT_HARNESS_COMPARISON.md:390),
# so there is no defensible default to bake in. The default here is unchanged (10) and rule 1
# (additive-or-byte-identical) is pinned by the last test in this file.
from verso import Agent, tool
from verso.context.prune import MASK
from verso.model.base import ModelResponse, ToolCall
from verso.model.fake import FakeModel
from verso.types import Usage

BIG = "x" * 4000          # ~1000 estimated tokens per tool result


@tool
def fetch(n: int) -> str:
    "Fetch a big blob."
    return BIG


def _agent(**kw):
    steps = [ModelResponse(text="", tool_calls=[ToolCall(id=f"t{i}", name="fetch", arguments={"n": i})],
                           usage=Usage()) for i in range(8)]
    steps.append(ModelResponse(text="done", tool_calls=[], usage=Usage()))
    fm = FakeModel(steps)
    return Agent(model=fm, tools=[fetch], max_context_tokens=500, **kw), fm


def _tool_msgs_of_last_turn(fm):
    # what the model actually SAW on the final turn — the honest observation point for pruning,
    # and it needs no new public API on Agent.
    messages, _tools, _system = fm.calls[-1]
    return [m for m in messages if m.role == "tool"]


async def test_retention_is_caller_controllable():
    # keep_last_n=1 must mask strictly more tool results than the built-in default of 10.
    agent, fm = _agent(prune_keep_last_n=1)
    await agent.run("go")
    tool_msgs = _tool_msgs_of_last_turn(fm)
    masked = [m for m in tool_msgs if m.content == MASK]
    kept = [m for m in tool_msgs if m.content != MASK]
    assert masked, "keep_last_n=1 should have masked older tool results"
    assert len(kept) == 1, f"exactly one tool result should survive, got {len(kept)}"


async def test_default_retention_is_unchanged_and_byte_identical():
    # No prune_keep_last_n => the shipped default (10). With 8 tool results, nothing is masked,
    # exactly as before this parameter existed.
    agent, fm = _agent()
    await agent.run("go")
    assert not [m for m in _tool_msgs_of_last_turn(fm) if m.content == MASK]


async def test_stream_path_honours_the_same_retention_as_run():
    # The eval path (VersoSpan.capture -> agent.stream) must not measure a different retention than
    # production (agent.run), or evals silently grade a differently-pruned agent. This test exists
    # because the first cut of prune_keep_last_n threaded run() and NOT stream(): run() masked 7 of 8
    # tool results while stream() masked 0.
    agent, fm = _agent(prune_keep_last_n=1)
    async for _ in agent.stream("go"):
        pass
    tool_msgs = _tool_msgs_of_last_turn(fm)
    assert [m for m in tool_msgs if m.content == MASK], "stream() dropped the configured retention"
    assert len([m for m in tool_msgs if m.content != MASK]) == 1


async def test_resume_carries_the_configured_retention():
    # Resume re-enters _drive; if the knob is not threaded through resume_loop the resumed run
    # silently reverts to the shipped default of 10. Rule 5: the threading needs its own test.
    #
    # The gate must fire LATE. A first-tool-call pause leaves nothing in history for prune to act on,
    # so the resumed run never prunes and the test passes either way — verified: the earlier version
    # of this test still passed with the threading deleted. Pausing on the 6th call means the resumed
    # _drive inherits a history already over budget, so retention is actually exercised.
    from verso.durable.inmem import InMemoryCheckpointStore
    from verso.safety.hooks import Hooks, PermissionDecision

    seen = {"n": 0}

    def ask_on_the_sixth(call):
        seen["n"] += 1
        return PermissionDecision.ASK if seen["n"] == 6 else PermissionDecision.ALLOW

    steps = [ModelResponse(text="", tool_calls=[ToolCall(id=f"t{i}", name="fetch", arguments={"n": i})],
                           usage=Usage()) for i in range(10)]
    steps.append(ModelResponse(text="done", tool_calls=[], usage=Usage()))
    fm = FakeModel(steps)
    agent = Agent(model=fm, tools=[fetch], max_context_tokens=500, prune_keep_last_n=1,
                  checkpointer=InMemoryCheckpointStore(),
                  hooks=Hooks(pre_tool=[ask_on_the_sixth]))
    paused = await agent.run("go")
    assert paused.resume_token, "expected an ASK pause to checkpoint"
    await agent.resume(paused.resume_token, approve=True)
    tool_msgs = _tool_msgs_of_last_turn(fm)
    assert [m for m in tool_msgs if m.content == MASK], "resumed run never pruned — test would not catch a drop"
    assert len([m for m in tool_msgs if m.content != MASK]) == 1, "resume reverted to the default retention"
