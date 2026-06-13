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
        # ids are always fresh uuids; plain INSERT. The memory_ai/memory_ad triggers keep memory_fts in sync,
        # including on eviction — so the FTS index can't accumulate orphaned terms.
        self.db.execute(
            "INSERT INTO memory(id,type,content,scope,importance,outcome,valid_at,invalid_at,embedding)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (r.id, r.type.value, r.content, r.scope, r.importance, r.outcome, r.valid_at, r.invalid_at,
             json.dumps(r.embedding)))
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

    def recent(self, *, scope="default", types=None, limit=100):
        # most-recent LIVE (non-invalidated) records of the given types — the consolidation feed for reflect().
        q = "SELECT rowid,* FROM memory WHERE scope=? AND invalid_at IS NULL"
        params: list = [scope]
        if types:
            q += " AND type IN (%s)" % ",".join("?" * len(types))
            params += [t.value for t in types]
        q += " ORDER BY valid_at DESC LIMIT ?"
        params.append(limit)
        return [_to_record(r) for r in self.db.execute(q, params).fetchall()]

    def search(self, query, *, embedding, now, scope="default", types=None, k=10, as_of=None):
        as_of = now if as_of is None else as_of
        rows = [dict(r) for r in self.db.execute("SELECT rowid,* FROM memory WHERE scope=?", (scope,))]
        # temporal + TTL validity at `as_of`
        live = []
        for row in rows:
            if types and row["type"] not in {t.value for t in types}:
                continue
            if row["valid_at"] > as_of:        # not yet stored at the as-of instant
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
        vec_rank = self._vector_rank(live, embedding)

        def fused(r):
            rrf = 1.0 / (RRF_K + lex_rank.get(r["rowid"], 10_000)) + 1.0 / (RRF_K + vec_rank.get(r["rowid"], 10_000))
            recency = math.exp(-(now - r["valid_at"]) / (30 * 86400))     # 30d decay
            penalty = 0.5 if r["outcome"] == "success" else 1.0           # down-weight successes
            return (0.5 * rrf + 0.3 * recency + 0.2 * r["importance"]) * penalty

        ranked = sorted(live, key=fused, reverse=True)[:k]
        return [_to_record(r) for r in ranked]

    def _vector_rank(self, live, embedding) -> dict:
        # brute-force cosine over live candidates (correct at personal-infra scale);
        # SqliteVecBackend overrides this with a sqlite-vec ANN index.
        order = sorted(live, key=lambda r: cosine(embedding, json.loads(r["embedding"])), reverse=True)
        return {r["rowid"]: i for i, r in enumerate(order)}


def _fts_query(q: str) -> str:
    terms = [t for t in "".join(c if c.isalnum() else " " for c in q).split() if t]
    # quote each (alphanumeric) term so FTS5 reads it as a literal, never an OR/AND/NOT/NEAR operator.
    return " OR ".join(f'"{t}"' for t in terms) or '""'


def _to_record(row) -> MemoryRecord:
    return MemoryRecord(id=row["id"], type=MemoryType(row["type"]), content=row["content"], scope=row["scope"],
                        importance=row["importance"], outcome=row["outcome"], valid_at=row["valid_at"],
                        invalid_at=row["invalid_at"], embedding=json.loads(row["embedding"]))
