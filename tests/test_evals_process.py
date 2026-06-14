# tests/test_evals_process.py
# Process-level evals (A1): assert on the tool PATH (name + args), not just the final output;
# plus triage (A4): worst-first ordering and panel-disagreement surfacing. All additive — the
# prior eval tests pass UNMODIFIED; these exercise the new params/fields only.
from verso import Agent, tool
from verso.evals.suite import Eval, Assertion, TraceCheck
from verso.evals.span import VersoSpan, VersoScore
from verso.evals.suite import UnitReport
from verso.evals.judge import LLMJudge, JudgePanel
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def search(q: str) -> str:
    "Search the corpus."
    return f"hits for {q}"


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


def _search_agent(answer="found it"):
    # turn 1: call search with specific args; turn 2: final answer
    return Agent(model=FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="search", arguments={"q": "verso"})], usage=Usage()),
        ModelResponse(text=answer, tool_calls=[], usage=Usage()),
    ]), tools=[search])


def _add_agent(answer="3"):
    # an agent that calls a DIFFERENT tool (never search) — the trace_check negative case
    return Agent(model=FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text=answer, tool_calls=[], usage=Usage()),
    ]), tools=[add])


# --- A1: tool-call arguments are captured (the path, not just the output) ---

async def test_capture_records_tool_call_arguments():
    span = await VersoSpan.capture(_search_agent(), "look up verso")
    tool_recs = [r for r in span.records if r.kind == "tool"]
    assert len(tool_recs) == 1
    assert tool_recs[0].name == "search"
    assert tool_recs[0].args == {"q": "verso"}          # TOOL_START args threaded into the TOOL_RESULT record


async def test_tool_calls_accessor_returns_name_args_ok_content():
    span = await VersoSpan.capture(_search_agent(), "look up verso")
    calls = span.tool_calls()
    assert calls == [("search", {"q": "verso"}, True, "hits for verso")]


async def test_jsonl_round_trips_args():
    # a record with args survives serialization (to_jsonl dumps r.__dict__, from_jsonl does SpanRecord(**r))
    span = await VersoSpan.capture(_search_agent(), "look up verso")
    restored = VersoSpan.from_jsonl(span.to_jsonl())
    assert restored.tool_calls() == span.tool_calls()
    assert [r.args for r in restored.records if r.kind == "tool"] == [{"q": "verso"}]


# --- A1: TraceCheck — process-level checks alongside output assertions ---

used_search = TraceCheck("used_search", lambda s: any(n == "search" for n, _, _, _ in s.tool_calls()))


async def test_trace_check_passes_when_tool_path_matches():
    report = await Eval.unit(
        agent_factory=lambda: _search_agent(),
        cases={"happy": "look up verso"},
        assertions=[Assertion("answered", lambda s: bool(s.output))],
        trace_checks=[used_search],
    )
    sc = report.scores["happy"]["used_search"]
    assert sc.passed and sc.kind == "trace"            # the path tier is distinct from assertions
    assert report.passed


async def test_trace_check_fails_when_tool_path_diverges():
    # same trace_check, but the agent called `add`, never `search` → the path check fails
    report = await Eval.unit(
        agent_factory=lambda: _add_agent(),
        cases={"wrong_path": "do something"},
        assertions=[Assertion("answered", lambda s: bool(s.output))],
        trace_checks=[used_search],
    )
    sc = report.scores["wrong_path"]["used_search"]
    assert not sc.passed and sc.kind == "trace"
    assert not report.passed                            # a failing trace_check fails the report
    # the output assertion still passed — only the PATH check caught it
    assert report.scores["wrong_path"]["answered"].passed


async def test_trace_check_with_args_predicate():
    # the args are usable in a trace_check (assert the right tool was called with the right args)
    called_with_q = TraceCheck("searched_verso",
                               lambda s: ("search", {"q": "verso"}, True, "hits for verso") in s.tool_calls())
    report = await Eval.unit(
        agent_factory=lambda: _search_agent(),
        cases={"happy": "look up verso"},
        assertions=[Assertion("answered", lambda s: bool(s.output))],
        trace_checks=[called_with_q],
    )
    assert report.scores["happy"]["searched_verso"].passed


