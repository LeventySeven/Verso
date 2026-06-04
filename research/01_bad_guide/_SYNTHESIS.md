# Verso — Design-Implications Synthesis

*Merges all 14 cluster notes in `01_bad_guide/`. Each claim cites the cluster(s) and primary source(s) it rests on. Opinionated by design — this is a brief to argue from in the brainstorm, not a neutral literature review.*

Cluster key: `karpathy` · `anthropic` · `context-eng` · `surveys` · `reasoning-rl` · `llm-arch` · `evals` · `coding-practice` · `production` · `retrieval-memory` · `multi-agent-ttc` · `primitives` · `oss-craft` · `cto-layers`

---

## 1. The 5–8 design principles these sources collectively endorse

These are the points where independent sources converge. Convergence across clusters is the signal; a principle held by one source is an opinion, a principle held by six is a constraint.

### P1 — The loop is trivial; the context is the product

Every source that defines an agent lands on the same primitive: *an LLM calling tools on environmental feedback in a loop* (`anthropic`: Anthropic's canonical definition; `surveys`: ReAct as proven baseline; `coding-practice`: LangChain CTO — "the agent primitive has not fundamentally changed"; `production`: Vercel's Malte — "agent = tool loop with a streaming wrapper"). The loop is ~50 lines. What separates a demo from a product is *what goes into the context window each turn* (`context-eng`: Jeff Huber — "context engineering is quite simply deciding what's in the context window"; `anthropic`: LangChain's post-mortem traced quality failures to "wrong context", not model capability; `llm-arch`: Sholto — in-context learning is functionally gradient descent, 320KB/token in context vs 0.07 bits/token in weights per `karpathy`). **Verso's highest-value abstraction is the context-assembly pipeline, not the loop.**

### P2 — Reliability, not capability or context length, is the binding constraint

The "nines" argument appears in three clusters independently: 90% per-step × 10 steps = 35% end-to-end; 99% × 10 = 90% (`karpathy` Dwarkesh; `surveys` Huyen's compound-mistake math; `llm-arch` Sholto — "agents haven't taken off because of nines of reliability… not context window"). The task-horizon paper quantifies it: 80% reliability horizons are 4–6× shorter than 50% horizons — "models that sometimes succeed on hard tasks cannot reliably perform tasks of moderate length" (`evals`). **Verso must be obsessed with per-step reliability:** step-level verification, retry with error isolation, checkpoint-after-success, and circuit-breakers for the empirically dominant failure modes (premature abandonment, repeated failed actions — `evals`).

### P3 — Transparency is a correctness property, not a DX nicety

Both Anthropic and LangChain name the same failure mode as a *bug*: abstractions that hide prompts/context make systems undebuggable and are "a common source of customer error" (`anthropic`: Anthropic verbatim; LangChain listed "making hidden prompts explicit" as a corrective action). LangGraph's explicit selling point is "no hidden prompts, no hidden context engineering" (`production`). **Every prompt, every context-assembly step, every tool call must be inspectable and overridable.** No magic strings, no invisible system prompts. The escape from any abstraction must be "show me what this expands to."

### P4 — Don't over-scaffold; the model is a reasoning primitive, and scaffolding is a depreciating asset

The single most load-bearing cross-cluster finding. RLVR shows 50 RL steps take Qwen3 from 5%→50% MATH — the reasoning was already in the weights, the scaffold just unlocked it (`reasoning-rl`). Noam Brown: "the ideal harness is no harness… before reasoning models, people engineered elaborate GPT-4o agentic systems, then reasoning models arrived and the scaffolding made it worse" (`multi-agent-ttc`). The Bitter Lesson is the theoretical spine: hand-coded structure helps short-term, plateaus, gets obsoleted by general methods + compute (`retrieval-memory` Sutton; `reasoning-rl` Chung — "clever structures posed by human researchers become the bottleneck when scaled up"). **Verso's default must be a clean ReAct loop with first-class tools and a verifiable exit condition — not a planner→executor→verifier graph.** Graphs are the SVM of agent frameworks: early wins, eventual ceiling.

### P5 — Workflows and agents are categorically different; keep them separate and let them compose

Anthropic's taxonomy is the frame: *workflows* = LLMs orchestrated through predefined code paths (the code drives); *agents* = LLMs dynamically directing their own process (the model drives) (`anthropic`). Vercel's Malte is emphatic that agent-as-product and internal-automation-agent are "categorically different things" (`production`). Jake Heller: linear/predictable flows should be `def step_one, def step_two` in code — only go agentic when the task genuinely requires re-planning (`context-eng`). **Verso should expose this split explicitly:** a deterministic-pipeline path and an agentic-loop path, composable, never blurred. Don't wrap a linear 5-step pipeline in a ReAct loop.

### P6 — Verifiable feedback is what makes agents work; design for ground truth

Coding and customer support are the two validated agent domains *because ground truth exists* — tests pass/fail, tickets resolve (`anthropic`). RLVR's power is the deterministic verifier; the moment you swap in an LLM judge you get reward hacking (DeepSeek's "dhdhdhdh" adversarial example scoring 100%; PRM listed as an "unsuccessful attempt" — `reasoning-rl`, `karpathy`). ChemCrow: LLM evaluators rated GPT-4 ≈ ChemCrow, human experts rated ChemCrow ≫ GPT-4 (`surveys`). TDD is the #1 coding-agent practice precisely because the test is a verifier (`coding-practice` Simon Willison). **Verso should privilege deterministic verifiers everywhere; LLM-as-judge is a labeled "soft eval," never a primary optimization target.** Tools should optionally return a verification signal alongside output.

### P7 — Evals are the iteration loop, and they must be framework-agnostic

"Unsuccessful products almost always share a root cause: failure to create robust evaluation systems… iterating quickly == success" (`evals` Hamel). LangChain's most durable product (LangSmith) is the one they deliberately *decoupled* from the framework, precisely so it'd get adopted (`anthropic`). The eval pipeline doubles as the fine-tuning data pipeline (`evals`, `context-eng`). **Evals are a first-class Verso primitive alongside Agent/Tool/Memory — but the eval layer must work even for users who don't adopt Verso's loop.** Lock-in through evals is a false strategy; adoption through evals is the right one.

### P8 — Zero-friction onboarding + opinionated minimal abstractions is the OSS forcing function

OSS clients have zero switching cost — "DX is the moat; users leave silently without filing a ticket" (`oss-craft` Thomas Wolf). The two axes that matter: (1) the distance from `pip install` to a first *non-trivial wow* result must feel like Apple unboxing; (2) the abstraction cursor (control vs simplicity) is a *taste* decision found only by dogfooding, not derived from requirements. "Each abstraction is a friction point — have very few." Good libraries are "extremely design-opinionated." API design has objective quality (`oss-craft` PG: partial order exists; strip extraneous influences like "this is how LangGraph does it"). **`Agent()` with no args must do something useful; 3 lines to a working ReAct loop vs 150 lines of StateGraph is the wedge.**

---

## 2. Concrete implications per Verso subsystem

### 2.1 Agent loop

- **Default = clean ReAct (Thought→Action→Observation), named explicitly, no magic.** Proven baseline across `surveys` (Weng: beats Act-only on both knowledge and decision tasks), `anthropic`, `coding-practice`. Reflection/evaluation are *separate optional hooks* layered on top, not fused into the loop (`surveys`: Reflexion architecture — evaluation and reflection are distinct modules).
- **`max_iterations` is required, not optional** (`anthropic`: "include stopping conditions to maintain control"). Plus heuristic early-stop: loop detection (consecutive identical action→same observation) and inefficiency detection — these are Reflexion's `h_t` (`surveys`), and they map exactly to the task-horizon paper's top two failure modes: premature abandonment (o1: 16/32) and repeating failed actions (GPT-4: 12/31) (`evals`). Build these as circuit-breakers, not user concerns.
- **Reliability primitives in the loop core:** retry with step-level error isolation; checkpoint after each successful step; structured-output validation before committing each tool call; a failure taxonomy surfaced to the caller — tool-failure vs model-failure vs context-failure (`karpathy`, `surveys` Huyen's 6 planning + 3 tool failure modes).
- **Async + interrupt/redirect are first-class, not wrappers.** Devin's entire UX is async handoff (kick off, come back later — `coding-practice`); Block's Goose makes interrupt-and-redirect first-class ("break in and take a different path" — `production`); TTC will push think-times to hours/days (`multi-agent-ttc`). The sync path is a convenience wrapper over async, not the reverse.
- **Reasoning-budget as a first-class control.** Qwen3's empty-vs-populated `<think>` tokens are user-accessible compute control (`reasoning-rl`). Expose `reasoning_effort`/`thinking_budget` at the agent/step level — not buried in a system prompt — so simple lookups skip reasoning and complex plans get full CoT.
- **Treat CoT as steering tokens, not ground-truth reasoning.** CoT is mechanistically valuable (adaptive compute, KV states for later attention) but *not faithful* — you can garble it and the model still answers correctly (`llm-arch` Sholto/Trenton; Miles Turpin paper). Verso's eval/safety primitives must not assume CoT faithfulness.
- **Autonomy is a laddered dial, not a binary** (`karpathy` autonomy slider Tab→file→repo→full; `production` Goose: full-HITL→progressive→fully-autonomous-with-voluntary-warnings). Expose `confirmation_policy` / `safety_level` per agent and a natural "dial down" path on every executor.

### 2.2 Tool system (MCP)

- **MCP-first is the correct hardware-interface abstraction** (`karpathy`: "MCP given directly to agents — very bullish"; `production` Block: every enterprise capability is an MCP-exposed capability; Dorsey's "everything is a capability, the agent is middleware"). Verso is the application layer; MCP is the driver layer; the LLM is the kernel (`karpathy` OS analogy). Don't try to be the kernel.
- **ACI (Agent-Computer Interface) is a first-class design concern** (`anthropic`). Tool descriptions, parameter names, and examples are the *primary lever* on tool-selection accuracy (`surveys`: MRKL — small models fail at routing even when the tool is correct; Huyen — invalid-tool / wrong-params / wrong-values are 3 distinct failure modes). Anthropic "spent more time optimizing tools than the overall prompt." Make parameter descriptions required (validated), support example-usage and edge-case fields, and ship tooling to empirically test tool-usage.
- **Poka-yoke: make invalid tool usage structurally impossible** (`anthropic`: SWE-bench absolute-path fix). Encourage input constraints at registration.
- **Tag every tool with side-effects; gate write actions** (`surveys` Huyen: read tools — knowledge augmentation + capability extension — are safe to auto-invoke; write tools — DB mutation, email, transfers — require gating). Verso enforces a per-tool `side_effects` flag → configurable gate (auto / confirm / require-HITL).
- **Tool-call normalization across providers (the "tool shim").** OSS models lack native tool calling — Block built a shim to adapt Llama/Qwen/DeepSeek to MCP (`production`). A provider abstraction that normalizes tool-call semantics across native and non-native models unlocks OSS as a first-class choice (also `production` Vercel: AISDK succeeded by staying at the level where chatbots and agents "looked the same").
- **Tool filtering per-turn + dynamic skill library.** Don't show all tools always (`surveys`: HuggingGPT task-type filtering, Voyager skill library, ablation-study advice). Support filtering by tag/task-type and an add/remove/retrieve skill registry. Block's "recipes" (bake a successful workflow into a shareable script) is the team-propagation version (`production`).
- **Verifiable tools enable native quality scoring.** Tools that return `{output, verified, confidence}` let the loop score tool-use without a judge model (`reasoning-rl`: RLVR scope expansion to citation-checking etc.).

### 2.3 Context engineering

- **Context assembly is a named, composable, inspectable object — not string concatenation.** The prompt is assembled from system message + user input + tool outputs + retrieval + history (`production` LangChain; `context-eng`). Emit a `ContextBundle(instruction, retrieved, history, tools, budget_used, budget_total)` per turn, inspectable *before* it hits the model.
- **`context.inspect()` — read exactly what the model reads** (`context-eng` Jake Heller: before changing any prompt, read raw context verbatim including OCR artifacts; "if it's hard for you to read, it'll be hard for the AI"). Make this the standard debug protocol.
- **Context budget is a hard constraint with a default ceiling (~40% utilization)** (`context-eng` Dex Horthy: keep utilization under 40% to enable clean compaction/handoff). Over-budget injection is a warning/blocking error, not a silent overflow.
- **Gather-and-glean is the canonical retrieval shape** (`context-eng` Jeff Huber): Stage 1 maximize recall (fan-out N query probes across structured + unstructured sources); Stage 2 maximize precision (rerank/glean before injection). Ranker hierarchy: vector → RRF → reranker → LLM-as-ranker ("brute-force search" for high-stakes). Long context is *not* a substitute for good context (Chroma report: ~40% performance at 170k tokens; curated context gives "massive gains").
- **Compaction is a first-class lifecycle event with a user-controllable prompt and structured output** (`context-eng`: default `/compact` is "trash"/a near-no-op; intentional compaction produces a structured handoff with file names + line numbers + what's-done/what-remains; `coding-practice`: auto-summarization as short-term-memory management). `agent.compact(prompt=...)` → a `CompactionBundle`, not raw text.
- **KV-cache-aware prefix discipline.** Keep the stable prefix (system prompt, tool schemas, base instructions) canonical, immutable, and first, to hit prefix caching (`context-eng`, `llm-arch`: KV cache is the real memory constraint — 6 KiB to 840 KiB/token across architectures; prefill cost vs generation cost differ). **Never silently truncate** — truncation is semantically lossy (`llm-arch` superposition: models are *underparameterized*, more context genuinely helps); prefer structured summarization.
- **Put scorable fields first in output schemas** (`context-eng` Jake Heller: emit verdict/number before explanation; constrain to one token via `max_tokens=1`+stop-words; the "about-to-explain" effect raises one-token answer quality). Default classification schema = `{verdict, confidence, explanation}`.
- **Few-shot example injection is a core memory primitive, not just retrieval** (`llm-arch`: in-context examples ≈ implicit fine-tuning; correct tool-use patterns in context before the task).

### 2.4 Memory / retrieval

- **Three-layer model is the right abstraction:** sensory/raw-embeddings → short-term/in-context (working memory) → long-term/external store (`surveys` Weng). Verso exposes these as distinct interfaces, not collapsed into "context." Be honest about the fourth: cross-session weight-level "learning" is unsolved (`karpathy` deficit #4; `reasoning-rl` continual learning "2027 maybe"). Label it: `memory.session` / `memory.store` / `memory.trained` (unavailable).
- **One canonical store, multiple query interfaces — not separate vector + KV + graph stores that desync** (`retrieval-memory` Turbopuffer: "the worst outages are state in multiple places not syncing up"). Working memory is *one thing* queryable three ways: semantic (vector), lexical (BM25/full-text), exact (regex/SQL-filter). Expose all three for simultaneous fan-out (`retrieval-memory`: agentic pattern is "dozens of concurrent heterogeneous queries per turn" — diversity matters more than any single modality).
- **Retrieval is burst-parallel from inside the loop, not a one-shot setup step** (`retrieval-memory`: old RAG = 1 call before 1 LLM call; new agentic = parallel heterogeneous queries). Design the `search` tool for fan-out invocation. Access pattern: cheap continuous appends (observations/tool outputs) + burst parallel reads at decision points + periodic background compaction (not per-turn).
- **Multi-factor retrieval scoring, not just cosine** (`surveys` Generative Agents: recency + importance + relevance; the LM-scored importance dimension is the most useful and most-ignored). Pluggable scoring.
- **Failure-case memory > success-case memory** (`context-eng` Chroma: injecting past *failures* reliably breaks local minima; injecting past *successes* causes lazy pattern-matching — "thanks, I'll just say that back"). Store failures explicitly; be cautious injecting successes.
- **Zero-infra default backend, clean swap to scalable.** SQLite + local embedding (or flat-file BM25) by default; swap to Turbopuffer/Pinecone/Weaviate without code changes (`retrieval-memory`: the Readwise $20–30k/mo-on-a-$5k/mo-company horror story; "starts for free, scales to serious").
- **Codebase/project memory is a moat *and* a usability requirement** (`coding-practice` Devin's "wiki" persists across sessions and is the stickiness mechanism; `multi-agent-ttc` Noam: "geniuses on day one" — the missing thing is job experience = project-specific memory). Memory should be open-format (markdown/JSON), versioned, taggable, exportable — the *durable asset* while the loop is ephemeral (`cto-layers`: "context is durable, software is ephemeral").
- **Minimal, non-prescriptive surface** (`retrieval-memory` Bitter Lesson applied: hard-coded chunking/summarization/entity-extraction heuristics are the wrong investment). Ship `store` / `retrieve(query, k, filters)`; don't pre-build graph retrieval or multi-hop. Store-everything-by-default + let the LLM judge relevance.

### 2.5 Evals / observability

- **`Eval` is a core construct alongside `Agent`/`Tool`/`Memory`** with a three-tier hierarchy (`evals` Hamel): L1 `eval.unit()` deterministic assertions in CI (feature × scenario matrix, sub-minute); L2 `eval.judge()` LLM-critique + human-alignment review; L3 `eval.experiment()` A/B post-ship. The hierarchy must be explicit so users know *which* level to reach for.
- **Feature × scenario tagging on test cases** turns a test runner into a debugging tool (`evals` Lucy pattern: one assertion per cell; filter "all failures in listing-finder / no-match").
- **Native trace store, zero-config, traces just exist** (`evals`, `coding-practice`, `production` all converge). Traces are the connective tissue of the Build→Test→Deploy→Monitor loop. Structured trace per run by default: every Thought/Action/Observation, tool call, sub-agent dispatch, with timestamps + token counts. Optional forwarding to LangSmith/Arize via adapter.
- **Agent observability ≠ traditional observability** (`production` LangChain explicit): expose tool run counts / latencies / error rates and *trajectory analytics* (which decision paths agents take), with unstructured payload inspection. Persona is the "agent engineer," not the SRE.
- **Measure reliability at the target horizon, not peak success** (`evals` task-horizon paper). Surface both `p50_horizon` (capability ceiling) and `p80_horizon` (production-reliability floor) so teams see whether they're in "sometimes works" or "ships to prod." Measure per-step pass rate separately from end-to-end so users find their bottleneck.
- **Multi-signal reward composition + anomaly detection on score trajectories** (`reasoning-rl` GRPO instability: track task-success + format + latency + tool-accuracy; flag sudden drops = the collapse signal). Not a single pass/fail score.
- **LLM-judge alignment is the ongoing quality signal** (`evals` Hamel's spreadsheet: 25–50 examples, model-outcome vs human-outcome, iterate the critique prompt, measure precision/recall split not raw agreement). Build it native; eval quality degrades as distributions shift.
- **Eval runs double as fine-tuning data collection** (`evals`, `context-eng` RFT: 50–100 examples + objective judge; CoCounsel moving to a fine-tuned model per micro-step). Export labeled trace pairs as JSONL.
- **Trace infra must be designed for scale from day one** (`coding-practice` SmithDB: P50 37 KB → P99 12 MB, 8.1M-token traces, 150M traces/week; agents are themselves users of the trace store so read-path latency is in the agent's critical path — target sub-100ms reads).
- **Domain-specific over generic** (`evals` Hamel: "don't rely on generic eval frameworks"; `reasoning-rl` Raschka: stopped looking at benchmark numbers — agentic-length benchmarks beat one-shot Q&A). Ship feature×scenario + judge-alignment + reliability-horizon as the differentiated primitives.

### 2.6 Multi-agent / orchestration escape hatch

- **The durable layer is the legitimate reason for the escape hatch — and it's mandatory in production, not optional.** Three independent production needs converge: long-running tasks (10 min–12 hr — `production` LangChain), pause-and-resume for HITL (`production` Vercel's ephemeral-webhook pattern — workflow `await`s a single-use URL, resumes hours later as if no time passed), and headless batch jobs (`production` Goose in CI). TTC at extreme durations makes async checkpoint-resume *mandatory* (`multi-agent-ttc`). This is the LangGraph-validated axis: durable execution + HITL + checkpoint-resume (`anthropic`).
- **But the escape hatch must not contaminate the 80% that don't need it.** Durable execution should be opt-in at the `agent.run()` call (or a `DurableAgent` subtype) — *not* a class hierarchy where every agent is a subgraph of a StateGraph (`primitives`: "that's the LangGraph mistake"). Counterpositioning claim Verso can make that incumbents can't rebut: "we don't force graphs; forcing graphs costs 3× complexity for 0 benefit on most agents."
- **Sub-agents = context isolation, not org-chart role-play** (`context-eng` Dex Horthy: sub-agents are about context control — offload an expensive search so its tokens don't pollute the parent; the sub-agent returns structured/compact results — file names + line numbers, not raw content). Typed compact return values; mind the "playing telephone" problem (prompt the parent to prompt the child on *how* to return).
- **Multi-agent value is parallelism + independence, not graph topology** (`multi-agent-ttc` Noam: current multi-agent is "heuristic," not Bitter-Lesson-compliant; the "civilizations" value is emergent over many independent agents, not a fixed DAG; wall-clock time is the TTC bottleneck → maximize parallelism, synchronize only at dependency boundaries). Default multi-agent path = breadth-first fan-out on independent subtasks with result synthesis.
- **The three real production topologies** to support in the durable layer (`production` Block + LangChain independently): hierarchical supervisor+worker, parallel fan-out with merge, sequential pipeline. The five Anthropic workflow patterns (prompt chaining, routing, parallelization [sectioning+voting], orchestrator-workers, evaluator-optimizer) are the composable named operators (`anthropic`).
- **Do NOT ship adversarial self-play as a first-class pattern** (`multi-agent-ttc`: self-play converges cleanly only in two-player zero-sum; for writing/research/code-review what competing agents optimize is undefined). Too much rope. Collaborative parallel fan-out is the safe high-value primitive.
- **Verify-then-return as a first-class pattern** (`surveys`: AlphaCode2 1M-samples+filter, Medprompt 11-vote, Gemini CoT@32; `reasoning-rl`: Best-of-N with verifiable scoring). Make sampling+verification a built-in, not a user-written for-loop — but gate it behind a verifiable signal.

### 2.7 Public API / DX

- **`Agent()` with no args does something useful; `@tool` is one decorator; memory read/write is one line.** These are the "magic corners" — infinite-size targets, shortest call paths for the most common ops (`oss-craft` Rauno/Fitts's Law). 3 lines to a working ReAct loop is the wedge vs 150 lines of StateGraph (`primitives`).
- **Implicit input — infer, don't require** (`oss-craft`: "the best input is no input"). Auto-detect decorated tools in scope; auto-configure backend (in-memory if none, Redis if `REDIS_URL` set); auto-select model tier if hints available. Every required config param is a tax.
- **Abstract as late as possible; be extremely design-opinionated** (`oss-craft` Wolf). Default to the concrete un-abstracted form; introduce abstraction only when explicitly needed. The abstraction cursor is found by dogfooding, not derivation.
- **Streaming/observable state by default — silence = an unresponsive UI** (`oss-craft` Rauno: immediate feedback at every interaction point). Every loop iteration emits observable state. Diffs-not-prose, structured-changes-not-raw-text, accept/reject affordances — minimize human *verification* time (`karpathy` generation-verification loop is the primary metric; "command-Y to accept, not read 1000 lines").
- **Design for the expert, not the tourist** (`oss-craft`): quiet production mode is the default once past the "I know what I'm doing" threshold; verbose debug is one flag away. Fidgetability affordances: `--dry-run`, `verso trace`, `verso explain`, a tool-sandbox REPL.
- **English-first entry point, typed/structured API for power + reliability** (`karpathy`: "everyone is a programmer because everyone speaks natural language"; `cto-layers`: domain experts must be able to build — the intel-warrant-officer example). `agent.run("analyze this CSV…")` is the door; typed schemas are the depth.
- **Structured output (Pydantic/Zod) is the default interface between model and tools** (`surveys`: "much of agent demo code is parsing model output" — a fundamental fragility; parse-string-output is an antipattern).
- **Fresh-mind ritual as a release-gate** (`oss-craft` Wolf: reinstall as a first-timer, run the first example, ask "does this look obvious?"). Not just unit tests — "does it still feel obvious?"
- **Python-first, not Python-also** (`production`: "when you're a serious AI cloud you have to support Python"; LangChain's 70M/mo Python downloads; Block's Python agent infra). See open tension §4 on TS.
- **Sandbox-first execution** (`coding-practice`: Willison/Wu/Chase all independently — sandbox isolation is the #1 security control; the "lethal trifecta" = private data + untrusted content + exfil vector, cut any leg; the auth-proxy pattern keeps API keys outside the agent's context). Execution-environment spectrum: virtual-FS → code-interpreter (QuickJS-style, multi-tenant default) → full sandbox (opt-in). Sandbox by default; `--trust-local` requires an explicit flag + warning.
- **Model-agnostic from day zero with a clean model-binding layer** (`anthropic` LangChain's founding constraint; `multi-agent-ttc` McGrew: start with the frontier model, distill/route to cheaper models second; `context-eng`: model routing per step is a cost/quality lever). `model` overridable per step; surface active-param count + KV-cache cost in model-selection guidance (`llm-arch`); route by *task type and capability threshold*, not cost alone (`reasoning-rl`: sub-threshold models "give up and settle for heuristics").

---

## 3. Positioning — primitive or wrapper, and the layer Verso must own

### Verdict: Verso is a primitive, and it must *behave* like one to survive.

The "GPT wrapper" pejorative is dead (`primitives` a16z; `cto-layers` Casado: "you don't call software a cloud wrapper — there's tremendous complexity on top of the model"). But that doesn't make any framework a primitive. The clusters draw a sharp line:

- **What Verso is NOT:** an SDK (write your own HTTP client in an hour), a workflow orchestrator (LangGraph/CrewAI live in the graph-DSL zone), or the model/kernel itself (`karpathy` OS analogy — Verso is the application/driver layer, not the CPU).
- **What Verso IS:** the agent-loop primitive — ReAct + MCP + memory + evals — at the layer "low enough to be structural (not a workflow), high enough to encode real engineering leverage (not just an HTTP client)" (`primitives`). It modularizes the agentic-orchestration function that today is integrated into every framework's bespoke graph object (`primitives`, via Aggregation Theory: modularize what incumbents integrated, own the developer relationship).

### The moat is NOT the loop — it is what accretes to the loop.

A cleaner ReAct loop is *differentiation*, not *defensibility* (`primitives` a16z moats panel: AI capability = differentiation, workflow/context ownership = defensibility; `cto-layers`: "no inherent endemic moat in the AI stack other than overcoming bootstrap"). The defensible layer is the **durable infrastructure** — what Palantir calls "ontology" (`cto-layers`): the memory system + tool registry + eval corpus that ties domain knowledge to agent decisions. Concretely:

- **Memory must be a real primitive, not a thin Redis adapter** — its own schema, retrieval semantics, eval hooks. Switching away means re-engineering all of it (`primitives`: process-power moat).
- **Eval results in Verso's format, versioned against tool/loop configs, become organizational knowledge** that's painful to migrate (`primitives`, `evals`).
- **The MCP tool registry is an aggregation play** — be the place tool servers register and developers discover them; "Verso-certified" tool servers get discovery advantage → supply-side lock-in (`primitives` Aggregation Theory).

### The strategic frame: alpha-layer infrastructure for a fragmenting market.

- Verso helps teams express what's *unique* about their domain/workflow (alpha software) rather than making every agent look the same (beta software) (`cto-layers` Palantir's alpha/beta rubric — LangGraph/CrewAI implement generic patterns = beta infrastructure).
- The market *fragments* (`cto-layers`: OpenAI lost code→Cursor, image→Midjourney, video→Sora; no single model wins everything). So Verso must **fragment well** — pluggable at every layer (model, tool registry, memory backend), assemble a domain-specific stack without lock-in to any one of them. Pluggability is a strategic requirement.
- **Feature→Product→Company ladder** (`primitives`): Verso starts as a "cleaner loop" (a feature vs LangGraph). It must backfill to a *product* (the full deployable runtime: loop + tools + memory + evals + durable layer) and then a *platform* (where developers build agent apps) before a model provider ships a first-party agent runtime — otherwise it's in VisiCalc territory.
- **Greenfield wedge** (`primitives`): don't fight to displace LangGraph's installed base — be the reflexive default for *every new agent project*. Architecture-over-model is the durable bet (`cto-layers`: "AI infrastructure layer is where value accrues; intelligence is becoming free at 10×/yr cost decline" — architect for the world 18 months out where the bottleneck is context + orchestration, not capability).

---

## 4. Open tensions / decisions for the brainstorm

### T1 — Python vs TypeScript (or both?)

- **For Python-first:** "serious AI cloud = must support Python"; LangChain 70M/mo Python; Block's agent infra is Python (`production`). The research substrate (RLVR, evals, fine-tuning, retrieval) is Python.
- **For TS-also:** Vercel ships its Workflow Development Kit and AISDK as TypeScript; TS is now #1 on GitHub; Vercel's Malte "doesn't have a bet on JavaScript" but supports both (`production`). The durable-execution story (`use workflow` directive, ephemeral webhooks) is TS-native at Vercel.
- **Decision needed:** Python-first is the clear call from the notes, but is the durable/workflow layer better expressed in TS? Does Verso ship a TS client later, or commit Python-only to keep the abstraction cursor tight (`oss-craft`: few abstractions, dogfood one language well)? **Recommendation to argue:** Python-first, single-language until the core abstraction is proven; resist multi-language until Day-30 customizability is solid (`anthropic`: LangChain's Day-1-vs-Day-30 trap).

### T2 — How much to abstract (the abstraction-cursor problem)

- The hardest *unresolvable-from-first-principles* decision (`oss-craft` Wolf: "a lot of taste here… try it a lot yourself"). Tension: zero-friction Day-1 (`Agent()` does something) vs Day-30 production customizability without a rewrite (`anthropic`: the exact failure that forced LangChain's 1.0 rebuild).
- **Sub-question:** which of the five Anthropic workflow patterns and four control-flow primitives (`surveys`: sequential/parallel/routing/loop) become *named first-class operators* vs left to user code? Naming them gives vocabulary (`anthropic`); over-naming them rebuilds the graph DSL Verso is positioned against.
- **Decision needed:** the team must dogfood real agents and find where abstractions break — this can't be designed on paper (`oss-craft`). Set a hard rule: every abstraction must have a one-line "show me what this expands to" (`anthropic` transparency-as-correctness).

### T3 — Durable-execution stance: how deep, how default?

- All production sources say durable execution is *required* for long-running/HITL/batch (`production`, `multi-agent-ttc`). But the primitives cluster insists it must be opt-in and non-contaminating (`primitives`).
- **Sub-questions:** Build a durable engine in-house, or integrate an existing one (Temporal-style / Vercel WDK-style)? Is checkpoint-resume a `agent.run(durable=True)` flag, a `DurableAgent` subtype, or a separate `Workflow` object that *composes* agents? The ephemeral-webhook HITL pattern (`production` Vercel) is elegant — adopt it directly or design our own?
- **Decision needed:** where exactly is the seam between the tactical (simple, ephemeral, per-session ReAct) layer and the durable (recoverable, cross-session, auditable) layer — and can a user move an agent across that seam without a rewrite?

### T4 — How much memory to own vs delegate

- Tension: memory is the moat (own it deeply — `primitives`, `cto-layers`) vs memory should be open/portable/not-locked-to-framework (`coding-practice` LangChain; `production` Block). Also: the Bitter Lesson warns against hard-coded memory schemas/heuristics (`retrieval-memory` Sutton), yet a "real primitive not a thin adapter" implies opinionated schema (`primitives`).
- **Resolution to argue:** own the *retrieval semantics + eval hooks + scoring* (the moat), keep the *storage format open* (markdown/JSON, exportable) and the *backend swappable* (SQLite→Turbopuffer). Store-everything-by-default + LLM-judges-relevance (minimal heuristics) satisfies both Sutton and the moat.

### T5 — Multi-agent: how much to expose now?

- Tension: the durable layer "should support multi-agent topologies" (`production`) vs "multi-agent is mostly heuristic scaffolding that gets washed away; the value is parallelism not topology" (`multi-agent-ttc`). Self-play is explicitly off-limits as a primitive (`multi-agent-ttc`).
- **Decision needed:** ship only context-isolating sub-agents + parallel fan-out now (the two safe, high-value patterns — `context-eng`, `multi-agent-ttc`), and defer supervisor/hierarchical orchestration to the durable layer? Or pre-build the three production topologies? **Recommendation to argue:** ship sub-agent-as-context-isolation + parallel-fan-out as tactical primitives; put supervisor/hierarchical only in the opt-in durable layer.

### T6 — Build-vs-absorb given the depreciating-scaffold problem

- Noam Brown's warning is sharp: "don't spend 6 months building something that gets tossed in 6 months — but RFT environment+reward design is durable" (`multi-agent-ttc`). Which Verso investments are *durable* (loop structure, MCP tool contract, memory persistence, eval hooks — `multi-agent-ttc`'s own list) vs *tactical scaffolding that model scale will absorb* (elaborate planning graphs, model routers — Noam: "routers will go away")?
- **Decision needed:** explicitly classify every planned subsystem as durable-or-tactical and refuse to over-invest in the tactical ones. Routers, hand-crafted planners, and reasoning scaffolds are tactical; the eval corpus, memory semantics, tool registry, and trace infra are durable.

### T7 — Open-source / monetization posture

- Convergent advice: *truly* open (not open-core), grow-the-pie, monetize hosting proportionally (`production` Vercel WDK + Block's "30,000 community engineers > 3,000 internal"); open-core "risks user trust for production-critical infra" (`production`). But the moat is the accreting ecosystem (registry, eval corpus, memory) (`primitives`) — which pushes toward a hosted control plane.
- **Decision needed:** what is open (the loop, MCP integration, memory primitive, eval primitives — everything a developer runs locally) vs hosted/paid (the registry-at-scale, the trace DB at 150M/week, the cost-governance gateway, the "Verso Engine" monitoring agent — `coding-practice`)? **Recommendation to argue:** genuinely-open core + premium hosting for the scale-dependent ecosystem pieces.

---

*Source files: all 14 notes in `/Users/seventyleven/Desktop/Verso/research/01_bad_guide/`. Every numbered point above is traceable to the cited cluster's primary source.*
