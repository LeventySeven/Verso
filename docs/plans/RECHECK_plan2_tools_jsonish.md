# RECHECK — Phase-0 Plan 2 (tools depth + jsonish)

**Auditor pass:** 2026-06-05 · review-only (no code changed)
**Plan:** `docs/plans/2026-06-05-phase0-plan2-tools-jsonish.md`
**PRD refs:** §5.3 (tools), §13 Phase 0 (`jsonish` = the one engine built in v1; rest of structured-output composed from Instructor later)

---

## Verdict: FIX-THEN-SHIP

The plan landed faithfully (all 6 tasks, all specified tests green, lint clean, zero new deps, loop stays provider-neutral, deferred items correctly NOT built). But `jsonish._light_fix` runs raw regexes over the **entire candidate text including string contents**, so it silently corrupts string *values* in exactly the documents it exists to repair. That is a correctness bug in the one non-composable engine this plan was meant to build well. Plus a usage-accounting bug on the reask path. Both are small, well-contained fixes — ship after they're fixed.

- **tests_green:** YES — `uv run pytest -q` → **50 passed, 1 skipped** (the 1 skip is the live Anthropic e2e, gated on `ANTHROPIC_API_KEY`).
- **lint_green:** YES — `uv run ruff check verso tests` → **All checks passed!**
- **Regression (25 walking-skeleton tests):** PASS. Skeleton set = test_agent(2), test_anthropic(3), test_dispatch(4), test_fake_model(5), test_loop(4), test_tool(3), test_types(3), test_e2e original 2 (`test_e2e_fake_full_path` + skipped `test_e2e_live_anthropic`) = 25; all green. Plan-2 added 25 more (builtins 3, loop_done 2, jsonish 9, coerce 5, structured_output 4, e2e +2).

---

## Blocking fixes

### B1 — `_light_fix` corrupts JSON **string contents** (`verso/tools/jsonish.py:55-60`)

All four substitutions run over the whole candidate, with no awareness of string boundaries. Because `_light_fix` only runs *after* strict `json.loads` fails (`parse`, lines 79-82), it fires on precisely the documents that contain Python literals / trailing commas — and if any string value happens to contain the words `True`/`False`/`None` or a `,]` / `,}` sequence, that value is mutated. Verified live:

```
parse('{"note": "this is True love", "v": True}')  -> {'note': 'this is true love', 'v': True}   # "True love" -> "true love"
parse('{"msg": "None of that", "x": None}')        -> {'msg': 'null of that',  'x': None}          # "None of that" -> "null of that"
parse('{"s": "a,]b", "n": None}')                  -> {'s': 'a]b',             'n': None}           # ',]' eaten inside the string
```

This is data corruption, not a parse failure — the caller gets a *successfully* coerced object with wrong field values and no error. It directly undermines the PRD §13 claim that `jsonish` is "the one engine built in v1, genuinely non-composable" built at full quality; BAML's actual fixer is string-aware for this reason.

Fix direction (no new dep): make the literal/comma fixes string-aware, e.g. tokenize like `_first_balanced` already does (it correctly tracks `in_str`/`esc`) and only rewrite outside strings; or split on a JSON-string regex and apply subs only to the non-string segments. The machinery to track string state already exists in this same file (lines 26-33).

### B2 — reask path **drops the first attempt's usage** (`verso/agent.py:34-37`)

On a reask, `retry = await run_loop(...)` produces a fresh `AgentResult` whose `.usage` covers only the retry. The returned object is `retry` (line 37), so the first run's tokens are **discarded** — the caller is under-billed and `result.usage` lies about what the agent actually spent. Verified:

```
first run usage 10/5, reask usage 7/3  ->  result.usage == Usage(input=7, output=3)   # 10/5 vanished
result.steps == 1                                                                       # also only the retry's steps
```

The orchestrator brief asked specifically whether reask "leaks or double-counts." Answer: it **under-counts** (loses the first attempt entirely). Fix: carry `result.usage` into the returned object, e.g. `retry.usage = result.usage + retry.usage` (and decide whether `steps` should sum too) before returning on success, and also fold it into the `StructuredOutputError` path if usage is ever surfaced there. `Usage.__add__` already exists (`types.py:19`).

---

## Non-blocking (note, don't gate ship)

