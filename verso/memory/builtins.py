# verso/memory/builtins.py
from __future__ import annotations

from verso.memory.store import Memory
from verso.memory.types import MemoryType
from verso.tools.tool import tool, Tool


def memory_tools(memory: Memory) -> list[Tool]:
    """Return `remember`/`recall` as @tools bound to `memory`. The agent manages its own memory
    observably (every call is a visible tool event); writes are ADD-only (never silent overwrite)."""

    @tool
    async def remember(content: str) -> str:
        "Store a durable fact, preference, or note so it can be recalled in future turns."
        await memory.remember(content, type=MemoryType.FACT, importance=0.7)
        return "remembered"

    @tool
    async def recall(query: str) -> list[str]:
        "Recall stored facts/preferences/notes relevant to a query."
        return [h.content for h in await memory.recall(query, k=5)]

    return [remember, recall]
