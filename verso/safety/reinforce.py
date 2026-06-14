# verso/safety/reinforce.py
from __future__ import annotations


def reinforce_objective(summary: str, *, every: int = 1):
    """A post_tool hook factory: re-anchor the agent to its objective by appending a compact
    task-summary line to tool results, on every `every`-th tool return. Plug into
    Hooks(post_tool=[reinforce_objective("ship the refund")]). Opt-in; no loop change."""
    if every < 1:
        raise ValueError("every must be >= 1")
    state = {"n": 0}

    def hook(call, content):
        state["n"] += 1
        if state["n"] % every == 0:
            return f"{content}\n[objective: {summary}]"
        return content

    return hook
