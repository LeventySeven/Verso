# RECHECK — Phase-0 Plan 5 (Streaming) — FINAL Phase-0 plan

**Auditor verdict: SHIP**
**Date:** 2026-06-06 · **Branch:** `main` · **HEAD:** `0d88227`

Plan 5 (the typed event stream + SSE transport) is implemented cleanly, fully tested,
and completes Phase 0. Review-only audit — no code changed. The findings below are all
non-blocking; there are zero blocking fixes.

---

## 1. Gate results (captured exactly)

| Gate | Result |
| --- | --- |
| `uv run pytest -q` | **118 passed, 1 skipped** (0.08s) |
| `uv run ruff check verso tests` | **All checks passed!** |
| `git branch --show-current` | `main` ✅ (plan requires commit on main, no feature branch) |
| Skip reason (`-rs`) | `tests/test_e2e.py:30: no ANTHROPIC_API_KEY` — intentional live-only test, **not a regression** |

`git log --oneline -8` — the five Plan-5 commits land in plan order on top of the Plan-4 tip:

```
0d88227 feat(stream): SSE transport; e2e stream/sse; README streaming snippet
e7a4d27 feat: Agent.stream() typed event stream + exports
a95adf3 feat(core): run_stream async generator (typed event stream over the loop)
03e6012 feat(model): ModelStreamChunk + iter_model_stream (stream-or-complete) + FakeModel.stream
709548d feat(stream): StreamEvent + 7 EventTypes
a61a4b7 docs(plans): Phase 0 Plan 5 — streaming
3b075f3 harden(model): tighten classify context-window match; doc FailoverModel .attempts race
44761ce feat(model): export reliability layer + Agent failover e2e + README
```

---

## 2. Behavioral verification (live probes, not just reading)

Every step-3 concern was probed directly with `uv run python`, not inferred.

### Event sequence matches loop semantics — CONFIRMED
- **`tool.start` strictly before `tool.result`**, correctly interleaved across multiple
  tool calls in one step. Probed a 2-tool-call step: order was
  `start(add) → result(add,2) → start(add) → result(add,4)`. ✅ (stream_loop.py:48,56)
- **done-tool terminates with `StopReason.DONE`**: probed; final `DONE` event carries
  `output=content`, `stop_reason=DONE`. ✅ (stream_loop.py:57–60)
- **`max_steps` terminates with `StopReason.DONE` event / `MAX_STEPS` reason**: the
  terminal `StreamEvent(type=DONE, result=...MAX_STEPS)` fires after the loop; tested
  by `test_stream_hits_max_steps`. ✅ (stream_loop.py:63–64)

### True-delta property is REAL — CONFIRMED
`FakeModel.stream()` splits text at `len(text)//2` into two non-empty pieces
(fake.py:30–33), each emitted as a `MESSAGE_DELTA`. Concatenation `==` final text is
asserted in `test_stream_tool_then_text`, `test_fake_model_streams_text_in_deltas_then_usage`
(`len(texts) >= 2`), and the e2e test. ✅

### `iter_model_stream` uses `stream()` vs `complete()` correctly, NO double-consume — CONFIRMED
Probed a model exposing BOTH `stream()` and `complete()`: `stream_called=1,
complete_called=0`. The `getattr(model,"stream",None)` branch `return`s after the
stream loop (streaming.py:35), so `complete()` is unreachable when `stream()` exists.
The fallback path (`_chunks_from_response`) only runs when `stream` is absent. No path
consumes the model twice. ✅

### FakeModel gaining `stream()` does NOT break `fm.calls` introspection — CONFIRMED
Both `complete()` (fake.py:19) and `stream()` (fake.py:25) append the **same 3-tuple**
`(list(messages), list(tools), system)` introduced in Plan 3. Audited every `.calls`
reader in the suite: `test_loop`, `test_context_loop`, `test_system_prefix`,
`test_structured_output`, `test_model_streaming`, `test_agent_stream` all index
`[0]/[1]/[2]` — consistent. (`test_failover*` `.calls` is an int counter on a different
fake class, unrelated.) ✅

### `to_sse` field omission + crash safety — CONFIRMED
- `ok=False` is **kept** (serialized `"ok": false`), because `False is not None` and
  `False != ""` are both true. ✅
- `step=1`, `arguments={}` are kept. ✅
- Empty string fields (`text==""`, `content==""`) are omitted by `val != ""`. ✅
- `default=str` prevents a crash on a non-`AgentResult` / non-JSON `result` — probed a
  bespoke object; serialized to its `repr` without raising. ✅ (sse.py:28)

### run vs run_stream parity — CONFIRMED on the paths that matter
Duplicated loop logic is a **known, plan-acknowledged tradeoff** (Plan says
"`run_stream()` ... mirrors `run_loop`"). I diffed behavior, not just code:
- **Raising tool then recovery**: both produce `output="recovered"`, `END_TURN`,
  `steps=2`; stream additionally surfaces `tool.result ok=False,
  content="Error: RuntimeError: kaboom"`. ✅
- **Usage accumulation**: identical `Usage(input_tokens=17, output_tokens=8)` across a
  tool step + final step. ✅
- **done-tool output**: `run_loop` returns `_format_result(result.data)`; `run_stream`
  returns `content` which equals `_format_result(res.data)` when `ok` — same value. ✅
- **FailoverModel** (no `stream()`): streams via the `complete()` fallback exactly as
  the plan claims ("every existing model incl. FailoverModel streams events today").
  `hasattr(FailoverModel, "stream") == False` → fallback path. ✅