# --- A1: LLMJudge trace_mode — judge the whole tool PATH, not just output ---

async def test_trace_mode_judge_sees_the_rendered_tool_path():
    # FakeModel records .calls; assert the judge's prompt contains the rendered path markers, not just output.
    span = await VersoSpan.capture(_search_agent(answer="the final answer"), "look up verso")
    judge_model = FakeModel([ModelResponse(text='{"passed": true, "value": 1.0, "detail": "ok"}', tool_calls=[], usage=Usage())])
    judge = LLMJudge(judge_model, rubric="Did it use the right tools?", trace_mode=True)
    await judge.score(span)
    prompt = judge_model.calls[-1][0][0].content          # (messages, tools, system) -> first user message
    assert "search()" in prompt                           # render() shows the tool path (a marker output alone lacks)
    assert "trace " + span.trace_id in prompt             # render()'s header line
    assert span.render() in prompt                        # the whole rendered path is fenced as DATA


async def test_trace_mode_off_is_output_only():
    # trace_mode=False (default) fences ONLY span.output — byte-identical to the pre-feature prompt.
    span = await VersoSpan.capture(_search_agent(answer="just the answer"), "look up verso")
    judge_model = FakeModel([ModelResponse(text='{"passed": true, "value": 1.0}', tool_calls=[], usage=Usage())])
    judge = LLMJudge(judge_model, rubric="ok")
    await judge.score(span)
    prompt = judge_model.calls[-1][0][0].content
    assert "just the answer" in prompt                    # the output is fenced
    assert "search()" not in prompt                       # the tool path is NOT — output only


# --- A4: JudgePanel divergence (population std-dev of member values) ---

def _judge(verdict):
    return LLMJudge(FakeModel([ModelResponse(text=verdict, tool_calls=[], usage=Usage())]), rubric="...")


async def test_panel_divergence_nonzero_when_judges_disagree():
    panel = JudgePanel([_judge('{"passed": true, "value": 0.9}'),
                        _judge('{"passed": false, "value": 0.1}'),
                        _judge('{"passed": true, "value": 0.5}')])
    score = await panel.score(VersoSpan(trace_id="x", output="ok"))
    assert score.divergence > 0                            # spread of [0.9,0.1,0.5] is non-zero
    # pstdev([0.9,0.1,0.5]) ≈ 0.327
    assert 0.3 < score.divergence < 0.35


async def test_single_judge_panel_has_zero_divergence():
    panel = JudgePanel([_judge('{"passed": true, "value": 0.7}')])
    score = await panel.score(VersoSpan(trace_id="x", output="ok"))
    assert score.divergence == 0.0                         # one judge → no disagreement


# --- A4: UnitReport.worst / .divergent (triage) ---

def _report():
    return UnitReport(scores={
        "a": {"x": VersoScore("x", True, value=0.9),
              "y": VersoScore("y", False, value=0.1, divergence=0.3)},
        "b": {"z": VersoScore("z", True, value=0.5, divergence=0.05)},
    })


def test_worst_returns_lowest_values_ascending():
    worst = _report().worst(2)
    assert len(worst) == 2
    assert [sc.value for _, _, sc in worst] == [0.1, 0.5]   # ascending, the 2 lowest
    assert worst[0][:2] == ("a", "y")                       # the worst is (case, name)


def test_worst_n_caps_and_flattens_the_matrix():
    worst = _report().worst()                               # default n=5, only 3 scores exist
    assert len(worst) == 3
    assert [sc.value for _, _, sc in worst] == [0.1, 0.5, 0.9]


def test_divergent_surfaces_high_spread_cases():
    div = _report().divergent(0.2)                          # only y (0.3) clears the threshold
    assert len(div) == 1
    assert div[0][:2] == ("a", "y")
    assert div[0][2].divergence == 0.3


def test_divergent_threshold_default_excludes_low_spread():
    # default threshold 0.25 → y (0.3) in, z (0.05) out, x (0.0) out
    div = _report().divergent()
    assert {(c, n) for c, n, _ in div} == {("a", "y")}
