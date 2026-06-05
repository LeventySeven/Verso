# Verso Phase 0 — Plan 3: Context Engineering

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make context a first-class, inspectable object. Introduce `ContextBundle` (system + history + tools with per-section token estimates), a token-budget guard that triggers `prune()` observation-masking, KV-cache discipline (instructions become a stable **system** prefix; deterministic tool-schema serialization), and `Agent.inspect()` that renders *exactly* what the model will receive.

**Architecture:** The loop stops hand-managing a `messages` list and instead owns a `ContextBundle`. Each turn it asks the bundle for its token estimate; if over `max_context_tokens` it prunes the history (mask old tool outputs, keep reasoning). The model is called with `complete(bundle.to_messages(), bundle.tools, system=bundle.system)`. `Agent.inspect(task)` builds the same bundle and returns it, so what you inspect byte-equals what the model gets.

**Tech Stack:** unchanged — Python 3.12 (uv-pinned), Pydantic v2, pytest + `FakeModel`. No new dependencies (the token estimate is a deliberate `~chars/4` heuristic; a real tokenizer is a later swap).

**Prereq:** Plans 1–2 merged and green (`uv run pytest` → 52 passed / 1 skipped). Paths relative to repo root `~/Desktop/Verso`. Run with `uv run`. Commit after every green test.

**Out of scope (deferred):** a real per-provider tokenizer (Anthropic `count_tokens` API / tiktoken); LLM-based `compact()` summarization (this plan ships only the LLM-free `prune()` pass — `compact()` is a later plan); `RunContext[T]` dependency-injection into tools/hooks (hooks plan); cache-hit telemetry. Keep the estimator approximate and the prune LLM-free.

---

## File Structure

```
verso/
├── context/
│   ├── __init__.py     # NEW (empty)
│   ├── tokens.py       # NEW — estimate_tokens()
│   ├── bundle.py       # NEW — ContextBundle (system/history/tools, sections, render, stable_prefix)
│   └── prune.py        # NEW — prune() observation-masking
├── model/base.py       # MODIFY — Model.complete gains keyword-only `system`
├── model/fake.py       # MODIFY — FakeModel records system; calls become 3-tuples
├── model/anthropic.py  # MODIFY — map `system` to the Anthropic `system` param
├── core/loop.py        # MODIFY — own a ContextBundle; budget→prune; pass system
└── agent.py            # MODIFY — max_context_tokens; Agent.inspect(task)
tests/
├── test_tokens.py          # NEW
├── test_bundle.py          # NEW
├── test_system_prefix.py   # NEW
├── test_prune.py           # NEW
└── test_context_loop.py    # NEW (budget→prune + inspect byte-equality)
```

---

## Task 1: Token estimator

**Files:**
- Create: `verso/context/__init__.py` (empty), `verso/context/tokens.py`
- Test: `tests/test_tokens.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tokens.py
from verso.context.tokens import estimate_tokens


def test_empty_is_zero():
    assert estimate_tokens("") == 0


def test_roughly_chars_over_four():
    assert estimate_tokens("a" * 40) == 10


def test_nonempty_is_at_least_one():
    assert estimate_tokens("hi") >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tokens.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.context.tokens'`.

- [ ] **Step 3: Create `verso/context/__init__.py` (empty) and `verso/context/tokens.py`**

```python
# verso/context/tokens.py
from __future__ import annotations

CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Cheap, provider-agnostic token estimate (~chars/4). Approximate BY DESIGN —
    used for budget guards, not billing. Swap for a real tokenizer later."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tokens.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/context/__init__.py verso/context/tokens.py tests/test_tokens.py
git commit -m "feat(context): estimate_tokens heuristic"
```

---

## Task 2: `ContextBundle`

