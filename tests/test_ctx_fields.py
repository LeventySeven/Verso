from verso import Agent, tool
from verso.stream.events import EventType
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


def _fm():
    return FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="probe", arguments={})],
                      usage=Usage(input_tokens=10, output_tokens=5)),
        ModelResponse(text="done", tool_calls=[], usage=Usage(input_tokens=3, output_tokens=2)),
    ])


async def test_ctx_exposes_usage_messages_model_step_on_run():
    seen = {}
    @tool
    def probe(ctx) -> str:
        "Read run state from ctx."
        seen.update(step=ctx.step, inp=ctx.usage.input_tokens, model=ctx.model, nmsgs=len(ctx.messages))
        return "ok"
    await Agent(model=_fm(), tools=[probe]).run("go")          # model_id defaults "" for FakeModel
    assert seen["step"] == 1
    assert seen["inp"] == 10                                   # cumulative usage at the tool's turn
    assert seen["nmsgs"] >= 2                                  # at least [user, assistant-with-toolcall]
    assert "model" in seen                                     # present (empty string for FakeModel is fine)


async def test_ctx_fields_on_stream_path_too():
    seen = {}
    @tool
    def probe(ctx) -> str:
        "Read run state from ctx."
        seen.update(inp=ctx.usage.input_tokens, step=ctx.step)
        return "ok"
    events = [ev async for ev in Agent(model=_fm(), tools=[probe]).stream("go")]
    assert events[-1].type == EventType.DONE
    assert seen["inp"] == 10 and seen["step"] == 1


async def test_ctx_less_tool_unaffected_back_compat():
    @tool
    def plain(x: int) -> int:
        "Add one."
        return x + 1
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="plain", arguments={"x": 1})], usage=Usage()),
        ModelResponse(text="2", tool_calls=[], usage=Usage()),
    ])
    r = await Agent(model=fm, tools=[plain]).run("go")
    assert r.output == "2"                                     # ctx-less tool path unchanged
