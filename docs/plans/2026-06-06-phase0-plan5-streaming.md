# Verso Phase 0 — Plan 5: Streaming (completes Phase 0)

> **✅ SHIPPED** — implemented test-first, independently rechecked-APPROVED, on `main`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `async for ev in agent.stream(task)` yields a typed, true-delta event stream (step / message.delta / reasoning.delta / tool.start / tool.result / done) as the loop runs, with an SSE transport for shipping it over HTTP.

**Architecture:** A `StreamEvent` value type (7 `EventType`s). A `run_stream()` async generator mirrors `run_loop` but *yields events* instead of returning once. It pulls model output through `iter_model_stream(model, ...)`, which uses `model.stream()` when the model provides one and otherwise **falls back to wrapping `complete()`** into chunks — so every existing model (incl. `FailoverModel`) streams events today. `FakeModel` gains a real `stream()` (text in 2 deltas) so true-delta reassembly is tested offline. `to_sse()` serializes events to `data: {json}\n\n` (terminated by `data: [DONE]\n\n`).

**Tech Stack:** unchanged — Python 3.12 (uv-pinned), Pydantic v2 (unused here), pytest + `FakeModel`. No new dependencies.

**Prereq:** Plans 1–4 merged and green (`uv run pytest` → 99 passed / 1 skipped, on `main`). Paths relative to repo root `~/Desktop/Verso`. Run with `uv run`. **Commit on `main`** (do not create a feature branch). Commit after every green test.

