# Verso — Product Requirements Document (v1)

**Status:** Draft v1.1 — design locked, **adversarially audited** (30-agent panel; `research/07_adversarial/_VERDICT.md`) · **Phases 0–2 + Plans 13–20 shipped (266 tests green)** · **raw-source rechecked + FULL-SOURCE-INVESTIGATED 2026-06-12** (verdict: design + bet held across all **319** Bad Guide sources, ~228 full-text + ~89 transcript-hunted, 4 workflows — **refinements consolidated in §14**; full evidence in `research/08_raw_recheck/` + `research/09_bad_guide_full_raw/`)
**Date:** 2026-06-04 · addenda 2026-06-05: §12 positioning/GTM + founder-OS cross-reference; §10 resolved + §13 build/compose/defer scope (after a 12-agent resolution pass + a 30-agent adversarial audit) · 2026-06-12: §14 — recheck + full 319-source sweep, consolidated into one by-section refinement layer (`research/08_raw_recheck/`, `research/09_bad_guide_full_raw/`)
**Owner:** Slava (@Seventydotleven)
**Grounding:** the verified "keep-it-simple" thesis (`Verso/research/THESIS_VERIFICATION.md`) + 28,496 lines of reverse-engineered harvest across 54 source notes and 3 synthesis briefs (`Verso/research/01_bad_guide/`, `02_core/`, `03_teardowns/`). Every default in this PRD traces to that evidence; load-bearing ones cite the source note in brackets, e.g. `[agentic-architectures]`. A separate **founder-OS / go-to-market** layer — a 244-source deep index of *The Bad Guide* — lives in `Verso/research/04_bad_guide_full/` and feeds §12.

---

## 0. TL;DR

Verso is a **Python agent framework** whose primitive is *the boring core done right*: one clean async ReAct loop, with the two things every other framework buries made first-class — **context engineering** and **evals + reliability**. Its organizing idea is the **tactical↔durable seam**: the same agent runs ephemeral-and-simple by default and is *promoted* to durable (event-sourced, checkpoint-resume, human-in-the-loop) with one flag — never a rewrite, never a forced graph. The one-sentence pitch, and the counter-position to LangGraph/CrewAI: **"we don't force the graph."**

---

## Implementation status (Phases 0–2 + follow-ups · 2026-06-14)

Phases 0–2 (plus follow-up Plans 13–20) are **built, tested, and pushed** (`uv run pytest` → 266 passing, 1 skipped; `ruff` clean). Every plan was implemented test-first and independently rechecked.

| Area | Shipped | Plan |
|---|---|---|
| Core ReAct loop, `@tool`/dispatch, ContextBundle + KV-cache prefix + `prune`, ProviderProfile/FailoverModel/retry, streaming + SSE | Phase 0 | walking-skeleton, plan2–5 |
| **Evals wedge** — VersoSpan/VersoScore, `Eval.unit` + pass^k, LLMJudge + JudgePanel, `define_outcome`, `from_trace`, OTel `gen_ai.*` | Phase 1 | plan6 |
| **Memory** — `Memory` over a swappable backend (Sqlite + InMemory + **`SqliteVecBackend` ANN index**), 4-tier typed, RRF retrieval, temporal `recall_as_of`, memory-as-tools, **`reflect()` consolidation + procedural tier** | Phase 1 + 2 | plan7, plan12, plan14 |
| **Safety / hooks** — 5-stage lifecycle hooks, 4-valued `PermissionDecision`, reinforcement-on-return; **`PermissionPolicy` + session modes + `confidence_router`**; **ctx-aware hooks** (`ctx.deps`/`trace_id` on run + stream) | Phase 1 + 2 | plan8, plan11, plan15 |
| **Prompt-cache** — `cache_control` ephemeral breakpoint on the byte-stable prefix | Phase 2 | plan9 |
| **The durable seam (the thesis)** — `RunContext[T]`, checkpoint/resume, pause-on-ASK + tool-initiated `ctx.hitl.request`, InMemory + Sqlite checkpoint stores, `Agent(checkpointer=, deps=)`. **Byte-identical when off; survives process restart.** | Phase 2 | plan10, plan13 |
| **"Don't limit the user" escape hatches** — provider/sampling params + `extra_body`/`extra_headers`, `Retry(feedback)` self-healing tools + output validators, `tool_from_schema` (raw/MCP), read-only `ctx` enrichment (usage/messages/model/step), richer resume (edit-args / deny / skip), `should_continue` steering hook, `merge_messages`/`RemoveMessage` compaction. **All additive — byte-identical when unused.** | Phase 2 | plan16 |
| **Time-travel (durable debugging)** — per-step checkpoint `history()` on the store contract + `Agent.fork(at_step=N)` to branch an independent run from any step (re-runs from the fork point, no step-memoization). Additive `checkpoint_history` table — legacy `.db` opens unmigrated; **no core-loop change** (`resume_loop` already continues a pending-less checkpoint). | Phase 2 | plan17 |
| **Multi-provider** — `OpenAIModel` (Chat Completions) + `GoogleModel` (Gemini) behind the unchanged `Model` Protocol; `init_model('openai:…' / 'google:…')`. Lazy SDK imports (suite stays dependency-free), OMIT discipline, `extra_body`/`extra_config` escape. Removes Anthropic lock-in. | Phase 2 | plan18 |
| **OpenAI-compatible zoo** — `init_model('groq:…' / 'openrouter:…' / 'together:…' / 'fireworks:…' / 'deepseek:…' / 'xai:…' / 'mistral:…' / 'ollama:…')` + raw `base_url`/`api_key` for ANY compatible endpoint (local vLLM, private gateway). One adapter, the whole zoo — never a fixed list. | Phase 2 | plan19 |
| **Model⇄logic swap** — `Agent(model='openai:gpt-4o')` (string or instance); per-run `run`/`stream`/`resume(model=…)`; `override(model=…)` scoped context manager. Write the logic once, change the model as many times as you want — no rebuild, no mutation (concurrent-safe). Matches Pydantic AI's typed shape. | Phase 2 | plan20 |

**Deferred (seams locked, tracked):** pgvector/Mem0 memory adapters (need a live Postgres / mem0 instance to verify-and-test against, not guess — the `MemoryBackend` contract is the seam they implement); durable streaming resume; cross-re-run side-effect memoization (full durable-execution determinism).

---

## 1. The bet (why Verso should exist)

The agent-framework market converges on one finding across every reverse-engineered production system: **the agent loop is 5–10 lines and is not where anyone competes.** The product is the harness around it — context/cache discipline, tool design, error recovery, durable state, evals. Yet the incumbents get this backwards:

- **LangGraph** forces a Pregel/BSP graph (`DEFAULT_RECURSION_LIMIT=10007`, channels with reducers, "writes invisible until end of step") as the *default* mental model — a tax most agents never need. `[fw-langchain-langgraph]`
- **LangChain** buried the loop under the LCEL `Runnable` layer (15+ classes of mandatory indirection) and shipped Day-1 ease that became a Day-30 wall — it had to rewrite to 1.0 and publicly concede its abstractions were "too heavy." `[anthropic-agent-design]`
- **CrewAI** ships two execution models in one repo (`Crew` + `Flow`) and fake streaming (run-in-thread + tail-an-event-bus). `[fw-crewai-letta]`
- **Claude Agent SDK** hides the loop inside a binary and is Anthropic-only — fatal for a general framework. `[fw-claude-sdk-platforms]`
- **Letta** ships a 2,134-line agent monolith and mandates Postgres+pgvector. `[fw-crewai-letta]`

The verified thesis says this happens because teams over-engineer around *transient* model limitations and call it architecture. Tactical workarounds (JSON-coercion hacks, hand-built CoT, small-context chunking) genuinely churn on a ~1–2 year clock; the **durable layer** (ReAct, context engineering, memory, evals, orchestration) persists across 3+ model generations. **Verso's wedge: ship the boring durable core as a clean, small, typed, async surface, and make the four things the big frameworks bury into 3,000-line files into first-class primitives — context, evals, typed memory, and the tactical/durable seam.**

This is differentiation *and* (eventually) defensibility: a cleaner loop is differentiation; the accreting **memory + eval corpus + tool registry** is the moat (Aggregation-Theory / process-power). `[primitives-not-wrappers]`

---

## 2. Scope, users, non-goals

**Who it's for (v1):** the author, first. Verso is **personal infrastructure, built dogfood-first**, architected clean enough to open-source later. The single loudest meta-lesson in the harvest is that the right abstraction cursor *cannot be found on paper — only by using the thing* (it's why LangChain had to rewrite). So v1 optimizes for "I can build my own AI products on this and feel where it's wrong," not for external adoption metrics.

**Eventual users (OSS-ready):** Python engineers building agentic products who want LangGraph's power without its graph tax, and who want evals/reliability in the box.

**Non-goals (what Verso refuses to be) — the principled refusal model:**

