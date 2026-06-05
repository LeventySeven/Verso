# verso/tools/tool.py
from __future__ import annotations
import inspect
import typing
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import create_model


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]   # JSON Schema for the arguments object
    fn: Callable[..., Any]
    args_model: type              # pydantic model used to validate arguments at dispatch


def _build_args_model(fn: Callable[..., Any]) -> type:
    sig = inspect.signature(fn)
    hints = typing.get_type_hints(fn)
    fields: dict[str, Any] = {}
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        annotation = hints.get(pname, str)
        default = ... if param.default is inspect.Parameter.empty else param.default
        fields[pname] = (annotation, default)
    return create_model(f"{fn.__name__}_Args", **fields)


def tool(fn: Callable[..., Any] | None = None, *, name: str | None = None,
         description: str | None = None) -> Tool | Callable[[Callable[..., Any]], Tool]:
    def make(f: Callable[..., Any]) -> Tool:
        args_model = _build_args_model(f)
        schema = args_model.model_json_schema()
        schema.pop("title", None)
        return Tool(
            name=name or f.__name__,
            description=(description or inspect.getdoc(f) or "").strip(),
            parameters=schema,
            fn=f,
            args_model=args_model,
        )

    return make(fn) if fn is not None else make
