# Verso — Adjudicator's Verdict

**Role:** Final adjudication of the adversarial panel. The panel's job was to BREAK the 9 locked
decisions in `06_design_resolutions/_RESOLUTIONS.md`; this file keeps what survived and cuts/revises
what didn't — decisively, evidence-bound.
**Date:** 2026-06-05
**Inputs adjudicated:** 27 per-decision critic files (9 decisions × 3 lenses: correctness /
scale-failure / thesis-scope), `_META_SCOPE.md`, `_STEELMAN.md`, `06_design_resolutions/_RESOLUTIONS.md`,
`THESIS_VERIFICATION.md`, `docs/PRD_v1.md`.
**Authority:** This file supersedes `_RESOLUTIONS.md §3` where it explicitly says so (§3 below). The
per-subsystem critics remain the deep evidence trail with file:line cites.

---

## 0. How this was weighed

**The panel converged.** Across 27 independent critiques there is exactly one verdict shape:
**REVISE, never REJECT.** Not one critic found the destination architecture wrong, and not one found
a misread source — every critic that made a load-bearing claim **re-cloned the repo and verified the
file:line** (`apache/burr`, `dbos-transact-py`, `inngest-py`, `google/ax`, `paradigmxyz/centaur`,
`Helicone/ai-gateway`, `tower`, `Not-Diamond/RoRF`, `vllm-project/semantic-router`, `mem0ai/mem0`,
`plastic-labs/honcho`, `vectorize-io/hindsight`, `memodb-io/memobase`, `langfuse`, `openinference`,
`autoevals`, `deepeval`, `langsmith-sdk`, `opik`, BAML, `instructor`, `open-strata`, microsandbox).
That is the strongest possible evidentiary footing, and it is why the verdicts below are high-confidence.

**Weighting rule applied:** critics that cited a verified `file:line` or a live clone outrank
hand-wavy scope assertions. Every finding promoted to a REVISE/REJECT/DEFER below is backed by a
source-verified citation, not by a "feels over-built" argument. The `_META_SCOPE` ranking and the
`_STEELMAN` compose-verdicts are used as the **integration frame** (they correctly diagnose the one
systemic error — *resolving on paper what the thesis says can only be resolved by use*) but the
*specific* keep/cut calls are driven by the per-decision source evidence, not by the meta-narrative.

**The one systemic finding** (unanimous across the 7 thesis-scope critics + both meta-docs): the
design is **architecturally excellent and scope-inverted.** It did the RE correctly, then committed
the complete final form of eight engines to Phase 0 — each carrying 5–8 *admitted* Open Unknowns
inside a doc titled "RESOLVED." A resolved design cannot have 30+ unresolved correctness unknowns;
those unknowns are the proof the schema will mutate during the first real build (the migration tax
the thesis exists to prevent). The fix is mechanical and identical for almost every subsystem:
**LOCK the schema/interface/types now (cheap, ~80–250 lines, expensive to change later); DEFER the
engine behind a `pip install` proxy; build the owned engine only when a *named, dogfooded* gap
demands it.**

---

## 1. Per-decision verdict table

For each of the 9 decisions: the verdict, confidence, and the single strongest **surviving**
objection (the one that lands even after steelmanning the BUILD case).

