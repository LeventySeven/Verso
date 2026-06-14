# verso/context/prune.py
from __future__ import annotations

from verso.model.base import Message

MASK = "[observation pruned to save context]"


def prune(history: list[Message], keep_last_n: int = 10) -> list[Message]:
    """Observation-masking: replace the CONTENT of tool-result messages older than the
    most recent `keep_last_n` tool results with a placeholder. Reasoning, user, and
    assistant turns are never touched, and message structure (ids/roles) is preserved.
    Idempotent: re-pruning already-masked messages is a no-op.
    `keep_last_n <= 0` masks ALL tool results (keep none); a negative value is treated as 0
    (avoids the `[:-0] == [:0] == []` slice gotcha that would otherwise mask nothing).

    Loop semantics (intentional, documented): the run loop calls prune as a SOFT, best-effort
    trigger when `max_context_tokens` is exceeded — it is not a hard cap. A single pass may not get
    under budget (the most-recent `keep_last_n` results are never masked, and user/assistant turns are
    never touched). And because the loop reassigns `bundle.history = prune(...)`, a budget-triggered
    prune is persisted to the per-step checkpoint, so a later durable `history()`/`fork()` sees the
    MASK placeholder, not the original tool output (durable history is lossy under budget pressure)."""
    tool_idxs = [i for i, m in enumerate(history) if m.role == "tool"]
    if keep_last_n <= 0:
        to_mask = set(tool_idxs)                      # keep none -> mask every tool result
    elif len(tool_idxs) <= keep_last_n:
        return list(history)
    else:
        to_mask = set(tool_idxs[:-keep_last_n])
    out: list[Message] = []
    for i, m in enumerate(history):
        if i in to_mask and m.content != MASK:
            out.append(Message(role="tool", content=MASK, tool_call_id=m.tool_call_id, name=m.name))
        else:
            out.append(m)
    return out
