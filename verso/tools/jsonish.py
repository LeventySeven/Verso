# verso/tools/jsonish.py
from __future__ import annotations
import json
import re
from typing import Any, Iterator

_FENCE = re.compile(r"```(?:json|JSON)?\s*\n?(.*?)```", re.DOTALL)


class JsonishError(ValueError):
    """Raised when no JSON value can be recovered from the input text."""


def _first_balanced(text: str) -> str | None:
    """Return the first balanced {...} or [...] substring, respecting strings/escapes."""
    start: int | None = None
    opener = closer = ""
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if start is None:
            if ch in "{[":
                start, opener, closer, depth = i, ch, ("}" if ch == "{" else "]"), 1
            continue
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _candidates(text: str) -> Iterator[str]:
    yield text.strip()
    m = _FENCE.search(text)
    if m:
        yield m.group(1).strip()
    balanced = _first_balanced(text)
    if balanced:
        yield balanced


def _light_fix(s: str) -> str:
    s = re.sub(r",(\s*[}\]])", r"\1", s)      # trailing commas
    s = re.sub(r"\bTrue\b", "true", s)        # python -> json literals
    s = re.sub(r"\bFalse\b", "false", s)
    s = re.sub(r"\bNone\b", "null", s)
    return s


def parse(text: str) -> Any:
    """Recover a JSON value from messy LLM output via an ordered waterfall.

    1. strict json  2. ```json fenced block  3. first balanced {...}/[...]  4. light fixes.
    """
    if not isinstance(text, str):
        raise JsonishError("jsonish.parse expects a string")
    seen: list[str] = []
    for cand in _candidates(text):
        if not cand or cand in seen:
            continue
        seen.append(cand)
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(_light_fix(cand))
        except json.JSONDecodeError:
            pass
    raise JsonishError(f"could not parse JSON from text: {text[:200]!r}")
