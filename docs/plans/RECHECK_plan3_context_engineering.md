# RECHECK — Verso Phase-0 Plan 3 (Context Engineering)

**Auditor:** RECHECK (review-only, no code changes)
**Date:** 2026-06-06
**Plan:** `docs/plans/2026-06-05-phase0-plan3-context-engineering.md`
**Verdict: SHIP**

---

## 1. Gate results (captured exactly)

```
$ uv run pytest -q
75 passed, 1 skipped in 0.06s

$ uv run ruff check verso tests
All checks passed!
```

- `tests_green`: **yes** — 75 passed, 1 skipped (the skip is `test_e2e_live_anthropic`, gated on `ANTHROPIC_API_KEY` — expected).
- `lint_green`: **yes** — clean.

### Test-count accounting (regression check)

- Plan-2 tip (`b6c2555`) had **53** test functions → 52 passing + 1 live-skipped. Matches the plan's prereq ("52 passed / 1 skipped").
- HEAD (`97d47e0`) collects **76** → 75 passing + 1 live-skipped.
- Plan 3 added **23** new tests: `test_tokens` (3), `test_bundle` (6), `test_prune` (5), `test_context_loop` (4), `test_system_prefix` (4), `test_e2e_inspect_offline` (1).
- `test_anthropic.py` is **unchanged** (3 tests before and after — the assistant/tool-mapping test predates Plan 3). All prior skeleton + Plan-2 tests still present and green; **no regressions**.

---

## 2. Plan alignment (Tasks 1–6)

| Task | Status | Notes |
|---|---|---|
| 1. `estimate_tokens` | ✅ landed verbatim | `~chars/4`, floor `max(1, …)`, empty→0. |
| 2. `ContextBundle` | ✅ landed verbatim | `system` property, `to_messages` (copy), `tool_schema_text` (sorted keys), `stable_prefix`, `sections`, `estimate_tokens`, `render`. |
| 3. `system` prefix in Model layer | ✅ landed verbatim | `base`/`fake`/`anthropic` all gain keyword-only `system`; Anthropic maps to `system` param, omits when falsy. |
| 4. `prune()` observation-masking | ✅ landed verbatim | masks tool-result content beyond `keep_last_n=10`, preserves structure, idempotent. |
| 5. loop owns bundle + budget→prune + `Agent.inspect()` | ✅ landed verbatim | `build_bundle`, budget guard, `max_context_tokens` threaded, `ContextBundle` exported. |
| 6. e2e + README | ✅ landed | `test_e2e_inspect_offline` added; README has the inspect/context snippet. |

Implementation matches the plan's code blocks essentially byte-for-byte.

---

## 3. Correctness probes (each verified by running live Python, not just reading)

### 3.1 `inspect()` byte-equals what the model receives on turn 1 — ✅ TRUE (turn-1 only, by design)
Verified: `agent.inspect(task).to_messages()` == `fm.calls[0][0]`, `.system == fm.calls[0][2]`, tool names equal. This is **a turn-1 claim only** — and that is exactly what the plan and PRD line 306 promise ("what it prints byte-equals what the model receives"). `inspect()` rebuilds the fresh turn-1 bundle via `build_bundle`; it does **not** and is not meant to mirror later turns once history grows or after a prune. The loop owns its own live bundle. **This is correct, not a bug** — but see §5 non-blocking note about documenting the turn-1 scope.

### 3.2 `prune()` correctness + idempotence + never masks non-tool turns — ✅ TRUE
- Idempotent across 1/2/3 applications (`prune(prune(prune(h)))` byte-identical). The `m.content != MASK` guard makes re-masking a no-op.
- Masks exactly `len(tool_idxs) - keep_last_n` oldest tool results (5 of 15 with N=10).
- Never touches `user`/`assistant` turns (filters on `role == "tool"`).
- Masked messages preserve `role`/`tool_call_id`/`name`; only `content` is replaced.
- **Returns a NEW list; input untouched.** Kept (unmasked) messages are the **same object identity** (no needless copy) — good for KV stability and cheap.