**Out of scope (deferred):** true token-level streaming for the Anthropic provider via `client.messages.stream()` (the event-stream architecture is built so adding `AnthropicModel.stream()` later is a drop-in — until then the fallback emits the answer as one `message.delta`); reasoning/thinking deltas from a real provider (the `reasoning.delta` event type exists and is emitted if a model yields `kind="reasoning"` chunks, but no shipped provider does yet); resumable stream reconnect (`attach(starting_after=N)` — that's a durable-runtime concern, Phase 2).

---

## File Structure

```
verso/
├── stream/
│   ├── __init__.py     # NEW (empty)
│   ├── events.py       # NEW — EventType, StreamEvent
│   └── sse.py          # NEW — to_sse(), sse()
├── model/
│   ├── streaming.py    # NEW — ModelStreamChunk, iter_model_stream()
│   └── fake.py         # MODIFY — add FakeModel.stream()
├── core/
│   └── stream_loop.py  # NEW — run_stream() async generator
├── agent.py            # MODIFY — Agent.stream()
└── __init__.py         # MODIFY — export StreamEvent, EventType
tests/
├── test_events.py
├── test_model_streaming.py
├── test_stream_loop.py
├── test_agent_stream.py
└── test_sse.py
```

---

## Task 1: `StreamEvent` + `EventType`

**Files:**
- Create: `verso/stream/__init__.py` (empty), `verso/stream/events.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_events.py
from verso.stream.events import EventType, StreamEvent


def test_all_seven_event_types():
    vals = {e.value for e in EventType}
    assert vals == {
        "step", "message.delta", "reasoning.delta",
        "tool.start", "tool.result", "error", "done",
    }


def test_message_delta_event():
    ev = StreamEvent(type=EventType.MESSAGE_DELTA, text="hi")
    assert ev.type is EventType.MESSAGE_DELTA and ev.text == "hi"


def test_tool_events():
    start = StreamEvent(type=EventType.TOOL_START, tool="add", arguments={"a": 1})
    res = StreamEvent(type=EventType.TOOL_RESULT, tool="add", ok=True, content="3")
    assert start.tool == "add" and start.arguments == {"a": 1}
    assert res.ok is True and res.content == "3"


def test_step_and_error_and_done():
    assert StreamEvent(type=EventType.STEP, step=2).step == 2
    assert StreamEvent(type=EventType.ERROR, error="boom").error == "boom"
    assert StreamEvent(type=EventType.DONE, result="R").result == "R"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_events.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.stream.events'`.

- [ ] **Step 3: Create `verso/stream/__init__.py` (empty) and `verso/stream/events.py`**

```python
# verso/stream/events.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any


class EventType(str, Enum):
    STEP = "step"                       # a loop step begins
    MESSAGE_DELTA = "message.delta"     # a chunk of the assistant's text answer
    REASONING_DELTA = "reasoning.delta" # a chunk of thinking (separate channel)
    TOOL_START = "tool.start"           # a tool call is about to run
    TOOL_RESULT = "tool.result"         # a tool returned
    ERROR = "error"                     # an error occurred
    DONE = "done"                       # terminal: carries the final AgentResult


@dataclass
class StreamEvent:
    """One true-delta event. Consumers match on `type`; text events are deltas to concatenate."""
    type: EventType
    text: str = ""                       # MESSAGE_DELTA / REASONING_DELTA
    tool: str | None = None              # TOOL_START / TOOL_RESULT
    arguments: dict | None = None        # TOOL_START
    ok: bool | None = None               # TOOL_RESULT
    content: str | None = None           # TOOL_RESULT
    step: int | None = None              # STEP
    error: str | None = None             # ERROR
    result: Any = None                   # DONE (an AgentResult)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_events.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/stream/__init__.py verso/stream/events.py tests/test_events.py
git commit -m "feat(stream): StreamEvent + 7 EventTypes"
```

---

## Task 2: `ModelStreamChunk` + `iter_model_stream` + `FakeModel.stream`

**Files:**
- Create: `verso/model/streaming.py`
- Modify: `verso/model/fake.py`
- Test: `tests/test_model_streaming.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_model_streaming.py
from verso.model.streaming import ModelStreamChunk, iter_model_stream
from verso.model.fake import FakeModel
from verso.model.base import Message, ModelResponse, ToolCall
from verso.types import Usage


async def _collect(aiter):
    return [c async for c in aiter]


async def test_fake_model_streams_text_in_deltas_then_usage():
    fm = FakeModel([ModelResponse(text="hello world", tool_calls=[], usage=Usage(output_tokens=2))])
    chunks = await _collect(fm.stream([Message(role="user", content="hi")], []))
    texts = [c.text for c in chunks if c.kind == "text"]
    assert "".join(texts) == "hello world"
    assert len(texts) >= 2                         # true-delta: more than one piece
    assert chunks[-1].kind == "usage" and chunks[-1].usage.output_tokens == 2
    assert fm.calls and fm.calls[0][0][0].content == "hi"   # recorded the call


async def test_fake_model_streams_tool_calls():
    tc = ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})
    fm = FakeModel([ModelResponse(text="", tool_calls=[tc], usage=Usage())])
    chunks = await _collect(fm.stream([], []))
    tool_chunks = [c for c in chunks if c.kind == "tool_call"]
    assert len(tool_chunks) == 1 and tool_chunks[0].tool_call is tc


class _CompleteOnly:
    """A model with NO stream() — exercises the iter_model_stream fallback."""
    def __init__(self, resp):
        self._resp = resp

    async def complete(self, messages, tools, *, system=None):
        return self._resp


async def test_iter_model_stream_falls_back_to_complete():
    resp = ModelResponse(text="done", tool_calls=[ToolCall(id="t", name="f", arguments={})], usage=Usage(input_tokens=3))
    chunks = await _collect(iter_model_stream(_CompleteOnly(resp), [], []))
    kinds = [c.kind for c in chunks]
    assert kinds == ["text", "tool_call", "usage"]
    assert chunks[0].text == "done"
    assert chunks[2].usage.input_tokens == 3


async def test_iter_model_stream_uses_stream_when_present():
    fm = FakeModel([ModelResponse(text="hi", tool_calls=[], usage=Usage())])
    chunks = await _collect(iter_model_stream(fm, [], []))
    assert any(c.kind == "text" for c in chunks)
    assert len(fm.calls) == 1                       # went through stream(), recorded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_model_streaming.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.model.streaming'`.

- [ ] **Step 3: Create `verso/model/streaming.py`**

```python
# verso/model/streaming.py
from __future__ import annotations
from dataclasses import dataclass
from typing import AsyncIterator, Sequence

from verso.model.base import Message, ModelResponse, ToolCall
from verso.tools.tool import Tool
from verso.types import Usage


@dataclass
class ModelStreamChunk:
    kind: str                          # "text" | "reasoning" | "tool_call" | "usage"
    text: str = ""
    tool_call: ToolCall | None = None
    usage: Usage | None = None


async def _chunks_from_response(resp: ModelResponse) -> AsyncIterator[ModelStreamChunk]:
    if resp.text:
        yield ModelStreamChunk(kind="text", text=resp.text)
    for tc in resp.tool_calls:
        yield ModelStreamChunk(kind="tool_call", tool_call=tc)
    yield ModelStreamChunk(kind="usage", usage=resp.usage)


async def iter_model_stream(model, messages: Sequence[Message], tools: Sequence[Tool],
                            *, system: str | None = None) -> AsyncIterator[ModelStreamChunk]:
    """Stream chunks from `model`: use model.stream() if it has one, else wrap complete().
    This lets the event loop stream over ANY model (incl. FailoverModel / complete-only)."""
    streamer = getattr(model, "stream", None)
    if streamer is not None:
        async for chunk in streamer(messages, tools, system=system):
            yield chunk
        return
    resp = await model.complete(messages, tools, system=system)
    async for chunk in _chunks_from_response(resp):
        yield chunk
```

- [ ] **Step 4: Add `stream()` to `verso/model/fake.py`**

Add this method to `FakeModel` (after `complete`), and add the import at the top:

```python
# at the top of verso/model/fake.py, add:
from verso.model.streaming import ModelStreamChunk
```

```python
    async def stream(self, messages: Sequence[Message], tools: Sequence[Tool],
                     *, system: str | None = None):
        self.calls.append((list(messages), list(tools), system))
        assert self._responses, "FakeModel ran out of scripted responses"
        resp = self._responses.pop(0)
        text = resp.text or ""
        if text:
            mid = len(text) // 2 or len(text)
            for piece in (text[:mid], text[mid:]):
                if piece:
                    yield ModelStreamChunk(kind="text", text=piece)
        for tc in resp.tool_calls:
            yield ModelStreamChunk(kind="tool_call", tool_call=tc)
        yield ModelStreamChunk(kind="usage", usage=resp.usage)
```

> Note: `FakeModel` keeps `complete()` too, so `Agent.run()` (which uses `complete`) is unaffected; only `Agent.stream()` uses `stream()`. Importing `streaming` here is safe (no cycle: `streaming.py` imports only `base`/`tool`/`types`).

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_model_streaming.py -v`
Expected: 4 passed.

- [ ] **Step 6: Run the full suite (no regressions)**

Run: `uv run pytest -q`
Expected: all green — `Agent.run()`/`run_loop` still use `complete()`; nothing else changed.

- [ ] **Step 7: Commit**

```bash
git add verso/model/streaming.py verso/model/fake.py tests/test_model_streaming.py
git commit -m "feat(model): ModelStreamChunk + iter_model_stream (stream-or-complete) + FakeModel.stream"
```

---

## Task 3: `run_stream()` — the streaming loop

**Files:**
- Create: `verso/core/stream_loop.py`
- Test: `tests/test_stream_loop.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stream_loop.py
from verso.core.stream_loop import run_stream
from verso.stream.events import EventType
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.tool import tool
from verso.tools.builtins import done
from verso.types import StopReason, Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def _events(aiter):
    return [ev async for ev in aiter]


async def test_stream_tool_then_text():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text="the answer is 3", tool_calls=[], usage=Usage(output_tokens=4)),
    ])
    evs = await _events(run_stream(fm, [add], "add 1 and 2"))
    types = [e.type for e in evs]
    assert types[0] is EventType.STEP
    assert EventType.TOOL_START in types and EventType.TOOL_RESULT in types
    assert types[-1] is EventType.DONE
    # true-delta: concatenated message deltas == the final text
    text = "".join(e.text for e in evs if e.type is EventType.MESSAGE_DELTA)
    assert text == "the answer is 3"
    final = evs[-1].result
    assert final.output == "the answer is 3" and final.stop_reason is StopReason.END_TURN


