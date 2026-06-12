from verso import Agent, tool
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def test_no_checkpointer_is_identical_to_phase1():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage(input_tokens=1, output_tokens=1)),
        ModelResponse(text="3", tool_calls=[], usage=Usage(input_tokens=1, output_tokens=1)),
    ])
    r = await Agent(model=fm, tools=[add]).run("add")
    assert r.output == "3" and r.stop_reason.value == "end_turn" and r.steps == 2
    assert (r.usage.input_tokens, r.usage.output_tokens) == (2, 2)
    assert r.resume_token is None and r.pending is None
