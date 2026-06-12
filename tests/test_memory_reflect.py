from verso.memory.store import Memory
from verso.memory.types import MemoryType


def _mem():
    return Memory.sqlite(":memory:", scope="u1", clock=lambda: 1000.0)


async def test_reflect_consolidates_episodics_into_a_fact_and_invalidates_sources():
    m = _mem()
    for i in range(3):
        await m.remember(f"saw event {i}", type=MemoryType.EPISODIC)
    facts = await m.reflect(lambda contents: [f"observed {len(contents)} events"], trigger_n=0)
    assert len(facts) == 1
    assert any("observed 3 events" in h.content for h in await m.recall("observed events"))
    # the consolidated sources are invalidated (ADD-only) — a fresh episodic recall no longer returns them
    assert not any("saw event" in h.content for h in await m.recall("event", types=[MemoryType.EPISODIC]))


async def test_reflect_below_trigger_n_is_a_noop():
    m = _mem()
    await m.remember("one episode", type=MemoryType.EPISODIC)
    assert await m.reflect(lambda c: ["should not run"], trigger_n=100) == []
    assert any("one episode" in h.content for h in await m.recall("episode", types=[MemoryType.EPISODIC]))


async def test_reflect_can_populate_the_procedural_tier():
    m = _mem()
    for i in range(2):
        await m.remember(f"did step {i}", type=MemoryType.EPISODIC, outcome="success")
    procs = await m.reflect(lambda c: ["procedure: do the steps in order"], trigger_n=0,
                            target_type=MemoryType.PROCEDURAL)
    assert len(procs) == 1
    hits = await m.recall("procedure steps", types=[MemoryType.PROCEDURAL])
    assert any("do the steps in order" in h.content for h in hits)


async def test_reflect_supports_an_async_reflector():
    m = _mem()
    await m.remember("an episodic note", type=MemoryType.EPISODIC)

    async def llm_reflector(contents):
        return ["a distilled fact"]

    facts = await m.reflect(llm_reflector, trigger_n=0)
    assert len(facts) == 1
    assert any("distilled fact" in h.content for h in await m.recall("distilled fact"))