async def test_stream_tool_start_and_result_payload():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 4, "b": 5})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    evs = await _events(run_stream(fm, [add], "go"))
    start = next(e for e in evs if e.type is EventType.TOOL_START)
    result = next(e for e in evs if e.type is EventType.TOOL_RESULT)
    assert start.tool == "add" and start.arguments == {"a": 4, "b": 5}
    assert result.tool == "add" and result.ok is True and result.content == "9"


async def test_stream_done_tool_terminates():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="d", name="done", arguments={"result": "final"})], usage=Usage()),
    ])
    evs = await _events(run_stream(fm, [done], "finish"))
    assert evs[-1].type is EventType.DONE
    assert evs[-1].result.output == "final" and evs[-1].result.stop_reason is StopReason.DONE


async def test_stream_hits_max_steps():
    looping = [ModelResponse(text="", tool_calls=[ToolCall(id=f"t{i}", name="add", arguments={"a": 1, "b": 1})], usage=Usage()) for i in range(5)]
    evs = await _events(run_stream(FakeModel(looping), [add], "loop", max_steps=2))
    assert evs[-1].type is EventType.DONE and evs[-1].result.stop_reason is StopReason.MAX_STEPS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_stream_loop.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.core.stream_loop'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/core/stream_loop.py
from __future__ import annotations
from typing import AsyncIterator, Sequence

