# tests/test_stream_retry_budget.py
# Parity: the streaming path must bound a tool's Retry by the per-tool max_tool_retries budget — exactly
# like _drive (verso/core/loop.py) — not just by max_steps. Mirrors the non-stream budget tests in
# tests/test_retry_feedback.py (test_tool_retry_budget_caps_an_always_retrying_tool +
# test_max_tool_retries_is_configurable_from_agent), but driven through Agent.stream() and counting the
# TOOL_RESULT events the stream emits.
from verso import Agent, tool
from verso.model.base import ModelResponse, ToolCall
from verso.model.fake import FakeModel
from verso.stream.events import EventType
from verso.tools.errors import Retry
from verso.types import StopReason, Usage


async def _events(aiter):
    return [ev async for ev in aiter]


def _always_retry_model(n: int) -> FakeModel:
    # n tool-calls to the always-retrying tool, then a terminal text turn so the stream can END_TURN
    # even if the budget did not stop it first (so a regression shows as a count mismatch, not a hang).
    return FakeModel(
        [ModelResponse(text="", tool_calls=[ToolCall(id=str(i), name="loops", arguments={"value": "x"})],
                       usage=Usage()) for i in range(n)]
        + [ModelResponse(text="gave up", tool_calls=[], usage=Usage())]
    )


async def test_stream_tool_retry_budget_caps_an_always_retrying_tool():
    # Mirror of test_tool_retry_budget_caps_an_always_retrying_tool on the stream path:
    # an always-Retry tool driven via agent.stream(...) with max_tool_retries=2 must TERMINATE (END_TURN
    # or MAX_STEPS, not a hang/crash) with exactly 2 'Retry:' tool results, then the terminal budget error.
    @tool
    def loops(value: str) -> str:
        "Always retries."
        raise Retry("never happy")

    # stuck_thresholds=None isolates the RETRY BUDGET (doom-loop detection is covered separately).
    agent = Agent(model=_always_retry_model(5), tools=[loops], max_tool_retries=2, stuck_thresholds=None)
    evs = await _events(agent.stream("go"))                 # must NOT hang or raise

    assert evs[-1].type is EventType.DONE
    assert evs[-1].result.stop_reason in (StopReason.END_TURN, StopReason.MAX_STEPS)  # it TERMINATES

    results = [e.content for e in evs if e.type is EventType.TOOL_RESULT]
    # the BUDGET (not the script) bounded it: exactly 2 'Retry:' feedbacks, then the terminal budget error
    assert sum(1 for c in results if c.startswith("Retry:")) == 2
    assert any("exceeded its retry budget (2)" in c for c in results)
    # every Retry/budget tool result is a failure result (ok is False), as on the non-stream path
    assert all(e.ok is False for e in evs if e.type is EventType.TOOL_RESULT)


async def test_stream_max_tool_retries_zero_is_configurable_from_agent():
    # Mirror of test_max_tool_retries_is_configurable_from_agent: max_tool_retries=0 ⇒ no 'Retry:' feedback
    # at all, just the immediate budget error — honored from the Agent surface on the stream path too.
    @tool
    def loops(value: str) -> str:
        "Always retries."
        raise Retry("nope")

    agent = Agent(model=_always_retry_model(4), tools=[loops], max_tool_retries=0, stuck_thresholds=None)
    evs = await _events(agent.stream("go"))

    assert evs[-1].type is EventType.DONE
    results = [e.content for e in evs if e.type is EventType.TOOL_RESULT]
    assert sum(1 for c in results if c.startswith("Retry:")) == 0      # budget=0 ⇒ zero Retry feedbacks
    assert any("exceeded its retry budget (0)" in c for c in results)  # immediate budget error instead


async def test_stream_no_retry_path_is_unchanged():
    # byte-identical-ish guard: a normal stream with no Retry still produces a single successful TOOL_RESULT
    # and an END_TURN — the budget machinery is inert when nothing raises Retry.
    @tool
    def add(a: int, b: int) -> int:
        "Add."
        return a + b

    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text="ok", tool_calls=[], usage=Usage()),
    ])
    evs = await _events(Agent(model=fm, tools=[add]).stream("go"))

    results = [e for e in evs if e.type is EventType.TOOL_RESULT]
    assert len(results) == 1 and results[0].ok is True and results[0].content == "3"
    assert evs[-1].type is EventType.DONE and evs[-1].result.stop_reason is StopReason.END_TURN
