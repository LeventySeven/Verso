# Verso Phase 0 — Plan 2: Tools Depth + jsonish

> **✅ SHIPPED** — implemented test-first, independently rechecked-APPROVED, on `main`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `jsonish` parse→coerce waterfall (the one non-composable engine), structured output via `Agent.run(task, output_type=Model)` with a single reask, and the `think`/`done` builtin tools (`done` → explicit `StopReason.DONE`).

**Architecture:** Builds directly on the walking skeleton (`verso/` package, `Model`/`Tool`/loop/`Agent` already exist). `jsonish.parse()` turns messy LLM text into a Python value via a small ordered waterfall; `coerce()` validates that value into a Pydantic type; `Agent.run(output_type=...)` uses `coerce` on the final answer and reasks once on failure. `done` is a builtin tool the loop recognizes by name to terminate with a structured result.

**Tech Stack:** unchanged — Python 3.12 (uv-pinned), Pydantic v2 (`TypeAdapter`), pytest + `FakeModel`. No new dependencies (Instructor composition is a LATER plan).

**Prereq:** Plan 1 (walking skeleton) is merged and green (`uv run pytest` → 25 passed / 1 skipped). All paths below are relative to repo root `~/Desktop/Verso`. Run everything with `uv run`. Commit after every green test.

**Out of scope (deferred — do NOT build here):** provider structured-output mode-map + robust retry engine (compose from Instructor, later plan); BAML typed-Flag cost function + streaming `Partial[T]`; the input-repair ladder for tool *arguments* (separate plan); the full `ToolError{kind,can_retry,...}` envelope (separate plan). Keep `jsonish` to the common-case waterfall.

---

## File Structure

```
verso/
├── types.py            # MODIFY — add StopReason.DONE; add AgentResult.parsed field
├── agent.py            # MODIFY — Agent.run(task, *, output_type=None) + one reask
├── core/loop.py        # MODIFY — recognize the `done` tool → return StopReason.DONE
└── tools/
    ├── builtins.py     # NEW — think, done
    ├── jsonish.py      # NEW — parse() waterfall + JsonishError
    └── coerce.py       # NEW — coerce() + CoercionError + StructuredOutputError
tests/
├── test_builtins.py    # NEW
├── test_loop_done.py   # NEW
├── test_jsonish.py     # NEW
├── test_coerce.py      # NEW
└── test_structured_output.py  # NEW
```

---

## Task 1: `StopReason.DONE` + `think`/`done` builtins

**Files:**
- Modify: `verso/types.py` (add one enum member)
- Create: `verso/tools/builtins.py`
- Test: `tests/test_builtins.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_builtins.py
from verso.tools.builtins import think, done
from verso.tools.tool import Tool
from verso.types import StopReason


def test_think_and_done_are_tools():
    assert isinstance(think, Tool) and think.name == "think"
    assert isinstance(done, Tool) and done.name == "done"
    assert "thought" in think.parameters["properties"]
    assert "result" in done.parameters["properties"]


def test_done_returns_its_result():
    assert done.fn(result="the answer") == "the answer"


def test_stop_reason_done_exists():
    assert StopReason.DONE == "done"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_builtins.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.tools.builtins'`.

- [ ] **Step 3: Add `StopReason.DONE` to `verso/types.py`**

In `verso/types.py`, inside `class StopReason`, add the member right after `END_TURN`:

```python
    END_TURN = "end_turn"      # model returned a final text answer (no tool calls)
    DONE = "done"              # model called the `done` tool to terminate with a result
    MAX_STEPS = "max_steps"    # loop hit the max_steps cap
```

- [ ] **Step 4: Create `verso/tools/builtins.py`**

```python
# verso/tools/builtins.py
from verso.tools.tool import tool


@tool
def think(thought: str) -> str:
    """Record a private reasoning step before acting. Use this to plan; it has no side effects."""
    return "noted"


@tool
def done(result: str) -> str:
    """Signal that the task is complete and return the final result to the user."""
    return result
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_builtins.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add verso/types.py verso/tools/builtins.py tests/test_builtins.py
git commit -m "feat(tools): think/done builtins + StopReason.DONE"
```

---

## Task 2: Loop recognizes `done` → terminate

