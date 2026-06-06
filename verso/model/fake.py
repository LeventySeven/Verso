# verso/model/fake.py
from __future__ import annotations
from typing import Sequence

from verso.model.base import Message, ModelResponse
from verso.model.streaming import ModelStreamChunk
from verso.tools.tool import Tool


class FakeModel:
    """A scripted Model for offline tests. Returns the given responses in order."""

    def __init__(self, responses: list[ModelResponse]):
        self._responses = list(responses)
        self.calls: list[tuple[list[Message], list[Tool], str | None]] = []

    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool],
                       *, system: str | None = None) -> ModelResponse:
        self.calls.append((list(messages), list(tools), system))
        assert self._responses, "FakeModel ran out of scripted responses"
        return self._responses.pop(0)

    async def stream(self, messages: Sequence[Message], tools: Sequence[Tool],
                     *, system: str | None = None):
        self.calls.append((list(messages), list(tools), system))
        assert self._responses, "FakeModel ran out of scripted responses"
        resp = self._responses.pop(0)
        text = resp.text or ""
        if text:
            mid = len(text) // 2 or len(text)
            for piece in (text[:mid], text[mid:]):
                if piece:
                    yield ModelStreamChunk(kind="text", text=piece)
        for tc in resp.tool_calls:
            yield ModelStreamChunk(kind="tool_call", tool_call=tc)
        yield ModelStreamChunk(kind="usage", usage=resp.usage)
