# Verso — Consolidated Design Resolutions

**Status:** Design finalized (pre-implementation). Supersedes the open forks in `docs/PRD_v1.md` §10.
**Date:** 2026-06-05
**Inputs:** `docs/PRD_v1.md` + all 12 subsystem notes in `research/06_design_resolutions/` (durable-runtime · production-topology · retrieval-backend · memory · model-routing · structured-output · tools-mcp · loop-and-coding-patterns · evals-trace · api-and-peers · sandboxes-multiagent).
**Purpose:** (1) one resolved-decisions table per PRD §10 fork + every subsystem call, with cross-agent conflicts adjudicated; (2) the finalized module map + public API surface with concrete backends/schemas; (3) diff-style PRD edits the orchestrator can apply; (4) the short list of things that genuinely need a Phase-0/1 prototype.

Label key throughout: **KNOWN** (read from RE'd source), **INFERRED** (derived), **DESIGNED** (Verso engineering for a proprietary gap), **CALIBRATE** (needs dogfood numbers).

---

## 0. The one cross-cutting decision: the colocated Postgres/SQLite story

Four subsystems independently chose the **same** storage substrate. This is the single most important consolidation and it is **not a conflict — it is a confirmation**: the agents converged without coordination.

| Subsystem | Dev tier (zero-infra) | Prod tier | Note |
|---|---|---|---|
| Durable runtime (`runtime/durable`) | SQLite (`aiosqlite`) | **Postgres** | `verso_runs` + `verso_step_outputs` + `verso_run_events` + `verso_hitl_promises` |
| Retrieval/memory vectors (`memory/ ‹edge2›`) | sqlite-vec | **pgvector** | "memories colocated with checkpoints in the same DB" (retrieval-backend.md D7) |
| Memory store (`memory/`) | sqlite-vec | **Postgres** (Hindsight model: pgvector + tsvector/pgroonga + `memory_links`) | memory.md D5 |
| Eval/trace store (`evals/`) | SQLite | ClickHouse (prod) **or** Postgres (small) | evals-trace.md D8 |

**RESOLVED (DESIGNED):** Verso ships **one colocated Postgres story**. In prod, a single Postgres instance holds: the durable checkpoint schema, the memory schema (pgvector), and (for small/dogfood deployments) the eval/trace schema. In dev, a single SQLite file + sqlite-vec holds all three. The user who already paid the "run Postgres" cost gets durable runtime + memory + traces for free — no second service. ClickHouse is an **opt-in eval-store upgrade** for operator-scale trace volume only (retrieval/checkpoints never go to ClickHouse). Qdrant is an **opt-in memory-scale upgrade** (>100k memories) only. This satisfies every subsystem's prod default without forcing a polyglot stack — and it is exactly the PRD's anti-Letta stance ("Letta mandates Postgres+pgvector" is bad only because it's *mandatory*; here it is the *prod* tier, with sqlite-vec as the zero-infra default).

One consequence to lock now: the durable-runtime schema and the memory schema share a Postgres instance but use **distinct table prefixes** (`verso_runs/...` vs `verso_memory*`/`memory_items`) so a single `CREATE EXTENSION vector` + one migration runner provisions both. Table-naming note in §1.

---

## 1. Resolved decisions table

### 1A. PRD §10 open forks — every one now RESOLVED

| # | PRD §10 fork | RESOLVED default | One-line evidence | Source note |
|---|---|---|---|---|
| 1 | Loop cap | `max_steps=25` **visible** + token-budget safety net + single synthetic-grace message (`MAX_STEPS_TEXT`) on the last step (a nudge, not a hard cut) | opencode injects a synthetic `assistant` "wrap up" message at `prompt.ts:1426`; no-cap is too runaway-prone for a framework | loop-and-coding §2 |
| 2 | Schema substrate | **Pydantic v2** runtime validation; `TypeAdapter(fn).json_schema()` is the single schema-gen path; v1/v2 dual-support banned; `TypedDict`/`dataclass` accepted as *sources* only | fastmcp + Instructor + Mirascope all build the schema from `TypeAdapter`; `model_construct` (streaming) and `validation_context` have no TypedDict equivalent | structured-output §2, tools-mcp §1 |
| 3 | Streaming delta | **True-delta globally**; SSE `data:{json}\n\n` + `[DONE]`; reasoning is a separate channel and is filtered before the stop check | Perplexity's fatal DX bug was inverting this; AgentKit infinite-loops if reasoning isn't filtered from the stop test | api-and-peers §6 |
| 4 | Multi-agent default topology | **Single-agent default.** Ship 3 opt-in shapes (`subagent_delegate`, `fan_out`, `Orchestration(orchestrator_workers)`), depth-cap **1**; **instrument before recommending** which | Evidence genuinely conflicts (Anthropic +90.2% from hierarchy vs Agent-S3 +13% from removing it) — the call is "ship all three, recommend none until evals" | sandboxes-multiagent §6, api-and-peers §8 |
| 5 | Memory taxonomy depth | **4-tier public enum** (`scratchpad 1h / episodic 7d / fact ∞ / procedural ∞`) + internal `EpistemicClass` (explicit/deductive/inductive/belief/procedural/skill/contradiction); extensible, not fixed-13 | Hindsight 4-way `fact_type`, Honcho 4 observation classes, MemOS lifecycle caps; Memanto's fixed-13 is opaque | memory §4 |
| 6 | Compaction model | **Two-pass:** cheap LLM-free `prune()` (observation-masking, keep reasoning/mask data, `N=10` rolling) as the routine pass; LLM `compact()` (anchored 8-section Markdown summary, rolling-update, aux model) only on overflow; deterministic truncation as the last-ditch fallback | opencode `compaction.ts` algorithm verbatim; JetBrains masking (+52% cheaper, +2.6% solve) is the prune pass, not a replacement for summary | loop-and-coding §3-5, PRD §5.2 |
| 7 | Tool-flooding strategy | **Deferred loading default above 20 tools/source**; 5 fixed meta-tools (`discover_tools/get_tool_details/execute_tool/search_tool_docs/handle_auth`); keyless field-weighted **BM25+** ranker; only the namespace manifest is eagerly injected | Strata 4-stage (action-granular, keyless); 77K→8.7K token gap from Claude Code teardown | tools-mcp §7-8 |
| 8 | **Durable substrate** *(biggest call)* | **BUILD in-house: pure Python + Postgres (SQLite dev), DBOS-style step-memoization** (re-enter loop, skip completed steps), Inngest `sha1(name)+:n` content-addressed step ids, AX two-log split, LangGraph 3 durability modes. Clean `CheckpointBackend` seam so a Temporal/Trigger.dev adapter can slot later. | Centaur/DBOS/Inngest/Windmill all prove pure-Python+Postgres step-memoization = Temporal's guarantees with no server; the seam test ("`durable=True`, zero loop changes") is trivial here and impossible-clean with Temporal's workflow/activity split | durable-runtime D1-D5, production-topology D2 |
| 9 | Code-execution escape hatch (Code Mode) | **Deferred to Phase 3** as planned; v1 default sandbox provider chosen = **microsandbox** (local libkrun microVM, `pip install`, <100ms boot, no daemon); E2B cloud + Daytona container as opt-in adapters behind one `CodeSandbox` protocol | microsandbox is the only "zero cloud account, hardware-grade isolation" local default; E2B requires `E2B_API_KEY` at import | sandboxes-multiagent §1-3 |
| 10 | HITL surface | **`await ctx.hitl.request(question, timeout=86400)`** is the only public API; backed by a **Resonate-style named Durable Promise** over `verso_hitl_promises`; `interrupt()`/`Command(resume=)` stays internal | Resonate's named promise is the only model that doesn't re-call the LLM on resume; the promise result is the memoized step output | durable-runtime D7, production-topology D7, api-and-peers §2 |
| 11 | Provider-quirk line | **Core ships clean adapters for top providers** (Anthropic/OpenAI/Google/Groq) via `ProviderProfile` + 5 hooks + `OMIT` sentinel; deep quirks pushed to `~/.verso/plugins/model-providers/` (last-writer-wins, failure-isolated) | LiteLLM's 4-method `Config` scaled to 100+ providers without monolith; `OMIT` beats LiteLLM's `drop_params` global | model-routing D1 |
| 12 | Self-improvement | **Ship `on_stop`/`on_idle`/`on_turn_complete` hooks in v1**; consolidation primitive (Honcho-style surprisal-gated "dream": `N=50` ∧ `≥8h`, top-10% novel) is **opt-in, not core** | Honcho `config.py:1168-1170` trigger constants; cluster-unanimous "never block the agent on consolidation" | memory §8, api-and-peers §10 |
| 13 | Judge panel | **Overridable named default** `DEFAULT_JUDGE_PANEL` (Sonnet 0.4 / GPT 0.4 / Gemini 0.2, threshold 0.7) + `.single(model)` shorthand + full custom; model strings are module-level constants, never hardcoded in panel logic | Character.AI production-validated weights; PRD §10.13 anti-vendor-lock satisfied by making it overridable, not absent | evals-trace D9 |

### 1B. Additional subsystem decisions worth locking (not in PRD §10 but load-bearing)

| Area | RESOLVED default | Evidence | Source |
|---|---|---|---|
| Loop shape | LIFO part-queue dispatcher over typed tasks (`CompactionTask`/`SubtaskTask`), not flat `if/elif` | opencode `prompt.ts:1278-1295` 4-branch LIFO | loop-and-coding §1 |
| Doom-loop guard | Composable `ToolInspector` pipeline; soft=3 (warn-inject), hard=5 (`STUCK`); canonical-JSON equality after stripping `IGNORED_PARAMS` | Cline two-threshold + opencode `processor.ts:36`; Goose pluggable inspector trait | loop-and-coding §6 |
| Plan/Act mode | Persisted run-level `mode` (`plan`/`act`) with per-mode `{prompt, tools, model}`; `task_boundary` tool enforces structurally | Cline persisted-mode + Roo Code `modeConfigSchema` | loop-and-coding §7 |
| One-flag seam mechanism | `durable=True` appends exactly **one** `PersisterHook` (PostRunStepHook) to the lifecycle adapter set; loop is byte-identical both ways | Burr `application.py:2565` / `persistence.py:214` — the entire seam is one 4-line class | api-and-peers §1 |
| Tool error contract | `{data, error, ok}` envelope with a structured `ToolError{kind, can_retry, retry_after_ms, prompt_content, developer_message}`; Arcade-derived `ErrorKind`; `mask_error_details=True` default | Arcade `OutputError` + MCP SEP-1303 `isError` placement | tools-mcp §3-5 |
| Tool auth HITL | `AuthInterrupt` as a *value* in `ToolResult` (not an exception); 45s long-poll; checkpoint `{auth_id, tool, input}` | Arcade `auth.py:24` `_DEFAULT_LONGPOLL_WAIT_TIME=45` | tools-mcp §6 |
| Structured-output parse | BAML jsonish 5-stage waterfall (universal post-hoc) + BAML typed-Flag cost function (not Levenshtein); SAP default, constrained decoding opt-in (local engines only) | BAML BFCL: SAP beats native FC on every model; CD needs logits Verso doesn't own | structured-output §1,4,5 |
| Reask loop | tenacity `stop_after_attempt(2)`, retry **only** on `ValidationError`; Guardrails `OnFailAction` (FIX→FIX_REASK→REASK→EXCEPTION); `total_usage` summed across attempts | Instructor `retry.py` + Guardrails `on_fail.py` | structured-output §6 |
| Model load-balancing | PeakEWMA + Power-of-Two-Choices; `decay_τ=30s`, `seed_rtt=250ms`; asymmetric peak-up/decay-down | Helicone `discover.rs:37-43`; Bifrost independently chose P2C | model-routing D2 |
| Cross-model failover | Two-axis `models[] × providers[]`, error-typed (`CONTEXT_WINDOW`→next model, `RATE_LIMIT`→next provider, `AUTH`→raise); `require_parameters=True` validated at init | Vercel two-level + OpenRouter `require_parameters` | model-routing D3-D4 |
| Reasoning-effort | `effort=low/med/high → {1024, 8192, 32768}` tokens, per-provider `build_extra_body`; per-step `should_reason` gate (selective beats always-on: +10.2pp, −47% latency) | vLLM SR + "When to Reason" arXiv 2510.08731 | model-routing D7 |
| Trace/score schema | `VersoScore` (5-element: name/value-float/source-enum/label?/reason? + trace_id FK + `correction` flywheel); `VersoSpan` 10-kind taxonomy + `dotted_order` sortable tree key; `gen_ai.*` OTel primary + OpenInference enrichment | 6 platforms converge on the score primitive; Langfuse 10-kind taxonomy; LangSmith `dotted_order` | evals-trace D1-D3 |
| Eval engine | One `EvalJob` engine for online (async queue, sample/delay/dedup) and offline (dataset run with denormalized snapshot); large-trace judge routing at 50k tokens | Opik Redis-Streams + Langfuse `dataset_run_items` snapshot | evals-trace D5-D6 |
| Multi-agent return type | `SubagentResult(summary, files, artifacts)` typed compact summary — never the sub-agent's raw history; lead IS the synthesizer | `_SYNTHESIS.md` Avoid #18; Grok leader-is-synthesizer | sandboxes-multiagent §6 |
| Credential boundary | Egress proxy / `HttpSecret(host=..., inject_header=...)`; agent + harness hold **no** secret; host-scoped credential; deny-all sandbox egress default | Anthropic "harness never aware of credentials" + Centaur iron-proxy + CF `globalOutbound` | production-topology D9, sandboxes-multiagent §4 |
| Topology at scale | Session (durable log) / Harness (stateless loop, fungible) / Sandbox (lazy on first sandboxed tool call) | Anthropic Managed Agents: lazy sandbox = p95 TTFT −90% | production-topology D1,D4 |

### 1C. CONFLICTS between subsystem agents — adjudicated

Four genuine cross-agent disagreements (and three apparent-but-not conflicts) were found. Calls made:

**C1 — `@tool` schema-gen path: `inspect`-walk vs `TypeAdapter(fn)`.**
*structured-output.md §8* proposes `tool_to_json_schema(fn)` via manual `inspect.signature` + `get_type_hints` + per-param `TypeAdapter(annotation)`. *tools-mcp.md §1* proposes porting fastmcp's `TypeAdapter(fn).json_schema()` applied to the **whole function** + a 6-step compress pipeline. *api-and-peers.md §4* just says "type hints → schema."
**CALL (RESOLVED, DESIGNED):** Adopt **tools-mcp.md's `TypeAdapter(fn)` whole-function path** as the single implementation (`verso/tools/schema.py::build_tool_schema`), because it correctly handles nested/Optional/Union/Literal via Pydantic in one call and ships the 6 protocol-correctness transforms (variadic-reject, forward-ref resolve, DI-strip, compress/prune-titles, keep `additionalProperties:false`, scalar-return-wrap). Fold in structured-output.md's two *additions* that tools-mcp.md lacks: the **`Annotated[T, Doc(...)]`** first-class param-doc path and the **`make_format_tool_schema(model)`** forced-extraction tool (all-fields-required) for structured output. There is **one** schema-gen function, not two. `FORMAT_TOOL_NAME="_verso_format_output"`.

**C2 — Memory prod backend: "pgvector colocated, no graph" vs "Hindsight Postgres with `memory_links` graph + Graphiti/Neo4j audit tier".**
*retrieval-backend.md D7* tiers as sqlite-vec → pgvector(colocated) → Qdrant, with **no graph arm** and recall = RRF over dense+sparse. *memory.md D5/D6/D9* tiers as sqlite-vec → **Hindsight-model Postgres** (pgvector + tsvector/pgroonga + `memory_links` 3-signal graph + bi-temporal columns) → **Graphiti/Neo4j audit tier**, with a **4-arm** retrieval (semantic+BM25+graph+temporal).
**CALL (RESOLVED):** memory.md is the **richer, authoritative** memory design; retrieval-backend.md is the authoritative **vector-retrieval mechanics** (RRF k-algebra, DBSF, ANN constants, ReadLevels). They are **layers, not competitors**:
- The **prod default** is the Hindsight single-Postgres model (memory.md D5): pgvector + tsvector + `memory_links` graph-without-a-graph-DB + bi-temporal columns. This is one Postgres, zero new services — consistent with §0.
- The **graph arm activates only in the Postgres backend** (memory.md D9); the sqlite-vec dev tier runs dense+BM25 only (no `memory_links`), which is exactly retrieval-backend.md's dev tier.
- **Qdrant** (retrieval-backend.md) and **Graphiti/Neo4j** (memory.md) are **two distinct opt-in scale tiers** for two distinct needs: Qdrant = pure vector scale (>100k, prefetch-tree hybrid, ACORN); Graphiti/Neo4j = bi-temporal `recall_as_of` audit when a graph DB's interval semantics are actually required. Ship the `MemoryBackend` interface with: `SqliteVecBackend` (dev), `PostgresBackend` (prod default, Hindsight model), `QdrantBackend` (vector scale), `GraphitiBackend` (audit). retrieval-backend.md's `BackendAdapter` and memory.md's `MemoryBackend` are **merged into one interface** (`verso/memory/backend.py`) — they describe the same edge.
- **RRF k:** reconcile the k disagreement with memory.md's **pool-size-adaptive rule** — `k=60` for large ANN/BM25 pools (retrieval-backend.md default, literature value), `k=1` for small graph candidate pools (Graphiti), Qdrant's `k=2` exposed as a documented "steep" preset. This subsumes both notes.

**C3 — Composite/recency scoring: two different formulas.**
*retrieval-backend.md §2.7* gives `0.5·semantic + 0.3·recency_decay(30d) + 0.2·importance` (PRD §5.4 verbatim, **additive**, post-fusion). *memory.md D6* gives Hindsight **multiplicative** bounded boosts (`CE × recency_boost(±10%) × temporal_boost(±10%) × proof_count_boost(±5%)`, recency window 365d).
**CALL (RESOLVED):** The PRD's additive `0.5/0.3/0.2` is the **default v1 post-fusion re-rank** (it is what §5.4 promises and what the dev tier can compute without a cross-encoder). The Hindsight multiplicative boost is the **opt-in "audit/quality" rerank** used when a cross-encoder reranker is configured (the multiplicative form is correct *only* when CE relevance is the primary signal — additive is correct when blending raw fused score + recency + importance). Both ship; the additive is default, multiplicative activates with `RerankConfig(reranker=CrossEncoderReranker())`. Recency window: keep PRD's 30d for the additive default, 365d for the CE-multiplicative path (they serve different score regimes). CALIBRATE which wins at dogfood.

**C4 — Durable schema table names: `verso_step_outputs` vs `verso_steps`; `verso_run_events` vs `verso_events`; `verso_hitl_promises` vs `verso_promises`.**
*durable-runtime.md D4* and *production-topology.md §Data Schema* describe the **same** schema with **different table names** and slightly different column sets (durable-runtime is richer: `agent_version`, `idempotency_key`, `parent_run_id/root_run_id`, lease columns, `available_at`, the `step_kind`/`RunEventType` enums; production-topology adds `verso_sandboxes` and `internal_only` on events + the lazy-sandbox/credential-proxy framing).
**CALL (RESOLVED):** **durable-runtime.md D4 is the authoritative schema** (it is the most complete). Apply these name reconciliations and merges:
- `verso_step_outputs` (durable-runtime) is canonical; production-topology's `verso_steps` is the same table — use `verso_step_outputs`.
- `verso_run_events` (durable-runtime) is canonical; production-topology's `verso_events` is the same — use `verso_run_events`, and **add production-topology's `internal_only BOOLEAN` column** (durable-runtime already has it — confirmed consistent).
- `verso_hitl_promises` (durable-runtime) is canonical; production-topology's `verso_promises` is the same — use `verso_hitl_promises`, keep production-topology's HTTP endpoint surface (`POST/GET/PATCH /v1/promises/{id}` + `/heartbeat` + `/callback`).
- **Add production-topology's `verso_sandboxes` table** (session→sandbox binding, `generation` counter) — durable-runtime omits it; it is needed for the lazy-sandbox topology. Keep it.
- Reconcile the run-status enum: durable-runtime uses `queued/running/sleeping/waiting/completed/failed/cancelled/max_recovery_exceeded`; production-topology uses `PENDING/SUSPENDED/SUCCESS/ERROR/CANCELLED/MAX_RECOVERY_EXCEEDED`. **Use durable-runtime's lowercase set** (it is finer-grained: separates `queued` from `running`, `sleeping` from `waiting`), mapping production-topology's `PENDING→queued`, `SUSPENDED→waiting|sleeping`, `SUCCESS→completed`, `ERROR→failed`.

**Apparent-but-not conflicts (no action needed, just noted so the orchestrator doesn't "fix" them):**
- *Durability modes* — durable-runtime D5, production-topology D6, api-and-peers all say `sync/async/exit`, default `async`. **Consistent.**
- *HITL surface* — durable-runtime D7, production-topology D7, api-and-peers §2 all say `await ctx.hitl.request()` over a Resonate named promise. **Consistent.**
- *Step identity* — durable-runtime D2 and production-topology D2 both say Inngest `sha1(name)+:n`. **Consistent.**
- *Default judge model string drift* — evals-trace uses `gpt-5-mini`/`gpt-5` in examples and `claude-sonnet-4-6` in the panel; PRD §7 uses `claude-sonnet-4-6`/`gpt-5.1`/`gemini-3-pro`. These are freshness-volatile model strings, not architecture. Pin them as module constants (`verso/model/known_models.py`) updated on model releases; not a conflict.

---

## 2. The resolved Verso architecture

### 2.1 Finalized module map

The 3 pluggable edges are marked `‹edgeN›`. Everything concrete is named with its now-chosen backend. Changes from PRD §4.2 are marked **(+)**.

```
verso/
  core/
    loop.py            LIFO part-queue dispatcher (<200 lines) · StopReason(9) · synthetic grace msg
    context_obj.py     RunContext[T] (contextvars-scoped: ctx.budget/emit/hitl/memory/usage)
    result.py          AgentResult(output, stop_reason, usage, cost_usd, trace_id, steps_taken)
    events.py          typed event model (tactical: in-memory list; durable: → backend)
  context/
    bundle.py          ContextBundle(instructions, memory, history, tools, retrieved, budget_*)
    budget.py          hard ceiling ~75-80%; reactive overflow on last-turn BILLED tokens (+20k reserve)
    kvcache.py         stable-prefix discipline · deterministic JSON · append-only enforcement
    compaction.py      prune() masking pass + compact() 8-section anchored summary (aux model)  (+)
    truncation.py      deterministic half/quarter fallback when summarizer overflows           (+)
    repomap.py         OPT-IN coding: tree-sitter + PageRank + binary-search budget            (+)
    inspector.py       agent.inspect() = byte-equal dry-run of context assembly
  model/               ‹edge1›
    profile.py         ProviderProfile (5 hooks + OMIT) · Anthropic/OpenAI/Google/Groq
    failover.py        two-axis models[]×providers[] · error-typed · call_with_retry(6,4s,240s)
    balancer.py        PeakEWMA + P2C (τ=30s, seed 250ms)
    budget.py          BudgetGuard (count|cost, check-before/charge-after, fail-open)
    reasoning.py       effort→tokens · should_reason_step() per-step gate
    routers/           OPT-IN learned routing: RoRFRouter · ConfidenceCascade · KNNRouter
    validation.py      require_parameters enforced at Agent.__init__
  tools/               schema-gen + dispatch
    decorator.py       @tool → frozen ToolMeta on fn.__verso__; fn returned unchanged
    schema.py          build_tool_schema = TypeAdapter(fn) + 6 transforms + Annotated[T,Doc]   (C1)
    dispatcher.py      {data,error,ok} envelope · parallel reads(5)/sequential writes · repair ladder
    result.py          ToolResult · ToolError(kind,can_retry,prompt_content) · AuthInterrupt
    jsonish.py         5-stage SAP waterfall (universal post-hoc parser)
    coerce.py          typed-Flag cost function (BAML table verbatim) · pick_best
    structured_output.py  parse_with_reask · Partial[T] streaming · OnFailAction
    registry.py        namespace:action · local-first · DEFERRED_LOADING_THRESHOLD=20
    deferred_loader.py 5 meta-tools · BM25+ field-weighted ranker
    edit_format.py     OPT-IN coding: SEARCH/REPLACE cascade · per-model EDIT_FORMAT_TABLE     (+)
    adapters/          ‹edge3›  native(default) · mcp(2025-11-25 client+server) · openapi(Phase 3)
  memory/              ‹edge2›
    types.py           MemoryItem · MemoryType(4) · EpistemicClass(7) · MemoryScope · bi-temporal
    memory.py          Memory: remember/recall/recall_as_of (tool-callable) · working-set FIFO 20
    retrieval.py       HybridQuery · RRF(k=60, pool-adaptive) + DBSF · composite + CE rerank     (C2,C3)
    backend.py         MemoryBackend iface + StoreConfig union (MERGES retrieval+memory ifaces)  (C2)
    backends/          sqlite_vec(dev) · pgvector(prod, Hindsight model) · qdrant · graphiti(audit)
    consolidate.py     OPT-IN surprisal-gated dream (N=50 ∧ 8h, top-10%)                         (+)
    embedder.py        asymmetric embed_document ≠ embed_query
  evals/               the wedge
    schema.py          VersoScore · VersoSpan(10-kind) · DatasetItem/RunItem · EvalRun           (+)
    trace.py           dotted_order tree · SpanContext (contextvars) · gen_ai.* + OpenInference  (+)
    judge.py           JudgePanel · 3 verdict modes · built-in scorers · DEFAULT_JUDGE_PANEL     (+)
    unit.py            EvalSuite · Assertion (incl. trajectory:*)                                (+)
    outcome.py         define_outcome bounded loop (default 3, max 20)
    online.py          EvalQueue (asyncio dev / Redis-Streams prod) · sample/delay/dedup         (+)
    store.py           TraceStore iface: SQLite(dev) · ClickHouse|Postgres(prod)                 (+)
    otel_compat.py     bidirectional gen_ai↔openinference map                                    (+)
  stream/
    events.py          StreamEvent (7-type discriminated) · true-delta · seq_id
    normalizer.py      strip-blank-around-tool-use · coerce end_turn · classify finish:"error"
    transport.py       SSE data:{json} + [DONE] · attach(starting_after=N) cursor replay
  runtime/
    tactical.py        in-memory: empty LifecycleAdapterSet (Burr seam)
    durable/           the seam
      backend.py       CheckpointBackend ABC (InMemory=tactical, Postgres/SQLite=durable)
      schema.py        verso_runs · verso_step_outputs · verso_run_events · verso_hitl_promises
                       · verso_sandboxes   (durable-runtime D4 canonical + production-topology merge) (C4)
      executor.py      DurableExecutor: run(durable=True) · submit() · attach() · _worker_loop
      step.py          ctx.step() memoization CM · hash_step_id (Inngest sha1+:n)
      hitl.py          HITLManager (Resonate named promise) · resolve/reject/timeout-scan
      session.py       Session(emit_event/get_events) · replay_to_messages
      worker.py        claim FOR UPDATE SKIP LOCKED · lease 30s · heartbeat 10s · recover
  orchestrate/         OPT-IN, separate import (verso.orchestrate)
    delegate.py        subagent_delegate(fork_mode) → SubagentResult · depth-cap 1
    fanout.py          fan_out(max_concurrency=5) · order-preserving
    orchestration.py   Orchestration(orchestrator_workers) · shared typed state store
    handoff.py         Handoff (control transfer) · as_tool (call+return) · router union
    graph.py           ESCAPE HATCH: Send-fan-out + Command-routing (map-reduce only)
    sandbox.py         CodeSandbox protocol (microsandbox default · e2b · daytona)              (+)
  safety/
    permissions.py     4-valued (allow|deny|ask|defer) · priority-ordered policy layers
    confidence.py      router [0,1] no dead zone (≥0.85 auto / 0.40-0.85 review / <0.40 discard)
    hooks.py           5-stage (pre/post_model · pre/post_tool · on_stop/error/idle) · error-isolated
    trust.py           system > framework_rules(immutable) > agent > user · web_fetch SSRF guard
    credential_proxy.py  HttpSecret host-scoped egress proxy (agent holds no secret)            (+)
```

Design invariant unchanged: `core/loop.py` stays **<200 lines**; all weight (retry, failover, compaction, dispatch, memoization) lives in sibling modules.

### 2.2 Finalized public API surface (the shape users touch)

This merges api-and-peers.md (the authority on surface ergonomics) with the concrete types each subsystem chose. Unchanged-from-PRD-§7 lines are kept; concretized lines are annotated.

```python
from verso import Agent, tool, init_model, Memory, ModelPolicy
from verso.runtime import RunContext

# --- @tool: TypeAdapter(fn) schema · ctx injected & filtered · {data,error,ok} envelope ---
@tool(read_only=False, destructive=True, idempotent=False, timeout=None, max_result_chars=None)
async def get_weather(city: str, ctx: RunContext) -> dict:
    """Required non-empty docstring → LLM description (ValueError at decoration if empty)."""
    ...  # raise freely; framework wraps. destructive=True ⇒ idempotent=False ⇒ max_attempts=1

# --- the 90% path ---
agent = Agent(
    model="anthropic:claude-sonnet-4-6",                 # "provider:model"; parsed on first use
    tools=[get_weather],
    instructions="You are ...",                          # first-class attr; never hidden/closure
    memory=Memory.default(),                             # sqlite-vec dev; 4-tier typed
    max_steps=25,
    model_policy=ModelPolicy(require_parameters=True,    # validated at __init__
                             fallback=["openai:gpt-5.1", "google:gemini-3-pro"]),
)

result = await agent.run("weather in Paris?")
# AgentResult(output, stop_reason: StopReason, usage: UsageStats, cost_usd, trace_id)
# StopReason ∈ {end_turn, max_steps, max_tokens, tool_rule_stop, cancelled, error,
#               budget_exhausted, stuck, compaction_failed, eval_exit}   (unified 10-value enum)

async for ev in agent.stream("..."):                    # 7-type true-delta + seq
    ...  # ev.type ∈ {message.delta, reasoning.delta, tool.start, tool.result, status, error, stream.end}

agent.inspect()  # → ContextBundle; ContextBundle.to_wire() byte-equals the actual wire payload

# --- the seam: one flag, same loop (Burr PersisterHook mechanism) ---
result = await agent.run("deep task", durable=True, durability="async")  # sync|async|exit
handle = await agent.submit("deep task")                # → RunHandle(run_id, status=queued)
async for ev in agent.attach(handle.run_id, starting_after=last_seq): ...
await agent.cancel(handle.run_id)
answer = await ctx.hitl.request("Approve sending this email?", timeout=86400)  # named durable promise

# --- knobs ---
await agent.run("...", effort="high", verbosity="quick", mode="plan")  # mode = persisted run state

# --- memory: typed + tool-callable + audit-grade ---
await agent.memory.remember(content="...", type="fact", confidence=0.9)  # ADD-only
await agent.memory.recall(query="...", types=["fact"], scope={"user_id": "u1"})  # 4-arm hybrid
await agent.memory.recall_as_of(query="...", date=...)  # audit tier; raises if backend non-bitemporal

# --- evals first-class (post-hoc, never gating the hot path) ---
from verso.evals import EvalSuite, JudgePanel, Factuality, GEval
suite  = EvalSuite.from_cases([...]); res = await suite.run(agent)   # Tier 1: unit/CI
panel  = JudgePanel.default(); scores = await panel.score(trace_id)  # Tier 2: judge panel
agent.define_outcome(rubric="...", max_iterations=3)                 # Tier 3: bounded revise

# --- opt-in multi-agent (separate import) ---
from verso.orchestrate import Orchestration, fan_out, subagent_delegate, Handoff
results = await fan_out(tasks=[...], workers=worker, max_concurrency=5)  # order-preserving
summary = await subagent_delegate("subtask", worker, fork_mode="none")  # → SubagentResult
team    = Orchestration(lead=agent, workers=[a,b,c], pattern="orchestrator_workers")

# --- hooks (5-stage, error-isolated) ---
@agent.hook("pre_tool")
async def gate(ctx, call): return "ask" if call.tool.destructive else "allow"

# --- opt-in tool adapters & code sandbox ---
agent.add_tools(mcp_server="...")          # MCP 2025-11-25, deferred-load >20 tools
agent.add_tools(openapi="./spec.yaml")     # Phase 3
agent = Agent.from_yaml("agent.yaml")      # simple stateless agents
```

**Surface invariants (unchanged + 4 confirmed):** one `provider:model` format; one true-delta convention; `stop_reason` always a named enum; tools raise freely, framework never lets an exception reach the loop; memory is one object with typed entries; routing is per-node config; single agent is the default, orchestration is a separate import; evals/resumable-streaming/durable-HITL/confidence-gating are in the box. **+** schema-gen is one path (`TypeAdapter(fn)`); HITL is one API (`ctx.hitl.request`); the durable seam is one hook (`PersisterHook`); `inspect()` byte-equality is a tested success criterion.

### 2.3 Concrete backends & schemas chosen (the durable-decision summary)

- **Durable substrate:** in-house, pure-Python + **Postgres** (prod) / **SQLite** (dev). Step-memoization (DBOS-style), content-addressed step ids (Inngest `sha1+:n`), two-log split (AX), 3 durability modes (LangGraph), Resonate named-promise HITL. Tables: `verso_runs`, `verso_step_outputs`, `verso_run_events`, `verso_hitl_promises`, `verso_sandboxes` (durable-runtime D4 schema, canonical — §1C/C4). Constants locked: `MAX_RECOVERY_ATTEMPTS=100`, `WORKER_LEASE=30s`, heartbeat `10s`, reconcile `0.5s`, `HITL_DEFAULT_TIMEOUT=86400s`, default durability `async`.
- **Memory:** **Hindsight single-Postgres model** prod (pgvector HNSW `m=16/ef_c=64/ef_s=40` + tsvector/pgroonga BM25 `k1=1.2/b=0.75` + `memory_links` graph + bi-temporal columns); **sqlite-vec** dev (`chunk_size=1024`, brute-force <10k); **Qdrant** vector-scale opt-in; **Graphiti/Neo4j** audit opt-in. RRF `k=60` (pool-adaptive: `k=1` graph pools, `k=2` "steep" preset). Composite re-rank additive `0.5/0.3/0.2` default, CE-multiplicative opt-in. ADD-only writes, integer-index anti-hallucination map, tier-selected conflict resolution. Tables: `memory_items`, `entities`, `unit_entities`, `memory_links`, `memory_history`, `memory_buffer`.
- **Eval/trace store:** **SQLite** dev, **ClickHouse** (operator-scale) or **Postgres** (small) prod. `VersoSpan`/`VersoScore` schemas; `dotted_order` tree key; `gen_ai.*` primary OTel.
- **Model edge:** `ProviderProfile` + 5 hooks + `OMIT`; PeakEWMA+P2C; two-axis error-typed failover; budget guard; learned routers opt-in. Provider plugins at `~/.verso/plugins/model-providers/`.
- **Code sandbox (Phase 3):** `CodeSandbox` protocol; **microsandbox** local default, E2B/Daytona opt-in; deny-all egress + credential proxy.

---

## 3. Proposed PRD edits (diff-style — apply to `docs/PRD_v1.md`)

### 3.1 Rewrite §10 entirely — "Deferred / open decisions" → "Resolved decisions (was deferred)"

Replace the §10 heading and intro:

```diff
-## 10. Deferred / open decisions (with chosen v1 defaults)
-
-These are the harvest's genuine forks. v1 picks a default and moves; each is revisited after dogfooding.
+## 10. Resolved decisions (formerly deferred)
+
+These were the harvest's genuine forks. As of 2026-06-05 each is RESOLVED from the 12-subsystem
+design pass (`research/06_design_resolutions/_RESOLUTIONS.md`). The default + evidence is below;
+only the items in §10-Phase-0 still need a prototype to finalize a number.
```

Rewrite each item (replace the 13 list entries):

```diff
-1. **Loop cap:** `max_steps=25` visible default + token-budget safety net + grace call. (vs Codex's no-cap.)
+1. **Loop cap — RESOLVED:** `max_steps=25` visible + token-budget safety net + a single synthetic
+   `MAX_STEPS_TEXT` "wrap up" assistant message on the last step (nudge, not hard cut). Evidence:
+   opencode `prompt.ts:1426`. [loop-and-coding §2]

-2. **Schema substrate:** type-hints → schema natively; Pydantic v2 *optional*, never v1/v2 dual.
+2. **Schema substrate — RESOLVED:** ONE schema-gen path: `pydantic.TypeAdapter(fn).json_schema()`
+   on the processed function (6 transforms: variadic-reject, forward-ref resolve, DI-strip,
+   compress/prune-titles, keep additionalProperties:false, scalar-wrap) + `Annotated[T, Doc(...)]`
+   param docs. Pydantic v2 runtime validation; v1/v2 dual banned; TypedDict/dataclass as sources
+   only. Evidence: fastmcp `function_parsing.py:130-314`. [tools-mcp §1, structured-output §2,8]

-3. **Streaming delta:** true-delta globally.
+3. **Streaming delta — RESOLVED:** true-delta globally; SSE `data:{json}\n\n` + `[DONE]`; reasoning
+   is a separate channel, filtered before the stop check. Evidence: AgentKit infinite-loops without
+   the filter; Perplexity's inverted-delta DX bug. [api-and-peers §6]

-4. **Multi-agent default topology:** single-agent default; orchestrator-workers + fan-out as the opt-in shapes; **instrument before recommending either** (evidence genuinely conflicts: Anthropic +90.2% vs Agent-S3 +13% from removing the hierarchy).
+4. **Multi-agent default topology — RESOLVED (instrument-before-recommend):** single-agent default;
+   ship THREE opt-in shapes — `subagent_delegate(fork_mode)`, `fan_out(max_concurrency=5)`,
+   `Orchestration(orchestrator_workers)` — all depth-capped at 1; `SubagentResult` typed compact
+   summary return (never raw history); lead IS the synthesizer. Which to recommend stays a
+   post-dogfood eval question (the evidence conflict is real). [sandboxes-multiagent §6]

-5. **Memory taxonomy depth:** 4-tier default, extensible enum (not Memanto's fixed 13).
+5. **Memory taxonomy depth — RESOLVED:** 4-tier public enum (scratchpad/episodic/fact/procedural)
+   + internal `EpistemicClass` (explicit/deductive/inductive/belief/procedural/skill/contradiction);
+   extensible, not fixed-13. Evidence: Hindsight/Honcho/MemOS. [memory §4]

-6. **Compaction model:** observation-masking default; same-model summarize fallback; thread-handoff exposed.
+6. **Compaction model — RESOLVED:** two-pass — cheap LLM-free `prune()` (observation-masking, keep
+   reasoning/mask data, rolling N=10) routine; LLM `compact()` (anchored 8-section Markdown summary,
+   rolling-update, AUX model to spare primary cache) on overflow; deterministic half/quarter
+   truncation as last-ditch. Reactive overflow on last-turn BILLED tokens + 20k reserve. Evidence:
+   opencode `compaction.ts`/`overflow.ts`; JetBrains masking. [loop-and-coding §3-5]

-7. **Tool-flooding strategy:** deferred loading default; meta-tool router available for very large sources.
+7. **Tool-flooding strategy — RESOLVED:** deferred loading default above 20 tools/source; 5 fixed
+   meta-tools (discover/details/execute/search/auth); keyless field-weighted BM25+ ranker; only the
+   namespace manifest eagerly injected. Evidence: Strata 4-stage; Claude Code 77K→8.7K. [tools-mcp §7-8]

-8. **Durable substrate:** in-house Postgres/SQLite event-log + checkpoint for v1; clean seam to adopt Temporal/Trigger.dev later. *(Biggest deferred infra call.)*
+8. **Durable substrate — RESOLVED (the big call):** BUILD in-house — pure Python + Postgres (SQLite
+   dev), DBOS-style step-memoization (re-enter loop, skip completed steps), Inngest content-addressed
+   step ids (`sha1(name)+:n`), AX two-log split, LangGraph 3 durability modes, Resonate named-promise
+   HITL. Clean `CheckpointBackend` ABC so a Temporal/Trigger.dev adapter slots later. Schema: 5 tables
+   in a `verso` schema (see _RESOLUTIONS §1C/C4 + durable-runtime §D4). Evidence: Centaur/DBOS/Inngest/
+   Windmill converge on pure-Python+Postgres = Temporal guarantees, no server. [durable-runtime,
+   production-topology]

-9. **Code-execution escape hatch (Code Mode):** deferred to ≥ Phase 3; sandbox provider TBD (E2B/Modal/V8 isolate).
+9. **Code-execution escape hatch — RESOLVED (provider chosen; still Phase 3):** `CodeSandbox`
+   protocol; default = microsandbox (local libkrun microVM, pip-install, <100ms boot, no daemon);
+   E2B cloud + Daytona container opt-in adapters. Deny-all egress + credential proxy (agent holds no
+   secret). Evidence: sandboxes-multiagent §1-4. [sandboxes-multiagent]

-10. **HITL surface:** high-level `await ctx.hitl.request()` is the API; `Command(resume=)` stays internal.
+10. **HITL surface — RESOLVED:** `await ctx.hitl.request(question, timeout=86400)` only public API,
+    backed by a Resonate-style named Durable Promise over `verso_hitl_promises`; the promise result
+    is the memoized step output (no LLM re-call on resume); `interrupt()`/`Command(resume=)` internal.
+    Evidence: Resonate spec; production-topology D7. [durable-runtime D7]

-11. **Provider-quirk line:** core ships clean adapters for the top providers; deep quirk accumulation pushed to per-provider plugins.
+11. **Provider-quirk line — RESOLVED:** `ProviderProfile` dataclass + 5 hooks (prepare_messages,
+    build_extra_body, fetch_models, normalize_response, normalize_error) + `OMIT` 3-state sentinel;
+    Anthropic/OpenAI/Google/Groq in core; deep quirks → `~/.verso/plugins/model-providers/`
+    (last-writer-wins, failure-isolated). Evidence: LiteLLM 4-method Config. [model-routing D1]

-12. **Self-improvement:** ship `on_turn_complete`/`on_idle` hooks in v1; a built-in consolidation primitive is opt-in, not core.
+12. **Self-improvement — RESOLVED:** ship `on_stop`/`on_idle`/`on_turn_complete` hooks in v1;
+    consolidation (surprisal-gated "dream": N=50 ∧ ≥8h, top-10% novel) is opt-in `memory/consolidate.py`,
+    not core. Evidence: Honcho `config.py:1168-1170`. [memory §8]

-13. **Judge panel:** ship an overridable example panel config; never hardcode a single vendor.
+13. **Judge panel — RESOLVED:** overridable named `DEFAULT_JUDGE_PANEL` (Sonnet 0.4 / GPT 0.4 /
+    Gemini 0.2, threshold 0.7) + `.single(model)` + full custom; model strings are module constants,
+    never hardcoded in panel logic. Evidence: Character.AI JudgeJudy panel. [evals-trace D9]
```

Append a new subsection at the end of §10:

```diff
+### §10-Phase-0 — the few items that still need a prototype (not paper)
+These are genuinely undecidable without dogfood numbers (see _RESOLUTIONS §4):
+the auxiliary compaction model choice; the default embedding model+dimension; the RoRF/threshold
+calibration corpus; CACHE_STICKY_STEPS, DEFERRED_LOADING_THRESHOLD, and the additive-vs-CE-rerank
+choice; the v1 credential-proxy/`verso-daemon` implementation depth; and replay_to_messages() fidelity.
```

### 3.2 §5 — gain the concrete tactical-core specs

- **§5.1 (core loop):** add that the loop is a **LIFO part-queue dispatcher** (CompactionTask/SubtaskTask enqueued, not if/elif branches) [loop-and-coding §1]; expand `StopReason` to the unified 10-value enum (`+ compaction_failed, eval_exit`); add the doom-loop **ToolInspector pipeline** (soft=3 warn / hard=5 STUCK, canonical-JSON + IGNORED_PARAMS) [loop-and-coding §6]; add **`exit_when` metric-terminated** runs [loop-and-coding §12].
- **§5.2 (context):** add the **reactive overflow** rule (check last-turn BILLED tokens incl. cache, `+20k` reserve) and the **two-pass compaction** (prune masking + 8-section anchored summary + truncation fallback) with the named constants [loop-and-coding §3-5].
- **§5.3 (tools):** lock the **`TypeAdapter(fn)` single schema-gen path** + 6 transforms [tools-mcp §1]; add the structured **`ToolError`/`ErrorKind`** taxonomy + `mask_error_details=True` + MCP `isError` placement [tools-mcp §3-5]; add `AuthInterrupt`-as-value HITL [tools-mcp §6]; add the **5 meta-tools + BM25+** deferred loader [tools-mcp §7-8].
- **§5.4 (memory):** replace the single backend line with the **4-backend ladder** (sqlite-vec / pgvector-Hindsight / Qdrant / Graphiti) and the **graph-arm-only-in-Postgres** rule; note RRF k is **pool-adaptive** (60/1/2); note the **additive-default / CE-multiplicative-opt-in** rerank split [memory §5,6,9 + retrieval-backend; §1C/C2,C3 here].
- **§5.5 (evals):** add the **`VersoScore`/`VersoSpan`** schema, the **`gen_ai.*` OTel** emission, the **3 judge verdict modes** + built-in scorers + Factuality asymmetric map, and the **online/offline single EvalJob engine** with the dataset snapshot [evals-trace D1-D7].
- **§5.6 (streaming):** add the **7-type `StreamEvent`** enum, the **stream normalizer** stages, and the **seq-cursor `attach(starting_after=N)`** protocol [api-and-peers §6, production-topology resumable-streaming].

### 3.3 §6 — gain the durable/topology/model specs

- **§6.1 (durable):** add the **5-table schema** (canonical names from §1C/C4), the **`ctx.step()` memoization contract**, the **3 durability modes**, the **Session/Harness/Sandbox topology** (lazy sandbox = p95 TTFT −90%), the **game-loop pseudocode**, and the **write-before-advance** invariant [durable-runtime, production-topology].
- **§6.2 (multi-agent):** add `SubagentResult` typed return, `subagent_delegate(fork_mode)`, `Orchestration` shared-typed-state, the **depth-cap-1** enforcement (`DepthCapExceeded`), and the router union type [sandboxes-multiagent §6, api-and-peers §8-9].
- **§6.3 (safety):** add the **credential proxy / `HttpSecret`** host-scoped egress boundary (agent holds no secret) [production-topology D9].
- **§6.4 (model):** add the **PeakEWMA+P2C** balancer, the **two-axis error-typed failover** table, the **`require_parameters` init-time enforcement**, the **`BudgetGuard`** check-before/charge-after + cache-aware cost, the **effort→token map + per-step `should_reason`**, and the **opt-in learned routers** [model-routing D2-D9].

### 3.4 §7 — adopt the merged surface from §2.2 above

Replace the §7 code block with §2.2 (it is the same shape, now with: the unified 10-value `StopReason`, the 7-type `StreamEvent`, `durability=` sub-option, `ctx: RunContext` typed in the `@tool` example, `recall(scope={...})` dict form, and `subagent_delegate` added to the orchestrate imports). Add the four new surface invariants (one schema-gen path, one HITL API, one seam hook, tested inspect byte-equality).

### 3.5 §3 — add three resolved rows to the locked-decisions table

```diff
+| Durable substrate | In-house pure-Python + Postgres/SQLite, step-memoization | No server; seam test trivial; Temporal adapter later via CheckpointBackend |
+| Storage story | One colocated Postgres (prod) / one SQLite file (dev) for checkpoints + memory + small traces | The user who runs Postgres gets durable+memory+traces free; sqlite-vec zero-infra default |
+| Schema-gen | Single `TypeAdapter(fn)` path | Handles nested/Optional/Union in one call; model_construct/validation_context have no TypedDict equivalent |
```

---

## 4. Remaining unknowns for Phase-0/1 dogfood (need a prototype, not paper)

These are the genuinely-undecidable items distilled from all 12 notes' "Open Unknowns" — the ones where the right answer is a measured number, not an argument. Everything else above is decided.

1. **Auxiliary compaction model.** Does a cheap aux model (haiku-class / gpt-mini) produce summaries good enough to resume mid-task without confusion, or is same-model-as-primary needed? Warp's deterministic TODO-preservation hybrid is the candidate. [loop-and-coding OU#1] — **Phase 0** (compaction lands in Phase 0).

2. **Default embedding model + dimension.** Cluster spans 384/1024/1536. Pick: `text-embedding-3-small@1024` (OpenAI, symmetric) vs a local `all-MiniLM-L6-v2@384` (dev, keyless) vs an asymmetric E5/BGE. Affects pgvector/sqlite-vec column dim and SBQ regime. [memory OU#1, retrieval OU#2] — **Phase 1**.

3. **RoRF threshold + calibration corpus.** Learned routing needs 200-500 representative tasks scored against both models to set `threshold = quantile(win_rates, 1-target_a_pct)`. Cannot be guessed. [model-routing OU#2] — **Phase 1+** (learned routing is opt-in; not blocking).

4. **Three CALIBRATE constants:** `CACHE_STICKY_STEPS=5` (too low → cache misses on long runs; too high → blocks failover) [model-routing OU#1]; `DEFERRED_LOADING_THRESHOLD=20` (Strata's 60-80% context-reduction claim needs measuring on Verso's own registry) [tools-mcp OU#1]; **additive `0.5/0.3/0.2` vs CE-multiplicative rerank** (C3 — which wins on the real memory corpus) [retrieval OU#3, memory C3]. — **Phase 0/1**.

5. **`replay_to_messages()` fidelity + step-hash stability.** Crash-resume must reconstruct the exact `messages[]` the provider expects (tool_result ordering, multi-tool batches), and the Inngest `:n` counter shifts hashes when a developer inserts a step mid-loop. Needs a round-trip test that crash-resumes a complex multi-step session and byte-compares context. Decide whether a "step names stable within a run-version" contract or a `fork_workflow(from_step)` migration tool is needed. [production-topology OU#2,7; durable-runtime OU] — **Phase 2** (before durable runtime ships).

6. **v1 credential-proxy + `verso-daemon` implementation depth.** The `HttpSecret` interface is stable; the proxy backend (localhost mitmproxy vs thin httpx transport) and the in-sandbox daemon build (Go binary vs shiv-Python, startup latency under libkrun) are not. The microsandbox smoltcp `verso.internal` domain-rule resolution needs an integration test (resolves before first guest SYN?). [sandboxes-multiagent OU#1,3; production-topology OU#4] — **Phase 3** (sandbox is Phase 3).

7. **`ctx.hitl.request()` in tactical mode.** In durable mode it's a checkpoint-backed pause; in tactical (no persister) the only sensible behaviors are block-on-stdin or a user-supplied callback. Pick the default before Phase 2. [api-and-peers OU#5] — **Phase 2**.

8. **G-Eval logprob fallback.** Anthropic exposes no `top_logprobs`; G-Eval Mode B must feature-detect and fall back to Mode A (structured) for non-OpenAI providers. Find the right fallback ergonomics. [evals-trace OU#1] — **Phase 1**.

Everything not in this list is **decided**. The loop above (Phase 0 dogfood → adjust → Phase 1 …) is the mechanism that closes these eight, in the PRD §8 build order.

---

*Consolidation complete. Authority order on conflict: this file > the 12 subsystem notes > PRD v1 §10 (now superseded). The subsystem notes remain the deep evidence trail (file:line cites, full Component Specs); this file is the adjudicated index.*
