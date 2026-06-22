# tests/test_tool_max_attempts.py
# The per-tool retry budget governs whether a tool's `Retry` is converted into a *'Retry:' invitation*
# (encouraging the model to call again) vs a terminal budget error. A non-idempotent tool gets 0 retries:
# its first Retry is the budget error, never an invitation — so the framework never invites re-running a
# side effect. (args vary per call + stuck disabled, so we isolate the budget, not the stuck-detector.)
from verso import Agent, tool
from verso.safety.hooks import Hooks
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.errors import Retry
from verso.types import Usage


def _calls(name, n):
    return [ModelResponse(text="", tool_calls=[ToolCall(id=f"{name}{i}", name=name, arguments={"i": i})], usage=Usage())
            for i in range(n)] + [ModelResponse(text="stop", tool_calls=[], usage=Usage())]


def _capture():
    seen: list[str] = []
    return seen, Hooks(post_tool=[lambda call, content: seen.append(content) or content])


async def test_non_idempotent_tool_gets_no_retry_invitation():
    @tool(idempotent=False)
    def charge(i: int) -> str:
        "Side-effecting; raises Retry."
        raise Retry("bad amount")
    seen, hooks = _capture()
    await Agent(model=FakeModel(_calls("charge", 3)), tools=[charge], hooks=hooks, stuck_thresholds=None).run("go")
    assert sum(1 for c in seen if c.startswith("Retry:")) == 0          # never invited to re-run a side effect
    assert any("exceeded its retry budget (0)" in c for c in seen)


async def test_idempotent_tool_keeps_default_retry_budget():
    @tool                                  # idempotent=True (default)
    def search(i: int) -> str:
        "Safe read; raises Retry."
        raise Retry("refine")
    seen, hooks = _capture()
    await Agent(model=FakeModel(_calls("search", 5)), tools=[search], hooks=hooks,
                max_tool_retries=2, stuck_thresholds=None).run("go")
    assert sum(1 for c in seen if c.startswith("Retry:")) == 2          # byte-identical to today's default
    assert any("exceeded its retry budget (2)" in c for c in seen)


async def test_explicit_max_attempts_overrides():
    @tool(max_attempts=2)                  # 2 dispatches -> exactly 1 retry invitation, ignoring max_tool_retries
    def thing(i: int) -> str:
        "Allow exactly one retry."
        raise Retry("again")
    seen, hooks = _capture()
    await Agent(model=FakeModel(_calls("thing", 5)), tools=[thing], hooks=hooks,
                max_tool_retries=5, stuck_thresholds=None).run("go")
    assert sum(1 for c in seen if c.startswith("Retry:")) == 1
    assert any("exceeded its retry budget (1)" in c for c in seen)
