# tests/test_fake_model.py
from verso.model.base import Message, ToolCall, ModelResponse
from verso.model.fake import FakeModel
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


async def test_fake_model_returns_scripted_responses_in_order():
    r1 = ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage(output_tokens=1))
    r2 = ModelResponse(text="the answer is 3", tool_calls=[], usage=Usage(output_tokens=2))
    fm = FakeModel([r1, r2])

    out1 = await fm.complete([Message(role="user", content="add 1 and 2")], [])
    out2 = await fm.complete([], [])
    assert out1 is r1
    assert out2 is r2
    assert len(fm.calls) == 2


async def test_fake_model_raises_when_exhausted():
    fm = FakeModel([])
    import pytest
    with pytest.raises(AssertionError):
        await fm.complete([], [])
