# Verso — Meta-Scope Adversarial Review: Is v1 Over-Built?

**Question asked:** The design now specifies BUILDING a durable-execution engine, a memory engine
(pgvector + tsvector + `memory_links` graph + bi-temporal + 4-arm retrieval), an eval/trace engine,
a jsonish/SAP parser, an in-house model-routing layer, a deferred-tool-loader, code sandboxes, and
multi-agent orchestration. The builder is **solo and dogfood-first**; the verified thesis is *"keep
it simple, ship, find the abstraction by using it."* **Is this over-built for a v1 one person can
ship and run?**

**Answer, in one sentence:** **Yes — substantially. Not because the architecture is wrong (it is
mostly right and the RE evidence is sound), but because the design builds the final form of eight
subsystems *on paper* before a single agent has run, which is the exact anti-pattern the PRD's own
load-bearing thesis names ("the right abstraction cursor cannot be found on paper — only by using
the thing").** The fix is almost never REJECT; it is **lock the schema/interface, defer the engine
behind a `pip install` proxy, build the owned version only when dogfood proves the gap.**

**Date:** 2026-06-05
**Inputs:** `docs/PRD_v1.md`, `research/THESIS_VERIFICATION.md`, `research/06_design_resolutions/_RESOLUTIONS.md`
+ the 12 subsystem notes, and the 21 adversarial critic files already in this folder (`07_adversarial/critic-*.md`).
**Label key:** KEEP (Phase-0/1 core), LOCK (define the type/schema now, don't build the engine),
DEFER (build later, named phase), CUT (don't build for v1 at all).

---

## 0. The single finding that organizes everything

Across **seven** independent thesis-scope critics (durable-engine, memory-engine, eval-trace-engine,
jsonish-parser, model-layer, deferred-tools, colocated-postgres) the verdict is **identical and
unanimous: REVISE, never REJECT.** Each critic, working alone, arrived at the *same shape* of
finding:

1. The **destination architecture is correct** and the RE evidence is genuine (file:line cites
   check out; no misread sources).
2. The **schema / interface / type layer is durable** and should be locked now — it is cheap
   (~80–250 lines of dataclasses) and expensive to change later.
3. The **engine implementation is the over-build** — it is 2–3 months of solo work per subsystem,
   it is specified before any dogfood evidence exists, and **every one has a named, pip-installable
   substitute** that satisfies the Phase-0/1 dogfood goal at a fraction of the cost.
4. Each subsystem's *own* "Open Unknowns" list (7 for durable, 8 for model-routing, etc.) is the
   tell: **you cannot have a "resolved" design with 7 unresolved correctness questions.** Those
   unknowns prove the design was finished before the evidence was available, and they will force the
   schema to change *during* the first real build — i.e. the migration tax the thesis warns about.

When seven adversaries who were not coordinating land on the same verdict, that verdict is the
finding. **The convergence is the signal, exactly as `_RESOLUTIONS.md §0` argues for the converged
Postgres story — except here the convergence is "you over-scoped Phase 0."**

This is also the second time this exact pattern has been caught: `CLAUDE.md` records the NIA teardown
ballooning to 43,627 lines (90% padding) before being rewritten to 2,500 lines of load-bearing
content. **The design docs are repeating that failure mode at the architecture layer** — 8,658 lines
of subsystem resolutions + 444 lines of consolidation, specifying engines for code that has never
run. Density of *shippable* decisions per line is low; density of *paper* decisions is high.

---

## 1. The honest size of what's specified vs. what one person can ship

The resolved module map (`_RESOLUTIONS.md §2.1`) is **~50 named modules across 11 packages**, with
backends, schemas, and constants for each. Concrete inventory of what the design says to BUILD:

| Subsystem | What's specified to build | Honest solo build cost | Dogfood evidence it exists yet? |
|---|---|---|---|
| Durable engine | 5-table Postgres schema, 11-method `CheckpointBackend` ABC, SHA-1 step ids, lease/heartbeat worker loop, Resonate promise HITL, 3 durability modes, AX two-log | 2–3 months; 7 open unknowns | **None** — Phase 2 feature, no agent run |
| Memory engine | 7-table Hindsight schema, 8-phase LLM extraction pipeline, 4-arm retrieval (semantic+BM25+graph+temporal), RRF+DBSF+composite+CE rerank, bi-temporal, 7-variant EpistemicClass, consolidation daemon, 4 backends | 2–3 months | **None** — Phase 1, no agent has produced a memory |
| Eval/trace engine | VersoSpan/VersoScore schema, SQLite + ClickHouse stores, EvalQueue (asyncio+Redis), EvalWorker, 9 scorer impls, JudgePanel, G-Eval logprob, EvalRun/DatasetRunItem snapshot | 2–3 months | **None** — no traces to score |
| Model layer | ProviderProfile+OMIT, PeakEWMA+P2C balancer, 2-axis failover, BudgetGuard+Redis, 3 learned routers (RoRF/Cascade/KNN), should_reason gate, cache-sticky routing — 9 modules | ~1 month for the 5 needed pieces; the rest can't run | **Partial** — 5 of 10 decisions provably can't be exercised on the Phase-0 provider |
| jsonish/SAP parser | 5-stage waterfall, typed-Flag coercion, provider mode map, reask loop, streaming Partial[T] | ~3 weeks for the novel 2; the other 3 duplicate Instructor | Waterfall is novel; mode-map/reask/partial are reinventions |
| Deferred tool loader | 5 meta-tools, BM25+ ranker (`bm25s`+`PyStemmer`), 20-tool threshold | ~2 weeks | **None** — solves a 300-tool problem; solo builder has 5–15 tools |
| Code sandboxes | `CodeSandbox` protocol, microsandbox/E2B/Daytona, credential proxy, deny-all egress | ~1 month | **None** — PRD says Phase 3 already |
| Multi-agent | subagent_delegate, fan_out, Orchestration, handoff, graph escape hatch, depth-cap | ~3 weeks | **None** — PRD says Phase 3 already; evidence on *whether it helps* is openly conflicting |

**Total designed-to-build surface: well over a year of solo engineering**, of which the PRD's own
Phase-0 exit criterion ("build a real personal agent on it") requires **maybe 6–8 weeks.** That gap
is the over-build.

---

## 2. THE RANKED CUT/DEFER LIST — "cut this first"

Ordered by *how confidently it should leave Phase-0/1*, most-cuttable first. Each entry: the cut,
**what it saves**, **what it risks**, and the cheaper substitute.

### CUT #1 — Learned model routers (RoRF / ConfidenceCascade / KNN) + per-step reasoning gate
**Action: CUT from v1 entirely (not just defer).** Lock a 3-line `LearnedRouter` Protocol; build nothing.
- **Saves:** ~3–4 weeks; a 1GB+ Jina-v3 model download (`trust_remote_code=True`), sklearn/pickle,
  and the `routers/` sub-package (3 dead files).
- **Risks:** ~zero. These **cannot run in v1 by construction**: RoRF needs a 200–500-task calibration
  corpus that does not exist; ConfidenceCascade needs logprobs that **Anthropic — the Phase-0 default
  provider — does not expose**; KNN needs an eval corpus. The model-layer critic verified all three.
- **Substitute:** none needed. The PRD §2 *explicitly disowns this*: "Not a model router / planner
  cult … routers are tactical scaffolding the harvest flags as depreciating." **Shipping learned
  routing in Phase 0 directly contradicts a locked non-goal.**

### CUT #2 — Deferred tool-loader (5 meta-tools + BM25+ ranker + `bm25s`/`PyStemmer`)
**Action: CUT from Phase 0/1; it is already Phase 3 in the PRD.** Keep the design as a Phase-3 appendix.
- **Saves:** ~2 weeks; the `bm25s` dependency (pulls `numba`, can add 1–2 GB to install) and `PyStemmer`.
- **Risks:** ~zero. The problem (>20 tools/source flooding context) **does not exist for a solo
  builder writing 5–15 native `@tool`s for their own agent.** The 77K→8.7K token figure describes a
  300-tool production MCP catalog — not the dogfood case.
- **Substitute:** native `@tool` only in Phase 0. When MCP lands in Phase 3 and a real >20-tool
  source appears, *measure* the context pressure, then wrap Strata or vendor its ~80-line BM25 module.

### CUT #3 — Code sandboxes (microsandbox / E2B / Daytona / credential proxy)
**Action: CUT from v1 build; PRD already says Phase 3.** Keep `CodeSandbox` as a 1-method protocol stub.
- **Saves:** ~1 month; the libkrun/microVM integration, the `verso-daemon` build, the smoltcp
  `verso.internal` domain-rule work (itself an open unknown), egress-proxy plumbing.
- **Risks:** low. Code execution is the *escape hatch*, not the primitive. A solo dogfood agent that
  needs to run code can shell out to a subprocess with a `--trust-local` flag in Phase 0/1.
- **Substitute:** local subprocess behind the protocol; adopt a real sandbox only when an untrusted-
  code workload actually exists.

### CUT #4 — Multi-agent orchestration (Orchestration / handoff / graph escape hatch)
**Action: CUT from v1 build; PRD already says Phase 3.** Keep `SubagentResult` and `subagent_delegate`
as the *only* multi-agent surface, and even that is borderline.
- **Saves:** ~3 weeks; the `Orchestration` shared-state store, `handoff` router union, the
  `Send`/`Command` graph module, depth-cap enforcement machinery.
- **Risks:** low-to-moderate. The PRD itself says single-agent is the default and orchestration is a
  separate opt-in import. The evidence on whether hierarchy *helps* is **openly conflicting**
  (Anthropic +90.2% vs Agent-S3 +13% from *removing* it) — `_RESOLUTIONS.md` D4 admits this and says
  "instrument before recommending." **You cannot instrument what you haven't dogfooded; therefore you
  cannot responsibly build the recommended shape yet.**
- **Substitute:** `asyncio.gather` over sub-agents (which a clean loop already enables) covers fan-out
  for dogfood. Build the typed orchestration only after evals exist to settle the topology question.

### CUT #5 — Eval/trace ENGINE (store + queue + 9 scorers + JudgePanel), keep the SCHEMA
**Action: LOCK the schema (VersoSpan 10-kind, VersoScore 5-element, `dotted_order`, source enum,
all named constants — ~80–100 lines). DEFER the engine to Phase 2.**
- **Saves:** ~2–3 months; SQLite DDL + ClickHouse schema (ReplacingMergeTree, sumMap, bloom filters),
  EvalQueue, EvalWorker, EvalRun/DatasetRunItem/ScoreSummary snapshot model, 9 reimplemented scorers.
- **Risks:** moderate but bounded. The genuinely Verso-specific wins (the `correction` HITL→dataset
  flywheel, `source_span_id` recursive observability, `p50/p80_horizon` metrics, `verify_grounding`
  at the loop level) are deferred — **but those are exactly what dogfood should sharpen first, so
  deferring them is correct, not lossy.**
- **Substitute:** emit OTel spans with `gen_ai.*` attributes (~50 lines); `pip install langfuse`
  (self-hosted free tier) as the Phase-0/1 trace store + online eval scheduler — it already runs the
  `evalService.ts` engine the design RE'd; `pip install autoevals` for scorers (the FACTUALITY_CHOICE_SCORES
  / EMBEDDING_SIM_FLOOR constants the design extracted *are* the autoevals constants); `braintrust.Eval()`
  for offline CI. **The proxy phase IS the use that finds the abstraction.**

### CUT #6 — Memory ENGINE (Hindsight extraction + graph arm + 4-arm retrieval + consolidation),
keep the SCHEMA + interface + a dead-simple backend
**Action: LOCK `MemoryItem`/`MemoryType`(4)/`EpistemicClass`(as types only)/`MemoryScope`/`MemoryBackend`
interface + the DDL. SHIP a ~100-line `SqliteVecBackend` (semantic-only, no graph, no BM25, no
consolidation). DEFER the engine to Phase 3.**
- **Saves:** ~2–3 months; the 8-phase LLM extraction pipeline, `memory_links` adjacency (kNN write
  on every insert), pgroonga/tsvector BM25, bi-temporal invalidation, the surprisal-gated dream
  daemon, and 3 of 4 backends.
- **Risks:** moderate. You lose graph recall and audit-grade `recall_as_of` in Phase 0/1 — but the
  memory critic verified Hindsight's 91.4% LongMemEval comes from a **large backbone model, not the
  graph arm**, and the builder does not yet know if their agent even *exercises* graph recall.
  `recall_as_of` is Phase 3 by the PRD's own definition (finance/health, not dogfood).
- **Substitute:** `pip install mem0ai` behind a ~40–80-line `Mem0Backend(MemoryBackend)` adapter.
  Mem0's V3 pipeline *is* the ADD-only write policy + integer-index anti-hallucination map the design
  copies; the composite re-rank (8 lines) runs client-side on Mem0's hits. Public API
  (`remember`/`recall`/`recall_as_of`) is identical from the agent's view — this is literally what the
  `‹edge2›` seam is for, and the PRD §5.4 already names "Mem0/Zep adapters."

### CUT #7 — Durable ENGINE (5 tables, 11-method ABC, lease worker, promise HITL, step-memoization),
keep the SEAM + a minimal `CheckpointBackend` interface
**Action: LOCK Decision A — the seam is one `PersisterHook`/`RunContext`-polymorphism; loop source
identical. DEFER Decision B — the bespoke engine — to Phase 2 entry, starting from a `pip install`.**
- **Saves:** the largest single line item: 2–3 months and the densest resolution doc (801 lines,
  **7 open correctness unknowns** including exactly-once for external-DB tools, journal compaction,
  `internal_only` semantics — all of which will mutate the schema once a real agent runs).
- **Risks:** moderate, and this is the one to think hardest about because **the seam IS Verso's
  primitive.** What you lose with a composed backend: mid-step memoization (vs whole-action re-run),
  background `submit()` queue, mid-step `ctx.hitl.request()`. The seam-mechanism critic confirms these
  gaps are **real but not bottlenecks before a single Phase-2 agent exists.**
- **Substitute (two valid options, decide at Phase 2 from dogfood):**
  - `pip install dbos` — pure Python + Postgres, `@DBOS.workflow()`/`@DBOS.step()`, startup recovery
    thread, `fork_workflow`, `recv/send` HITL. Its 2-table schema (`workflow_status`+`operation_outputs`)
    **is the schema Verso copied and renamed.** Step-memoization is built-in (closer to Verso's target
    than Burr).
  - `pip install 'apache-burr[asyncpg]'` — `PersisterHook` + `AsyncPostgreSQLPersister` (425 lines,
    production-tested); `halt_before`/`halt_after` action-boundary HITL. Coarser (whole-state-per-step,
    no mid-step memoization) but the seam test passes today.
  - **Recommendation:** DBOS is the better proxy because its memoization model matches the eventual
    target, so swapping the owned engine behind `CheckpointBackend` later is a localized change.

### DEFER #8 (lower confidence) — jsonish over-build: keep the novel parser, compose the rest
**Action: KEEP the jsonish 5-stage waterfall + typed-Flag coercion (genuinely unbuildable from any
library). COMPOSE the provider-mode-map, reask loop, and streaming `Partial[T]` from Instructor.**
- **Saves:** ~30% of the structured-output scope (~200 lines of duplicated tenacity glue + a
  hand-maintained `PROVIDER_STRUCTURED_OUTPUT_CAPS` table a solo builder should not own).
- **Risks:** low. The hard constraint: Instructor hard-deps `openai>=2.0.0`, so naive `import
  instructor` is out for a provider-agnostic framework. The jsonish-parser critic verified a clean
  path: lift the 4–5 relevant modules (`core/retry.py`, `processing/function_calls.py`, `mode.py`,
  `dsl/partial.py`, `dsl/json_tracker.py`) stripped of the openai import — a 1–2 day fork, not a
  rebuild. Also correct the benchmark framing: the 19.8% FC number is *deprecated* function-calling,
  not modern forced-TOOLS mode; SAP's real win is on prose-with-embedded-JSON and stream truncation.
- **Note:** this is the *only* subsystem where part of the engine is genuinely non-composable and
  must be built in v1. Keep the waterfall; trim the reinventions.

---

## 3. The TRUE minimal core (what actually ships in v1)

Two tests define "minimal": **(a) it proves the tactical↔durable seam**, and **(b) it lets the user
build their own AI products on Verso.** Everything that does not serve one of those two is cut or
deferred above. What remains:

### Phase 0 — the dogfoodable tactical core (the actual product)
Build these, full quality, because they ARE the wedge and the seam can't be proven without them:

1. **`core/loop.py`** — the `<200`-line async ReAct loop with the named `StopReason` enum,
   `max_steps=25` + token-budget + the single grace message, the doom-loop `ToolInspector` (soft=3/
   hard=5), and `AgentResult`. **This is the thing the whole repo exists to keep small — build it
   first and keep it honest.**
2. **`context/`** — `RunContext[T]`, `ContextBundle`, KV-cache discipline (stable prefix / append-only
   / deterministic JSON), the hard budget ceiling, the `prune()` observation-masking pass, and
   `agent.inspect()`. **This is the deep differentiator; it must be real, not a stub.** (Defer the
   LLM `compact()` summary to "when prune isn't enough" — it needs the aux-model dogfood call anyway.)
3. **`tools/`** — `@tool` → `TypeAdapter(fn)` schema (the one schema-gen path), `{data,error,ok}`
   dispatch that never raises into the loop, the `ToolError` envelope, the input-repair ladder, the
   jsonish waterfall (the one non-composable parser piece), `think`/`done`. **Native only — no MCP,
   no deferred loader, no openapi.**
4. **`model/`** — the *thin* layer only: `ProviderProfile`+`OMIT`, Anthropic + OpenAI (+ Google)
   profiles, **basic** two-axis error-typed failover, `require_parameters` enforced at init,
   `call_with_retry` (6/4s/240s), force `include_usage`, `AttemptRecord`. **~4 files, ~250 lines.**
   No balancer, no budget-Redis, no learned routers, no reasoning gate.
5. **`stream/`** — one 7-type true-delta `StreamEvent`, the stream normalizer, SSE transport.
   (Resumable `attach(starting_after=N)` cursor replay is a *durable* concern → Phase 2.)

**Phase 0 exit:** build a real personal agent on it. ~6–8 weeks solo.

### Phase 1 — memory + the eval wedge, **as interfaces over proxies**
1. **`memory/`** — LOCK the types + `MemoryBackend` interface + DDL. SHIP `SqliteVecBackend`
   (semantic-only, ~100 lines) + a `Mem0Backend` adapter (~40–80 lines). `remember`/`recall` work.
2. **`evals/`** — LOCK `VersoSpan`/`VersoScore` + constants (~80–100 lines). Emit `gen_ai.*` OTel.
   Use Langfuse + autoevals + `braintrust.Eval()` as the engine. Ship `define_outcome` (the bounded
   generate→grade→revise loop — that one is small and Verso-specific).
3. **`safety/hooks.py`** — the 5-stage lifecycle hooks (this is the extensibility mechanism the rest
   of the framework hangs off; build it, it's small).

**Phase 1 exit:** an eval suite (running through the proxy) drives an iteration on the Phase-0 agent.

### Phase 2 — the seam, proven (the moment of truth for the primitive)
1. **`runtime/`** — LOCK the seam (`PersisterHook`/`RunContext` polymorphism). Back it with **DBOS**
   (preferred) behind a minimal `CheckpointBackend`. Prove the success criterion: *the identical
   agent runs tactically and durably with one flag and zero loop-code changes.* Build the bespoke
   engine **only** if DBOS's friction is real and named.
2. **`safety/permissions.py` + `confidence.py`** + `max_budget_usd` (simple counter, no Redis).
3. Resumable streaming `attach()` (now that there's a durable log to attach to).

**Phase 2 exit:** the same agent runs a long, crash-resumable, HITL-gated task via `durable=True`.

### Phase 3+ — opt-in scale (build only what dogfood demanded)
The owned durable engine (if DBOS friction proved it), the owned memory engine (if Mem0 gaps proved
it), the owned eval store (if Langfuse gaps proved it), MCP + deferred loader, pgvector + graph arm,
multi-agent, sandboxes. **Each gated on a proven gap, not a paper design.**

---

## 4. Why this minimal core still satisfies both of the user's stated goals

**Goal (a): prove the tactical↔durable seam.** The seam is proven by Phase 0 (clean loop +
`RunContext` + event model) plus Phase 2's one-flag test. **It does not require the bespoke engine** —
it requires the *interface* and *any* backend behind it. DBOS-behind-the-seam proves the primitive as
well as a hand-built engine would, and proves it months sooner. **Building the engine first actually
delays the proof of the primitive** — which is the inversion the thesis exists to prevent.

**Goal (b): let the user build their own AI products on Verso.** A user builds products on: a clean
loop, real context engineering + `inspect()`, native typed tools, multi-provider failover, streaming,
working memory, and a way to eval. **All of that is in Phase 0/1 above.** The owned engines
(durable/memory/eval) are *infrastructure the user doesn't touch the internals of* — so swapping
DBOS/Mem0/Langfuse for an in-house version later is invisible to the products built on top. The user
can build today; the substitutions happen underneath them.

---

## 5. The one CORRECTNESS landmine to fix regardless of scope (not a cut — a bug)

Independent of the over-build, the seam-mechanism **correctness** critic found a real contradiction
the scope decision must not paper over:

- `api-and-peers.md` D1 claims the loop body is **"byte-identical, never branches on `durable`"**
  and cites Burr `application.py:2565`.
- `durable-runtime.md` D9 says the LLM call is **"ALWAYS wrapped in `ctx.step(...)`"** so a crash
  mid-inference doesn't re-call the model.
- **These contradict each other.** Burr checkpoints at the *action* boundary (hook fired by infra,
  outside the body). Verso checkpoints at *sub-iteration* granularity (`ctx.step()` invoked *inside*
  the body). The loop is identical in *source text* but not in the Burr sense; the correct citations
  are DBOS `_core.py` / Centaur `workflow_engine.py:338-435`, not Burr.
- **Consequence to lock now:** the `async with ctx.step()` block must contain **only** the single
  call + result assignment. Any side effect inside the block runs in tactical mode but is **skipped on
  durable resume** — a silent divergence between the two runtimes, which would falsify the seam's
  central promise. Enforce this as a documented contract (and ideally a runtime guard) on day one,
  because the seam is the product. Choosing DBOS as the Phase-2 proxy (CUT #7) helps here: DBOS's
  `@DBOS.step()` already encodes this single-call contract.

---

## 6. The bottom line

The design is **architecturally excellent and scope-inverted.** It did the hard RE correctly and then
made the one mistake the thesis it's built on exists to prevent: it resolved on paper what can only be
resolved by use, and called a design with 30+ unresolved correctness unknowns "finished."

**Cut order, compressed:** learned routers → deferred tool-loader → sandboxes → multi-agent →
eval-engine → memory-engine → durable-engine; trim (not cut) jsonish. Lock every schema/interface
those critics flagged as durable; build every engine behind a `pip install` proxy (DBOS, Mem0,
Langfuse/autoevals, Instructor-lift); replace each proxy only when a *named, dogfooded* gap demands
it.

**The minimal v1 that proves the seam and lets the user build products is ~6–8 weeks (Phase 0) +
~3–4 weeks (Phase 1, interfaces-over-proxies) + the one-flag seam test (Phase 2 over DBOS) — not the
year-plus of engine-building currently specified.** Ship that. Find the abstraction by using it. Then
build the engines the dogfood actually asks for.

---

*Sources: the 7 thesis-scope + correctness critics in this folder are unanimous (all REVISE). This
meta-scope ranks and consolidates their findings against the PRD's own Phase-0/1 exit criteria and the
verified "find the abstraction by using it" thesis. Authority: this file consolidates `07_adversarial/`;
the per-subsystem critics remain the deep evidence trail with file:line cites.*
