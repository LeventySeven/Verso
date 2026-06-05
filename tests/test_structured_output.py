# tests/test_structured_output.py
import pytest
from pydantic import BaseModel
from verso import Agent
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse
from verso.tools.coerce import StructuredOutputError
from verso.types import Usage


class Point(BaseModel):
    x: int
    y: int


async def test_output_type_parses_final_answer():
    fm = FakeModel([ModelResponse(text='{"x": 1, "y": 2}', tool_calls=[], usage=Usage())])
    result = await Agent(model=fm).run("give a point", output_type=Point)
    assert isinstance(result.parsed, Point)
    assert result.parsed.x == 1 and result.parsed.y == 2
    assert result.output == '{"x": 1, "y": 2}'


async def test_output_type_reasks_once_then_succeeds():
    fm = FakeModel([
        ModelResponse(text="sorry, x is five", tool_calls=[], usage=Usage()),       # unparseable
        ModelResponse(text='{"x": 5, "y": 6}', tool_calls=[], usage=Usage()),       # reask answer
    ])
    result = await Agent(model=fm).run("give a point", output_type=Point)
    assert result.parsed == Point(x=5, y=6)
    assert len(fm.calls) == 2  # original + one reask


async def test_output_type_raises_after_failed_reask():
    fm = FakeModel([
        ModelResponse(text="nope", tool_calls=[], usage=Usage()),
        ModelResponse(text="still nope", tool_calls=[], usage=Usage()),
    ])
    with pytest.raises(StructuredOutputError):
        await Agent(model=fm).run("give a point", output_type=Point)


async def test_run_without_output_type_unchanged():
    fm = FakeModel([ModelResponse(text="plain text", tool_calls=[], usage=Usage())])
    result = await Agent(model=fm).run("hi")
    assert result.output == "plain text"
    assert result.parsed is None
