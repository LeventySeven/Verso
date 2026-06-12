from verso import Agent, tool
from verso.evals.span import VersoSpan
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


def _agent():
    # turn 1: call add; turn 2: final answer
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage(input_tokens=10, output_tokens=2)),
        ModelResponse(text="the answer is 3", tool_calls=[], usage=Usage(input_tokens=8, output_tokens=4)),
    ])
    return Agent(model=fm, tools=[add], instructions="be terse")


async def test_capture_from_stream_records_tools_stop_output_and_usage():
    span = await VersoSpan.capture(_agent(), "add 1 and 2")
    assert span.tool_names() == ["add"]          # which tools ran, in order
    assert span.ok                               # no tool errored
    assert span.output == "the answer is 3"
    assert span.stop_reason == "end_turn"
    assert span.steps == 2
    assert span.usage_total == 24                # 10+2+8+4
    assert span.trace_id                         # addressable


async def test_jsonl_round_trips():
    span = await VersoSpan.capture(_agent(), "add 1 and 2")
    restored = VersoSpan.from_jsonl(span.to_jsonl())
    assert restored.tool_names() == span.tool_names()
    assert restored.output == span.output
    assert restored.trace_id == span.trace_id


async def test_render_shows_tools_and_final():
    span = await VersoSpan.capture(_agent(), "add 1 and 2")
    out = span.render()
    assert "add(" in out and "the answer is 3" in out
