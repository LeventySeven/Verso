# Verso — The Steelman for COMPOSE-not-BUILD

**Status:** Adversarial brief. The strongest honest case for the *opposite* architecture.
**Date:** 2026-06-05
**Stance:** This document deliberately argues against the locked `06_design_resolutions/_RESOLUTIONS.md`, which chose BUILD on nearly every subsystem. It is not a recommendation; it is the case the BUILD decision must be able to beat. If BUILD survives this, it is justified. If it doesn't, the resolutions are wrong.
**Inputs:** `docs/PRD_v1.md`, `06_design_resolutions/_RESOLUTIONS.md`, the 12 subsystem notes, and the source-level teardowns in `03_teardowns/` (every candidate library below was cloned and read at file:line — citations live in those notes).

Label key: **OWN** = Verso writes and controls this code. **DELEGATE** = a third-party library does the work behind a Verso seam. **HYBRID** = Verso owns a thin layer, the library does the heavy lifting.

---

## 0. The thesis, restated as an attack

The PRD's own founding claim (`PRD_v1.md §1`, §2; `THESIS_VERIFICATION.md §7`) is:

> "Teams over-engineer around *transient* model limitations and call it architecture." … "The right abstraction cursor **cannot be found on paper — only by using the thing.**"

The resolutions then turn around and design, *on paper, before a single dogfood agent has run*:

- a 5-table durable execution engine with lease management, fencing, a 100-attempt poison-pill, two-log split, Resonate named-promise HITL, and 3 durability modes (`runtime/durable/*`);
- a 4-backend memory cognition layer (sqlite-vec / Hindsight-Postgres / Qdrant / Graphiti-Neo4j) with bi-temporal columns, a `memory_links` graph-without-a-graph-DB, surprisal-gated dream consolidation, and a 4-arm hybrid retriever (`memory/*`);
- a full eval/trace store with `VersoSpan` 10-kind taxonomy, `dotted_order` tree keys, online/offline `EvalJob` engine, judge panels, and bidirectional `gen_ai.*`↔OpenInference mapping (`evals/*`);
- a 5-stage jsonish parser + typed-Flag coercion cost function + reask loop (`tools/jsonish.py`, `coerce.py`, `structured_output.py`);
- a model edge with PeakEWMA+P2C load-balancing, two-axis error-typed failover, budget guard, and learned routers (`model/*`);
- a fastmcp-cloned schema generator + 5-meta-tool deferred loader + MCP client/server (`tools/*`);
- a `CodeSandbox` protocol with microsandbox/E2B/Daytona adapters + credential proxy (`orchestrate/sandbox.py`, `safety/credential_proxy.py`).

**That is the scope of a multi-engineer, multi-quarter platform.** The single durable-runtime resolution document is 801 lines with *seven admitted Open Unknowns* inside a doc titled "RESOLVED." Seven unresolved unknowns in a resolved design is not completeness — it is evidence the design outran the evidence. The `06` resolutions are the *exact* anti-pattern the thesis names: architecture discovered by re-reading other people's source code (DBOS's `_core.py`, Langfuse's ClickHouse schema, Mem0's `ADDITIVE_EXTRACTION_PROMPT`, Instructor's `retry.py`) instead of by running one's own agent.

The composition counter-thesis is one sentence:

> **Verso's actual moat is the loop, the seam, the `@tool` ergonomics, the context assembly, and the unified API. Everything below those is a solved engine that the ecosystem has already built, source-verified in our own teardowns, and `pip install`-ready. Verso should be ~2–3k LOC that *composes* those engines, and spend 100% of its scarce design budget on the five things no library gives you.**

The teardowns themselves keep pointing here. Every infra note's "For Verso" section recommends *adopting the shape* of a library (the DBOS two-table schema, the Langfuse score shape, the RRF k-algebra, the fastmcp `TypeAdapter(fn)` path). The resolutions then took "adopt the shape" and silently upgraded it to "reimplement the engine that produces the shape." The steelman says: if the shape is right *and the engine is `pip install`-able and source-clean*, **import the engine, keep the shape for free, and write none of it.**

