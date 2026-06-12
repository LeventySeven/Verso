# verso/memory/backend.py
from __future__ import annotations
from typing import Protocol, runtime_checkable

from verso.memory.types import MemoryRecord


@runtime_checkable
class MemoryBackend(Protocol):
    """The durable contract. sqlite (dev) / pgvector / Mem0 implement this; products never see it."""
    def add(self, record: MemoryRecord) -> None: ...
    def search(self, query: str, *, embedding: list[float], now: float,
               scope: str = "default", types: list | None = None, k: int = 10,
               as_of: float | None = None) -> list[MemoryRecord]: ...
    def invalidate(self, id: str, at: float) -> None: ...
    def count(self) -> int: ...
