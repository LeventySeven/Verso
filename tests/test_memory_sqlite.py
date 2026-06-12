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


def test_recall_query_with_fts_operator_words_is_literal_not_syntax():
    # LLM recall queries can contain FTS5 operator barewords (AND/OR/NOT/NEAR); each must be matched
    # as a literal term, not parsed as an operator — otherwise FTS5 raises sqlite3.OperationalError.
    b = _backend()
    b.add(_rec("a", "Smith and Wesson revolver"))
    b.add(_rec("b", "unrelated strawberry cake"))
    hits = b.search("Smith AND Wesson", embedding=HashEmbedder(128).embed("Smith AND Wesson"), now=200.0)
    assert hits and hits[0].id == "a"                    # no crash; operator words matched as literals


def test_search_after_eviction_returns_only_survivors():
    # eviction DELETEs from `memory`; the memory_ad trigger must drop the evicted rows' FTS terms too,
    # otherwise stale rowids linger in the index. Search must surface survivors and never an evicted record.
    b = _backend(cap=2)
    for i in range(4):
        b.add(_rec(f"r{i}", f"postgres pooling note {i}", valid_at=float(i)))   # r0,r1 evicted; r2,r3 survive
    hits = b.search("postgres pooling note", embedding=HashEmbedder(128).embed("postgres pooling note"), now=10.0)
    ids = {h.id for h in hits}
    assert ids == {"r2", "r3"}                           # exactly the survivors, no orphaned/evicted rows
    assert b.count() == len(hits) == 2                   # FTS index stayed in lockstep with `memory`
