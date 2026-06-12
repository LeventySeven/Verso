# Verso Phase 2 — Plan 13: RunContext[T] injection into tools

> **Follow-up to Plan 11**, completes the durable-HITL story from Plan 10. Implement with `compound-v:batched-implementation` (TDD). Never edit a test to make it pass.

**Goal:** let a tool body **receive the typed `RunContext[T]`** — read `ctx.deps` (injected dependencies: db handle, user id, config) and call **`ctx.hitl.request(prompt)`** to pause the durable run for human input, then **resume** with the human's answer. This makes the `[T]` in `RunContext[T]` real for tools and turns durable HITL into something *any tool* can trigger (Plan 10 could only pause from a `pre_tool` ASK decision).

**Done (machine-checkable):** `uv run pytest -q` green + `uv run ruff check verso tests` clean — proving: (1) a tool declaring a `ctx` parameter receives the `RunContext` (and `ctx` is **not** a model-visible argument in its JSON schema); (2) `Agent(deps=X)` makes `ctx.deps == X` inside the tool; (3) a tool calling `ctx.hitl.request("…")` on a **durable** agent pauses (`PAUSED` + `pending.prompt == "…"`) without finishing; (4) `Agent.resume(token, answer=Y)` re-runs the tool with `ctx.hitl.request(...) == Y` and completes; (5) **back-compat**: a tool with no `ctx` param behaves exactly as before, and a no-checkpointer run is still byte-identical to Phase 1 (all prior tests pass unmodified).

