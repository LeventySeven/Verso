# tests/test_memory_tools.py
from verso import Agent
from verso.memory.store import Memory
from verso.memory.builtins import memory_tools
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


async def test_agent_remembers_then_recalls_via_tools():
    mem = Memory.sqlite(":memory:", scope="u1", clock=lambda: 1000.0)
    remember, recall = memory_tools(mem)
    # turn 1: remember; turn 2: recall; turn 3: final answer
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="remember", arguments={"content": "user prefers metric units"})], usage=Usage()),
        ModelResponse(text="", tool_calls=[ToolCall(id="t2", name="recall", arguments={"query": "units"})], usage=Usage()),
        ModelResponse(text="noted: metric", tool_calls=[], usage=Usage()),
    ])
    result = await Agent(model=fm, tools=[remember, recall]).run("remember my unit preference, then recall it")
    assert result.output == "noted: metric"
    # the write is observable + durable: a fresh recall sees it
    hits = await mem.recall("units")
    assert any("metric" in h.content for h in hits)
