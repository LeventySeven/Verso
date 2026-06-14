# tests/test_memory_correctness.py
# Two memory-correctness regressions, asserted identically across BOTH backends (and the optional
# sqlite-vec subclass, which inherits both code paths unchanged):
#   Bug 1 — bound eviction must be tier-aware: a permanent FACT/PROCEDURAL is never dropped to make room
#           for an ephemeral SCRATCHPAD/EPISODIC while any evictable non-permanent row remains. When every
#           row is permanent the oldest is still evicted, so the bound keeps making progress.
#   Bug 2 — recent() must honor the SAME per-type TTL search()/recall() honors (once given a clock), so
#           reflect() — which feeds on recent() — never consolidates an already-expired episodic.
import pytest

from verso.memory.sqlite import SqliteBackend
from verso.memory.inmem import InMemoryBackend
from verso.memory.embed import HashEmbedder
from verso.memory.store import Memory
from verso.memory.types import MemoryRecord, MemoryType, TTL_SECONDS

EPISODIC_TTL = TTL_SECONDS[MemoryType.EPISODIC]   # 7d, from the single source of truth


def _stored_ids(b) -> set:
    # Surviving ids straight from each backend's store — checks eviction directly, without the TTL
    # filtering that search() would layer on (a SCRATCHPAD would be TTL-dropped by search regardless
    # of whether it was evicted). sqlite/sqlitevec expose `.db`; inmem exposes `._recs`.
    if hasattr(b, "db"):
        return {r["id"] for r in b.db.execute("SELECT id FROM memory")}
    return {r.id for r in b._recs}


def _rec(id, content, **kw):
    return MemoryRecord(id=id, type=kw.get("type", MemoryType.FACT), content=content,
                        scope=kw.get("scope", "default"),
                        importance=kw.get("importance", 0.5), outcome=kw.get("outcome"),
                        valid_at=kw.get("valid_at", 100.0), invalid_at=kw.get("invalid_at"),
                        embedding=HashEmbedder(128).embed(content))


@pytest.fixture(params=["sqlite", "inmem", "sqlitevec"])
def make_backend(request):
    """Factory so each test can pick its own max_records; same param set as test_memory_backends."""
    def _make(max_records):
        emb = HashEmbedder(128)
        if request.param == "sqlite":
            return SqliteBackend(":memory:", embedder=emb, max_records=max_records)
        if request.param == "inmem":
            return InMemoryBackend(embedder=emb, max_records=max_records)
        pytest.importorskip("sqlite_vec")
        from verso.memory.sqlitevec import SqliteVecBackend
        return SqliteVecBackend(":memory:", embedder=emb, max_records=max_records)
    return _make


# ---- Bug 1: tier-aware bound eviction -------------------------------------------------------------

def test_bound_eviction_preserves_permanent_over_ephemeral(make_backend):
    # max_records=2: a permanent FACT stored FIRST (oldest by valid_at) plus two later ephemerals can't
    # all fit. Pure age-ordered eviction would delete the FACT (the oldest); tier-aware eviction drops an
    # ephemeral instead. The FACT must survive.
    b = make_backend(2)
    b.add(_rec("fact", "a permanent fact", type=MemoryType.FACT, valid_at=1.0))
    b.add(_rec("eph1", "ephemeral one", type=MemoryType.SCRATCHPAD, valid_at=2.0))
    b.add(_rec("eph2", "ephemeral two", type=MemoryType.EPISODIC, valid_at=3.0))
    ids = _stored_ids(b)
    assert b.count() == 2
    assert "fact" in ids                       # the permanent tier survived the bound
    assert "eph1" not in ids                   # the oldest *ephemeral* was evicted, not the FACT


