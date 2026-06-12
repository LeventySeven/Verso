# Verso Phase 1 — Plan 8: Safety & hooks

> **Phase-1 plan set:** Plan 6 (evals) → Plan 7 (memory) → **Plan 8 — safety/hooks (this doc)**. Smallest of the three; it is the **one Phase-1 plan that modifies `core/loop.py`** (additively, fully back-compatible). Implement task-by-task with `compound-v:batched-implementation` (TDD). Never edit a test to make it pass.

**Goal:** ship the **5-stage lifecycle hooks** as the extensibility mechanism (not core-loop edits), the **4-valued permission decision** (`allow | deny | ask | defer`) on tool calls, and the **reinforcement-on-tool-return channel** (§14.4 — `post_tool` may rewrite a tool result to re-assert the objective / inject a recovery hint, *because* the static prefix is frozen for the cache). Hooks are **opt-in**; with no hooks attached, the loop behaves byte-identically to Phase 0.

**Done (machine-checkable):** `uv run pytest -q` green + `uv run ruff check verso tests` clean — proving: each of the 5 hook points fires in order during a run; a `pre_tool` hook returning `DENY` skips the tool and feeds a model-legible denial (the loop continues, the model self-corrects); a `post_tool` hook can rewrite the result the model sees (reinforcement); and **an `Agent` with no hooks produces the same `AgentResult` as before** (the existing Phase-0 loop/agent tests stay green unchanged).

**Approach / key facts (research fold-in):**
- The loop to modify is `verso/core/loop.py` `run_loop(model, tools, task, max_steps=25, instructions=None, max_context_tokens=None)` (lines 29–60). Its structure: per step → `prune` (if over budget) → `model.complete(...)` → if no tool calls `return END_TURN` → else append assistant turn, then for each `tool_call`: look up the tool, `dispatch`, format `content`, special-case `done`, append the tool message. The five hook points map onto exactly these existing seams — **no restructuring**, just calls at the boundaries.
- `dispatch(tool, args)` (`verso/tools/dispatch.py`) returns `{data, error, ok}` and **never raises** into the loop — keep that invariant; hooks wrap it, they don't bypass it.
- `Agent.__init__` (`verso/agent.py:15`) and `agent._run` thread args into `run_loop`; add `hooks` the same way. `Agent.stream` uses `run_stream` (`core/stream_loop.py`) — **for Phase 1, wire hooks into `run_loop` only**; note `run_stream` as a follow-up so the two paths don't silently diverge (divergence rule below).
- §14.4 is the reason `post_tool` exists as a *rewrite* point (not just a notifier): the tool-result envelope is the primary site to inject dynamic state, since the cached prefix must stay frozen.
- **Phase-1 scope of `ASK`/`DEFER`:** real durable human-in-the-loop (`ctx.hitl.request`, checkpoint-before-pause) is **Phase 2** (§6.1). In Phase 1, `ASK` routes to an optional synchronous `ask` callback (default: treat as `DENY` if none is supplied) and `DEFER` is treated as skip-for-now. Lock the 4-valued enum now; the durable `ASK` lands with the seam. Do not build HITL here.

**Divergence rule:** if wiring hooks into `run_loop` forces a change to the `AgentResult` shape or breaks any existing test, **stop and report** — the hooks must be purely additive. If the streaming path (`run_stream`) needs the same hooks to stay consistent and that turns out non-trivial, surface it rather than half-wiring it. After ~3 failed attempts at any one point, escalate.

**User Review Required:** **yes — one item.** This plan modifies `verso/core/loop.py` (the audited Phase-0 core). The change must be *purely additive and back-compatible* (hooks default to a no-op; all existing loop/agent/e2e tests pass unchanged). Confirm the diff touches only the hook call sites + the new `hooks` parameter before merging.

**Tech stack:** unchanged — Python 3.12, dataclasses/enum, async hooks, pytest + `FakeModel`. No new dependency.

