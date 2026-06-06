# tests/test_e2e.py
import os
import pytest
from pydantic import BaseModel
from verso import Agent, tool, init_model
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.builtins import done
from verso.types import Usage, StopReason


@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b


async def test_e2e_fake_full_path():
    """The whole public path: Agent + @tool + loop + result, no network."""
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 20, "b": 22})], usage=Usage(input_tokens=8, output_tokens=2)),
        ModelResponse(text="42", tool_calls=[], usage=Usage(input_tokens=9, output_tokens=1)),
    ])
    result = await Agent(model=fm, tools=[add]).run("what is 20 + 22?")
    assert result.output == "42"
    assert result.stop_reason is StopReason.END_TURN
    assert result.usage.input_tokens == 17


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
async def test_e2e_live_anthropic():
    """One real call. Skipped unless ANTHROPIC_API_KEY is set."""
    agent = Agent(model=init_model("anthropic:claude-sonnet-4-6"), tools=[add],
                  instructions="Use the add tool for any arithmetic.")
    result = await agent.run("Use the add tool to compute 20 + 22, then reply with just the number.")
    assert "42" in result.output
    assert result.stop_reason is StopReason.END_TURN
    assert result.usage.output_tokens > 0


# --- appended: structured output + done, offline ---
class Sum(BaseModel):
    total: int


async def test_e2e_structured_output_offline():
    from verso.model.fake import FakeModel
    from verso.model.base import ModelResponse
    from verso.types import Usage
    fm = FakeModel([ModelResponse(text='{"total": 42}', tool_calls=[], usage=Usage())])
    result = await Agent(model=fm).run("sum 20 and 22 as JSON", output_type=Sum)
    assert result.parsed == Sum(total=42)


async def test_e2e_done_tool_offline():
    from verso.model.fake import FakeModel
    from verso.model.base import ModelResponse, ToolCall
    from verso.types import Usage
    fm = FakeModel([ModelResponse(text="", tool_calls=[ToolCall(id="d", name="done", arguments={"result": "complete"})], usage=Usage())])
    result = await Agent(model=fm, tools=[done]).run("finish")
    assert result.output == "complete" and result.stop_reason is StopReason.DONE


# --- appended: context engineering, offline ---
async def test_e2e_inspect_offline():
    from verso.model.fake import FakeModel
    from verso.model.base import ModelResponse
    from verso.types import Usage
    fm = FakeModel([ModelResponse(text="hi", tool_calls=[], usage=Usage())])
    agent = Agent(model=fm, tools=[add], instructions="be terse")
    bundle = agent.inspect("what is 2+2?")
    rendered = bundle.render()
    assert "[system]" in rendered and "be terse" in rendered
    assert "[user] what is 2+2?" in rendered
    assert bundle.estimate_tokens() > 0


# --- appended: streaming, offline ---
async def test_e2e_stream_and_sse_offline():
    from verso import Agent, EventType
    from verso.stream.sse import sse
    from verso.model.fake import FakeModel
    from verso.model.base import ModelResponse
    from verso.types import Usage
    fm = FakeModel([ModelResponse(text="hello", tool_calls=[], usage=Usage())])
    agent = Agent(model=fm)
    events = [e async for e in agent.stream("hi")]
    assert "".join(e.text for e in events if e.type is EventType.MESSAGE_DELTA) == "hello"
    assert events[-1].type is EventType.DONE

    fm2 = FakeModel([ModelResponse(text="hello", tool_calls=[], usage=Usage())])
    lines = [ln async for ln in sse(Agent(model=fm2).stream("hi"))]
    assert lines[-1] == "data: [DONE]\n\n"
