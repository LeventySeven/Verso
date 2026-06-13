from verso import Agent, tool
from verso.safety.hooks import Hooks, PermissionDecision
from verso.stream.events import EventType
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def ping(to: str) -> str:
    "Ping."
    return f"pong {to}"


def _fm():
    return FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="ping", arguments={"to": "x"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])


async def test_ctx_aware_hooks_receive_deps_and_trace_id_on_run():
    seen = {}
    hooks = Hooks(
        pre_tool=[lambda call, ctx: seen.update(uid=ctx.deps["uid"]) or PermissionDecision.ALLOW],
        on_stop=[lambda result, ctx: seen.update(trace=ctx.trace_id)],
    )
    r = await Agent(model=_fm(), tools=[ping], hooks=hooks, deps={"uid": "u-7"}).run("go")
    assert r.output == "done"
    assert seen["uid"] == "u-7"           # ctx.deps injected into a pre_tool hook
    assert seen["trace"]                  # ctx.trace_id injected into an on_stop hook


async def test_ctx_aware_hooks_work_on_the_stream_path_too():
    seen = {}
    hooks = Hooks(post_tool=[lambda call, content, ctx: seen.update(uid=ctx.deps["uid"]) or content])
    events = [ev async for ev in Agent(model=_fm(), tools=[ping], hooks=hooks, deps={"uid": "u-9"}).stream("go")]
    assert events[-1].type == EventType.DONE
    assert seen["uid"] == "u-9"           # ctx reaches hooks on the stream path too (run/stream parity)


async def test_ctx_less_hooks_are_unchanged_back_compat():
    fired = []
    hooks = Hooks(pre_tool=[lambda call: fired.append(call[0]) or PermissionDecision.ALLOW],
                  on_stop=[lambda result: fired.append(result.stop_reason.value)])
    r = await Agent(model=_fm(), tools=[ping], hooks=hooks).run("go")   # no deps; ctx-less hooks
    assert r.output == "done" and fired == ["ping", "end_turn"]