---

## File structure

```
verso/
└── safety/
    ├── __init__.py     # NEW — exports Hooks, Hook stages, PermissionDecision
    └── hooks.py        # NEW — PermissionDecision enum + Hooks container (5 stages, all default no-op)
verso/core/loop.py      # MODIFY — accept `hooks`; call the 5 points; honor pre_tool decision + post_tool rewrite
verso/agent.py          # MODIFY — accept `hooks=` in __init__; thread to run_loop
verso/__init__.py       # MODIFY — export Hooks, PermissionDecision
tests/
├── test_hooks.py       # NEW — the 5 points fire; deny skips; post_tool rewrites
└── test_hooks_backcompat.py   # NEW — no hooks ⇒ identical AgentResult
README.md               # MODIFY — append a hooks snippet
```

---

## Task 1: `Hooks` container + `PermissionDecision`

**Files:** Create `verso/safety/__init__.py` (empty), `verso/safety/hooks.py`; Test (first half of) `tests/test_hooks.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_hooks.py
from verso.safety.hooks import Hooks, PermissionDecision


async def test_hooks_default_to_noop_and_compose():
    fired = []
    h = Hooks(
        pre_model=[lambda bundle: fired.append("pre_model")],
        post_tool=[lambda call, content: fired.append("post_tool") or content],
    )
    await h.run_pre_model("BUNDLE")
    out = await h.run_post_tool(("add", {}), "3")
    assert fired == ["pre_model", "post_tool"]
    assert out == "3"                               # default: content passes through unchanged


async def test_pre_tool_decision_defaults_allow_and_first_non_allow_wins():
    h = Hooks(pre_tool=[lambda call: PermissionDecision.ALLOW,
                        lambda call: PermissionDecision.DENY])
    assert await h.run_pre_tool(("send_email", {})) == PermissionDecision.DENY
    assert await Hooks().run_pre_tool(("x", {})) == PermissionDecision.ALLOW   # no hooks ⇒ allow
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement `verso/safety/hooks.py`:**

```python
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

    async def run_pre_model(self, bundle) -> None:
        for h in self.pre_model:
            await _maybe_await(h(bundle))

    async def run_post_model(self, response) -> None:
        for h in self.post_model:
            await _maybe_await(h(response))

    async def run_pre_tool(self, call: ToolCallView) -> PermissionDecision:
        decision = PermissionDecision.ALLOW
        for h in self.pre_tool:
            d = await _maybe_await(h(call))
            if d and d != PermissionDecision.ALLOW:   # first non-allow wins (most restrictive)
                return d
        return decision

    async def run_post_tool(self, call: ToolCallView, content: str) -> str:
        for h in self.post_tool:                      # reinforcement channel: may rewrite the result
            content = await _maybe_await(h(call, content)) or content
        return content

    async def run_on_stop(self, result) -> None:
        for h in self.on_stop:
            await _maybe_await(h(result))
```

- [ ] **Step 4 — run, expect 2 passed; commit:** `git commit -am "feat(safety): Hooks (5-stage lifecycle) + 4-valued PermissionDecision"`

---

## Task 2: wire hooks into the loop (additive, back-compatible)

**Files:** Modify `verso/core/loop.py`, `verso/agent.py`; Test: extend `tests/test_hooks.py` + new `tests/test_hooks_backcompat.py`.

- [ ] **Step 1 — failing tests:**

```python
# --- appended to tests/test_hooks.py ---
from verso import Agent, tool
from verso.safety.hooks import Hooks, PermissionDecision
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def send_email(to: str) -> str:
    "Send an email."
    return f"sent to {to}"


