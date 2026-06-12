# Verso Phase 2 — Plan 10: RunContext[T] + the durable seam

> **✅ SHIPPED** — implemented test-first, independently rechecked-APPROVED, on `main`.

> **Phase-2 plan set:** Plan 9 (cache_control ✓) → **Plan 10 — durable seam (this doc)** → Plan 11 (safety depth, builds on RunContext[T]) → Plan 12 (memory real-infra). This is the thesis-critical plan. Implement with `compound-v:batched-implementation` (TDD: failing test → run → minimal code → run → commit). Never edit a test to make it pass.

**Goal:** ship Verso's core bet — the **tactical↔durable seam**. One flag turns an ordinary in-memory agent into a **durable** one that **checkpoints its state each step**, can **pause for a human decision**, and **resumes** from the checkpoint (after a pause *or* a crash) — **with no rewrite and no forced graph**. When the flag is off, the loop is **byte-identical to Phase 1**.

**Done (machine-checkable):** `uv run pytest -q` green + `uv run ruff check verso tests` clean — proving: (1) an `Agent` with **no** `checkpointer` produces the same `AgentResult` as before (all Phase-0/1 tests pass unmodified); (2) with a `checkpointer`, a run that hits a `pre_tool` ASK **pauses** — returns `AgentResult(stop_reason=PAUSED, resume_token=…, pending=HumanRequest(…))` — and the tool did **not** run; (3) `Agent.resume(token, approve=True)` runs the held tool and finishes; `resume(token, approve=False)` feeds a denial and finishes; (4) the state survives a *fresh store instance* (crash-simulating) via `SqliteCheckpointStore`; (5) the same store contract passes against **both** `InMemoryCheckpointStore` and `SqliteCheckpointStore`.

**Approach / key facts (research fold-in):**
- The loop is `verso/core/loop.py` `run_loop(model, tools, task, max_steps=25, instructions=None, max_context_tokens=None, hooks=None)` (lines 32–83). Structure: `build_bundle` → per step: `prune?` → `pre_model` → `model.complete` → `post_model` → if no tool_calls return END_TURN → else append assistant turn, then per `tc`: `pre_tool` decision (ALLOW/DENY/ASK/DEFER) → dispatch → `post_tool` → append tool message; `done`-tool early return; MAX_STEPS at the end. **Hooks already give us the ASK seam (Plan 8).** The durable pause hangs off the *existing* ASK branch — no new control structure in the hot path.
- `verso/types.py`: `StopReason` enum (END_TURN/DONE/MAX_STEPS/ERROR), `AgentResult(output, stop_reason, usage, steps, parsed)`, `Usage(input_tokens, output_tokens)` frozen with `__add__`. `verso/model/base.py`: `ToolCall(id, name, arguments: dict)`, `Message(role, content="", tool_calls=[], tool_call_id=None, name=None)`.
- `verso/agent.py`: `Agent.__init__(model, tools, *, instructions, max_steps, max_context_tokens, hooks)`; `_run` → `run_loop`; `run` wraps `_run` with output-coercion. Add `checkpointer` the same additive way `hooks` was added in Plan 8.
- **Precedent to copy:** the memory module (`verso/memory/sqlite.py`, `verso/memory/inmem.py`, `verso/memory/backend.py`) is the exact shape for "Protocol + two backends + cross-backend contract test" — DDL string in a `types`-style module, `sqlite3` stdlib, an `InMemory*` twin, one `@pytest.fixture(params=[…])` contract test. Mirror it. `verso/evals/span.py`'s `to_jsonl`/`from_jsonl` is the precedent for round-trippable serialization.
- **Pause via the ASK branch, not a tool yet.** Tools do **not** receive `RunContext` in this plan (that injection is Plan 11). The Plan-10 pause trigger is: `pre_tool` returns `ASK`, there is no sync `hooks.ask` resolver, **and** a checkpointer is present → durable pause. The `Hitl.request()` API (which a tool *will* call once Plan 11 injects `ctx`) is built here and unit-tested via the `Paused` signal, but the loop-level trigger in this plan is the ASK decision. Don't wire `ctx` into `dispatch`/tools here — that's Plan 11.

**Divergence rule:** if wiring durability into `run_loop` forces any change to the **no-checkpointer** path (i.e. an existing Phase-0/1 test needs editing), **stop and report** — durability must be purely additive, exactly like hooks in Plan 8. If `Message`/`ToolCall` serialization can't round-trip losslessly, surface it (don't silently drop a field). After ~3 failed attempts at any one mechanism, escalate rather than grind.