**Approach / key facts (research fold-in):**
- `verso/tools/tool.py`: `Tool(name, description, parameters, fn, args_model)`. `_build_args_model(fn)` builds a pydantic model from the fn signature, skipping `self`/`cls`/varargs. **The `ctx` param must ALSO be skipped** (it's framework-injected, not a model argument) — otherwise it becomes a required JSON-schema field the model is asked to fill.
- `verso/tools/dispatch.py`: `dispatch(tool, arguments)` validates args → `tool.fn(**validated.model_dump())` → `ToolResult(ok,data,error)`, **never raises** (catches `Exception`). Two changes: inject `ctx` when the tool wants it, and **let `Paused` propagate** (it's control flow, not a tool error).
- `verso/durable/context.py` (Plan 10): `RunContext[T]` (`trace_id, deps, step, store, hitl`), `HumanRequest(prompt, key, tool_name, tool_call_id)`, `Paused(request)`, `Hitl.request(prompt, key)` currently *always* raises. **`Hitl` must become resume-aware**: on the first run `request()` raises `Paused`; on resume the answer is pre-loaded and `request()` *returns* it. **The re-run model:** resuming a tool-initiated pause re-executes the tool body from the top, so `ctx.hitl.request(...)` returns the answer the second time. ⚠️ **Tools using `ctx.hitl.request` must be idempotent up to the request call** (no irreversible side-effect before it) — document this loudly; it's the standard durable-execution constraint.
- `verso/core/loop.py` (Plan 10): `_drive` runs tools via `dispatch`. The durable-ASK pause already exists (`HumanRequest` + defer-siblings + `_checkpoint` + `PAUSED`). Factor that into a `_pause(...)` helper and reuse it for the tool-`Paused` path. `resume_loop` currently handles the ASK approve/deny case; add the tool-input (answer) case, keyed on a new `HumanRequest.kind`.
- `verso/agent.py` (Plan 10): `_run` creates a `RunContext` only when `checkpointer` is set. Change to **always** create one (`store=self.checkpointer`, which may be `None`) so tools always get a real `ctx`; add a `deps` ctor param. This stays byte-identical: `_checkpoint` no-ops when `store is None`, and the durable branches all gate on `ctx.store is not None`.

**Divergence rule:** durability + ctx-injection must be **purely additive** — a tool without a `ctx` param and a run without a checkpointer must behave exactly as before (all Phase-0/1/2 tests pass unmodified). If `Paused` propagation can't be made to coexist with `dispatch`'s never-raise contract for *normal* tool errors, stop and report. After ~3 failed attempts at any one mechanism, escalate.

**User Review Required:** **yes** — modifies `verso/core/loop.py` (the audited core, 3rd time) + `verso/tools/dispatch.py`. The change must be additive: confirm a ctx-less tool + no-checkpointer run is byte-identical before merging.

**Out of scope:** memoizing *other* (non-hitl) side-effects across a re-run (full durable-execution determinism — the idempotency caveat covers it by documentation); streaming-path ctx-injection (note it); multiple distinct `hitl.request` calls in one tool body resolved in one resume (single request per pause this plan); pgvector/Mem0 (Plan 14).

---

## File structure

```
verso/durable/context.py   # MODIFY — Hitl carries resolved answers; HumanRequest.kind
verso/tools/tool.py        # MODIFY — Tool.wants_ctx; _build_args_model skips `ctx`
verso/tools/dispatch.py    # MODIFY — dispatch(tool, args, ctx=None): inject ctx; propagate Paused
verso/core/loop.py         # MODIFY — pass ctx to dispatch; _pause() helper; tool-Paused path; resume answer case
verso/agent.py             # MODIFY — deps= ctor param; always-create ctx; resume(answer=)
tests/
├── test_durable_ctx_tools.py   # NEW — deps injection; tool pause+resume-with-answer; ctx-less unchanged; tactical degrade
README.md                  # MODIFY — ctx.deps + ctx.hitl snippet + the idempotency note
```

---

## Task 1: ctx-aware `Hitl` + `Tool.wants_ctx` + `dispatch` injection/propagation

**Files:** Modify `verso/durable/context.py`, `verso/tools/tool.py`, `verso/tools/dispatch.py`; Test (plumbing half of) `tests/test_durable_ctx_tools.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_durable_ctx_tools.py
from verso import Agent, tool
from verso.tools.dispatch import dispatch
from verso.durable.context import RunContext, Paused
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage, StopReason
from verso.durable.inmem import InMemoryCheckpointStore


def test_ctx_is_not_a_model_visible_argument():
    @tool
    def whoami(ctx) -> str:
        "Return the caller id."
        return ctx.deps["uid"]
    assert whoami.wants_ctx is True
    assert "ctx" not in whoami.parameters.get("properties", {})   # framework-injected, not a model arg


async def test_dispatch_injects_ctx_and_propagates_paused():
    @tool
    def needs_input(ctx) -> str:
        "Ask a human."
        return ctx.hitl.request("approve?")        # raises Paused on the first run
    ctx: RunContext = RunContext(trace_id="x", deps={"uid": "u1"}, store=InMemoryCheckpointStore())
    import pytest
    with pytest.raises(Paused):
        await dispatch(needs_input, {}, ctx=ctx)   # Paused propagates, NOT swallowed into ToolResult

    @tool
    def reads_deps(ctx) -> str:
        "Read deps."
        return ctx.deps["uid"]
    res = await dispatch(reads_deps, {}, ctx=ctx)
    assert res.ok and res.data == "u1"
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — modify `verso/durable/context.py`** — make `Hitl` resume-aware and add `HumanRequest.kind`:

```python
@dataclass
class HumanRequest:
    prompt: str
    key: str = "default"
    tool_name: str | None = None
    tool_call_id: str | None = None
    kind: str = "input"          # "input" = a tool asked via ctx.hitl.request; "approve" = a pre_tool ASK gate


class Hitl:
    """The human-in-the-loop handle on RunContext. On the first run `request()` raises Paused to pause
    the durable run; on RESUME the answer is pre-loaded (via `_resolve`) and `request()` returns it, so
    the re-running tool body continues past the call. Tools using this must be idempotent up to the
    request (no irreversible side-effect before it) — resume re-executes the tool from the top."""
    def __init__(self) -> None:
        self._answers: dict[str, object] = {}

    def request(self, prompt: str, *, key: str = "default"):
        if key in self._answers:
            return self._answers[key]            # resumed → return the human's answer
        raise Paused(HumanRequest(prompt=prompt, key=key, kind="input"))

    def _resolve(self, key: str, answer: object) -> None:
        self._answers[key] = answer
```

(Keep `RunContext.hitl: Hitl = field(default_factory=Hitl)` — each run gets a fresh `Hitl`.)

- [ ] **Step 4 — modify `verso/tools/tool.py`** — skip `ctx` in the args model and record `wants_ctx`:
  - In `_build_args_model`, change the skip set to `("self", "cls", "ctx")`.
  - Add `wants_ctx: bool = False` to the `Tool` dataclass.
  - In `tool()`'s `make`, compute `wants_ctx = "ctx" in inspect.signature(f).parameters` and pass it to `Tool(...)`.

- [ ] **Step 5 — modify `verso/tools/dispatch.py`** — inject ctx, propagate Paused:

```python
from verso.durable.context import Paused   # add to imports

async def dispatch(tool: Tool, arguments: dict[str, Any], ctx: object | None = None) -> ToolResult:
    """Validate args, run the tool (injecting RunContext if it declares `ctx`), and ALWAYS return a
    ToolResult — EXCEPT Paused, which is control flow (a human-in-the-loop pause) and must reach the loop."""
    try:
        validated = tool.args_model(**arguments)
    except ValidationError as e:
        return ToolResult(ok=False, error=f"ValidationError: {e}")
    try:
        kwargs = dict(validated.model_dump())
        if tool.wants_ctx:
            kwargs["ctx"] = ctx
        result = tool.fn(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return ToolResult(ok=True, data=result)
    except Paused:
        raise                              # pause request → loop handles it (durable pause)
    except Exception as e:  # noqa: BLE001 — tool failures are data, not exceptions
        return ToolResult(ok=False, error=f"{type(e).__name__}: {e}")
```

- [ ] **Step 6 — run, expect 2 passed; full suite stays green; commit:** `git commit -am "feat(durable): ctx-aware Hitl + Tool.wants_ctx + dispatch ctx-injection/Paused-propagation"`

---

## Task 2: wire ctx into the loop + `Agent(deps=)` + resume-with-answer

**Files:** Modify `verso/core/loop.py`, `verso/agent.py`, `README.md`; Test (pause/resume half of) `tests/test_durable_ctx_tools.py`.

- [ ] **Step 1 — failing tests (append):**

```python
def _durable_agent(store, deps=None):
    @tool
    def refund(amount: int, ctx) -> str:
        "Refund a customer after human approval."
        decision = ctx.hitl.request(f"approve refund of {amount}?")   # pauses; on resume returns the answer
        return f"refunded {amount}" if decision == "yes" else "refund cancelled"
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="refund", arguments={"amount": 50})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    return Agent(model=fm, tools=[refund], checkpointer=store, deps=deps)


async def test_tool_hitl_request_pauses_then_resumes_with_the_answer():
    store = InMemoryCheckpointStore()
    agent = _durable_agent(store)
    paused = await agent.run("refund the customer")
    assert paused.stop_reason == StopReason.PAUSED
    assert paused.pending.prompt == "approve refund of 50?" and paused.pending.kind == "input"
    resumed = await agent.resume(paused.resume_token, answer="yes")
    assert resumed.stop_reason == StopReason.END_TURN and resumed.output == "done"


async def test_agent_deps_reach_the_tool():
    seen = {}
    @tool
    def grab(ctx) -> str:
        "Read deps."
        seen["uid"] = ctx.deps["uid"]
        return "ok"
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="grab", arguments={})], usage=Usage()),
        ModelResponse(text="done", tool_calls=[], usage=Usage()),
    ])
    await Agent(model=fm, tools=[grab], deps={"uid": "u-42"}).run("go")
    assert seen["uid"] == "u-42"
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — modify `verso/core/loop.py`:**
  - Add `from verso.durable.context import Paused` to imports.
  - **Factor the durable-ASK pause body into a helper** `_pause(ctx, bundle, task, usage, step, hooks, resp, tc, request) -> AgentResult` (defer unprocessed siblings, fill `request.tool_name/tool_call_id` from `tc` if unset, `_checkpoint(..., pending=request)`, build the `PAUSED` `AgentResult`, `await hooks.run_on_stop`, return it). Replace the inline ASK-branch body with `return await _pause(..., HumanRequest(prompt=f"Approve tool '{tc.name}' with args {tc.arguments}?", tool_name=tc.name, tool_call_id=tc.id, kind="approve"))`.
  - In the tool-run section, pass `ctx` to dispatch and catch `Paused`:
    ```python
    else:
        try:
            result = await dispatch(t, tc.arguments, ctx=ctx)
        except Paused as p:
            if ctx is not None and ctx.store is not None:
                return await _pause(ctx, bundle, task, usage, step, hooks, resp, tc, p.request)
            content = f"Tool '{tc.name}' requested human input but this run is not durable; it did not pause."
        else:
            content = _format_result(result.data) if result.ok else f"Error: {result.error}"
            if tc.name == "done" and result.ok:
                final = AgentResult(output=_format_result(result.data), stop_reason=StopReason.DONE,
                                    usage=usage, steps=step)
                await hooks.run_on_stop(final)
                return final
    content = await hooks.run_post_tool((tc.name, tc.arguments), content)
    bundle.history.append(Message(role="tool", content=content, tool_call_id=tc.id, name=tc.name))
    ```
  - In `resume_loop`, branch on `cp.pending.kind`:
    ```python
    if cp.pending is not None and cp.pending.tool_call_id is not None:
        tc_name, tc_id = cp.pending.tool_name, cp.pending.tool_call_id
        tool_map = {t.name: t for t in tools}
        args = next((c.arguments for m in reversed(bundle.history) for c in m.tool_calls if c.id == tc_id), {})
        if cp.pending.kind == "input":
            # tool-initiated pause: pre-load the human's answer, then RE-RUN the tool (idempotent up to the request)
            ctx.hitl._resolve(cp.pending.key, answer)
            if tc_name in tool_map:
                res = await dispatch(tool_map[tc_name], args, ctx=ctx)
                content = _format_result(res.data) if res.ok else f"Error: {res.error}"
            else:
                content = f"Error: unknown tool '{tc_name}'."
        else:
            # pre_tool ASK gate: run on approve, deny otherwise (existing behavior)
            if approve and tc_name in tool_map:
                res = await dispatch(tool_map[tc_name], args, ctx=ctx)
                content = _format_result(res.data) if res.ok else f"Error: {res.error}"
            else:
                content = f"Tool '{tc_name}' was denied by the human reviewer; it did not run."
        from verso.safety.hooks import Hooks
        content = await (hooks or Hooks()).run_post_tool((tc_name, args), content)
        bundle.history.append(Message(role="tool", content=content, tool_call_id=tc_id, name=tc_name))
    ```
    `resume_loop` gains an `answer: object = None` parameter (alongside `approve`).
  - Note: on the `input` re-run, `dispatch(..., ctx=ctx)` calls the tool again; `ctx.hitl.request` now returns the resolved answer (no re-pause). The `done`-tool can't be the held tool (ASK/hitl never fire on `done`'s dispatch path before its early-return — verify).