def _agent(hooks):
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="send_email", arguments={"to": "x@y.z"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    return Agent(model=fm, tools=[send_email], hooks=hooks)


async def test_deny_skips_the_tool_and_loop_continues():
    seen = {}
    h = Hooks(pre_tool=[lambda call: PermissionDecision.DENY],
              post_tool=[lambda call, content: seen.setdefault("content", content) or content])
    result = await _agent(h).run("email x")
    assert result.output == "done"                      # loop continued after the denial
    assert "denied" in seen["content"].lower()          # the model saw a legible denial, not a sent email


async def test_post_tool_reinforcement_rewrites_the_result():
    h = Hooks(post_tool=[lambda call, content: content + "  [reminder: confirm the address first]"])
    captured = {}
    h.post_model = [lambda resp: None]
    # allow path: tool runs, post_tool appends a reinforcement note the model sees next turn
    h2 = Hooks(post_tool=[lambda call, content: f"{content}  [objective: finish the task]"])
    result = await _agent(h2).run("email x")
    assert result.output == "done"


async def test_all_five_points_fire_in_order():
    order = []
    h = Hooks(
        pre_model=[lambda b: order.append("pre_model")],
        post_model=[lambda r: order.append("post_model")],
        pre_tool=[lambda c: order.append("pre_tool") or PermissionDecision.ALLOW],
        post_tool=[lambda c, content: order.append("post_tool") or content],
        on_stop=[lambda r: order.append("on_stop")],
    )
    await _agent(h).run("email x")
    # turn 1: pre_model, post_model, pre_tool, post_tool ; turn 2: pre_model, post_model ; then on_stop
    assert order[:4] == ["pre_model", "post_model", "pre_tool", "post_tool"]
    assert order[-1] == "on_stop"
```

```python
# tests/test_hooks_backcompat.py
from verso import Agent, tool
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


def _responses():
    return [ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage(input_tokens=1, output_tokens=1)),
            ModelResponse(text="3", tool_calls=[], usage=Usage(input_tokens=1, output_tokens=1))]


async def test_no_hooks_is_identical_to_phase0():
    bare = await Agent(model=FakeModel(_responses()), tools=[add]).run("add")
    assert bare.output == "3" and bare.stop_reason.value == "end_turn" and bare.steps == 2
    assert (bare.usage.input_tokens, bare.usage.output_tokens) == (2, 2)
```

- [ ] **Step 2 — run, expect FAIL** (`Agent` has no `hooks`).

- [ ] **Step 3 — modify `verso/core/loop.py`** — add the `hooks` parameter and the 5 call sites. Replace the `run_loop` signature + body (keep `_format_result`, `build_bundle`, imports; add `from verso.safety.hooks import Hooks, PermissionDecision`):

```python
async def run_loop(model: Model, tools: Sequence[Tool], task: str,
                   max_steps: int = 25, instructions: str | None = None,
                   max_context_tokens: int | None = None, hooks: "Hooks | None" = None) -> AgentResult:
    from verso.safety.hooks import Hooks, PermissionDecision
    hooks = hooks or Hooks()
    bundle = build_bundle(tools, task, instructions)
    tool_map = {t.name: t for t in tools}
    usage = Usage()

    for step in range(1, max_steps + 1):
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
                if decision == PermissionDecision.ASK and hooks.ask is not None and hooks.ask((tc.name, tc.arguments)):
                    pass  # approved → fall through to run
                else:
                    content = f"Tool '{tc.name}' was {decision.value} by policy; it did not run."
                    content = await hooks.run_post_tool((tc.name, tc.arguments), content)
                    bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))
                    continue
            t = tool_map.get(tc.name)
            if t is None:
                content = f"Error: unknown tool '{tc.name}'."
            else:
                result_ = await dispatch(t, tc.arguments)
                content = _format_result(result_.data) if result_.ok else f"Error: {result_.error}"
                if tc.name == "done" and result_.ok:
                    final = AgentResult(output=_format_result(result_.data), stop_reason=StopReason.DONE,
                                        usage=usage, steps=step)
                    await hooks.run_on_stop(final)
                    return final
            content = await hooks.run_post_tool((tc.name, tc.arguments), content)
            bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))

    result = AgentResult(output="", stop_reason=StopReason.MAX_STEPS, usage=usage, steps=max_steps)
    await hooks.run_on_stop(result)
    return result
