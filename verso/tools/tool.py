# verso/tools/tool.py
from __future__ import annotations
import inspect
import typing
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import ConfigDict, create_model


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]   # JSON Schema for the arguments object
    fn: Callable[..., Any]
    args_model: type              # pydantic model used to validate arguments at dispatch
    wants_ctx: bool = False       # True if the tool declares a `ctx` param → RunContext is injected at dispatch
    privileged: bool = False      # sensitive/side-effecting (send_email, refund, write_file). A "read"-tier
                                  # Agent drops privileged tools at construction → they're structurally absent,
                                  # so untrusted input can't even request one (no call-time decision to reach).
    idempotent: bool = True       # safe to auto-retry on a Retry signal? False (side-effecting) → no auto-retry
                                  # (max_attempts=1): re-running a charge/email is a correctness bug. Orthogonal
                                  # to `privileged` (trust boundary). Byte-identical when True (the default).
    max_attempts: int | None = None   # explicit dispatch cap, overrides idempotent/max_tool_retries when set
    timeout_seconds: float | None = None  # wall-clock cap for an async tool body (asyncio.wait_for); None = no cap


def _build_args_model(fn: Callable[..., Any]) -> type:
    sig = inspect.signature(fn)
    hints = typing.get_type_hints(fn)
    fields: dict[str, Any] = {}
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls", "ctx"):
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue  # *args/**kwargs can't become typed JSON-schema fields
        annotation = hints.get(pname, str)
        default = ... if param.default is inspect.Parameter.empty else param.default
        fields[pname] = (annotation, default)
    return create_model(f"{fn.__name__}_Args", **fields)


def tool(fn: Callable[..., Any] | None = None, *, name: str | None = None,
         description: str | None = None, privileged: bool = False,
         idempotent: bool = True, max_attempts: int | None = None,
         timeout_seconds: float | None = None
         ) -> Tool | Callable[[Callable[..., Any]], Tool]:
    def make(f: Callable[..., Any]) -> Tool:
        args_model = _build_args_model(f)
        schema = args_model.model_json_schema()
        schema.pop("title", None)
        wants_ctx = "ctx" in inspect.signature(f).parameters
        return Tool(
            name=name or f.__name__,
            description=(description or inspect.getdoc(f) or "").strip(),
            parameters=schema,
            fn=f,
            args_model=args_model,
            wants_ctx=wants_ctx,
            privileged=privileged,
            idempotent=idempotent,
            max_attempts=max_attempts,
            timeout_seconds=timeout_seconds,
        )

    return make(fn) if fn is not None else make


def tool_from_schema(name: str, description: str, parameters: dict,
                     fn: Callable[..., Any], *, wants_ctx: bool = False,
                     privileged: bool = False, idempotent: bool = True,
                     max_attempts: int | None = None, timeout_seconds: float | None = None) -> Tool:
    """Register a tool from a RAW JSON Schema (MCP / OpenAPI / dynamically-generated) — the escape hatch
    for when you already have a schema and don't want signature introspection. Args are passed through to
    `fn` (permissive validation; the caller owns the schema). `@tool` stays the ergonomic default."""
    args_model = create_model(f"{name}_Args", __config__=ConfigDict(extra="allow"))
    return Tool(name=name, description=description, parameters=parameters, fn=fn,
                args_model=args_model, wants_ctx=wants_ctx, privileged=privileged,
                idempotent=idempotent, max_attempts=max_attempts, timeout_seconds=timeout_seconds)
