# tests/test_loop.py
from verso.core.loop import run_loop
from verso.model.fake import FakeModel
from verso.model.base import Message, ModelResponse, ToolCall
from verso.tools.tool import tool
from verso.types import StopReason, Usage


@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b


async def test_loop_runs_tool_then_returns_text():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage(output_tokens=1)),
        ModelResponse(text="The answer is 3.", tool_calls=[], usage=Usage(output_tokens=2)),
    ])
    result = await run_loop(fm, [add], "add 1 and 2", max_steps=25)
    assert result.output == "The answer is 3."
    assert result.stop_reason is StopReason.END_TURN
    assert result.steps == 2
    assert result.usage.output_tokens == 3


async def test_loop_feeds_tool_result_back_to_model():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 4, "b": 5})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    await run_loop(fm, [add], "go")
    # second call's message history must contain the tool result "9"
    second_call_messages = fm.calls[1][0]
    tool_msgs = [m for m in second_call_messages if m.role == "tool"]
    assert any("9" in m.content for m in tool_msgs)


async def test_loop_unknown_tool_is_reported_not_crashed():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="nope", arguments={})], usage=Usage()),
        ModelResponse(text="recovered", tool_calls=[], usage=Usage()),
    ])
    result = await run_loop(fm, [add], "go")
    assert result.output == "recovered"
    tool_msgs = [m for m in fm.calls[1][0] if m.role == "tool"]
    assert any("unknown tool" in m.content.lower() for m in tool_msgs)


async def test_loop_hits_max_steps():
    # model always asks for a tool, never finishes
    looping = [ModelResponse(text="", tool_calls=[ToolCall(id=f"t{i}", name="add", arguments={"a": 1, "b": 1})], usage=Usage()) for i in range(10)]
    fm = FakeModel(looping)
    result = await run_loop(fm, [add], "loop forever", max_steps=3)
    assert result.stop_reason is StopReason.MAX_STEPS
    assert result.steps == 3
