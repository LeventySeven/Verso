# verso/evals/suite.py
from __future__ import annotations
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
                     assertion: Assertion, *, k: int = 5) -> float:
        """pass^k — repeat the same case k times; return the pass rate (reliability is a distribution)."""
        passes = 0
        for i in range(k):
            span = await VersoSpan.capture(agent_factory(), task, trace_id=f"k{i}")
            passes += int(assertion.score(span).passed)
        return passes / k

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
