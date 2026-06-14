# tests/test_evals_budget.py
# A2 (LLMJudge.calibrate) + A3 (budget-aware pass_k + best_of_n). Additive: every prior eval test
# passes UNMODIFIED. FakeModel makes both the judge verdicts and the captured spans' usage_total
# fully scripted, so the confusion matrix and the budget curve are known exactly.
from verso import Agent, tool, CalibrationReport, BestOfN
from verso.evals.suite import Eval, Assertion
from verso.evals.judge import LLMJudge
from verso.evals.span import VersoSpan
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


# ----------------------------------------------------------------------------- A2: calibrate

def _verdict(passed: bool) -> ModelResponse:
    # The judge model returns ONLY JSON; calibrate compares score().passed to the human label.
    body = '{"passed": true, "value": 1.0}' if passed else '{"passed": false, "value": 0.0}'
    return ModelResponse(text=body, tool_calls=[], usage=Usage())


def _span(tag: str) -> VersoSpan:
    return VersoSpan(trace_id=tag, output=tag, stop_reason="end_turn", steps=1)


async def test_calibrate_computes_precision_recall_f1_against_known_confusion_matrix():
    # 5 labeled spans, scored IN ORDER (FakeModel pops verdicts in order): 2 TP, 1 FP, 1 FN, 1 TN.
    #   precision = TP/(TP+FP) = 2/3 ; recall = TP/(TP+FN) = 2/3 ; f1 = 2/3 ; agreement = (2+1)/5 = 0.6
    s_tp1, s_tp2, s_fp, s_fn, s_tn = (_span("tp1"), _span("tp2"), _span("fp"), _span("fn"), _span("tn"))
    judge = LLMJudge(model=FakeModel([
        _verdict(True),    # tp1: human True,  judge pass  -> TP
        _verdict(True),    # tp2: human True,  judge pass  -> TP
        _verdict(True),    # fp:  human False, judge pass  -> FP
        _verdict(False),   # fn:  human True,  judge fail  -> FN
        _verdict(False),   # tn:  human False, judge fail  -> TN
    ]), rubric="...")
    labeled = [(s_tp1, True), (s_tp2, True), (s_fp, False), (s_fn, True), (s_tn, False)]

    report = await judge.calibrate(labeled)

    assert isinstance(report, CalibrationReport)
    assert report.n == 5
    assert report.precision == 2 / 3
    assert report.recall == 2 / 3
    assert report.f1 == 2 / 3                       # harmonic mean of 2/3 and 2/3 is 2/3
    assert report.agreement == 0.6                  # 3 of 5 agree (2 TP + 1 TN)
    # The disagreement queue is exactly the FP and the FN, as (span, human_label, judge_passed).
    assert report.disagreements == [(s_fp, False, True), (s_fn, True, False)]


async def test_calibrate_minimal_2tp_1fp_1fn_matches_prompt_example():
    # Prompt's worked example: 2 TP, 1 FP, 1 FN -> precision 2/3, recall 2/3.
    spans = [_span("a"), _span("b"), _span("c"), _span("d")]
    judge = LLMJudge(model=FakeModel([
        _verdict(True), _verdict(True), _verdict(True), _verdict(False),
    ]), rubric="...")
    labeled = [(spans[0], True), (spans[1], True), (spans[2], False), (spans[3], True)]

    report = await judge.calibrate(labeled)

    assert (report.precision, report.recall, report.f1) == (2 / 3, 2 / 3, 2 / 3)
    assert report.agreement == 0.5                  # 2 of 4 agree (both TP)


async def test_calibrate_zero_denominators_are_zero_not_division_error():
    # Judge passes nothing and every label is False -> TP=FP=FN=0; precision/recall/f1 all 0.0,
    # but agreement is perfect (every judge==human).
    spans = [_span("x"), _span("y")]
    judge = LLMJudge(model=FakeModel([_verdict(False), _verdict(False)]), rubric="...")
    report = await judge.calibrate([(spans[0], False), (spans[1], False)])
    assert report.precision == 0.0 and report.recall == 0.0 and report.f1 == 0.0
    assert report.agreement == 1.0 and report.disagreements == []


async def test_calibrate_empty_is_all_zero():
    judge = LLMJudge(model=FakeModel([]), rubric="...")
    report = await judge.calibrate([])
    assert report.n == 0
    assert (report.precision, report.recall, report.f1, report.agreement) == (0.0, 0.0, 0.0, 0.0)
    assert report.disagreements == []


