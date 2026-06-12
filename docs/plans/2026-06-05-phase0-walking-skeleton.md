# Verso Phase 0 — Walking Skeleton Implementation Plan

> **✅ SHIPPED** — implemented test-first, independently rechecked-APPROVED, on `main`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `await Agent(model, tools).run("…")` execute a real async ReAct loop against a live LLM provider, call a native `@tool`, and return `AgentResult(output, stop_reason, usage)`.

**Architecture:** A tiny provider-neutral core. The loop (`core/loop.py`) drives a `Model` (protocol) and a set of `Tool`s; tool dispatch always returns a `{ok,data,error}` envelope and never raises into the loop; one concrete provider (`AnthropicModel`) implements `Model`. A `FakeModel` test double lets the loop + tools be tested fully offline; a single live smoke test exercises the real provider, skipped unless `ANTHROPIC_API_KEY` is set.

**Tech Stack:** Python 3.12 · `uv` · Pydantic v2 (schema-gen + arg validation) · `anthropic` SDK (behind the `Model` interface) · pytest + pytest-asyncio (auto mode) · ruff.

**Scope (this plan is the walking skeleton — deliberately minimal):** IN — project scaffold, core types, `@tool` + schema-gen, `{ok,data,error}` dispatch, `Model` protocol + `FakeModel`, the ReAct loop, the `Agent` API, the Anthropic provider, end-to-end wiring. OUT (later Phase-0 plans) — streaming, multi-provider failover, the `jsonish` parser/structured-output, context engineering (`prune`/`inspect`/budget), memory, evals, durable runtime. Keep those out; do not stub them speculatively.

**Conventions for the implementer:** every public type is a `@dataclass` or Pydantic model with explicit fields (no bare dicts crossing module boundaries except the JSON-schema `parameters`). All I/O is `async`. Tests live in `tests/` mirroring the package path. Run everything with `uv run`. Commit after every green test.

---

## File Structure

```
Verso/                      (repo root — already has docs/, research/, README.md, .gitignore)
├── pyproject.toml          # NEW — package metadata, deps, pytest/ruff config
├── verso/
│   ├── __init__.py         # public API: Agent, tool, init_model, AgentResult, StopReason
│   ├── types.py            # StopReason, Usage, AgentResult
│   ├── agent.py            # Agent class (thin wrapper over the loop)
│   ├── core/
│   │   ├── __init__.py
│   │   └── loop.py         # run_loop() — the ReAct loop
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── tool.py         # @tool decorator, Tool dataclass, schema-gen
│   │   └── dispatch.py     # ToolResult, dispatch()
│   └── model/
│       ├── __init__.py
│       ├── base.py         # Model protocol, Message, ToolCall, ModelResponse
│       ├── fake.py         # FakeModel test double (shipped — users test with it too)
│       └── anthropic.py    # AnthropicModel
└── tests/
    ├── test_types.py
    ├── test_tool.py
    ├── test_dispatch.py
    ├── test_fake_model.py
    ├── test_loop.py
    ├── test_agent.py
    ├── test_anthropic.py
    └── test_e2e.py
```

Responsibilities: `types.py` = result/usage value objects (no logic). `model/base.py` = the provider contract + the message representation the loop and every provider share. `tools/` = turning a Python function into a schema + running it safely. `core/loop.py` = the only place control flow lives. `agent.py`/`__init__.py` = the public surface. `model/anthropic.py` = the one impl that touches the network.

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `verso/__init__.py`, `verso/core/__init__.py`, `verso/tools/__init__.py`, `verso/model/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "verso"
version = "0.0.1"
description = "A simple Python agent framework — the loop done right."
requires-python = ">=3.12"
dependencies = ["pydantic>=2.7", "anthropic>=0.40"]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "ruff>=0.6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

- [ ] **Step 2: Create empty package files**

Create these as empty files: `verso/core/__init__.py`, `verso/tools/__init__.py`, `verso/model/__init__.py`, `tests/__init__.py`. Create `verso/__init__.py` with a placeholder:

```python
__version__ = "0.0.1"
```

- [ ] **Step 3: Sync the environment**

Run: `uv sync --extra dev`
Expected: creates `.venv`, installs pydantic, anthropic, pytest, pytest-asyncio, ruff.

- [ ] **Step 4: Verify pytest runs (zero tests)**

Run: `uv run pytest -q`
Expected: `no tests ran` (exit 0 or 5). Either is fine — it proves the harness works.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml verso/ tests/
git commit -m "chore: scaffold verso package (uv, pydantic, pytest)"
```

