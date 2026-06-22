# Plan 22 — Residual-mine slate (loop honesty · durable/context integrity · eval moat)

> Source: a residual deep-mine of the `researchfms` primaries (teardowns + core transcripts + BAD_GUIDE)
> against shipped Verso, adversarially verified vs `verso/*.py` (`research/10_residual_mine/GAP_REPORT.md`,
> 54-agent workflow). Verdict: **no new primitive category** — the residual is incremental hardening, and
> the strongest findings are **contradictions where the docs overclaim** mechanisms the source lacks.
> User approved the recommended 7-item slate + a doc-truth pass.

Every item is **additive and byte-identical when unused**. Test-first → full suite → recheck → gated commit per batch.

## Slate A — make the loop's terminal states honest (closes 3 contradictions)
1. **Stuck-detector + `StopReason.STUCK`** (`core/stuck.py`, `types.py`, `core/loop.py`, `stream_loop.py`).
   New pure `detect_stuck(history, thresholds)`: (a) same `(tool,args)` signature repeated `repeated_action`
   times in a row; (b) `tool_errors` consecutive `Error:` tool results. Default **on**, thresholds=4 (above
   the small `max_steps` caps in unit tests → healthy/short runs never trip it; a real doom-loop at
   `max_steps=25` is caught early). `stuck_thresholds=None` disables. Byte-identical for non-doom-loop runs.
2. **Grace call at max_steps** — **opt-in** `max_steps_policy: 'stop'|'generate' = 'stop'`. On `generate`,
   one final `model.complete(..., tools=[])` after the loop yields a best-effort answer; default `stop`
   keeps today's `output=''`+`MAX_STEPS` (byte-identical). (`output=''`+`MAX_STEPS` is honest — the run hit
   the cap; grace is a production nicety, so it is opt-in, not the default.)
3. **Non-idempotent `max_attempts=1`** — `Tool.idempotent: bool=True` + `Tool.max_attempts: int|None=None`,
   **decoupled from `privileged`** (orthogonal). Retry budget per tool = `max_attempts-1` if set, else
   `0 if not idempotent else max_tool_retries`. Byte-identical for idempotent tools (the default). Fixes the
   real correctness bug: a `send_email`/`charge` tool that raises `Retry` is no longer auto-re-run.

## Slate B — durable / context integrity
4. **`repair_history(history)`** (`context/history.py`) — pure, no-op on healthy history: closes orphan
   tool_calls (synthetic `[interrupted]` result), drops orphan tool_results, dedups tool_call_ids. Called at
   `_drive` entry (covers fresh = no-op, resume, fork) so a crash-recovered / forked / hand-built history is
   always a valid provider payload — converts a cryptic resume-400 into a recoverable state.
5. **Per-tool timeout** — `Tool.timeout_seconds: float|None=None`; `dispatch` wraps the awaitable in
   `asyncio.wait_for`, returns `{ok:false, error:'timed out'}` on expiry. Byte-identical when unset. A hung
   async tool no longer eats the whole wall-clock budget. (Sync tool bodies can't be interrupted — documented.)

## Slate C — eval moat
6. **`TrajectoryCheck(name, expected, match)`** (`evals/suite.py`) — `match ∈ {exact, in_order, any_order}`
   over `span.tool_calls()`; same `.score()` shape as `Assertion`/`TraceCheck` (`kind='trace'`), drops into
   `Eval.unit(trace_checks=[...])`. The most common process-eval pattern, currently hand-rolled lambdas.
7. **`LLMJudge(examples=...)`** (`evals/judge.py`) — `examples: list[(output, passed, rationale)]`; when
   non-empty, a few-shot block is prepended to the judge prompt. Empty (default) = byte-identical. Closes the
   existing `calibrate()→disagreements→rubric` dead-end (feed disagreements back as examples).

## Doc-truth pass (make the docs match the leaner reality)
Correct README + PRD where they overclaim vs source (verified):
- `StopReason`: list the real values (now `END_TURN/DONE/MAX_STEPS/PAUSED/ERROR/STUCK`); drop the unbuilt
  `budget_exhausted/cancelled/tool_rule_stop/max_tokens` claims (no triggers exist).
- Grace call: document as **opt-in** (`max_steps_policy='generate'`), not default behavior.
- Tools: real fields are `privileged` + (new) `idempotent`/`max_attempts`/`timeout_seconds`; drop the
  `read_only/destructive` hint claim. Errors are strings in the `{ok,data,error}` envelope — there is no
  `ToolError` class; correct that.
- Input-repair: it is the `jsonish` 4-stage waterfall (strict/fenced/first-balanced/light_fix) — drop the
  `ast.literal_eval/json5/repair_json` + `SequenceMatcher` fuzzy-name + repeated-call-short-circuit claims.
- Hooks: real slots are `pre_model/post_model/pre_tool/post_tool/on_stop` (+ `ask`, `should_continue`) — drop
  `on_error/on_idle`.
- `ContextBundle`: 3 fields (`instructions/history/tools`) — drop the `memory/retrieved/budget` field claim.
- Stream events: real `EventType` set has no `status`.

## Refused this pass (named, per GAP_REPORT §3/§5)
Provider-native JSON-schema fast-path (L-shaped, waterfall already covers correctness); the context-compaction
trio (`on_context_pressure`/head+tail/model-view split — defer to one consolidated pass when an agent runs long
enough to need it); deployment-tier stream reliability (SSE keepalive / chunk-stall / prod monitor — until a
stream endpoint is actually deployed); the tool-ergonomics batch (`examples`/`instructions`/docstring-args/
`mark_external_content` — polish, batch later); all GAP_REPORT §2-tail backlog. `prepare_step` + in-loop reask
+ `truncated`-recovery were offered as the "cost & correctness extras" option but not selected for this slate.