---

## 1. What Verso OWNS no matter what (the irreducible core — ~2–3k LOC)

These five are the things *no* library in any teardown ships, and they are exactly what the PRD identifies as the wedge. Compose-not-build does **not** weaken these — it concentrates the entire engineering budget on them.

| Owned primitive | Why no library has it | Approx LOC |
|---|---|---|
| **The loop** (`core/loop.py`) | Every framework either buries it (LangGraph Pregel, LangChain LCEL), hides it in a binary (Claude SDK), or monolith-bloats it (Letta 2,134 / Hermes 3,600). A clean <200-line async ReAct loop with a named `StopReason` enum, LIFO part-queue dispatch, grace-call-on-budget, and stuck detection is *the product surface*. | ~200 |
| **The seam** (`runtime/tactical.py` + the `durable=True` flag) | "Same loop, in-memory by default, durable by one flag, zero loop-code changes" is the counter-position. No library offers it because each *is* one side of the seam (DBOS = always durable; bare async = never). Verso owns the **adapter boundary** that makes the same loop run against either runtime. | ~150 |
| **`@tool` ergonomics** (`tools/decorator.py`) | The decorator that turns a plain async Python fn + docstring + type hints into a registered, schema'd, policy-tagged tool — and the `{data, error, ok}` envelope contract that means "tools raise freely, the loop never sees an exception." The *schema generation* can be delegated; the *ergonomic contract* is Verso's. | ~150 |
| **Context assembly** (`context/bundle.py`, `kvcache.py`, `inspector.py`) | `ContextBundle` as a named, inspectable object; `agent.inspect()` byte-equality; KV-cache stable-prefix discipline; budget-as-hard-constraint. This is the "deep differentiator" (`PRD §5.2`) and it is glue *between* the delegated parts (memory recall, tool schemas, history) — inherently Verso-owned because it is the integration point. | ~400 |
| **The unified API** (`verso/__init__.py`, `Agent`) | One `Agent(...)` surface; `provider:model` strings; one streaming-delta convention; one HITL API; one `Memory` object. This is the taste layer the PRD is built around. It is *thin glue over delegated engines* — which is precisely the composition argument. | ~300 |

Add the streaming normalizer (~150), hooks/permissions wiring (~200), and the model-id parsing + config plumbing (~200), and the irreducible Verso is **~2,000–2,500 LOC of orchestration**. Everything in §2 below is what that glue *calls into* instead of reimplementing.

The PRD's wrapper test — *"a better base model makes the durable layer more valuable, not obsolete"* — passes identically whether the durable layer is Verso-built or DBOS-composed. Composition does not fail the wrapper test. It only changes *who maintains the plumbing.*

---

## 2. Per-subsystem: exactly what Verso delegates vs keeps

For each subsystem: the candidate library, the precise seam, what Verso still OWNS, what it DELEGATEs, and the source evidence the library is real and clean.

### 2.1 Durable runtime → **DBOS** (`pip install dbos`)

**The seam Verso owns:** `agent.run(task)` vs `agent.run(task, durable=True)`. In tactical mode the loop runs in-memory. In durable mode, Verso wraps each loop step in `@DBOS.step()` and the whole run in `@DBOS.workflow()`. The `durable=True` flag selects which wrapper set is applied. That is the entire seam — ~4 lines per the Burr `PersisterHook` model the resolutions themselves cite (`api-and-peers §1`: "the entire seam is one 4-line class").

