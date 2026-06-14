# tests/test_recheck_fix1.py
# Regression tests: the streaming + resume paths must mirror the audited non-streaming loop (_drive),
# so the SAME tool set that works via Agent.run() does not crash or misbehave via stream()/resume().
from verso import Agent, tool
from verso.core.stream_loop import run_stream
from verso.durable.inmem import InMemoryCheckpointStore
from verso.model.base import ModelResponse, ToolCall
from verso.model.fake import FakeModel
from verso.safety.hooks import Hooks, PermissionDecision
from verso.stream.events import EventType
from verso.tools.errors import Retry
from verso.types import StopReason, Usage


async def _events(aiter):
    return [ev async for ev in aiter]


# ---------------------------------------------------------------------------
# Fix 1: stream dispatch must not let Retry / Paused escape the async generator
# ---------------------------------------------------------------------------

async def test_stream_tool_raising_retry_becomes_feedback_and_completes():
    # A @tool raising Retry on the stream path: stream() must complete (no exception), the feedback
    # content must surface in a TOOL_RESULT, and the loop must end normally.
    @tool
    def flaky() -> str:
        "Always asks for a do-over."
        raise Retry("try again with units")
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="flaky", arguments={})], usage=Usage()),
        ModelResponse(text="ok", tool_calls=[], usage=Usage()),
    ])
    evs = await _events(run_stream(fm, [flaky], "go"))     # must NOT raise
    res = next(e for e in evs if e.type is EventType.TOOL_RESULT)
    assert res.ok is False and res.content == "Retry: try again with units"
    assert evs[-1].type is EventType.DONE
    assert evs[-1].result.stop_reason is StopReason.END_TURN


async def test_stream_tool_hitl_request_not_durable_message_no_paused_escapes():
    # A @tool that calls ctx.hitl.request (raises Paused) on a stream (store=None by construction):
    # stream() must complete with the same "not durable" wording _drive uses — no Paused escapes.
    @tool
    def needs_input(ctx) -> str:
        "Ask a human."
        return ctx.hitl.request("approve?")
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="needs_input", arguments={})], usage=Usage()),
        ModelResponse(text="ok", tool_calls=[], usage=Usage()),
    ])
    agent = Agent(model=fm, tools=[needs_input], deps={"uid": "u1"})   # deps, but no checkpointer → store=None
    evs = await _events(agent.stream("go"))                            # must NOT raise Paused
    res = next(e for e in evs if e.type is EventType.TOOL_RESULT)
    assert res.ok is False
    assert res.content == ("Tool 'needs_input' requested human input but this run is not durable; "
                           "it did not pause.")
    assert evs[-1].type is EventType.DONE and evs[-1].result.stop_reason is StopReason.END_TURN


# ---------------------------------------------------------------------------
# Fix 2: ASK on the stream path emits an honest, DISTINCT message (not "by policy")
# ---------------------------------------------------------------------------

async def test_stream_ask_gate_emits_distinct_message_even_with_checkpointer():
    # On run(), ASK + a checkpointer routes to a durable pause. On stream() there is no durable pause,
    # so the message must be the new honest ASK wording — explicitly NOT the generic "by policy" string.
    @tool
    def add(a: int, b: int) -> int:
        "Add."
        return a + b
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text="ok", tool_calls=[], usage=Usage()),
    ])
    hooks = Hooks(pre_tool=[lambda call: PermissionDecision.ASK])
    agent = Agent(model=fm, tools=[add], hooks=hooks, checkpointer=InMemoryCheckpointStore())
    evs = await _events(agent.stream("go"))
    res = next(e for e in evs if e.type is EventType.TOOL_RESULT)
    assert res.ok is False
    assert res.content == ("Tool 'add' requested human approval (ASK) but streaming HITL is not "
                           "available; it did not run.")
    assert "by policy" not in res.content                  # the divergence is intentional + documented
    assert evs[-1].type is EventType.DONE and evs[-1].result.stop_reason is StopReason.END_TURN


# ---------------------------------------------------------------------------
# Fix 3: resume() must populate ctx.model and seed ctx.step/usage/messages for the re-dispatch
# ---------------------------------------------------------------------------

class _FakeModelWithId(FakeModel):
    """FakeModel that advertises a model_id, so ctx.model is observable on the resumed run."""
    model_id = "fake-resume-1"


async def test_resume_populates_ctx_model_step_usage_messages_for_redispatch():
    seen: list[dict] = []

    @tool
    def refund(amount: int, ctx) -> str:
        "Refund after human approval (records the ctx views it can see on each run)."
        seen.append(dict(model=ctx.model, step=ctx.step,
                         inp=ctx.usage.input_tokens, nmsgs=len(ctx.messages)))
        decision = ctx.hitl.request(f"approve refund of {amount}?")
        return f"refunded {amount}" if decision == "yes" else "cancelled"

    store = InMemoryCheckpointStore()
    fm = _FakeModelWithId([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="refund", arguments={"amount": 50})],
                      usage=Usage(input_tokens=7, output_tokens=3)),
        ModelResponse(text="done", tool_calls=[], usage=Usage(input_tokens=2, output_tokens=1)),
    ])
    agent = Agent(model=fm, tools=[refund], checkpointer=store)
    paused = await agent.run("refund the customer")
    assert paused.stop_reason == StopReason.PAUSED
    cp = store.load(paused.resume_token)

    resumed = await agent.resume(paused.resume_token, answer="yes")
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"

    # the LAST recorded run is the resume re-dispatch — it must see the resumed state, not zero defaults
    redispatch = seen[-1]
    assert redispatch["model"] == "fake-resume-1"          # ctx.model populated on resume (Fix 3 part 1)
    assert redispatch["step"] == cp.step                   # step seeded from the checkpoint (Fix 3 part 2)
    assert redispatch["inp"] > 0                            # cumulative usage non-zero (not Usage(0,0))
    assert redispatch["nmsgs"] > 0                          # messages non-empty (not [])


