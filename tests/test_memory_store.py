# tests/test_memory_store.py
from verso.memory.store import Memory
from verso.memory.types import MemoryType


async def test_remember_then_recall_roundtrip_with_scope_injected():
    m = Memory.sqlite(path=":memory:", scope="user-1", clock=lambda: 1000.0)
    await m.remember("postgres pooling uses pgbouncer", type=MemoryType.FACT, importance=0.9)
    hits = await m.recall("postgres pooling")
    assert hits and "pgbouncer" in hits[0].content
    assert hits[0].scope == "user-1"                       # scope auto-injected


async def test_remember_is_additive_supersede_invalidates_not_deletes():
    # advancing clock: store old @1000, supersede @2000, time-travel to @1500 (strictly between).
    clk = {"t": 1000.0}
    m = Memory.sqlite(path=":memory:", scope="user-1", clock=lambda: clk["t"])
    rid = await m.remember("the value is 1", type=MemoryType.FACT)      # valid_at=1000
    clk["t"] = 2000.0
    await m.supersede(rid, "the value is 2", type=MemoryType.FACT)      # old.invalid_at=2000; new.valid_at=2000
    now_hits = await m.recall("value")                                 # now=2000
    assert any("2" in h.content for h in now_hits)
    assert not any(h.content == "the value is 1" for h in now_hits)     # old invalidated → gone from "now"
    # recall_as_of BEFORE the supersession still sees the old fact, and NOT the not-yet-stored new one:
    past = await m.recall_as_of("value", as_of=1500.0)
    assert any(h.content == "the value is 1" for h in past)             # known at t=1500
    assert not any(h.content == "the value is 2" for h in past)         # stored later (@2000) — not yet known
