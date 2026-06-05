# tests/test_types.py
from verso.types import StopReason, Usage, AgentResult


def test_usage_adds():
    a = Usage(input_tokens=10, output_tokens=5)
    b = Usage(input_tokens=3, output_tokens=7)
    total = a + b
    assert total == Usage(input_tokens=13, output_tokens=12)


def test_agent_result_fields():
    r = AgentResult(output="hi", stop_reason=StopReason.END_TURN, usage=Usage(), steps=1)
    assert r.output == "hi"
    assert r.stop_reason is StopReason.END_TURN
    assert r.steps == 1


def test_stop_reason_is_str_enum():
    assert StopReason.MAX_STEPS == "max_steps"