- [ ] **Step 4 — modify `verso/agent.py`:**
  - Add `deps: object | None = None` to `__init__`, store `self.deps`.
  - `_run`: **always** create `ctx = RunContext(trace_id=uuid.uuid4().hex, deps=self.deps, store=self.checkpointer)` (no longer conditional) and pass it.
  - `resume(self, token, *, approve: bool = True, answer: object = None)`: pass both through to `resume_loop`.

- [ ] **Step 5 — README: append to the durable section:**

````markdown
Tools can read injected dependencies and pause for a human themselves:

```python
@tool
def refund(amount: int, ctx) -> str:        # `ctx` is injected, never a model argument
    "Refund after human approval."
    if ctx.hitl.request(f"approve refund of {amount}?") != "yes":   # pauses the durable run
        return "cancelled"
    ctx.deps["ledger"].refund(amount)        # ctx.deps carries your typed dependencies
    return "refunded"

agent = Agent(model=..., tools=[refund], deps={"ledger": ledger}, checkpointer=store)
paused = await agent.run("refund $50")       # → PAUSED, paused.pending.prompt
done = await agent.resume(paused.resume_token, answer="yes")   # re-runs refund; hitl returns "yes"
```

Resume re-executes the tool from the top with the answer returned — **make hitl tools idempotent up to the request** (no irreversible side-effect before `ctx.hitl.request`).
````