No divergence found that would make `run` and `stream` behave differently for the same
input. The single structural difference (two loop bodies) is intentional and documented.

---

## 3. CORE-GOALS alignment (plan + PRD_v1)

- **Event stream + SSE is the deliverable** — delivered: 7 `EventType`s, `run_stream`
  generator, `Agent.stream()`, `to_sse()`/`sse()` with `data: [DONE]\n\n` sentinel. ✅
- **True token-level Anthropic streaming correctly DEFERRED** — no `AnthropicModel.stream()`;
  complete-only models emit the answer as one `message.delta` via the fallback. The seam
  (`iter_model_stream` honoring any `model.stream()`) makes the future provider stream a
  drop-in. ✅ (matches plan "Out of scope")
- **`Agent.run()` unchanged** — verified by `git diff 44761ce..HEAD -- verso/agent.py`:
  the ONLY change is the additive `stream()` method + two imports. `run()/_run()/inspect()`
  are byte-identical. ✅
- **Provider-neutral** — `iter_model_stream(model, ...)` duck-types on `getattr(model,
  "stream", None)`; nothing anthropic-specific in the stream path. ✅

---

## 4. Phase-0 completeness — all five capabilities present & green

| # | Capability | Modules | Tests (all green) |
| --- | --- | --- | --- |
| 1 | Clean async ReAct loop | `core/loop.py`, `agent.py` | test_loop (4), test_loop_done (2), test_agent (…) |
| 2 | Native `@tool` + dispatch + jsonish structured output | `tools/tool.py`, `tools/dispatch.py`, `tools/coerce.py`, `tools/jsonish` | test_tool (3), test_dispatch (4), test_coerce (5), test_jsonish (10), test_structured_output (5) |
| 3 | Context engineering (bundle/inspect/prune/budget) | `context/bundle.py`, `context/prune.py`, `context/tokens.py` | test_bundle (7), test_prune (5), test_tokens (3), test_context_loop (4), test_system_prefix (4) |
| 4 | Model reliability (classify/retry/failover) | `model/errors.py`, `model/retry.py`, `model/failover.py` | test_errors (9), test_retry (6), test_failover (6), test_failover_e2e (2) |
| 5 | Streaming + SSE | `stream/events.py`, `stream/sse.py`, `model/streaming.py`, `core/stream_loop.py` | test_events (4), test_model_streaming (4), test_stream_loop (4), test_agent_stream (2), test_sse (4) |

Plus `test_e2e.py` ties it together (offline stream + SSE; one live test skipped w/o key).
**Nothing Phase-0-scoped is missing.** Phase 0 is complete.

---

## 5. Findings — non-blocking only

1. **`reasoning.delta` branch is dead code today (forward-compat).** `stream_loop.py:33–34`
   handles `kind=="reasoning"`, but no shipped model (incl. `FakeModel`) yields reasoning
   chunks, so the branch is never executed and never tested. This is **explicitly DEFERRED
   in the plan** ("the `reasoning.delta` event type exists ... but no shipped provider does
   yet"). Acceptable; flag only so a future reviewer doesn't read it as tested.

2. **`EventType.ERROR` is never emitted by `run_stream`.** Tool failures surface as
   `tool.result` with `ok=False` (good, parity with `run_loop`); a model-call exception
   propagates out of the async generator rather than becoming an `error` event + graceful
   `DONE(StopReason.ERROR)`. `run_loop` has the identical behavior, so this is **not a
   stream regression** — it's a loop-wide design choice (StopReason.ERROR is documented as
   "later phases add more reasons"). The `ERROR` event type is unit-tested for construction
   only (test_events.py:27). Consider, in a later phase, wrapping the model call in
   try/except to emit a terminal `ERROR` event so SSE consumers see a clean stream end
   instead of a raised exception mid-iteration.

3. **Duplicated loop logic (run_loop vs run_stream).** Two parallel loop bodies must be
   kept in sync by hand; a future change to one (e.g., a new termination reason or a tool
   pre/post hook) can silently skip the other. Verified they currently agree on output,
   stop_reason, steps, and usage across normal / done / max_steps / raising-tool /
   failover paths. **Known, plan-acknowledged tradeoff** — noted, not a defect. If this
   grows, factor the shared body into a single driver that takes an event sink.

4. **Empty-result done tool drops `content` over the wire (cosmetic).** A `done(result="")`
   produces `tool.result ok=True` with `content=""`, which `to_sse` omits (by the `!= ""`
   rule), and a final `DONE` with `output=""`. Consistent with `run_loop` and harmless,
   but an SSE consumer sees a `tool.result` with no `content` field for an empty answer.
   No action needed.

---

## 6. Regression check

All prior tests pass (118 passed, 1 intentional live skip). The Plan-5 changes are
strictly additive:
- `iter_model_stream` adds a `stream()` branch without touching `complete()`.
- `FakeModel.stream()` is new; `complete()` untouched → `Agent.run()/run_loop` unaffected.
- `agent.py` adds `stream()` only.
- `__init__.py` adds two exports.
No existing module's behavior changed. **No coverage regression.** The only new-but-untested
paths are the two deferred forward-compat branches noted above (reasoning.delta, ERROR
event), both out of Phase-0 scope.

---

## Bottom line

**SHIP.** Tests green, lint clean, on `main`, Phase 0 complete. Zero blocking issues.
The two untested branches (`reasoning.delta`, `ERROR` event emission) are deliberately
deferred and mirror existing loop behavior; address them when wiring a real provider's
token stream and a streaming error path in a later phase.
