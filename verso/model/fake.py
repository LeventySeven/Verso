# verso/model/fake.py
from __future__ import annotations
from typing import Sequence

from verso.model.base import Message, ModelResponse
from verso.tools.tool import Tool


class FakeModel:
    """A scripted Model for offline tests. Returns the given responses in order."""

    def __init__(self, responses: list[ModelResponse]):
        self._responses = list(responses)
        self.calls: list[tuple[list[Message], list[Tool]]] = []

    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool]) -> ModelResponse:
        self.calls.append((list(messages), list(tools)))
        assert self._responses, "FakeModel ran out of scripted responses"
        return self._responses.pop(0)
