# tests/test_hooks_backcompat.py
from verso import Agent, tool
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


def _responses():
    return [ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage(input_tokens=1, output_tokens=1)),
            ModelResponse(text="3", tool_calls=[], usage=Usage(input_tokens=1, output_tokens=1))]


async def test_no_hooks_is_identical_to_phase0():
    bare = await Agent(model=FakeModel(_responses()), tools=[add]).run("add")
    assert bare.output == "3" and bare.stop_reason.value == "end_turn" and bare.steps == 2
    assert (bare.usage.input_tokens, bare.usage.output_tokens) == (2, 2)