**Files:**
- Create: `verso/context/bundle.py`
- Test: `tests/test_bundle.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bundle.py
from verso.context.bundle import ContextBundle
from verso.model.base import Message, ToolCall
from verso.tools.tool import tool


@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b


def _bundle():
    return ContextBundle(
        instructions="be terse",
        history=[
            Message(role="user", content="add 1 and 2"),
            Message(role="assistant", content="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})]),
            Message(role="tool", content="3", tool_call_id="t1", name="add"),
        ],
        tools=[add],
    )


def test_system_is_instructions():
    assert _bundle().system == "be terse"


def test_to_messages_is_a_copy_of_history():
    b = _bundle()
    msgs = b.to_messages()
    assert msgs == b.history
    msgs.append(Message(role="user", content="x"))
    assert len(b.history) == 3  # mutating the copy must not touch the bundle


def test_sections_and_total():
    b = _bundle()
    s = b.sections()
    assert set(s) == {"instructions", "tools", "history"}
    assert all(isinstance(v, int) for v in s.values())
    assert b.estimate_tokens() == sum(s.values())


def test_stable_prefix_is_byte_identical_across_different_history():
    b1 = _bundle()
    b2 = _bundle()
    b2.history = b2.history + [Message(role="user", content="another turn")]
    assert b1.stable_prefix() == b2.stable_prefix()   # prefix (system+tools) unaffected by history


def test_tool_schema_text_is_deterministic():
    b = _bundle()
    assert b.tool_schema_text() == b.tool_schema_text()
    assert '"name": "add"' in b.tool_schema_text()


def test_render_shows_system_tools_and_turns():
    out = _bundle().render()
    assert "[system]" in out and "be terse" in out
    assert "[tools]" in out
    assert "[user] add 1 and 2" in out
    assert "add(" in out  # the tool call is rendered
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_bundle.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.context.bundle'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/context/bundle.py
from __future__ import annotations
import json
from dataclasses import dataclass, field

from verso.context.tokens import estimate_tokens
from verso.model.base import Message
from verso.tools.tool import Tool


def _message_text(m: Message) -> str:
    parts = [m.content or ""]
    for tc in m.tool_calls:
        parts.append(f"{tc.name}({json.dumps(tc.arguments, sort_keys=True)})")
    return " ".join(p for p in parts if p)


@dataclass
class ContextBundle:
    """The named, inspectable assembly of everything sent to the model this turn."""
    instructions: str | None = None
    history: list[Message] = field(default_factory=list)
    tools: list[Tool] = field(default_factory=list)

    @property
    def system(self) -> str | None:
        return self.instructions

    def to_messages(self) -> list[Message]:
        return list(self.history)

    def tool_schema_text(self) -> str:
        # deterministic (sorted-key) serialization — the cache-stable tool prefix
        return json.dumps(
            [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in self.tools],
            sort_keys=True,
        )

    def stable_prefix(self) -> str:
        # the KV-cache prefix: system + tool schemas; must be byte-identical across turns
        return (self.instructions or "") + "\n" + self.tool_schema_text()

    def sections(self) -> dict[str, int]:
        return {
            "instructions": estimate_tokens(self.instructions or ""),
            "tools": estimate_tokens(self.tool_schema_text()),
            "history": sum(estimate_tokens(_message_text(m)) for m in self.history),
        }

    def estimate_tokens(self) -> int:
        return sum(self.sections().values())

    def render(self) -> str:
        lines: list[str] = []
        if self.instructions:
            lines.append(f"[system]\n{self.instructions}")
        if self.tools:
            lines.append(f"[tools]\n{self.tool_schema_text()}")
        for m in self.history:
            extra = ""
            if m.tool_calls:
                extra = " -> " + ", ".join(
                    f"{tc.name}({json.dumps(tc.arguments, sort_keys=True)})" for tc in m.tool_calls
                )
            lines.append(f"[{m.role}] {m.content}{extra}")
        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_bundle.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/context/bundle.py tests/test_bundle.py
git commit -m "feat(context): ContextBundle (system/history/tools, sections, stable_prefix, render)"
```

---

## Task 3: `system` prefix in the Model layer

