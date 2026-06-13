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


@pytest.fixture(params=["sqlite", "inmem", "sqlitevec"])
def backend(request):
    emb = HashEmbedder(128)
    if request.param == "sqlite":
        return SqliteBackend(":memory:", embedder=emb, max_records=3)
    if request.param == "inmem":
        return InMemoryBackend(embedder=emb, max_records=3)
    pytest.importorskip("sqlite_vec")            # only the vec param needs the optional dep
    from verso.memory.sqlitevec import SqliteVecBackend
    return SqliteVecBackend(":memory:", embedder=emb, max_records=3)


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


def test_contract_recent_returns_live_records_newest_first(backend):
    backend.add(_rec("e0", "episode zero", type=MemoryType.EPISODIC, valid_at=10.0))
    backend.add(_rec("e1", "episode one", type=MemoryType.EPISODIC, valid_at=20.0))
    backend.add(_rec("f0", "a fact", type=MemoryType.FACT, valid_at=15.0))
    rec = backend.recent(scope="default", types=[MemoryType.EPISODIC], limit=10)
    assert [r.id for r in rec] == ["e1", "e0"]      # newest-first, type-filtered (the FACT is excluded)
    backend.invalidate("e0", at=25.0)
    assert [r.id for r in backend.recent(scope="default", types=[MemoryType.EPISODIC], limit=10)] == ["e1"]


def test_sqlitevec_index_stays_in_sync_through_eviction():
    pytest.importorskip("sqlite_vec")
    from verso.memory.sqlitevec import SqliteVecBackend
    emb = HashEmbedder(128)
    b = SqliteVecBackend(":memory:", embedder=emb, max_records=2)
    for i in range(5):
        b.add(_rec(f"r{i}", f"vector note {i}", valid_at=float(i)))   # r0..r2 evicted; r3,r4 survive
    vec_n = b.db.execute("SELECT count(*) c FROM vec_memory").fetchone()["c"]
    assert vec_n == b.count() == 2               # vec0 index kept in lockstep with memory through eviction
    hits = b.search("vector note", embedding=emb.embed("vector note"), now=10.0)
    assert {h.id for h in hits} == {"r3", "r4"}  # KNN over the ANN index returns exactly the survivors
