# Verso Phase 1 — Plan 7: Memory

> **✅ SHIPPED** — implemented test-first, independently rechecked-APPROVED, on `main`.

> **Phase-1 plan set:** Plan 6 (evals) → **Plan 7 — memory (this doc)** → Plan 8 (safety/hooks). Independent of Plan 6; can be built in parallel. Implement task-by-task with `compound-v:batched-implementation` (TDD: failing test → run → minimal code → run → commit). Never edit a test to make it pass.

**Goal:** ship Memory as a real primitive (not a Redis adapter): **one `Memory` object** over a **swappable backend**, the 4-tier typed schema (`scratchpad/episodic/fact/procedural`), `remember`/`recall`/`recall_as_of` (ADD-only, one write model), **RRF-fused retrieval** (lexical + vector + exact), temporal versioning, write-time **importance** + **outcome-status**, **bounded by default**. LOCK the types + `MemoryBackend` interface + DDL now; SHIP a **zero-infra stdlib-SQLite** backend. Memory is **opt-in / durable-tier** — OFF for tactical one-shots (§14.7).

**Done (machine-checkable):** `uv run pytest -q` green + `uv run ruff check verso tests` clean — proving: a `Memory` over `SqliteBackend` stores typed records; `recall(query, ...)` returns RRF-fused results that rank an exact lexical hit above a noise record; `recall_as_of(date)` excludes facts invalidated after that date; importance + outcome-status affect ranking (successes down-weighted); the store is bounded (oldest evicted past the cap). **No new required dependency** (stdlib `sqlite3`; the embedder is pluggable with a deterministic dev default; real embedders/Mem0/pgvector are optional swaps).

**Approach / key facts (research fold-in):**
- Phase-0 patterns to follow: small single-responsibility files, `from __future__ import annotations`, dataclasses, async where the loop touches it (`Memory.remember/recall` are async to match the tool path), `FakeModel`-style deterministic test doubles, commit-after-green. Memory is a **new module**; nothing in `verso/` references it yet.
- **Simplicity deviations from §13's literal wording (no-overkill, flagged for the recheck):**
  1. §13 says "SqliteVecBackend"; we ship **`SqliteBackend`** on **stdlib `sqlite3`** — FTS5 for lexical (BM25), **brute-force cosine** for vector, SQL `WHERE` for exact — and **RRF** to fuse. At personal-infra scale brute-force vector is correct; `sqlite-vec` is a drop-in *index* optimization deferred until a dogfood corpus is large enough to feel it. Zero extra dependency, fully testable offline.
  2. §13 says "SHIP `SqliteVecBackend` + a `Mem0Backend` adapter" — the point being to **prove the `MemoryBackend` pluggable edge is real, not asserted** (a one-implementation interface proves nothing). We honor that by shipping **two** backends in Phase 1: `SqliteBackend` (the persistent dev default) **and** `InMemoryBackend` (a dict-based, dependency-free, zero-persistence backend — the right choice for ephemeral/tactical agents and the cleanest proof that the interface swaps). The `Mem0Backend` adapter is **interface-ready and deferred-by-honesty only**: writing an adapter to `mem0ai` now means *guessing* an SDK API I cannot verify (against the no-bullshit / no-guessing-SDK-usage rule) — it lands, against the same interface, the moment `mem0ai` is actually added (verify its `add/search/get_all` signatures first). The edge itself is proven *now*.
- **Embeddings:** a pluggable `Embedder` protocol with a deterministic **`HashEmbedder`** dev default (char-trigram hashing → fixed-dim L2-normalized vector — deterministic, offline, good enough that identical/near text scores high; real semantic embedders, e.g. an API or local model, swap in). The **lexical (FTS5) arm carries real retrieval quality**; the vector arm + RRF give the interface its shape and improve with a real embedder.
- **Composite ranking (§5.4 + §14.7):** final score blends `RRF(lexical, vector)` with `recency_decay` and stored `importance`, and **down-weights `outcome="success"`** records (successes breed lazy pattern-matching; failures reliably help — Huber). `importance` and `outcome` are written **once, at store time** — never re-scored on the hot path (read).

**Divergence rule:** if FTS5 is unavailable in the runner's `sqlite3` build, **stop and report** (don't silently drop the lexical arm) — the fix is a build note, not a redesign. After ~3 failed attempts at any single mechanism, surface it.

