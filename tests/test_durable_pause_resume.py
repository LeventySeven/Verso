from verso import Agent, tool
from verso.safety.hooks import Hooks, PermissionDecision
from verso.durable.inmem import InMemoryCheckpointStore
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason


@tool
def send_email(to: str) -> str:
    "Send an email."
    return f"sent to {to}"


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
    store = InMemoryCheckpointStore()
    agent = _paused_agent(store)
    paused = await agent.run("email x")
    assert paused.stop_reason == StopReason.PAUSED
    resumed = await agent.resume(paused.resume_token, approve=True)
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"


async def test_resume_deny_feeds_a_denial_and_finishes_without_running_the_tool():
    store = InMemoryCheckpointStore()
    agent = _paused_agent(store)
    paused = await agent.run("email x")
    resumed = await agent.resume(paused.resume_token, approve=False)
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"
