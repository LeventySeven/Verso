# tests/test_hook_fail_open.py
# A permission hook that returns None is INDISTINGUISHABLE at runtime from "I have no opinion"
# and from "I meant to DENY but fell off the end of a branch". Verso resolves that ambiguity as
# ALLOW, which is the fail-open class audited in teardowns/AGENT_SECURITY_DEFENSE.md:26
# ("five silent fail-open paths across four security codebases, none of which alarms").
#
# The current semantic is DELIBERATE (it mirrors post_tool's None=passthrough) so it is pinned
# here rather than changed — changing it would break rule 1. `strict=True` is the opt-in that
# turns the ambiguity into a loud failure for callers who want it.
import pytest

from verso.safety.hooks import Hooks, PermissionDecision


async def test_pre_tool_returning_none_allows_by_default():
    # CHARACTERIZATION: pins today's behavior so it can never drift silently.
    h = Hooks(pre_tool=[lambda call: None])
    assert await h.run_pre_tool(("rm_rf", {"path": "/"})) == PermissionDecision.ALLOW


async def test_strict_turns_a_none_permission_decision_into_a_loud_error():
    h = Hooks(pre_tool=[lambda call: None], strict=True)
    with pytest.raises(ValueError, match="pre_tool"):
        await h.run_pre_tool(("rm_rf", {"path": "/"}))


async def test_strict_still_allows_an_explicit_allow():
    h = Hooks(pre_tool=[lambda call: PermissionDecision.ALLOW], strict=True)
    assert await h.run_pre_tool(("ls", {})) == PermissionDecision.ALLOW


async def test_strict_defaults_off_so_existing_hooks_are_byte_identical():
    assert Hooks().strict is False
    h = Hooks(pre_tool=[lambda call: None, lambda call: PermissionDecision.DENY])
    assert await h.run_pre_tool(("x", {})) == PermissionDecision.DENY


async def test_strict_also_rejects_a_truthy_non_decision():
    # `True` is not a PermissionDecision, but `True != ALLOW` makes the default path treat it as a
    # deny-ish verdict — a junk return silently becomes policy. strict makes it loud.
    h = Hooks(pre_tool=[lambda call: True], strict=True)
    with pytest.raises(ValueError, match="pre_tool"):
        await h.run_pre_tool(("rm_rf", {}), None)


async def test_strict_accepts_the_bare_string_forms():
    # PermissionDecision is a str-Enum; "deny" is a legitimate, equal-comparing return today.
    h = Hooks(pre_tool=[lambda call: "deny"], strict=True)
    assert await h.run_pre_tool(("rm_rf", {})) == PermissionDecision.DENY
