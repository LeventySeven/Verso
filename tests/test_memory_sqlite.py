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
