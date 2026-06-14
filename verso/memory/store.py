# verso/memory/store.py
from __future__ import annotations
import inspect
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

    async def reflect(self, reflector: Callable[[list[str]], object], *, trigger_n: int = 100,
                      target_type: MemoryType = MemoryType.FACT, importance: float = 0.8,
                      limit: int = 1000) -> list[str]:
        """Consolidate accumulated episodic memories into durable FACT/PROCEDURAL knowledge — the step
        that makes memory compound (§5.4). Gather live episodics, hand their contents to `reflector`
        (an LLM or a deterministic fn → derived statements), store each as a `target_type` memory, and
        invalidate the consolidated sources (ADD-only: never deleted). A no-op until `trigger_n`
        episodics have accumulated (pass trigger_n=0 to force). `reflector` may be sync or async."""
        # thread the store clock into recent() so reflect()'s notion of "live" matches recall()/search():
        # an episodic past its TTL is dropped here and never consolidated into a fresh permanent FACT.
        episodics = self.backend.recent(scope=self.scope, types=[MemoryType.EPISODIC], limit=limit,
                                        now=self.clock())
        if not episodics or len(episodics) < trigger_n:
            return []
        out = reflector([r.content for r in episodics])
        derived = await out if inspect.isawaitable(out) else out
        if isinstance(derived, str):           # a reflector that returns one string → one memory, not per-char
            derived = [derived]
        ids = [await self.remember(d, type=target_type, importance=importance) for d in derived]
        at = self.clock()
        for r in episodics:
            self.backend.invalidate(r.id, at)              # sources consolidated → invalidated, never deleted
        return ids


async def load_skills(memory: Memory, *, scope: str | None = None,
                      types: tuple[MemoryType, ...] = (MemoryType.PROCEDURAL, MemoryType.FACT),
                      limit: int = 20, header: str = "Learned context (from memory):") -> str:
    """Turn consolidated permanent memory into an instruction prefix — the bridge between `reflect()`
    (which keeps consolidating durable records) and the static `instructions` string (which otherwise
    never evolves between runs). Pure read + format: pulls the most-recent live records of `types`
    (PROCEDURAL/FACT, the permanent tiers) for `scope` and renders them as a compact bullet prefix
    so `instructions = base + await load_skills(mem, scope=...)` carries what the agent has learned.

    Returns ``""`` when there's nothing to inject, so `base + load_skills(...)` is byte-identical to
    `base` on an empty memory. No new memory state, no loop change."""
    records = memory.backend.recent(scope=memory.scope if scope is None else scope,
                                    types=list(types), limit=limit, now=memory.clock())
    if not records:
        return ""
    bullets = "\n".join(f"- {r.content}" for r in records)
    return f"{header}\n{bullets}"
