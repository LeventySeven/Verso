# Verso — Next plan slate (merged from the recheck + the bad-guide/twitter mine)

> Synthesized from two workflows: **(1)** recheck-everything + teardown/core mine (53 agents) and **(2)** deep-mine of BAD_GUIDE's research-taste/CTO/CPO/AI sections + ALL 47 twitter/X articles (Anthropic-heavy) + 148 curated AI essays (68 agents). Plan 21 already shipped the confirmed bug-fixes (ranks 1–5 of WF1, incl. 2 security holes). What remains is **net-new, on-thesis, not-yet-shipped** work. Both workflows converged hard on **eval craft** — the corpus's loudest, most Verso-aligned signal ("reliability is a distribution"; "the accreting corpus of run-traces IS the moat").

> **STATUS: SHIPPED 2026-06-14.** Plan 21 (recheck fixes, incl. 2 security holes) + the full slate below (Clusters A–E) are built, each batch implementer→recheck(APPROVED)→gated-commit→pushed. `uv run pytest -q` → **366 passed, 1 skipped**; ruff clean. The "deliberately dropped" list was honored (nothing from it built). Remaining open items: backend Protocol `recent(now=)` doc-parity (done); TraceCheck/Assertion name-collision (documented, user-controlled).

## Principles that should steer Verso (distilled from the corpus)
- **AI research taste:** the harness compounds, models rotate — invest in the loop/evals/tooling, never the weights. The corpus of real run-traces is the moat. Build meta-methods, not hardcoded discoveries. Simplest impl is cheapest to discard when the model improves (no-overkill is itself a research bet).
- **Reliability & eval craft (the Anthropic throughline):** reliability is a *distribution* (pass^k + per-step rate, against a token/cost/step budget), not a scalar. Verifier's Rule: build the checker before the loop. A miscalibrated judge is worse than none — score it precision/recall vs humans. Process > outcome: score the trace, not just the final answer. Incident → regression in one line.
- **Harness design:** protect the ~150-line loop from accretion; complexity lives in tools + context, not scaffolding. Don't force the graph (needs a *demo-able artifact*). Re-anchor the objective on every tool return. Context is a finite attention budget. Silent failure is the defining hazard — legible traces are the defense.
- **CTO craft:** additive/byte-identical-when-off; behavioral-equivalence diff before migrating; back-compat non-negotiable (checkpoints provider-agnostic); a wrong API name is a UI bug; mirrors must match the audited core.
- **CPO taste:** scope reduction *is* quality; wrap-don't-invent (map to concepts users know); opinionated defaults are a moat; HITL is a first-class design primitive (surface a bounded decision, not a context dump).
- **Simplicity/anti-bullshit:** complexity budget scales with *measured* gain; every feature earns its keep or is removed with no penalty; fewer principled primitives beat a pile of knobs.

---

## The slate (ranked, themed; recommended = build-next candidates)

### ⭐ Cluster A — Eval craft (the convergent #1; Verso's moat) — *recommend building this cluster next*
- **A1 · Process-level evals** *(M)* — `VersoSpan` drops the agent's decisions: `TOOL_START` already carries `arguments` on the event stream but `capture()` ignores it, so every Assertion/judge sees only `span.output`. Add `args` to `SpanRecord` + `tool_calls()` accessor + `Eval.unit(trace_checks=[…])` + `LLMJudge(trace_mode=True)` (uses `span.render()`). Lets you assert on the *path* (right answer via a wrong/risky tool route now scores differently) and makes `from_trace` regressions process-aware. Additive; byte-identical when unused. *(WF2 r1)*
- **A2 · `LLMJudge.calibrate(labeled)`** *(S)* — return precision/recall/F1/agreement + the disagreement list against human labels. The judge's own docstring demands this; Plan 21 fenced it, this trusts-but-verifies it. *(WF2 r2)*
- **A3 · Budget-aware reliability** *(M)* — `Eval.pass_k(budgets=[…])` → `{budget: pass_rate}` (abort each trial via a `should_continue` on `ctx.usage`); add `Eval.best_of_n(...)`. Turns "reliability is a distribution" into a measured axis; both compose shipped primitives. *(WF2 r3)*
- **A4 · `UnitReport.worst(n)` + `divergent()`** *(S)* — read the lowest-scoring traces first; surface JudgePanel disagreement (add `divergence` std-dev field to VersoScore) instead of averaging it away. Read-only accessors over captured data. *(WF2 r6)*

