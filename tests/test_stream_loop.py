# tests/test_stream_loop.py
from verso.core.stream_loop import run_stream
from verso.stream.events import EventType
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.tool import tool
from verso.tools.builtins import done
from verso.types import StopReason, Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def _events(aiter):
    return [ev async for ev in aiter]


async def test_stream_tool_then_text():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text="the answer is 3", tool_calls=[], usage=Usage(output_tokens=4)),
    ])
    evs = await _events(run_stream(fm, [add], "add 1 and 2"))
    types = [e.type for e in evs]
    assert types[0] is EventType.STEP
    assert EventType.TOOL_START in types and EventType.TOOL_RESULT in types
    assert types[-1] is EventType.DONE
    # true-delta: concatenated message deltas == the final text
    text = "".join(e.text for e in evs if e.type is EventType.MESSAGE_DELTA)
    assert text == "the answer is 3"
    final = evs[-1].result
    assert final.output == "the answer is 3" and final.stop_reason is StopReason.END_TURN


async def test_stream_tool_start_and_result_payload():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 4, "b": 5})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    evs = await _events(run_stream(fm, [add], "go"))
    start = next(e for e in evs if e.type is EventType.TOOL_START)
    result = next(e for e in evs if e.type is EventType.TOOL_RESULT)
    assert start.tool == "add" and start.arguments == {"a": 4, "b": 5}
    assert result.tool == "add" and result.ok is True and result.content == "9"


async def test_stream_done_tool_terminates():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="d", name="done", arguments={"result": "final"})], usage=Usage()),
    ])
    evs = await _events(run_stream(fm, [done], "finish"))
    assert evs[-1].type is EventType.DONE
    assert evs[-1].result.output == "final" and evs[-1].result.stop_reason is StopReason.DONE


async def test_stream_hits_max_steps():
    looping = [ModelResponse(text="", tool_calls=[ToolCall(id=f"t{i}", name="add", arguments={"a": 1, "b": 1})], usage=Usage()) for i in range(5)]
    evs = await _events(run_stream(FakeModel(looping), [add], "loop", max_steps=2))
    assert evs[-1].type is EventType.DONE and evs[-1].result.stop_reason is StopReason.MAX_STEPS