def test_bound_eviction_preserves_procedural_too(make_backend):
    # PROCEDURAL is the other permanent tier (TTL None) — derive-from-types.py, not a FACT-only list.
    b = make_backend(2)
    b.add(_rec("proc", "a permanent procedure", type=MemoryType.PROCEDURAL, valid_at=1.0))
    b.add(_rec("eph1", "ephemeral one", type=MemoryType.SCRATCHPAD, valid_at=2.0))
    b.add(_rec("eph2", "ephemeral two", type=MemoryType.SCRATCHPAD, valid_at=3.0))
    ids = _stored_ids(b)
    assert b.count() == 2
    assert "proc" in ids                       # PROCEDURAL is permanent too


def test_bound_eviction_all_permanent_still_evicts_oldest(make_backend):
    # If every row is permanent the bound must still hold — otherwise it could never make progress.
    # Evict the OLDEST permanent row.
    b = make_backend(2)
    b.add(_rec("f0", "fact zero", type=MemoryType.FACT, valid_at=1.0))
    b.add(_rec("f1", "fact one", type=MemoryType.FACT, valid_at=2.0))
    b.add(_rec("f2", "fact two", type=MemoryType.FACT, valid_at=3.0))
    ids = _stored_ids(b)
    assert b.count() == 2                       # progress guaranteed even when all-permanent
    assert "f0" not in ids                      # oldest permanent evicted
    assert ids == {"f1", "f2"}


# ---- Bug 2: recent() honors TTL (so reflect() does too) -------------------------------------------

def test_recent_honors_ttl_like_search(make_backend):
    b = make_backend(100)
    now = 1000.0 + EPISODIC_TTL + 10.0
    # `stale` stored long ago (age > EPISODIC TTL at `now`); `fresh` stored just now (well within TTL).
    b.add(_rec("stale", "ancient episode", type=MemoryType.EPISODIC, valid_at=1000.0))
    b.add(_rec("fresh", "recent episode", type=MemoryType.EPISODIC, valid_at=now - 5.0))

    got = {r.id for r in b.recent(types=[MemoryType.EPISODIC], now=now)}
    assert "stale" not in got                   # expired → dropped, exactly as search()/recall() drops it
    assert "fresh" in got                       # within TTL → returned

    # cross-check the contract: search() agrees on what's live
    searched = {r.id for r in b.search("episode", embedding=HashEmbedder(128).embed("episode"), now=now)}
    assert "stale" not in searched and "fresh" in searched

    # back-compat: with NO clock, recent() keeps its pre-fix invalid_at-only behavior (no TTL drop)
    no_clock = {r.id for r in b.recent(types=[MemoryType.EPISODIC])}
    assert "stale" in no_clock and "fresh" in no_clock


# ---- Bug 2 end-to-end: reflect() does not consolidate an expired episodic -------------------------

@pytest.mark.parametrize("backend_kind", ["sqlite", "inmem"])
async def test_reflect_skips_ttl_expired_episodics(backend_kind):
    clk = {"t": 1000.0}
    emb = HashEmbedder(128)
    if backend_kind == "sqlite":
        backend = SqliteBackend(":memory:", embedder=emb, max_records=100)
    else:
        backend = InMemoryBackend(embedder=emb, max_records=100)
    m = Memory(backend, emb, scope="default", clock=lambda: clk["t"])

    await m.remember("stale episode about pgbouncer", type=MemoryType.EPISODIC)   # valid_at=1000
    clk["t"] = 1000.0 + EPISODIC_TTL + 10.0                                       # advance past TTL
    await m.remember("fresh episode about pgbouncer", type=MemoryType.EPISODIC)   # fresh at the new now

    seen_contents = []

    def reflector(contents):
        seen_contents.extend(contents)
        return [f"consolidated {len(contents)} live episodes"]

    facts = await m.reflect(reflector, trigger_n=0)
    assert len(facts) == 1
    # reflect() fed only the LIVE (within-TTL) episodic to the reflector — the expired one is excluded
    assert any("fresh episode" in c for c in seen_contents)
    assert not any("stale episode" in c for c in seen_contents)
    # and the consolidated fact reflects exactly one live source
    assert any("consolidated 1 live episodes" in h.content for h in await m.recall("consolidated"))
