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


def _turn_keys(history: list[Message]) -> list[tuple[str, str]]:
    """For each assistant tool-calling turn, a (action_sig, result_sig) pair, where result_sig is the
    concatenated contents of the tool results matching that turn's tool_call ids (in id order; "" if a
    result isn't present yet). Comparing BOTH halves is what separates a doom-loop (same call, same
    result) from legitimate polling (same call, CHANGING result → progress, not stuck)."""
    n = len(history)
    keys: list[tuple[str, str]] = []
    for i, m in enumerate(history):
        sig = _sig(m)
        if sig is None:
            continue
        ids = [tc.id for tc in m.tool_calls]
        resmap: dict[str, str] = {}
        for j in range(i + 1, n):
            mj = history[j]
            if mj.role == "tool" and mj.tool_call_id in ids and mj.tool_call_id not in resmap:
                resmap[mj.tool_call_id] = mj.content or ""
        keys.append((sig, "|".join(resmap.get(tid, "") for tid in ids)))
    return keys


def detect_stuck(history: list[Message], thresholds: StuckThresholds) -> str | None:
    """Return a short reason string if the trajectory is in a doom-loop, else None. Pure + read-only;
    cheap enough to call once per step. Two patterns (both real, both reachable in the ReAct loop):
      (a) the same tool call AND the same result repeated `repeated_action` times in a row — genuine
          non-progress (polling with a CHANGING result is NOT stuck, by design);
      (b) `tool_errors` consecutive tool results that are errors (error spiral)."""
    keys = _turn_keys(history)
    if len(keys) >= thresholds.repeated_action and len(set(keys[-thresholds.repeated_action:])) == 1:
        return f"repeated the same tool call with the same result {thresholds.repeated_action}x (no progress)"
    tool_msgs = [m for m in history if m.role == "tool"]
    if len(tool_msgs) >= thresholds.tool_errors and all(
        (m.content or "").startswith("Error:") for m in tool_msgs[-thresholds.tool_errors:]
    ):
        return f"{thresholds.tool_errors} consecutive tool errors"
    return None