**Files:**
- Modify: `verso/core/loop.py`
- Test: `tests/test_loop_done.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_loop_done.py
from verso.core.loop import run_loop
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.builtins import done, think
from verso.types import StopReason, Usage


async def test_loop_terminates_on_done_tool():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="d1", name="done", arguments={"result": "final answer"})], usage=Usage(output_tokens=1)),
    ])
    result = await run_loop(fm, [done], "do it")
    assert result.output == "final answer"
    assert result.stop_reason is StopReason.DONE
    assert result.steps == 1


async def test_loop_think_then_done():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="think", arguments={"thought": "plan"})], usage=Usage()),
        ModelResponse(text="", tool_calls=[ToolCall(id="d1", name="done", arguments={"result": "42"})], usage=Usage()),
    ])
    result = await run_loop(fm, [think, done], "compute")
    assert result.output == "42"
    assert result.stop_reason is StopReason.DONE
    assert result.steps == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_loop_done.py -v`
Expected: FAIL — both reach `MAX_STEPS`/`END_TURN` mismatch (the loop doesn't yet special-case `done`). Specifically `assert result.stop_reason is StopReason.DONE` fails.

- [ ] **Step 3: Modify the tool-call loop in `verso/core/loop.py`**

Replace the existing `for tc in resp.tool_calls:` block with this version (adds the `done` short-circuit):

```python
        messages.append(Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls))
        for tc in resp.tool_calls:
            t = tool_map.get(tc.name)
            if t is None:
                content = f"Error: unknown tool '{tc.name}'."
            else:
                result = await dispatch(t, tc.arguments)
                content = _format_result(result.data) if result.ok else f"Error: {result.error}"
                if tc.name == "done" and result.ok:
                    return AgentResult(output=_format_result(result.data),
                                       stop_reason=StopReason.DONE, usage=usage, steps=step)
            messages.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_loop_done.py -v`
Expected: 2 passed.

- [ ] **Step 5: Run the full suite (no regressions)**

Run: `uv run pytest -q`
Expected: all prior tests still pass + the 2 new ones (skeleton's loop/agent tests unaffected — they use no `done` tool).

- [ ] **Step 6: Commit**

```bash
git add verso/core/loop.py tests/test_loop_done.py
git commit -m "feat(core): loop terminates on the done tool (StopReason.DONE)"
```

---

## Task 3: `jsonish.parse()` waterfall

**Files:**
- Create: `verso/tools/jsonish.py`
- Test: `tests/test_jsonish.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_jsonish.py
import pytest
from verso.tools.jsonish import parse, JsonishError


def test_strict_json():
    assert parse('{"a": 1, "b": 2}') == {"a": 1, "b": 2}


def test_json_array():
    assert parse("[1, 2, 3]") == [1, 2, 3]


def test_fenced_json_block():
    text = "Here you go:\n```json\n{\"a\": 1}\n```\nHope that helps!"
    assert parse(text) == {"a": 1}


def test_json_embedded_in_prose():
    text = 'Sure! The result is {"a": 1, "b": 2}. Let me know if you need more.'
    assert parse(text) == {"a": 1, "b": 2}


def test_trailing_comma_is_fixed():
    assert parse('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_python_literals_normalized():
    assert parse('{"ok": True, "bad": False, "x": None}') == {"ok": True, "bad": False, "x": None}


def test_nested_braces_balanced_extraction():
    text = 'prefix {"a": {"b": [1, 2]}, "c": 3} suffix'
    assert parse(text) == {"a": {"b": [1, 2]}, "c": 3}


def test_unparseable_raises():
    with pytest.raises(JsonishError):
        parse("there is absolutely no json here")


def test_non_string_raises():
    with pytest.raises(JsonishError):
        parse(123)  # type: ignore[arg-type]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_jsonish.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.tools.jsonish'`.

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_jsonish.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/tools/jsonish.py tests/test_jsonish.py
git commit -m "feat(tools): jsonish.parse waterfall (strict/fenced/balanced/light-fix)"
```

---

## Task 4: `coerce()` — parse + validate into a type

**Files:**
- Create: `verso/tools/coerce.py`
- Test: `tests/test_coerce.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_coerce.py
import pytest
from pydantic import BaseModel
from verso.tools.coerce import coerce, CoercionError


class Point(BaseModel):
    x: int
    y: int


def test_coerce_clean_json_into_model():
    p = coerce('{"x": 1, "y": 2}', Point)
    assert isinstance(p, Point) and p.x == 1 and p.y == 2


def test_coerce_from_messy_text():
    p = coerce('Here: ```json\n{"x": 3, "y": 4}\n```', Point)
    assert p.x == 3 and p.y == 4


def test_coerce_unparseable_raises_coercion_error():
    with pytest.raises(CoercionError):
        coerce("no json here", Point)


def test_coerce_schema_mismatch_raises_coercion_error():
    with pytest.raises(CoercionError):
        coerce('{"x": "not-an-int", "y": 2}', Point)


def test_coerce_list_type():
    assert coerce("[1, 2, 3]", list[int]) == [1, 2, 3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_coerce.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.tools.coerce'`.

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_coerce.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/tools/coerce.py tests/test_coerce.py
git commit -m "feat(tools): coerce() — jsonish parse + pydantic validate into a type"
```

---

## Task 5: Structured output — `Agent.run(output_type=...)` with one reask

**Files:**
- Modify: `verso/types.py` (add `AgentResult.parsed`)
- Modify: `verso/agent.py` (`output_type` + reask)
- Modify: `verso/__init__.py` (export the new errors)
- Test: `tests/test_structured_output.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_structured_output.py
import pytest
from pydantic import BaseModel
from verso import Agent
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse
from verso.tools.coerce import StructuredOutputError
from verso.types import Usage


class Point(BaseModel):
    x: int
    y: int


async def test_output_type_parses_final_answer():
    fm = FakeModel([ModelResponse(text='{"x": 1, "y": 2}', tool_calls=[], usage=Usage())])
    result = await Agent(model=fm).run("give a point", output_type=Point)
    assert isinstance(result.parsed, Point)
    assert result.parsed.x == 1 and result.parsed.y == 2
    assert result.output == '{"x": 1, "y": 2}'


async def test_output_type_reasks_once_then_succeeds():
    fm = FakeModel([
        ModelResponse(text="sorry, x is five", tool_calls=[], usage=Usage()),       # unparseable
        ModelResponse(text='{"x": 5, "y": 6}', tool_calls=[], usage=Usage()),       # reask answer
    ])
    result = await Agent(model=fm).run("give a point", output_type=Point)
    assert result.parsed == Point(x=5, y=6)
    assert len(fm.calls) == 2  # original + one reask


async def test_output_type_raises_after_failed_reask():
    fm = FakeModel([
        ModelResponse(text="nope", tool_calls=[], usage=Usage()),
        ModelResponse(text="still nope", tool_calls=[], usage=Usage()),
    ])
    with pytest.raises(StructuredOutputError):
        await Agent(model=fm).run("give a point", output_type=Point)


async def test_run_without_output_type_unchanged():
    fm = FakeModel([ModelResponse(text="plain text", tool_calls=[], usage=Usage())])
    result = await Agent(model=fm).run("hi")
    assert result.output == "plain text"
    assert result.parsed is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_structured_output.py -v`
Expected: FAIL — `TypeError: run() got an unexpected keyword argument 'output_type'` (and `parsed` not on AgentResult).

- [ ] **Step 3: Add `parsed` to `AgentResult` in `verso/types.py`**

Change the `AgentResult` dataclass to add a trailing optional field:

```python
@dataclass
class AgentResult:
    output: str
    stop_reason: StopReason
    usage: Usage
    steps: int
    parsed: object | None = None   # set when run(output_type=...) succeeds
```

- [ ] **Step 4: Rewrite `verso/agent.py`**

```python
# verso/agent.py
from __future__ import annotations
from typing import Sequence

from verso.core.loop import run_loop
from verso.model.base import Model
from verso.tools.coerce import CoercionError, StructuredOutputError, coerce
from verso.tools.tool import Tool
from verso.types import AgentResult


class Agent:
    def __init__(self, model: Model, tools: Sequence[Tool] = (), *,
                 instructions: str | None = None, max_steps: int = 25):
        self.model = model
        self.tools = list(tools)
        self.instructions = instructions
        self.max_steps = max_steps

    async def run(self, task: str, *, output_type: type | None = None) -> AgentResult:
        result = await run_loop(self.model, self.tools, task,
                                max_steps=self.max_steps, instructions=self.instructions)
        if output_type is None:
            return result
        try:
            result.parsed = coerce(result.output, output_type)
            return result
        except CoercionError as first:
            reask = (
                f"{task}\n\nYour previous answer was:\n{result.output}\n\n"
                f"That could not be parsed into the required format ({first}). "
                "Reply with ONLY valid JSON matching the requested schema — no prose, no code fences."
            )
            retry = await run_loop(self.model, self.tools, reask,
                                   max_steps=self.max_steps, instructions=self.instructions)
            try:
                retry.parsed = coerce(retry.output, output_type)
                return retry
            except CoercionError as second:
                name = getattr(output_type, "__name__", repr(output_type))
                raise StructuredOutputError(
                    f"could not produce {name} after one reask: {second}"
                ) from second
```

- [ ] **Step 5: Export the errors from `verso/__init__.py`**

Add to the imports and `__all__` in `verso/__init__.py`:

```python
from verso.tools.coerce import CoercionError, StructuredOutputError
```

And add `"CoercionError"`, `"StructuredOutputError"` to the `__all__` list.

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_structured_output.py -v`
Expected: 4 passed.

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest -q`
Expected: all green (skeleton + Plan-2 tests). Then `uv run ruff check verso tests` → clean.

- [ ] **Step 8: Commit**

```bash
git add verso/types.py verso/agent.py verso/__init__.py tests/test_structured_output.py
git commit -m "feat: structured output via Agent.run(output_type=...) with one reask"
```

---

## Task 6: End-to-end + README

**Files:**
- Test: extend `tests/test_e2e.py` (append)
- Modify: `README.md` (append a structured-output snippet to the Quickstart)

- [ ] **Step 1: Append the offline e2e test to `tests/test_e2e.py`**

```python
# --- appended: structured output + done, offline ---
from pydantic import BaseModel
from verso.tools.builtins import done
from verso.types import StopReason


class Sum(BaseModel):
    total: int


async def test_e2e_structured_output_offline():
    from verso.model.fake import FakeModel
    from verso.model.base import ModelResponse
    from verso.types import Usage
    fm = FakeModel([ModelResponse(text='{"total": 42}', tool_calls=[], usage=Usage())])
    result = await Agent(model=fm).run("sum 20 and 22 as JSON", output_type=Sum)
    assert result.parsed == Sum(total=42)


async def test_e2e_done_tool_offline():
    from verso.model.fake import FakeModel
    from verso.model.base import ModelResponse, ToolCall
    from verso.types import Usage
    fm = FakeModel([ModelResponse(text="", tool_calls=[ToolCall(id="d", name="done", arguments={"result": "complete"})], usage=Usage())])
    result = await Agent(model=fm, tools=[done]).run("finish")
    assert result.output == "complete" and result.stop_reason is StopReason.DONE
```

- [ ] **Step 2: Run the e2e file**

Run: `uv run pytest tests/test_e2e.py -v`
Expected: prior e2e tests + 2 new pass; the live test still SKIPPED without a key.

- [ ] **Step 3: Append to `README.md` Quickstart**

Add after the existing Quickstart code block (before `## Status`):

````markdown
**Structured output** — ask for a type and get it back parsed:

```python
from pydantic import BaseModel

class Point(BaseModel):
    x: int
    y: int

result = await agent.run("Give me a point at 1,2 as JSON.", output_type=Point)
print(result.parsed)            # Point(x=1, y=2)  — reasks once if the model's first answer won't parse
```

**`done` tool** — explicit, structured termination instead of sentinel strings:

```python
from verso.tools import builtins
agent = Agent(model=..., tools=[builtins.done, my_tool])   # loop ends when the model calls done(result=...)
```
````

- [ ] **Step 4: Full suite + lint**

Run: `uv run pytest -q` → all green (live skipped). Then `uv run ruff check verso tests` → clean.

- [ ] **Step 5: Commit**

```bash
git add tests/test_e2e.py README.md
git commit -m "test: e2e structured-output + done; README structured-output snippet"
```

---

## Done criteria (Plan 2)

- `uv run pytest -q` green (live skipped); `uv run ruff check verso tests` clean.
- `await Agent(model).run(task, output_type=MyPydanticModel)` returns an `AgentResult` with `.parsed` a validated instance, reasking once on a parse/validation miss and raising `StructuredOutputError` only after that.
- `jsonish.parse()` recovers JSON from strict / fenced / prose-embedded / trailing-comma / python-literal inputs and raises `JsonishError` on genuine non-JSON.
- A model that calls `done(result=...)` terminates the loop with `StopReason.DONE` and that result as output.

## Deferred to later plans
Provider structured-output mode-map + robust retry (compose from Instructor), BAML typed-Flag coercion + streaming `Partial[T]`, the tool-argument input-repair ladder, and the full `ToolError{kind,can_retry,...}` envelope. Then: context engineering (Plan 3), model-layer depth (Plan 4), streaming (Plan 5).
