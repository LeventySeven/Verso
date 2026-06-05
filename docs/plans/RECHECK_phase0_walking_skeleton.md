# RECHECK — Verso Phase-0 Walking Skeleton (Tasks 1–10)

**Auditor role:** review-only. No code was changed. Findings below are for the orchestrator to act on.
**Date:** 2026-06-05
**Scope reviewed:** all of `verso/`, all of `tests/`, against `docs/plans/2026-06-05-phase0-walking-skeleton.md`, `docs/PRD_v1.md`, `research/THESIS_VERIFICATION.md`.

---

## Test + Lint status

- **Tests: GREEN.** `uv run pytest -q` → **25 passed, 1 skipped** in ~0.04s. The 1 skip is `test_e2e_live_anthropic` (correctly gated on `ANTHROPIC_API_KEY`). All 10 task commits are present and the per-task expected counts match.
- **Lint: RED (4 errors).** `uv run ruff check verso tests` → **4 errors, 3 auto-fixable**:
  1. `tests/test_dispatch.py:2` — `F401` unused `import pytest`.
  2. `tests/test_fake_model.py:25` — `E402` module-level import (`from verso.model.fake import FakeModel`) not at top of file. This is a direct artifact of the plan (Task 6 Step 1 says "append" the import mid-file); it is intentional in the plan but ruff flags it.
  3. `tests/test_loop.py:4` — `F401` unused `Message`.
  4. `verso/core/loop.py:6` — `F401` unused `ToolCall`.

The plan's Done-criteria explicitly require `ruff check verso tests` to be **clean**, so lint failing is a **plan-violation / blocking** item even though it is trivial.

---

## Bugs

### B1 (non-blocking, latent) — `_build_args_model` mis-handles `*args` / `**kwargs`
`verso/tools/tool.py:24-29` iterates `sig.parameters` and only skips `self`/`cls`; it never inspects `param.kind`. A tool declaring `*args` or `**kwargs` produces nonsense schema fields (verified live: `def f(a:int, **kw)` → `kw` becomes a required `string` field; `*args` → `args` becomes a `string` field), and at dispatch `validated.model_dump()` would then pass a literal `kw`/`args` kwarg into `fn`, breaking the call. Out of scope for the documented `@tool` contract (plain typed params), so not blocking — but it is a real correctness gap worth a 2-line guard (`if param.kind in (VAR_POSITIONAL, VAR_KEYWORD): continue`).

### B2 (non-blocking, by-design-for-now) — empty model output yields empty `AgentResult.output`
`verso/core/loop.py:34-36`: if the model returns no tool calls and empty text, the loop returns `END_TURN` with `output=""`. Acceptable for the skeleton; no `StopReason` beyond the three exists yet (plan defers others). Flag only so it is a conscious choice later.

### No other correctness bugs found.
The loop correctly: sums usage across steps, appends the assistant turn with both text and tool_calls before dispatching, feeds each tool result back keyed by `tool_call_id`, reports unknown tools as a tool message (recoverable, does not crash), and caps at `max_steps` returning `steps == max_steps`. `dispatch` validates then runs, awaits awaitables, and converts both `ValidationError` and arbitrary tool exceptions into the `{ok,data,error}` envelope. The Anthropic mapper round-trips text, tool_use, and tool_result blocks correctly and only adds `tools` when non-empty.

---

## Security

- **No `eval`/`exec`, no `subprocess`, no `shell=True`, no string-built SQL.** Nothing in the package shells out or evals.
- **No secret leakage.** `ANTHROPIC_API_KEY` is never read in package code; the SDK reads it from env on its own. The key is only referenced in the test skip-guard. No keys, tokens, or PII in source.
- **Broad `except Exception` in `dispatch.py:30` is appropriate and labeled** (`# noqa: BLE001 — tool failures are data, not exceptions`). It captures `type(e).__name__: e` into the error string rather than swallowing silently, and the loop surfaces it to the model. This is the intended design ("dispatch NEVER raises into the loop"), not error-masking. The only caveat: it also catches `KeyboardInterrupt`? No — bare `Exception` does **not** catch `KeyboardInterrupt`/`SystemExit` (those are `BaseException`), so cancellation still propagates. Correct.
- **Tool error strings are echoed back to the model verbatim** (`f"Error: {result.error}"`). For a local-function tool registry this is fine; when MCP/openapi adapters land (later phase), error text from untrusted tool sources will reach the prompt — note for the PRD's `trust_level` work, not a Phase-0 issue.