**Files:**
- Modify: `verso/model/base.py`, `verso/model/fake.py`, `verso/model/anthropic.py`
- Test: `tests/test_system_prefix.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_system_prefix.py
from verso.model.fake import FakeModel
from verso.model.base import Message, ModelResponse
from verso.model.anthropic import AnthropicModel
from verso.tools.tool import tool
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def test_fake_model_records_system():
    fm = FakeModel([ModelResponse(text="ok", tool_calls=[], usage=Usage())])
    await fm.complete([Message(role="user", content="hi")], [], system="be terse")
    messages, tools, system = fm.calls[0]
    assert system == "be terse"
    assert messages[0].content == "hi"


async def test_fake_model_system_defaults_none():
    fm = FakeModel([ModelResponse(text="ok", tool_calls=[], usage=Usage())])
    await fm.complete([], [])
    assert fm.calls[0][2] is None


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, content, it, ot):
        self.content = content
        self.usage = _Block(input_tokens=it, output_tokens=ot)


class _Msgs:
    def __init__(self, resp):
        self._resp = resp
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return self._resp


class _Client:
    def __init__(self, resp):
        self.messages = _Msgs(resp)


async def test_anthropic_maps_system_param():
    client = _Client(_Resp([_Block(type="text", text="hi")], 1, 1))
    m = AnthropicModel("claude-x", client=client)
    await m.complete([Message(role="user", content="hi")], [add], system="be terse")
    assert client.messages.kwargs["system"] == "be terse"


async def test_anthropic_omits_system_when_none():
    client = _Client(_Resp([_Block(type="text", text="hi")], 1, 1))
    m = AnthropicModel("claude-x", client=client)
    await m.complete([Message(role="user", content="hi")], [add])
    assert "system" not in client.messages.kwargs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_system_prefix.py -v`
Expected: FAIL — `TypeError: complete() got an unexpected keyword argument 'system'`.

- [ ] **Step 3: Modify `verso/model/base.py`**

Change the `Model.complete` signature (add keyword-only `system`):

```python
    async def complete(self, messages: Sequence[Message], tools: Sequence["Tool"],
                       *, system: str | None = None) -> ModelResponse:
        ...
```

- [ ] **Step 4: Modify `verso/model/fake.py`**

Replace the `complete` method (record `system`; `calls` entries become 3-tuples `(messages, tools, system)`):

```python
    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool],
                       *, system: str | None = None) -> ModelResponse:
        self.calls.append((list(messages), list(tools), system))
        assert self._responses, "FakeModel ran out of scripted responses"
        return self._responses.pop(0)
```

Also update the `calls` type annotation in `__init__` to:

```python
        self.calls: list[tuple[list[Message], list[Tool], str | None]] = []
```

- [ ] **Step 5: Modify `verso/model/anthropic.py`**

Change the `complete` signature and add the system param to the request. Replace the `complete` method's signature line and the `kwargs` assembly:

```python
    async def complete(self, messages: Sequence[Message], tools: Sequence[Tool],
                       *, system: str | None = None) -> ModelResponse:
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "messages": self._to_anthropic_messages(messages),
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._to_anthropic_tools(tools)
        resp = await self.client.messages.create(**kwargs)
```

(The rest of `complete` — the response-block parsing — is unchanged.)

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_system_prefix.py -v`
Expected: 4 passed.

- [ ] **Step 7: Run the full suite (no regressions)**

Run: `uv run pytest -q`
Expected: all green — existing tests index `fm.calls[i][0]` (messages) which is unchanged; the new 3rd tuple element doesn't affect them.

- [ ] **Step 8: Commit**

```bash
git add verso/model/base.py verso/model/fake.py verso/model/anthropic.py tests/test_system_prefix.py
git commit -m "feat(model): keyword-only system prefix (instructions -> Anthropic system param)"
```

---

## Task 4: `prune()` observation-masking

**Files:**
- Create: `verso/context/prune.py`
- Test: `tests/test_prune.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prune.py
from verso.context.prune import prune, MASK
from verso.model.base import Message, ToolCall


def _tool_msg(i):
    return Message(role="tool", content=f"result-{i}", tool_call_id=f"t{i}", name="add")


def test_no_masking_when_under_window():
    history = [Message(role="user", content="go")] + [_tool_msg(i) for i in range(5)]
    assert prune(history, keep_last_n=10) == history