**User Review Required:** none. New `verso/memory/` module + tests only; **no** change to `core/loop.py` or the `Agent` run path (Memory is opt-in, attached explicitly). The SQLite file is created under a caller-supplied path (default `:memory:` in tests); no destructive ops on existing data.

**Out of scope (deferred — lock the seam, build nothing):** the `procedural` tier population + `reflect(trigger_n≈100)` episodic→semantic consolidation; `pgvector`/graph backends; the Mem0/Zep adapters; bi-temporal confidence-decay constants; `sqlite-vec` index; the `AGENTS.md` project-context-file loader (it's a §5.4 static-memory convenience — a small follow-up, not the primitive). Note each; ship none.

**Tech stack:** stdlib `sqlite3` (FTS5), Pydantic v2 optional. No new required deps. Optional extras (later): `verso[memory]` for `sqlite-vec`/`mem0ai`/`pgvector`.

---

## File structure

```
verso/
└── memory/
    ├── __init__.py     # NEW — exports Memory, MemoryRecord, MemoryType, MemoryBackend, SqliteBackend, Embedder, HashEmbedder
    ├── types.py        # NEW — MemoryType enum, MemoryRecord dataclass, the DDL string (the locked schema)
    ├── embed.py        # NEW — Embedder protocol + HashEmbedder (deterministic dev default) + cosine
    ├── backend.py      # NEW — MemoryBackend protocol (add / search / invalidate / count)
    ├── sqlite.py       # NEW — SqliteBackend (FTS5 lexical + brute-force vector + filter + RRF fuse + bound)
    ├── inmem.py        # NEW — InMemoryBackend (dict-based, dependency-free — proves the pluggable edge)
    ├── builtins.py     # NEW — memory_tools(memory) → bound `remember`/`recall` @tools (memory-as-tool-calls)
    └── store.py        # NEW — Memory (the one object): remember / recall / recall_as_of over a backend
tests/
├── test_memory_embed.py     # NEW
├── test_memory_backends.py  # NEW — the MemoryBackend contract, run against BOTH backends (the edge proof)
├── test_memory_store.py     # NEW
└── test_memory_tools.py     # NEW — the agent manages its own memory via @tools, observably
verso/__init__.py            # MODIFY — export the memory surface
README.md                    # MODIFY — append a memory snippet
```

---

## Task 1: Types + DDL (the locked schema) + Embedder

**Files:** Create `verso/memory/__init__.py` (empty), `verso/memory/types.py`, `verso/memory/embed.py`; Test `tests/test_memory_embed.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_memory_embed.py
from verso.memory.embed import HashEmbedder, cosine


def test_embed_is_deterministic_and_normalized():
    e = HashEmbedder(dim=64)
    v1, v2 = e.embed("the cat sat"), e.embed("the cat sat")
    assert v1 == v2                                   # deterministic
    assert abs(sum(x * x for x in v1) - 1.0) < 1e-6   # L2-normalized


def test_similar_text_scores_higher_than_unrelated():
    e = HashEmbedder(dim=128)
    base = e.embed("database connection pooling")
    near = e.embed("database connection pool")
    far = e.embed("strawberry cake recipe")
    assert cosine(base, near) > cosine(base, far)
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement `verso/memory/types.py`:**

```python
# verso/memory/types.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class MemoryType(str, Enum):
    SCRATCHPAD = "scratchpad"   # TTL ~1h
    EPISODIC = "episodic"       # TTL ~7d
    FACT = "fact"               # permanent
    PROCEDURAL = "procedural"   # permanent (reserved; populated in a later plan)


# Per-type default TTL in seconds (None = permanent). Enforced by the backend.
TTL_SECONDS: dict[MemoryType, int | None] = {
    MemoryType.SCRATCHPAD: 3600,
    MemoryType.EPISODIC: 7 * 86400,
    MemoryType.FACT: None,
    MemoryType.PROCEDURAL: None,
}


@dataclass
class MemoryRecord:
    id: str
    type: MemoryType
    content: str
    scope: str = "default"              # user_id / agent_id / run_id, joined — auto-injected by Memory
    importance: float = 0.5             # written ONCE at store time, never re-scored on read
    outcome: str | None = None          # "success" | "failure" | None — success is down-weighted on recall
    valid_at: float = 0.0               # store time (epoch seconds; injected, not wall-clock-at-read)
    invalid_at: float | None = None     # set on supersession; record is never deleted, only invalidated
    embedding: list[float] = field(default_factory=list)


# The locked DDL — the durable contract. Backends implement this shape (sqlite here; pgvector later).
DDL = """
CREATE TABLE IF NOT EXISTS memory (
  id TEXT PRIMARY KEY, type TEXT NOT NULL, content TEXT NOT NULL, scope TEXT NOT NULL,
  importance REAL NOT NULL, outcome TEXT, valid_at REAL NOT NULL, invalid_at REAL, embedding TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(content, content='memory', content_rowid='rowid');
CREATE INDEX IF NOT EXISTS memory_scope ON memory(scope, type);
"""
```

- [ ] **Step 4 — implement `verso/memory/embed.py`:**

```python
# verso/memory/embed.py
from __future__ import annotations
import hashlib
import math
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    dim: int
    def embed(self, text: str) -> list[float]: ...


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))          # inputs are L2-normalized → dot == cosine


