# verso/evals/suite.py
from __future__ import annotations
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from verso.evals.span import VersoSpan, VersoScore


@dataclass(frozen=True)
class Assertion:
    """A deterministic check over a captured run — the preferred (execution) tier of the
    verifiability hierarchy: execution/structural checks first, the judge only as a fallback."""
    name: str
    check: Callable[[VersoSpan], bool]

    def score(self, span: VersoSpan) -> VersoScore:
        ok = bool(self.check(span))
        return VersoScore(name=self.name, passed=ok, value=1.0 if ok else 0.0, kind="assertion")


@dataclass(frozen=True)
class TraceCheck:
    """A deterministic check over the tool PATH (process-level), not just the final output —
    e.g. `lambda s: any(n == "search" for n, _, _, _ in s.tool_calls())`. Same shape as
    Assertion; scores kind="trace" to keep the path tier distinct from output assertions."""
    name: str
    check: Callable[[VersoSpan], bool]

    def score(self, span: VersoSpan) -> VersoScore:
        ok = bool(self.check(span))
        return VersoScore(name=self.name, passed=ok, value=1.0 if ok else 0.0, kind="trace")


@dataclass(frozen=True)
class TrajectoryCheck:
    """A deterministic check over the ORDERED tool path (the names from `span.tool_calls()`) against an
    `expected` sequence — the most common process-level eval, named instead of hand-rolled. `match`:
      - 'exact'     : the actual tool-name list equals `expected` exactly
      - 'in_order'  : `expected` is an ordered SUBSEQUENCE of the actual names (extra calls allowed between)
      - 'any_order' : every `expected` name appears (multiset subset), order irrelevant
    Same `.score()` shape as Assertion/TraceCheck (kind='trace'), so it drops straight into
    `Eval.unit(trace_checks=[...])`."""
    name: str
    expected: tuple
    match: str = "in_order"

    def score(self, span: VersoSpan) -> VersoScore:
        actual = [n for n, *_ in span.tool_calls()]
        exp = list(self.expected)
        if self.match == "exact":
            ok = actual == exp
        elif self.match == "any_order":
            counts = Counter(actual)
            ok = all(counts[name] >= need for name, need in Counter(exp).items())
        else:  # 'in_order' — expected is an ordered subsequence of the actual names
            it = iter(actual)
            ok = all(any(a == e for a in it) for e in exp)
        return VersoScore(name=self.name, passed=ok, value=1.0 if ok else 0.0, kind="trace")


@dataclass
class BestOfN:
    """Peak output / best-of-N: the highest-scoring of k samples for one task. `all_scores` keeps the
    full sample distribution alongside the winner (so you can see the spread, not just the max)."""
    span: VersoSpan
    score: VersoScore
    all_scores: list[VersoScore]


@dataclass
class PredictReport:
    """Does a cheap PROXY forecast the real OUTCOME? (de-risk a leading indicator before you build a
    loop on it). `phi` is the phi coefficient of the proxy-vs-outcome 2×2; `divergent` lists the cases
    where the two checks disagreed (the proxy is lying about those)."""
    n: int
    phi: float
    agreement: float
    confusion: dict                         # keys: tp, fp, fn, tn
    divergent: list                         # (case_name, proxy_passed, outcome_passed) where they differ


@dataclass
class LiftReport:
    """Harness-floor vs model-ceiling — "the harness compounds, models rotate" as numbers. Per axis
    (assertion name): the pass-rate of each model, the `harness_floor` (worst model = what the harness
    delivers regardless of model) and the `model_ceiling` (best-minus-worst spread = the lift a better
    model buys you on top of the floor)."""
    per_axis: dict                          # axis -> {model_label: pass_rate}
    harness_floor: dict                     # axis -> min rate across models
    model_ceiling: dict                     # axis -> (max - min) rate across models


