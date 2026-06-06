# verso/stream/events.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any


class EventType(str, Enum):
    STEP = "step"                       # a loop step begins
    MESSAGE_DELTA = "message.delta"     # a chunk of the assistant's text answer
    REASONING_DELTA = "reasoning.delta" # a chunk of thinking (separate channel)
    TOOL_START = "tool.start"           # a tool call is about to run
    TOOL_RESULT = "tool.result"         # a tool returned
    ERROR = "error"                     # an error occurred
    DONE = "done"                       # terminal: carries the final AgentResult


@dataclass
class StreamEvent:
    """One true-delta event. Consumers match on `type`; text events are deltas to concatenate."""
    type: EventType
    text: str = ""                       # MESSAGE_DELTA / REASONING_DELTA
    tool: str | None = None              # TOOL_START / TOOL_RESULT
    arguments: dict | None = None        # TOOL_START
    ok: bool | None = None               # TOOL_RESULT
    content: str | None = None           # TOOL_RESULT
    step: int | None = None              # STEP
    error: str | None = None             # ERROR
    result: Any = None                   # DONE (an AgentResult)
