# verso/safety/hooks.py
from __future__ import annotations
import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class PermissionDecision(str, Enum):
    ALLOW = "allow"     # run the tool
    DENY = "deny"       # skip; feed the model a denial it can react to
    ASK = "ask"         # route to a sync `ask` callback (Phase 1); durable HITL is Phase 2
    DEFER = "defer"     # skip for now (treated as deny-this-turn in Phase 1)


ToolCallView = tuple[str, dict]   # (tool_name, arguments)


@dataclass
class VerificationOutcome:
    """What an `on_stop` hook may return to VETO a *natural* termination (END_TURN / DONE):
    a maker-checker on the done-point. `passed=False` makes the loop append `detail` as feedback
    and re-drive the model (bounded by `Hooks.max_verify_retries`); `passed=True` (or returning
    None, as every existing hook does) lets the run terminate. Hooks that return None keep
    `run_on_stop` returning None → the loop is byte-identical."""
    passed: bool
    detail: str = ""


async def _maybe_await(v):
    return await v if inspect.isawaitable(v) else v


def _wants_ctx(fn) -> bool:
    try:
        return "ctx" in inspect.signature(fn).parameters
    except (TypeError, ValueError):   # builtins / C callables expose no signature
        return False


def _is_decision(d) -> bool:
    # PermissionDecision is a str-Enum, so the bare strings ("allow"/"deny"/...) are legitimate and
    # compare equal to the members — accept those, reject everything else (None, True, 0, "yes").
    # Only consulted under `strict`; the default path is untouched.
    try:
        PermissionDecision(d)
        return True
    except (ValueError, KeyError, TypeError):
        return False


async def _fire(hook, args, ctx):
    # inject the RunContext only into hooks that declare a `ctx` parameter; ctx-less hooks are
    # called exactly as before (byte-identical back-compat) — same convention as tool ctx-injection.
    call = hook(*args, ctx=ctx) if (ctx is not None and _wants_ctx(hook)) else hook(*args)
    return await _maybe_await(call)


@dataclass
class Hooks:
    """The 5-stage lifecycle hooks — the extensibility mechanism (not core-loop edits).
    Every stage is a list of (sync or async) callables; all default empty = no-op. The loop calls
    the `run_*` helpers, so hook authors never touch the loop."""
    pre_model: list[Callable[[Any], Any]] = field(default_factory=list)         # (bundle) -> None
    post_model: list[Callable[[Any], Any]] = field(default_factory=list)        # (response) -> None
    pre_tool: list[Callable[[ToolCallView], Any]] = field(default_factory=list)  # (call) -> PermissionDecision
    post_tool: list[Callable[[ToolCallView, str], Any]] = field(default_factory=list)  # (call, content) -> content
    on_stop: list[Callable[[Any], Any]] = field(default_factory=list)           # (result) -> None | VerificationOutcome
    ask: Callable[[ToolCallView], bool] | None = None                           # ASK resolver (Phase 1)
    should_continue: Callable[..., Any] | None = None                           # (bundle[, ctx]) -> bool; stop the loop when False
    max_verify_retries: int = 1                                                 # re-drive budget when an on_stop hook vetoes a natural stop (1 = at most one re-drive)
    strict: bool = False                                                        # opt-in: a pre_tool hook returning anything that is not a PermissionDecision raises instead of falling through

    async def run_pre_model(self, bundle, ctx=None) -> None:
        for h in self.pre_model:
            await _fire(h, (bundle,), ctx)

    async def run_post_model(self, response, ctx=None) -> None:
        for h in self.post_model:
            await _fire(h, (response,), ctx)

    async def run_pre_tool(self, call: ToolCallView, ctx=None) -> PermissionDecision:
        for h in self.pre_tool:
            d = await _fire(h, (call,), ctx)
            # A hook returning None is ambiguous: it can mean "no opinion, let another hook decide"
            # (the documented convention, mirroring post_tool's None=passthrough) or "I meant to DENY
            # and fell off the end of a branch" — the silent fail-open audited across four shipped
            # security codebases. Resolving it as ALLOW is the shipped semantic and stays the default,
            # because flipping it would deny for every hook that legitimately abstains (rule 1).
            # `strict=True` is for callers who would rather crash than discover the ambiguity in prod.
            if self.strict and not _is_decision(d):
                name = getattr(h, "__name__", repr(h))
                raise ValueError(
                    f"strict Hooks: pre_tool hook {name!r} returned {d!r} for tool {call[0]!r}; "
                    "return an explicit PermissionDecision (ALLOW to abstain)."
                )
            if d and d != PermissionDecision.ALLOW:   # first non-allow wins (most restrictive)
                return d
        return PermissionDecision.ALLOW

    async def run_post_tool(self, call: ToolCallView, content: str, ctx=None) -> str:
        for h in self.post_tool:                      # reinforcement channel: may rewrite the result
            out = await _fire(h, (call, content), ctx)
            if out is not None:                       # None => passthrough; "" => deliberate redaction (don't fail open)
                content = out
        return content

    async def run_on_stop(self, result, ctx=None) -> "VerificationOutcome | None":
        # Fire every on_stop hook (ctx-injection + sync/async still via _fire). If any returns a
        # vetoing VerificationOutcome (passed=False), return the FIRST one so the loop can re-drive;
        # else return None. All existing hooks return None → run_on_stop returns None → byte-identical.
        veto = None
        for h in self.on_stop:
            out = await _fire(h, (result,), ctx)
            if veto is None and isinstance(out, VerificationOutcome) and not out.passed:
                veto = out
        return veto

    async def run_should_continue(self, bundle, ctx=None) -> bool:
        # unset → always continue (byte-identical no-op). Routed through _fire so a predicate that
        # declares `ctx` can steer on live run state (ctx.usage / ctx.deps) — e.g. stop on a token budget.
        if self.should_continue is None:
            return True
        return bool(await _fire(self.should_continue, (bundle,), ctx))
