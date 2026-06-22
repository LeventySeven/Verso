# verso/core/stuck.py
from __future__ import annotations
import json
from dataclasses import dataclass

from verso.model.base import Message


@dataclass(frozen=True)
class StuckThresholds:
    """Doom-loop detection thresholds — conservative by design (fire only on a clear non-progress
    pattern). Defaults sit ABOVE the small `max_steps` caps used in unit tests, so a short legitimate
    run never trips them while a real doom-loop (`max_steps=25`) is caught early. Pass
    `stuck_thresholds=None` to the loop to disable detection entirely (byte-identical to no detector)."""
    repeated_action: int = 4   # N consecutive assistant turns with the SAME (tool, args) signature
    tool_errors: int = 4       # N consecutive tool observations whose content is an error


def _sig(m: Message) -> str | None:
    """A stable signature of an assistant turn's tool calls (sorted name+args), or None if `m` is not a
    tool-calling assistant turn. Two turns with the same signature are the same action."""
    if m.role != "assistant" or not m.tool_calls:
        return None
    return json.dumps(
        sorted((tc.name, json.dumps(tc.arguments, sort_keys=True, default=str)) for tc in m.tool_calls),
        sort_keys=True,
    )


def detect_stuck(history: list[Message], thresholds: StuckThresholds) -> str | None:
    """Return a short reason string if the trajectory is in a doom-loop, else None. Pure + read-only;
    cheap enough to call once per step. Two patterns (both real, both reachable in the ReAct loop):
      (a) the same tool-call signature repeated `repeated_action` times in a row (no progress);
      (b) `tool_errors` consecutive tool results that are errors (error spiral)."""
    sigs = [s for s in (_sig(m) for m in history) if s is not None]
    if len(sigs) >= thresholds.repeated_action and len(set(sigs[-thresholds.repeated_action:])) == 1:
        return f"repeated the same tool call {thresholds.repeated_action}x with no new result"
    tool_msgs = [m for m in history if m.role == "tool"]
    if len(tool_msgs) >= thresholds.tool_errors and all(
        (m.content or "").startswith("Error:") for m in tool_msgs[-thresholds.tool_errors:]
    ):
        return f"{thresholds.tool_errors} consecutive tool errors"
    return None
