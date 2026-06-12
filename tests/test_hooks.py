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
