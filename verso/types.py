# verso/types.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class StopReason(str, Enum):
    END_TURN = "end_turn"      # model returned a final text answer (no tool calls)
    MAX_STEPS = "max_steps"    # loop hit the max_steps cap
    ERROR = "error"            # unrecoverable error (later phases add more reasons)


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


@dataclass
class AgentResult:
    output: str
    stop_reason: StopReason
    usage: Usage
    steps: int
