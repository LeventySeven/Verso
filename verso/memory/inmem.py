# verso/memory/inmem.py
from __future__ import annotations
import math

from verso.memory.types import MemoryRecord, TTL_SECONDS
from verso.memory.embed import Embedder, cosine

RRF_K = 60

# Permanent tiers, derived from the single source of truth in types.py (TTL None == permanent) — mirror
# of SqliteBackend.PERMANENT_TYPE_VALUES, kept non-divergent. Here we keep the MemoryType members
# (the in-memory records carry MemoryType, not the stored string).
PERMANENT_TYPES = frozenset(t for t, ttl in TTL_SECONDS.items() if ttl is None)


class InMemoryBackend:
    """Dict/list-based MemoryBackend — dependency-free, zero-persistence. For ephemeral/tactical
    agents and as the proof that the MemoryBackend edge swaps. Same semantics as SqliteBackend
    (RRF over lexical-overlap + vector; temporal/TTL filter; success down-weight; bound)."""
    def __init__(self, *, embedder: Embedder, max_records: int = 10_000):
        self.embedder, self.max_records = embedder, max_records
        self._recs: list[MemoryRecord] = []

    def add(self, r: MemoryRecord) -> None:
        self._recs = [x for x in self._recs if x.id != r.id] + [r]
        n_evict = len(self._recs) - self.max_records
        if n_evict > 0:
            # Tier-aware eviction, mirroring SqliteBackend._enforce_bound: rank eviction candidates with
            # non-permanent (TTL'd) tiers first, oldest valid_at within each tier — so an ephemeral row is
            # always dropped before a permanent FACT/PROCEDURAL. Only when every row is permanent does the
            # oldest permanent row get evicted, so the bound still makes progress. Evict the first N.
            ranked = sorted(self._recs, key=lambda x: (x.type in PERMANENT_TYPES, x.valid_at))
            evict_ids = {id(x) for x in ranked[:n_evict]}
            self._recs = [x for x in self._recs if id(x) not in evict_ids]

    def invalidate(self, id: str, at: float) -> None:
        for r in self._recs:
            if r.id == id:
                r.invalid_at = at

    def count(self) -> int:
        return len(self._recs)

    def recent(self, *, scope="default", types=None, limit=100, now=None):
        # "Live" must match search()/recall(): non-invalidated AND not past its per-type TTL, so reflect()
        # (which feeds on recent()) never consolidates an expired episodic that recall() drops. `now` is the
        # clock search() uses; reflect() threads the store clock through. It is optional and defaults to None
        # — clock-less callers keep the pre-fix behavior (invalid_at-only), so every existing caller is
        # unaffected; the TTL filter engages only once a caller supplies `now`. Mirrors SqliteBackend.recent.
        def _live(r: MemoryRecord) -> bool:
            if r.scope != scope or r.invalid_at is not None or (types and r.type not in types):
                return False
            if now is None:
                return True
            ttl = TTL_SECONDS[r.type]
            return ttl is None or now - r.valid_at <= ttl     # same TTL drop as search()

        live = [r for r in self._recs if _live(r)]
        live.sort(key=lambda r: r.valid_at, reverse=True)   # newest-first
        return live[:limit]

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