- **`_first_balanced` is anchored to the *first* opening bracket and never retries from a later one** (`jsonish.py:21-42`). A stray non-JSON `{`/`[` earlier in the prose makes the whole extraction fail even when a clean object follows. Verified: `parse('use {curly} braces like {"a": 1}')` raises `JsonishError`; `parse('he said "hi {there" and then {"a": 1}')` also raises. Acceptable for a "common-case waterfall" (plan §13 scopes `jsonish` to the common case), but it's the most likely real-world miss after B1. A backtracking variant (try each opener until one yields valid JSON) would close it; defer unless dogfood hits it.
- **Multi-tool turn containing `done` abandons later tool calls in the same turn** (`loop.py:39-49`). If an assistant turn emits `[think, done, think]`, the loop returns on `done` and the trailing `think`'s `tool_call_id` never gets a result message. Harmless here (the loop exits, so no malformed history is ever sent back to a provider), and matches the intended "done = terminate" semantics — but worth a one-line comment so a future maintainer doesn't think it's an oversight. Verified: output `FINAL`, `StopReason.DONE`, trailing call dropped cleanly.
- **`done` is recognized by hardcoded name string** (`loop.py:46`, `tc.name == "done"`). Fine for Phase 0, but it couples the loop to the builtin's name; if a user shadows/ renames `done` the short-circuit silently won't fire. A marker attribute on the `Tool` (e.g. `is_terminal`) would be cleaner later. Not in scope for this plan.
- **`coerce` Optional/Union coverage is untested.** `test_coerce.py` covers BaseModel, `list[int]`, mismatch, unparseable. `TypeAdapter` handles `Optional[T]`/`int | str` fine, but there's no test pinning it, and `jsonish` returning `null` -> `Optional` is a plausible LLM case. Add a couple of cases (e.g. `coerce("null", Optional[int])`, a `Union`). Coverage gap, not a bug.
- **`jsonish` has no test for adversarial/deeply-nested input.** I probed both: 200-deep nesting parses in ~0ms; an unclosed fence with 5000 `{` returns in ~0.3ms. **No catastrophic backtracking** — `_FENCE` uses a lazy `.*?` and `_light_fix`'s patterns are linear; `_first_balanced` is a single O(n) pass. Security-wise this is clean; just unpinned by tests.
- **`done` short-circuit only on `result.ok`** (`loop.py:46`). If `done`'s args fail validation, dispatch returns `ok=False`, the loop feeds the error back and continues — correct behavior (lets the model retry), but there's no test for "done with bad args." Minor coverage gap.
- **`think` returns the constant `"noted"`** while its docstring says "no side effects" — consistent with PRD §5.3 ("`think` = no-op CoT scratchpad"). Fine.

---

## CORE-GOALS / PRD alignment — PASS

- **`jsonish` is the one non-composable engine built here** ✓ (`jsonish.py` + `coerce.py`). Modulo B1, the waterfall (strict -> fenced -> balanced -> light-fix) matches §13's "BAML-style waterfall, the one engine built in v1."
- **Reask is a minimal single retry, NOT a re-implemented retry engine** ✓ (`agent.py:28-43`): one `try`, one reask, raise on second failure. No mode-map, no provider branching, no `Partial[T]` — Instructor composition correctly deferred.
- **No new dependencies** ✓ — `jsonish` uses only stdlib `json`/`re`; `coerce` uses Pydantic v2 `TypeAdapter` (already a dep). No import added beyond existing.
- **Loop stays provider-neutral** ✓ — `loop.py` talks only to the `Model` protocol; the `done` short-circuit is on tool *name*, not provider.
- **Deferred items NOT built** ✓ — confirmed absent: no Instructor mode-map / provider structured-output map; no BAML typed-Flag or streaming `Partial[T]`; no tool-argument repair ladder (PRD §5.3's `json.loads->ast->json5->repair_json` ladder is *not* present — correct, it's deferred); no full `ToolError{kind,can_retry}` envelope (`dispatch.py` still returns the simple `{ok,data,error}`). Nothing over-built.
- **`done` -> `StopReason.DONE`** ✓ (`types.py:9`, `loop.py:46-48`); termination is a named enum, not text-sniffing (PRD §5.1 invariant).

## Plan task-by-task — all landed as specified

| Task | Spec | Landed | Note |
|---|---|---|---|
| 1 | `StopReason.DONE` + `think`/`done` builtins | ✓ | verbatim to plan; `test_builtins.py` present (3 tests) |
| 2 | loop terminates on `done` | ✓ | `loop.py:46-48` exactly as planned |
| 3 | `jsonish.parse` waterfall | ✓ | matches plan code byte-for-byte; **B1 bug is inherited from the plan's own snippet** |
| 4 | `coerce()` + errors | ✓ | `CoercionError`/`StructuredOutputError` both defined in `coerce.py` |
| 5 | `Agent.run(output_type=)` + one reask | ✓ | `agent.py` matches plan; **B2 usage-drop inherited from plan snippet** |
| 6 | e2e + README | ✓ | 2 offline e2e tests added; README snippet present |

Note: both blocking bugs (B1, B2) are present **in the plan's own code listings**, so the implementer faithfully transcribed the plan — the defects are design-level, not implementation drift.

---

## Commands run

```
uv run pytest -q                  -> 50 passed, 1 skipped in ~0.05s
uv run ruff check verso tests     -> All checks passed!
uv run pytest <skeleton 25>       -> 24 passed (+1 skipped live e2e) = 25 green
```
