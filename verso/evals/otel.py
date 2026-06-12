# verso/evals/otel.py
from __future__ import annotations
from verso.evals.span import VersoSpan, VersoScore


def to_otel_attrs(span: VersoSpan, scores: list[VersoScore] | None = None) -> dict:
    """Project a captured run to OpenTelemetry GenAI semantic-convention attributes (dot-form, the
    §10 locked fix: `gen_ai.usage.cache_read.input_tokens`-style; NO `RERANKER` span kind — Verso
    has no reranker primitive). This is what a composed Langfuse/OTel exporter consumes; it is the
    in-house BUILD, the exporter engine is the COMPOSE."""
    attrs = {
        "gen_ai.system": "verso",
        "gen_ai.operation.name": "agent.run",
        "gen_ai.response.finish_reason": span.stop_reason,
        "gen_ai.usage.input_tokens": span.usage_in,
        "gen_ai.usage.output_tokens": span.usage_out,
        "verso.trace_id": span.trace_id,
        "verso.steps": span.steps,
        "verso.tools": ",".join(span.tool_names()),
        "verso.step_pass_rate": span.step_pass_rate(),
    }
    for s in (scores or []):
        attrs[f"verso.score.{s.name}"] = s.value
    return attrs