def test_masks_oldest_tool_outputs_beyond_window():
    history = [_tool_msg(i) for i in range(12)]
    out = prune(history, keep_last_n=10)
    assert out[0].content == MASK and out[1].content == MASK
    assert [m.content for m in out[2:]] == [f"result-{i}" for i in range(2, 12)]


def test_never_masks_non_tool_messages():
    history = [Message(role="user", content="u"),
              Message(role="assistant", content="a", tool_calls=[ToolCall(id="t", name="add", arguments={})])]
    history += [_tool_msg(i) for i in range(12)]
    out = prune(history, keep_last_n=10)
    assert out[0].content == "u"
    assert out[1].content == "a"


def test_preserves_tool_call_id_and_structure_on_masked():
    history = [_tool_msg(i) for i in range(12)]
    out = prune(history, keep_last_n=10)
    assert out[0].tool_call_id == "t0" and out[0].role == "tool" and out[0].name == "add"


def test_idempotent():
    history = [_tool_msg(i) for i in range(12)]
    once = prune(history, keep_last_n=10)
    twice = prune(once, keep_last_n=10)
    assert [m.content for m in once] == [m.content for m in twice]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_prune.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.context.prune'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/context/prune.py
from __future__ import annotations

from verso.model.base import Message

MASK = "[observation pruned to save context]"


def prune(history: list[Message], keep_last_n: int = 10) -> list[Message]:
    """Observation-masking: replace the CONTENT of tool-result messages older than the
    most recent `keep_last_n` tool results with a placeholder. Reasoning, user, and
    assistant turns are never touched, and message structure (ids/roles) is preserved.
    Idempotent: re-pruning already-masked messages is a no-op."""
    tool_idxs = [i for i, m in enumerate(history) if m.role == "tool"]
    if len(tool_idxs) <= keep_last_n:
        return list(history)
    to_mask = set(tool_idxs[:-keep_last_n])
    out: list[Message] = []
    for i, m in enumerate(history):
        if i in to_mask and m.content != MASK:
            out.append(Message(role="tool", content=MASK, tool_call_id=m.tool_call_id, name=m.name))
        else:
            out.append(m)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_prune.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/context/prune.py tests/test_prune.py
git commit -m "feat(context): prune() observation-masking (LLM-free)"
```

---

## Task 5: Wire bundle + budget + inspect into the loop and Agent

**Files:**
- Modify: `verso/core/loop.py`, `verso/agent.py`
- Modify: `verso/__init__.py` (export `ContextBundle`)
- Test: `tests/test_context_loop.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_context_loop.py
from verso import Agent
from verso.context.bundle import ContextBundle
from verso.context.prune import MASK
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.tool import tool
from verso.types import Usage, StopReason


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def test_inspect_byte_equals_what_model_receives():
    fm = FakeModel([ModelResponse(text="done", tool_calls=[], usage=Usage())])
    agent = Agent(model=fm, tools=[add], instructions="be terse")
    bundle = agent.inspect("hello")
    await agent.run("hello")
    sent_messages, sent_tools, sent_system = fm.calls[0]
    assert bundle.to_messages() == sent_messages
    assert bundle.system == sent_system == "be terse"
    assert [t.name for t in bundle.tools] == [t.name for t in sent_tools]
    assert isinstance(bundle, ContextBundle)


async def test_instructions_go_as_system_not_a_user_message():
    fm = FakeModel([ModelResponse(text="ok", tool_calls=[], usage=Usage())])
    await Agent(model=fm, instructions="SYS").run("hi")
    messages, _tools, system = fm.calls[0]
    assert system == "SYS"
    assert [m.content for m in messages] == ["hi"]   # no instructions message in history