# ------------------------------------------------------------------ A3: pass_k budgets + best_of_n

@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


answered_3 = Assertion("answered_3", lambda s: "3" in s.output)


def _agent(answer: str = "3", *, total_tokens: int = 0):
    # Two turns (tool call + final). All scripted usage lands on the FINAL turn so the span's
    # usage_total is exactly `total_tokens` (the agent loop sums usage across turns; the tool turn
    # contributes 0 here). This is how the captured spans carry a KNOWN usage_total.
    return Agent(model=FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text=answer, tool_calls=[], usage=Usage(input_tokens=total_tokens)),
    ]), tools=[add])


def _factory(scripts):
    # Hand out a fresh agent per capture, walking `scripts` (a list of (answer, total_tokens)) in order.
    it = iter(scripts)

    def make():
        answer, total = next(it)
        return _agent(answer, total_tokens=total)

    return make


async def test_pass_k_back_compat_returns_a_float_when_budgets_is_none():
    # BACK-COMPAT: with budgets unset, pass_k returns the float pass-rate exactly as before.
    rate = await Eval.pass_k(lambda: _agent(), "add 1 and 2", answered_3, k=3)
    assert isinstance(rate, float)
    assert rate == 1.0


async def test_pass_k_budgets_returns_a_monotonic_nondecreasing_curve():
    # 4 captures, all PASS (answer contains "3"), with usage_total = 10, 20, 30, 40.
    scripts = [("3", 10), ("3", 20), ("3", 30), ("3", 40)]
    curve = await Eval.pass_k(_factory(scripts), "add 1 and 2", answered_3, k=4,
                              budgets=[5, 15, 25, 100])
    assert isinstance(curve, dict)
    # B=5: no run fits -> 0; B=15: only the 10-token run -> 1/4; B=25: 10 & 20 -> 2/4; B=100: all -> 1.0
    assert curve == {5: 0.0, 15: 0.25, 25: 0.5, 100: 1.0}
    # tight budget gives a LOWER rate than a loose one; the curve never decreases as B grows.
    budgets_sorted = sorted(curve)
    rates = [curve[b] for b in budgets_sorted]
    assert rates == sorted(rates)                    # monotonic non-decreasing in B
    assert curve[5] < curve[100]


async def test_pass_k_budgets_excludes_failing_runs_even_under_a_loose_budget():
    # A run must BOTH pass the assertion AND fit the budget. A cheap-but-wrong run never counts.
    scripts = [("3", 10), ("seven", 5), ("3", 40)]   # the 5-token run FAILS the assertion
    curve = await Eval.pass_k(_factory(scripts), "add 1 and 2", answered_3, k=3,
                              budgets=[5, 100])
    # B=5: only the failing 5-token run fits the budget, but it fails -> 0.0
    # B=100: the two passing runs (10 and 40 tokens) both fit -> 2/3
    assert curve[5] == 0.0
    assert curve[100] == 2 / 3


async def test_best_of_n_returns_the_highest_scoring_sample():
    # Score by output length so the k samples have distinct, known values; the winner is the max value.
    by_len = Assertion("by_len", lambda s: len(s.output) >= 3)
    scripts = [("a", 0), ("ccc", 0), ("bb", 0)]            # outputs of length 1, 3, 2
    # by_len.score(span).value is 1.0 for len>=3 ("ccc") else 0.0 -> the 3-char sample is the peak.
    best = await Eval.best_of_n(_factory(scripts), "add 1 and 2", by_len, k=3)
    assert isinstance(best, BestOfN)
    assert best.span.output == "ccc"
    assert best.score.value == 1.0
    assert best.score.value == max(sc.value for sc in best.all_scores)
    assert len(best.all_scores) == 3


async def test_best_of_n_breaks_ties_toward_the_first_sample():
    # Two samples tie at the max score -> the FIRST one wins (max() keeps the first maximal element).
    by_len = Assertion("by_len", lambda s: len(s.output) >= 2)
    scripts = [("xx", 0), ("yy", 0), ("z", 0)]            # first two both score 1.0; third scores 0.0
    best = await Eval.best_of_n(_factory(scripts), "add 1 and 2", by_len, k=3)
    assert best.span.output == "xx"                       # ties -> first
    assert best.score.value == 1.0
