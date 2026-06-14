# Verso — Plan 16: "Don't limit the user" hardening (Tier 1 + Tier 2)

> Grounded in a teardown comparison vs **LangGraph** + **Pydantic AI** (`researchfms/teardowns/{LANGGRAPH,PYDANTIC_AI}.md`, distilled in `research/03_teardowns/`). Verso's *architecture* is non-limiting (no forced graph, swappable Protocols, `inspect()` transparency, one-flag durability — the corpus endorses these). The gaps are **unshipped escape hatches**, several already reserved in the PRD. Implement with `compound-v:batched-implementation` (TDD); recheck each batch. Never edit a test to make it pass; every change is **additive / back-compatible** (no `temperature` set, no `Retry` raised, no `ctx` field read ⇒ byte-identical to today).

**Goal:** remove the first-hour walls a real user hits — set sampling params, retry-a-tool-with-feedback, register a raw/MCP tool, read usage/history from `ctx`, approve-and-edit a held tool, steer the loop without a graph, and compact history safely.

**Done (machine-checkable):** `uv run pytest -q` green + `uv run ruff check verso tests` clean — proving each item below, AND every prior test passes UNMODIFIED (additive). 190 currently pass.

> **STATUS: SHIPPED 2026-06-14.** All 7 tasks (Batches P–T) implemented test-first, each independently rechecked (verdict APPROVED), and pushed. `uv run pytest -q` → **217 passed, 1 skipped**; `ruff` clean. The no-feature path stayed byte-identical at every batch — the additive gate held throughout. One scope cut: `bypass_termination` was dropped (no clean use in Verso's no-`return_direct` model).

**Divergence rule:** any item that forces a change to a no-opt-in path (a test that used none of these features breaks) means the change wasn't additive — STOP and report. After ~3 failed attempts at one mechanism, escalate.

**User Review Required:** **yes** — Batches Q/R/S touch `verso/core/loop.py` (the audited core) again, additively. Confirm the no-feature path stays byte-identical before merging each.

---

## Batches (by coupling / risk)

- ✅ **Batch P — edges (isolated, no core-loop touch):** Task 1 (provider/sampling params) + Task 3 (`Tool.from_schema`).
- ✅ **Batch Q — ctx enrichment:** Task 4 (`RunContext` read-only `usage`/`messages`/`model`/`step`, populated by the loop).
- ✅ **Batch R — self-healing:** Task 2 (`Retry(feedback)` from tools + output validators + configurable reask).
- ✅ **Batch S — expressiveness:** Task 5 (richer resume: approve-with-edited-args / deny-message / skip) + Task 6 (`should_continue` around-step control hook + a "plain async Python" recipe). *`bypass_termination` dropped — cargo-cult, no clean use in Verso's no-`return_direct` model. `should_continue` is `ctx`-aware (can steer on `ctx.usage` budget).*
- ✅ **Batch T — history hygiene:** Task 7 (`merge_messages` dedup-by-id + `RemoveMessage` / `__remove_all__` compaction; `Message.id` added additively, serde round-trips it byte-identically).

---

## Task 1 — Provider / sampling params passthrough  *(Batch P; `verso/model/anthropic.py`)*

The single most-hit wall: `AnthropicModel` exposes only `model_id`/`max_tokens`. Add the common knobs + a raw `extra_body`/`extra_headers` escape (the universal passthrough — covers `effort`, `output_config`, betas). `None` ⇒ omit (the `OMIT` discipline from `06_design_resolutions/model-routing.md`).

- [ ] **Failing test** (`tests/test_model_params.py`): a fake client captures `messages.create(**kwargs)`; assert `temperature`/`top_p`/`stop_sequences`/`thinking` flow through only when set, `extra_body`/`extra_headers` pass through, and an `AnthropicModel("x")` with none set sends **no** such keys (byte-identical to today).
- [ ] **Implement**: add to `__init__` (all default `None`): `temperature, top_p, stop_sequences, thinking, extra_body, extra_headers`; store them. In `complete()`, just before `resp = await self.client.messages.create(**kwargs)`:
```python
        for key, val in (("temperature", self.temperature), ("top_p", self.top_p),
                         ("stop_sequences", self.stop_sequences), ("thinking", self.thinking)):
            if val is not None:
                kwargs[key] = val
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body        # raw JSON-body passthrough (effort, output_config, …)
        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers  # e.g. anthropic-beta
```
  Also thread these through `init_model` is out of scope (keep `init_model` simple); document constructing `AnthropicModel(...)` directly for params.
- [ ] Run + commit: `feat(model): sampling params + extra_body/extra_headers passthrough on AnthropicModel`

---

## Task 3 — `Tool.from_schema` raw-tool escape  *(Batch P; `verso/tools/tool.py`)*

`@tool` (signature→schema) is the only door. Add a raw constructor for MCP/OpenAPI/dynamic tools that already carry a JSON schema. PRD reserves this (`PRD_v1.md:442`, "Verso's most-deletable abstraction").

- [ ] **Failing test** (`tests/test_tool_from_schema.py`): build a tool from a hand-written JSON schema + a plain fn; `dispatch` it with valid args → runs; `tool.parameters` is the exact schema passed; a `wants_ctx=True` variant receives `ctx`.
- [ ] **Implement** a module-level `tool_from_schema` (export from `verso` + `verso.tools`):
```python
from pydantic import ConfigDict, create_model

def tool_from_schema(name: str, description: str, parameters: dict, fn, *, wants_ctx: bool = False) -> Tool:
    """Register a tool from a raw JSON Schema (MCP / OpenAPI / dynamically-generated) — the escape hatch
    when you already have a schema and don't want signature introspection. Args are passed through to `fn`
    (permissive validation: the caller owns the schema). `@tool` stays the ergonomic default."""
    args_model = create_model(f"{name}_Args", __config__=ConfigDict(extra="allow"))
    return Tool(name=name, description=description, parameters=parameters, fn=fn,
                args_model=args_model, wants_ctx=wants_ctx)
```
  (Verify `Tool` field order / `wants_ctx` default in the current dataclass first. The permissive `args_model` validates trivially and `.model_dump()` returns the passed kwargs incl. extras — confirm with a quick probe.)
- [ ] Run + commit: `feat(tools): tool_from_schema — raw-JSON-schema tool registration escape hatch`

---

## Task 4 — Enrich `RunContext` (read-only `usage`/`messages`/`model`/`step`)  *(Batch Q; `durable/context.py` + `core/loop.py` + `agent.py`)*

Pydantic AI's `RunContext` exposes `deps` + `message_history` + `usage` + `run_step` + `retries` (`PYDANTIC_AI.md:31,202`). Verso's exposes only `{trace_id, deps, step, store, hitl}`. Add read-only views so a tool/hook can be budget-aware / history-aware / model-conditional.

- [ ] **Failing test** (`tests/test_ctx_fields.py`): a ctx-aware tool reads `ctx.usage.input_tokens` (cumulative so far), `ctx.messages` (the history list), `ctx.model`, `ctx.step` (current step) mid-run; assert sane values.
- [ ] **Implement**: add to `RunContext` (all defaulted, mutable): `usage: Usage = field(default_factory=Usage)`, `messages: list = field(default_factory=list)`, `model: str = ""`. In `_drive`, inside the step loop, **after** `usage = usage + resp.usage`: `if ctx is not None: ctx.step, ctx.usage, ctx.messages = step, usage, bundle.history`. Set `ctx.model` where ctx is created (`Agent._run`/`stream`: `model=getattr(self.model, "model_id", "")`). Import `Usage` into `context.py` (no cycle: `verso.types` imports nothing from durable).
- [ ] Additive check: ctx-less tools/hooks unaffected; a run with no ctx-reads is byte-identical.
- [ ] Run + commit: `feat(durable): RunContext exposes read-only usage/messages/model/step for tools+hooks`

---

## Task 2 — `Retry(feedback)` self-healing + output validators + configurable reask  *(Batch R; `tools/dispatch.py` + `core/loop.py` + `agent.py`)*

The biggest semantic gap. Pydantic AI: a tool/validator raises `ModelRetry("why")` → a `RetryPromptPart` (the structured error *is* the prompt) → the model self-corrects, bounded by a per-tool/per-output retry budget (`PYDANTIC_AI.md:317,386,422`). Verso has none — tools return a passive `{error}` and output coercion is reask-once-then-raise.

- [ ] **Failing tests** (`tests/test_retry_feedback.py`):
  1. a tool raises `Retry("need a 2-letter code")` on the first call, succeeds on the second (FakeModel scripts a corrected call); assert the loop fed the feedback back and the run completed; assert a per-tool retry **budget** caps an always-raising tool (turns into a terminal error, not an infinite loop).
  2. `Agent.run(task, output_type=T, validators=[v], max_output_retries=2)` where `v` raises `Retry("must be positive")` once → the agent reasks with the feedback and then succeeds; assert `max_output_retries` is honored.
- [ ] **Implement**:
  - `Retry(Exception)` in `verso/tools/errors.py` (or `durable/context.py` next to `Paused`): `__init__(self, feedback: str)`. Export from `verso`.
  - `dispatch`: add `except Retry: raise` **before** the general `except Exception` (propagate, like `Paused`).
  - `_drive` tool section: wrap dispatch in `except Retry as r:` → append a model-visible tool message `content=f"Retry: {r.feedback}"` with `tool_call_id=tc.id, name=tc.name`, bump `retries[tc.name]`; if `retries[tc.name] > max_tool_retries` (default 2, a `run_loop` param) append a terminal `f"Error: tool '{tc.name}' exceeded retry budget"` instead. (Track `retries: dict[str,int]` in `_drive`'s scope.) The model sees the feedback and re-calls. Keep `Paused` handling unchanged.
  - **Output validators + reask budget** in `Agent.run`: add params `validators: list[Callable] = ()` and `max_output_retries: int = 1` (default 1 = today's behavior). After `coerce(...)`, run each validator(parsed); a validator raising `Retry(feedback)` (or a `CoercionError`) triggers a reask that **includes the feedback**; loop up to `max_output_retries`, then raise `StructuredOutputError`. (Generalize the existing one-reask block into a bounded loop.)
- [ ] Additive check: no `Retry` raised + `max_output_retries` default 1 ⇒ byte-identical to today.
- [ ] Run + commit: `feat(core): Retry(feedback) self-healing tools + output validators + configurable reask`

---

## Task 5 — Richer resume (approve-with-edited-args / deny-message / skip)  *(Batch S; `core/loop.py` + `agent.py`)*

LangGraph `Command(resume, update, goto)` and Pydantic AI `ToolApproved(override_args=…)` / `ToolDenied(message=…)` let a reviewer **approve-and-edit**, **deny-with-reason**, or **skip** (`PYDANTIC_AI.md:390`). Verso's `resume(approve|answer)` is approve-only on the ASK-gate path. Enrich the **ASK-gate resume** (the `kind="approve"` branch in `resume_loop`); leave the `kind="input"` (`ctx.hitl.request`) re-run path as-is.

- [ ] **Failing tests** (append to `tests/test_durable_pause_resume.py`): on an ASK-gate pause, `resume(token, approve=True, override_args={...})` runs the held tool **with the edited args**; `resume(token, approve=False, deny_message="use the sandbox")` feeds that exact message back; `resume(token, skip=True)` continues without running the tool (a "skipped by reviewer" tool result).
- [ ] **Implement**: `Agent.resume(token, *, approve=True, answer=None, override_args=None, deny_message=None, skip=False)` → pass through to `resume_loop`. In `resume_loop`'s `kind=="approve"` branch:
  - `skip=True` → `content = f"Tool '{tc_name}' was skipped by the reviewer."` (don't dispatch).
  - `approve and override_args is not None` → dispatch with `override_args` instead of the recovered `args`.
  - `not approve` → `content = deny_message or f"Tool '{tc_name}' was denied by the human reviewer; it did not run."`
  - else (approve, no edits) → existing behavior.
  Keep the `kind=="input"` branch unchanged.
- [ ] Additive check: existing `resume(approve=…)` calls behave exactly as before (new params default to no-op).
- [ ] Run + commit: `feat(durable): richer resume — override_args / deny_message / skip on the approval gate`

---

## Task 6 — Around-step control hook + `bypass_termination` + "plain async Python" example  *(Batch S; `core/loop.py` + `safety/hooks.py` + `docs/`)*

Hooks can observe/veto but not **steer**; termination is hardwired (`_SYNTHESIS.md:94` flagged the missing `bypass_termination`). Give users control flow *without a graph* (thesis intact).

- [ ] **Failing tests** (`tests/test_control_flow.py`):
  1. a `post_tool` (or new `pre_step`) hook that, when it sees a sentinel, sets a flag making the loop **stop early** with a chosen output — assert `stop_reason`/output reflect it. (Mechanism: a `Hooks.should_continue: Callable[[ctx|bundle], bool] | None` checked at the top of each step; returning False ends the run with `StopReason.END_TURN` and the last text.)
  2. a `done`-style tool registered with `bypass_termination=True` returns its result **without ending the loop** (the model keeps going) — proving handoff-style tools (`_SYNTHESIS.md:94`).
- [ ] **Implement**: (a) `Tool.bypass_termination: bool = False`; in `_drive`'s `done` early-return, gate on `tc.name == "done" and result.ok and not t.bypass_termination`. (b) `Hooks.should_continue` (optional predicate); at the top of the step loop, `if hooks.should_continue is not None and not await _fire_pred(...): return AgentResult(END_TURN, last_text, …)`. Keep both no-ops when unset.
- [ ] **Docs**: add `docs/recipes/plain-async-python.md` — the no-graph orchestrator-workers / routing recipe (the PRD-reserved "drop to plain Python" exit, `PRD_v1.md:461`): show calling `agent.run()` inside ordinary `async` control flow (branch, loop, fan-out with `asyncio.gather`) instead of a framework graph. Link it from the README.
- [ ] Additive check: no `should_continue`, no `bypass_termination` ⇒ byte-identical.
- [ ] Run + commit: `feat(core): around-step control hook + bypass_termination + plain-async-python recipe`

---

## Task 7 — `add_messages`-style history hygiene  *(Batch T; `verso/context/` + a test)*

Safe compaction needs dedup + targeted removal (`fw-langchain-langgraph.md:628` #11): dedup-by-id, `RemoveMessage(id=X)` targeted delete, `RemoveMessage(id="__remove_all__")` compaction reset.

- [ ] **Failing test** (`tests/test_history_merge.py`): a `merge_messages(history, incoming)` helper dedups by message id (same id ⇒ replace, not append), a `RemoveMessage(id=X)` drops message X, and `RemoveMessage(id="__remove_all__")` clears all prior — leaving only post-marker messages (the compaction-replace pattern).
- [ ] **Implement**: `verso/context/history.py` — `RemoveMessage` sentinel + `merge_messages(existing, incoming) -> list[Message]`. (Verify `Message` has/needs an `id`; if not, dedup by `tool_call_id` for tool turns + identity for others, and document the limitation — don't silently no-op.) This is a **utility** for compaction authors, not wired into the loop by default (additive).
- [ ] Run + commit: `feat(context): add_messages-style merge + RemoveMessage for safe compaction`

---

## Verification plan
**Automated:** `uv run pytest -q && uv run ruff check verso tests` → all green; **every prior test passes unmodified** (the additive gate — a feature off ⇒ byte-identical). Criterion: tests pass AND no assertion weakened.
**Manual:** set `AnthropicModel(..., temperature=0.2, extra_body={"output_config":{"effort":"high"}})` and confirm it reaches the request; write a tool that raises `Retry`; register an MCP-shaped tool via `tool_from_schema`; resume a paused run with `override_args`.

## Done criteria
A user can, without forking the framework: set any provider/sampling param; retry a tool or output with feedback; register a raw-schema tool; read usage/history/model from `ctx`; approve-and-edit / deny / skip a held tool; stop or steer the loop without a graph; and compact history safely. All additive; thesis ("no forced graph, simple core") intact.

## Out of scope (Tier 3, deferred)
Time-travel `list`/`fork(at_step=N)`; step-output memoization on resume; durable streaming resume; typed-state reducer channels for concurrent multi-agent writes (opt-in only, never the default). pgvector/Mem0 (infra-gated).
