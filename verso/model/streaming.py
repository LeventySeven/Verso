# verso/model/streaming.py
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator, Sequence

from verso.model.base import Message, ModelResponse, ToolCall
from verso.tools.tool import Tool
from verso.types import Usage


@dataclass
class ModelStreamChunk:
    kind: str                          # "text" | "reasoning" | "tool_call" | "usage"
    text: str = ""
    tool_call: ToolCall | None = None
    usage: Usage | None = None


async def _chunks_from_response(resp: ModelResponse) -> AsyncIterator[ModelStreamChunk]:
    if resp.text:
        yield ModelStreamChunk(kind="text", text=resp.text)
    for tc in resp.tool_calls:
        yield ModelStreamChunk(kind="tool_call", tool_call=tc)
    yield ModelStreamChunk(kind="usage", usage=resp.usage)


async def iter_model_stream(model, messages: Sequence[Message], tools: Sequence[Tool],
                            *, system: str | None = None) -> AsyncIterator[ModelStreamChunk]:
    """Stream chunks from `model`: use model.stream() if it has one, else wrap complete().
    This lets the event loop stream over ANY model (incl. FailoverModel / complete-only)."""
    streamer = getattr(model, "stream", None)
    if streamer is not None:
        async for chunk in streamer(messages, tools, system=system):
            yield chunk
        return
    resp = await model.complete(messages, tools, system=system)
    async for chunk in _chunks_from_response(resp):
        yield chunk