- **Not an SDK / HTTP client.** (You can write one in an hour; it isn't the product.)
- **Not a graph-DSL / workflow-orchestrator by default.** Graphs are an opt-in escape hatch, never the spine. *"Don't build a better LangGraph wrapper."* `[transcripts-yc]`
- **Not the model/kernel.** Verso is the application/driver layer above a thin provider abstraction; it never re-implements inference or model serving. `[karpathy-canon]` OS analogy.
- **Not MCP-first.** Native Python functions are the tool path; MCP is a demoted, opt-in adapter for *external* servers only (MCP schema-bloat eats the context window — Yarats/Perplexity). `[research-perplexity]` anti-pattern #11.
- **Not multi-language (v1).** Python-only until the core abstraction is proven. No Rust: the binding constraint is LLM API latency (seconds), not interpreter overhead (microseconds); a Rust/FFI boundary would buy nothing a user can feel while walling off Python OSS contributors — and "don't over-engineer around a non-bottleneck" is the verified thesis itself.
- **Not a model router / planner cult.** Routers and hand-crafted planners are *tactical* scaffolding the harvest flags as depreciating; Verso supports them but never centers them. `[multi-agent-ttc]`

---

## 3. Locked decisions

| Decision | Call | Rationale |
|---|---|---|
| Scope | Personal infra, dogfood-first, OSS-ready | Find the abstraction cursor by use, not on paper `[oss-library-craft]` |
| Language | **Python-first, single language. No Rust.** | LLM latency dominates; research substrate is Python; resist multi-lang until core proven |
| Identity | All three layers: simple loop (surface) + context-engineering (deep diff) + evals/reliability (moat) | The harvest's convergent stack |
| v1 ambition | Full vision — **designed** complete, **built** in dogfood-order phases | Honors "full vision" without over-building ahead of evidence |
| Architecture | C-synthesis: tactical↔durable seam as spine; one cohesive package; 3 pluggable edges | Most faithful to thesis + harvest |
| Tools | **Native Python `@tool` is THE path; MCP demoted to optional adapter** | Native = zero schema-bloat, inspectable; MCP for external interop only |
| Pluggable edges | model providers · memory backends · tool sources | Only the three things that genuinely vary across deployments |

---

## 4. Architecture — the spine (Chunk 1)

### 4.1 The tactical↔durable seam (the organizing idea)

```python
agent.run(task)                  # TACTICAL: in-memory, append-only history, fast. The 90%.
agent.run(task, durable=True)    # DURABLE: SAME loop, every step checkpointed to an event log
   ── or ── agent.submit(task)   #          → crash-resume, HITL pause/resume across processes,
                                 #          long-running/background jobs, time-travel.
```

The loop code is **identical** across both runtimes. Durability is a property of the *runtime the loop executes in*, not a different loop and not a graph you author. The loop is **event-sourced internally** — every step emits a typed event — so the **tactical runtime** keeps events in memory while the **durable runtime** persists them to a checkpointer. You never rewrite an agent to make it durable; you flip a flag and cross the seam.

This is Verso's counter-position incumbents cannot rebut: *forcing graphs costs ~3× complexity for ~0 benefit on most agents* `[primitives-not-wrappers]`, and the seam is the verified thesis rendered as architecture — durable-layer durable, tactical-layer simple, move across without a rewrite.

### 4.2 Module map (designed in full; built in phases)

The **3 pluggable edges** the harvest proved must swap are marked `‹edgeN›`; everything else is concrete (resisting premature abstraction).

```
verso/
  core/         loop · RunContext · AgentResult+StopReason · typed event model
  context/      ContextBundle assembly · token budget · KV-cache discipline ·
                observation-masking compaction · agent.inspect()          ← deep differentiator
  model/        ‹edge1› ProviderProfile adapters · per-node router · reasoning-effort dial
  tools/        @tool registry · dispatch (always {data,error,ok}) · repair ladder ·
                ‹edge3› tool-source adapters: native(default) · mcp(opt-in) · openapi
  memory/       unified Memory (short+long+compaction) · 4-tier typed · temporal/audit ·
                retrieval (RRF k=60) · ‹edge2› backends: sqlite-vec(dev)→pgvector(prod)
  evals/        unit · judge-panel · define_outcome(bounded) · grounding-verify   ← the wedge
  stream/       one structured event stream · resumable transport · background runs
  runtime/      tactical (in-memory)  +  durable (event-sourced checkpoint/resume/HITL)  ← the seam
  orchestrate/  OPT-IN: subagent-as-context-isolation · parallel fan-out · graph escape hatch
  safety/       permissions (allow/deny/ask/defer) · confidence router · 5-stage hooks · trust hierarchy
```

Design invariant: the loop stays **<200 lines** because all weight (retry, failover, dispatch, compaction) lives in its own sibling module, each small and single-purpose. `[hermes-agent-core]` (anti-pattern: Hermes' 3,600-line loop, Letta's 2,134-line agent).

---

## 5. The tactical core (Chunk 2)

> **[Audited 2026-06-05]** This section describes the full *target* design. **§13 is authoritative on what v1 actually BUILDS vs COMPOSES vs DEFERS** — notably: structured-output (§5.3) builds only the `jsonish` waterfall and *composes* its reask/mode-map/streaming from Instructor; memory (§5.4) and evals (§5.5) lock their schemas in Phase 0/1 but *compose* the engines from Mem0 and Langfuse+autoevals+Braintrust. Everything else here is Phase-0 BUILD.

### 5.1 Core loop (`core/loop.py`)

A `<200`-line async ReAct loop:

```
while not cancelled and budget.remaining:
    bundle = assemble_context(...)          # § 5.2
    response = await model.call(bundle)     # § 6.4 (router, failover)
    if response.tool_calls:
        results = await dispatch(response.tool_calls)   # § 5.3 (parallel reads, sequential writes)
        append(results)                                  # append-only, never mutate
    else:
        return finalize(response)
```

- **Termination = named `StopReason` enum**, never text-sniffing "done": `end_turn · max_steps · max_tokens · tool_rule_stop · cancelled · error · budget_exhausted · stuck`. `[fw-crewai-letta]` (Letta `_decide_continuation`), `[coding-claude-code]` (12 `TerminalReason`s).
- **Caps:** `max_steps=25` *visible* default (not LangGraph's hidden 10007) + token-budget as the real safety net + a single **deterministic grace call** on budget exhaustion (model summarizes instead of a hard mid-task cut). `[hermes-agent-core]`. Avoid LangChain's opportunistic `early_stopping_method="generate"` extra-LLM-call anti-pattern.
- **Stuck detection** (repeated identical action→observation, error loops, monologue) → `STUCK` stop reason + optional `declare_bankruptcy()`, never silent looping. `[external-agentic-products]` (OpenHands thresholds: repeated=4, error-loop=3).
- **Result is always** `AgentResult(output, stop_reason: StopReason, usage: UsageStats, cost_usd, trace_id)`. `[fw-crewai-letta]`.
- **Optional `tool_rules`** constraint solver (Init/Terminal/Continue/Child/RequiresApproval) turns free-form ReAct into a declarative FSM without hardcoding workflows. `[fw-crewai-letta]` (Letta — copy the solver). Opt-in.
- **Optional mode-gate FSM** (`PLANNING → EXECUTION → VERIFICATION` enforced by a `task_boundary` tool — the model *cannot* edit while planning; constraint is architectural, not advisory). Opt-in per turn, with a "skip mode for trivial work" selector. `[coding-gemini-antigravity]` (the single most impactful reliability pattern in that teardown).

### 5.2 Context engineering (`context/`) — the deep differentiator

The harvest's #1 principle: *the loop is trivial; the context is the product.*

- **`RunContext[T]`** — typed, injected into every tool and hook: `ctx.budget.{remaining,is_last_step}`, `ctx.emit(event)`, `ctx.hitl.request(q)`, `ctx.memory`, `ctx.usage_by_category()`. Replaces LangChain's ContextVar/`config['configurable']` implicit propagation with explicit typed injection. `[fw-langchain-langgraph]` (copy Runtime v0.6).
- **`ContextBundle(instructions, memory, history, tools, retrieved, budget_used, budget_total)`** — context is a named, composable, **inspectable** object, never string concatenation. `agent.inspect()` returns *exactly what the model sees* (transparency-as-correctness: hidden prompts are bugs). `[anthropic-agent-design]`, `[context-engineering]`.
- **KV-cache discipline, framework-enforced** (the #1 free cost lever): stable prefix (system + tool schemas + base instructions) is **immutable and first**; dynamic suffix after; **append-only** history (never mutate/reorder prior turns); **deterministic JSON** serialization (sorted keys). The framework prevents accidental cache breaks (e.g. timestamps in the system prompt). Manus-style discipline = ~10× cost reduction from architecture alone. `[agentic-architectures]`, `[coding-claude-code]` (`__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__`).
- **Budget is a hard constraint** with a default soft ceiling (~75–80% of window before compaction; never wait for 100%). Over-budget is a warning/blocking event, **never silent truncation** (lossy → hallucination). `[context-engineering]`, `[agentic-architectures]`.
- **Compaction = first-class lifecycle event.** Default strategy: **observation-masking** (keep all reasoning/actions, mask tool outputs beyond rolling window `N=10` → 52% cheaper, +2.6% solve-rate, zero API overhead). Fallback: authored summarize-and-replace (structured handoff: goal / done / files / failed-and-why / next / constraints) with an anti-hallucination instruction ("only mark done on explicit confirmation"). Pruned items become placeholder strings, never silent deletes. `[agentic-architectures]` (JetBrains NeurIPS 2025), `[coding-conductor]`.
- **Distilled-reflection memory** for research-style loops (`ResearchMemory(cap=50)`): never accumulate raw tool outputs in the iterative window — compress each iteration to short notes, reintroduce raw sources only at final synthesis. ~66% token reduction. `[infra-retrieval-tools]` (Tavily/Firecrawl converged).

### 5.3 Tools (`tools/`) — native-first, MCP optional

- **`@tool` decorator is THE tool path:** docstring + type hints → JSON schema automatically (no Pydantic required; Pydantic v2 optional for rich validation — and v2-only, never the v1/v2 dual-support bug farm). `[fw-langchain-langgraph]` avoid #22.
- **Tool config carries policy, not just schema:** `read_only` / `destructive` / `idempotent` hints (drive permission routing for free), optional `timeout`, `retry`, `max_result_chars`, and an optional deterministic **`validate()`** pre-execution check that runs *before* any side effect commits (3 outcomes: retry / escalate-to-approval / inform — none execute the side effect). `[transcripts-yc-rootaccess]` (Parahelp 99% on billing actions), `[top-agentic-startups]` (Dust `ToolSpec`).
- **Dispatch ALWAYS returns `{data, error, ok}` — never raises into the loop.** Tool functions may `raise` freely; the framework wraps. `[hermes-agent-core]`, `[fw-composio-browseruse]` (Composio envelope). Errors are **model-legible with a hint** — errors are the self-correction mechanism. `[transcripts-dlai]`.
- **Input-repair ladder** (`json.loads → ast.literal_eval → json5 → repair_json`) + fuzzy tool-name correction (`SequenceMatcher > 0.85`) + repeated-`(tool,args)` short-circuit (returns cached result, breaks infinite loops). `[fw-crewai-letta]`.
- **Parallelism:** read-only tools run concurrently (bounded `max_concurrency=5`) with **order preservation** (results appended in original call order regardless of completion); mutating tools run sequentially; concurrency forced to 1 when any call needs approval. `[fw-composio-browseruse]`, `[hermes-agent-core]`, `[external-agentic-products]` (Mastra).
- **Non-idempotent tools → `max_attempts=1`** (auto-retrying state-changing actions is a correctness bug). `[top-agentic-startups]`.
- **Built-ins shipped:** `think` (no-op CoT scratchpad → forces reflection into an observable channel) and `done(result)` (structured termination with an optional verification checklist). **~Zero opinionated domain tools** — the framework ships the mechanism, not the toolbox. `[research-nia-societies-mindtrip]`, `[hermes-agent-core]` ("ship 0 built-in tools").
- **Tool-source adapters (`‹edge3›`, opt-in):** `native` (default), `mcp` (external servers only — never inlined; discovered via a tool-search/deferred-loading meta-tool so 1000 schemas don't flood context), `openapi` (import a spec as tools). Deferred loading is the default whenever a source is large (77K→8.7K tokens). `[coding-claude-code]`, `[fw-composio-browseruse]`, `[coding-cursor-zed]`.

### 5.4 Memory (`memory/`) — a real primitive, not a Redis adapter

- **One `Memory` object, three faces:** short-term (in-context working set, a channel of the event log), long-term (one canonical store queried three ways — semantic/vector + lexical/BM25 + exact/filter, fanned out in parallel), and compaction (TTL- and token-budget policies). Not three desyncing stores. `[infra-vector-memory]` (Turbopuffer: "worst outages are state in multiple places not syncing").
- **4-tier typed**, extensible enum: `scratchpad` (1h) / `episodic` (7d) / `fact` (∞) / `procedural` (∞); per-type TTL enforced by the store, scope keys (`user_id`/`agent_id`/`run_id`) auto-injected. `[research-nia-societies-mindtrip]`, `[missing-top-agentic]` (Mem0).
- **Memory-as-tool-calls** (the LLM manages its own memory, observably): `remember / recall / recall_as_of`. Writes are **additive** (ADD-only extraction; model never silently overwrites). `[fw-crewai-letta]` (Letta), `[missing-top-agentic]`.
- **Temporal versioning / audit-grade:** every fact carries `valid_at / invalid_at / expired_at`; facts are marked invalid, **never deleted**; confidence decays on contradiction/supersession; `recall_as_of(date)` = "what the agent knew at decision time" (first-class for finance/health). `[agents-products]` (MiroFish/Zep), `[agents-stardrift-gordian-wedge]` (Memanto).
- **Retrieval:** RRF (`k=60`) default reranker (pluggable `Reranker`), asymmetric embeddings (source ≠ query), composite scoring (`0.5·semantic + 0.3·recency_decay(30d) + 0.2·importance`, importance computed once at write). `[infra-vector-memory]`, `[external-agentic-products]`.
- **Open format, swappable backend (`‹edge2›`):** markdown/JSON, exportable; `sqlite-vec` (dev, zero-infra default) → `pgvector` (prod) → Mem0/Zep adapters. **Bounded by default** (a budget policy ships with the module — "bounded + curated memory is signal"). `[infra-vector-memory]`, `[fw-claude-sdk-platforms]`.
- A simple **project-context file** (`AGENTS.md`/`VERSO.md` hierarchy, root→cwd merge) is the always-loaded static memory; the typed store is the dynamic layer. `[transcripts-yc]`, `[coding-devin-warp]`.

### 5.5 Evals (`evals/`) — the wedge (first-class, in the box)

No framework ships this; every winning *product* does. `Eval` is a core construct alongside `Agent`/`Tool`/`Memory`.

- **Three tiers:** `eval.unit()` (deterministic assertions in CI, a feature×scenario matrix, sub-minute) → `eval.judge()` (LLM-critique panel + human-alignment review) → `eval.experiment()` (A/B post-ship). The hierarchy is explicit so users know which to reach for. `[evals-reliability]` (Hamel).
- **`agent.define_outcome(rubric, max_iterations=3)`** → bounded generate→grade→revise (never an unbounded `while True`). `[research-deepresearch]` (Anthropic `define_outcome`, default 3 / max 20).
- **Judge panel pluggable, no vendor lock** (Character.AI's Sonnet/GPT/Gemini panel is the *example* default, overridable — hardcoding three vendors would violate the no-single-vendor rule). Post-hoc only, **never in the hot path**. `[agents-character-deep]`.
- **Evals share the production code path (eval == run).** Traces are native and zero-config; eval runs export labeled trace pairs as fine-tuning JSONL. `[training-pipelines]`, `[evals-reliability]`.
- **Reliability surfaced honestly:** `p50_horizon` (capability ceiling) vs `p80_horizon` (production-reliability floor), plus per-step pass rate separate from end-to-end so users find their bottleneck. The eval API nudges users to **declare a verifier**; "no symbolic verifier → weak guarantee" is surfaced, never hidden behind a proxy. `[evals-reliability]`, `[transcripts-stanford-palantir]`.
- **`verify_grounding`** mode: claims tied to retrieved content + a per-claim provenance span — separates retrieval bugs from prompt bugs. `[agents-products]`.

### 5.6 Streaming (`stream/`)

- **One structured event stream** (typed discriminated parts: `message.delta · reasoning.delta · tool.start · tool.result · error · status`), filters as query params, not 7 separate stream modes. Reasoning is a **separate channel** from content. `[fw-langchain-langgraph]`, `[multiagent-grok-heavy]`.
- **True-delta convention, globally** (consumers can buffer; senders can't un-accumulate) — pick one and never invert. `[research-perplexity]` (Perplexity's fatal DX bug). SSE `data: {json}\n\n` + `[DONE]` terminator.
- **Stream normalizer runs before the loop sees provider output** (strip blank text around tool-use, coerce `end_turn`-with-tool-use, repair malformed JSON, classify mid-stream `finish_reason:"error"` chunks — HTTP 200 is sent before the first token). `[external-agentic-products]` (Strands), `[infra-serving]`.
- **Resumable transport:** `seq_id` per frame + cursor replay (`attach?starting_after=N`); decoupled worker so reconnect is safe.

---

## 6. Durable layer, multi-agent, safety, providers (Chunk 3)

> **[Audited 2026-06-05]** Full *target* design; **§13 governs v1 sequencing.** The durable runtime (§6.1) LOCKS the seam in Phase 0 but COMPOSES the engine from DBOS at Phase 2 — default durability is **SYNC**, and the seam mechanism is DBOS/Centaur `ctx.step()` (not Burr). The model layer (§6.4) ships thin in Phase 0; balancer/budget/reasoning-gate move to Phase 2 and **learned routers are rejected for v1**. Multi-agent (§6.2) + Code Mode sandbox are Phase 3.

### 6.1 Durable runtime (`runtime/durable`)

The same loop, executed against a persisted event log.

- **Checkpoint-bracket every step**; durability modes `sync | async | exit`. Crash-resume re-runs from the last checkpoint (completed steps are not re-executed — writes-present = skip). `[fw-langchain-langgraph]` (LangGraph durability), `[coding-conductor]`.
- **HITL is a first-class status, not an exception/callback.** Surface: `answer = await ctx.hitl.request("Approve sending this email?")` — checkpoint-before-pause, resume hours later / a different process. The low-level `interrupt()`/`Command(resume=)` is hidden behind this. `[fw-langchain-langgraph]` (improve #37), `[external-agentic-products]`.
- **`await condition`** declarative suspension (resume on external write / approval / webhook). `[transcripts-stanford-palantir]` (Palantir).
- **Background/long-running jobs:** `submit()` → `{id, status}`; `attach(id, starting_after=N)`; webhook on terminal; `cancel()`. `max_llm_calls` and `max_budget_usd` enforced in this layer. `[research-deepresearch]`, `[infra-model-routing]`.
- **Durable substrate decision (deferred, see §10):** start with a Postgres/SQLite event-log + checkpoint built in-house; keep a clean seam so a Temporal/Trigger.dev-style engine can back it later if needed. `[how-they-did-it]`.

### 6.2 Multi-agent (`orchestrate/`) — opt-in escape hatch, separate import

Single agent + tool parallelism is the default. Multi-agent is never implicit.

- **Sub-agent = context isolation, not org-chart role-play:** offload an expensive sub-task so its tokens don't pollute the parent; the sub-agent returns a **typed compact summary** (file names + line numbers, not raw content). No parent-history inheritance by default (fork modes: `none | last_n | full`). **Depth cap default = 1** (no nested orchestrators). `[context-engineering]` (Dex Horthy), `[research-deepresearch]`, `[fw-claude-sdk-platforms]`.
- **Parallel fan-out:** `fan_out(tasks, max_concurrency=4..6)` — the framework orchestrates concurrency (LLMs are bad at it); synchronize only at dependency boundaries. `[startup-ai-pipelines]`, `[agentic-deep]`.
- **Orchestrator-workers** is the default *durable-layer* multi-agent shape; shared **typed state store** (not message-passing) for coordination. `[agentic-architectures]` (Anthropic +90.2% on breadth-first), `[startup-ai-pipelines]`.
- **Cross-model reviewer hook** ("rubber duck" — a reviewer from a different model family) is the cheapest multi-agent win. `[agentic-deep]`.
- **Explicitly NOT shipped:** adversarial self-play (converges only in 2-player zero-sum), convergence-based termination (use turns ∧ time ∧ tokens), nested orchestrators by default, sub-agents writing the final report. `[multi-agent-ttc]`, `[research-deepresearch]`.
- **Graph escape hatch (`orchestrate/graph`):** `Send`-fan-out + `Command`-routing for *legitimate* map-reduce / explicit backtracking only — never the default.

### 6.3 Safety & hooks (`safety/`)

- **5-stage lifecycle hooks** as the extensibility mechanism (not core-loop edits): `pre_model · post_model · pre_tool · post_tool · on_stop/on_error/on_idle`, async, with `updatedInput`/`updatedToolOutput`. `[fw-langchain-langgraph]` (middleware), `[agentic-deep]` (Claude Code hooks).
- **Permission decision is 4-valued:** `allow | deny | ask | defer`; composable priority-ordered policy layers; session modes `allow_all | ask_every | ask_once` + per-tool override. `[coding-claude-code]`, `[fw-claude-sdk-platforms]`.
- **Confidence router** covers the **full [0,1] range, no dead zone** (the Wedge bug): `high≥0.85 auto / 0.40–0.85 review-queue / <0.40 discard`, append-only audit log. `[agents-stardrift-gordian-wedge]`.
- **Prompt trust hierarchy:** `system > framework_rules(immutable) > agent > user`; security-critical instructions live **only** in immutable `framework_rules`, never in a user-injectable block (the reproducible Perplexity Deep Research vuln). Untrusted tool content tagged `trust_level`; ACL-trim **before** context assembly; `web_fetch` only fetches previously-seen URLs (structural SSRF defense). `[leaked-prompts]`, `[research-deepresearch]`, `[transcripts-bigtech]`.
- **`max_budget_usd` hard cap on by default**; sandbox-first for code execution (`--trust-local` requires an explicit flag). `[agentic-deep]`, `[coding-agents-practice]`.

### 6.4 Model / provider layer (`model/`, `‹edge1›`)

- **Sit above a thin provider abstraction; never re-implement it.** A `ProviderProfile` dataclass with a few polymorphic hooks (`prepare_messages`, `build_extra_body`, `fetch_models`, …) + an `OMIT` three-state sentinel (use-default / strip-field / override). OpenAI request shape is canonical; every other provider is a translation. Plugin discovery (`~/.verso/plugins/model-providers/`) with last-writer-wins, failure-isolated. `[hermes-surfaces]`, `[infra-model-routing]` (LiteLLM's 4-method `Config`, without the 592K-LOC monolith).
- **Routing is per-node config, not global.** `ModelPolicy(provider_order, require_parameters=True, data_collection, max_price, sort, fallback=[...])`. `require_parameters=True` is **critical for tool agents** (a fallback provider that silently drops `tools` returns text instead of a tool call and breaks the loop with no error). `[infra-model-routing]` (OpenRouter).
- **Cross-model failover, not same-model retry** (same-model retry repeats failures): heterogeneous chain (e.g. Sonnet → Gemini → GPT) on outage/rate-limit/malformed-tool-call, plus error-typed fallback lists (context-window vs content-policy vs general). `[coding-devin-warp]`, `[infra-model-routing]`.
- **Role-tiered models:** a cheap `loop_model`, a mid `retry_model`, a reasoning `synthesis_model` used **only** for final synthesis — never default the reasoning tier for every step. A first-class `AuxiliaryClient` (compression/classify/judge) never touches the primary's prompt cache. `[infra-retrieval-tools]`, `[hermes-agent-core]`.
- **Reasoning-effort dial** as a first-class knob (`effort="low|medium|high"` → token mapping; effort is meaningful to users, raw token counts aren't); pass `reasoning_details` back across turns. `[coding-claude-code]`, `[infra-model-routing]`.
- **Retry defaults** (battle-tested, don't invent): exponential backoff + jitter, `attempts=6, initial=4s, max=240s`. Tool-name sanitization (`/`,`.` → `_`) with reverse-map. `[external-agentic-products]`, `[infra-model-routing]`.

---

## 7. Public API surface (the shape users touch)

```python
# --- the 90% path: one agent, a few tools, async ---
from verso import Agent, tool, init_model, Memory, ModelPolicy

@tool  # docstring + type hints → schema; ctx is injected, filtered from the LLM view
async def get_weather(city: str, ctx) -> dict:
    ...  # raise freely — framework wraps to {data, error, ok}

agent = Agent(
    model=init_model("anthropic:claude-sonnet-4-6"),     # "provider:model"
    tools=[get_weather],                                  # native is the default path
    instructions="You are ...",                           # readable/editable, never hidden
    memory=Memory.default(),                              # 4-tier, sqlite-vec dev backend
    max_steps=25,                                         # visible default, not 10007
    model_policy=ModelPolicy(require_parameters=True,     # CRITICAL for tool agents
                             fallback=["openai:gpt-5.1", "google:gemini-3-pro"]),
)

result = await agent.run("weather in Paris?")
# result.output · result.stop_reason (StopReason) · result.usage · result.cost_usd

async for ev in agent.stream("..."):                     # one structured event stream (true-delta)
    ...  # ev.type in {message.delta, reasoning.delta, tool.start, tool.result, status, error}

agent.inspect()                                          # EXACTLY what the model will see

# --- cross the seam: durable / long-running (SAME agent, one flag) ---
handle = await agent.submit("deep task")                 # → {id, status: queued}
async for ev in agent.attach(handle.id, starting_after=last_seq): ...   # reconnect-safe
answer = await ctx.hitl.request("Approve sending this email?")          # checkpoint-backed pause

# --- knobs ---
await agent.run("...", effort="high", verbosity="quick", mode="plan")

# --- memory: typed + tool-callable + audit-grade ---
await agent.memory.remember(type="fact", content="...", confidence=0.9)
await agent.memory.recall(query="...", types=["fact", "preference"], scope="user")
await agent.memory.recall_as_of(query="...", date=...)

# --- evals first-class (post-hoc, never gating the hot path) ---
suite = Evals.from_sessions(agent, last_n=50)
agent.define_outcome(rubric="...", max_iterations=3)     # bounded generate→grade→revise

# --- opt-in multi-agent (separate import; NOT the default) ---
from verso.orchestrate import Orchestration, fan_out
team = Orchestration(lead=agent, workers=[a, b, c], pattern="orchestrator_workers")

# --- hooks (declarative or callable) ---
@agent.hook("pre_tool")
async def gate(req, ctx):
    return "ask" if req.tool.destructive else "allow"

# --- opt-in tool adapters ---
agent.add_tools(mcp_server="...")        # external MCP server (demoted, opt-in)
agent.add_tools(openapi="./spec.yaml")   # import a spec as tools

# --- config-file path for simple stateless agents ---
agent = Agent.from_yaml("agent.yaml")
```

**Surface invariants:** `result.stop_reason` is always a named enum; tool functions raise freely and the framework never lets an exception reach the loop; one model-id format (`provider:model`) and one streaming-delta convention (true-delta) globally; memory is one object with typed entries; routing is per-node config; **single agent is the default and orchestration is an explicit separate import**; evals, resumable streaming, durable HITL and confidence-gating are *in the box*, not bolted on. `Agent()` with sensible args does something useful in ~3 lines (the wedge vs 150 lines of StateGraph).

---

## 8. v1 build phasing (dogfood-order)

The full architecture above is locked now; the **code** lands in phases, each dogfooded on a real agent before the next, so the abstraction cursor is adjusted from use, not paper.

- **Phase 0 — the dogfoodable core.** `core/` (loop, RunContext, AgentResult, events) + `context/` (assembly, budget, KV-cache discipline, inspect, observation-masking compaction) + `tools/` (native `@tool`, dispatch, repair ladder, `think`/`done`) + `model/` (1–2 providers, per-node policy, cross-model failover) + `stream/` (one event stream, true-delta). **Exit:** build a real personal agent on it.
- **Phase 1 — memory + the eval wedge.** `memory/` (sqlite-vec, 4-tier typed, RRF retrieval, recall/remember) + `evals/` (`unit`, `judge` panel, `define_outcome`, native traces) + `safety/` hooks (5-stage). **Exit:** an eval suite drives an iteration on the Phase-0 agent.
- **Phase 2 — the durable seam.** `runtime/durable` (event-sourced checkpoint/resume, `submit/attach`, `ctx.hitl.request`, `await condition`) + `safety/` permissions + confidence router + `max_budget_usd`. **Exit:** the same agent runs a long, crash-resumable, HITL-gated task by flipping `durable=True`.
- **Phase 3 — opt-in scale.** `orchestrate/` (subagent-as-context-isolation, `fan_out`, orchestrator-workers, reviewer hook, graph escape hatch) + tool adapters (`mcp`, `openapi`, deferred loading) + `pgvector` backend + temporal/audit memory. **Exit:** a multi-agent research task; OSS-readiness review.

---

## 9. Success criteria

- **The 3-line wedge holds:** a useful agent (loop + a tool + memory + streaming) in ≤ ~10 lines, vs the StateGraph equivalent.
- **The seam holds:** an agent written tactically runs durably by flipping one flag, with **zero loop-code changes** — proven by a test that runs the identical agent in both runtimes.
- **`agent.inspect()` is honest:** what it prints byte-equals what the model receives.
- **Evals are real:** a feature×scenario `eval.unit()` suite + a judge panel run on Verso's own executor (eval == run), surfacing p50/p80 horizons.
- **Dogfood gate:** at least one of the author's own AI products runs on Verso before any OSS release.
- **Thesis-fidelity:** no graph required for any tactical agent; no MCP required for any tool; no Rust anywhere; the loop file stays < 200 lines.

---

## 10. Resolved decisions (adversarially audited)

These forks were resolved by a 12-agent resolution pass (`research/06_design_resolutions/`) then stress-tested by a 30-agent adversarial panel (`research/07_adversarial/`). The panel could not break a single architecture — every load-bearing claim was re-verified against cloned source — but it found the design **scope-inverted** (it resolved on paper the final form of 8 engines before any agent ran, the exact anti-pattern the thesis forbids). Resolution: **lock every durable schema/interface now; COMPOSE proven engines via `pip install` proxies; build only the non-composable core; defer owned engines to the phase that proves the gap.** The build/compose/defer scope is **§13** (authoritative where it differs from §5/§6). Full per-decision verdicts: `research/07_adversarial/_VERDICT.md`.

1. **Loop cap** — RESOLVED: `max_steps=25` visible + token-budget + single synthetic grace message. ✓ survives.
2. **Schema substrate** — RESOLVED: **Pydantic v2 required** (not optional); single `TypeAdapter(fn)` schema-gen path; v1/v2 dual banned. ✓ survives.
3. **Streaming delta** — RESOLVED: true-delta globally; reasoning filtered before the stop check. ✓ survives.
4. **Multi-agent topology** — DEFER to Phase 3 (per §8): single-agent default; `subagent_delegate`/`fan_out` are thin asyncio wrappers (may land earlier if dogfood asks); `Orchestration(SharedTypedState)` waits until after the Phase-2 durable substrate (no RE source; contradicts the sourced message-passing pattern).
5. **Memory taxonomy** — RESOLVED: 4-tier public enum + internal `EpistemicClass`; extensible. Types locked Phase 0; engine composed/deferred (§13).
6. **Compaction** — RESOLVED: two-pass — LLM-free `prune()` observation-masking (N=10) routine; LLM `compact()` on overflow only; deterministic truncation last-ditch.
7. **Tool-flooding / deferred loading** — DEFER to Phase 3 (per §8): the >20-tools problem doesn't exist for a solo dev writing 5–15 native `@tool`s; keep the Strata 4-stage design as a Phase-3 appendix (add an `inputSchema.properties` branch — Strata's param signal is otherwise dead code for MCP).
8. **Durable substrate** — RESOLVED, **split** (was the biggest call): **(A) LOCK the seam now** — `durable=True` selects a `CheckpointBackend` via `RunContext` polymorphism; loop source identical; the `async with ctx.step()` block holds ONLY the single call + assignment (side effects inside are skipped on durable resume). Correct citation: DBOS `_core.py` / Centaur `workflow_engine.py:338-435` (NOT Burr — it checkpoints at the action boundary). **(B) COMPOSE the engine** = `pip install dbos` behind the interface (DBOS's `workflow_status`+`operation_outputs` IS this schema); build the bespoke 5-table engine only if dogfood names DBOS friction. **(C) Default durability = SYNC, not ASYNC** (ASYNC re-fires LLM calls on crash → divergent result → corrupted event log); `@tool(destructive=True)` forces SYNC; `seq` via DB IDENTITY, never `MAX(seq)+1`.
9. **Code Mode sandbox** — DEFER to Phase 3 (per §8): default provider = microsandbox (local libkrun, + a KVM-availability check); E2B/Daytona as opt-in adapters behind one `CodeSandbox` protocol.
10. **HITL surface** — RESOLVED: `await ctx.hitl.request(question, timeout=86400)` is the only public API, over a Resonate-style named Durable Promise; `interrupt()`/`Command(resume=)` stays internal.
11. **Model layer** — RESOLVED (thin core now; advanced routing deferred; **learned routers REJECTED for v1**): Phase 0 builds the thin layer (`ProviderProfile`+`OMIT`, Anthropic/OpenAI/Google, error-typed two-axis failover, `require_parameters` at init, `call_with_retry`, force `include_usage`; `asyncio.Lock`, not `threading.Lock`). DEFER PeakEWMA/P2C balancer + budget-Redis + reasoning gate to Phase 2 (need concurrency/traces to calibrate). REJECT learned routers (RoRF/ConfidenceCascade/KNN) — ConfidenceCascade needs logprobs Anthropic doesn't expose; RoRF needs a calibration corpus that doesn't exist; both violate the §2 "not a router cult" non-goal. Lock a 3-line `LearnedRouter` Protocol only.
12. **Self-improvement** — RESOLVED: ship `on_stop`/`on_idle`/`on_turn_complete` hooks v1; consolidation ("dream") is opt-in, not core.
13. **Judge panel** — RESOLVED: overridable `DEFAULT_JUDGE_PANEL` (model strings as module constants) + `.single(model)` + full custom; never vendor-hardcoded.

**Correctness fixes the panel surfaced (apply regardless of scope):** durable default ASYNC→SYNC; the seam citation is DBOS/Centaur not Burr, and the `ctx.step()` block must hold only the single call/assignment or durable resume silently diverges; `remember()` currently bypasses memory extraction (pick one write model — Mem0 direct-extract); OTel cache attrs need **dot** form (`gen_ai.usage.cache_read.input_tokens`); drop the `RERANKER` span kind (downgrades to SPAN in Langfuse; Verso has no reranker primitive); a reask on a non-idempotent/destructive tool must default `allow_reask=False` (else it can silently rewrite the whole call).

---

## 11. Evidence anchors

- **Thesis verification:** `Verso/research/THESIS_VERIFICATION.md` (3 independent layers; keep-it-simple confirmed as frontier consensus; the absolutes are opinion/prediction).
- **Synthesis briefs:** `Verso/research/01_bad_guide/_SYNTHESIS.md` (8 design principles), `02_core/_SYNTHESIS.md` (ADOPT/OPT-IN/AVOID pattern table), `03_teardowns/_SYNTHESIS.md` (framework gap analysis + first-cut module map + 22 copyable mechanisms + 27 anti-patterns).
- **54 cluster notes** under the three `research/0*/` folders are the per-source evidence trail; bracket tags in this PRD (e.g. `[agentic-architectures]`) name the note each load-bearing default comes from.
- **Founder-OS / GTM layer:** `Verso/research/04_bad_guide_full/` — a 244-source deep index of *The Bad Guide* (`INDEX.md`) + `_SYNTHESIS.md` (15 cross-cutting frameworks, the 3-followers→hunted distribution playbook, taste checklists, the YC/fundraising one-pager, a tuned operating loop, and a Verso-specific GTM). Feeds §12.

---

## 12. Positioning, the demo-able wedge & go-to-market

The design above is *technical*; this section captures the few positioning facts that are genuinely **product requirements**, and points to the full go-to-market playbook. Source: `research/04_bad_guide_full/_SYNTHESIS.md`.

**Counter-position (the one-line moat):** *"We don't force the graph."* LangGraph cannot drop the graph — it's its identity and its installed base — so this is a counter-position an incumbent structurally can't copy (7 Powers). Verso passes the **wrapper test**: a better base model makes the durable layer (context, evals, memory, the seam) *more* valuable, not obsolete.

**The demo-able wedge is a design constraint, not marketing.** Verso must be screenshot-worthy by construction — the aha-moment has to fit in one image or diff. The three launch artifacts are also three design forcing-functions:
- **W1 — the side-by-side:** `Agent(...).run()` in ~10 lines next to the equivalent ~150-line `StateGraph`. → keeps the API tiny on the 90% path (§7).
- **W2 — the one-flag diff:** the `durable=True` change that adds crash-resume + HITL with **zero loop-code changes**. → this IS the seam test in §9; the diff must literally be one line.
- **W3 — `agent.inspect()`** printing exactly what the model sees. → an inherently demo-able transparency surface; treat its output formatting as taste work, not debug dump.

So §9's success criteria (tiny wedge, one-flag seam, honest inspect) double as the launch artifacts — build them to be screenshotted.

**Go-to-market (pointer, not in this PRD's scope):** one channel — X build-in-public + Show HN (where Python engineers fighting LangGraph already are); cold-start = 5–10 named engineers recruited by hand + dogfood-first; build-in-public as the acquisition loop; spiky-POV launch (*"the loop was never the hard part — context and evals are, and every framework buries them"*). Full playbook: `04_bad_guide_full/_SYNTHESIS.md` §2 (distribution) + §6 (Verso GTM).

---

## 13. Revised v1 scope — BUILD vs COMPOSE vs DEFER (adversarially audited)

The load-bearing output of the audit (`research/07_adversarial/_VERDICT.md` §2); **authoritative where it differs from the "build" framing in §5/§6.** Rule: **build the irreducible core + the two non-composable pieces; compose the solved engines behind locked interfaces; defer every owned engine to the phase that proves the gap.** The owned engines are internals the user never touches, so swapping a proxy for an in-house version later is invisible to products built on Verso.

**Phase 0 — dogfoodable tactical core (~6–8 weeks solo) · BUILD, full quality:**
- `core/loop.py` — the <200-line async ReAct loop (StopReason, `max_steps=25` + grace, doom-loop inspector, `AgentResult`).
- `context/` — `RunContext` · `ContextBundle` · KV-cache discipline · hard budget · `prune()` observation-masking · `inspect()` byte-equality. *(The deep differentiator — real, not a stub. LLM `compact()` deferred to "when prune isn't enough.")*
- `tools/` — `@tool`→`TypeAdapter(fn)` · `{data,error,ok}` dispatch that never raises · `ToolError` · repair ladder · `think`/`done`. **Native only — no MCP, no deferred loader.**
- `tools/jsonish.py` + `coerce.py` — the BAML 5-stage waterfall + typed-Flag coercion (**the one engine built in v1 — genuinely non-composable**). **COMPOSE the rest of structured-output from Instructor** (reask + provider mode-map + `Partial[T]`, openai-dep stripped; `allow_reask=False` on non-idempotent tools).
- `model/` — the **thin** layer only (~250 lines): `ProviderProfile`+`OMIT`, 3 providers, error-typed two-axis failover, `require_parameters`, `call_with_retry`, usage. No balancer, no learned routers, no reasoning gate.
- `stream/` — one 7-type true-delta event + normalizer + SSE. *(Resumable `attach()` → Phase 2.)*
- **Exit:** build a real personal agent on it.

**Phase 1 — memory + the eval wedge, as INTERFACES over PROXIES (~3–4 weeks solo):**
- `memory/` — **LOCK** types + `MemoryBackend` interface + DDL. **SHIP** `SqliteVecBackend` (~100 ln) + a `Mem0Backend` adapter (~40–80 ln; Mem0 V3 = the copied ADD-only write policy). No graph/bi-temporal/consolidation yet. Fix `remember()` to use one write model (Mem0 direct-extract).
- `evals/` — **BUILD** `VersoSpan`/`VersoScore` + constants (~80–100 ln), OTel emit (`gen_ai.*`, dot-form cache attrs, no `RERANKER`), and `define_outcome`. **COMPOSE the engine:** self-hosted Langfuse (trace store + online scheduler) + `autoevals`/DeepEval (scorers) + `braintrust.Eval()` (offline CI).
- `safety/hooks.py` — the 5-stage lifecycle hooks.
- **Exit:** an eval suite (through the proxy) drives an iteration on the Phase-0 agent.

**Phase 2 — the seam, proven (the moment of truth):**
- `runtime/` — **LOCK** the seam (`PersisterHook`/`RunContext` polymorphism); back it with **DBOS** behind a minimal `CheckpointBackend`; prove the success criterion (identical agent, one flag, zero loop-code changes); enforce the `ctx.step()` body-contract; **default durability = SYNC**. Build the bespoke engine only if DBOS friction is named.
- `safety/permissions.py` + `confidence.py` + `max_budget_usd` (counter, no Redis); `model/balancer.py` + reasoning gate (now calibratable); resumable `attach()`.
- **Colocated Postgres** is forced here by the seam — install the 5 checkpoint tables only (memory/trace tables join the *same* PG at Phase 3, which is when "you already run PG → memory free" is actually earned). *(pgroonga is a separate install — on stock PG the BM25 arm falls back to tsvector; not "zero new services.")*
- **Exit:** the same agent runs a long, crash-resumable, HITL-gated task via `durable=True`.

**Phase 3+ — opt-in scale (build only what dogfood demanded):** the owned durable engine (if DBOS friction proven), the owned memory engine (Hindsight model: extraction/graph/BM25/bi-temporal/consolidation — if Mem0 gaps proven), the owned eval store (correction-flywheel / `source_span_id` / p50–p80 horizons / `verify_grounding` — if Langfuse gaps proven), MCP + deferred tool-loader, pgvector + graph arm, multi-agent (`subagent_delegate`/`fan_out` first; `Orchestration` after its coordination backend is decided), sandboxes (microsandbox + KVM check). **Each gated on a proven gap, not a paper design.**

---

## 14. v1.1 — Full-source investigation refinements (consolidated, 2026-06-12)

This section **supersedes the five chronological addenda** (the old §14 recheck + §15–§18 per-workflow passes), folding every surviving delta into one deduplicated layer **organized by the section it refines**. It **governs §1–§13 where it differs** (same convention as §13). Provenance: a recheck (`research/08_raw_recheck/`) + a **full 319-source sweep of *The Bad Guide*** across 4 workflows (`research/09_bad_guide_full_raw/` — 310 per-source notes + 23 theme syntheses; ~228 full-text, ~89 transcript-hunted).

**Verdict (whole corpus): the design and the bet held.** No source forced a redesign; the steelman (browser-use "every abstraction is a liability") was rebutted by Cursor (the frontier model *can't* do the latency-critical executor job; the harness's reward flywheel *generates the weights*). "Keep-it-simple, harness-is-the-moat, don't-force-the-graph" is now validated by the full corpus, not a sample. Output: 1 shipped-code gap + a handful of small primitives that earn their place + three numeric/contradiction sharpenings + a sharpened positioning layer + a long RESIST list. Founder-OS / GTM-execution material was **firewalled out of the PRD** to the WF3/WF4 syntheses + `research/04_bad_guide_full`.

### 14.0 — One shipped-code item (Phase 2; intent-verified — *not* a Phase-0 defect)
- **KV-cache: emit the `cache_control` breakpoint.** §5.2 ships byte-stable `stable_prefix` (the durable half — done); the Anthropic provider sets no `cache_control` (`grep -ri cache_control verso/` → 0), so Anthropic caching (not automatic) isn't engaged. Intent check (plan3 + its RECHECK): plan3 deliberately scoped the model-agnostic *discipline* and **explicitly deferred cache-hit telemetry**; §13 keeps the model layer thin until Phase 2. So §5.2's "~10×" is a **scale claim realized in Phase 2**, landing *with* `cache_read_input_tokens` telemetry and the ~4096-token-minimum-prefix caveat. Fix: one `cache_control:{type:"ephemeral"}` on the last stable-prefix block, as a *positioned* breakpoint (next: a moving tail breakpoint).

### 14.1 — §1 (the bet / moat)
- **Forward-framing:** Amodei's *"marginal returns to intelligence"* (the harness is the bottleneck precisely when the model is strong); METR's 207-day doubling (95% CI 166–240) + the 80% horizon lagging the 50% by **4–6×** (the seam closes that gap, robust across the CI); Valenzuela's *"we're not solving agents backwards"* (control-primitives-first).
- **Measured harness lift** (lead positioning with these, not assertions): Vercel v0 **+29pp from the harness, 0 from the model** (64.7%→93.9%); Sierra τ-bench 61%/35% one-shot; Glean 0.9¹⁰≈0.35. **March-of-nines** (tactical≈90%; durable = the higher nines) + **35M× context-density** + the **OS analogy**.
- **Moat layers (stack these):** **schlep-as-moat** (the harness is the canonical AI-engineering schlep the framework-builder culture filters out pre-deliberation — a *psychological* layer atop the incentive one); **feature-vs-structural firewall** (feature moats evaporate — position only on switching-cost-at-the-seam + the eval-corpus network effect); **legibility ceiling** (incumbents get *less* legible as they scale) + status-hierarchy non-transfer; **feature-blackmail immunity** ("small enough to refuse") + **mental-model capture** (the seam becomes how engineers *think* about reliability); **evals are the taboo / forbidden quadrant** (nobody publishes real failure rates → the corpus moat needs an honesty commitment competitors won't make). Reframe the flywheel as a **"behavioral-context repository"** (agents run against Verso's accumulated definition of correct behavior). The **two-layer secret**: technical (loop is commodity) × human (orgs extend-in-place, don't rewrite).
- **Tests/framing:** the **Grossmann/Einstein** test (every moat claim must be the judgment layer, not commoditizable execution); **native-vs-skeuomorphic** as the sharpest one-line counter-position (frameworks mimic how humans *draw* a workflow; Verso matches how agents *run*); "we don't force the graph" promoted to a **named Counter-Positioning power** (incumbents can't un-adopt the graph without breaking their API+story); **problem-selection over feature-differentiation**; cold-start honesty (Verso is **Stage 1**; the flywheel is a Stage-3 asset; the *launch* moat is the seam switching cost). "Models aren't moats; evaluation frameworks are" is now Garry-Tan-attributable (quoting-grade).

### 14.2 — §2 (non-goals)
- **Reframe the register:** non-goals are **evidence-updatable lower-level decisions, NOT identity** (firm in voice, revisable in status — avoids the obstinacy failure). Each non-goal gets a one-line **"why we refused."**
- **Vocabulary:** "Verso ships **knives, not avocado slicers**" (no EmailAgent/SlackAgent bundles); **"no Magic AI input surfaces — explicit affordances everywhere"**; name the anti-pattern **"desiccated simplicity"** (the minimal-API framework that achieved *emptiness instead of essence* — nothing to hold onto at 2am; Verso keeps the essence: the seam, the eval surface, inspect()); **"no pre-packaged eval metrics"** (generic metrics false-pass the bugs that matter — ship the mechanism, refuse the metrics). The **durable flag is a MODE, not an optional checkbox**; the seam is **"governance without a rewrite."** **A2A orchestration is unsolved** → explicitly out of v1; the framework is CLI/API-first.

### 14.3 — §4 (the seam)
- The seam **collapses LangChain's own Framework→Runtime→Harness tiers into one flag** (use their tier vocabulary). The **compaction/handoff document *is* the seam artifact** (the durable checkpoint = the briefing a fresh sub-agent reads). Add a **persisted progress artifact** at the §5.2↔§6.1 boundary (compaction keeps *one run* under budget but doesn't survive a cold start — Anthropic). Invariant: **"every seam is an audited exploit surface."**

### 14.4 — §5.1 (loop)
- **Reinforcement-on-tool-return** [adopt]: tool returns are the primary *dynamic-context injection* site; the `{data,error,ok}` envelope gains an optional `reinforce`/`note` channel; ship a `todo`/echo builtin beside `think`/`done`.
- **Loop-invariant detectors** [adopt]: a `hallucination_loop` detector (hash of identical consecutive action+observation) + first-class typed `max_steps`/`stop_if`; compound-error math (0.95ⁿ → 0.6 @10) in the docs. Add **`scope_exceeded`/`abstain`** to the `StopReason` enum (an honest stop beats a hallucinated completion).
- **Version-tagged scaffolding ratchet** [adopt]: tag any block added to compensate for a model weakness; review at each model bump. The <200-line invariant is a *ratchet*, not a static cap.

### 14.5 — §5.2 (context engineering)
- **Compaction is cache-cost-aware, not count-aware** [CHANGE — the one real contradiction]: masking/editing **unconditionally invalidates the KV cache**; trigger only when projected token savings > cache-miss cost. **Lower the working ceiling from ~75–80% → ~40–50%, framed as *attention budget* (task-tiered)** [CHANGE — numeric]: quality clips early (Horthy ~40%; Huber "drops precipitously at 10K on non-trivial tasks"; Ralph ~147–152K on a 200K model). Expose `context_utilization()` (~40% warn). Dynamic data stays **out** of the static prefix; model explicit/moving cache anchors.
- **`inspect()` returns typed slot metadata** (static/dynamic/active-window families + token counts), not a flat string; open §5.2 with the **one-to-many mechanism**.
- **Retrieval = async concurrent burst + filter-before-rank** [adopt] (8+ parallel queries/round; precision-filter gate *ahead of* RRF). **Tiered RAG** (hardcode predictable paths, retrieve only the tail). **`<think>` is a distinct observation class** (compact aggressively, don't re-feed). Compact/YAML emit for bulky tool output (keep deterministic-JSON for the cached prefix). "Situational awareness over prescriptive instruction." *Lock-defer:* `ContextBundle.from_repo(path, budget)` + stable-facts session snapshot; recombined-(not-hallucinated)-trajectory augmentation.

### 14.6 — §5.3 (tools)
- **ACI (Agent-Computer Interface) as a named concept** [adopt]: the tool definition is a UI for the model; the failure point is *argument extraction* (first fix = simplify the tool, not the prompt); native typed `@tool` is THE path *because* it intercepts that. Tool-doc checklist: examples as a first-class field, enum/constrained params, absolute-path poka-yoke.
- **"Tools must not be agentic" law** [adopt]: never smuggle a second agent behind a tool signature.
- **Reserve a tax-free raw / code-execution escape hatch** [CHANGE — interface only]: `@tool` stays the ergonomic default but is not the *only* door (pull §13's deferred `CodeSandbox`/raw-tool interface forward — the wrapper test on Verso's most-deletable abstraction).
- **Verification-tool pattern + exec-capture** [adopt]: tools whose output is agent-readable pass/fail+why (self-correction); the harness distinguishes "agent claims success" from "harness observed output."

### 14.7 — §5.4 (memory)
- **Store outcome-status on episodic memory** [adopt]: a write-time `outcome: success|failure|abandoned` scalar; **down-weight successes** (they breed lazy pattern-matching; failures reliably help). (Write-time importance is already in §5.4.)
- **Dual-store** [sharpen]: full transcript (the event log) + distilled working memory (projected state) as **two distinct API artifacts**, never merged.
- **Scope correction** [sharpen]: the 4-tier store **pays off only in recurring workflow agents** — a durable-tier concern, OFF for tactical one-shots. **Permissioning/ethical-walls precede multi-agent memory** (a pre-retrieval gate, not a stored property). *Lock-defer:* the `procedural` tier = reusable versioned abstractions (define the empty slot, hold the line vs Voyager); `reflect(trigger_n≈100)` consolidation.

### 14.8 — §5.5 (evals — the wedge)
- **One unified eval+debug surface over the event log** [adopt]: in-loop / observability-driven (no external system); a programmable, domain-overridable trace renderer that shows the **raw context window**; open §5.5 with silent-failure (Karpathy) + evals-as-gradient (BAIR). The **prod==eval context-shape invariant** (evals run the *live loop*, never a simplified path).
- **`eval.from_trace(trace_id)` / failure→test-case capture** [LOCK-DEFER · Phase 1]: a captured production failure *is* a trace → freeze it into the permanent suite (this **is** §1's accreting-corpus moat). A getting-started sanity protocol (overfit-one / input-independent-baseline / "the model should struggle to pass"). `--judge-model <other-provider>` as a one-liner.
- **Verifiability hierarchy** [adopt]: execution-verifiable (compiler/test/schema/DB) **>** bounded LLM-judge **>** open critique. **Eval-gaming threat model** [adopt]: models behave better under eval (randomize framing + holdouts); reward-hack via environment manipulation → support **constraint-satisfaction** outcomes + isolate the grader from the agent's write surface.
- **Reliability is a distribution** [adopt]: report **pass^k** + **per-step** pass rate, aggregate over seeds, length-normalize the judge. Judge↔human alignment = **precision/recall** (not raw agreement); `compare()` returns a **per-case regression list**. *Lock-defer:* simulation fixtures (mock APIs + LLM-simulated user); per-step/PRM hooks; second-half (HITL/stateful) eval mode + a named *tractability-delta* gap.
- **"Poor man's RLHF"** [adopt, thin]: HITL corrections → embedded → retrieved as gold few-shot (user-owned store; Verso trains nothing). Pairs with failure→test-case capture.

### 14.9 — §6.1 (durable runtime)
- **Persisted progress artifact** surfaced at resume (the durable twin of compaction). **Plan-as-HITL-artifact** [adopt]: the human reviews a structured, editable *plan object* before execution (it doubles as the resumable artifact + `define_outcome` anchor). **Checkpoint pins the full config** (model version + system prompt + tool set), not just event state; fast model-rollback is a named failure mode. **Tri-state operating modes** (sync-HITL / autonomous-self-interrupting / headless-CI-with-review) + mid-run self-interrupt. Honest scoping: **checkpoint/resume ≠ continual learning** (distillation is unsolved — a trust signal, not a gap to hide).

### 14.10 — §6.2 (multi-agent)
- **Lead with failure-quarantine + scheduler-offload + context-isolation, not parallelism** [sharpen]; bounded default `spawn` signature: **subset context + subset tools + shorter step budget than parent**; one primitive, not an orchestration layer. **Typed (non-prose) inter-agent return schema** (summary/affected-state/blockers — Hippocratic's "JSON not prose"). Add a **no-graph orchestrator-workers worked example** in plain async Python (the proof of "we don't force the graph"). Name the **reviewer-as-supervisor** pattern (writes single-threaded, extra agents add *intelligence not actions*) + a `persona` knob. **A2A is unsolved → frontier, not v1 scope.** *Lock-defer:* `serialize=True`/`max_parallel` on side-effecting tools; per-sub-agent strategy/model override.

### 14.11 — §6.3 (safety)
- **Sandbox-as-first-class** [adopt — the clearest net-new gap]: model-written code runs in a sandbox, **not the harness's own process**; the **lethal trifecta** (private data + untrusted input + exfiltration) is the scope checklist; blast-radius = the caller's own auth ceiling; strip/escape special tokens at context assembly.
- **Concurrent supervisor / safety-watcher pattern** [adopt]: one *generic* second agent reviews the primary's output post-hoc on a rubric (vertical oversight, distinct from §6.2 quarantine and from a pre-action guardrail; **rubric-scored, not adversarial self-play**) — NOT a trained 22-model constellation.
- Hooks framed as **architectural-decision surfaces** (fire at decision boundaries; write-trust per-action-class), not per-step audit.

### 14.12 — §6.4 (model / provider)
- **Loop-tier selection axis = tool-call quality, not token price** [sharpen]: cheapest-per-token ≠ cheapest-per-task; the reasoning tier defaults to a *distilled* (~32B-class) model, never the cheap loop; role-tiering is **task-shaped, not just size-shaped**. The provider adapter **exposes explicit cache controls/anchors** (lock per-architecture tuning as the provider's problem). Name the **decider/executor split**. Checkpoint pins model version (fast rollback — see §14.9).

### 14.13 — §7 (demo-able wedge + product taste)
- **Re-spec `inspect()`** from "taste surface" → a **data viewer** (Husain's 5 viewer requirements: all context in one place, one-click feedback, open-ended annotation, fast filter/sort, keyboard shortcuts), affordance-bearing, trending toward **direct manipulation** (in-place — you don't leave Python), and the **"agent diff"** surface (*what changed between this run and the last*).
- **The wedge is *epistemic*, not promotional**: it "isolates the force" so the engineer independently echoes a concern they already had; sell **structural confidence**; pass the **Specificity** + **Surprise** tests; add the **NurtureBoss "invisible-bug" demo** (same agent with/without the harness). The wedge is **kindling** — eval/run artifacts are first-class shareable objects; the diff is tweetable.
- **Output-surface taste invariants:** **Frequency × Novelty** ("how does it feel after 200 invocations today?"), **aesthetic integrity = function-appearance coherence**, **"a thousand small decisions no model makes for you"** (deterministic checkpoint key-ordering), **"ask to save only when necessary"** = silent auto-checkpoint, **spell-check-sized** primitives. Activation metric = a **product outcome** (durable cycle in week 1), not stars. The **press-release-sentence feature-admission gate** (a new primitive must fit the current press release without rewriting the premise).

### 14.14 — §12 (positioning)
- **Category + POV** ("the tactical↔durable seam: one agent, one flag, never a rewrite"); ban "-er-than-LangChain" Better-Trap language; the **anti-framework triumvirate** (Anthropic "use the APIs directly" + Chase "we traded power for ease of use" + Ronacher "build your own abstraction") as headline ammo; **embedded in-process evals** vs LangChain's monetize-LangSmith model; the **"why not DSPy"** answer (evals are the gradient, optimization stays in Python); **Helmer 7-Powers test** + switching-costs-at-the-seam.
- **"Harness" is the *internal* word — validate the external one** via JTBD interviews in problem-language (highest-leverage process delta). The competitor is **"doing nothing" / inertia + risk-asymmetry** ("you don't get fired for IBM"; "no decision" ≈ 40% of B2B losses) — position at the **struggling moment**; make switching feel *safer*. Counter-position lines: "kitchen not recipe," "tool-shaped vs app-shaped," "Smooth Sailor vs Tugboat," "what becomes possible if you discard the graph?", "bit-rotting sophistication." **Denominator-compression** (compete on time-to-reliability + effort-to-reliability). **Resolve the positioning canvas before writing copy.** Persona: the **structurally-aware senior/AI engineer** who *discovered the failure by building* (the 50M, not the 5K; not the vibe-coder), evaluating a harness for their **2nd/3rd** production agent; examples read like Python, not PyTorch. **Intellectual-honesty register**, **DX-led organic GTM** (no sales motion, superconsumer-first). Positioning **leads the product by one step, not three**.

### 14.15 — RESIST (anti-overkill — explicitly NOT v1, consolidated across all passes)
A DSPy-style DSL / auto-optimizer (evals are the optimizer, in Python); a LangSmith-style separate eval SaaS **or** a Replit-"Learn" data-flywheel (Verso emits eval signal to the user's own store, owns none — §2); a model-router DSL / learned router / price-optimizer; per-attention-architecture (MLA/GQA/MQA) cache code paths; implementing MIPS/ANN in-framework; an agentic-retrieval backend in §5.4 (Hebbia kept vector — RRF default holds); a Generative-Agents always-on memory stream + reflection daemon by default; Anthropic context-editing as the *default* compaction; a second-LLM output-reformat pass; an A/B subsystem; a per-model logistic calibration backend; Voyager-style skill libraries; the `procedural` tier as a skill-synthesis engine; supervisor *chains* of N models / a trained constellation; adversarial self-play scoring (degenerates outside zero-sum); a director-agent / sleep-time-compute self-improving loop; Replit reversible-FS forking as a primitive; task-specialized *fine-tuned* worker models as a Verso capability; an enterprise knowledge-graph memory topology + RBAC engine in the memory module; building PRMs / intermediate-step graders in v1; an A2A protocol / message-bus / agent-marketplace; a phase/mode state machine on the loop; a per-outcome pricing/metering engine; cloud-data-gravity coupling; synthetic eval/conversation generation; fine-tuning-specific eval tooling; a non-i.i.d. eval mode (reserve the seam); **all GTM-execution apparatus in the PRD** (→ `research/04_bad_guide_full`); feature-first positioning; consumer-viral theater.

### 14.16 — Convergently confirmed (cite, don't change)
harness-is-the-moat is now *consensus* (BAIR/Sequoia/Thompson/a16z — so positioning must win on the *shape*, not the claim); no-graph (6 independent sources incl. 2 non-agent: Sutton's *Bitter Lesson*, HF *Ultra-Scale Playbook*); ReAct loop canonical (Weng); cross-model failover + role-tiered models (production-confirmed by Ronacher); MCP demotion (large catalogs burn context); KV-cache discipline as table-stakes with the production numbers (Character.AI: 95% inter-turn cache, 13.5× cheaper, 180-msg average); append-only log doubles as eval ground truth; the bitter-lesson churn clock (Yao 5%-method vs 30%-generation; METR 207-day CI); §5.5 wedge is *under-sold, not mis-chosen* (Ronacher: evals are "the hardest problem"; Yao: "evaluation becomes more important than training") — with *agentic trajectory eval* flagged as the open frontier Verso must not claim to have closed; §13's COMPOSE-don't-build validated.

---

*(Historical note — the original §14 recheck intro, preserved for provenance:) Before opening Phase 1, the **full raw sources** behind *The Bad Guide* CTO + AI sections were read (not the harvest summaries), focused on the **"2026 additions"** added after the 2026-06-04/05 research pass. Four parallel read-only workers, one dedicated to steelmanning the case *against* a framework. Evidence + verbatim quotes: `research/08_raw_recheck/` (`_RECHECK_REPORT.md` + 4 cluster notes).*

---

*PRD v1.1 — design locked, adversarially audited (12-agent resolution + 30-agent panel), **Phase 0 shipped, raw-source rechecked + full-source-investigated (all 319 Bad Guide sources across 4 workflows — design + bet held)**. §10/§12/§13 added 2026-06-05; **§14 (2026-06-12) consolidates the recheck + the 4-workflow investigation into one by-section refinement layer and supersedes the former chronological §15–§18.** Next: `writing-plans` for Phase 1 (memory + the eval wedge), folding in §14.7 (memory) + §14.8 (evals) + §14.5 (context).*

