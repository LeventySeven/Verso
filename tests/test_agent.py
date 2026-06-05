# tests/test_agent.py
from verso import Agent, tool
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def test_agent_run_end_to_end_with_fake_model():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 2, "b": 2})], usage=Usage()),
        ModelResponse(text="4", tool_calls=[], usage=Usage()),
    ])
    agent = Agent(model=fm, tools=[add])
    result = await agent.run("what is 2+2?")
    assert result.output == "4"
    assert result.stop_reason is StopReason.END_TURN


async def test_agent_respects_max_steps():
    fm = FakeModel([ModelResponse(text="", tool_calls=[ToolCall(id="t", name="add", arguments={"a": 1, "b": 1})], usage=Usage()) for _ in range(5)])
    agent = Agent(model=fm, tools=[add], max_steps=2)
    result = await agent.run("loop")
    assert result.stop_reason is StopReason.MAX_STEPS