No security blockers.

---

## Anti-patterns / un-idiomatic Python

- **A1 (cosmetic):** `verso/model/anthropic.py` uses bare `list[dict]` return hints (e.g. `_to_anthropic_messages -> list[dict]`) instead of `list[dict[str, Any]]`. Harmless; matches the plan verbatim.
- **A2 (cosmetic):** Per-field `title` keys remain in the generated JSON-schema `properties` (only the top-level `title` is popped at `tool.py:38`). Anthropic ignores unknown schema keys, so no functional impact; could be stripped for cleanliness later.
- **A3 (test hygiene, non-blocking):** `@tool def add` is re-defined at module level in five separate test files. Because each is its own module this is safe, but it is duplication; a shared fixture would be cleaner (not required for the skeleton).
- The three lint `F401`s (B/loop `ToolCall`, test `Message`, test `pytest`) are dead imports — see Lint status.
- **No dead/speculative code beyond the unused imports.** Crucially, the team did **not** stub streaming, memory, jsonish, context-engineering, failover, or extra `StopReason`s — exactly as the plan's "do not stub speculatively" instruction demanded. This is a positive.

---

## Goal + principle alignment

| Principle (plan / PRD / thesis) | Status | Evidence |
|---|---|---|
| **Keep it simple, no over-engineering, no speculative stubs** | ✅ PASS | Whole package is ~150 LoC across 8 files. None of the deferred subsystems (streaming, memory, jsonish, context, failover) are stubbed. Matches THESIS_VERIFICATION's "stay ruthlessly simple in the tactical layer." |
| **Loop is provider-neutral (ONLY `model/anthropic.py` imports `anthropic`)** | ✅ PASS | `grep` across `verso/` finds the single `from anthropic import AsyncAnthropic` at `anthropic.py:21`, lazily inside the `client` property. The loop depends only on the `Model` protocol. A second provider needs zero loop changes. |
| **Dispatch NEVER raises into the loop** | ✅ PASS | `dispatch.py` wraps both validation and execution; returns `ToolResult(ok=False, error=...)` on every failure path. The loop's unknown-tool branch also produces a message, never an exception. Tests `test_dispatch_catches_exceptions` + `test_loop_unknown_tool_is_reported_not_crashed` cover it. |
| **Single TypeAdapter/create_model schema path** | ✅ PASS (with nuance) | One path: `tool.py:_build_args_model` → `pydantic.create_model` → `.model_json_schema()`, and the **same** `args_model` is reused at dispatch for validation. No second/divergent schema generator exists. (Plan used `create_model`, not `TypeAdapter`; functionally the single-source-of-truth intent is met.) |
| **Tactical ↔ durable seam left clean, not prematurely built** | ✅ PASS | The durable runtime, memory, `RunContext`, hooks, `ModelPolicy`, and `ContextBundle` from the PRD are entirely absent — correctly deferred. The seam is the `Model` protocol + `Tool` dataclass + `AgentResult`; nothing durable is half-wired. |
| **Native-tools-first** | ✅ PASS | The only tool path is the native `@tool` decorator over a Python function. No MCP/openapi adapter was introduced (PRD demotes those to opt-in later). |

**One alignment wrinkle (non-blocking, plan-faithful):** the PRD (§5.2, KV-cache discipline; the example surface) treats `instructions` as a stable **system/prefix** layer. The skeleton instead injects `instructions` as a plain `user` message (`loop.py:24-25`), which the Anthropic mapper emits as a `user` block — producing **two consecutive `user` messages** (instructions, then task) with **no `system` param ever set**. This is exactly what the plan's code specifies, so it is faithful to *this* plan, but it diverges from the PRD's "instructions = immutable prefix / system" intent. Worth correcting when the context/KV-cache phase lands; not a Phase-0 defect.

