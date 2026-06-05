# verso/tools/coerce.py
from __future__ import annotations
from typing import TypeVar

from pydantic import TypeAdapter, ValidationError

from verso.tools.jsonish import JsonishError, parse

T = TypeVar("T")


class CoercionError(ValueError):
    """Raised when text cannot be parsed and validated into the target type."""


class StructuredOutputError(ValueError):
    """Raised when an agent cannot produce the requested output_type (after reask)."""


def coerce(text: str, target: type[T]) -> T:
    """Parse messy text (jsonish) then validate it into `target` via Pydantic."""
    try:
        value = parse(text)
    except JsonishError as e:
        raise CoercionError(str(e)) from e
    try:
        return TypeAdapter(target).validate_python(value)
    except ValidationError as e:
        name = getattr(target, "__name__", repr(target))
        raise CoercionError(f"value did not match {name}: {e}") from e