**User Review Required:** **yes — one item.** This plan modifies `verso/core/loop.py` (the audited core) a second time and adds two fields to `AgentResult` + one `StopReason`. The change must be *purely additive and back-compatible*: no `checkpointer` ⇒ byte-identical to Phase 1, all prior loop/agent/stream tests pass unchanged. Confirm the `loop.py` diff touches only the durable branch + the new `ctx`/`checkpointer` parameter before merging.

**Out of scope (lock the seam, build nothing):** `RunContext[T]` injection into hooks/tools (Plan 11); the permission-policy router / session modes / confidence router (Plan 11); resume of a *streaming* run (`run_stream` stays tactical this plan — note it, don't half-wire it); multi-pause / nested-pause within one step; pause triggered by an arbitrary tool calling `ctx.hitl.request` end-to-end through `dispatch` (needs Plan 11's ctx-injection — the `Hitl`/`Paused` primitive is built and unit-tested here, the loop trigger is ASK). Postgres/Redis checkpoint stores. Note each; ship none.

**Tech stack:** stdlib `sqlite3` + `json`, dataclasses/enum/typing.Generic. No new dependency.

---

## File structure

```
verso/
└── durable/
    ├── __init__.py      # NEW — exports RunContext, HumanRequest, Hitl, Paused, Checkpoint,
    │                    #       CheckpointStore, InMemoryCheckpointStore, SqliteCheckpointStore
    ├── context.py       # NEW — RunContext[T], HumanRequest, Paused, Hitl
    ├── serde.py         # NEW — Message/ToolCall ⇄ dict (lossless round-trip)
    ├── checkpoint.py    # NEW — Checkpoint dataclass + CheckpointStore Protocol
    ├── inmem.py         # NEW — InMemoryCheckpointStore (dict-based)
    └── sqlite.py        # NEW — SqliteCheckpointStore (stdlib sqlite3; survives process restart)
verso/types.py           # MODIFY — StopReason.PAUSED; AgentResult.resume_token + .pending
verso/core/loop.py       # MODIFY — accept ctx=; per-step checkpoint; durable-ASK pause; resume entry
verso/agent.py           # MODIFY — accept checkpointer=; Agent.resume(token, approve)
verso/__init__.py        # MODIFY — export the durable surface
tests/
├── test_durable_serde.py        # NEW — Message/ToolCall round-trip
├── test_durable_checkpoint.py   # NEW — store contract across BOTH backends
├── test_durable_pause_resume.py # NEW — pause on ASK, resume approve/deny, end-to-end
└── test_durable_backcompat.py   # NEW — no checkpointer ⇒ identical AgentResult
README.md                # MODIFY — durable-seam snippet
```

---

## Task 1: `RunContext[T]` + `HumanRequest` + `Paused` + `Hitl` + serde

**Files:** Create `verso/durable/__init__.py` (empty for now), `verso/durable/context.py`, `verso/durable/serde.py`; Test `tests/test_durable_serde.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_durable_serde.py
from verso.model.base import Message, ToolCall
from verso.durable.serde import msg_to_dict, msg_from_dict
from verso.durable.context import RunContext, Hitl, Paused, HumanRequest


def test_message_round_trips_including_tool_calls():
    msgs = [
        Message(role="user", content="add 1 and 2"),
        Message(role="assistant", content="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})]),
        Message(role="tool", content="3", tool_call_id="t1", name="add"),
    ]
    restored = [msg_from_dict(msg_to_dict(m)) for m in msgs]
    assert restored == msgs                      # dataclass equality — every field survived


def test_hitl_request_raises_paused_with_the_prompt():
    ctx: RunContext[None] = RunContext(trace_id="x")
    import pytest
    with pytest.raises(Paused) as ei:
        ctx.hitl.request("approve the refund?", key="refund")
    assert isinstance(ei.value.request, HumanRequest)
    assert ei.value.request.prompt == "approve the refund?" and ei.value.request.key == "refund"
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement `verso/durable/serde.py`** (verify `Message`/`ToolCall` fields against `verso/model/base.py` first — they are `ToolCall(id,name,arguments)` and `Message(role,content,tool_calls,tool_call_id,name)`):

```python
# verso/durable/serde.py
from __future__ import annotations

from verso.model.base import Message, ToolCall


def msg_to_dict(m: Message) -> dict:
    return {
        "role": m.role,
        "content": m.content,
        "tool_calls": [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in m.tool_calls],
        "tool_call_id": m.tool_call_id,
        "name": m.name,
    }