---

## Task 2: Core value types (`StopReason`, `Usage`, `AgentResult`)

**Files:**
- Create: `verso/types.py`
- Test: `tests/test_types.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_types.py
from verso.types import StopReason, Usage, AgentResult


def test_usage_adds():
    a = Usage(input_tokens=10, output_tokens=5)
    b = Usage(input_tokens=3, output_tokens=7)
    total = a + b
    assert total == Usage(input_tokens=13, output_tokens=12)


def test_agent_result_fields():
    r = AgentResult(output="hi", stop_reason=StopReason.END_TURN, usage=Usage(), steps=1)
    assert r.output == "hi"
    assert r.stop_reason is StopReason.END_TURN
    assert r.steps == 1


def test_stop_reason_is_str_enum():
    assert StopReason.MAX_STEPS == "max_steps"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.types'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/types.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class StopReason(str, Enum):
    END_TURN = "end_turn"      # model returned a final text answer (no tool calls)
    MAX_STEPS = "max_steps"    # loop hit the max_steps cap
    ERROR = "error"            # unrecoverable error (later phases add more reasons)


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


@dataclass
class AgentResult:
    output: str
    stop_reason: StopReason
    usage: Usage
    steps: int
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_types.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/types.py tests/test_types.py
git commit -m "feat(types): StopReason, Usage, AgentResult"
```

---

## Task 3: The `Model` contract + message types

**Files:**
- Create: `verso/model/base.py`
- Test: `tests/test_fake_model.py` (covers types here; `FakeModel` arrives in Task 5)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fake_model.py
from verso.model.base import Message, ToolCall, ModelResponse
from verso.types import Usage


def test_message_defaults():
    m = Message(role="user", content="hello")
    assert m.tool_calls == []
    assert m.tool_call_id is None


def test_tool_call_fields():
    tc = ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})
    assert tc.name == "add"
    assert tc.arguments["a"] == 1


def test_model_response_fields():
    r = ModelResponse(text="done", tool_calls=[], usage=Usage(input_tokens=1))
    assert r.text == "done"
    assert r.tool_calls == []
    assert r.usage.input_tokens == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fake_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.model.base'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/model/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence, TYPE_CHECKING

from verso.types import Usage

if TYPE_CHECKING:
    from verso.tools.tool import Tool


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    role: str                                   # "user" | "assistant" | "tool"
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)   # set on assistant turns
    tool_call_id: str | None = None             # set on tool-result turns
    name: str | None = None                     # tool name, on tool-result turns


@dataclass
class ModelResponse:
    text: str
    tool_calls: list[ToolCall]
    usage: Usage


class Model(Protocol):
    """A provider that turns a message history + available tools into one response."""

    async def complete(self, messages: Sequence[Message], tools: Sequence["Tool"]) -> ModelResponse:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_fake_model.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/model/base.py tests/test_fake_model.py
git commit -m "feat(model): Model protocol + Message/ToolCall/ModelResponse"
```

---

## Task 4: `@tool` decorator + schema generation

**Files:**
- Create: `verso/tools/tool.py`
- Test: `tests/test_tool.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tool.py
from verso.tools.tool import tool, Tool


