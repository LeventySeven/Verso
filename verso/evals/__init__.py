# verso/evals/__init__.py
"""Verso evals — the in-process wedge: Eval.unit/judge, Assertion, VersoSpan/VersoScore,
LLMJudge/JudgePanel, define_outcome, and the OTel gen_ai.* projection.

The heavy engine is composed, not built: install `verso[evals]` to export `VersoSpan` to
Langfuse / score with autoevals / run offline CI with `braintrust.Eval()`. These are optional
and lazily imported; the in-process surface above needs none of them.
"""
from verso.evals.span import VersoSpan, VersoScore, SpanRecord
from verso.evals.suite import Eval, Assertion, TraceCheck, UnitReport, BestOfN
from verso.evals.judge import Judge, LLMJudge, JudgePanel, CalibrationReport
from verso.evals.outcome import define_outcome, OutcomeResult
from verso.evals.otel import to_otel_attrs

__all__ = ["VersoSpan", "VersoScore", "SpanRecord", "Eval", "Assertion", "TraceCheck",
           "UnitReport", "BestOfN", "Judge", "LLMJudge", "JudgePanel", "CalibrationReport",
           "define_outcome", "OutcomeResult", "to_otel_attrs"]
