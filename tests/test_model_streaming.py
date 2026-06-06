# tests/test_model_streaming.py
from verso.model.streaming import ModelStreamChunk, iter_model_stream
from verso.model.fake import FakeModel
from verso.model.base import Message, ModelResponse, ToolCall
from verso.types import Usage


async def _collect(aiter):
    return [c async for c in aiter]


async def test_fake_model_streams_text_in_deltas_then_usage():
    fm = FakeModel([ModelResponse(text="hello world", tool_calls=[], usage=Usage(output_tokens=2))])
    chunks = await _collect(fm.stream([Message(role="user", content="hi")], []))
    assert all(isinstance(c, ModelStreamChunk) for c in chunks)
    texts = [c.text for c in chunks if c.kind == "text"]
    assert "".join(texts) == "hello world"
    assert len(texts) >= 2                         # true-delta: more than one piece
    assert chunks[-1].kind == "usage" and chunks[-1].usage.output_tokens == 2
    assert fm.calls and fm.calls[0][0][0].content == "hi"   # recorded the call


async def test_fake_model_streams_tool_calls():
    tc = ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})
    fm = FakeModel([ModelResponse(text="", tool_calls=[tc], usage=Usage())])
    chunks = await _collect(fm.stream([], []))
    tool_chunks = [c for c in chunks if c.kind == "tool_call"]
    assert len(tool_chunks) == 1 and tool_chunks[0].tool_call is tc


class _CompleteOnly:
    """A model with NO stream() — exercises the iter_model_stream fallback."""
    def __init__(self, resp):
        self._resp = resp

    async def complete(self, messages, tools, *, system=None):
        return self._resp


async def test_iter_model_stream_falls_back_to_complete():
    resp = ModelResponse(text="done", tool_calls=[ToolCall(id="t", name="f", arguments={})], usage=Usage(input_tokens=3))
    chunks = await _collect(iter_model_stream(_CompleteOnly(resp), [], []))
    kinds = [c.kind for c in chunks]
    assert kinds == ["text", "tool_call", "usage"]
    assert chunks[0].text == "done"
    assert chunks[2].usage.input_tokens == 3


async def test_iter_model_stream_uses_stream_when_present():
    fm = FakeModel([ModelResponse(text="hi", tool_calls=[], usage=Usage())])
    chunks = await _collect(iter_model_stream(fm, [], []))
    assert any(c.kind == "text" for c in chunks)
    assert len(fm.calls) == 1                       # went through stream(), recorded
