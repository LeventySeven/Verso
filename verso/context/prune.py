# verso/context/prune.py
from __future__ import annotations

from verso.model.base import Message

MASK = "[observation pruned to save context]"


def prune(history: list[Message], keep_last_n: int = 10) -> list[Message]:
    """Observation-masking: replace the CONTENT of tool-result messages older than the
    most recent `keep_last_n` tool results with a placeholder. Reasoning, user, and
    assistant turns are never touched, and message structure (ids/roles) is preserved.
    Idempotent: re-pruning already-masked messages is a no-op."""
    tool_idxs = [i for i, m in enumerate(history) if m.role == "tool"]
    if len(tool_idxs) <= keep_last_n:
        return list(history)
    to_mask = set(tool_idxs[:-keep_last_n])
    out: list[Message] = []
    for i, m in enumerate(history):
        if i in to_mask and m.content != MASK:
            out.append(Message(role="tool", content=MASK, tool_call_id=m.tool_call_id, name=m.name))
        else:
            out.append(m)
    return out