def test_tool_builds_schema_from_signature():
    @tool
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    assert isinstance(add, Tool)
    assert add.name == "add"
    assert add.description == "Add two integers."
    props = add.parameters["properties"]
    assert props["a"]["type"] == "integer"
    assert props["b"]["type"] == "integer"
    assert set(add.parameters["required"]) == {"a", "b"}


def test_tool_optional_param_not_required():
    @tool
    def greet(name: str, loud: bool = False) -> str:
        """Greet someone."""
        return name

    assert "name" in add_required(greet)
    assert "loud" not in add_required(greet)


def add_required(t: Tool) -> set[str]:
    return set(t.parameters.get("required", []))


def test_tool_call_invokes_underlying_fn():
    @tool
    def mul(a: int, b: int) -> int:
        "Multiply."
        return a * b

    assert mul.fn(3, 4) == 12
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tool.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.tools.tool'`.

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tool.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/tools/tool.py tests/test_tool.py
git commit -m "feat(tools): @tool decorator with pydantic schema-gen"
```

---

## Task 5: Tool dispatch — the `{ok,data,error}` envelope

**Files:**
- Create: `verso/tools/dispatch.py`
- Test: `tests/test_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dispatch.py
import pytest
from verso.tools.tool import tool
from verso.tools.dispatch import dispatch, ToolResult


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


@tool
async def aadd(a: int, b: int) -> int:
    "Async add."
    return a + b


@tool
def boom(x: int) -> int:
    "Always raises."
    raise ValueError("nope")


async def test_dispatch_sync_tool():
    res = await dispatch(add, {"a": 2, "b": 3})
    assert res == ToolResult(ok=True, data=5, error=None)


async def test_dispatch_async_tool():
    res = await dispatch(aadd, {"a": 4, "b": 1})
    assert res.ok and res.data == 5


async def test_dispatch_catches_exceptions():
    res = await dispatch(boom, {"x": 1})
    assert res.ok is False
    assert "ValueError" in res.error
    assert "nope" in res.error


async def test_dispatch_validation_error_is_returned_not_raised():
    res = await dispatch(add, {"a": "not-an-int", "b": 3})
    assert res.ok is False
    assert "validation" in res.error.lower() or "int" in res.error.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dispatch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.tools.dispatch'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/tools/dispatch.py
from __future__ import annotations
import inspect
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from verso.tools.tool import Tool


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None


async def dispatch(tool: Tool, arguments: dict[str, Any]) -> ToolResult:
    """Validate args, run the tool, and ALWAYS return a ToolResult — never raise."""
    try:
        validated = tool.args_model(**arguments)
    except ValidationError as e:
        return ToolResult(ok=False, error=f"ValidationError: {e}")
    try:
        result = tool.fn(**validated.model_dump())
        if inspect.isawaitable(result):
            result = await result
        return ToolResult(ok=True, data=result)
    except Exception as e:  # noqa: BLE001 — tool failures are data, not exceptions
        return ToolResult(ok=False, error=f"{type(e).__name__}: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dispatch.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/tools/dispatch.py tests/test_dispatch.py
git commit -m "feat(tools): dispatch with {ok,data,error} envelope (never raises)"
```

---

## Task 6: `FakeModel` test double

**Files:**
- Create: `verso/model/fake.py`
- Test: extend `tests/test_fake_model.py`

- [ ] **Step 1: Write the failing test (append to `tests/test_fake_model.py`)**

```python
from verso.model.fake import FakeModel


async def test_fake_model_returns_scripted_responses_in_order():
    r1 = ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage(output_tokens=1))
    r2 = ModelResponse(text="the answer is 3", tool_calls=[], usage=Usage(output_tokens=2))
    fm = FakeModel([r1, r2])

    out1 = await fm.complete([Message(role="user", content="add 1 and 2")], [])
    out2 = await fm.complete([], [])
    assert out1 is r1
    assert out2 is r2
    assert len(fm.calls) == 2


