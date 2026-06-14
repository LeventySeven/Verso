import pytest
from verso import Agent, tool
from verso.tools.errors import Retry
from verso.tools.dispatch import dispatch
from verso.tools.coerce import StructuredOutputError
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage
from pydantic import BaseModel


async def test_dispatch_propagates_retry():
    @tool
    def t(x: int) -> int:
        "t"
        raise Retry("x must be > 0")
    with pytest.raises(Retry):
        await dispatch(t, {"x": -1})


async def test_tool_retry_feeds_feedback_then_succeeds():
    calls = {"n": 0}
    @tool
    def code(value: str) -> str:
        "Return a 2-letter code."
        calls["n"] += 1
        if calls["n"] == 1:
            raise Retry("must be exactly 2 letters")
        return "ok"
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="a", name="code", arguments={"value": "x"})], usage=Usage()),
        ModelResponse(text="", tool_calls=[ToolCall(id="b", name="code", arguments={"value": "xy"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    r = await Agent(model=fm, tools=[code]).run("go")
    assert r.output == "done" and calls["n"] == 2     # retried with feedback, then succeeded


async def test_tool_retry_budget_caps_an_always_retrying_tool():
    from verso.safety.hooks import Hooks
    seen: list[str] = []
    @tool
    def loops(value: str) -> str:
        "Always retries."
        raise Retry("never happy")
    fm = FakeModel([ModelResponse(text="", tool_calls=[ToolCall(id=str(i), name="loops", arguments={"value": "x"})], usage=Usage()) for i in range(5)]
                   + [ModelResponse(text="gave up", tool_calls=[], usage=Usage())])
    hooks = Hooks(post_tool=[lambda call, content: seen.append(content) or content])  # capture every tool result
    r = await Agent(model=fm, tools=[loops], hooks=hooks, max_tool_retries=2).run("go")
    assert r.stop_reason.value in ("end_turn", "max_steps")           # it TERMINATES (no infinite Retry loop)
    # the BUDGET (not the script) bounded it: exactly 2 'Retry:' feedbacks, then the terminal budget error
    assert sum(1 for c in seen if c.startswith("Retry:")) == 2
    assert any("exceeded its retry budget" in c for c in seen)


async def test_max_tool_retries_is_configurable_from_agent():
    seen: list[str] = []
    @tool
    def loops(value: str) -> str:
        "Always retries."
        raise Retry("nope")
    fm = FakeModel([ModelResponse(text="", tool_calls=[ToolCall(id=str(i), name="loops", arguments={"value": "x"})], usage=Usage()) for i in range(4)]
                   + [ModelResponse(text="stop", tool_calls=[], usage=Usage())])
    hooks = Hooks(post_tool=[lambda call, content: seen.append(content) or content])
    await Agent(model=fm, tools=[loops], hooks=hooks, max_tool_retries=0).run("go")  # 0 ⇒ no Retry feedback at all
    assert sum(1 for c in seen if c.startswith("Retry:")) == 0        # budget=0 honored from the Agent surface
    assert any("exceeded its retry budget (0)" in c for c in seen)


class Code(BaseModel):
    value: str


async def test_output_validator_retry_then_succeed():
    fm = FakeModel([
        ModelResponse(text='{"value": "x"}', tool_calls=[], usage=Usage()),     # fails validator
        ModelResponse(text='{"value": "xy"}', tool_calls=[], usage=Usage()),    # passes
    ])
    def two_letters(c: Code):
        if len(c.value) != 2:
            raise Retry("value must be exactly 2 letters")
    r = await Agent(model=fm, tools=[]).run("go", output_type=Code, validators=[two_letters], max_output_retries=2)
    assert r.parsed.value == "xy"


async def test_output_reask_budget_exhausts_and_raises():
    fm = FakeModel([ModelResponse(text='{"value": "x"}', tool_calls=[], usage=Usage()) for _ in range(5)])
    def two_letters(c: Code):
        if len(c.value) != 2:
            raise Retry("nope")
    with pytest.raises(StructuredOutputError):
        await Agent(model=fm, tools=[]).run("go", output_type=Code, validators=[two_letters], max_output_retries=1)
