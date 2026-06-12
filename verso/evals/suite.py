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


@dataclass
class UnitReport:
    scores: dict[str, dict[str, VersoScore]] = field(default_factory=dict)   # case -> name -> score

    @property
    def passed(self) -> bool:
        return all(sc.passed for case in self.scores.values() for sc in case.values())


class Eval:
    @staticmethod
    async def unit(*, agent_factory: Callable[[], "object"], cases: dict[str, str],
                   assertions: list[Assertion]) -> UnitReport:
        """Run `agent` (a fresh instance per case — prod==eval: the real Agent via the same stream)
        over a feature×scenario matrix and score each with deterministic assertions."""
        report = UnitReport()
        for case_name, task in cases.items():
            span = await VersoSpan.capture(agent_factory(), task, trace_id=f"{case_name}")
            report.scores[case_name] = {a.name: a.score(span) for a in assertions}
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
