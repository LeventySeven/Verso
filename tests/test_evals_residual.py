# tests/test_evals_residual.py
# Three additive eval-craft methods. Additive: every prior eval test passes UNMODIFIED.
#   1. Eval.predicts  — does a cheap PROXY forecast the real OUTCOME? (phi coefficient of the 2×2)
#   2. UnitReport.bucket — group failures into named piles before prioritizing
#   3. Eval.lift      — harness-floor vs model-ceiling across a list of models
# FakeModel scripts make the proxy/outcome per span and each model's behavior fully known, so every
# count, phi, agreement, divergent list, and pass-rate is exact.
from verso import Agent, tool, PredictReport, LiftReport, VersoScore
from verso.evals.suite import Eval, Assertion, UnitReport
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def search(q: str) -> str:
    "Search."
    return "hit"


# Tier-mixed assertions: PROXY reads the tool PATH (a cheap leading indicator), OUTCOME reads the
# final output (what we actually care about). Scripting each span's path + output drives the 2×2.
proxy = Assertion("proxy", lambda s: "search" in s.tool_names())
outcome = Assertion("outcome", lambda s: "done" in s.output)


def _agent(*, did_search: bool, answer: str):
    # A span where proxy==did_search and outcome==("done" in answer), both known per construction.
    responses: list[ModelResponse] = []
    if did_search:
        responses.append(ModelResponse(
            text="", tool_calls=[ToolCall(id="t1", name="search", arguments={"q": "x"})], usage=Usage()))
    responses.append(ModelResponse(text=answer, tool_calls=[], usage=Usage()))
    return Agent(model=FakeModel(responses), tools=[search])


def _factory(specs):
    # Hand out a fresh agent per capture, walking `specs` (list of (did_search, answer)) in order.
    it = iter(specs)

    def make():
        did_search, answer = next(it)
        return _agent(did_search=did_search, answer=answer)

    return make


# ------------------------------------------------------------------------------- 1. Eval.predicts

async def test_predicts_known_2x2_phi_agreement_and_divergent():
    # 4 cases, one of each cell (proxy = did_search, outcome = "done" in answer):
    #   tp: search + "done"      proxy True,  outcome True
    #   fp: search + "nope"      proxy True,  outcome False
    #   fn: no-search + "done"   proxy False, outcome True
    #   tn: no-search + "nope"   proxy False, outcome False
    cases = {"tp": "a", "fp": "b", "fn": "c", "tn": "d"}
    specs = [(True, "done"), (True, "nope"), (False, "done"), (False, "nope")]
    report = await Eval.predicts(agent_factory=_factory(specs), cases=cases,
                                 proxy=proxy, outcome=outcome)
    assert isinstance(report, PredictReport)
    assert report.n == 4
    assert report.confusion == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    # phi = (tp*tn - fp*fn)/sqrt((tp+fp)(tp+fn)(tn+fp)(tn+fn)) = (1-1)/sqrt(2*2*2*2) = 0/4 = 0.0
    assert report.phi == 0.0
    assert report.agreement == 0.5                       # (tp+tn)/n = 2/4
    # divergent = the cells where proxy != outcome: the FP (True,False) and the FN (False,True).
    assert report.divergent == [("fp", True, False), ("fn", False, True)]


async def test_predicts_perfect_correlation_phi_one():
    # Proxy perfectly forecasts outcome: every search->done, every no-search->nope. 2 TP, 2 TN.
    cases = {"a": "1", "b": "2", "c": "3", "d": "4"}
    specs = [(True, "done"), (True, "done"), (False, "nope"), (False, "nope")]
    report = await Eval.predicts(agent_factory=_factory(specs), cases=cases,
                                 proxy=proxy, outcome=outcome)
    assert report.confusion == {"tp": 2, "fp": 0, "fn": 0, "tn": 2}
    # phi = (2*2 - 0)/sqrt((2)(2)(2)(2)) = 4/4 = 1.0 ; perfect agreement, nothing divergent.
    assert report.phi == 1.0
    assert report.agreement == 1.0
    assert report.divergent == []


async def test_predicts_zero_denominator_is_phi_zero_not_crash():
    # Proxy passes on EVERY case (all search) -> fn = tn = 0, so a factor of the denominator is 0.
    # Must return phi 0.0 (no ZeroDivisionError).
    cases = {"a": "1", "b": "2"}
    specs = [(True, "done"), (True, "nope")]             # tp=1, fp=1, fn=0, tn=0
    report = await Eval.predicts(agent_factory=_factory(specs), cases=cases,
                                 proxy=proxy, outcome=outcome)
    assert report.confusion == {"tp": 1, "fp": 1, "fn": 0, "tn": 0}
    assert report.phi == 0.0                              # denom factor zero -> 0.0, no crash
    assert report.agreement == 0.5                        # (1+0)/2


# ---------------------------------------------------------------------------- 2. UnitReport.bucket

def _score(name: str, passed: bool) -> VersoScore:
    return VersoScore(name=name, passed=passed, value=1.0 if passed else 0.0)


