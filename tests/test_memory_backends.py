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