from verso.context.prune import prune
from verso.core.loop import _format_result, build_bundle
from verso.model.base import Message, Model
from verso.model.streaming import iter_model_stream
from verso.stream.events import EventType, StreamEvent
from verso.tools.dispatch import dispatch
from verso.tools.tool import Tool
from verso.types import AgentResult, StopReason, Usage


async def run_stream(model: Model, tools: Sequence[Tool], task: str,
                     max_steps: int = 25, instructions: str | None = None,
                     max_context_tokens: int | None = None) -> AsyncIterator[StreamEvent]:
    bundle = build_bundle(tools, task, instructions)
    tool_map = {t.name: t for t in tools}
    usage = Usage()

    for step in range(1, max_steps + 1):
        yield StreamEvent(type=EventType.STEP, step=step)
        if max_context_tokens is not None and bundle.estimate_tokens() > max_context_tokens:
            bundle.history = prune(bundle.history)

        text_parts: list[str] = []
        tool_calls = []
        async for chunk in iter_model_stream(model, bundle.to_messages(), bundle.tools, system=bundle.system):
            if chunk.kind == "text":
                text_parts.append(chunk.text)
                yield StreamEvent(type=EventType.MESSAGE_DELTA, text=chunk.text)
            elif chunk.kind == "reasoning":
                yield StreamEvent(type=EventType.REASONING_DELTA, text=chunk.text)
            elif chunk.kind == "tool_call" and chunk.tool_call is not None:
                tool_calls.append(chunk.tool_call)
            elif chunk.kind == "usage" and chunk.usage is not None:
                usage = usage + chunk.usage

        text = "".join(text_parts)
        if not tool_calls:
            yield StreamEvent(type=EventType.DONE, result=AgentResult(
                output=text, stop_reason=StopReason.END_TURN, usage=usage, steps=step))
            return

        bundle.history.append(Message(role="assistant", content=text, tool_calls=tool_calls))
        for tc in tool_calls:
            yield StreamEvent(type=EventType.TOOL_START, tool=tc.name, arguments=tc.arguments)
            t = tool_map.get(tc.name)
            if t is None:
                content, ok = f"Error: unknown tool '{tc.name}'.", False
            else:
                res = await dispatch(t, tc.arguments)
                content = _format_result(res.data) if res.ok else f"Error: {res.error}"
                ok = res.ok
            yield StreamEvent(type=EventType.TOOL_RESULT, tool=tc.name, ok=ok, content=content)
            if tc.name == "done" and ok:
                yield StreamEvent(type=EventType.DONE, result=AgentResult(
                    output=content, stop_reason=StopReason.DONE, usage=usage, steps=step))
                return
            bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

    yield StreamEvent(type=EventType.DONE, result=AgentResult(
        output="", stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_stream_loop.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add verso/core/stream_loop.py tests/test_stream_loop.py
git commit -m "feat(core): run_stream async generator (typed event stream over the loop)"
```

---

## Task 4: `Agent.stream()` + exports

**Files:**
- Modify: `verso/agent.py`, `verso/__init__.py`
- Test: `tests/test_agent_stream.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent_stream.py
from verso import Agent, StreamEvent, EventType
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.tools.tool import tool
from verso.types import Usage, StopReason


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def test_agent_stream_yields_events_and_final_result():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 2, "b": 2})], usage=Usage()),
        ModelResponse(text="4", tool_calls=[], usage=Usage()),
    ])
    evs = [ev async for ev in Agent(model=fm, tools=[add]).stream("2+2?")]
    assert all(isinstance(e, StreamEvent) for e in evs)
    assert evs[-1].type is EventType.DONE
    assert evs[-1].result.output == "4" and evs[-1].result.stop_reason is StopReason.END_TURN