**What Verso DELEGATEs to DBOS:**
- The two-table schema. The resolutions' `verso_runs` + `verso_step_outputs` *is* `dbos.workflow_status` + `dbos.operation_outputs` — source-confirmed verbatim in `infra-durable-execution.md:180–202`, and the resolution doc *admits this* (`durable-runtime.md:22`: "the entire durable engine is Python + Postgres … no server needed").
- Step memoization (re-enter, skip completed by key, run forward to first miss) — the exact "Family B" model the teardown says is correct for a non-deterministic ReAct loop (`infra-durable-execution.md:1117`).
- `startup_recovery_thread`, `MAX_RECOVERY_ATTEMPTS=100`, `executor_id` ownership filter, `SetWorkflowID` idempotency, `fork_workflow(id, start_step)` restart-from-step, `@DBOS.scheduled(cron)` — *every constant the resolutions hard-code is already DBOS's, already production, already tested* (`_recovery.py:26`, `_registrations.py:10`, `_context.py:169`, `_scheduler.py:25`).
- HITL: `DBOS.recv(topic, timeout)` + `DBOS.send(dest, msg, topic)` is a working durable pause/resume *today*. It is the universal HITL primitive the teardown identifies (`infra-durable-execution.md:1140`: "all the same primitive … an opaque external identifier the run yields on").
- Worker release on wait, write-before-advance, `DBOSClient` out-of-process control API (`list_workflows`/`retrieve_workflow`/`fork_workflow`) — which Verso's Phase-0 build would *not even have*.

**What Verso must accept it loses (honest):** DBOS uses *call-order ordinal* step ids (`function_id`), not Inngest's content-addressed `sha1(name):n`. Ordinals break if the developer *reorders* steps between runs. Resonate's named HTTP-resolvable promise (clean external resolvers like Slack/webhooks) is not DBOS's `recv` model. The 3 durability modes collapse to DBOS's sync-ish default. **None of these matter for a solo dogfooding builder** (you control your own loop order; your HITL resolver is you). Each is a localized 1–2 day swap *later*, behind the same seam, *if the pain is real* — which is the thesis's whole point.

**Library is real and clean:** `dbos-transact-py`, pure Python + Postgres, no orchestration server, no Rust binary. Cloned and read at `infra-durable-execution.md:161–276`.

**Verdict driver:** building a second worker-queue-management layer (the resolution's `CheckpointBackend` ABC has *11* methods vs LangGraph's 5; the extra 6 are lease/claim/recover — pure worker-queue plumbing) before running one agent is the textbook "non-bottleneck dependency written before the bottleneck is known."

---

### 2.2 Memory → **Mem0** (default) / **Zep** (audit tier) (`pip install mem0ai` / `zep-python`)

**The seam Verso owns:** the one `Memory` object with `remember / recall / recall_as_of` as *tool calls* the LLM can invoke (memory-as-tool-calls, observable), the 4-tier public type enum, the scope-key injection (`user_id/agent_id/run_id`), and the working-set FIFO that lives in the context window. That ergonomic + the *placement in the loop* (search-before-turn, write-after-turn-async) is Verso's.

**What Verso DELEGATEs:**
- To **Mem0**: the entire extract→ADD-only→dedup→entity-link write loop (1 LLM call/turn, md5 dedup, `linked_ids`), the composable `user_id ∧ agent_id ∧ run_id` scoping (which the memory note *already recommends Verso adopt as its default* — `memory-systems.md:968`), and the additive `semantic + bm25_sigmoid + entity_boost` fusion. The teardown's convergent verdict (`memory-systems.md:934`) — "additive + invalidate/version, never hard-delete" — *is Mem0 V3's default behavior*. Verso would be reimplementing Mem0 to get Mem0's answer.
- To **Zep/Graphiti**: the bi-temporal `valid_at/invalid_at/expired_at` edges and `recall_as_of(date)` audit-grade time-travel. The resolutions' own `GraphitiBackend` audit tier *is Graphiti*. `agents-products §10` documents Zep's temporal model as the reference; the resolution copies its semantics into hand-rolled Postgres bi-temporal columns for no stated reason except "one less service."

