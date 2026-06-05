# tests/test_loop_done.py
from verso.core.loop import run_loop
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.builtins import done, think
from verso.types import StopReason, Usage


async def test_loop_terminates_on_done_tool():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="d1", name="done", arguments={"result": "final answer"})], usage=Usage(output_tokens=1)),
    ])
    result = await run_loop(fm, [done], "do it")
    assert result.output == "final answer"
    assert result.stop_reason is StopReason.DONE
    assert result.steps == 1


async def test_loop_think_then_done():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="think", arguments={"thought": "plan"})], usage=Usage()),
        ModelResponse(text="", tool_calls=[ToolCall(id="d1", name="done", arguments={"result": "42"})], usage=Usage()),
    ])
    result = await run_loop(fm, [think, done], "compute")
    assert result.output == "42"
    assert result.stop_reason is StopReason.DONE
    assert result.steps == 2
