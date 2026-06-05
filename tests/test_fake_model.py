# tests/test_fake_model.py
from verso.model.base import Message, ToolCall, ModelResponse
from verso.types import Usage


def test_message_defaults():
    m = Message(role="user", content="hello")
    assert m.tool_calls == []
    assert m.tool_call_id is None


def test_tool_call_fields():
    tc = ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})
    assert tc.name == "add"
    assert tc.arguments["a"] == 1


def test_model_response_fields():
    r = ModelResponse(text="done", tool_calls=[], usage=Usage(input_tokens=1))
    assert r.text == "done"
    assert r.tool_calls == []
    assert r.usage.input_tokens == 1