| # | Decision | Verdict | Conf. | Strongest surviving objection (source-verified) |
|---|---|---|---|---|
| 1 | **Seam mechanism** (`durable=True` = one `PersisterHook`, loop byte-identical) | **SURVIVES** (architecture) — **REVISE** the citation + add a body-contract | **HIGH** | The "byte-identical loop, Burr `application.py:2565`" cite is a **misattribution**: Burr checkpoints at the *action* boundary (hook in `finally`, outside the body); Verso checkpoints at *sub-iteration* via `ctx.step()` *inside* the body. Correct cites are DBOS `_core.py` / Centaur `workflow_engine.py:338-435`. Consequence to lock: the `async with ctx.step()` block must contain ONLY the single call + result assignment — any side effect inside runs tactically but is SKIPPED on durable resume, silently falsifying the seam. (Verified vs cloned `apache/burr` HEAD.) |
| 2 | **Durable engine** (5-table schema, 11-method ABC, lease worker, promise HITL, step-memoization; reject Temporal) | **REVISE** → split: **LOCK** the seam + a minimal `CheckpointBackend` interface; **DEFER** the bespoke engine to **Phase 2**, starting from **DBOS** behind the interface | **HIGH** | The engine is a 2–3 month build with **7 admitted Open Unknowns** (exactly-once for external-DB tools, journal compaction, `internal_only` semantics…) that will each mutate the schema once a real agent runs. DBOS (`pip install dbos`) **IS** the chosen architecture — its `workflow_status`+`operation_outputs` is the schema Verso renamed; its `MAX_RECOVERY_ATTEMPTS=100`, `startup_recovery_thread`, `fork_workflow` are the constants Verso hard-codes. Building it before running one agent is the precise anti-pattern the thesis names. **Also a real bug:** flip the durability **default from ASYNC → SYNC** (ASYNC re-fires LLM calls on crash producing a *different* non-deterministic result → corrupted event log; 3 critics independently). |
| 3 | **Colocated Postgres** (one PG = checkpoints + memory + traces; one SQLite dev) | **SURVIVES** (architecture) — **REVISE** the framing + 3 scale fixes | **HIGH** | Architecture is sound and the RE is clean. But: (a) "one Postgres, zero new services" is **misleading** — pgroonga is a separate OS-level install; on stock PG the BM25 arm silently degrades to tsvector; (b) the merged 13-table migration is **prematurely bundled** — the only Phase-0/1/2 forcing-function for Postgres is the Phase-2 durable seam; memory + traces run on sqlite-vec + SQLite through Phase 1; (c) at scale: `seq = MAX(seq)+1` is a race (use a DB identity/SEQUENCE), and HNSW-insert WAL/LWLock contention starves the checkpoint write path (segregate connection pools). |
| 4 | **Model layer** (ProviderProfile+OMIT, P2C+PeakEWMA balancer, two-axis failover, budget guard, learned routers, reasoning gate) | **REVISE** → split: **LOCK+BUILD** the thin core for Phase 0; **DEFER** balancer/budget/reasoning-gate; **REJECT** learned routers for v1 | **HIGH** | The thin core (ProviderProfile+OMIT, error-typed two-axis failover, `require_parameters` at init, `call_with_retry`, force `include_usage`, `AttemptRecord`) SURVIVES — it is ~250 lines and correct. But **learned routers (RoRF/ConfidenceCascade/KNN) CANNOT run in v1 by construction**: ConfidenceCascade needs logprobs Anthropic (the default provider) **does not expose** → it degenerates to always-escalate; RoRF needs a 200–500-task calibration corpus that doesn't exist. Shipping them also **directly contradicts a locked PRD non-goal** ("Not a model router cult"). Plus correctness bugs: `threading.Lock`→`asyncio.Lock`, TTFB-not-wall-clock EWMA signal, TOCTOU budget race. (Verified vs cloned Helicone/RoRF/vLLM-SR + Tower source.) |
| 5 | **Memory engine** (Hindsight single-PG, 4-arm retrieval, graph arm, bi-temporal, consolidation daemon, 4 backends) | **REVISE** → **LOCK** types+interface+DDL; **SHIP** `SqliteVecBackend` + a `Mem0Backend` adapter for Phase 1; **DEFER** the engine to **Phase 3** | **HIGH** | The full Hindsight+Mem0+Graphiti+Honcho synthesis is the right *target* but a multi-quarter build mis-scheduled into Phase 1. Mem0's V3 pipeline **is** the ADD-only write policy + integer-index anti-hallucination map Verso copies; `pip install mem0ai` behind a ~40–80-line adapter gives identical `remember`/`recall` from the agent's view (the `‹edge2›` seam, already named in PRD §5.4). **Also a HIGH-severity correctness bug:** `remember()` calls `flush_buffer()` then `insert()` directly — it bypasses the extraction pipeline and stores raw turns (incoherent: implements neither Mem0-extract nor Memobase-buffer). Plus 2 mis-cites (Honcho daemon is actually Mem0 `proxy/main.py`; `vector(1024)` is Graphiti's, Hindsight's real default is 384). |
| 6 | **Eval/trace engine** (VersoSpan 10-kind + VersoScore + dotted_order, dual-emit OTel, one EvalJob engine, 9 scorers, JudgePanel) | **REVISE** → **LOCK+BUILD** the schema + OTel emit + `define_outcome`; **DEFER** store/queue/scorers to **Phase 2** behind Langfuse + autoevals + Braintrust | **HIGH** | Least-defensible BUILD in the set: the teardown itself proves the score shape is **universal** ("accepted by Langfuse/Phoenix/Opik/MLflow/LangSmith with field renames only, no per-backend adapter"), and OpenInference ships **~33 free auto-instrumentors** — building the store *forfeits* free tracing of every other composed library. The schema (VersoSpan/VersoScore/constants, ~80–100 lines) is durable and must be locked now; the store/queue/9-scorers are ~2–3 months of operational plumbing Langfuse + `autoevals` already run. Plus correctness fixes: cache-token attrs must be **dot not underscore** (`gen_ai.usage.cache_read.input_tokens`), and **drop RERANKER** kind (silently downgrades to SPAN in Langfuse; Verso has no first-class reranker primitive). |
| 7 | **jsonish/SAP parser** (5-stage waterfall + typed-Flag coercion + provider mode-map + reask loop + streaming Partial) | **REVISE** → **KEEP+BUILD** the waterfall + Flag coercion (non-composable); **COMPOSE** the reask loop + mode-map + Partial from Instructor | **MED-HIGH** | The 5-stage waterfall and typed-Flag cost function are genuinely unbuildable from any library — keep them. But the reask loop, the hand-maintained `PROVIDER_STRUCTURED_OUTPUT_CAPS` table, and streaming `Partial[T]` **duplicate Instructor** at production quality; lift the 4–5 relevant modules (strip the `openai>=2.0.0` hard-dep — a 1–2 day fork). **Correct the benchmark framing:** the 19.8% number is *deprecated function-calling*, not modern forced-TOOLS; SAP's real win is prose-with-embedded-JSON + stream truncation, not "beats forced tool-calls." **Highest-severity bug (FM2):** a reask on a non-idempotent tool freely regenerates the *whole* call (recipient/body can change) — add `allow_reask=False` default when `tool.idempotent==False`. (Verified vs cloned BAML + Instructor.) |
| 8 | **Deferred tool-loader** (5 meta-tools + BM25+ ranker, >20-tool threshold) | **DEFER** → Phase 3 (PRD already says so); keep design as a Phase-3 appendix | **HIGH** | The problem it solves (>20 tools/source flooding context) **does not exist for a solo builder writing 5–15 native `@tool`s**; the 77K→8.7K figure describes a 300-tool MCP catalog. PRD §8 already schedules it Phase 3; the resolution spec-coded it as if it were a current commitment, pulling in `bm25s` (drags `numba`, +1–2 GB install) + `PyStemmer` as non-bottleneck Phase-0 deps. **Also a real correctness finding for when it ships:** Strata's weight-15 parameter signal reads OpenAPI fields (`path_params`/`body_schema`) that standard MCP tools never produce (they ship `inputSchema`) → the param signal is **dead code** for the MCP path unless an `inputSchema.properties` extraction branch is added. (Verified vs cloned `open-strata`.) |
| 9 | **Multi-agent + sandbox** (3 topologies depth-cap-1 + CodeSandbox: microsandbox/E2B/Daytona) | **DEFER** → Phase 3 (PRD already says so). Sub-split: `subagent_delegate`/`fan_out` ship at Phase 3 as designed; `Orchestration(SharedTypedState)` defer **past Phase 2** | **HIGH** | Both features are **explicitly Phase 3 in the PRD** (§8, §10.9); the resolution re-labeled them "v1" 9× with no stated rationale. Concretely unbuildable now: `Orchestration`'s `SharedTypedState` coordination primitive has **no RE source and contradicts the sourced pattern** — Grok and Anthropic Research both use *directed message-passing*, not a shared dict; and it depends on the Phase-2 durable substrate that doesn't exist yet. The `verso.internal` egress proxy is an **unverified security mechanism** (the resolution's own Open Unknown #1). Sandbox compose-decision was *already correct* (microsandbox default) — but add a KVM-availability check (silently dead on shared cloud VMs). |

**Tally:** 2 SURVIVES (seam mechanism, colocated Postgres — both with revisions), 4 REVISE-split
(durable, model, memory, eval — lock-schema/defer-engine), 1 REVISE-compose (jsonish), 2 DEFER
(deferred-tools, multi-agent+sandbox — both already Phase 3 in PRD). **Zero REJECTs of an
architecture.** One sub-component REJECT for v1: learned model routers (D4 → cannot run on the
Phase-0 provider; contradicts a locked non-goal).

---

## 2. Revised v1 scope — what Phase 0 BUILDS vs COMPOSES vs DEFERS

This is the load-bearing output: a solo, dogfood-first builder must be able to ship it. It reconciles
the `_META_SCOPE` cut-list with the `_STEELMAN` compose-verdicts and the source-verified per-decision
findings. **The rule: build only the irreducible core + the two genuinely non-composable pieces;
compose the solved engines; lock every durable schema; defer every engine to the phase that proves it.**

### Phase 0 — the dogfoodable tactical core (~6–8 weeks solo). BUILD, full quality.
These ARE the wedge and the seam cannot be proven without them.

1. **`core/loop.py`** — the `<200`-line async ReAct loop, LIFO part-queue dispatch, `StopReason`
   enum, `max_steps=25` + token-budget + single synthetic grace message, doom-loop `ToolInspector`
   (soft=3/hard=5), `AgentResult`. *The thing the whole repo exists to keep small.*
2. **`context/`** — `RunContext[T]`, `ContextBundle`, KV-cache discipline (stable prefix /
   append-only / deterministic JSON), hard budget ceiling, `prune()` observation-masking,
   `agent.inspect()` byte-equality. *The deep differentiator — real, not a stub.* (Defer LLM
   `compact()` to "when prune isn't enough" — it needs the aux-model dogfood call anyway.)
3. **`tools/`** — `@tool` → `TypeAdapter(fn)` schema (one schema-gen path), `{data,error,ok}`
   dispatch that never raises into the loop, `ToolError` envelope, input-repair ladder, `think`/`done`.
   **Native only — no MCP, no deferred loader, no openapi.**
4. **`tools/jsonish.py` + `tools/coerce.py`** — the BAML 5-stage waterfall + typed-Flag coercion.
   **This is the one engine piece that must be built in v1** (genuinely non-composable). **COMPOSE
   the rest of structured-output from Instructor** (lift reask loop + mode-map + `Partial[T]`,
   openai-stripped). Add the FM2 guard: no reask on non-idempotent tools.
5. **`model/`** — the **thin** layer only: `ProviderProfile`+`OMIT`, Anthropic + OpenAI (+ Google)
   profiles, error-typed two-axis failover, `require_parameters` at init, `call_with_retry`
   (6/4s/240s), force `include_usage`, `AttemptRecord`. **~4 files, ~250 lines.** No balancer, no
   budget-Redis, **no learned routers, no reasoning gate.**
6. **`stream/`** — one 7-type true-delta `StreamEvent`, the normalizer, SSE transport.
   (Resumable `attach(starting_after=N)` is a durable concern → Phase 2.)

**Phase 0 exit:** build a real personal agent on it.

### Phase 1 — memory + the eval wedge, as INTERFACES over PROXIES (~3–4 weeks solo).

1. **`memory/`** — **LOCK** the types + `MemoryBackend` interface + DDL (cheap, durable). **SHIP**
   `SqliteVecBackend` (semantic-only, ~100 lines) **+ a `Mem0Backend` adapter** (~40–80 lines).
   `remember`/`recall` work via Mem0's V3 pipeline. Fix the `remember()` buffer-vs-insert incoherence
   by choosing one pattern (Mem0-direct-extract is simpler) before any code is written. **No graph
   arm, no bi-temporal, no consolidation daemon, no 4-arm retrieval — Phase 3.**
2. **`evals/`** — **LOCK+BUILD** `VersoSpan`/`VersoScore` + constants (~80–100 lines), the OTel emit
   layer (`gen_ai.*` primary, dot-form cache attrs, no RERANKER kind), and `define_outcome` (the
   bounded generate→grade→revise loop — small and Verso-specific). **COMPOSE the engine:** Langfuse
   (self-hosted) as trace store + online eval scheduler, `autoevals`/DeepEval for scorers (the
   constants Verso extracted ARE the autoevals constants), `braintrust.Eval()` for offline CI.
3. **`safety/hooks.py`** — the 5-stage lifecycle hooks (the extensibility mechanism the framework
   hangs off; small, build it).

**Phase 1 exit:** an eval suite (through the proxy) drives an iteration on the Phase-0 agent.

### Phase 2 — the seam, proven (the moment of truth for the primitive).

1. **`runtime/`** — **LOCK** the seam (`PersisterHook`/`RunContext` polymorphism); back it with
   **DBOS** behind a minimal `CheckpointBackend`. Prove the success criterion: *the identical agent
   runs tactically and durably with one flag and zero loop-code changes.* Enforce the `ctx.step()`
   body-contract (single call + assignment only). Build the bespoke engine **only** if DBOS friction
   is real and named. **Default durability = SYNC, not ASYNC.**
2. **`safety/permissions.py` + `confidence.py`** + `max_budget_usd` (simple counter, no Redis).
3. **`model/balancer.py` + reasoning gate** — now that multi-provider concurrent traffic + agent
   traces exist to calibrate them. Resumable streaming `attach()`.
4. **Colocated Postgres** — at Phase 2, Postgres is forced by the durable seam: install the 5
   checkpoint tables only (no `CREATE EXTENSION vector`, no memory tables — those land in Phase 3 on
   the *same* instance, which is when the "you already run PG → memory free" win is actually earned).

**Phase 2 exit:** the same agent runs a long, crash-resumable, HITL-gated task via `durable=True`.

### Phase 3+ — opt-in scale (build only what dogfood demanded).
The owned durable engine (if DBOS friction proved it), the owned memory engine (if Mem0 gaps proved
it — Hindsight model: extraction pipeline, graph arm, BM25, bi-temporal, consolidation), the owned
eval store (if Langfuse gaps proved it — the `correction` HITL→dataset flywheel, `source_span_id`
recursive observability, `p50/p80_horizon` metrics, `verify_grounding`), MCP + deferred loader,
pgvector + graph arm, multi-agent (`subagent_delegate`/`fan_out` first; `Orchestration` after the
`SharedTypedState` backend is decided), sandboxes (microsandbox + KVM check). **Each gated on a
proven gap, not a paper design.**

**Why this still satisfies both stated goals.** (a) *Proving the seam* requires the *interface* +
*any* backend behind it — DBOS-behind-the-seam proves the primitive as well as a hand-built engine
and months sooner; building the engine first actually *delays* the proof. (b) *Letting the user build
products* requires a clean loop, real context engineering + `inspect()`, native typed tools,
multi-provider failover, streaming, working memory, and a way to eval — **all in Phase 0/1 above.**
The owned engines are infrastructure the user never touches the internals of, so swapping
DBOS/Mem0/Langfuse for in-house versions later is invisible to products built on top.

---

## 3. Updated diff-style PRD edits (supersedes `_RESOLUTIONS.md §3` where noted)

These edits incorporate the surviving + revised decisions. Where the panel forced a change to an
`_RESOLUTIONS.md §3` edit, it is marked **[SUPERSEDES §3.x]**.

### 3.1 §10 item 8 (Durable substrate) — **[SUPERSEDES `_RESOLUTIONS.md §3.1` item 8]**

```diff
-8. **Durable substrate — RESOLVED (the big call):** BUILD in-house — pure Python + Postgres ...
-   DBOS-style step-memoization ... Schema: 5 tables in a `verso` schema ...
+8. **Durable substrate — RESOLVED (split into seam + engine):**
+   (A) SEAM — LOCK NOW: `durable=True` selects a `CheckpointBackend` via `RunContext` polymorphism;
+       loop SOURCE is identical (tactical = InMemory no-op; durable = backed). Correct citation:
+       DBOS `_core.py` / Centaur `workflow_engine.py:338-435` (NOT Burr application.py:2565 — Burr
+       checkpoints at the action boundary, Verso at sub-iteration). CONTRACT: the `async with
+       ctx.step()` block contains ONLY the single call + result assignment (side effects inside are
+       skipped on durable resume).
+   (B) ENGINE — DEFER to Phase 2, start from `pip install dbos`: DBOS's workflow_status+
+       operation_outputs IS this schema; MAX_RECOVERY_ATTEMPTS=100, startup recovery, fork_workflow
+       are already there. Build the bespoke 5-table engine ONLY if DBOS friction is named in dogfood.
+   (C) Default durability = SYNC (not ASYNC): ASYNC re-fires LLM calls on crash → different
+       non-deterministic result → corrupted event log. ASYNC is an explicit per-step opt-in.
+       `@tool(destructive=True)` auto-forces SYNC. seq via DB IDENTITY/SEQUENCE, never MAX(seq)+1.
```

### 3.2 §10 item 11 + §6.4 (Model layer) — **[SUPERSEDES `_RESOLUTIONS.md §3.1` item 11 + §3.3 §6.4]**

```diff
-11. **Provider-quirk line — RESOLVED:** `ProviderProfile` + 5 hooks + `OMIT` ... [and the model
-    layer ships balancer, budget guard, learned routers, reasoning gate]
+11. **Model layer — RESOLVED (thin core now; advanced routing deferred; learned routers REJECTED v1):**
+    Phase 0 BUILD: `ProviderProfile`+5 hooks+`OMIT`, Anthropic/OpenAI/Google profiles, error-typed
+    two-axis failover, `require_parameters` at init, `call_with_retry`, force include_usage,
+    AttemptRecord (~250 lines). Use `asyncio.Lock` (never threading.Lock); EWMA signal = TTFB not
+    wall-clock; budget check is atomic (no TOCTOU).
+    DEFER to Phase 2: PeakEWMA+P2C balancer, BudgetGuard+Redis, should_reason gate, cache-sticky
+    (all need multi-provider concurrency / agent traces to calibrate).
+    REJECT for v1: learned routers (RoRF/ConfidenceCascade/KNN). ConfidenceCascade needs logprobs
+    Anthropic does not expose; RoRF needs a 200-500-task corpus that doesn't exist; shipping them
+    contradicts the §2 non-goal "Not a model router cult." Lock a 3-line LearnedRouter Protocol only.
```

### 3.3 §5.4 (Memory) — **[SUPERSEDES `_RESOLUTIONS.md §3.2 §5.4` + §1C/C2]**

```diff
-§5.4: replace the single backend line with the 4-backend ladder (sqlite-vec / pgvector-Hindsight /
-Qdrant / Graphiti) and the graph-arm-only-in-Postgres rule [full engine shipped Phase 1]
+§5.4 — Phase 1: LOCK MemoryItem/MemoryType(4)/EpistemicClass(types only)/MemoryScope/MemoryBackend
+iface + DDL. SHIP SqliteVecBackend (semantic-only, ~100 lines) + Mem0Backend adapter (~40-80 lines,
+Mem0 V3 = the ADD-only policy + integer-index map). Fix remember(): pick ONE write model (Mem0
+direct-extract preferred) — do NOT call flush_buffer() then insert() (bypasses extraction).
+DEFER to Phase 3: the Hindsight PostgresBackend (extraction pipeline, memory_links graph arm, BM25,
+bi-temporal columns, 4-arm retrieval, consolidation daemon), Qdrant, Graphiti audit tier.
+[CORRECTION] daemon-thread pattern is Mem0 mem0/proxy/main.py:154-166, NOT Honcho. Default embed
+dim is a Phase-1 dogfood choice (Hindsight's real default is 384, not the doc's 1024 = Graphiti's).
```

### 3.4 §5.5 (Evals) — **[SUPERSEDES `_RESOLUTIONS.md §3.2 §5.5`]**

```diff
-§5.5: add VersoScore/VersoSpan schema, gen_ai.* OTel, 3 judge modes + built-in scorers, online/
-offline single EvalJob engine with dataset snapshot [full engine shipped Phase 1]
+§5.5 — Phase 1 BUILD: VersoSpan/VersoScore + named constants (~80-100 lines), OTel emit layer
+(gen_ai.* primary; cache attrs in DOT form: gen_ai.usage.cache_read.input_tokens; DROP RERANKER
+span kind — it silently becomes SPAN in Langfuse and Verso has no first-class reranker), and
+define_outcome (bounded revise loop). COMPOSE the engine in Phase 1: Langfuse (self-host) as trace
+store + online scheduler, autoevals/DeepEval for scorers (Verso's extracted constants ARE the
+autoevals constants), braintrust.Eval() for offline CI. DEFER owned store/queue/9-scorers to Phase 2
+(trigger: the correction-flywheel, source_span_id, p50/p80_horizon, verify_grounding gaps).
```

### 3.5 §3 locked-decisions table — **[SUPERSEDES `_RESOLUTIONS.md §3.5`]**

```diff
-| Durable substrate | In-house pure-Python + Postgres/SQLite, step-memoization | ... |
-| Storage story | One colocated Postgres ... for checkpoints + memory + small traces | ... |
+| Durable substrate | Seam locked now; engine = DBOS-behind-CheckpointBackend at Phase 2; bespoke
+  engine only if DBOS friction is dogfood-proven | No engine before one agent runs |
+| Storage story | SQLite + sqlite-vec dev everywhere; Postgres forced ONLY at Phase 2 by the durable
+  seam (5 checkpoint tables); memory/trace tables join the SAME PG at Phase 3 | pgroonga is a
+  SEPARATE install — say "tsvector fallback on stock PG", not "zero new services" |
+| Memory engine | Types+iface+DDL locked Phase 0; SqliteVec + Mem0 adapter Phase 1; Hindsight engine
+  Phase 3 | Mem0 V3 = the copied write policy; build the engine on proven gaps |
+| Eval engine | Schema+OTel+define_outcome built Phase 1; store/queue/scorers = Langfuse+autoevals+
+  Braintrust until Phase 2 | Score shape is universal; OpenInference ships ~33 free instrumentors |
| Schema-gen | Single `TypeAdapter(fn)` path | unchanged — survives |
```

### 3.6 §8 phasing — keep as written (the panel VINDICATES the existing PRD §8)

No edit. The PRD's Phase 0→1→2→3 order is correct; the resolutions violated it by pulling Phase-3
work (deferred-tools, multi-agent, sandbox) and Phase-2/3 engines (durable, memory, eval) into Phase
0/1. The verdict realigns the resolutions *to* §8 rather than changing §8. Add one clarifying line to
§10 item 9 and a new orchestrate note: *"deferred-tools, multi-agent topologies, and Code Mode sandbox
are Phase 3 per §8; their `06` design specs are Phase-3 appendices, not v1 build mandates. `Orchestration`
(SharedTypedState) waits until after the Phase-2 durable substrate (its coordination backend depends
on it). `subagent_delegate`/`fan_out` are thin asyncio wrappers that may land earlier if dogfood asks."*

### 3.7 Structured-output (§5.3) — keep the waterfall, compose the rest

```diff
+§5.3 structured output — BUILD the BAML jsonish 5-stage waterfall + typed-Flag coercion (genuinely
+non-composable). COMPOSE reask loop + provider mode-map + Partial[T] from Instructor (lift 4-5
+modules, strip openai>=2.0.0 hard-dep, ~1-2 day fork). Add: allow_reask=False default when a tool is
+idempotent=False/destructive=True (a reask freely regenerates the whole call → wrong email/payment).
+Benchmark framing: SAP's win is prose-with-embedded-JSON + stream truncation; the 19.8% figure is
+DEPRECATED function-calling, not modern forced-TOOLS mode.
```

---

## 4. What changed and why (for the user)

The adversarial panel could not break a single one of your nine architectures — every critic
re-cloned the source and confirmed your RE is correct, your schemas are right, and your destination
is sound. What they broke, unanimously, is the **timing**: the design resolved on paper the final
form of eight engines (durable, memory, eval, model-routing, jsonish, deferred-tools, multi-agent,
sandbox) before a single agent has run, each carrying 5–8 admitted "Open Unknowns" — which is the
exact anti-pattern your own load-bearing thesis exists to prevent ("the abstraction cursor can't be
found on paper, only by using the thing"). The fix is not to discard anything: it is to **lock every
durable schema/interface now (cheap, ~80–250 lines each), ship the proven engines as `pip install`
proxies behind those interfaces (DBOS for durable, Mem0 for memory, Langfuse+autoevals+Braintrust for
eval, Instructor for the reask/mode-map/streaming parts of structured-output), build only the two
genuinely non-composable pieces yourself (the clean loop + context engineering, and the BAML jsonish
waterfall), and build each owned engine later only when dogfood names a real gap the proxy can't
fill.** Three things were cut harder: learned model routers are REJECTED for v1 (they literally can't
run — Anthropic exposes no logprobs and there's no calibration corpus, and shipping them violates your
own "not a router cult" non-goal); deferred-tools and multi-agent/sandbox are pushed back to Phase 3
(where your own PRD §8 already put them). A handful of concrete correctness bugs surfaced and must be
fixed regardless of scope: the seam's Burr citation is wrong (it's DBOS/Centaur, and the `ctx.step()`
block must hold only the single call or durable resume silently diverges), the durability default must
flip ASYNC→SYNC, `remember()` currently bypasses memory extraction, the OTel cache attributes need
dots not underscores, and a reask on a non-idempotent tool can silently rewrite the whole call. The
result is a v1 a solo builder can actually ship in ~6–8 weeks (Phase 0) + ~3–4 weeks (Phase 1) plus
the one-flag seam test (Phase 2 over DBOS) — instead of the year-plus of engine-building the
resolutions specified.

---

*Adjudication complete. Authority on conflict: this file > `_RESOLUTIONS.md` (superseded where §3
edits are marked) > the 12 subsystem notes > PRD §10. The 27 per-decision critic files remain the
deep evidence trail. Every keep/cut/defer above traces to a source-verified file:line finding, not to
a scope opinion.*
