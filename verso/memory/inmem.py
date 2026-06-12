# verso/memory/inmem.py
from __future__ import annotations
import math

from verso.memory.types import MemoryRecord, TTL_SECONDS
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
            if r.valid_at > as_of:                 # not yet stored at the as-of instant
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
