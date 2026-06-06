# tests/test_events.py
from verso.stream.events import EventType, StreamEvent


def test_all_seven_event_types():
    vals = {e.value for e in EventType}
    assert vals == {
        "step", "message.delta", "reasoning.delta",
        "tool.start", "tool.result", "error", "done",
    }


def test_message_delta_event():
    ev = StreamEvent(type=EventType.MESSAGE_DELTA, text="hi")
    assert ev.type is EventType.MESSAGE_DELTA and ev.text == "hi"


def test_tool_events():
    start = StreamEvent(type=EventType.TOOL_START, tool="add", arguments={"a": 1})
    res = StreamEvent(type=EventType.TOOL_RESULT, tool="add", ok=True, content="3")
    assert start.tool == "add" and start.arguments == {"a": 1}
    assert res.ok is True and res.content == "3"


def test_step_and_error_and_done():
    assert StreamEvent(type=EventType.STEP, step=2).step == 2
    assert StreamEvent(type=EventType.ERROR, error="boom").error == "boom"
    assert StreamEvent(type=EventType.DONE, result="R").result == "R"