async def test_fake_model_raises_when_exhausted():
    fm = FakeModel([])
    import pytest
    with pytest.raises(AssertionError):
        await fm.complete([], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fake_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.model.fake'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/model/fake.py
from __future__ import annotations
from typing import Sequence

from verso.model.base import Message, ModelResponse
from verso.tools.tool import Tool


class FakeModel:
    """A scripted Model for offline tests. Returns the given responses in order."""

    def __init__(self, responses: list[ModelResponse]):
        self._responses = list(responses)
        self.calls: list[tuple[list[Message], list[Tool]]] = []

    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool]) -> ModelResponse:
        self.calls.append((list(messages), list(tools)))
        assert self._responses, "FakeModel ran out of scripted responses"
        return self._responses.pop(0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_fake_model.py -v`
Expected: all passed (5 total in this file).

- [ ] **Step 5: Commit**

```bash
git add verso/model/fake.py tests/test_fake_model.py
git commit -m "test(model): FakeModel scripted test double"
```

---

## Task 7: The ReAct loop

**Files:**
- Create: `verso/core/loop.py`
- Test: `tests/test_loop.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_loop.py
from verso.core.loop import run_loop
from verso.model.fake import FakeModel
from verso.model.base import Message, ModelResponse, ToolCall
from verso.tools.tool import tool
from verso.types import StopReason, Usage


@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b


async def test_loop_runs_tool_then_returns_text():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage(output_tokens=1)),
        ModelResponse(text="The answer is 3.", tool_calls=[], usage=Usage(output_tokens=2)),
    ])
    result = await run_loop(fm, [add], "add 1 and 2", max_steps=25)
    assert result.output == "The answer is 3."
    assert result.stop_reason is StopReason.END_TURN
    assert result.steps == 2
    assert result.usage.output_tokens == 3


async def test_loop_feeds_tool_result_back_to_model():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 4, "b": 5})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    await run_loop(fm, [add], "go")
    # second call's message history must contain the tool result "9"
    second_call_messages = fm.calls[1][0]
    tool_msgs = [m for m in second_call_messages if m.role == "tool"]
    assert any("9" in m.content for m in tool_msgs)


async def test_loop_unknown_tool_is_reported_not_crashed():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="nope", arguments={})], usage=Usage()),
        ModelResponse(text="recovered", tool_calls=[], usage=Usage()),
    ])
    result = await run_loop(fm, [add], "go")
    assert result.output == "recovered"
    tool_msgs = [m for m in fm.calls[1][0] if m.role == "tool"]
    assert any("unknown tool" in m.content.lower() for m in tool_msgs)


async def test_loop_hits_max_steps():
    # model always asks for a tool, never finishes
    looping = [ModelResponse(text="", tool_calls=[ToolCall(id=f"t{i}", name="add", arguments={"a": 1, "b": 1})], usage=Usage()) for i in range(10)]
    fm = FakeModel(looping)
    result = await run_loop(fm, [add], "loop forever", max_steps=3)
    assert result.stop_reason is StopReason.MAX_STEPS
    assert result.steps == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_loop.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.core.loop'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/core/loop.py
from __future__ import annotations
import json
from typing import Sequence

from verso.model.base import Message, Model, ToolCall
from verso.tools.dispatch import dispatch
from verso.tools.tool import Tool
from verso.types import AgentResult, StopReason, Usage


def _format_result(data) -> str:
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return str(data)