```

> Note: the `ASK`-approved path falls through to run the tool; `DENY`/`DEFER`/unresolved-`ASK` skip it with a legible message that still passes through `post_tool`. The `{data,error,ok}` dispatch invariant is untouched.

- [ ] **Step 4 — modify `verso/agent.py`:** add `hooks: "Hooks | None" = None` to `Agent.__init__`, store `self.hooks = hooks`, and pass `hooks=self.hooks` in `_run`'s `run_loop(...)` call. (Leave `stream` as-is for Phase 1 — see Deferred.)

- [ ] **Step 5 — run the new tests, expect green;** then **run the FULL suite:** `uv run pytest -q`. The Phase-0 loop/agent/e2e tests **must stay green unchanged** (back-compat). Then `uv run ruff check verso tests` → clean.

- [ ] **Step 6 — export from `verso/__init__.py`** (`from verso.safety.hooks import Hooks, PermissionDecision`; add to `__all__`).

- [ ] **Step 7 — commit:** `git commit -am "feat(core): wire 5-stage hooks into run_loop (additive, back-compat) + permission/reinforcement"`

---

## Task 3: hooks on the streaming path (run ↔ stream parity)

Hooks must work on `agent.stream()` too, or the two run paths silently diverge. Same 5 points; the streaming loop is `verso/core/stream_loop.py` `run_stream(...)` (the structure mirrors `run_loop`).

**Files:** Modify `verso/core/stream_loop.py`, `verso/agent.py`; Test: new `tests/test_hooks_stream.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_hooks_stream.py
from verso import Agent, tool
from verso.safety.hooks import Hooks, PermissionDecision
from verso.stream.events import EventType
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def send_email(to: str) -> str:
    "Send an email."
    return f"sent to {to}"


async def test_stream_honors_pre_tool_deny_and_still_completes():
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="send_email", arguments={"to": "x@y.z"})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    agent = Agent(model=fm, tools=[send_email], hooks=Hooks(pre_tool=[lambda c: PermissionDecision.DENY]))
    events = [ev async for ev in agent.stream("email x")]
    tool_results = [ev for ev in events if ev.type == EventType.TOOL_RESULT]
    assert tool_results and tool_results[0].ok is False and "denied" in tool_results[0].content.lower()
    assert events[-1].type == EventType.DONE and events[-1].result.output == "done"
```

- [ ] **Step 2 — run, expect FAIL** (`run_stream`/`Agent.stream` take no `hooks`).
- [ ] **Step 3 — modify `verso/core/stream_loop.py`** — add `hooks: "Hooks | None" = None` to `run_stream`; `from verso.safety.hooks import Hooks, PermissionDecision`; `hooks = hooks or Hooks()`. Insert the 5 points at the same seams as `run_loop`:
  - `await hooks.run_pre_model(bundle)` **before** the `async for chunk in iter_model_stream(...)` loop.
  - after the chunk loop, build `resp = ModelResponse(text=text, tool_calls=tool_calls, usage=usage)` and `await hooks.run_post_model(resp)` (parity with `run_loop`'s `post_model(response)`).
  - in the `for tc in tool_calls:` loop, **after** `yield TOOL_START` and **before** dispatch: `decision = await hooks.run_pre_tool((tc.name, tc.arguments))`; if `decision != ALLOW` (and not an `ASK`-approved via `hooks.ask`), set `content, ok = f"Tool '{tc.name}' was {decision.value} by policy; it did not run.", False`, run it through `post_tool`, `yield StreamEvent(TOOL_RESULT, tool=tc.name, ok=ok, content=content)`, append the tool message, and `continue` (skip dispatch).
  - **before** every `yield StreamEvent(TOOL_RESULT, ...)` on the run path: `content = await hooks.run_post_tool((tc.name, tc.arguments), content)` (the reinforcement rewrite the model sees next turn).
  - **before** each `yield StreamEvent(DONE, result=...)`: `await hooks.run_on_stop(result)` (build the `result` first, then stop-hook, then yield).
  - Keep the `done`-tool early-DONE and the `{data,error,ok}` dispatch invariants unchanged.
- [ ] **Step 4 — modify `verso/agent.py`** `Agent.stream`: pass `hooks=self.hooks` into `run_stream(...)`.
- [ ] **Step 5 — run the new test + the FULL suite:** `uv run pytest -q` → all green (the Phase-0 streaming/e2e tests must stay green: a no-hooks stream is byte-identical). `uv run ruff check verso tests` → clean.
- [ ] **Step 6 — commit:** `git commit -am "feat(core): wire hooks into run_stream — run/stream parity (additive, back-compat)"`

---

## Task 4: README

**Files:** Modify `README.md`.

- [ ] **Step 1 — append before `## Status`:**