**What Verso must accept it loses (honest):** the "one colocated Postgres" elegance (`RESOLUTIONS §0`) — Mem0 wants its own store; Zep is a service. You trade "memory + checkpoints + traces in one DB" for "import a memory engine." That is a *real* cohesion loss (see §3.1). You also accept Mem0's opinionated taxonomy over Verso's 4-tier+EpistemicClass design. **But** the colocation argument is itself a BUILD justification, not a user-felt benefit: a solo builder does not care whether memories and checkpoints share a Postgres instance; they care that recall works and writes don't block the turn (which both libraries already guarantee — async daemon-thread add).

**Library is real and clean:** Mem0 (`mem0ai`) and Zep both source-read across `memory-systems.md` (write-loop spectrum table line 924, embedding/NER table line 938). Both pluggable-backend by design — exactly the `MemoryBackend` interface the resolution wants to *define*, which Mem0 *already exposes*.

---

### 2.3 Eval / trace → **Langfuse** (trace+online judge) / **Phoenix** (eval+OpenInference) (self-host both; `pip install langfuse` / `arize-phoenix`)

**The seam Verso owns:** `eval.unit()` / `eval.judge()` / `eval.experiment()` as the three-tier API; `define_outcome(rubric, max_iterations=3)` bounded revise; "eval == run" (evals execute through the same loop). The *judge-panel ergonomic* and the *bounded generate→grade→revise loop* are Verso's. The trace *emission* is delegated.

**What Verso DELEGATEs:**
- The trace store, span tree, score table, and online-eval scheduler to **Langfuse** (Postgres OLTP + ClickHouse OLAP, async LLM-judge via `JobExecution` + delayed queue — `eval-observability.md:14`, "the cleanest readable implementation of 'score every production trace without blocking the agent'"). The resolution's `VersoSpan`/`VersoScore`/`dotted_order`/online `EvalJob` engine is a *reimplementation of Langfuse's data model* — and the teardown literally says (`eval-observability.md:569`) "one score shape … accepted by Langfuse/Phoenix/Opik/MLflow/LangSmith **with field renames only. No per-backend adapter.**" If the shape is portable across all of them, *emit the shape and use one of them as the store.*
- The metric suite + eval attachment to **Phoenix/OpenInference**: Faithfulness, Factuality A–E, G-Eval, ToolCorrectness, trajectory assertions are *already implemented* in DeepEval/RAGAS/autoevals/Phoenix. The resolution's "built-in scorer suite" is a port of these.
- **The killer composition fact** (`eval-observability.md:267–269`): OpenInference ships **~33 auto-instrumentation packages** (`openinference-instrumentation-{openai,anthropic,litellm,mcp,instructor,...}`) that monkey-patch via `wrapt`. **If Verso emits OTLP, every library it composes — LiteLLM, Instructor, fastmcp, Mem0 — is already correctly traced with zero Verso code.** Composition *makes the eval layer easier*, because the things being traced are off-the-shelf and already instrumented. Building everything in-house *forfeits* 33 free instrumentors.

**What Verso must accept it loses (honest):** "traces are native and zero-config, in the box" becomes "traces are native if you point at a Langfuse/Phoenix instance." That is a real DX downgrade for the absolute-zero-infra dev tier — but Phoenix runs in-process and Langfuse self-hosts on the *same Postgres* the durable layer would use; the SQLite dev tier can emit OTLP to a local Phoenix. The wedge ("evals first-class") is about the *API and the eval==run seam*, both of which Verso keeps.

**Verdict driver:** the eval-store reimplementation is the *least* defensible BUILD in the whole resolution set, because the teardown explicitly proves the score shape is universal and 33 free instrumentors exist. This is pure NIH.

---

### 2.4 Structured output → **Instructor** (`pip install instructor`)

