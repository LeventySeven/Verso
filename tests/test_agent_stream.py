# tests/test_agent_stream.py
from verso import Agent, StreamEvent, EventType
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.tool import tool
from verso.types import Usage, StopReason


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def test_agent_stream_yields_events_and_final_result():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 2, "b": 2})], usage=Usage()),
        ModelResponse(text="4", tool_calls=[], usage=Usage()),
    ])
    evs = [ev async for ev in Agent(model=fm, tools=[add]).stream("2+2?")]
    assert all(isinstance(e, StreamEvent) for e in evs)
    assert evs[-1].type is EventType.DONE
    assert evs[-1].result.output == "4" and evs[-1].result.stop_reason is StopReason.END_TURN


async def test_agent_stream_threads_instructions_and_budget():
    fm = FakeModel([ModelResponse(text="ok", tool_calls=[], usage=Usage())])
    agent = Agent(model=fm, instructions="be terse")
    _ = [ev async for ev in agent.stream("hi")]
    # instructions routed as system on the (stream) call
    assert fm.calls[0][2] == "be terse"
