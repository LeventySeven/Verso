# tests/test_context_loop.py
from verso import Agent
from verso.context.bundle import ContextBundle
from verso.context.prune import MASK
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.tool import tool
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def test_inspect_byte_equals_what_model_receives():
    fm = FakeModel([ModelResponse(text="done", tool_calls=[], usage=Usage())])
    agent = Agent(model=fm, tools=[add], instructions="be terse")
    bundle = agent.inspect("hello")
    await agent.run("hello")
    sent_messages, sent_tools, sent_system = fm.calls[0]
    assert bundle.to_messages() == sent_messages
    assert bundle.system == sent_system == "be terse"
    assert [t.name for t in bundle.tools] == [t.name for t in sent_tools]
    assert isinstance(bundle, ContextBundle)


async def test_instructions_go_as_system_not_a_user_message():
    fm = FakeModel([ModelResponse(text="ok", tool_calls=[], usage=Usage())])
    await Agent(model=fm, instructions="SYS").run("hi")
    messages, _tools, system = fm.calls[0]
    assert system == "SYS"
    assert [m.content for m in messages] == ["hi"]   # no instructions message in history


async def test_budget_triggers_prune_of_old_tool_outputs():
    # 12 tool turns then a final answer; tiny budget forces a prune before the last call
    responses = [
        ModelResponse(text="", tool_calls=[ToolCall(id=f"t{i}", name="add", arguments={"a": 1, "b": 1})], usage=Usage())
        for i in range(12)
    ]
    responses.append(ModelResponse(text="final", tool_calls=[], usage=Usage()))
    fm = FakeModel(responses)
    agent = Agent(model=fm, tools=[add], max_context_tokens=1)  # force pruning
    result = await agent.run("loop a lot")
    assert result.output == "final"
    # the LAST model call should have seen masked old tool outputs
    last_messages = fm.calls[-1][0]
    masked = [m for m in last_messages if m.role == "tool" and m.content == MASK]
    assert len(masked) >= 1


async def test_no_prune_when_budget_unset():
    fm = FakeModel([ModelResponse(text="ok", tool_calls=[], usage=Usage())])
    await Agent(model=fm, tools=[add]).run("hi")  # max_context_tokens=None default
    assert all(m.content != MASK for m in fm.calls[0][0])
