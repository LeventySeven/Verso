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


async def _maybe_await(v):
    return await v if inspect.isawaitable(v) else v


def _wants_ctx(fn) -> bool:
    try:
        return "ctx" in inspect.signature(fn).parameters
    except (TypeError, ValueError):   # builtins / C callables expose no signature
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
    on_stop: list[Callable[[Any], Any]] = field(default_factory=list)           # (result) -> None
    ask: Callable[[ToolCallView], bool] | None = None                           # ASK resolver (Phase 1)

    async def run_pre_model(self, bundle, ctx=None) -> None:
        for h in self.pre_model:
            await _fire(h, (bundle,), ctx)

    async def run_post_model(self, response, ctx=None) -> None:
        for h in self.post_model:
            await _fire(h, (response,), ctx)

    async def run_pre_tool(self, call: ToolCallView, ctx=None) -> PermissionDecision:
        for h in self.pre_tool:
            d = await _fire(h, (call,), ctx)
            if d and d != PermissionDecision.ALLOW:   # first non-allow wins (most restrictive)
                return d
        return PermissionDecision.ALLOW

    async def run_post_tool(self, call: ToolCallView, content: str, ctx=None) -> str:
        for h in self.post_tool:                      # reinforcement channel: may rewrite the result
            content = await _fire(h, (call, content), ctx) or content
        return content

    async def run_on_stop(self, result, ctx=None) -> None:
        for h in self.on_stop:
            await _fire(h, (result,), ctx)
