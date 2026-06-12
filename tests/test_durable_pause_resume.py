from verso import Agent, tool
from verso.safety.hooks import Hooks, PermissionDecision
from verso.durable.inmem import InMemoryCheckpointStore
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason


RAN: list[str] = []        # records actual tool-body executions — proves approve runs / deny does not


@tool
def send_email(to: str) -> str:
    "Send an email."
    RAN.append(to)
    return f"sent to {to}"


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


def _paused_agent(store):
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="send_email", arguments={"to": "x@y.z"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    hooks = Hooks(pre_tool=[lambda call: PermissionDecision.ASK])
    return Agent(model=fm, tools=[send_email], hooks=hooks, checkpointer=store)


async def test_durable_ask_pauses_and_checkpoints_instead_of_denying():
    store = InMemoryCheckpointStore()
    result = await _paused_agent(store).run("email x")
    assert result.stop_reason == StopReason.PAUSED
    assert result.resume_token and result.pending is not None
    assert result.pending.tool_name == "send_email"
    cp = store.load(result.resume_token)
    assert cp is not None and cp.pending is not None and cp.step >= 1


async def test_resume_approve_runs_the_held_tool_and_finishes():
    RAN.clear()
    store = InMemoryCheckpointStore()
    agent = _paused_agent(store)
    paused = await agent.run("email x")
    assert paused.stop_reason == StopReason.PAUSED
    assert RAN == []                                     # held tool did NOT run while paused
    resumed = await agent.resume(paused.resume_token, approve=True)
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"
    assert RAN == ["x@y.z"]                              # approve actually executed the tool body


async def test_resume_deny_feeds_a_denial_and_finishes_without_running_the_tool():
    RAN.clear()
    store = InMemoryCheckpointStore()
    agent = _paused_agent(store)
    paused = await agent.run("email x")
    resumed = await agent.resume(paused.resume_token, approve=False)
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"
    assert RAN == []                                     # deny never executed the tool body (the real proof)


async def test_durable_pause_defers_unprocessed_siblings_so_resume_is_well_formed():
    store = InMemoryCheckpointStore()
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[
            ToolCall(id="t1", name="send_email", arguments={"to": "x@y.z"}),   # ASK → pauses first
            ToolCall(id="t2", name="add", arguments={"a": 1, "b": 2}),         # ALLOW sibling, never reached
        ], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    hooks = Hooks(pre_tool=[lambda call: PermissionDecision.ASK if call[0] == "send_email"
                            else PermissionDecision.ALLOW])
    agent = Agent(model=fm, tools=[send_email, add], hooks=hooks, checkpointer=store)
    paused = await agent.run("do both")
    assert paused.stop_reason == StopReason.PAUSED
    cp = store.load(paused.resume_token)
    # the unprocessed sibling 'add' (t2) got a deferred result → no unmatched tool_use block in the turn
    result_ids = {m["tool_call_id"] for m in cp.history if m["role"] == "tool"}
    assert "t2" in result_ids
    resumed = await agent.resume(paused.resume_token, approve=True)   # resolves t1; turn stays well-formed
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"