# ---------------------------------------------------------------------------
# Fix 4: a re-dispatch that raises Paused again must surface PAUSED, not crash the caller
# ---------------------------------------------------------------------------

async def test_resume_input_tool_pausing_twice_surfaces_paused_not_crash():
    # (a) a tool that calls ctx.hitl.request TWICE (two keys): the re-dispatch on resume hits the SECOND
    # request and raises Paused again. The guarantee under test (Fix 4) is that this re-pause is SURFACED
    # as StopReason.PAUSED — it must not escape resume_loop and crash the host coroutine. (The re-run HITL
    # model carries one answer per resume, same as _drive; a two-request tool re-pausing is expected.)
    bodies: list[str] = []

    @tool
    def two_step(ctx) -> str:
        "Asks two separate human questions."
        bodies.append("enter")
        a = ctx.hitl.request("first?", key="k1")
        b = ctx.hitl.request("second?", key="k2")
        return f"{a}+{b}"

    store = InMemoryCheckpointStore()
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="two_step", arguments={})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    agent = Agent(model=fm, tools=[two_step], checkpointer=store)

    paused1 = await agent.run("go")
    assert paused1.stop_reason == StopReason.PAUSED and paused1.pending.key == "k1"
    assert len(bodies) == 1                                 # ran once up to the first request

    paused2 = await agent.resume(paused1.resume_token, answer="A")   # must NOT crash
    assert paused2.stop_reason == StopReason.PAUSED         # second pause surfaced, not an escaped exception
    assert paused2.pending.key == "k2"                     # re-bound to the next request
    assert paused2.pending.tool_name == "two_step" and paused2.pending.tool_call_id == "t1"
    assert len(bodies) == 2                                 # re-ran exactly once up to the second request


async def test_resume_approved_ask_gate_then_internal_hitl_request_surfaces_paused():
    # (b) a pre_tool-ASK-gated tool whose body ALSO calls ctx.hitl.request: approving the gate + resume
    # must return PAUSED (not crash); the body runs at most once before the internal pause.
    bodies: list[str] = []

    @tool
    def gated(ctx) -> str:
        "ASK-gated AND internally pauses for input."
        bodies.append("enter")
        ans = ctx.hitl.request("inner approve?", key="inner")
        return f"ran:{ans}"

    store = InMemoryCheckpointStore()
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="gated", arguments={})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    hooks = Hooks(pre_tool=[lambda call: PermissionDecision.ASK])
    agent = Agent(model=fm, tools=[gated], hooks=hooks, checkpointer=store)

    gate = await agent.run("go")
    assert gate.stop_reason == StopReason.PAUSED and gate.pending.kind == "approve"
    assert bodies == []                                     # gate paused BEFORE the body ran

    paused = await agent.resume(gate.resume_token, approve=True)   # approve the gate → body runs → inner pause
    assert paused.stop_reason == StopReason.PAUSED          # internal hitl pause surfaced, not a crash
    assert paused.pending.kind == "input" and paused.pending.key == "inner"
    assert paused.pending.tool_name == "gated" and paused.pending.tool_call_id == "t1"
    assert len(bodies) == 1                                 # body ran exactly once before pausing

    resumed = await agent.resume(paused.resume_token, answer="yes")   # resolve inner → finishes
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"


# ---------------------------------------------------------------------------
# Fix 5 (ride-along): a pre_tool hook returning the bare string 'deny' must not crash on .value
# ---------------------------------------------------------------------------

async def test_run_raw_string_deny_decision_does_not_crash():
    # str-enum equality means a bare 'deny' is accepted everywhere; building the skip message via
    # decision.value used to AttributeError. run() must complete with a denial fed back to the model.
    @tool
    def add(a: int, b: int) -> int:
        "Add."
        return a + b
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text="ok", tool_calls=[], usage=Usage()),
    ])
    hooks = Hooks(pre_tool=[lambda call: "deny"])           # bare string, not the enum member
    result = await Agent(model=fm, tools=[add], hooks=hooks).run("go")   # must NOT raise AttributeError
    assert result.stop_reason == StopReason.END_TURN and result.output == "ok"
    # the denial reached the model on the next turn
    last_msgs = fm.calls[-1][0]
    assert any(m.role == "tool" and "was deny by policy" in m.content for m in last_msgs)


async def test_stream_raw_string_deny_decision_does_not_crash():
    # Same ride-along on the stream path: bare 'deny' must not AttributeError on decision.value.
    @tool
    def add(a: int, b: int) -> int:
        "Add."
        return a + b
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text="ok", tool_calls=[], usage=Usage()),
    ])
    hooks = Hooks(pre_tool=[lambda call: "deny"])
    evs = await _events(Agent(model=fm, tools=[add], hooks=hooks).stream("go"))   # must NOT raise
    res = next(e for e in evs if e.type is EventType.TOOL_RESULT)
    assert res.ok is False and "was deny by policy" in res.content
    assert evs[-1].type is EventType.DONE