### Cluster B — Harness reliability (small, hot-path-adjacent, on-thesis)
- **B1 · `reinforce_objective(summary, every=)`** *(S)* — a named `post_tool` factory that re-anchors the goal on every tool return (the most-cited reliability lever; the seam already exists, this just blesses a default). *(WF2 r4)*
- **B2 · `tool_output_budget`** *(S)* — opt-in middle-truncation (`first-half + …[truncated N]… + last-half`) of oversized tool results in `_format_result`; default None = today. Treats context as the finite resource it is. *(WF2 r5)*

### Cluster C — Correctness follow-ups from the recheck (real bugs, deferred from Plan 21)
- **C1 · Memory tier-aware eviction + recent()/reflect() TTL** *(M)* — `_enforce_bound` evicts by age across ALL types, so a *permanent* FACT is deleted for newer ephemeral scratchpads (data-loss vs the documented 4-tier contract); `recent()` ignores TTL so `reflect()` consolidates expired episodics. Fix both backends identically. *(WF1 r6 — genuine correctness)*
- **C2 · Retry-After + instant failover** *(S)* — `call_with_retry` ignores the `Retry-After` header providers send on 429s (sleeps wrong); `FailoverModel` only advances after exhausting all backoff on the current candidate. Honor the header; add `instant_failover`. Inside the existing RetryPolicy/FailoverModel seam. *(WF1 r7)*

### Cluster D — Durable invariant + proof artifacts
- **D1 · Provider-agnostic checkpoint test** *(M)* — the durable seam promises cross-provider resume, but nothing tests that `msg_to_dict` blobs are provider-neutral. Add a `version` field + a checkpoint-under-model-A → resume-under-model-B test (the model-agnostic guarantee as CI). *(WF2 r8)*
- **D2 · No-graph orchestrator-workers worked example** *(S)* — `examples/orchestrator_workers.py` (~30 lines, public API, `asyncio.gather`) + `examples/minimal_agent.py` (<80 lines) — make the "we don't force the graph" bet *falsifiable* with a forkable artifact, referenced from README. Zero library code. *(WF2 r7)*
- **D3 · Context contracts: doc soft-cap + lossy-prune; guard `prune(keep_last_n=0)`** *(S)* — fix the `[:-0]` off-by-one (keep-0 must mask all), document `max_context_tokens` as a soft trigger + that in-loop prune is lossy-on-checkpoint, lock with tests. Mostly honesty. *(WF1 r8)*

### Cluster E — HITL product quality (nice-to-have)
- **E1 · `HumanRequest.human_prompt`** *(S)* — an optional reviewer-facing message distinct from the internal `prompt`; a pause should surface a bounded decision, not implementation detail. One additive field. *(WF2 r9)*
- **E2 · stream Retry-budget parity** *(S)* — thread `max_tool_retries` into the stream path (Plan 21 FIX-1 left stream Retry bounded by `max_steps`, not the per-tool budget). *(recheck Minor)*

---

## Deliberately dropped (both workflows agreed — Verso's bet is refusing these)
Native MCP adapter *(own plan if ever)* · parallel tool dispatch · LLM-driven context compaction/summarization · orchestrator/workers/fan-out **as primitives** (recipes, not core) · guardian/classifier permission model (`confidence_router` covers it) · deferred tool-schema loading (no 50-tool registry) · model capability registry · async submit/poll & sleep-time compute · weighted/tagged failover · `FusionModel` ensemble · `LethalTriadPolicy`/per-tool risk_tags (cross-cutting tax) · judge-scramble detection · `Eval.preregister` · `PermissionPolicy.auto()` (dup of allow_all) · per-tool TTL · Reflexion/self-critique policy (ships the anti-pattern) · METR time-horizon annotation · `error_budget` StopReason (hot-path) · `Agent.spec`/anti-sycophancy default · cache-token tracking + Anthropic thinking round-trip *(small standalone observability, not now)*. **All off-thesis, composable from existing seams, or speculative-without-signal.**

## Recommendation
Build **Cluster A (eval craft)** next — it is the convergent #1 across both mines, the most on-thesis (evals are Verso's moat), and largely additive composition over shipped primitives. Fold in **B1+B2** (tiny, high-leverage) and **C1** (a real data-loss bug). Hold C2/D/E for a following pass.