async def test_budget_triggers_prune_of_old_tool_outputs():
    # 12 tool turns then a final answer; tiny budget forces a prune before the last call
    responses = [
        ModelResponse(text="", tool_calls=[ToolCall(id=f"t{i}", name="add", arguments={"a": 1, "b": 1})], usage=Usage())
        for i in range(12)
    ]
    responses.append(ModelResponse(text="final", tool_calls=[], usage=Usage()))
    fm = FakeModel(responses)
    agent = Agent(model=fm, tools=[add], max_context_tokens=1)  # force pruning
    result = await agent.run("loop a lot")
    assert result.output == "final"
    # the LAST model call should have seen masked old tool outputs
    last_messages = fm.calls[-1][0]
    masked = [m for m in last_messages if m.role == "tool" and m.content == MASK]
    assert len(masked) >= 1


async def test_no_prune_when_budget_unset():
    fm = FakeModel([ModelResponse(text="ok", tool_calls=[], usage=Usage())])
    await Agent(model=fm, tools=[add]).run("hi")  # max_context_tokens=None default
    assert all(m.content != MASK for m in fm.calls[0][0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_context_loop.py -v`
Expected: FAIL — `AttributeError: 'Agent' object has no attribute 'inspect'` (and `run` doesn't accept `max_context_tokens` yet).

- [ ] **Step 3: Rewrite `verso/core/loop.py`**

Replace the entire body of `run_loop` (keep the `_format_result` helper and imports; add the bundle/prune imports):

```python
# verso/core/loop.py
from __future__ import annotations
import json
from typing import Sequence

from verso.context.bundle import ContextBundle
from verso.context.prune import prune
from verso.model.base import Message, Model
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


def build_bundle(tools: Sequence[Tool], task: str, instructions: str | None) -> ContextBundle:
    return ContextBundle(instructions=instructions,
                         history=[Message(role="user", content=task)],
                         tools=list(tools))


async def run_loop(model: Model, tools: Sequence[Tool], task: str,
                   max_steps: int = 25, instructions: str | None = None,
                   max_context_tokens: int | None = None) -> AgentResult:
    bundle = build_bundle(tools, task, instructions)
    tool_map = {t.name: t for t in tools}
    usage = Usage()

    for step in range(1, max_steps + 1):
        if max_context_tokens is not None and bundle.estimate_tokens() > max_context_tokens:
            bundle.history = prune(bundle.history)

        resp = await model.complete(bundle.to_messages(), bundle.tools, system=bundle.system)
        usage = usage + resp.usage

        if not resp.tool_calls:
            return AgentResult(output=resp.text, stop_reason=StopReason.END_TURN,
                               usage=usage, steps=step)

        bundle.history.append(Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls))
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
            bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

    return AgentResult(output="", stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps)
```

- [ ] **Step 4: Rewrite `verso/agent.py`**

Add `max_context_tokens` and `inspect`; thread the budget through both run paths:

```python
# verso/agent.py
from __future__ import annotations
from typing import Sequence

from verso.context.bundle import ContextBundle
from verso.core.loop import build_bundle, run_loop
from verso.model.base import Model
from verso.tools.coerce import CoercionError, StructuredOutputError, coerce
from verso.tools.tool import Tool
from verso.types import AgentResult


class Agent:
    def __init__(self, model: Model, tools: Sequence[Tool] = (), *,
                 instructions: str | None = None, max_steps: int = 25,
                 max_context_tokens: int | None = None):
        self.model = model
        self.tools = list(tools)
        self.instructions = instructions
        self.max_steps = max_steps
        self.max_context_tokens = max_context_tokens

    def inspect(self, task: str) -> ContextBundle:
        """Return the exact ContextBundle the model will receive for `task` (turn 1)."""
        return build_bundle(self.tools, task, self.instructions)

    async def _run(self, task: str) -> AgentResult:
        return await run_loop(self.model, self.tools, task, max_steps=self.max_steps,
                              instructions=self.instructions,
                              max_context_tokens=self.max_context_tokens)

    async def run(self, task: str, *, output_type: type | None = None) -> AgentResult:
        result = await self._run(task)
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
            retry = await self._run(reask)
            try:
                retry.parsed = coerce(retry.output, output_type)
                retry.usage = result.usage + retry.usage
                retry.steps = result.steps + retry.steps
                return retry
            except CoercionError as second:
                name = getattr(output_type, "__name__", repr(output_type))
                raise StructuredOutputError(
                    f"could not produce {name} after one reask: {second}"
                ) from second
```

- [ ] **Step 5: Export `ContextBundle` from `verso/__init__.py`**

Add to the imports and `__all__`:

```python
from verso.context.bundle import ContextBundle
```

(add `"ContextBundle"` to `__all__`).

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_context_loop.py -v`
Expected: 4 passed.

- [ ] **Step 7: Run the full suite + lint**

Run: `uv run pytest -q`
Expected: all green (existing loop/agent tests still pass — instructions default None, so behavior is unchanged except instructions now route to `system`; tests that passed instructions were live-only or none did). Then `uv run ruff check verso tests` → clean.

> If any existing test asserted an instructions message appeared in history, update it to assert `system` instead — but the skeleton/Plan-2 tests do not pass `instructions`, so none should need changes.

- [ ] **Step 8: Commit**

```bash
git add verso/core/loop.py verso/agent.py verso/__init__.py tests/test_context_loop.py
git commit -m "feat(context): loop owns ContextBundle; budget->prune; Agent.inspect()"
```

---

## Task 6: End-to-end + README

**Files:**
- Test: extend `tests/test_e2e.py` (append)
- Modify: `README.md` (append an inspect/context note)

- [ ] **Step 1: Append the offline e2e test to `tests/test_e2e.py`**

```python
# --- appended: context engineering, offline ---
async def test_e2e_inspect_offline():
    from verso.model.fake import FakeModel
    from verso.model.base import ModelResponse
    from verso.types import Usage
    fm = FakeModel([ModelResponse(text="hi", tool_calls=[], usage=Usage())])
    agent = Agent(model=fm, tools=[add], instructions="be terse")
    bundle = agent.inspect("what is 2+2?")
    rendered = bundle.render()
    assert "[system]" in rendered and "be terse" in rendered
    assert "[user] what is 2+2?" in rendered
    assert bundle.estimate_tokens() > 0
```

- [ ] **Step 2: Run the e2e file**

Run: `uv run pytest tests/test_e2e.py -v`
Expected: prior e2e tests + the new one pass; live test still SKIPPED.

- [ ] **Step 3: Append to `README.md` Quickstart (before `## Status`)**

````markdown
**Inspect the context** — see exactly what the model will receive (byte-for-byte):

```python
agent = Agent(model=..., tools=[add], instructions="Be terse.", max_context_tokens=8000)
print(agent.inspect("What is 2+2?").render())
# [system] Be terse.
# [tools] [{"description": "...", "name": "add", "parameters": {...}}]
# [user] What is 2+2?
```

Instructions become a stable **system** prefix (KV-cache friendly); when the running context exceeds `max_context_tokens`, old tool outputs are masked (`prune()`), never silently dropped.
````

- [ ] **Step 4: Full suite + lint**

Run: `uv run pytest -q` → all green (live skipped). Then `uv run ruff check verso tests` → clean.

- [ ] **Step 5: Commit**

```bash
git add tests/test_e2e.py README.md
git commit -m "test: e2e inspect/context; README context-engineering snippet"
```

---

## Done criteria (Plan 3)

- `uv run pytest -q` green (live skipped); `uv run ruff check verso tests` clean.
- `agent.inspect(task)` returns a `ContextBundle` whose `to_messages()`/`system`/tools **byte-equal** the arguments the model receives on turn 1 (proven by `test_inspect_byte_equals_what_model_receives`).
- Instructions are sent as the Anthropic `system` param (stable prefix), not a user message.
- When running context exceeds `max_context_tokens`, `prune()` masks the oldest tool outputs (placeholder, structure preserved) and the agent still completes.
- `ContextBundle.stable_prefix()` is byte-identical across turns with the same instructions+tools.

## Deferred to later plans
A real per-provider tokenizer; LLM-based `compact()` summarization (this plan ships only LLM-free `prune()`); `RunContext[T]` injection into tools/hooks; cache-hit telemetry. Then: model-layer depth (Plan 4: failover/retry/`AttemptRecord`), streaming (Plan 5).