**The seam Verso owns:** the 3 semantic format intents (`strict`/`tool`/`json`) exposed to the caller, with the adapter owning the fallback ladder (Mirascope's clean surface — `structured-output.md:347`). The *caller ergonomic* is Verso's.

**What Verso DELEGATEs to Instructor:**
- The `Mode` enum — the authoritative, maintained, per-provider map of which structured-output wire API each provider supports (`structured-output.md:112`). This map *changes every time a provider ships a feature*; maintaining it in-house is a permanent tax.
- The reask retry loop that feeds the Pydantic `ValidationError` back to the model, with `InstructorRetryException` carrying `last_completion / n_attempts / total_usage / failed_attempts` — exactly the per-attempt observability the resolution wants to build (`structured-output.md:128,141`).
- The `Partial[T]` streaming construct-not-validate path (`structured-output.md:153`) — Instructor and Mirascope share the *same* `silviumarcu` lineage; the resolution's `model_construct`-until-root-closes is that code.

**What Verso must accept it loses (honest):** BAML's *jsonish 5-stage waterfall* and the *typed-Flag edit-cost coercion* (the resolution's chosen `tools/jsonish.py` + `coerce.py`) are **more powerful** than Instructor's parse-then-reask — BAML repairs malformed syntax *without* a model round-trip, where Instructor always pays a reask. So here the BUILD has a genuine quality argument: BAML-style SAP saves tokens/latency on malformed output. **But** BAML is itself a library (`pip install baml-py`), and the honest HYBRID is: delegate the reask loop + mode map to Instructor, and *optionally* compose BAML's parser for the no-reask fast path — not hand-write either. Writing the jsonish waterfall from scratch (the resolution's plan) is reimplementing BAML for no reason BAML doesn't already serve.

---

### 2.5 Model routing → **LiteLLM** (`pip install litellm`)

**The seam Verso owns:** `ModelPolicy(require_parameters=True, fallback=[...])` as *per-node config* (not global), the `provider:model` string format, and the *agent-critical* `require_parameters=True` enforcement at `Agent.__init__` (a fallback provider that silently drops `tools` returns text and breaks the loop — the single hardest-won routing finding, `infra-model-routing` OpenRouter). That policy *surface* is Verso's; the provider translation is delegated.

**What Verso DELEGATEs to LiteLLM:**
- 100+ provider translations (OpenAI shape canonical, every other provider a translation) — the `ProviderProfile` + 5-hooks the resolution designs is *LiteLLM's 4-method `Config`* (`get_supported_openai_params` / `map_openai_params` / `transform_request` / `transform_response`).
- Error-typed fallback chains (`context_window_fallbacks` / `content_policy_fallbacks` / general `fallbacks`) — the resolution's "two-axis error-typed failover" is LiteLLM's feature.
- `max_iterations_limiter` per session, `dynamic_rate_limiter`, tool-name sanitization (`/`,`.`→`_` with reverse map), `DualCache`, cost accounting via `INCRBYFLOAT` — all LiteLLM, all source-read.

**What Verso must accept it loses (honest):** the resolution's reason to *not* use LiteLLM is the synthesis's "592K-LOC monolith" line (`_SYNTHESIS.md §1.4`). That is the real tension — LiteLLM is a heavy, sprawling dependency, and the `OMIT` 3-state sentinel beats LiteLLM's global `drop_params`. PeakEWMA+P2C load-balancing and learned routers (`model-gateways §1,2`) are genuinely *not* LiteLLM's strength. So routing is the **strongest BUILD case** of the seven: the surface is small, the quirks are the moat (`hermes-surfaces §1` — Hermes' `anthropic_adapter.py` is 2,273 lines of hard-won quirks), and a thin `ProviderProfile` over the *raw provider SDKs* avoids the monolith. **The honest composition answer here is HYBRID:** use LiteLLM as the *translation+failover engine* behind the `ProviderProfile` seam (so you don't maintain 100 provider dialects), but keep the `OMIT` sentinel and per-node policy as Verso's thin wrapper. Do not hand-write the 100-provider translation table.

---

### 2.6 Tools / MCP → **fastmcp** (`pip install fastmcp`)

**The seam Verso owns:** the `@tool` decorator ergonomic, the `{data, error, ok}` envelope, the policy tags (`read_only`/`destructive`/`idempotent` → permission routing for free), the input-repair ladder, and the dispatch contract (parallel reads, sequential writes, order preservation). The *tool ergonomic and dispatch* are the heart of the product and stay Verso-owned.

**What Verso DELEGATEs to fastmcp:**
- Schema generation: the resolution's chosen path *is* `pydantic.TypeAdapter(fn).json_schema()` + the 6 compression transforms — and the teardown says (`infra-tools-mcp.md:639`) **"port fastmcp verbatim."** "Port verbatim" is composition with extra steps. Just import fastmcp's `function_parsing.py` path.
- The MCP client + server (every Verso agent both produces and consumes MCP) — fastmcp is the reference MCP implementation; reimplementing the 2025-11-25 protocol client/server is gratuitous.
- `ctx.elicit` (in-loop input elicitation, accept/decline/cancel) — fastmcp ships it.

**What Verso must accept it loses (honest):** fastmcp explicitly left the `@tool(on_error=…)` error model open (`infra-tools-mcp.md:658`, issue #2882) — so the structured `ToolError{kind, can_retry, retry_after_ms, prompt_content}` (Arcade-derived) and the deferred-loading 5-meta-tool BM25+ loader are *genuinely Verso additions on top of fastmcp*, not in any library. That is the correct HYBRID line: **delegate schema-gen + MCP protocol to fastmcp; OWN the error envelope, the dispatch parallelism contract, and the deferred loader.** The resolution's mistake is reimplementing the schema-gen ("port verbatim") instead of importing it.

---

### 2.7 Sandbox → **microsandbox** (local default) / **E2B** (cloud) (`pip install microsandbox` / `e2b`)

**The seam Verso owns:** the `CodeSandbox` protocol (`snapshot()` / `resume()` / `exec()` / `code_run()→{exit_code, stdout, artifacts}`) and the deny-all-egress + credential-proxy *policy* (agent holds no secret). The protocol and policy are Verso's; the VM/container is delegated.

**What Verso DELEGATEs:** literally everything inside the box. microsandbox is a self-contained `pip install` (`microsandbox==0.5.4` bundles the `msb` binary, libkrun microVM, <100ms boot, no daemon — `infra-sandboxes-multiagent.md:238`). E2B/Daytona are the cloud/container adapters. The resolution *already* says "default = microsandbox, E2B/Daytona opt-in" — so this subsystem is **already a compose decision.** There is nothing to BUILD here except the protocol shim, which is correct.

**What Verso must accept it loses (honest):** nothing material. The credential proxy (`HttpSecret` host-scoped egress) is the only owned piece and it's correctly owned (security boundary). This subsystem is the proof that compose-not-build is *already* the resolution's answer when the engine is genuinely hard (a hypervisor) — which raises the question the steelman presses: *why is a hypervisor "obviously compose" but a Postgres step-memoization loop "obviously build"?* The honesty cut is that durable-execution **feels** buildable (it's "just Postgres + a loop") and a microVM doesn't. "Feels buildable" is precisely the trap the thesis warns about.

---

## 3. What Verso HONESTLY LOSES with compose-not-build

The steelman is not complete without its own strongest counter-arguments. These are real and some are load-bearing.

### 3.1 Cross-layer cohesion — the colocated-Postgres story dies

The single most elegant idea in `06` is `§0`: **one Postgres holds checkpoints + memory + traces; the user who paid the "run Postgres" cost gets all three free.** Compose-not-build *shatters* this: DBOS has its schema, Mem0 wants its store, Langfuse needs Postgres+ClickHouse, Phoenix its own. You go from *one* migration runner + `CREATE EXTENSION vector` to *N* services each with its own ops surface. For a solo builder this is a real regression: "zero-infra dev tier" (one SQLite file) becomes "run 3–4 dockerized services." This is the strongest single argument *against* the steelman, and it is genuine.

*Steelman rebuttal:* the cohesion is a BUILD-side benefit, not a user-felt feature. It optimizes the operator's bill of materials, not the agent's behavior. And it is recoverable: Phoenix runs in-process; DBOS and Langfuse can target the same Postgres; the dev tier can be SQLite + in-process Phoenix. You lose the *single-instance* elegance, not the zero-infra-dev experience.

### 3.2 The seam-across-checkpoint+memory+trace

Verso's deepest design idea is that the *same event* threads through the durable checkpoint, the memory write, and the trace span — one append, three consumers. If those are three vendored engines with three event models, Verso has to *fan one logical step-event out into three foreign schemas* and keep them consistent. The "one event, byte-identical across runtimes and stores" invariant gets harder, not easier. A crash mid-fan-out can leave the checkpoint advanced but the trace missing. **A built stack can make step-commit, memory-write, and trace-emit a single transaction; a composed stack cannot** (DBOS's transaction-piggyback works for *its* tables, not Mem0's). This is the most technically serious loss.

*Steelman rebuttal:* trace emission is allowed to be best-effort (it's observability, not state); memory writes are already async-off-the-request-path in *every* system (`memory-systems.md:953` — "never consolidate on the request path"), so they are *intentionally* not in the step transaction. Only the checkpoint must be transactional, and that's DBOS's job alone. The "one transaction across three engines" ideal is mostly a phantom requirement.

### 3.3 The moat argument weakens

The PRD's defensibility story (`§1`, §12) is the *accreting* memory + eval corpus + tool registry as process-power, plus a cleaner loop as differentiation. If memory is Mem0, evals are Langfuse, and routing is LiteLLM, the accreting-corpus moat now lives partly in *other people's data models* and the "we built the engines" narrative evaporates. What's left is "we have good taste in glue" — which is real (cf. Vercel, Cursor) but is a *thinner* moat than "we own the four buried primitives." An incumbent could compose the same libraries.

*Steelman rebuttal:* the moat was never the engines. LangGraph's moat is the 700-integration installed base, not Pregel; Cursor's moat is taste + distribution, not a model. The PRD's own wrapper test says the durable layer is valuable *because models improve* — that's true of composed plumbing too. And "we don't force the graph" (the actual counter-position) is an *API-shape* claim, fully owned regardless of what's underneath.

### 3.4 Dependency / version risk + the "complexity budget"

Composing 7 libraries means 7 release cadences, 7 transitive-dependency trees (LiteLLM alone drags a huge tree; Langfuse pulls ClickHouse drivers), 7 potential breaking changes, and version-conflict hell (Pydantic v1/v2 across deps is the exact bug-farm the PRD bans — `PRD §5.3`). The teardown's own anti-pattern #24 (`_SYNTHESIS.md`) warns: *vendor count > 12 → `0.999^12 ≈ 98.8%` per run → >30%/month failure*. Composition *raises* the vendor count it warns against. A built core has *one* dependency tree Verso controls.

*Steelman rebuttal:* this is the strongest pragmatic objection and it bounds *how many* to compose. It argues for HYBRID (compose the 2–3 hardest engines, build the rest) rather than compose-everything. It does **not** rescue building DBOS/Langfuse/microsandbox from scratch, because those are the ones where the build cost dwarfs the dependency cost.

### 3.5 "We don't force the graph" purity

A subtle loss: some composed engines *do* impose a model. LangGraph-as-memory-store would smuggle the graph back in; Temporal-as-durable would reintroduce the workflow/activity split the PRD rejects. The steelman's chosen libraries (DBOS, Mem0, fastmcp, microsandbox) were picked *because* they don't — DBOS is "just decorators," Mem0 is "just a Memory object." But the discipline required to keep composition from leaking a foreign mental model into the API is itself ongoing design work. Compose-not-build is not free of the "don't force a model" tax; it just relocates it to the seam.

---

## 4. Per-subsystem verdict

| Subsystem | Verdict | One-line reason |
|---|---|---|
| **Durable runtime** | **COMPOSE (DBOS)** for Phase 0/1; build later only if friction is real | DBOS is the resolution's exact architecture, `pip install`-ready and production-tested; building it before running one agent is the precise "abstraction-on-paper" anti-pattern the thesis names. |
| **Memory** | **COMPOSE (Mem0 default + Zep audit) behind Verso's `Memory` seam** | The teardown's convergent verdict (additive + invalidate/version, composable scoping) *is* Mem0 V3's default behavior; the only loss (colocated Postgres) is an operator nicety, not a user feature. |
| **Eval / trace** | **COMPOSE (Langfuse + Phoenix)** — least defensible BUILD | The score shape is provably universal ("field renames only") and OpenInference ships 33 free auto-instrumentors; reimplementing the store is pure NIH that *forfeits* free tracing of every other composed library. |
| **Structured output** | **HYBRID — delegate reask+mode-map (Instructor); optionally compose BAML parser; OWN the 3-intent surface** | Instructor owns the per-provider mode map that changes constantly; the only BUILD-justifying piece (BAML jsonish no-reask repair) is itself a library — import, don't hand-write. |
| **Model routing** | **HYBRID — LiteLLM as translation+failover engine behind `ProviderProfile`; OWN `OMIT` + per-node policy** | Provider-quirk accumulation is a genuine moat (Hermes' 2,273-line adapter), but maintaining 100 provider dialects by hand is the worst use of the LOC budget; wrap LiteLLM, keep the thin policy surface. |
| **Tools / MCP** | **HYBRID — delegate schema-gen + MCP protocol (fastmcp); OWN error envelope + dispatch + deferred loader** | The teardown literally says "port fastmcp verbatim" for schema-gen (so import it), but the structured `ToolError` and the deferred 5-meta-tool loader are real Verso additions fastmcp left open. |
| **Sandbox** | **COMPOSE (microsandbox + E2B)** — already the resolution's call | A hypervisor is obviously not buildable; this subsystem is the proof-by-example that compose-not-build is right whenever the engine is genuinely hard — and it asks why durable-execution gets a different rule. |

**Aggregate verdict:** the strongest honest position is not "compose everything" but **"compose the 3 engines that are clearly solved + hard (durable=DBOS, eval=Langfuse/Phoenix, sandbox=microsandbox), HYBRID the 3 where Verso owns a thin moat-bearing surface (routing, tools, structured-output), and keep memory composed because the ecosystem already converged on Mem0's exact answer."** Under that split, Verso's *written* code collapses to the §1 irreducible core (~2–3k LOC: loop, seam, `@tool` ergonomics, context assembly, unified API) plus six thin seams — which is *exactly the size the PRD claims to want* (`loop <200 lines`, "one cohesive package, 3 pluggable edges") and *not* the multi-quarter platform `06` actually specs.

**The one question the BUILD decision must answer to survive this steelman:** the resolutions chose COMPOSE for the sandbox (a hypervisor) and BUILD for durable-execution (Postgres + a memoized loop) — but DBOS proves the latter is *also* a finished `pip install`. If "the engine is hard and solved" justifies composing the hypervisor, what distinguishes durable-execution, eval-store, and memory — all equally finished `pip install`s, all source-verified in our own teardowns — except that they *feel* buildable? "Feels buildable" is the trap the thesis was written to prevent.

---

*Steelman written 2026-06-05 as the adversarial counter to `06_design_resolutions/_RESOLUTIONS.md`. It argues the opposite of the locked decisions on purpose. Authority note: this does NOT supersede the resolutions; it is the case they must beat. Companion to the per-subsystem critic files in this folder.*
