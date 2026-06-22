# verso/types.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class StopReason(str, Enum):
    END_TURN = "end_turn"      # model returned a final text answer (no tool calls)
    DONE = "done"              # model called the `done` tool to terminate with a result
    MAX_STEPS = "max_steps"    # loop hit the max_steps cap
    PAUSED = "paused"          # durable run paused for a human decision; resumable via resume_token
    STUCK = "stuck"            # doom-loop detected (repeated identical action / error spiral) — honest early stop
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
    parsed: object | None = None      # set when run(output_type=...) succeeds
    resume_token: str | None = None   # set when stop_reason is PAUSED; pass to Agent.resume(...)
    pending: object | None = None     # the HumanRequest awaiting an answer (typed object to avoid import cycle)
    truncated: bool = False           # the terminating model response was cut off by max_tokens (partial output)
