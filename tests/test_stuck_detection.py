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


def test_detect_stuck_requires_unchanged_result():
    t = StuckThresholds()
    same, poll = [], []
    for i in range(4):
        same.append(Message(role="assistant", tool_calls=[ToolCall(id=f"a{i}", name="x", arguments={"q": 1})]))
        same.append(Message(role="tool", tool_call_id=f"a{i}", name="x", content="identical"))
        poll.append(Message(role="assistant", tool_calls=[ToolCall(id=f"b{i}", name="x", arguments={"q": 1})]))
        poll.append(Message(role="tool", tool_call_id=f"b{i}", name="x", content=f"status-{i}"))   # changes
    assert detect_stuck(same, t) is not None      # same call + same result = doom-loop
    assert detect_stuck(poll, t) is None          # same call + CHANGING result = progress (polling)


async def test_polling_with_changing_results_is_not_stuck():
    # a poll(id) tool whose result changes each call is progress, not a doom-loop — must NOT trip STUCK
    state = {"n": 0}

    @tool
    def poll(id: str) -> str:
        "Poll a job status."
        state["n"] += 1
        return f"status-{state['n']}"

    fm = FakeModel([ModelResponse(text="", tool_calls=[ToolCall(id=f"p{i}", name="poll", arguments={"id": "x"})], usage=Usage())
                    for i in range(6)] + [ModelResponse(text="ready", tool_calls=[], usage=Usage())])
    r = await run_loop(fm, [poll], "poll until ready", max_steps=25)
    assert r.stop_reason is StopReason.END_TURN    # changing results = progress, never STUCK


# --- alternating (period-2) doom-loop: the A-B-A-B cycle the period-1 detector misses ---

def _cycle(n, *, change_results):
    """n full A-B cycles: tool x then tool y, each with a (stable | changing) result."""
    h = []
    for i in range(n):
        h.append(Message(role="assistant", tool_calls=[ToolCall(id=f"a{i}", name="x", arguments={"k": 1})]))
        h.append(Message(role="tool", tool_call_id=f"a{i}", name="x", content=f"ra{i}" if change_results else "ra"))
        h.append(Message(role="assistant", tool_calls=[ToolCall(id=f"b{i}", name="y", arguments={"k": 2})]))
        h.append(Message(role="tool", tool_call_id=f"b{i}", name="y", content=f"rb{i}" if change_results else "rb"))
    return h


def test_alternating_cycle_with_stable_results_is_stuck():
    t = StuckThresholds()                                  # default alternating threshold (3 cycles)
    assert detect_stuck(_cycle(3, change_results=False), t) is not None


def test_alternating_cycle_with_changing_results_is_not_stuck():
    t = StuckThresholds()
    assert detect_stuck(_cycle(3, change_results=True), t) is None    # changing results = progress


def test_short_alternation_is_below_threshold():
    t = StuckThresholds()
    assert detect_stuck(_cycle(2, change_results=False), t) is None   # 2 cycles < threshold 3


def test_alternating_can_be_disabled_by_threshold():
    t = StuckThresholds(alternating=0)
    assert detect_stuck(_cycle(4, change_results=False), t) is None   # 0 disables the period-2 check


async def test_alternating_loop_stops_as_stuck_in_the_real_loop():
    # the model oscillates between two no-op tools with identical results forever
    @tool
    def x(k: int) -> str:
        "noop x"
        return "ra"

    @tool
    def y(k: int) -> str:
        "noop y"
        return "rb"

    seq = []
    for i in range(8):
        seq.append(ModelResponse(text="", tool_calls=[ToolCall(id=f"a{i}", name="x", arguments={"k": 1})], usage=Usage()))
        seq.append(ModelResponse(text="", tool_calls=[ToolCall(id=f"b{i}", name="y", arguments={"k": 2})], usage=Usage()))
    r = await run_loop(FakeModel(seq), [x, y], "oscillate", max_steps=25)
    assert r.stop_reason is StopReason.STUCK and r.steps < 25