async def run_loop(model: Model, tools: Sequence[Tool], task: str,
                   max_steps: int = 25, instructions: str | None = None) -> AgentResult:
    messages: list[Message] = []
    if instructions:
        messages.append(Message(role="user", content=instructions))
    messages.append(Message(role="user", content=task))
    tool_map = {t.name: t for t in tools}
    usage = Usage()

    for step in range(1, max_steps + 1):
        resp = await model.complete(messages, list(tools))
        usage = usage + resp.usage

        if not resp.tool_calls:
            return AgentResult(output=resp.text, stop_reason=StopReason.END_TURN,
                               usage=usage, steps=step)

        messages.append(Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls))
        for tc in resp.tool_calls:
            t = tool_map.get(tc.name)
            if t is None:
                content = f"Error: unknown tool '{tc.name}'."
            else:
                result = await dispatch(t, tc.arguments)
                content = _format_result(result.data) if result.ok else f"Error: {result.error}"
            messages.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

    return AgentResult(output="", stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_loop.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/core/loop.py tests/test_loop.py
git commit -m "feat(core): async ReAct loop with max_steps + StopReason"
```

---

## Task 8: The `Agent` public API

**Files:**
- Create: `verso/agent.py`
- Modify: `verso/__init__.py`
- Test: `tests/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent.py
from verso import Agent, tool
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def test_agent_run_end_to_end_with_fake_model():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 2, "b": 2})], usage=Usage()),
        ModelResponse(text="4", tool_calls=[], usage=Usage()),
    ])
    agent = Agent(model=fm, tools=[add])
    result = await agent.run("what is 2+2?")
    assert result.output == "4"
    assert result.stop_reason is StopReason.END_TURN


async def test_agent_respects_max_steps():
    fm = FakeModel([ModelResponse(text="", tool_calls=[ToolCall(id="t", name="add", arguments={"a": 1, "b": 1})], usage=Usage()) for _ in range(5)])
    agent = Agent(model=fm, tools=[add], max_steps=2)
    result = await agent.run("loop")
    assert result.stop_reason is StopReason.MAX_STEPS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agent.py -v`
Expected: FAIL — `ImportError: cannot import name 'Agent' from 'verso'`.

- [ ] **Step 3: Write `verso/agent.py`**

```python
# verso/agent.py
from __future__ import annotations
from typing import Sequence

from verso.core.loop import run_loop
from verso.model.base import Model
from verso.tools.tool import Tool
from verso.types import AgentResult


class Agent:
    def __init__(self, model: Model, tools: Sequence[Tool] = (), *,
                 instructions: str | None = None, max_steps: int = 25):
        self.model = model
        self.tools = list(tools)
        self.instructions = instructions
        self.max_steps = max_steps

    async def run(self, task: str) -> AgentResult:
        return await run_loop(
            self.model, self.tools, task,
            max_steps=self.max_steps, instructions=self.instructions,
        )
```

- [ ] **Step 4: Update `verso/__init__.py`**

```python
# verso/__init__.py
from verso.agent import Agent
from verso.tools.tool import tool, Tool
from verso.types import AgentResult, StopReason, Usage
from verso.model.base import Model, Message, ModelResponse, ToolCall

__version__ = "0.0.1"
__all__ = [
    "Agent", "tool", "Tool", "AgentResult", "StopReason", "Usage",
    "Model", "Message", "ModelResponse", "ToolCall", "init_model",
]


def init_model(spec: str):
    """Build a Model from a 'provider:model_id' string. Only 'anthropic' in Phase 0."""
    provider, _, model_id = spec.partition(":")
    if provider == "anthropic":
        from verso.model.anthropic import AnthropicModel
        return AnthropicModel(model_id)
    raise ValueError(f"unknown provider '{provider}' (Phase 0 supports 'anthropic')")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_agent.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add verso/agent.py verso/__init__.py tests/test_agent.py