---

## Plan alignment (per-task)

All 10 tasks landed, one commit each, in order (`git log`: `5c00942`→`90287e8`), matching the plan's commit messages.

| Task | Landed? | Notes |
|---|---|---|
| 1 — scaffold (`pyproject.toml`, pkg dirs) | ✅ | `pyproject.toml` is byte-for-byte the plan's (pydantic≥2.7, anthropic≥0.40, pytest-asyncio auto, ruff line-length 100). Empty `__init__` files present. |
| 2 — `types.py` (StopReason/Usage/AgentResult) | ✅ | Verbatim. `Usage` frozen+hashable, `__add__` correct. |
| 3 — `model/base.py` (Model protocol + msg types) | ✅ | Verbatim. `Message` mutable-default `tool_calls` uses `field(default_factory=list)` — correct, no shared-mutable bug. |
| 4 — `@tool` + schema-gen | ✅ | Verbatim. See B1 (`*args/**kwargs` latent gap) — beyond the plan's tested surface. |
| 5 — dispatch `{ok,data,error}` | ✅ | Verbatim. |
| 6 — `FakeModel` | ✅ | Verbatim — incl. the mid-file import that trips ruff E402 (the plan literally instructs "append"). |
| 7 — ReAct loop | ✅ | Verbatim. |
| 8 — `Agent` + `init_model` | ✅ | Verbatim. `init_model` only knows `anthropic`, raises `ValueError` otherwise — matches plan. |
| 9 — `AnthropicModel` | ✅ | Verbatim. DI client + lazy real client. 3 mapping tests pass. |
| 10 — e2e + live smoke + README quickstart | ✅ | `test_e2e_fake_full_path` passes; live test skipped without key. README has the Quickstart block. |

**Deviations:** none functional. The only gap vs the plan's **Done-criteria** is the lint-clean requirement (4 ruff errors), three of which are dead imports the implementer left behind and one (E402) baked into the plan's own test-authoring instruction.

**Under-tested areas (acceptable for a skeleton, noting for the record):**
- No test asserts `instructions` actually reaches the model history (the two-user-message behavior in B/alignment is untested).
- No test for a tool returning a non-str/non-JSON value through `_format_result` (the `str(obj)` fallback path).
- No test for the `init_model` unknown-provider `ValueError`.
- `*args/**kwargs` schema-gen (B1) is untested — which is why the latent bug is invisible.

---

## Verdict + ordered fix list

**Verdict: FIX-THEN-SHIP.** The skeleton is functionally correct, secure, principle-aligned, and faithful to the plan task-for-task. The only thing standing between it and the plan's own Done-criteria is lint cleanliness. Fix the 4 lint errors and it ships.

**Blocking (required to meet plan Done-criteria — all trivial):**
1. `tests/test_dispatch.py:2` — remove unused `import pytest` (F401).
2. `tests/test_loop.py:4` — drop unused `Message` from the import (F401).
3. `verso/core/loop.py:6` — drop unused `ToolCall` from the import (F401).
4. `tests/test_fake_model.py:25` — resolve E402: either move `from verso.model.fake import FakeModel` to the top of the file, or add a scoped `# noqa: E402` (the plan's "append" instruction caused this). Moving it up is cleaner.
   - (Items 1–3 are `ruff check --fix`-able in one shot; 4 needs a manual move or noqa.)

**Non-blocking (defer or pick up opportunistically):**
- B1: guard `_build_args_model` against `VAR_POSITIONAL`/`VAR_KEYWORD` params (`tool.py:24`).
- Alignment wrinkle: route `instructions` as a `system`/stable-prefix layer (not a `user` message) when the context/KV-cache phase lands; avoid two consecutive `user` messages in the Anthropic mapper.
- A1: tighten `list[dict]` hints to `list[dict[str, Any]]` in `anthropic.py`.
- A2: strip per-field `title` from generated tool schemas if a cleaner payload is wanted.
- A3: factor the duplicated test `add` tool into a shared fixture.
- Coverage: add tests for `init_model` unknown-provider `ValueError`, `_format_result` non-str fallback, and the `instructions` → history wiring.
