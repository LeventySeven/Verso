# tests/test_verify_gate.py
# The "verify-before-done" gate: an on_stop hook may return a VerificationOutcome to VETO a
# *natural* termination (END_TURN / DONE), feeding the detail back so the loop re-drives once
# (bounded by Hooks.max_verify_retries). Hooks that return None stay byte-identical.
from verso import Agent, tool, VerificationOutcome
from verso.safety.hooks import Hooks, VerificationOutcome as VO_direct
from verso.core.loop import run_loop
from verso.core.stream_loop import run_stream
from verso.stream.events import EventType
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.builtins import done
from verso.types import StopReason, Usage


def _text(t: str) -> ModelResponse:
    return ModelResponse(text=t, tool_calls=[], usage=Usage())


def _done(result: str, id="d") -> ModelResponse:
    return ModelResponse(text="", tool_calls=[ToolCall(id=id, name="done", arguments={"result": result})], usage=Usage())


# --- export ---------------------------------------------------------------------------------

def test_verification_outcome_is_exported_and_is_the_same_class():
    # exported from the package root AND it is the very class hooks.py defines (not a shadow).
    assert VerificationOutcome is VO_direct
    o = VerificationOutcome(passed=False, detail="x")
    assert o.passed is False and o.detail == "x"
    assert VerificationOutcome(passed=True).detail == ""    # detail defaults to ""


# --- veto then pass (END_TURN path) ---------------------------------------------------------

async def test_veto_then_pass_redrives_once_on_end_turn():
    # First natural END_TURN is vetoed; the loop must NOT terminate — it re-drives once with the
    # feedback in history, the model is called again, and the SECOND terminal finishes.
    fm = FakeModel([_text("first attempt"), _text("second attempt")])
    calls = {"n": 0}

    def verifier(result):
        calls["n"] += 1
        return VerificationOutcome(passed=False, detail="missing X") if calls["n"] == 1 else VerificationOutcome(passed=True)

    r = await Agent(model=fm, hooks=Hooks(on_stop=[verifier])).run("go")
    assert r.output == "second attempt"              # finished on the re-driven turn, not the first
    assert r.stop_reason is StopReason.END_TURN
    assert r.steps == 2                              # two model turns ran (one re-drive)
    assert len(fm.calls) == 2                        # the model WAS called a second time
    assert calls["n"] == 2                           # on_stop fired at both terminations
    # the feedback was injected as a user message between the two attempts
    seen_second = fm.calls[1][0]                     # messages passed to the 2nd model.complete
    assert any(m.role == "user" and "missing X" in (m.content or "") for m in seen_second)


# --- veto then pass (DONE path) -------------------------------------------------------------

async def test_veto_then_pass_redrives_once_on_done_tool():
    # The `done` tool is the OTHER natural termination. A veto re-drives; the second done finishes.
    fm = FakeModel([_done("v1", id="d1"), _done("v2", id="d2")])
    calls = {"n": 0}

    def verifier(result):
        calls["n"] += 1
        return VerificationOutcome(passed=False, detail="incomplete") if calls["n"] == 1 else None

    r = await run_loop(fm, [done], "do it", hooks=Hooks(on_stop=[verifier]))
    assert r.output == "v2"                           # finished on the SECOND done, not the first
    assert r.stop_reason is StopReason.DONE
    assert r.steps == 2
    assert len(fm.calls) == 2
    # the re-driven turn must be well-formed: the first done's tool result + the feedback are present
    seen_second = fm.calls[1][0]
    assert any(m.role == "tool" and m.tool_call_id == "d1" for m in seen_second)   # done's result was recorded
    assert any(m.role == "user" and "incomplete" in (m.content or "") for m in seen_second)


# --- budget cap -----------------------------------------------------------------------------

async def test_budget_cap_one_redrive_then_terminates_even_if_still_vetoed():
    # A hook that ALWAYS vetoes + max_verify_retries=1 → exactly ONE re-drive, then it terminates
    # anyway (no infinite loop). Two model calls total (initial + one re-drive).
    fm = FakeModel([_text("a"), _text("b"), _text("c"), _text("d")])
    calls = {"n": 0}

    def always_veto(result):
        calls["n"] += 1
        return VerificationOutcome(passed=False, detail="nope")

    r = await Agent(model=fm, hooks=Hooks(on_stop=[always_veto], max_verify_retries=1)).run("go")
    assert r.stop_reason is StopReason.END_TURN
    assert r.output == "b"                            # terminated on the second (re-driven) turn
    assert len(fm.calls) == 2                         # initial + exactly one re-drive
    assert calls["n"] == 2                            # on_stop fired twice (both terminations checked)