### 3.3 system-prefix routing — ✅ TRUE, no double-send
- Instructions route to the Anthropic `system` param (`kwargs["system"] = system` when truthy).
- Verified `test_instructions_go_as_system_not_a_user_message`: history is `["hi"]` only — instructions appear **nowhere** as a user/history message. `build_bundle` seeds history with only the user task; instructions live solely on `bundle.instructions` → `bundle.system`. No leak.
- Anthropic omits `system` from kwargs when `None`/empty (`if system:`).

### 3.4 `estimate_tokens` sanity — ✅ sane
`''→0`, `'a'*40→10`, `'hi'→1`, `'abc'→1` (floor works: `3//4=0 → max(1,0)=1`). Approximate by design (no tokenizer), exactly as the plan scopes.

### 3.5 KV-cache discipline / no mutation of prior messages — ✅ CLEAN
- Loop **appends** to `bundle.history` (assistant + tool turns); never reorders or edits prior turns.
- Prune **reassigns** `bundle.history = prune(...)` to a new list; masked entries are **new** `Message` objects, kept entries keep identity. No in-place mutation of existing `Message` objects anywhere. KV-cache discipline (PRD line 135) honored.
- `stable_prefix()` is byte-identical across turns for the same instructions+tools (proven by `test_stable_prefix_is_byte_identical_across_different_history`).

### 3.6 budget threshold semantics — ✅ intended ceiling, with one benign edge
- `if max_context_tokens is not None and bundle.estimate_tokens() > max_context_tokens: prune(...)`. Compares the **full** estimate (instructions + tools + history) to `max_context_tokens` directly — a **hard ceiling**, strict `>`. This is the plan's intended Phase-0 semantics.
- Benign edge (not a bug): if the over-budget pressure comes from instructions+tools while there are ≤10 tool results, `prune()` is a no-op — the budget cannot be enforced that turn. Harmless: the loop is `max_steps`-bounded, so no infinite loop; nothing crashes; the model simply gets the full (over-budget) context. The PRD's richer behavior (soft ~75–80% ceiling, over-budget warning/blocking event, `compact()` fallback, deterministic grace call) is **explicitly deferred** to later plans (PRD lines 136–137, 322). In-scope.

### 3.7 most-recent tool result is never masked — ✅ TRUE
The loop appends the just-produced tool result, then prunes at the **top** of the next iteration with `keep_last_n=10`, so the newest tool outputs are always retained. In the budget test the last model call sees 10 kept + 2 masked tool messages and the most-recent tool message is unmasked. The model never loses the observation it just generated.

---

## 4. Security — deterministic JSON serialization on non-serializable tool args

**Finding (LOW severity, non-blocking):** `ContextBundle._message_text`, `ContextBundle.render`, and (transitively) `sections`/`estimate_tokens` call `json.dumps(tc.arguments, sort_keys=True)` **without** a try/except. If a `ToolCall.arguments` dict contains a non-JSON-native value (e.g. a `set`), these raise `TypeError: Object of type set is not JSON serializable`. Reproduced:

```
C4 CRASH estimate_tokens: TypeError Object of type set is not JSON serializable
C4 CRASH render:          TypeError Object of type set is not JSON serializable
```

**Why this is LOW / non-blocking:**
- In production, `ToolCall.arguments` is **always** JSON-native: `AnthropicModel` builds it via `dict(block.input)` where `block.input` is parsed straight off the JSON wire. Non-JSON args are unreachable from a real provider.
- The crash is only reachable by hand-constructing an exotic `ToolCall` (tests/fakes) — not a real-world path, no untrusted-input vector.
- `tool_schema_text()` serializes `t.parameters` (a Pydantic-generated JSON schema) — always JSON-safe.

