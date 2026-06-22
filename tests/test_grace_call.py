# tests/test_grace_call.py
from verso.core.loop import run_loop
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.tool import tool
from verso.types import StopReason, Usage


@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b


def _loop_resp(i):
    return ModelResponse(text="", tool_calls=[ToolCall(id=f"t{i}", name="add", arguments={"a": i, "b": 1})], usage=Usage(output_tokens=1))


async def test_default_max_steps_is_byte_identical_empty_output():
    fm = FakeModel([_loop_resp(i) for i in range(10)])
    result = await run_loop(fm, [add], "loop", max_steps=3, stuck_thresholds=None)
    assert result.stop_reason is StopReason.MAX_STEPS
    assert result.output == ""                    # default policy='stop' — unchanged from today


async def test_generate_policy_emits_best_effort_answer():
    # 3 looping steps, then a final text response consumed by the single grace call (tools=[])
    fm = FakeModel([_loop_resp(i) for i in range(3)] + [ModelResponse(text="best-effort summary", tool_calls=[], usage=Usage(output_tokens=5))])
    result = await run_loop(fm, [add], "loop", max_steps=3, max_steps_policy="generate", stuck_thresholds=None)
    assert result.stop_reason is StopReason.MAX_STEPS      # still hit the cap...
    assert result.output == "best-effort summary"          # ...but a grace answer instead of ''
    # the grace call must request NO tools (it forces a text answer, not another tool round)
    assert fm.calls[-1][1] == []