git commit -m "feat: Agent public API + init_model factory"
```

---

## Task 9: The Anthropic provider

**Files:**
- Create: `verso/model/anthropic.py`
- Test: `tests/test_anthropic.py`

The provider is dependency-injected with a `client` so the unit test passes a fake client (no network). The real default client is created lazily.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_anthropic.py
from verso.model.anthropic import AnthropicModel
from verso.model.base import Message
from verso.tools.tool import tool


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, content, input_tokens, output_tokens):
        self.content = content
        self.usage = _Block(input_tokens=input_tokens, output_tokens=output_tokens)


class FakeAnthropicMessages:
    def __init__(self, resp):
        self._resp = resp
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self._resp


class FakeAnthropicClient:
    def __init__(self, resp):
        self.messages = FakeAnthropicMessages(resp)


async def test_maps_text_response():
    resp = _Resp([_Block(type="text", text="hello")], input_tokens=10, output_tokens=3)
    client = FakeAnthropicClient(resp)
    m = AnthropicModel("claude-x", client=client)
    out = await m.complete([Message(role="user", content="hi")], [add])
    assert out.text == "hello"
    assert out.tool_calls == []
    assert out.usage.input_tokens == 10 and out.usage.output_tokens == 3
    # tools were mapped into the request
    assert client.messages.kwargs["tools"][0]["name"] == "add"
    assert client.messages.kwargs["tools"][0]["input_schema"]["properties"]["a"]["type"] == "integer"


async def test_maps_tool_use_response():
    resp = _Resp(
        [_Block(type="tool_use", id="tu1", name="add", input={"a": 1, "b": 2})],
        input_tokens=5, output_tokens=4,
    )
    m = AnthropicModel("claude-x", client=FakeAnthropicClient(resp))
    out = await m.complete([Message(role="user", content="add")], [add])
    assert len(out.tool_calls) == 1
    tc = out.tool_calls[0]
    assert tc.id == "tu1" and tc.name == "add" and tc.arguments == {"a": 1, "b": 2}


async def test_maps_assistant_and_tool_messages_into_request():
    from verso.model.base import ToolCall
    resp = _Resp([_Block(type="text", text="ok")], 1, 1)
    client = FakeAnthropicClient(resp)
    m = AnthropicModel("claude-x", client=client)
    history = [
        Message(role="user", content="add 1 and 2"),
        Message(role="assistant", content="", tool_calls=[ToolCall(id="tu1", name="add", arguments={"a": 1, "b": 2})]),
        Message(role="tool", content="3", tool_call_id="tu1", name="add"),
    ]
    await m.complete(history, [add])
    sent = client.messages.kwargs["messages"]
    # assistant turn carries a tool_use block; tool turn becomes a user tool_result block
    assert sent[1]["role"] == "assistant"
    assert sent[1]["content"][0]["type"] == "tool_use"
    assert sent[2]["role"] == "user"
    assert sent[2]["content"][0]["type"] == "tool_result"
    assert sent[2]["content"][0]["tool_use_id"] == "tu1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_anthropic.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.model.anthropic'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/model/anthropic.py
from __future__ import annotations
from typing import Any, Sequence

from verso.model.base import Message, ModelResponse, ToolCall
from verso.tools.tool import Tool
from verso.types import Usage

DEFAULT_MAX_TOKENS = 4096


class AnthropicModel:
    def __init__(self, model_id: str, *, client: Any = None, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.model_id = model_id
        self.max_tokens = max_tokens
        self._client = client  # injected in tests; created lazily in prod

    @property
    def client(self) -> Any:
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic()
        return self._client

    def _to_anthropic_messages(self, messages: Sequence[Message]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m.role == "user":
                out.append({"role": "user", "content": m.content})
            elif m.role == "assistant":
                blocks: list[dict] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
                out.append({"role": "assistant", "content": blocks})
            elif m.role == "tool":
                out.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}
                ]})
        return out

    def _to_anthropic_tools(self, tools: Sequence[Tool]) -> list[dict]:
        return [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]

    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool]) -> ModelResponse:
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "messages": self._to_anthropic_messages(messages),
        }
        if tools:
            kwargs["tools"] = self._to_anthropic_tools(tools)
        resp = await self.client.messages.create(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))

        return ModelResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage=Usage(input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_anthropic.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/model/anthropic.py tests/test_anthropic.py
git commit -m "feat(model): AnthropicModel provider (message + tool mapping)"
```

---

## Task 10: End-to-end wiring + live smoke test

