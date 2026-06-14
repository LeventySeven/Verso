from verso import Agent, tool
from verso.safety.hooks import Hooks
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason


@tool
def step_tool(value: str) -> str:
    "A tool."
    return "ok"


async def test_should_continue_stops_the_loop_early():
    # FakeModel would loop forever calling the tool; should_continue caps it after 2 steps
    fm = FakeModel([ModelResponse(text="", tool_calls=[ToolCall(id=str(i), name="step_tool", arguments={"value": "x"})], usage=Usage()) for i in range(10)])
    checks = {"n": 0}
    def keep_going(bundle):
        checks["n"] += 1
        return checks["n"] <= 2                    # allow steps 1 and 2, stop at the 3rd check
    r = await Agent(model=fm, tools=[step_tool], hooks=Hooks(should_continue=keep_going)).run("go")
    assert r.stop_reason == StopReason.END_TURN     # stopped by the predicate, not MAX_STEPS(25)
    assert r.steps == 2                             # two steps ran before the stop


async def test_no_should_continue_is_unchanged():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="step_tool", arguments={"value": "x"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    r = await Agent(model=fm, tools=[step_tool]).run("go")
    assert r.output == "done" and r.stop_reason == StopReason.END_TURN   # byte-identical to today
