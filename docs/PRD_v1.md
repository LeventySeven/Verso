# Verso — Product Requirements Document (v1)

**Status:** Draft v1 (design locked, pre-implementation)
**Date:** 2026-06-04
**Owner:** Slava (@Seventydotleven)
**Grounding:** the verified "keep-it-simple" thesis (`Verso/research/THESIS_VERIFICATION.md`) + 28,496 lines of reverse-engineered harvest across 54 source notes and 3 synthesis briefs (`Verso/research/01_bad_guide/`, `02_core/`, `03_teardowns/`). Every default in this PRD traces to that evidence; load-bearing ones cite the source note in brackets, e.g. `[agentic-architectures]`.

---

## 0. TL;DR

Verso is a **Python agent framework** whose primitive is *the boring core done right*: one clean async ReAct loop, with the two things every other framework buries made first-class — **context engineering** and **evals + reliability**. Its organizing idea is the **tactical↔durable seam**: the same agent runs ephemeral-and-simple by default and is *promoted* to durable (event-sourced, checkpoint-resume, human-in-the-loop) with one flag — never a rewrite, never a forced graph. The one-sentence pitch, and the counter-position to LangGraph/CrewAI: **"we don't force the graph."**

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

## 10. Deferred / open decisions (with chosen v1 defaults)

These are the harvest's genuine forks. v1 picks a default and moves; each is revisited after dogfooding.

1. **Loop cap:** `max_steps=25` visible default + token-budget safety net + grace call. (vs Codex's no-cap.)
2. **Schema substrate:** type-hints → schema natively; Pydantic v2 *optional*, never v1/v2 dual.
3. **Streaming delta:** true-delta globally.
4. **Multi-agent default topology:** single-agent default; orchestrator-workers + fan-out as the opt-in shapes; **instrument before recommending either** (evidence genuinely conflicts: Anthropic +90.2% vs Agent-S3 +13% from removing the hierarchy).
5. **Memory taxonomy depth:** 4-tier default, extensible enum (not Memanto's fixed 13).
6. **Compaction model:** observation-masking default; same-model summarize fallback; thread-handoff exposed.
7. **Tool-flooding strategy:** deferred loading default; meta-tool router available for very large sources.
8. **Durable substrate:** in-house Postgres/SQLite event-log + checkpoint for v1; clean seam to adopt Temporal/Trigger.dev later. *(Biggest deferred infra call.)*
9. **Code-execution escape hatch (Code Mode):** deferred to ≥ Phase 3; sandbox provider TBD (E2B/Modal/V8 isolate).
10. **HITL surface:** high-level `await ctx.hitl.request()` is the API; `Command(resume=)` stays internal.
11. **Provider-quirk line:** core ships clean adapters for the top providers; deep quirk accumulation pushed to per-provider plugins.
12. **Self-improvement:** ship `on_turn_complete`/`on_idle` hooks in v1; a built-in consolidation primitive is opt-in, not core.
13. **Judge panel:** ship an overridable example panel config; never hardcode a single vendor.

---

## 11. Evidence anchors

- **Thesis verification:** `Verso/research/THESIS_VERIFICATION.md` (3 independent layers; keep-it-simple confirmed as frontier consensus; the absolutes are opinion/prediction).
- **Synthesis briefs:** `Verso/research/01_bad_guide/_SYNTHESIS.md` (8 design principles), `02_core/_SYNTHESIS.md` (ADOPT/OPT-IN/AVOID pattern table), `03_teardowns/_SYNTHESIS.md` (framework gap analysis + first-cut module map + 22 copyable mechanisms + 27 anti-patterns).
- **54 cluster notes** under the three `research/0*/` folders are the per-source evidence trail; bracket tags in this PRD (e.g. `[agentic-architectures]`) name the note each load-bearing default comes from.

---

*PRD v1 — design locked, implementation pending. Next: per-step implementation plan (writing-plans), then Phase 0 build.*
