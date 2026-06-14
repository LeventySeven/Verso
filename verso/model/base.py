# verso/model/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence, TYPE_CHECKING

from verso.types import Usage

if TYPE_CHECKING:
    from verso.tools.tool import Tool


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    role: str                                   # "user" | "assistant" | "tool"
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)   # set on assistant turns
    tool_call_id: str | None = None             # set on tool-result turns
    name: str | None = None                     # tool name, on tool-result turns
    id: str | None = None                       # optional stable id for history dedup/compaction (see verso/context/history.py)


@dataclass
class ModelResponse:
    text: str
    tool_calls: list[ToolCall]
    usage: Usage


class Model(Protocol):
    """A provider that turns a message history + available tools into one response."""

    async def complete(self, messages: Sequence[Message], tools: Sequence["Tool"],
                       *, system: str | None = None) -> ModelResponse:
        ...
