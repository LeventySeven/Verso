# verso/memory/store.py
from __future__ import annotations
import time
import uuid
from typing import Callable

from verso.memory.backend import MemoryBackend
from verso.memory.embed import Embedder, HashEmbedder
from verso.memory.sqlite import SqliteBackend
from verso.memory.types import MemoryRecord, MemoryType


class Memory:
    """The one Memory object. ADD-only write model: `remember` stores; `supersede` invalidates
    the old + adds the new (never an in-place overwrite). Opt-in / durable-tier — attach to an
    Agent only for recurring-workflow agents; tactical one-shots run without it."""
    def __init__(self, backend: MemoryBackend, embedder: Embedder, *, scope: str = "default",
                 clock: Callable[[], float] = time.time):
        self.backend, self.embedder, self.scope, self.clock = backend, embedder, scope, clock

    @classmethod
    def sqlite(cls, path: str = ":memory:", *, scope: str = "default",
               clock: Callable[[], float] = time.time, max_records: int = 10_000) -> "Memory":
        emb = HashEmbedder()
        return cls(SqliteBackend(path, embedder=emb, max_records=max_records), emb, scope=scope, clock=clock)

    async def remember(self, content: str, *, type: MemoryType = MemoryType.EPISODIC,
                       importance: float = 0.5, outcome: str | None = None) -> str:
        rid = uuid.uuid4().hex
        self.backend.add(MemoryRecord(id=rid, type=type, content=content, scope=self.scope,
                                      importance=importance, outcome=outcome, valid_at=self.clock(),
                                      embedding=self.embedder.embed(content)))
        return rid

    async def supersede(self, old_id: str, content: str, *, type: MemoryType = MemoryType.FACT,
                        importance: float = 0.5) -> str:
        self.backend.invalidate(old_id, self.clock())
        return await self.remember(content, type=type, importance=importance)

    async def recall(self, query: str, *, types: list[MemoryType] | None = None, k: int = 10) -> list[MemoryRecord]:
        now = self.clock()
        return self.backend.search(query, embedding=self.embedder.embed(query), now=now,
                                   scope=self.scope, types=types, k=k)

    async def recall_as_of(self, query: str, *, as_of: float, k: int = 10) -> list[MemoryRecord]:
        return self.backend.search(query, embedding=self.embedder.embed(query), now=as_of,
                                   scope=self.scope, k=k, as_of=as_of)