def _report() -> UnitReport:
    # Mixed pass/fail across cases and names; two distinct failure names share a prefix ("fmt_*").
    return UnitReport(scores={
        "case1": {"fmt_json": _score("fmt_json", False), "answered": _score("answered", True)},
        "case2": {"fmt_csv": _score("fmt_csv", False), "answered": _score("answered", False)},
        "case3": {"fmt_json": _score("fmt_json", True), "answered": _score("answered", False)},
    })


def test_bucket_groups_failures_by_name_by_default():
    piles = _report().bucket()
    # Only failures, keyed by score.name. fmt_json fails once (case1), answered fails twice (case2,3).
    assert set(piles) == {"fmt_json", "fmt_csv", "answered"}
    assert piles["fmt_json"] == [("case1", "fmt_json", _report().scores["case1"]["fmt_json"])]
    assert [c for c, _, _ in piles["answered"]] == ["case2", "case3"]
    assert [c for c, _, _ in piles["fmt_csv"]] == ["case2"]
    # Every bucketed score is a failure.
    assert all(not sc.passed for pile in piles.values() for _, _, sc in pile)


def test_bucket_custom_classifier_groups_by_prefix():
    # A richer pile: collapse fmt_json + fmt_csv into one "fmt" bucket via a (case, score) classifier.
    piles = _report().bucket(lambda c, s: s.name.split("_")[0])
    assert set(piles) == {"fmt", "answered"}
    assert [c for c, _, _ in piles["fmt"]] == ["case1", "case2"]    # both fmt_* failures, in case order
    assert [c for c, _, _ in piles["answered"]] == ["case2", "case3"]


def test_bucket_failures_only_false_includes_passes():
    piles = _report().bucket(failures_only=False)
    # answered now includes the passing case3-... wait: answered passes in case1, fails in case2/case3.
    # With failures_only=False every (case, name, score) appears.
    flat = [(c, n) for pile in piles.values() for c, n, _ in pile]
    assert ("case1", "answered") in flat                 # a PASS is now included
    assert len(flat) == 6                                 # 3 cases x 2 names, nothing filtered
    assert any(sc.passed for pile in piles.values() for _, _, sc in pile)


# ------------------------------------------------------------------------------------ 3. Eval.lift

@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


answered_3 = Assertion("answered_3", lambda s: "3" in s.output)


def _model(answer: str, label: str) -> FakeModel:
    # A one-turn scripted model with a known model_id (the lift label) and a known output.
    m = FakeModel([ModelResponse(text=answer, tool_calls=[], usage=Usage())])
    m.model_id = label
    return m


async def test_lift_floor_is_min_and_ceiling_is_spread_across_models():
    # Two models behind the SAME harness over the SAME case. `good` answers "3" (passes answered_3),
    # `bad` answers "seven" (fails). override(model=M) swaps agent.model for each capture, so the two
    # rates are 1.0 (good) and 0.0 (bad).
    good = _model("3", "good")
    bad = _model("seven", "bad")
    # A fresh base agent per capture; override picks the per-model FakeModel. The base model is never
    # consumed (override replaces it before capture), so a bare placeholder is fine.
    placeholder = FakeModel([])
    report = await Eval.lift(
        agent_factory=lambda: Agent(model=placeholder, tools=[add]),
        cases={"only": "add 1 and 2"},
        assertions=[answered_3],
        models=[good, bad],
    )
    assert isinstance(report, LiftReport)
    # per_axis: the axis "answered_3" maps each model_id label to its pass-rate.
    assert report.per_axis == {"answered_3": {"good": 1.0, "bad": 0.0}}
    assert report.harness_floor == {"answered_3": 0.0}   # worst model = the floor the harness guarantees
    assert report.model_ceiling == {"answered_3": 1.0}   # max - min spread = the lift a better model buys


async def test_lift_uses_string_specs_as_labels_and_picks_each_model():
    # Confirm the label rule: a str spec is its own label, a Model uses model_id. Here both are Models
    # but with different scripted answers across TWO cases, so the rates are fractional and exact.
    #   m_hi: "3" on both cases -> rate 1.0 ; m_lo: "3" then "x" -> rate 0.5
    m_hi = FakeModel([ModelResponse(text="3", tool_calls=[], usage=Usage()),
                      ModelResponse(text="3", tool_calls=[], usage=Usage())])
    m_hi.model_id = "hi"
    m_lo = FakeModel([ModelResponse(text="3", tool_calls=[], usage=Usage()),
                      ModelResponse(text="x", tool_calls=[], usage=Usage())])
    m_lo.model_id = "lo"
    report = await Eval.lift(
        agent_factory=lambda: Agent(model=FakeModel([]), tools=[add]),
        cases={"c1": "add 1 and 2", "c2": "add 1 and 2"},
        assertions=[answered_3],
        models=[m_hi, m_lo],
    )
    assert report.per_axis["answered_3"] == {"hi": 1.0, "lo": 0.5}
    assert report.harness_floor["answered_3"] == 0.5
    assert report.model_ceiling["answered_3"] == 0.5
