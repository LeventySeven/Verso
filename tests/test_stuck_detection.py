# tests/test_stuck_detection.py
from verso.core.loop import run_loop
from verso.core.stuck import StuckThresholds, detect_stuck
from verso.model.fake import FakeModel
from verso.model.base import Message, ModelResponse, ToolCall
from verso.tools.tool import tool
from verso.types import StopReason, Usage


@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b


def _asst(i):
    return ModelResponse(text="", tool_calls=[ToolCall(id=f"t{i}", name="add", arguments={"a": 1, "b": 1})], usage=Usage())


async def test_repeated_identical_calls_stop_as_stuck():
    # the model loops the SAME (tool, args) forever; default detector (threshold 4) fires before max_steps=25
    fm = FakeModel([_asst(i) for i in range(12)])
    result = await run_loop(fm, [add], "loop", max_steps=25)
    assert result.stop_reason is StopReason.STUCK
    assert result.steps < 25                      # caught early, did NOT burn the whole budget


async def test_stuck_detection_can_be_disabled():
    fm = FakeModel([_asst(i) for i in range(12)])
    result = await run_loop(fm, [add], "loop", max_steps=5, stuck_thresholds=None)
    assert result.stop_reason is StopReason.MAX_STEPS    # detector off -> runs to the cap as before


async def test_short_legitimate_run_is_byte_identical():
    # a real 2-step run (tool then answer) must be untouched by the (default-on) detector
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text="3", tool_calls=[], usage=Usage()),
    ])
    result = await run_loop(fm, [add], "add", max_steps=25)
    assert result.output == "3" and result.stop_reason is StopReason.END_TURN


async def test_stuck_is_wired_through_agent_run_and_stream():
    from verso import Agent
    from verso.stream.events import EventType
    r = await Agent(model=FakeModel([_asst(i) for i in range(12)]), tools=[add], max_steps=25).run("loop")
    assert r.stop_reason is StopReason.STUCK
    evs = [ev async for ev in Agent(model=FakeModel([_asst(i) for i in range(12)]), tools=[add], max_steps=25).stream("loop")]
    assert evs[-1].type is EventType.DONE and evs[-1].result.stop_reason is StopReason.STUCK


def test_detect_stuck_is_pure_and_conservative():
    t = StuckThresholds()
    # 3 identical calls is below threshold 4 -> not stuck
    h3 = [Message(role="assistant", tool_calls=[ToolCall(id=str(i), name="x", arguments={"a": 1})]) for i in range(3)]
    assert detect_stuck(h3, t) is None
    # 4 identical -> stuck
    h4 = [Message(role="assistant", tool_calls=[ToolCall(id=str(i), name="x", arguments={"a": 1})]) for i in range(4)]
    assert detect_stuck(h4, t) is not None
    # 4 DIFFERENT calls -> not stuck (varying args = progress)
    hv = [Message(role="assistant", tool_calls=[ToolCall(id=str(i), name="x", arguments={"a": i})]) for i in range(4)]
    assert detect_stuck(hv, t) is None
    # 4 consecutive tool errors -> stuck
    he = [Message(role="tool", name="x", tool_call_id=str(i), content="Error: boom") for i in range(4)]
    assert detect_stuck(he, t) is not None
