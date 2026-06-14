# tests/test_model_swap.py
# Plan 20 Batch X: swap the model by string or instance, per-run or scoped, without rebuilding the Agent.
import pytest
from pydantic import BaseModel

from verso import Agent
from verso.safety.hooks import Hooks, PermissionDecision
from verso.durable.inmem import InMemoryCheckpointStore
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason
from verso.tools.tool import tool
from verso.stream.events import EventType


class Point(BaseModel):
    x: int
    y: int


def _text(s: str) -> ModelResponse:
    return ModelResponse(text=s, tool_calls=[], usage=Usage())


# 1. A 'provider:model' string at construction resolves to the right Model class + model_id.
def test_string_model_at_construction_resolves():
    a = Agent(model="anthropic:claude-x")
    assert type(a.model).__name__ == "AnthropicModel"
    assert a.model.model_id == "claude-x"

    b = Agent(model="openai:gpt-4o")
    assert type(b.model).__name__ == "OpenAIModel"
    assert b.model.model_id == "gpt-4o"


# 2. A Model instance passes through untouched (byte-identical: same object).
def test_model_instance_passes_through_unchanged():
    fm = FakeModel([_text("hi")])
    assert Agent(model=fm).model is fm


# 3. The key one: per-run override applies to that run only and does not stick.
async def test_per_run_override_does_not_stick():
    default = FakeModel([_text("DEFAULT"), _text("DEFAULT")])
    other = FakeModel([_text("OTHER")])
    agent = Agent(model=default)

    assert (await agent.run("x", model=other)).output == "OTHER"
    assert (await agent.run("x")).output == "DEFAULT"      # override didn't stick

    assert len(other.calls) == 1                            # the override model was used exactly once
    assert len(default.calls) == 1                          # and the default exactly once (the no-override run)


# 4. The override holds across structured-output reasks (both tries hit the override, never the default).
async def test_override_holds_across_reasks():
    override = FakeModel([
        _text("not json at all"),          # first try: unparseable → triggers a reask
        _text('{"x": 1, "y": 2}'),         # reask: valid
    ])
    default = FakeModel([_text('{"x": 9, "y": 9}')])
    agent = Agent(model=default)

    result = await agent.run("give a point", output_type=Point, max_output_retries=1, model=override)
    assert result.parsed == Point(x=1, y=2)
    assert len(override.calls) == 2        # both the original and the reask used the override
    assert len(default.calls) == 0         # the default was never touched


# 5. override() restores the previous model even when the block raises.
def test_override_context_manager_restores_on_exception():
    default = FakeModel([_text("d")])
    other = FakeModel([_text("o")])
    agent = Agent(model=default)

    with pytest.raises(RuntimeError):
        with agent.override(model=other):
            assert agent.model is other
            raise RuntimeError("boom")
    assert agent.model is default          # restored despite the exception


# 5b. override() also restores on the normal (non-exception) exit, and yields self.
async def test_override_context_manager_normal_exit():
    default = FakeModel([_text("DEFAULT")])
    other = FakeModel([_text("OTHER")])
    agent = Agent(model=default)

    with agent.override(model=other) as a:
        assert a is agent
        assert (await agent.run("x")).output == "OTHER"    # runs inside the block use the override
    assert agent.model is default
    assert (await agent.run("x")).output == "DEFAULT"


# 6. A paused durable run can resume on a different model.
@tool
def send_email(to: str) -> str:
    "Send an email."
    return f"sent to {to}"


async def test_resume_on_a_different_model():
    store = InMemoryCheckpointStore()
    default = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="send_email",
                      arguments={"to": "x@y.z"})], usage=Usage()),
        # NOTE: no second response scripted on default — if resume used it, FakeModel would raise.
    ])
    other = FakeModel([_text("RESUMED_OTHER")])
    hooks = Hooks(pre_tool=[lambda call: PermissionDecision.ASK])
    agent = Agent(model=default, tools=[send_email], hooks=hooks, checkpointer=store)

    paused = await agent.run("email x")
    assert paused.stop_reason == StopReason.PAUSED

    resumed = await agent.resume(paused.resume_token, approve=True, model=other)
    assert resumed.stop_reason == StopReason.END_TURN
    assert resumed.output == "RESUMED_OTHER"
    assert len(other.calls) == 1           # the continuation ran on `other`
    assert len(default.calls) == 1         # default only produced the initial (paused) turn


# 7. stream() honors a per-stream override.
async def test_stream_override():
    default = FakeModel([_text("DEFAULT")])
    other = FakeModel([_text("OTHER")])
    agent = Agent(model=default)

    events = [e async for e in agent.stream("x", model=other)]
    assert events[-1].type is EventType.DONE
    assert events[-1].result.output == "OTHER"
    assert len(other.calls) >= 1
    assert len(default.calls) == 0
