# tests/test_durable_ctx_tools.py
import pytest
from verso import Agent, tool
from verso.tools.dispatch import dispatch
from verso.durable.context import RunContext, Paused
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason
from verso.durable.inmem import InMemoryCheckpointStore


def test_ctx_is_not_a_model_visible_argument():
    @tool
    def whoami(ctx) -> str:
        "Return the caller id."
        return ctx.deps["uid"]
    assert whoami.wants_ctx is True
    assert "ctx" not in whoami.parameters.get("properties", {})   # framework-injected, not a model arg


async def test_dispatch_injects_ctx_and_propagates_paused():
    @tool
    def needs_input(ctx) -> str:
        "Ask a human."
        return ctx.hitl.request("approve?")        # raises Paused on the first run
    ctx: RunContext = RunContext(trace_id="x", deps={"uid": "u1"}, store=InMemoryCheckpointStore())
    with pytest.raises(Paused):
        await dispatch(needs_input, {}, ctx=ctx)   # Paused propagates, NOT swallowed into ToolResult

    @tool
    def reads_deps(ctx) -> str:
        "Read deps."
        return ctx.deps["uid"]
    res = await dispatch(reads_deps, {}, ctx=ctx)
    assert res.ok and res.data == "u1"


def _durable_agent(store, deps=None):
    @tool
    def refund(amount: int, ctx) -> str:
        "Refund a customer after human approval."
        decision = ctx.hitl.request(f"approve refund of {amount}?")   # pauses; on resume returns the answer
        return f"refunded {amount}" if decision == "yes" else "refund cancelled"
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="refund", arguments={"amount": 50})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    return Agent(model=fm, tools=[refund], checkpointer=store, deps=deps)


async def test_tool_hitl_request_pauses_then_resumes_with_the_answer():
    store = InMemoryCheckpointStore()
    agent = _durable_agent(store)
    paused = await agent.run("refund the customer")
    assert paused.stop_reason == StopReason.PAUSED
    assert paused.pending.prompt == "approve refund of 50?" and paused.pending.kind == "input"
    resumed = await agent.resume(paused.resume_token, answer="yes")
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"


async def test_agent_deps_reach_the_tool():
    seen = {}
    @tool
    def grab(ctx) -> str:
        "Read deps."
        seen["uid"] = ctx.deps["uid"]
        return "ok"
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="grab", arguments={})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    await Agent(model=fm, tools=[grab], deps={"uid": "u-42"}).run("go")
    assert seen["uid"] == "u-42"