class HashEmbedder:
    """Deterministic, offline dev embedder: hash char-trigrams into a fixed-dim bag, L2-normalize.
    Good enough that near-identical text scores high; swap a real semantic embedder for production
    (the Embedder protocol is the seam). The FTS5 lexical arm carries real retrieval quality."""
    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        t = f"  {text.lower().strip()}  "
        for i in range(len(t) - 2):
            h = int(hashlib.blake2b(t[i:i+3].encode(), digest_size=8).hexdigest(), 16)
            v[h % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]
```

- [ ] **Step 5 — run, expect 2 passed; commit:** `git commit -am "feat(memory): MemoryType/MemoryRecord/DDL (locked schema) + pluggable HashEmbedder"`

---

## Task 2: `SqliteBackend` — FTS5 + brute-force vector + RRF + temporal + bound

**Files:** Create `verso/memory/backend.py`, `verso/memory/sqlite.py`; Test `tests/test_memory_sqlite.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_memory_sqlite.py
from verso.memory.sqlite import SqliteBackend
from verso.memory.embed import HashEmbedder
from verso.memory.types import MemoryRecord, MemoryType


def _rec(id, content, **kw):
    e = HashEmbedder(dim=128)
    return MemoryRecord(id=id, type=kw.get("type", MemoryType.FACT), content=content,
                        importance=kw.get("importance", 0.5), outcome=kw.get("outcome"),
                        valid_at=kw.get("valid_at", 100.0), invalid_at=kw.get("invalid_at"),
                        embedding=e.embed(content))


def _backend(cap=100):
    return SqliteBackend(path=":memory:", embedder=HashEmbedder(dim=128), max_records=cap)


def test_rrf_ranks_exact_lexical_hit_above_noise():
    b = _backend()
    b.add(_rec("a", "postgres connection pooling with pgbouncer"))
    b.add(_rec("b", "strawberry shortcake with whipped cream"))
    hits = b.search("postgres connection pooling", embedding=HashEmbedder(128).embed("postgres connection pooling"), now=200.0)
    assert hits[0].id == "a"


def test_recall_as_of_excludes_facts_invalidated_after_the_date():
    b = _backend()
    b.add(_rec("old", "the capital is X", valid_at=100.0, invalid_at=150.0))   # invalidated at t=150
    hits_before = b.search("capital", embedding=HashEmbedder(128).embed("capital"), now=120.0, as_of=120.0)
    hits_after = b.search("capital", embedding=HashEmbedder(128).embed("capital"), now=200.0, as_of=200.0)
    assert any(h.id == "old" for h in hits_before)      # valid at t=120
    assert not any(h.id == "old" for h in hits_after)   # invalid by t=200


def test_success_outcome_is_downweighted_vs_failure():
    b = _backend()
    b.add(_rec("succ", "deploy step ran", outcome="success"))
    b.add(_rec("fail", "deploy step ran", outcome="failure"))   # identical content
    hits = b.search("deploy step", embedding=HashEmbedder(128).embed("deploy step"), now=200.0)
    assert hits[0].id == "fail"                          # failures rank above successes


def test_bounded_evicts_oldest_past_cap():
    b = _backend(cap=3)
    for i in range(5):
        b.add(_rec(f"r{i}", f"record number {i}", valid_at=float(i)))
    assert b.count() == 3                                # bounded by default
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement `verso/memory/backend.py`:**

```python
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
```