- [ ] **Step 6 — full suite + lint; commit:** `uv run pytest -q && uv run ruff check verso tests`; `git commit -am "feat(core): ctx into tools + Agent(deps=) + tool-hitl pause/resume-with-answer (additive)"`

---

## Verification plan

**Automated:** `uv run pytest -q && uv run ruff check verso tests` → all green. Load-bearing: every Phase-0/1/2 test passes **unmodified** (ctx-less tools + no-checkpointer runs byte-identical); the new tests prove ctx.deps injection, `ctx` absent from the tool's JSON schema, tool-hitl pause→resume-with-answer round-trip. Criterion: tests pass AND no assertion weakened.

**Manual:** confirm `git diff` on `core/loop.py` is the `_pause` factoring + the tool-`Paused` catch + the resume `input` branch only (User-Review item). Build a durable agent with a `refund(amount, ctx)` tool, run → PAUSED, `resume(answer="yes")` → completes; confirm `ctx` is absent from `refund`'s `.parameters`.

## Done criteria (Plan 13)
- A tool declaring `ctx` receives the `RunContext`; `ctx` is not a model-visible argument; `Agent(deps=X)` reaches `ctx.deps`.
- A tool calling `ctx.hitl.request` on a durable agent pauses (`PAUSED` + prompt), and `resume(answer=Y)` re-runs it with the request returning `Y` and finishes.
- Back-compat: ctx-less tools + no-checkpointer runs are byte-identical; all prior tests pass unmodified.
- The idempotency caveat (re-run-from-top) is documented in code + README.

## Deferred
Cross-re-run memoization of non-hitl side-effects (full durable determinism); streaming-path ctx-injection; multiple `hitl.request` calls resolved per resume; `ctx` injection into hooks (the hook signatures are fixed — a separate, smaller change if needed).