async def test_budget_zero_no_redrive_terminates_immediately_despite_veto():
    # max_verify_retries=0 → a veto cannot re-drive at all; the run terminates on the first done.
    fm = FakeModel([_done("only", id="d1"), _done("never", id="d2")])
    calls = {"n": 0}

    def always_veto(result):
        calls["n"] += 1
        return VerificationOutcome(passed=False, detail="nope")

    r = await run_loop(fm, [done], "go", hooks=Hooks(on_stop=[always_veto], max_verify_retries=0))
    assert r.output == "only" and r.stop_reason is StopReason.DONE
    assert r.steps == 1
    assert len(fm.calls) == 1                         # NO second model call
    assert calls["n"] == 1


async def test_budget_two_allows_two_redrives():
    # max_verify_retries=2 → up to two re-drives; an always-veto hook then terminates on turn 3.
    fm = FakeModel([_text("a"), _text("b"), _text("c"), _text("d")])

    def always_veto(result):
        return VerificationOutcome(passed=False, detail="again")

    r = await Agent(model=fm, hooks=Hooks(on_stop=[always_veto], max_verify_retries=2)).run("go")
    assert r.output == "c"                            # initial + 2 re-drives = 3 turns
    assert len(fm.calls) == 3


# --- byte-identical when unused -------------------------------------------------------------

async def test_on_stop_returning_none_is_unchanged():
    # The existing kind of on_stop hook (returns None) must NOT trigger any re-drive.
    fm = FakeModel([_text("done text")])
    fired = []
    r = await Agent(model=fm, hooks=Hooks(on_stop=[lambda result: fired.append(result.stop_reason)])).run("go")
    assert r.output == "done text" and r.stop_reason is StopReason.END_TURN
    assert r.steps == 1 and len(fm.calls) == 1        # single turn, no re-drive
    assert fired == [StopReason.END_TURN]


async def test_no_on_stop_hooks_is_unchanged():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="d1", name="done", arguments={"result": "final"})], usage=Usage()),
    ])
    r = await run_loop(fm, [done], "go")              # no hooks at all
    assert r.output == "final" and r.stop_reason is StopReason.DONE
    assert r.steps == 1 and len(fm.calls) == 1


async def test_outcome_with_passed_true_does_not_redrive():
    # An on_stop hook may also return VerificationOutcome(passed=True) — an explicit "ok to stop".
    fm = FakeModel([_text("ok")])
    r = await Agent(model=fm, hooks=Hooks(on_stop=[lambda result: VerificationOutcome(passed=True, detail="looks good")])).run("go")
    assert r.output == "ok" and r.stop_reason is StopReason.END_TURN
    assert len(fm.calls) == 1                         # passed=True is not a veto → no re-drive


# --- ctx still injected through the _fire path ----------------------------------------------

async def test_ctx_is_still_injected_into_a_verifying_on_stop_hook():
    # A ctx-aware on_stop hook still receives the RunContext (the _fire path) AND can veto.
    fm = FakeModel([_text("a"), _text("b")])
    seen = {}
    state = {"n": 0}

    def verifier(result, ctx):
        state["n"] += 1
        seen["trace"] = ctx.trace_id                  # ctx injected because the hook names it
        seen["uid"] = ctx.deps["uid"]
        return VerificationOutcome(passed=False, detail="redo") if state["n"] == 1 else VerificationOutcome(passed=True)

    r = await Agent(model=fm, hooks=Hooks(on_stop=[verifier]), deps={"uid": "u-1"}).run("go")
    assert r.output == "b"                            # vetoed once, then passed
    assert seen["trace"] and seen["uid"] == "u-1"     # ctx.trace_id + ctx.deps reached the hook
    assert state["n"] == 2


# --- multiple hooks: first veto wins, all still fire ----------------------------------------

