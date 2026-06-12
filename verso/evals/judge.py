# verso/evals/judge.py
from __future__ import annotations
from typing import Protocol, runtime_checkable

from verso.evals.span import VersoSpan, VersoScore
from verso.tools.coerce import coerce
from verso.model.base import Model, Message


@runtime_checkable
class Judge(Protocol):
    async def score(self, span: VersoSpan) -> VersoScore: ...


class LLMJudge:
    """Post-hoc LLM judge — NEVER in the hot path. Pluggable model (use a *different* provider
    than the agent under test; `--judge-model <other-provider>`). The judge sees only the captured
    span (the eval-gaming guard: it is isolated from the agent's write surface).

    NOTE for alignment work: when validating a judge against human labels, score it by
    precision/recall, NOT raw agreement (raw agreement misleads under class imbalance — §14.8)."""
    def __init__(self, model: Model, rubric: str, name: str = "judge"):
        self.model, self.rubric, self.name = model, rubric, name

    async def score(self, span: VersoSpan) -> VersoScore:
        prompt = (f"Rubric: {self.rubric}\n\nThe agent produced this final output:\n{span.output}\n\n"
                  'Reply with ONLY JSON: {"passed": bool, "value": 0..1, "detail": str}.')
        resp = await self.model.complete([Message(role="user", content=prompt)], [])
        try:
            v = coerce(resp.text, dict)
            return VersoScore(name=self.name, passed=bool(v.get("passed")),
                              value=float(v.get("value", 0.0)), kind="judge", detail=str(v.get("detail", "")))
        except Exception as e:                       # a judge failure is a score, never an exception into the suite
            return VersoScore(name=self.name, passed=False, value=0.0, kind="judge", detail=f"judge-parse-error: {e}")


class JudgePanel:
    """A panel of judges, aggregated by majority (pass) + mean (value). Post-hoc, never in the hot
    path. The default panel (e.g. Sonnet/GPT/Gemini) is an OVERRIDABLE example — never a hardcoded
    three-vendor lock-in. Use a different provider here than the agent under test."""
    def __init__(self, judges: list[Judge], name: str = "panel"):
        self.judges, self.name = judges, name

    async def score(self, span: VersoSpan) -> VersoScore:
        scores = [await j.score(span) for j in self.judges]
        passed = sum(s.passed for s in scores) * 2 > len(scores)      # majority
        value = sum(s.value for s in scores) / len(scores)
        return VersoScore(name=self.name, passed=passed, value=value, kind="judge",
                          detail="; ".join(f"{s.name}={s.value:.2f}" for s in scores))