async def test_agent_stream_threads_instructions_and_budget():
    fm = FakeModel([ModelResponse(text="ok", tool_calls=[], usage=Usage())])
    agent = Agent(model=fm, instructions="be terse")
    _ = [ev async for ev in agent.stream("hi")]
    # instructions routed as system on the (stream) call
    assert fm.calls[0][2] == "be terse"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agent_stream.py -v`
Expected: FAIL — `ImportError: cannot import name 'StreamEvent' from 'verso'` (and no `Agent.stream`).

- [ ] **Step 3: Add `stream()` to `verso/agent.py`**

Add the import and the method (place `stream` after `run`):

```python
# add to imports in verso/agent.py:
from typing import AsyncIterator
from verso.core.stream_loop import run_stream
from verso.stream.events import StreamEvent
```

```python
    async def stream(self, task: str) -> AsyncIterator[StreamEvent]:
        async for ev in run_stream(self.model, self.tools, task, max_steps=self.max_steps,
                                   instructions=self.instructions,
                                   max_context_tokens=self.max_context_tokens):
            yield ev
```

- [ ] **Step 4: Export from `verso/__init__.py`**

Add:

```python
from verso.stream.events import StreamEvent, EventType
```

Append `"StreamEvent"`, `"EventType"` to `__all__`.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_agent_stream.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add verso/agent.py verso/__init__.py tests/test_agent_stream.py
git commit -m "feat: Agent.stream() typed event stream + exports"
```

---

## Task 5: SSE transport + e2e + README

**Files:**
- Create: `verso/stream/sse.py`
- Test: `tests/test_sse.py`
- Modify: extend `tests/test_e2e.py`, `README.md`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sse.py
import json
from verso.stream.sse import to_sse, sse
from verso.stream.events import EventType, StreamEvent
from verso.types import AgentResult, StopReason, Usage


def _parse(line: str) -> dict:
    assert line.startswith("data: ") and line.endswith("\n\n")
    return json.loads(line[len("data: "):].strip())


def test_to_sse_message_delta():
    payload = _parse(to_sse(StreamEvent(type=EventType.MESSAGE_DELTA, text="hi")))
    assert payload == {"type": "message.delta", "text": "hi"}


def test_to_sse_tool_result_omits_empty_fields():
    payload = _parse(to_sse(StreamEvent(type=EventType.TOOL_RESULT, tool="add", ok=True, content="3")))
    assert payload == {"type": "tool.result", "tool": "add", "ok": True, "content": "3"}


def test_to_sse_done_serializes_result():
    r = AgentResult(output="42", stop_reason=StopReason.END_TURN, usage=Usage(input_tokens=5, output_tokens=2), steps=3)
    payload = _parse(to_sse(StreamEvent(type=EventType.DONE, result=r)))
    assert payload["type"] == "done"
    assert payload["result"]["output"] == "42"
    assert payload["result"]["stop_reason"] == "end_turn"
    assert payload["result"]["usage"] == {"input_tokens": 5, "output_tokens": 2}
    assert payload["result"]["steps"] == 3