**Files:**
- Test: `tests/test_e2e.py`
- Modify: `README.md` (add a Quickstart)

- [ ] **Step 1: Write the tests**

```python
# tests/test_e2e.py
import os
import pytest
from verso import Agent, tool, init_model
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason


@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b


async def test_e2e_fake_full_path():
    """The whole public path: Agent + @tool + loop + result, no network."""
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 20, "b": 22})], usage=Usage(input_tokens=8, output_tokens=2)),
        ModelResponse(text="42", tool_calls=[], usage=Usage(input_tokens=9, output_tokens=1)),
    ])
    result = await Agent(model=fm, tools=[add]).run("what is 20 + 22?")
    assert result.output == "42"
    assert result.stop_reason is StopReason.END_TURN
    assert result.usage.input_tokens == 17


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
async def test_e2e_live_anthropic():
    """One real call. Skipped unless ANTHROPIC_API_KEY is set."""
    agent = Agent(model=init_model("anthropic:claude-sonnet-4-6"), tools=[add],
                  instructions="Use the add tool for any arithmetic.")
    result = await agent.run("Use the add tool to compute 20 + 22, then reply with just the number.")
    assert "42" in result.output
    assert result.stop_reason is StopReason.END_TURN
    assert result.usage.output_tokens > 0
```

- [ ] **Step 2: Run the offline test (and confirm live test is skipped)**

Run: `uv run pytest tests/test_e2e.py -v`
Expected: `test_e2e_fake_full_path` PASS; `test_e2e_live_anthropic` SKIPPED.

- [ ] **Step 3: Run the full suite**

Run: `uv run pytest -q`
Expected: all tests pass (live test skipped). Then run `uv run ruff check verso tests` — expected: clean (fix any lint).

- [ ] **Step 4: (Optional, manual) run the live smoke test**

Run: `ANTHROPIC_API_KEY=sk-... uv run pytest tests/test_e2e.py::test_e2e_live_anthropic -v`
Expected: PASS — proves the real provider path end-to-end. (Skip if no key handy; CI stays green via the skip.)

- [ ] **Step 5: Add a Quickstart to `README.md`**

Add this section near the top of `README.md` (after the intro, before `## Status`):

````markdown
## Quickstart (Phase 0 — walking skeleton)

```python
import asyncio
from verso import Agent, tool, init_model

@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b

async def main():
    agent = Agent(model=init_model("anthropic:claude-sonnet-4-6"), tools=[add])
    result = await agent.run("What is 20 + 22? Use the add tool.")
    print(result.output, "·", result.stop_reason, "·", result.usage)

asyncio.run(main())
```

Set `ANTHROPIC_API_KEY` first. Tests run offline via a `FakeModel`: `uv run pytest`.
````

- [ ] **Step 6: Commit**

```bash
git add tests/test_e2e.py README.md
git commit -m "test: end-to-end (fake + live-smoke) + README quickstart"
```

---

## Done criteria (walking skeleton)

- `uv run pytest -q` is green (live test skipped without a key); `uv run ruff check verso tests` is clean.
- `await Agent(model=init_model("anthropic:..."), tools=[add]).run("…")` returns an `AgentResult` with the right `output`, `stop_reason`, and summed `usage` — verified by the live smoke test when a key is present.
- The loop is provider-neutral (only `verso/model/anthropic.py` imports `anthropic`); a second provider can be added later by implementing `Model` with zero loop changes.

## What this intentionally leaves for the next Phase-0 plans

Streaming (`stream/`), multi-provider failover + retry + `AttemptRecord` (`model/` depth), the `jsonish` waterfall + Instructor-composed structured output (`tools/jsonish.py`), context engineering (`ContextBundle`, budget, `prune()`, `inspect()`), `think`/`done` builtins, and `StopReason` values beyond `END_TURN`/`MAX_STEPS`/`ERROR`. Do not build these here — each is its own plan so the skeleton stays a true minimal vertical slice.