@dataclass
class UnitReport:
    scores: dict[str, dict[str, VersoScore]] = field(default_factory=dict)   # case -> name -> score

    @property
    def passed(self) -> bool:
        return all(sc.passed for case in self.scores.values() for sc in case.values())

    def worst(self, n: int = 5) -> list[tuple[str, str, VersoScore]]:
        """Triage: read the failures first — the n lowest-`value` (case, name, score) tuples,
        ascending by value (the worst-scoring checks across the whole matrix)."""
        flat = [(case, name, sc) for case, names in self.scores.items() for name, sc in names.items()]
        flat.sort(key=lambda t: t[2].value)
        return flat[:n]

    def divergent(self, threshold: float = 0.25) -> list[tuple[str, str, VersoScore]]:
        """Surface judge disagreement: (case, name, score) tuples where the panel's member judges
        diverged by at least `threshold` (high spread = a contested case worth a human look)."""
        return [(case, name, sc) for case, names in self.scores.items()
                for name, sc in names.items() if sc.divergence >= threshold]

    def bucket(self, classifier: Callable[[str, VersoScore], str] | None = None, *,
               failures_only: bool = True) -> dict[str, list[tuple[str, str, VersoScore]]]:
        """Failure-bucketing: group (case, name, score) into named piles so you attack the biggest pile
        first (aggregation BEFORE prioritization). Default `classifier` buckets by `score.name`; pass one
        (case, score)->label for richer piles. `failures_only` (default) keeps only `not passed`."""
        piles: dict[str, list[tuple[str, str, VersoScore]]] = {}
        for case, names in self.scores.items():
            for name, sc in names.items():
                if failures_only and sc.passed:
                    continue
                label = classifier(case, sc) if classifier is not None else sc.name
                piles.setdefault(label, []).append((case, name, sc))
        return piles