**Asymmetry worth noting:** the loop's `_format_result` **already** guards `json.dumps` with `try/except (TypeError, ValueError) → str(...)`, so tool *results* are crash-proof, but the bundle's *argument* serialization is not. A one-line `default=str` (or the same try/except) on the three `json.dumps(tc.arguments…)` sites would close the asymmetry and make `inspect()` total. Optional hardening, not required to ship.

No other security concerns: no injection surface, no SSRF/eval, instructions never echoed into history.

---

## 5. CORE-GOALS / PRD alignment

Confirmed against `docs/PRD_v1.md`:

- **Context is first-class & inspectable** (PRD §5.2 line 134; line 306) — ✅ `ContextBundle` is a named object; `inspect()` byte-equals turn-1 input.
- **KV-cache discipline** (PRD line 135: stable prefix first, append-only history, deterministic sorted-key JSON) — ✅ `stable_prefix()` + `sort_keys=True` + append-only loop.
- **Observation-masking, N=10, placeholder not delete** (PRD line 137, 322) — ✅ `MASK`, `keep_last_n=10`, structure preserved.
- **prune is LLM-free; compact() deferred** (PRD line 322 two-pass) — ✅ `compact()` correctly absent this plan.
- **No tokenizer dependency** (estimate approximate by design) — ✅ `~chars/4`; `pyproject` unchanged.
- **Loop stays provider-neutral** — ✅ loop calls the `Model` protocol with `system=…`; only `AnthropicModel` knows the wire format. `FakeModel` records the same 3-tuple. Adding a provider needs zero loop changes.
- **Deferred items correctly absent:** real tokenizer ✅, `compact()` ✅, `RunContext[T]` injection ✅ (no `ctx` parameter threaded into tools/hooks — Phase-0 thin, matches PRD §13 sequencing).

PRD-vs-Phase-0 gaps that are **intentionally deferred** (not defects): soft ~75–80% budget ceiling, over-budget warning/blocking *event*, deterministic grace call, `compact()` fallback. All later-plan scope.

---

## 6. Coverage gaps (non-blocking, for later)

- No test asserts `prune()` does not mutate its input list (the property holds — verified manually — but isn't pinned by a test).
- No test for the budget no-op edge (over-budget via instructions+tools with ≤10 tool results) — behavior is benign but untested.
- No test that `stable_prefix()` stays identical *through an actual loop run* (only the bundle-level unit test exists).
- `inspect()`'s turn-1-only scope is correct but undocumented in the docstring beyond "(turn 1)" — a one-line note that it does not track later turns would prevent misuse.

---

## 7. Verdict

**SHIP.** All gates green (75 passed / 1 live-skipped, ruff clean). All six tasks landed as specified with no regressions to the 52-test baseline. Every flagged correctness concern was probed live and is correct: turn-1 byte-equality holds, `prune()` is correct + idempotent + non-tool-safe, system instructions route to `system` with no double-send, `estimate_tokens` is sane, no prior-message mutation (KV-cache clean), and the budget threshold is the intended hard ceiling. The single finding (unguarded `json.dumps` on tool args in the bundle) is LOW severity, unreachable from real providers, and optional to harden. CORE-GOALS/PRD alignment is strong; all deferred items are correctly absent.

### Blocking fixes
None.

### Non-blocking (optional)
1. `verso/context/bundle.py:14` and `:63` (and transitively `:35` is already safe) — guard `json.dumps(tc.arguments, sort_keys=True)` with `default=str` (or try/except like `loop._format_result`) so `inspect()`/`render()`/`estimate_tokens()` are total on exotic args. Closes the asymmetry with `verso/core/loop.py:17-20`.
2. `verso/core/loop.py:37` — optional: document/handle the over-budget-via-prefix no-op (or add the PRD soft-ceiling) when budget work lands.
3. `verso/agent.py:23` — extend the `inspect()` docstring to state it reflects turn 1 only (not later/post-prune turns).
4. Add tests: prune-non-mutation, budget no-op edge, `inspect()` turn-1-only scope.
