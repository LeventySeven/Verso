# tests/test_harness_reliability.py
import pytest

from verso import Agent, reinforce_objective, tool
from verso.core.loop import _truncate_tool_output
from verso.core.stream_loop import run_stream
from verso.durable.context import RunContext
from verso.model.base import ModelResponse, ToolCall
from verso.model.fake import FakeModel
from verso.safety.hooks import Hooks
from verso.stream.events import EventType
from verso.types import StopReason, Usage


@tool
def ping(value: str) -> str:
    "A tool that echoes."
    return "pong"


@tool
def big(n: int) -> str:
    "A tool that returns a long string."
    return "A" * n


def _two_tool_calls_then_done(name: str, args: dict):
    # two tool turns, then a plain text turn so the loop ends with END_TURN.
    return FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name=name, arguments=args)], usage=Usage()),
        ModelResponse(text="", tool_calls=[ToolCall(id="t2", name=name, arguments=args)], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])


def _one_tool_call_then_done(name: str, args: dict):
    return FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name=name, arguments=args)], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])


def _tool_messages(history):
    return [m for m in history if m.role == "tool"]


# --- B1: reinforce_objective -------------------------------------------------

async def test_reinforce_objective_appends_on_every_tool_return():
    h = Hooks(post_tool=[reinforce_objective("do X")])
    fm = _one_tool_call_then_done("ping", {"value": "x"})
    agent = Agent(model=fm, tools=[ping], hooks=h)
    result = await agent.run("go")
    assert result.stop_reason == StopReason.END_TURN
    # the tool result the model received carries the re-anchor line
    tool_turn_msgs = [m for call in fm.calls for m in call[0] if m.role == "tool"]
    assert any("[objective: do X]" in m.content for m in tool_turn_msgs)
    assert any(m.content.startswith("pong") for m in tool_turn_msgs)


async def test_reinforce_objective_every_2_appends_on_second_only():
    h = Hooks(post_tool=[reinforce_objective("do X", every=2)])
    fm = _two_tool_calls_then_done("ping", {"value": "x"})
    agent = Agent(model=fm, tools=[ping], hooks=h)
    await agent.run("go")
    # gather all tool messages the model ever saw, in order; first return plain, second re-anchored
    tool_msgs = [m for call in fm.calls for m in call[0] if m.role == "tool"]
    # de-dup by tool_call_id preserving first appearance order (history grows, so a msg recurs across calls)
    seen, ordered = set(), []
    for m in tool_msgs:
        if m.tool_call_id not in seen:
            seen.add(m.tool_call_id)
            ordered.append(m)
    assert len(ordered) == 2
    assert "[objective: do X]" not in ordered[0].content    # 1st tool return: not appended
    assert "[objective: do X]" in ordered[1].content        # 2nd tool return: appended


def test_reinforce_objective_every_zero_raises():
    with pytest.raises(ValueError):
        reinforce_objective("do X", every=0)


# --- B2: tool_output_budget --------------------------------------------------

def test_truncate_helper_middle_truncates():
    s = "A" * 5000
    out = _truncate_tool_output(s, 100)
    assert "...[truncated 4900 chars]..." in out
    assert out.startswith("A" * 50)          # first half slice
    assert out.endswith("A" * 50)            # last half slice
    assert len(out) < len(s)


def test_truncate_helper_noop_when_under_budget_or_zero():
    s = "short"
    assert _truncate_tool_output(s, 100) == "short"   # under budget → identical
    assert _truncate_tool_output(s, 0) == "short"     # budget 0 → no-op (disabled)
    assert _truncate_tool_output("X" * 50, 50) == "X" * 50   # exactly at budget → identical


async def test_tool_output_budget_truncates_via_agent_loop():
    # the long tool result, run with a small budget on the Agent, lands truncated in what the model sees.
    fm = _one_tool_call_then_done("big", {"n": 5000})
    agent = Agent(model=fm, tools=[big], tool_output_budget=100)
    result = await agent.run("go")
    assert result.stop_reason == StopReason.END_TURN
    tool_msgs = [m for call in fm.calls for m in call[0] if m.role == "tool"]
    assert tool_msgs, "model should have seen a tool result"
    content = tool_msgs[0].content
    assert "...[truncated 4900 chars]..." in content
    assert content.startswith("A" * 50) and content.endswith("A" * 50)
    assert len(content) < 5000


async def test_tool_output_budget_default_is_byte_identical():
    # default (None) → the tool result passes through unchanged.
    fm = _one_tool_call_then_done("ping", {"value": "x"})
    agent = Agent(model=fm, tools=[ping])          # no tool_output_budget
    await agent.run("go")
    tool_msgs = [m for call in fm.calls for m in call[0] if m.role == "tool"]
    assert any(m.content == "pong" for m in tool_msgs)   # exactly the raw result, no marker
    assert all("...[truncated" not in m.content for m in tool_msgs)


async def test_tool_output_budget_via_runcontext_through_run_loop():
    # prove the LOOP applies it (not just Agent) by threading a RunContext with the field set.
    from verso.core.loop import run_loop
    ctx = RunContext(trace_id="t", tool_output_budget=100)
    fm = _one_tool_call_then_done("big", {"n": 5000})
    result = await run_loop(fm, [big], "go", ctx=ctx)
    assert result.stop_reason == StopReason.END_TURN
    tool_msgs = [m for m in ctx.messages if m.role == "tool"]
    assert tool_msgs and "...[truncated 4900 chars]..." in tool_msgs[0].content


# --- stream parity -----------------------------------------------------------

async def test_tool_output_budget_truncates_under_stream():
    ctx = RunContext(trace_id="s", store=None, tool_output_budget=100)
    fm = _one_tool_call_then_done("big", {"n": 5000})
    evs = [ev async for ev in run_stream(fm, [big], "go", ctx=ctx)]
    result_ev = next(e for e in evs if e.type is EventType.TOOL_RESULT)
    assert "...[truncated 4900 chars]..." in result_ev.content
    assert result_ev.content.startswith("A" * 50) and result_ev.content.endswith("A" * 50)
    # and the history the model would see next is truncated too
    tool_hist = [m for m in ctx.messages if m.role == "tool"]
    assert tool_hist and "...[truncated 4900 chars]..." in tool_hist[0].content


async def test_stream_no_budget_is_byte_identical():
    ctx = RunContext(trace_id="s", store=None)     # no tool_output_budget
    fm = _one_tool_call_then_done("big", {"n": 200})
    evs = [ev async for ev in run_stream(fm, [big], "go", ctx=ctx)]
    result_ev = next(e for e in evs if e.type is EventType.TOOL_RESULT)
    assert result_ev.content == "A" * 200          # full, untouched
    assert "...[truncated" not in result_ev.content
