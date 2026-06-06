# tests/test_sse.py
import json
from verso.stream.sse import to_sse, sse
from verso.stream.events import EventType, StreamEvent
from verso.types import AgentResult, StopReason, Usage


def _parse(line: str) -> dict:
    assert line.startswith("data: ") and line.endswith("\n\n")
    return json.loads(line[len("data: "):].strip())


def test_to_sse_message_delta():
    payload = _parse(to_sse(StreamEvent(type=EventType.MESSAGE_DELTA, text="hi")))
    assert payload == {"type": "message.delta", "text": "hi"}


def test_to_sse_tool_result_omits_empty_fields():
    payload = _parse(to_sse(StreamEvent(type=EventType.TOOL_RESULT, tool="add", ok=True, content="3")))
    assert payload == {"type": "tool.result", "tool": "add", "ok": True, "content": "3"}


def test_to_sse_done_serializes_result():
    r = AgentResult(output="42", stop_reason=StopReason.END_TURN, usage=Usage(input_tokens=5, output_tokens=2), steps=3)
    payload = _parse(to_sse(StreamEvent(type=EventType.DONE, result=r)))
    assert payload["type"] == "done"
    assert payload["result"]["output"] == "42"
    assert payload["result"]["stop_reason"] == "end_turn"
    assert payload["result"]["usage"] == {"input_tokens": 5, "output_tokens": 2}
    assert payload["result"]["steps"] == 3


async def test_sse_stream_terminates_with_done_sentinel():
    async def gen():
        yield StreamEvent(type=EventType.MESSAGE_DELTA, text="a")
        yield StreamEvent(type=EventType.DONE, result=AgentResult("a", StopReason.END_TURN, Usage(), 1))
    lines = [line async for line in sse(gen())]
    assert lines[-1] == "data: [DONE]\n\n"
    assert _parse(lines[0]) == {"type": "message.delta", "text": "a"}
