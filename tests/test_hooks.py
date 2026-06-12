# tests/test_hooks.py
from verso.safety.hooks import Hooks, PermissionDecision


async def test_hooks_default_to_noop_and_compose():
    fired = []
    h = Hooks(
        pre_model=[lambda bundle: fired.append("pre_model")],
        post_tool=[lambda call, content: fired.append("post_tool") or content],
    )
    await h.run_pre_model("BUNDLE")
    out = await h.run_post_tool(("add", {}), "3")
    assert fired == ["pre_model", "post_tool"]
    assert out == "3"                               # default: content passes through unchanged


async def test_pre_tool_decision_defaults_allow_and_first_non_allow_wins():
    h = Hooks(pre_tool=[lambda call: PermissionDecision.ALLOW,
                        lambda call: PermissionDecision.DENY])
    assert await h.run_pre_tool(("send_email", {})) == PermissionDecision.DENY
    assert await Hooks().run_pre_tool(("x", {})) == PermissionDecision.ALLOW   # no hooks ⇒ allow


# --- appended to tests/test_hooks.py ---
from verso import Agent, tool  # noqa: E402
from verso.model.fake import FakeModel  # noqa: E402
from verso.model.base import ModelResponse, ToolCall  # noqa: E402
from verso.types import Usage  # noqa: E402


@tool
def send_email(to: str) -> str:
    "Send an email."
    return f"sent to {to}"


def _agent(hooks):
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="send_email", arguments={"to": "x@y.z"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    return Agent(model=fm, tools=[send_email], hooks=hooks)


async def test_deny_skips_the_tool_and_loop_continues():
    seen = {}
    h = Hooks(pre_tool=[lambda call: PermissionDecision.DENY],
              post_tool=[lambda call, content: seen.setdefault("content", content) or content])
    result = await _agent(h).run("email x")
    assert result.output == "done"                       # loop continued past the denial
    # the model sees a legible non-execution message (decision.value is "deny", NOT "denied"):
    assert "deny" in seen["content"].lower() and "did not run" in seen["content"].lower()
    assert "sent to" not in seen["content"]              # the tool did NOT run


async def test_post_tool_reinforcement_sees_real_result_on_allow_path():
    seen = {}
    h = Hooks(post_tool=[lambda call, content: seen.setdefault("content", content) or f"{content}  [objective: finish]"])
    result = await _agent(h).run("email x")
    assert result.output == "done"
    assert seen["content"] == "sent to x@y.z"            # post_tool fired on the ALLOW path with the real result


async def test_all_five_points_fire_in_order():
    order = []
    h = Hooks(
        pre_model=[lambda b: order.append("pre_model")],
        post_model=[lambda r: order.append("post_model")],
        pre_tool=[lambda c: order.append("pre_tool") or PermissionDecision.ALLOW],
        post_tool=[lambda c, content: order.append("post_tool") or content],
        on_stop=[lambda r: order.append("on_stop")],
    )
    await _agent(h).run("email x")
    # turn 1: pre_model, post_model, pre_tool, post_tool ; turn 2: pre_model, post_model ; then on_stop
    assert order[:4] == ["pre_model", "post_model", "pre_tool", "post_tool"]
    assert order[-1] == "on_stop"