- [ ] **Step 4 — implement `verso/memory/sqlite.py`** (FTS5 lexical + brute-force vector → RRF fuse, blended with recency + importance, success down-weighted; temporal `as_of`; bound via oldest-`valid_at` eviction):

```python
# verso/memory/sqlite.py
from __future__ import annotations
import json
import math
import sqlite3

from verso.memory.types import MemoryRecord, MemoryType, TTL_SECONDS, DDL
from verso.memory.embed import Embedder, cosine

RRF_K = 60


class SqliteBackend:
    def __init__(self, path: str = ":memory:", *, embedder: Embedder, max_records: int = 10_000):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.embedder = embedder
        self.max_records = max_records
        self.db.executescript(DDL)

    def add(self, r: MemoryRecord) -> None:
        cur = self.db.execute(
            "INSERT OR REPLACE INTO memory(id,type,content,scope,importance,outcome,valid_at,invalid_at,embedding)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (r.id, r.type.value, r.content, r.scope, r.importance, r.outcome, r.valid_at, r.invalid_at,
             json.dumps(r.embedding)))
        self.db.execute("INSERT INTO memory_fts(rowid, content) VALUES(?, ?)", (cur.lastrowid, r.content))
        self.db.commit()
        self._enforce_bound()

    def _enforce_bound(self) -> None:
        n = self.count()
        if n > self.max_records:
            self.db.execute(
                "DELETE FROM memory WHERE id IN (SELECT id FROM memory ORDER BY valid_at ASC LIMIT ?)",
                (n - self.max_records,))
            self.db.commit()

    def invalidate(self, id: str, at: float) -> None:
        self.db.execute("UPDATE memory SET invalid_at=? WHERE id=?", (at, id))   # never deleted
        self.db.commit()

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) c FROM memory").fetchone()["c"]

    def search(self, query, *, embedding, now, scope="default", types=None, k=10, as_of=None):
        as_of = now if as_of is None else as_of
        rows = [dict(r) for r in self.db.execute("SELECT rowid,* FROM memory WHERE scope=?", (scope,))]
        # temporal + TTL validity at `as_of`
        live = []
        for row in rows:
            if types and row["type"] not in {t.value for t in types}:
                continue
            if row["invalid_at"] is not None and row["invalid_at"] <= as_of:
                continue
            ttl = TTL_SECONDS[MemoryType(row["type"])]
            if ttl is not None and as_of - row["valid_at"] > ttl:
                continue
            live.append(row)
        if not live:
            return []
        # lexical rank (FTS5 bm25) and vector rank (brute-force cosine) → RRF fuse
        lex_ids = [r["rowid"] for r in self.db.execute(
            "SELECT rowid FROM memory_fts WHERE memory_fts MATCH ? ORDER BY bm25(memory_fts)",
            (_fts_query(query),))]
        lex_rank = {rid: i for i, rid in enumerate(lex_ids)}
        vec_order = sorted(live, key=lambda r: cosine(embedding, json.loads(r["embedding"])), reverse=True)
        vec_rank = {r["rowid"]: i for i, r in enumerate(vec_order)}

        def fused(r):
            rrf = 1.0 / (RRF_K + lex_rank.get(r["rowid"], 10_000)) + 1.0 / (RRF_K + vec_rank.get(r["rowid"], 10_000))
            recency = math.exp(-(now - r["valid_at"]) / (30 * 86400))     # 30d decay
            penalty = 0.5 if r["outcome"] == "success" else 1.0           # down-weight successes
            return (0.5 * rrf + 0.3 * recency + 0.2 * r["importance"]) * penalty

        ranked = sorted(live, key=fused, reverse=True)[:k]
        return [_to_record(r) for r in ranked]


def _fts_query(q: str) -> str:
    terms = [t for t in "".join(c if c.isalnum() else " " for c in q).split() if t]
    return " OR ".join(terms) or '""'


def _to_record(row) -> MemoryRecord:
    return MemoryRecord(id=row["id"], type=MemoryType(row["type"]), content=row["content"], scope=row["scope"],
                        importance=row["importance"], outcome=row["outcome"], valid_at=row["valid_at"],
                        invalid_at=row["invalid_at"], embedding=json.loads(row["embedding"]))
```