async def test_first_veto_wins_among_multiple_on_stop_hooks():
    fm = FakeModel([_text("a"), _text("b")])
    seen = []
    state = {"n": 0}

    def fire_only(result):
        seen.append("first")                          # returns None — still fires every time
        return None

    def veto_then_pass(result):
        seen.append("second")
        state["n"] += 1
        return VerificationOutcome(passed=False, detail="d2") if state["n"] == 1 else VerificationOutcome(passed=True)

    r = await Agent(model=fm, hooks=Hooks(on_stop=[fire_only, veto_then_pass])).run("go")
    assert r.output == "b"
    assert seen.count("first") == 2 and seen.count("second") == 2   # BOTH hooks fired at both stops


# --- PAUSED / should_continue are NOT gated -------------------------------------------------

async def test_should_continue_stop_is_not_gated_by_a_veto():
    # A should_continue stop is a force-stop, NOT "the model says it's done" — a vetoing on_stop
    # hook must NOT re-drive it. The run still stops at the predicate.
    @tool
    def noop(value: str) -> str:
        "noop"
        return "ok"

    looping = [ModelResponse(text="", tool_calls=[ToolCall(id=str(i), name="noop", arguments={"value": "x"})], usage=Usage()) for i in range(10)]
    fm = FakeModel(looping)
    checks = {"n": 0}

    def keep_going(bundle):
        checks["n"] += 1
        return checks["n"] <= 2                        # stop at the 3rd check

    r = await Agent(model=fm, tools=[noop],
                    hooks=Hooks(should_continue=keep_going,
                                on_stop=[lambda result: VerificationOutcome(passed=False, detail="veto")])).run("go")
    assert r.stop_reason is StopReason.END_TURN        # stopped by the predicate
    assert r.steps == 2                                # NOT re-driven past the force-stop


# --- stream parity --------------------------------------------------------------------------

async def test_stream_veto_redrives_once_on_end_turn():
    # The stream path mirrors run(): a veto at the natural END_TURN re-drives once, yielding more
    # events, and the SECOND terminal finishes.
    fm = FakeModel([_text("first"), _text("second")])
    state = {"n": 0}

    def verifier(result):
        state["n"] += 1
        return VerificationOutcome(passed=False, detail="missing Y") if state["n"] == 1 else VerificationOutcome(passed=True)

    events = [ev async for ev in run_stream(fm, [], "go", hooks=Hooks(on_stop=[verifier]))]
    done_events = [e for e in events if e.type is EventType.DONE]
    assert len(done_events) == 1                       # exactly one DONE — the first stop did NOT emit DONE
    assert done_events[0].result.output == "second"
    assert done_events[0].result.stop_reason is StopReason.END_TURN
    assert len(fm.calls) == 2                          # re-driven once
    # two STEP events: the model was re-driven for a second step
    assert sum(1 for e in events if e.type is EventType.STEP) == 2


async def test_stream_veto_redrives_once_on_done_tool():
    fm = FakeModel([_done("s1", id="d1"), _done("s2", id="d2")])
    state = {"n": 0}

    def verifier(result):
        state["n"] += 1
        return VerificationOutcome(passed=False, detail="redo it") if state["n"] == 1 else None

    events = [ev async for ev in run_stream(fm, [done], "go", hooks=Hooks(on_stop=[verifier]))]
    done_events = [e for e in events if e.type is EventType.DONE]
    assert len(done_events) == 1 and done_events[0].result.output == "s2"
    assert done_events[0].result.stop_reason is StopReason.DONE
    assert len(fm.calls) == 2
    # the re-driven turn saw the first done's tool result + the feedback
    seen_second = fm.calls[1][0]
    assert any(m.role == "tool" and m.tool_call_id == "d1" for m in seen_second)
    assert any(m.role == "user" and "redo it" in (m.content or "") for m in seen_second)


async def test_stream_budget_cap_terminates_despite_persistent_veto():
    fm = FakeModel([_text("a"), _text("b"), _text("c")])

    def always_veto(result):
        return VerificationOutcome(passed=False, detail="no")

    events = [ev async for ev in run_stream(fm, [], "go", hooks=Hooks(on_stop=[always_veto], max_verify_retries=1))]
    done_events = [e for e in events if e.type is EventType.DONE]
    assert len(done_events) == 1 and done_events[0].result.output == "b"   # one re-drive then stop
    assert len(fm.calls) == 2