````markdown
**Hooks — the extensibility seam** (the loop stays <200 lines; weight lives here):

```python
from verso import Agent, Hooks, PermissionDecision

hooks = Hooks(
    pre_tool=[lambda call: PermissionDecision.ASK if call[0] == "send_email" else PermissionDecision.ALLOW],
    post_tool=[lambda call, content: f"{content}\n[reminder: stay on task]"],   # reinforcement on every return
    on_stop=[lambda result: log(result.stop_reason)],
)
agent = Agent(model=..., tools=[...], hooks=hooks)   # no hooks ⇒ identical to the bare loop
```

Permission is 4-valued (`allow | deny | ask | defer`); durable human-in-the-loop (`ctx.hitl.request`) arrives with the Phase-2 seam.
````

- [ ] **Step 2 — full suite + lint, then commit:** `uv run pytest -q && uv run ruff check verso tests`; `git commit -am "docs: hooks snippet in README"`

---

## Verification plan

**Automated:** `uv run pytest -q && uv run ruff check verso tests` → all green (live test skipped). The back-compat test (`test_hooks_backcompat.py`) is the load-bearing one: **a no-hooks agent must be byte-identical to Phase 0**. Criterion: tests pass AND the Phase-0 tests were not modified to accommodate the change (if a Phase-0 test needed editing, the hooks change was not additive — that's a failure, not a pass).

**Manual:** attach a `pre_tool` hook that `DENY`s a destructive tool on a real run and confirm the agent narrates around the denial rather than crashing; confirm `git diff` on `core/loop.py` touches only the hook call sites + the `hooks` parameter (the User-Review item).

## Done criteria (Plan 8)
- The 5 hook stages fire in loop order; `pre_tool` returns a `PermissionDecision`; `DENY`/`DEFER` skip the tool with a model-legible message; `ASK` routes to the optional sync resolver.
- `post_tool` can rewrite the tool result the model sees next turn (the reinforcement-on-tool-return channel).
- An `Agent` with no hooks is byte-identical to Phase 0 (all prior tests green, unmodified).
- **Hooks fire on both `run` and `stream` (parity)** — a no-hooks stream is byte-identical to Phase 0.
- The `{data,error,ok}` dispatch invariant and the loop's <200-line shape are preserved.

## Deferred (lock the seam, build nothing)
Durable `ASK` / `ctx.hitl.request` (checkpoint-before-pause) — **Phase 2** (§6.1); composable priority-ordered permission *policy layers* + session modes (`allow_all|ask_every|ask_once`) and the confidence router (§6.3) — **Phase 2**; `RunContext[T]` injection into hooks (the typed `ctx`) — lands when the durable layer needs it. (`run`/`stream` parity is **done** in Task 3, not deferred.)