- [ ] **Step 5 — run, expect 4 passed.** (If `bm25(memory_fts)` errors, the runner's SQLite lacks FTS5 with bm25 — per the divergence rule, stop and report; do not silently fall back.)
- [ ] **Step 6 — commit:** `git commit -am "feat(memory): SqliteBackend — FTS5+vector RRF fuse, temporal recall_as_of, success-downweight, bounded"`

---

## Task 3: `Memory` — remember / recall / recall_as_of (one write model, ADD-only) + exports

**Files:** Create `verso/memory/store.py`; Modify `verso/memory/__init__.py`, `verso/__init__.py`, `README.md`; Test `tests/test_memory_store.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_memory_store.py
from verso.memory.store import Memory
from verso.memory.types import MemoryType


def _mem():
    return Memory.sqlite(path=":memory:", scope="user-1", clock=lambda: 1000.0)


async def test_remember_then_recall_roundtrip_with_scope_injected():
    m = _mem()
    await m.remember("postgres pooling uses pgbouncer", type=MemoryType.FACT, importance=0.9)
    hits = await m.recall("postgres pooling")
    assert hits and "pgbouncer" in hits[0].content
    assert hits[0].scope == "user-1"                    # scope auto-injected


async def test_remember_is_additive_supersede_invalidates_not_deletes():
    m = _mem()
    rid = await m.remember("the value is 1", type=MemoryType.FACT)
    await m.supersede(rid, "the value is 2", type=MemoryType.FACT)
    now_hits = await m.recall("value")
    assert any("2" in h.content for h in now_hits)
    assert not any("the value is 1" == h.content for h in now_hits)   # old invalidated, not returned now
    # but recall_as_of before the supersession still sees the old fact:
    past = await m.recall_as_of("value", as_of=1000.0)
    assert any("the value is 1" == h.content for h in past)
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement `verso/memory/store.py`:**

```python
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
    """The one Memory object (three faces: short-term/long-term/compaction policy live here).
    ADD-only write model: `remember` stores; `supersede` invalidates the old + adds the new
    (never an in-place overwrite). Memory is opt-in / durable-tier — attach it to an Agent only
    for recurring-workflow agents; tactical one-shots run without it (§14.7)."""
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
```

- [ ] **Step 4 — write `verso/memory/__init__.py`** (export `Memory, MemoryRecord, MemoryType, MemoryBackend, SqliteBackend, Embedder, HashEmbedder`) and **add `from verso.memory import Memory, MemoryType` to `verso/__init__.py`** imports + `__all__`.

- [ ] **Step 5 — run the full suite + lint:** `uv run pytest -q` → all green; `uv run ruff check verso tests` → clean.

- [ ] **Step 6 — README: append before `## Status`:**

````markdown
**Memory — typed, temporal, RRF-retrieved** (opt-in; for recurring-workflow agents):

```python
from verso import Memory, MemoryType

mem = Memory.sqlite("agent.db", scope="user-1")
await mem.remember("prefers metric units", type=MemoryType.FACT, importance=0.9)
hits = await mem.recall("units")                       # RRF: lexical + vector + recency + importance
past = await mem.recall_as_of("units", as_of=ts)       # what the agent knew at decision time
```

One store, swappable backend (stdlib SQLite dev default → pgvector/Mem0 later); ADD-only, never deletes (supersede invalidates); bounded by default.
````

- [ ] **Step 7 — commit:** `git commit -am "feat(memory): Memory (remember/recall/recall_as_of, ADD-only) + exports + README"`

---

## Task 4: `InMemoryBackend` + the cross-backend contract (prove the pluggable edge)

A second backend proves `MemoryBackend` is a real swappable edge — and a dict-based, zero-persistence backend is the right store for ephemeral/tactical agents (no SQLite file).

**Files:** Create `verso/memory/inmem.py`; Test `tests/test_memory_backends.py`.

- [ ] **Step 1 — failing test (the same contract, run against BOTH backends):**

```python
# tests/test_memory_backends.py
import pytest
from verso.memory.sqlite import SqliteBackend
from verso.memory.inmem import InMemoryBackend
from verso.memory.embed import HashEmbedder
from verso.memory.types import MemoryRecord, MemoryType


def _rec(id, content, **kw):
    return MemoryRecord(id=id, type=kw.get("type", MemoryType.FACT), content=content,
                        importance=kw.get("importance", 0.5), outcome=kw.get("outcome"),
                        valid_at=kw.get("valid_at", 100.0), invalid_at=kw.get("invalid_at"),
                        embedding=HashEmbedder(128).embed(content))


@pytest.fixture(params=["sqlite", "inmem"])
def backend(request):
    emb = HashEmbedder(128)
    return SqliteBackend(":memory:", embedder=emb, max_records=3) if request.param == "sqlite" \
        else InMemoryBackend(embedder=emb, max_records=3)


def test_contract_recall_ranks_relevant_first(backend):
    backend.add(_rec("a", "postgres connection pooling with pgbouncer"))
    backend.add(_rec("b", "strawberry shortcake recipe"))
    hits = backend.search("postgres pooling", embedding=HashEmbedder(128).embed("postgres pooling"), now=200.0)
    assert hits[0].id == "a"


def test_contract_recall_as_of_and_bound(backend):
    backend.add(_rec("old", "value is X", valid_at=100.0, invalid_at=150.0))
    assert any(h.id == "old" for h in backend.search("value", embedding=HashEmbedder(128).embed("value"), now=120.0, as_of=120.0))
    assert not any(h.id == "old" for h in backend.search("value", embedding=HashEmbedder(128).embed("value"), now=200.0, as_of=200.0))
    for i in range(5):
        backend.add(_rec(f"r{i}", f"row {i}", valid_at=float(i)))
    assert backend.count() <= 3                     # both backends honor the bound
```

- [ ] **Step 2 — run, expect FAIL** (the `inmem` params fail).
- [ ] **Step 3 — implement `verso/memory/inmem.py`** (same `MemoryBackend` contract; a deliberately separate, simpler implementation — at 2 backends, a little duplication is honest, not worth a shared-ranking abstraction):

```python
# verso/memory/inmem.py
from __future__ import annotations
import math

from verso.memory.types import MemoryRecord, MemoryType, TTL_SECONDS
from verso.memory.embed import Embedder, cosine

RRF_K = 60


class InMemoryBackend:
    """Dict/list-based MemoryBackend — dependency-free, zero-persistence. For ephemeral/tactical
    agents and as the proof that the MemoryBackend edge swaps. Same semantics as SqliteBackend
    (RRF over lexical-overlap + vector; temporal/TTL filter; success down-weight; bound)."""
    def __init__(self, *, embedder: Embedder, max_records: int = 10_000):
        self.embedder, self.max_records = embedder, max_records
        self._recs: list[MemoryRecord] = []

    def add(self, r: MemoryRecord) -> None:
        self._recs = [x for x in self._recs if x.id != r.id] + [r]
        if len(self._recs) > self.max_records:
            self._recs.sort(key=lambda x: x.valid_at)
            self._recs = self._recs[-self.max_records:]

    def invalidate(self, id: str, at: float) -> None:
        for r in self._recs:
            if r.id == id:
                r.invalid_at = at

    def count(self) -> int:
        return len(self._recs)

    def search(self, query, *, embedding, now, scope="default", types=None, k=10, as_of=None):
        as_of = now if as_of is None else as_of
        q_terms = set(_terms(query))
        live = []
        for r in self._recs:
            if r.scope != scope:
                continue
            if types and r.type not in types:
                continue
            if r.invalid_at is not None and r.invalid_at <= as_of:
                continue
            ttl = TTL_SECONDS[r.type]
            if ttl is not None and as_of - r.valid_at > ttl:
                continue
            live.append(r)
        if not live:
            return []
        lex = sorted(live, key=lambda r: len(q_terms & set(_terms(r.content))), reverse=True)
        lex_rank = {r.id: i for i, r in enumerate(lex)}
        vec = sorted(live, key=lambda r: cosine(embedding, r.embedding), reverse=True)
        vec_rank = {r.id: i for i, r in enumerate(vec)}

        def fused(r: MemoryRecord) -> float:
            rrf = 1.0 / (RRF_K + lex_rank[r.id]) + 1.0 / (RRF_K + vec_rank[r.id])
            recency = math.exp(-(now - r.valid_at) / (30 * 86400))
            penalty = 0.5 if r.outcome == "success" else 1.0
            return (0.5 * rrf + 0.3 * recency + 0.2 * r.importance) * penalty

        return sorted(live, key=fused, reverse=True)[:k]


def _terms(s: str) -> list[str]:
    return ["".join(c for c in t if c.isalnum()) for t in s.lower().split() if t]
```

- [ ] **Step 4 — run, expect both params green; commit:** `git commit -am "feat(memory): InMemoryBackend — dependency-free 2nd backend; cross-backend contract proves the edge"`

---

## Task 5: memory-as-tool-calls — the LLM manages its own memory, observably (§5.4 headline)

**Files:** Create `verso/memory/builtins.py`; Modify `verso/memory/__init__.py`; Test `tests/test_memory_tools.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_memory_tools.py
from verso import Agent
from verso.memory.store import Memory
from verso.memory.builtins import memory_tools
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


async def test_agent_remembers_then_recalls_via_tools():
    mem = Memory.sqlite(":memory:", scope="u1", clock=lambda: 1000.0)
    remember, recall = memory_tools(mem)
    # turn 1: remember; turn 2: recall; turn 3: final answer
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="remember", arguments={"content": "user prefers metric units"})], usage=Usage()),
        ModelResponse(text="", tool_calls=[ToolCall(id="t2", name="recall", arguments={"query": "units"})], usage=Usage()),
        ModelResponse(text="noted: metric", tool_calls=[], usage=Usage()),
    ])
    result = await Agent(model=fm, tools=[remember, recall]).run("remember my unit preference, then recall it")
    assert result.output == "noted: metric"
    # the write is observable + durable: a fresh recall sees it
    hits = await mem.recall("units")
    assert any("metric" in h.content for h in hits)
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement `verso/memory/builtins.py`** (bind a `Memory` into `@tool`s the model can call — ADD-only; the calls show up in the stream/span, so memory management is *observable*):

```python
# verso/memory/builtins.py
from __future__ import annotations

from verso.memory.store import Memory
from verso.memory.types import MemoryType
from verso.tools.tool import tool, Tool


def memory_tools(memory: Memory) -> list[Tool]:
    """Return `remember`/`recall` as @tools bound to `memory`. The agent manages its own memory
    observably (every call is a visible tool event); writes are ADD-only (never silent overwrite).
    (RunContext-injected memory replaces the closure binding when the typed `ctx` lands in Phase 2.)"""

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
```

- [ ] **Step 4 — export `memory_tools` from `verso/memory/__init__.py`** (and add to `verso/__init__.py` if exposing at top level). If the `@tool` decorator rejects a closure-defined async function (confirm in `verso/tools/tool.py`), report per the divergence rule — do not work around it with a different tool mechanism.
- [ ] **Step 5 — run + lint; commit:** `uv run pytest -q && uv run ruff check verso tests`; `git commit -am "feat(memory): memory-as-tool-calls (remember/recall @tools) — observable, ADD-only"`

---

## Verification plan

**Automated:** `uv run pytest -q && uv run ruff check verso tests` → all green (live test skipped). Criterion is **tests pass AND no assertion weakened / no expected output hardcoded** — a temporal/ranking test made green by loosening the assertion is a failure.

**Manual:** create a `Memory.sqlite("scratch.db")`, `remember` 3–4 records of varying `importance`/`outcome`, `recall` a query, and eyeball that the ranking is sane (exact lexical hit on top, successes below failures). Confirm the suite runs with **no** non-stdlib import (no `sqlite-vec`, no `mem0ai`).

## Done criteria (Plan 7)
- `Memory.sqlite(...)` stores typed records with auto-injected scope; `recall` returns RRF-fused (lexical+vector) results blended with recency + importance, successes down-weighted.
- `recall_as_of(date)` is temporally correct (excludes facts invalidated by that date; respects per-type TTL).
- Writes are ADD-only; `supersede` invalidates (never deletes); the store is bounded (oldest-`valid_at` evicted past the cap).
- Importance + outcome are written once at store time, never re-scored on read (no hot-path LLM call).
- **The pluggable edge is proven, not asserted:** the same `MemoryBackend` contract test passes against **both** `SqliteBackend` and `InMemoryBackend`; `memory_tools()` lets the agent manage its own memory observably (ADD-only `remember`/`recall` @tools).
- Zero new required dependency; `MemoryBackend` is the locked interface that pgvector / Mem0 / sqlite-vec implement next, with zero change to products.

## Deferred (lock the seam, build nothing)
The `Mem0Backend` adapter is **interface-ready** — written against `mem0ai` when that optional dep is added (verify its `add/search/get_all` signatures first; do not guess); same for Zep/pgvector and the `sqlite-vec` index. The `procedural` tier population + `reflect(trigger_n≈100)` consolidation; the `AGENTS.md` static-context loader; confidence-decay constants. Each is a named follow-up gated on a proven dogfood gap — the *edge* itself is already proven by the two shipped backends.