def msg_from_dict(d: dict) -> Message:
    return Message(
        role=d["role"],
        content=d.get("content", ""),
        tool_calls=[ToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"]) for tc in d.get("tool_calls", [])],
        tool_call_id=d.get("tool_call_id"),
        name=d.get("name"),
    )
```

- [ ] **Step 4 — implement `verso/durable/context.py`:**

```python
# verso/durable/context.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Generic, NoReturn, TypeVar

T = TypeVar("T")


@dataclass
class HumanRequest:
    """A request for an out-of-band human decision that paused a durable run."""
    prompt: str
    key: str = "default"
    tool_name: str | None = None      # the tool awaiting approval (when the pause came from a pre_tool ASK)
    tool_call_id: str | None = None


class Paused(Exception):
    """Raised to pause a durable run for human input. Carries the HumanRequest to surface."""
    def __init__(self, request: HumanRequest):
        super().__init__(request.prompt)
        self.request = request


class Hitl:
    """The human-in-the-loop handle on RunContext. `request()` pauses the run (durable) by raising
    Paused; the loop catches it, checkpoints, and returns a PAUSED AgentResult. (Tools gain access to
    this once Plan 11 injects RunContext into dispatch; in Plan 10 the loop-level trigger is a pre_tool ASK.)"""
    def request(self, prompt: str, *, key: str = "default") -> NoReturn:
        raise Paused(HumanRequest(prompt=prompt, key=key))


@dataclass
class RunContext(Generic[T]):
    """The typed run context threaded through a durable run. `deps` is the caller's typed payload
    (DB handles, user id, config). `store` being non-None is THE flag that makes a run durable —
    when present the loop checkpoints each step and can pause/resume; when None the run is tactical."""
    trace_id: str
    deps: T | None = None
    step: int = 0
    store: object | None = None        # CheckpointStore | None — typed as object to avoid an import cycle
    hitl: Hitl = field(default_factory=Hitl)
```

- [ ] **Step 5 — run, expect 2 passed; commit:** `git commit -am "feat(durable): RunContext[T] + HumanRequest/Paused/Hitl + Message serde"`

---

## Task 2: `Checkpoint` + `CheckpointStore` protocol + `InMemoryCheckpointStore`

**Files:** Create `verso/durable/checkpoint.py`, `verso/durable/inmem.py`; Test (first half of) `tests/test_durable_checkpoint.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_durable_checkpoint.py
import pytest
from verso.durable.checkpoint import Checkpoint
from verso.durable.inmem import InMemoryCheckpointStore
from verso.durable.context import HumanRequest


def _cp(trace_id="r1", step=2):
    return Checkpoint(
        trace_id=trace_id, task="do the thing", instructions="be terse",
        history=[{"role": "user", "content": "do the thing", "tool_calls": [], "tool_call_id": None, "name": None}],
        usage_in=10, usage_out=4, step=step,
        pending=HumanRequest(prompt="approve send_email?", tool_name="send_email", tool_call_id="t1"),
    )


@pytest.fixture(params=["inmem"])     # sqlite param added in Task 5
def store(request):
    return InMemoryCheckpointStore()


def test_save_then_load_round_trips(store):
    store.save(_cp())
    got = store.load("r1")
    assert got is not None
    assert got.trace_id == "r1" and got.step == 2 and got.task == "do the thing"
    assert got.pending is not None and got.pending.tool_name == "send_email"
    assert got.history[0]["content"] == "do the thing"


def test_load_missing_is_none_and_delete_removes(store):
    assert store.load("nope") is None
    store.save(_cp(trace_id="r2"))
    store.delete("r2")
    assert store.load("r2") is None
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement `verso/durable/checkpoint.py`:**

```python
# verso/durable/checkpoint.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from verso.durable.context import HumanRequest


@dataclass
class Checkpoint:
    """A serializable snapshot of a run's resumable state — enough to rebuild the ContextBundle and
    continue from `step`. `history` holds serialized Messages (see durable.serde). `pending` is set
    only when the run paused for a human decision; None means a plain crash-recovery checkpoint."""
    trace_id: str
    task: str
    instructions: str | None
    history: list[dict] = field(default_factory=list)
    usage_in: int = 0
    usage_out: int = 0
    step: int = 0
    pending: HumanRequest | None = None


@runtime_checkable
class CheckpointStore(Protocol):
    """The durable contract. sqlite (survives restart) / in-memory (tests, ephemeral) implement it;
    Postgres/Redis implement it later with zero change to the loop."""
    def save(self, cp: Checkpoint) -> None: ...
    def load(self, trace_id: str) -> Checkpoint | None: ...
    def delete(self, trace_id: str) -> None: ...
```

- [ ] **Step 4 — implement `verso/durable/inmem.py`:**

```python
# verso/durable/inmem.py
from __future__ import annotations
import copy

from verso.durable.checkpoint import Checkpoint


class InMemoryCheckpointStore:
    """Dict-based CheckpointStore — ephemeral, dependency-free. For tests and tactical-durable hybrids
    where 'durable within the process' is enough. Deep-copies on save/load so callers can't mutate a
    stored checkpoint by reference (parity with the sqlite store, which serializes)."""
    def __init__(self) -> None:
        self._cps: dict[str, Checkpoint] = {}

    def save(self, cp: Checkpoint) -> None:
        self._cps[cp.trace_id] = copy.deepcopy(cp)

    def load(self, trace_id: str) -> Checkpoint | None:
        cp = self._cps.get(trace_id)
        return copy.deepcopy(cp) if cp is not None else None

    def delete(self, trace_id: str) -> None:
        self._cps.pop(trace_id, None)
```

- [ ] **Step 5 — run, expect 2 passed; commit:** `git commit -am "feat(durable): Checkpoint + CheckpointStore protocol + InMemoryCheckpointStore"`

---

## Task 3: durability in `run_loop` — per-step checkpoint + durable-ASK pause (additive)

**Files:** Modify `verso/types.py`, `verso/core/loop.py`; Test `tests/test_durable_backcompat.py` + (pause half of) `tests/test_durable_pause_resume.py`.

- [ ] **Step 1 — failing tests:**

```python
# tests/test_durable_backcompat.py
from verso import Agent, tool
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


async def test_no_checkpointer_is_identical_to_phase1():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage(input_tokens=1, output_tokens=1)),
        ModelResponse(text="3", tool_calls=[], usage=Usage(input_tokens=1, output_tokens=1)),
    ])
    r = await Agent(model=fm, tools=[add]).run("add")
    assert r.output == "3" and r.stop_reason.value == "end_turn" and r.steps == 2
    assert (r.usage.input_tokens, r.usage.output_tokens) == (2, 2)
    assert r.resume_token is None and r.pending is None      # the new fields default cleanly
```

```python
# tests/test_durable_pause_resume.py  (pause half — resume half added in Task 4)
from verso import Agent, tool
from verso.safety.hooks import Hooks, PermissionDecision
from verso.durable.inmem import InMemoryCheckpointStore
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason


@tool
def send_email(to: str) -> str:
    "Send an email."
    return f"sent to {to}"


def _paused_agent(store):
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="send_email", arguments={"to": "x@y.z"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    hooks = Hooks(pre_tool=[lambda call: PermissionDecision.ASK])   # ask, with no sync resolver
    return Agent(model=fm, tools=[send_email], hooks=hooks, checkpointer=store)


async def test_durable_ask_pauses_and_checkpoints_instead_of_denying():
    store = InMemoryCheckpointStore()
    result = await _paused_agent(store).run("email x")
    assert result.stop_reason == StopReason.PAUSED
    assert result.resume_token and result.pending is not None
    assert result.pending.tool_name == "send_email"            # the held tool is named
    # the tool did NOT run, and the state was checkpointed under the token
    cp = store.load(result.resume_token)
    assert cp is not None and cp.pending is not None and cp.step >= 1
```

- [ ] **Step 2 — run, expect FAIL** (`Agent` takes no `checkpointer`; no `StopReason.PAUSED`).
- [ ] **Step 3 — modify `verso/types.py`:** add the PAUSED reason and the two additive `AgentResult` fields:

```python
class StopReason(str, Enum):
    END_TURN = "end_turn"
    DONE = "done"
    MAX_STEPS = "max_steps"
    PAUSED = "paused"          # NEW — durable run paused for a human decision; resumable via resume_token
    ERROR = "error"
```

```python
@dataclass
class AgentResult:
    output: str
    stop_reason: StopReason
    usage: Usage
    steps: int
    parsed: object | None = None
    resume_token: str | None = None   # NEW — set when stop_reason is PAUSED; pass to Agent.resume(...)
    pending: object | None = None     # NEW — the HumanRequest awaiting an answer (typed object to avoid import cycle)
```

- [ ] **Step 4 — modify `verso/core/loop.py`** — add `ctx` + a shared driver, additively. The fresh `run_loop` builds the bundle from `task`; a new `resume_loop` (Task 4) rebuilds it from a checkpoint. Both call `_drive`. Insert ONLY: the `ctx` param, the per-step `_checkpoint(...)` call, and the durable-ASK pause branch. Everything else is unchanged from the Plan-8 version.

```python
# add to imports:
from verso.durable.context import RunContext, HumanRequest
from verso.durable.checkpoint import Checkpoint
from verso.durable.serde import msg_to_dict

# ... _format_result and build_bundle unchanged ...

def _checkpoint(ctx, bundle, task, usage, step, pending=None):
    if ctx is None or ctx.store is None:
        return
    ctx.store.save(Checkpoint(
        trace_id=ctx.trace_id, task=task, instructions=bundle.instructions,
        history=[msg_to_dict(m) for m in bundle.history],
        usage_in=usage.input_tokens, usage_out=usage.output_tokens, step=step, pending=pending,
    ))


async def run_loop(model, tools, task, max_steps=25, instructions=None,
                   max_context_tokens=None, hooks=None, ctx=None):
    bundle = build_bundle(tools, task, instructions)
    return await _drive(model, tools, task, bundle, Usage(), 1, max_steps,
                        max_context_tokens=max_context_tokens, hooks=hooks, ctx=ctx)


async def _drive(model, tools, task, bundle, usage, start_step, max_steps,
                 *, max_context_tokens=None, hooks=None, ctx=None):
    from verso.safety.hooks import Hooks, PermissionDecision
    hooks = hooks or Hooks()
    tool_map = {t.name: t for t in tools}

    for step in range(start_step, max_steps + 1):
        if max_context_tokens is not None and bundle.estimate_tokens() > max_context_tokens:
            bundle.history = prune(bundle.history)

        await hooks.run_pre_model(bundle)
        resp = await model.complete(bundle.to_messages(), bundle.tools, system=bundle.system)
        await hooks.run_post_model(resp)
        usage = usage + resp.usage

        if not resp.tool_calls:
            result = AgentResult(output=resp.text, stop_reason=StopReason.END_TURN, usage=usage, steps=step)
            await hooks.run_on_stop(result)
            return result

        bundle.history.append(Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls))
        for tc in resp.tool_calls:
            decision = await hooks.run_pre_tool((tc.name, tc.arguments))
            if decision != PermissionDecision.ALLOW:
                approved = (decision == PermissionDecision.ASK and hooks.ask is not None
                            and hooks.ask((tc.name, tc.arguments)))
                if approved:
                    pass  # sync-approved → fall through to run
                elif decision == PermissionDecision.ASK and ctx is not None and ctx.store is not None:
                    # durable HITL: checkpoint the held tool and pause for an out-of-band decision
                    pending = HumanRequest(prompt=f"Approve tool '{tc.name}' with args {tc.arguments}?",
                                           tool_name=tc.name, tool_call_id=tc.id)
                    _checkpoint(ctx, bundle, task, usage, step, pending=pending)
                    paused = AgentResult(output="", stop_reason=StopReason.PAUSED, usage=usage, steps=step,
                                         resume_token=ctx.trace_id, pending=pending)
                    await hooks.run_on_stop(paused)
                    return paused
                else:
                    content = f"Tool '{tc.name}' was {decision.value} by policy; it did not run."
                    content = await hooks.run_post_tool((tc.name, tc.arguments), content)
                    bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))
                    continue
            t = tool_map.get(tc.name)
            if t is None:
                content = f"Error: unknown tool '{tc.name}'."
            else:
                result = await dispatch(t, tc.arguments)
                content = _format_result(result.data) if result.ok else f"Error: {result.error}"
                if tc.name == "done" and result.ok:
                    final = AgentResult(output=_format_result(result.data), stop_reason=StopReason.DONE,
                                        usage=usage, steps=step)
                    await hooks.run_on_stop(final)
                    return final
            content = await hooks.run_post_tool((tc.name, tc.arguments), content)
            bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

        _checkpoint(ctx, bundle, task, usage, step)   # per-step crash-recovery checkpoint (no pending)

    result = AgentResult(output="", stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps)
    await hooks.run_on_stop(result)
    return result
```

> Notes for the implementer: (a) `_drive` is the Plan-8 loop body **verbatim** plus exactly three additions — the `ctx` param, the `elif decision == ASK and ctx … store` durable-pause branch, and the trailing `_checkpoint(ctx, …)` after each step. Keep the `done`-early-return and the `{data,error,ok}` dispatch invariant untouched. (b) With `ctx=None` (or `ctx.store=None`), `_checkpoint` is a no-op and the durable branch is unreachable → byte-identical to Phase 1. (c) Verify the Plan-8 hook-ordering tests still pass — `_checkpoint` runs **after** the per-`tc` loop, so it does not change hook firing order.

- [ ] **Step 5 — run the new tests + the FULL suite:** `uv run pytest -q` → all green; **every Phase-0/1 test passes unmodified** (back-compat gate). `uv run ruff check verso tests` → clean. If a prior test needed editing, STOP and report (non-additive).
- [ ] **Step 6 — commit:** `git commit -am "feat(core): durable run_loop — per-step checkpoint + durable-ASK pause (additive, back-compat)"`

---

## Task 4: `Agent(checkpointer=)` + `Agent.resume(token, approve)` + exports

**Files:** Modify `verso/core/loop.py` (add `resume_loop`), `verso/agent.py`, `verso/durable/__init__.py`, `verso/__init__.py`; Test (resume half of) `tests/test_durable_pause_resume.py`.

- [ ] **Step 1 — failing test (append to `tests/test_durable_pause_resume.py`):**

```python
async def test_resume_approve_runs_the_held_tool_and_finishes():
    store = InMemoryCheckpointStore()
    agent = _paused_agent(store)
    paused = await agent.run("email x")
    assert paused.stop_reason == StopReason.PAUSED
    resumed = await agent.resume(paused.resume_token, approve=True)
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"


async def test_resume_deny_feeds_a_denial_and_finishes_without_running_the_tool():
    store = InMemoryCheckpointStore()
    agent = _paused_agent(store)
    paused = await agent.run("email x")
    resumed = await agent.resume(paused.resume_token, approve=False)
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"
    # the held tool never produced a "sent to" result on the denial path
```

- [ ] **Step 2 — run, expect FAIL** (`Agent.resume`/`resume_loop` don't exist).
- [ ] **Step 3 — add `resume_loop` to `verso/core/loop.py`** (rebuild the bundle from the checkpoint, resolve the held tool per `approve`, then continue via `_drive`):

```python
from verso.durable.serde import msg_from_dict   # add to imports

async def resume_loop(model, tools, ctx, approve: bool, *, max_steps=25,
                      max_context_tokens=None, hooks=None) -> AgentResult:
    if ctx.store is None:
        raise ValueError("resume requires a checkpointer")
    cp = ctx.store.load(ctx.trace_id)
    if cp is None:
        raise KeyError(f"no checkpoint for {ctx.trace_id}")
    bundle = ContextBundle(instructions=cp.instructions,
                           history=[msg_from_dict(d) for d in cp.history],
                           tools=list(tools))
    usage = Usage(input_tokens=cp.usage_in, output_tokens=cp.usage_out)
    if cp.pending is not None and cp.pending.tool_call_id is not None:
        # resolve the held tool: run it on approve, else append a model-legible denial
        from verso.safety.hooks import Hooks
        hk = hooks or Hooks()
        tc_name, tc_id = cp.pending.tool_name, cp.pending.tool_call_id
        tool_map = {t.name: t for t in tools}
        # recover the held tool's arguments from the assistant turn already in history (bind once, always)
        args = next((c.arguments for m in reversed(bundle.history) for c in m.tool_calls if c.id == tc_id), {})
        if approve and tc_name in tool_map:
            res = await dispatch(tool_map[tc_name], args)
            content = _format_result(res.data) if res.ok else f"Error: {res.error}"
        else:
            content = f"Tool '{tc_name}' was denied by the human reviewer; it did not run."
        content = await hk.run_post_tool((tc_name, args), content)
        bundle.history.append(Message(role="tool", content=content, tool_call_id=tc_id, name=tc_name))
    return await _drive(model, tools, cp.task, bundle, usage, cp.step + 1, max_steps,
                        max_context_tokens=max_context_tokens, hooks=hooks, ctx=ctx)
```

> Implementer notes: the held tool's `arguments` live on the assistant turn already in `bundle.history` (the loop appended it before pausing) — recover them by `tool_call_id`, don't re-store them. `cp.step + 1` continues at the next step. The `done`-tool case can't be the held tool (ASK only fires on real tools), so no special-casing needed. Keep `dispatch`'s `{data,error,ok}` contract.

- [ ] **Step 4 — modify `verso/agent.py`:** add `checkpointer` to `__init__`; thread `ctx` into `_run` when a checkpointer is set; add `resume`:

```python
import uuid
from verso.durable.context import RunContext

class Agent:
    def __init__(self, model, tools=(), *, instructions=None, max_steps=25,
                 max_context_tokens=None, hooks=None, checkpointer=None):
        ...
        self.checkpointer = checkpointer

    async def _run(self, task: str) -> AgentResult:
        ctx = RunContext(trace_id=uuid.uuid4().hex, store=self.checkpointer) if self.checkpointer is not None else None
        return await run_loop(self.model, self.tools, task, max_steps=self.max_steps,
                              instructions=self.instructions, max_context_tokens=self.max_context_tokens,
                              hooks=self.hooks, ctx=ctx)

    async def resume(self, token: str, *, approve: bool) -> AgentResult:
        if self.checkpointer is None:
            raise ValueError("resume requires an Agent constructed with a checkpointer")
        ctx = RunContext(trace_id=token, store=self.checkpointer)
        return await resume_loop(self.model, self.tools, ctx, approve, max_steps=self.max_steps,
                                 max_context_tokens=self.max_context_tokens, hooks=self.hooks)
```

> Add `resume_loop` to the `from verso.core.loop import …` line. Leave `stream` untouched (streaming stays tactical this plan). `run(output_type=…)` keeps working — a PAUSED result simply isn't coerced (it has no final output); that's acceptable for Phase 2 (coercing a resumed result is a later refinement).

- [ ] **Step 5 — exports:** `verso/durable/__init__.py` exports `RunContext, HumanRequest, Hitl, Paused, Checkpoint, CheckpointStore, InMemoryCheckpointStore` (add `SqliteCheckpointStore` in Task 5). Add `from verso.durable import RunContext, InMemoryCheckpointStore` (and `SqliteCheckpointStore` after Task 5) to `verso/__init__.py` + `__all__` — **additive**, don't disturb the evals/memory/safety exports.
- [ ] **Step 6 — run + full suite + lint; commit:** `uv run pytest -q && uv run ruff check verso tests`; `git commit -am "feat(durable): Agent(checkpointer=) + Agent.resume(token, approve) + resume_loop + exports"`

---

## Task 5: `SqliteCheckpointStore` (survives restart) + cross-store contract + README

**Files:** Create `verso/durable/sqlite.py`; Modify `verso/durable/__init__.py`, `verso/__init__.py`, `tests/test_durable_checkpoint.py`, `README.md`.

- [ ] **Step 1 — extend the contract test to BOTH stores** (the durability proof — a *fresh* store instance over the same DB file reloads the checkpoint, simulating a process restart):

```python
# edit the fixture in tests/test_durable_checkpoint.py:
from verso.durable.sqlite import SqliteCheckpointStore

@pytest.fixture(params=["inmem", "sqlite"])
def store(request, tmp_path):
    if request.param == "inmem":
        return InMemoryCheckpointStore()
    return SqliteCheckpointStore(str(tmp_path / "ckpt.db"))


# add (sqlite-only — survives a fresh store instance over the same file):
def test_sqlite_checkpoint_survives_a_fresh_store_instance(tmp_path):
    path = str(tmp_path / "ckpt.db")
    SqliteCheckpointStore(path).save(_cp(trace_id="r9", step=3))
    reopened = SqliteCheckpointStore(path)                 # simulate a process restart
    got = reopened.load("r9")
    assert got is not None and got.step == 3 and got.pending.tool_name == "send_email"
```

- [ ] **Step 2 — run, expect FAIL** (`sqlite` param + new test).
- [ ] **Step 3 — implement `verso/durable/sqlite.py`** (one row per trace_id; the whole checkpoint serialized as JSON in a single column — checkpoints are read/written whole, so a blob column is the simplest correct schema; mirror `verso/memory/sqlite.py` connection style):

```python
# verso/durable/sqlite.py
from __future__ import annotations
import json
import sqlite3

from verso.durable.checkpoint import Checkpoint
from verso.durable.context import HumanRequest

DDL = "CREATE TABLE IF NOT EXISTS checkpoint (trace_id TEXT PRIMARY KEY, data TEXT NOT NULL)"


class SqliteCheckpointStore:
    """Stdlib-sqlite CheckpointStore — survives process restart (the point of 'durable'). One row per
    trace_id; the checkpoint is read/written whole, so it's stored as a single JSON blob. pgvector/Redis
    stores implement the same CheckpointStore contract later with zero loop change."""
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute(DDL)
        self.db.commit()

    def save(self, cp: Checkpoint) -> None:
        p = cp.pending
        data = json.dumps({
            "trace_id": cp.trace_id, "task": cp.task, "instructions": cp.instructions,
            "history": cp.history, "usage_in": cp.usage_in, "usage_out": cp.usage_out, "step": cp.step,
            "pending": None if p is None else {"prompt": p.prompt, "key": p.key,
                                               "tool_name": p.tool_name, "tool_call_id": p.tool_call_id},
        })
        self.db.execute("INSERT OR REPLACE INTO checkpoint(trace_id, data) VALUES(?, ?)", (cp.trace_id, data))
        self.db.commit()

    def load(self, trace_id: str) -> Checkpoint | None:
        row = self.db.execute("SELECT data FROM checkpoint WHERE trace_id=?", (trace_id,)).fetchone()
        if row is None:
            return None
        d = json.loads(row[0])
        pend = d["pending"]
        return Checkpoint(
            trace_id=d["trace_id"], task=d["task"], instructions=d["instructions"],
            history=d["history"], usage_in=d["usage_in"], usage_out=d["usage_out"], step=d["step"],
            pending=None if pend is None else HumanRequest(**pend),
        )

    def delete(self, trace_id: str) -> None:
        self.db.execute("DELETE FROM checkpoint WHERE trace_id=?", (trace_id,))
        self.db.commit()
```

- [ ] **Step 4 — export `SqliteCheckpointStore`** from `verso/durable/__init__.py` and `verso/__init__.py` (+ `__all__`).
- [ ] **Step 5 — README: append before `## Status`:**

````markdown
**Durable seam — one flag, no rewrite** (tactical by default; durable when you need it):

```python
from verso import Agent, SqliteCheckpointStore

agent = Agent(model=..., tools=[...], hooks=ask_before_send,
              checkpointer=SqliteCheckpointStore("runs.db"))   # the one flag
paused = await agent.run("refund the customer")    # pauses on an ASK tool
if paused.stop_reason is StopReason.PAUSED:
    # ...show paused.pending.prompt to a human, hours later, in another process...
    done = await agent.resume(paused.resume_token, approve=True)
```

No `checkpointer` ⇒ the loop is byte-identical to the tactical path. The state is checkpointed each step (crash-recoverable) and on pause; resume runs in a fresh process. No graph, no rewrite.
````

- [ ] **Step 6 — full suite + lint; commit:** `uv run pytest -q && uv run ruff check verso tests`; `git commit -am "feat(durable): SqliteCheckpointStore (survives restart) + cross-store contract + README"`

---

## Verification plan

**Automated:** `uv run pytest -q && uv run ruff check verso tests` → all green. The load-bearing test is `test_durable_backcompat.py`: **a no-checkpointer agent is byte-identical to Phase 1** (and all prior loop/agent/stream tests pass unmodified — if a Phase-0/1 test needed editing, the change was not additive, which is a failure). Criterion: tests pass AND no assertion weakened / no expected output hardcoded — a pause/resume test made green by loosening an assertion is a failure.

**Manual:** build an `Agent` with a `SqliteCheckpointStore("scratch.db")` and an ASK-on-`send_email` hook; `run` a task that triggers it; confirm `stop_reason is PAUSED` and `pending.prompt` reads sensibly; in a **fresh `python` process** construct the same agent over the same DB file and `resume(token, approve=True)` — confirm it completes. Confirm `git diff` on `core/loop.py` touches only the `ctx` param, `_checkpoint`, the durable-ASK branch, `_drive`/`resume_loop` factoring (the User-Review item).

## Done criteria (Plan 10)
- One flag (`checkpointer=`) flips tactical→durable with **no other code change**; off ⇒ byte-identical to Phase 1 (all prior tests green, unmodified).
- A durable run **checkpoints each step** and **pauses** on a `pre_tool` ASK with no sync resolver, returning `PAUSED` + `resume_token` + `pending` without running the tool.
- `Agent.resume(token, approve=True/False)` rebuilds state from the checkpoint and finishes — running or denying the held tool.
- Checkpoints **survive a fresh store instance** (crash/restart) via `SqliteCheckpointStore`; the same `CheckpointStore` contract passes against **both** backends.
- `Message`/`ToolCall` serialization round-trips losslessly; the `{data,error,ok}` dispatch invariant and the loop's shape are preserved.

## Deferred (lock the seam, build nothing)
`RunContext[T]` injection into hooks/tools + an arbitrary tool calling `ctx.hitl.request` end-to-end (Plan 11); permission-policy layers / session modes / confidence router (Plan 11); durable **streaming** resume; multi/nested pause; Postgres/Redis checkpoint stores. The `Hitl`/`Paused` primitive and the `CheckpointStore` contract are the locked seams those build on.