class Eval:
    @staticmethod
    async def unit(*, agent_factory: Callable[[], "object"], cases: dict[str, str],
                   assertions: list[Assertion],
                   trace_checks: list[TraceCheck] = ()) -> UnitReport:
        """Run `agent` (a fresh instance per case — prod==eval: the real Agent via the same stream)
        over a feature×scenario matrix and score each with deterministic assertions. `trace_checks`
        (optional) add process-level checks over the tool PATH alongside the output assertions."""
        report = UnitReport()
        for case_name, task in cases.items():
            span = await VersoSpan.capture(agent_factory(), task, trace_id=f"{case_name}")
            scored = {a.name: a.score(span) for a in assertions}
            scored.update({tc.name: tc.score(span) for tc in trace_checks})
            report.scores[case_name] = scored
        return report

    @staticmethod
    async def pass_k(agent_factory: Callable[[], "object"], task: str,
                     assertion: Assertion, *, k: int = 5,
                     budgets: list[int] | None = None) -> "float | dict[int, float]":
        """pass^k — repeat the same case k times; return the pass rate (reliability is a distribution).

        `budgets` (optional) makes reliability a distribution AS A FUNCTION of a token budget, computed
        POST-HOC from each span's `usage_total` — no hooks, no loop change. A run that passed using U
        tokens would also pass under any budget B ≥ U, and would be stopped before passing under B < U,
        so "passed AND usage_total ≤ B" equals the actively-capped pass rate. Returns:
          - `budgets is None` → the float pass-rate, exactly as before (BACK-COMPAT, unchanged).
          - `budgets` set     → dict[int, float] mapping each B → pass-rate under that cap (the curve is
            monotonic non-decreasing in B: a higher budget can only admit more passing runs)."""
        spans = [await VersoSpan.capture(agent_factory(), task, trace_id=f"k{i}") for i in range(k)]
        scored = [(s, assertion.score(s).passed) for s in spans]
        if budgets is None:
            return sum(int(passed) for _, passed in scored) / k
        return {b: sum(1 for s, passed in scored if passed and s.usage_total <= b) / k for b in budgets}

    @staticmethod
    async def best_of_n(agent_factory: Callable[[], "object"], task: str,
                        scorer: Assertion, *, k: int = 5) -> BestOfN:
        """Peak output / best-of-N as a one-liner: run k captures, score each with `scorer`, return the
        highest-scoring one (ties → first). Composes the existing VersoSpan.capture + Assertion.score —
        no loop/model change. The complement of pass_k: pass_k measures the floor (reliability), this
        the ceiling (best achievable on a task)."""
        results = [(s := await VersoSpan.capture(agent_factory(), task, trace_id=f"n{i}"), scorer.score(s))
                   for i in range(k)]
        best_span, best_score = max(results, key=lambda r: r[1].value)   # max() keeps the FIRST on ties
        return BestOfN(span=best_span, score=best_score, all_scores=[sc for _, sc in results])

    @staticmethod
    def from_trace(span: VersoSpan, assertions: list[Assertion]) -> UnitReport:
        """incident -> regression: score a *captured* span (a real past run, e.g. a production
        failure loaded from JSONL) against assertions. The accreting corpus of these IS the moat."""
        report = UnitReport()
        report.scores[span.trace_id] = {a.name: a.score(span) for a in assertions}
        return report

    @staticmethod
    async def judge(*, agent_factory, cases: dict[str, str], panel) -> UnitReport:
        """Run the agent over the matrix and score each capture with a JudgePanel (the LLM-critique
        tier — use where deterministic Assertions can't express the criterion). Post-hoc only."""
        report = UnitReport()
        for case_name, task in cases.items():
            span = await VersoSpan.capture(agent_factory(), task, trace_id=case_name)
            report.scores[case_name] = {panel.name: await panel.score(span)}
        return report

    @staticmethod
    async def predicts(*, agent_factory: Callable[[], "object"], cases: dict[str, str],
                       proxy: Assertion, outcome: Assertion) -> PredictReport:
        """Does a cheap PROXY forecast the real OUTCOME? Capture each case ONCE (like unit()), score it
        with BOTH checks, and report how well the proxy predicts the outcome via the phi coefficient of
        the 2×2 table. Distinct from LLMJudge.calibrate (judge-vs-human): this is leading-indicator-vs-
        what-you-care-about, so you can de-risk a proxy before building a loop on it."""
        tp = fp = fn = tn = 0
        divergent: list = []
        for case_name, task in cases.items():
            span = await VersoSpan.capture(agent_factory(), task, trace_id=case_name)
            p = proxy.score(span).passed
            o = outcome.score(span).passed
            if p and o:
                tp += 1
            elif p and not o:
                fp += 1
            elif not p and o:
                fn += 1
            else:
                tn += 1
            if p != o:
                divergent.append((case_name, p, o))
        n = tp + fp + fn + tn
        denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        phi = (tp * tn - fp * fn) / denom if denom else 0.0
        agreement = (tp + tn) / n if n else 0.0
        return PredictReport(n=n, phi=phi, agreement=agreement,
                             confusion={"tp": tp, "fp": fp, "fn": fn, "tn": tn}, divergent=divergent)

    @staticmethod
    async def lift(*, agent_factory: Callable[[], "object"], cases: dict[str, str],
                   assertions: list[Assertion], models: list) -> LiftReport:
        """Harness-floor vs model-ceiling: run the SAME harness over the SAME cases under each model in
        `models` (a str spec or a Model), score with `assertions`, and report per-axis pass-rates. The
        `harness_floor` (min over models) is what your harness delivers regardless of model; the
        `model_ceiling` (max-minus-min spread) is the lift a better model buys on top of that floor.
        Each capture uses `agent.override(model=M)`, which swaps `agent.model` for the nested capture."""
        # axis -> model_label -> [pass(bool), ...] across cases
        tally: dict[str, dict[str, list[bool]]] = {a.name: {} for a in assertions}
        for m in models:
            label = m if isinstance(m, str) else getattr(m, "model_id", repr(m))
            for case_name, task in cases.items():
                agent = agent_factory()
                with agent.override(model=m):
                    span = await VersoSpan.capture(agent, task, trace_id=f"{label}:{case_name}")
                for a in assertions:
                    tally[a.name].setdefault(label, []).append(a.score(span).passed)
        per_axis: dict = {}
        harness_floor: dict = {}
        model_ceiling: dict = {}
        for axis, by_model in tally.items():
            rates = {lbl: sum(passes) / len(passes) for lbl, passes in by_model.items()}
            per_axis[axis] = rates
            vals = list(rates.values())
            harness_floor[axis] = min(vals) if vals else 0.0
            model_ceiling[axis] = (max(vals) - min(vals)) if vals else 0.0
        return LiftReport(per_axis=per_axis, harness_floor=harness_floor, model_ceiling=model_ceiling)