async def test_sse_stream_terminates_with_done_sentinel():
    async def gen():
        yield StreamEvent(type=EventType.MESSAGE_DELTA, text="a")
        yield StreamEvent(type=EventType.DONE, result=AgentResult("a", StopReason.END_TURN, Usage(), 1))
    lines = [line async for line in sse(gen())]
    assert lines[-1] == "data: [DONE]\n\n"
    assert _parse(lines[0]) == {"type": "message.delta", "text": "a"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'verso.stream.sse'`.

- [ ] **Step 3: Write the implementation**

```python
# verso/stream/sse.py
from __future__ import annotations
import json
from typing import AsyncIterator

from verso.stream.events import StreamEvent
from verso.types import AgentResult


def _result_dict(r: AgentResult) -> dict:
    return {
        "output": r.output,
        "stop_reason": r.stop_reason.value,
        "steps": r.steps,
        "usage": {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens},
    }


def to_sse(event: StreamEvent) -> str:
    """Serialize one event as an SSE frame: `data: {json}\\n\\n`. Empty/None fields are omitted."""
    payload: dict = {"type": event.type.value}
    for key in ("text", "tool", "arguments", "ok", "content", "step", "error"):
        val = getattr(event, key)
        if val is not None and val != "":
            payload[key] = val
    if event.result is not None:
        payload["result"] = _result_dict(event.result) if isinstance(event.result, AgentResult) else event.result
    return f"data: {json.dumps(payload, default=str)}\n\n"


async def sse(events: AsyncIterator[StreamEvent]) -> AsyncIterator[str]:
    """Wrap an event stream as SSE frames, terminated by `data: [DONE]\\n\\n`."""
    async for ev in events:
        yield to_sse(ev)
    yield "data: [DONE]\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sse.py -v`
Expected: 4 passed.

- [ ] **Step 5: Append the offline e2e test to `tests/test_e2e.py`**

```python
# --- appended: streaming, offline ---
async def test_e2e_stream_and_sse_offline():
    from verso import Agent, EventType
    from verso.stream.sse import sse
    from verso.model.fake import FakeModel
    from verso.model.base import ModelResponse
    from verso.types import Usage
    fm = FakeModel([ModelResponse(text="hello", tool_calls=[], usage=Usage())])
    agent = Agent(model=fm)
    events = [e async for e in agent.stream("hi")]
    assert "".join(e.text for e in events if e.type is EventType.MESSAGE_DELTA) == "hello"
    assert events[-1].type is EventType.DONE

    fm2 = FakeModel([ModelResponse(text="hello", tool_calls=[], usage=Usage())])
    lines = [ln async for ln in sse(Agent(model=fm2).stream("hi"))]
    assert lines[-1] == "data: [DONE]\n\n"
```

- [ ] **Step 6: Append to `README.md` Quickstart (before `## Status`)**

````markdown
**Streaming** — a typed, true-delta event stream (and SSE for HTTP):

```python
async for ev in agent.stream("What is 2+2? Use the add tool."):
    if ev.type.value == "message.delta":
        print(ev.text, end="", flush=True)
    elif ev.type.value == "tool.start":
        print(f"\n[calling {ev.tool}({ev.arguments})]")
    elif ev.type.value == "done":
        print("\n", ev.result.stop_reason)

# ship it over HTTP:
from verso.stream.sse import sse
async for frame in sse(agent.stream("...")):   # 'data: {json}\n\n' ... 'data: [DONE]\n\n'
    ...
```
````

- [ ] **Step 7: Full suite + lint**

Run: `uv run pytest -q` → all green (live skipped). Then `uv run ruff check verso tests` → clean.

- [ ] **Step 8: Commit**

```bash
git add verso/stream/sse.py tests/test_sse.py tests/test_e2e.py README.md
git commit -m "feat(stream): SSE transport; e2e stream/sse; README streaming snippet"
```

---

## Done criteria (Plan 5 — and Phase 0)

- `uv run pytest -q` green (live skipped); `uv run ruff check verso tests` clean.
- `async for ev in agent.stream(task)` yields `StreamEvent`s ending in a `DONE` event whose `result` is the `AgentResult`; concatenated `message.delta` texts equal the final answer (true-delta); `tool.start`/`tool.result` carry the call + outcome.
- Streaming works over a complete-only model (via `iter_model_stream` fallback) and over `FakeModel`'s real `stream()`; `Agent.run()` is unchanged.
- `to_sse(event)` emits `data: {json}\n\n`; `sse(events)` terminates with `data: [DONE]\n\n`.

**Phase 0 is complete:** a clean async ReAct loop · native typed `@tool` + safe dispatch + `jsonish`→Pydantic structured output · first-class inspectable/budgeted/cache-disciplined context · retry + cross-model failover · and a typed streaming event surface with SSE.

## Deferred to later phases
True token-level Anthropic streaming (`AnthropicModel.stream()` — drop-in via the existing adapter); real reasoning deltas; resumable stream reconnect (`attach(starting_after=N)`, Phase 2 durable runtime); then Phase 1 (memory + eval over proxies) and Phase 2 (the durable seam over DBOS).
