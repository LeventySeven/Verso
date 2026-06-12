# tests/test_evals_otel.py
from verso.evals.otel import to_otel_attrs
from verso.evals.span import VersoSpan, VersoScore


def test_otel_uses_dotform_gen_ai_attrs_and_no_reranker():
    span = VersoSpan(trace_id="t1", output="hi", stop_reason="end_turn", steps=2, usage_total=24)
    span.usage_in, span.usage_out = 16, 8
    attrs = to_otel_attrs(span, [VersoScore("answered", passed=True, value=1.0)])
    assert attrs["gen_ai.usage.input_tokens"] == 16          # dot-form (the §10 locked fix)
    assert attrs["gen_ai.usage.output_tokens"] == 8
    assert attrs["gen_ai.response.finish_reason"] == "end_turn"
    assert attrs["verso.score.answered"] == 1.0
    assert not any("RERANKER" in k or "reranker" in k for k in attrs)   # §10: drop the RERANKER span kind
