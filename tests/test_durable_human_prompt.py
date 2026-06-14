# tests/test_durable_human_prompt.py
# E1: an OPTIONAL reviewer-facing pause message. A tool passes human_prompt= to ctx.hitl.request; the
# PAUSED result surfaces it via pending.display while pending.prompt keeps the agent-internal detail, and
# it survives a real sqlite process restart. With no human_prompt, display == prompt (byte-identical).
from verso import Agent, tool
from verso.durable.context import RunContext, Hitl, Paused, HumanRequest
from verso.durable.inmem import InMemoryCheckpointStore
from verso.durable.sqlite import SqliteCheckpointStore
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason


def _refund_agent(store):
    @tool
    def refund(amount: int, ctx) -> str:
        "Refund a customer after human approval."
        # The internal `prompt` carries a low-level detail; `human_prompt` is the bounded reviewer surface.
        ok = ctx.hitl.request(
            f"internal: refund txn for ${amount} (key=refund-{amount})",
            key="k",
            human_prompt="Approve the $50 refund to Acme?",
        )
        return f"refunded {amount}" if ok == "yes" else "refund cancelled"
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="refund", arguments={"amount": 50})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    return Agent(model=fm, tools=[refund], checkpointer=store)


# --- unit: HumanRequest.display + Hitl.request thread human_prompt through Paused ---

def test_display_prefers_human_prompt_over_prompt():
    hr = HumanRequest(prompt="internal detail", human_prompt="Approve the $50 refund to Acme?")
    assert hr.display == "Approve the $50 refund to Acme?"
    assert hr.prompt == "internal detail"          # the agent-internal detail is untouched


def test_display_falls_back_to_prompt_when_human_prompt_unset():
    hr = HumanRequest(prompt="internal detail")
    assert hr.human_prompt is None
    assert hr.display == "internal detail"          # byte-identical surface when unset


def test_hitl_request_threads_human_prompt_into_the_paused_request():
    ctx: RunContext[None] = RunContext(trace_id="x")
    import pytest
    with pytest.raises(Paused) as ei:
        ctx.hitl.request("internal detail", key="k", human_prompt="Approve the $50 refund to Acme?")
    req = ei.value.request
    assert isinstance(req, HumanRequest)
    assert req.prompt == "internal detail"
    assert req.human_prompt == "Approve the $50 refund to Acme?"
    assert req.display == "Approve the $50 refund to Acme?"


def test_hitl_request_without_human_prompt_is_back_compatible():
    # existing callers pass only prompt/key → human_prompt is None → display == prompt
    ctx: RunContext[None] = RunContext(trace_id="x")
    import pytest
    with pytest.raises(Paused) as ei:
        ctx.hitl.request("approve the refund?", key="refund")
    req = ei.value.request
    assert req.human_prompt is None and req.display == "approve the refund?"
    assert isinstance(ctx.hitl, Hitl)


# --- end-to-end: pause surfaces display; survives sqlite restart; resume finishes ---

async def test_paused_result_exposes_human_prompt_via_display():
    store = InMemoryCheckpointStore()
    paused = await _refund_agent(store).run("refund the customer")
    assert paused.stop_reason == StopReason.PAUSED
    # the reviewer sees the bounded message; the internal prompt is preserved underneath
    assert paused.pending.display == "Approve the $50 refund to Acme?"
    assert paused.pending.prompt == "internal: refund txn for $50 (key=refund-50)"
    assert paused.pending.human_prompt == "Approve the $50 refund to Acme?"


async def test_human_prompt_survives_sqlite_restart(tmp_path):
    path = str(tmp_path / "ck.db")
    paused = await _refund_agent(SqliteCheckpointStore(path)).run("refund the customer")
    assert paused.stop_reason == StopReason.PAUSED

    # reopen the store over the SAME file (process restart) and reload the checkpoint
    reloaded = SqliteCheckpointStore(path).load(paused.resume_token)
    assert reloaded is not None and reloaded.pending is not None
    assert reloaded.pending.human_prompt == "Approve the $50 refund to Acme?"
    assert reloaded.pending.prompt == "internal: refund txn for $50 (key=refund-50)"
    assert reloaded.pending.display == "Approve the $50 refund to Acme?"

    # and a brand-new agent over the same file can still resume to completion
    resume_agent = Agent(model=FakeModel([ModelResponse(text="done", tool_calls=[], usage=Usage())]),
                         tools=_refund_agent(SqliteCheckpointStore(path)).tools,
                         checkpointer=SqliteCheckpointStore(path))
    resumed = await resume_agent.resume(paused.resume_token, answer="yes")
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"


async def test_no_human_prompt_is_byte_identical_in_pending_and_display(tmp_path):
    # a tool that omits human_prompt → pending.human_prompt is None, display == prompt, and the
    # serialized pending key is None across a sqlite round-trip (no behavior change when unset).
    @tool
    def refund(amount: int, ctx) -> str:
        "Refund a customer after human approval."
        ok = ctx.hitl.request(f"approve refund of {amount}?")
        return f"refunded {amount}" if ok == "yes" else "cancelled"
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="refund", arguments={"amount": 50})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    path = str(tmp_path / "ck.db")
    paused = await Agent(model=fm, tools=[refund], checkpointer=SqliteCheckpointStore(path)).run("refund")
    assert paused.stop_reason == StopReason.PAUSED
    assert paused.pending.human_prompt is None
    assert paused.pending.display == "approve refund of 50?" == paused.pending.prompt
    reloaded = SqliteCheckpointStore(path).load(paused.resume_token)
    assert reloaded.pending.human_prompt is None
    assert reloaded.pending.display == reloaded.pending.prompt == "approve refund of 50?"
