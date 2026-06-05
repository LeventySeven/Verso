# RE Targets: TypeScript/JS Agent Frameworks

_Generated: 2026-06-05_

---

## Already Covered

The following TS/JS frameworks already have substantive teardowns in `/Users/seventyleven/Desktop/researchfms/teardowns/`:

- **MASTRA.md** (602 lines + Coverage Expansion) — deep RE: agent loop as `.dowhile` workflow, snapshot/suspend/resume, tool approval HITL, memory (working + semantic), scorers/evals, processors, multi-agent network, A2A. The durable seam IS the core finding — same loop runs in-memory or durably via Inngest.
- **VERCEL_AI_SDK.md** (424 lines + Coverage Expansion) — deep RE: `generateText` multi-step loop, `streamText` internals, `LanguageModelV2` provider spec, tool taxonomy, `generateObject` strategies, UI Message Stream reconstruction, `ToolLoopAgent`. This is the substrate Mastra, Trigger.dev, and Temporal's AI plugin all sit on top of.

---

## RE Targets

### Inngest AgentKit

**What:** TypeScript multi-agent network framework built on top of Inngest's durable function runtime. Agents, Networks, Routers, and a shared typed State are the four primitives.

**Why for Verso:** The Router → State → Agent loop is the clearest implementation of *deterministic vs. LLM-based routing as a slider* in any open TS framework. The state machine that routers read is Verso's direct analogue — typed, shared across agents, accessible for both code-based and model-based dispatch. AgentKit's "orchestration-first" design (no graph DSL, but explicit routing logic in code) is closest in philosophy to Verso's non-graph default. Inngest underneath provides durable execution for free — Verso needs to make a comparable seam decision.

**What to RE:** The `packages/` core in `inngest/agent-kit`: (1) `Network` class — how the run loop calls Router → Agent → State update in sequence; (2) `State` type — the KV + conversation history hybrid, how tools write to it; (3) `Router` — the exact function signature, how `onRoute` lifecycle hook fires, how code-based vs. agent-based routing coexist; (4) how MCP tool sources are registered and called; (5) any deterministic replay gate in tests (appears in December 2025 PRs).

**Source pointer:** `https://github.com/inngest/agent-kit` — fully open source, monorepo, MIT license.

**Priority:** P0

---

### Cloudflare Agents SDK

**What:** TypeScript SDK where every agent IS a Cloudflare Durable Object — one instance per agent identity, SQLite-backed state, WebSocket hibernation, built-in scheduling, MCP client. The `@cloudflare/agents` package wraps DO lifecycle into an opinionated `Agent` base class.

**Why for Verso:** Cloudflare's model is the extreme end of Verso's "tactical↔durable seam" problem: they made durability a *deployment target* (DO), not an in-process abstraction. Understanding their tradeoffs (hibernation cost, SQL-as-state, no hot-path in-memory mode) directly informs where Verso should draw its seam. The `@callable()` decorator for type-safe RPC over WebSocket is a concrete pattern for Verso's edge-communication design. The `queue()` / `dequeue()` task system is a minimal durable task queue worth understanding before designing Verso's own. The 2026 Agents Week additions (`keepAlive`, `runFiber`, `stash`, `onFiberRecovered`) are new durable execution primitives worth benchmarking against Verso's checkpoint model.

**What to RE:** (1) `Agent` class source in `cloudflare/agents` — the `onStart`, `setState`, `schedule`, `sql` tag, `this.mcp`, `@callable` decorator implementation; (2) `cf_agents_state` / `cf_agents_schedules` / `cf_agents_queues` SQL schema; (3) hibernation lifecycle — how `hibernate: true` default works, when agent wakes, what costs; (4) `AIChatAgent` and `@cloudflare/think` higher-level agent loop; (5) the 2026 fiber primitives if public in source.

**Source pointer:** `https://github.com/cloudflare/agents` — open source, Apache 2.0.

**Priority:** P0

---

### OpenAI Agents SDK (JS/TS)

**What:** Lightweight TypeScript port of OpenAI's Python Agents SDK. Core primitives: Agent (instructions + tools + handoffs), Handoffs (delegation between agents), Guardrails (input/output validation), Tracing, Sessions (persistent working memory), and as of April 2026 — Sandbox Agents (filesystem + shell) and a Subagent primitive.

**Why for Verso:** This is the reference implementation of the *handoffs-as-first-class-primitive* pattern — where delegation is explicit and typed, not emergent from prompting. Verso needs a clear position on handoffs vs. spawning vs. tool-calling sub-agents, and the JS SDK is the cleanest open implementation to study. The April 2026 "Next Evolution" release (sandbox execution, subagent beta, long-horizon harness) is the most recent public articulation of where agent infrastructure is heading. The Tracing system — span-based, collecting LLM calls + tool calls + handoffs into a unified trace — is a direct reference for Verso's observability layer. The Sessions model (persistent working context within a run) maps directly to Verso's in-turn context management.

**What to RE:** (1) `Agent` class definition — how `handoffs`, `tools`, `guardrails` are typed; (2) the runner loop in `src/runner/` — how handoffs trigger, how the active agent switches, termination condition; (3) `Session` implementation — what's stored, storage backend, how context is assembled per turn; (4) Tracing — the span model, `TracingProcessor` interface, default OTEL export; (5) `SandboxAgent` added April 2026 — filesystem workspace model, how sandbox state snapshots work.

**Source pointer:** `https://github.com/openai/openai-agents-js` — open source, MIT.

**Priority:** P0

---

### LangGraph.js

**What:** TypeScript port of LangGraph — graph-based stateful agent orchestration. Nodes (functions), edges (conditional routing), and a typed `StateAnnotation` form a compiled graph that runs with automatic checkpointing, HITL interrupts, and long-term memory via `Store`.

**Why for Verso:** LangGraph.js is the *explicit foil* for Verso's design. Verso explicitly rejects graph-DSL-by-default; studying LangGraph.js is how Verso stays honest about what graphs buy and what they cost. The `Annotation` / `StateAnnotation` typed state model — where graph state is a merged reducer-style object — is the most mature typed-state implementation in any TS agent framework and directly informs Verso's typed memory design. The HITL interrupt/resume mechanism (breakpoints, `Command` objects) is the JS ecosystem's reference for mid-run human intervention — Verso's seam must be at least this ergonomic. The `Store` API (cross-thread persistent memory, namespace-scoped) is a clean design for Verso's durable memory backend interface.

**What to RE:** (1) `StateGraph` compile-to-runnable flow in `langgraphjs` source — `addNode`, `addEdge`, `addConditionalEdges`, `compile()`; (2) `StateAnnotation` and `Annotation.Root` — how reducer merges work, how type inference flows through; (3) Checkpoint serialization — the `BaseCheckpointSaver` interface, the Postgres/SQLite savers; (4) Interrupt/resume — `interrupt()` function signature, `Command` object, how the graph re-enters at the interrupted node; (5) `InMemoryStore` and `BaseStore` interface for cross-thread memory; (6) Streaming — the `stream()` call modes (`values`, `updates`, `messages`, `custom`).

**Source pointer:** `https://github.com/langchain-ai/langgraphjs` — open source, MIT. Weekly npm: ~42k, production-stable as of mid-2025.

**Priority:** P0

---

### Convex Agent Component (`@convex-dev/agent`)

**What:** A Convex component (not a standalone framework) that gives Convex apps a managed agent layer: persistent threads, message storage, hybrid vector+text search over thread history, tool calling via Convex mutations, and real-time streaming over WebSockets. Built on Vercel AI SDK underneath.

**Why for Verso:** Convex's model is *the reactive-backend pattern for agents* — long-running AI work runs as Convex mutations/actions (durable by default) while clients stay live-reactive via WebSocket subscriptions without polling. This is a concrete implementation of Verso's "same agent, different durability tier" seam — except Convex hardcodes the durable path. The thread/message schema (how messages are stored, indexed, and injected as context) is a worked implementation of Verso's typed memory primitive: messages are first-class DB rows, searchable by both embedding and text, injectable into LLM context at configurable limits. The hybrid search-before-inject pattern (semantic + BM25 over conversation history as RAG) is a specific design choice Verso's memory layer should either adopt or consciously reject.

**What to RE:** (1) Full source at `get-convex/agent` — `Agent` class, `createAgent()`, thread model, message schema; (2) how tool calls are expressed as Convex mutations (the type-safety bridge between AI SDK tools and Convex's runtime); (3) `searchMessages()` — the hybrid vector+text query, what fields are indexed, what limits are hardcoded; (4) streaming — how deltas are sent over Convex's WebSocket subscription model vs SSE; (5) multi-agent handoff — how one agent passes a thread to another.

**Source pointer:** `https://github.com/get-convex/agent` — open source, MIT.

**Priority:** P1

---

### VoltAgent

**What:** TypeScript agent framework with declarative agent definition (provider, tools, memory adapter, sub-agents), a workflow engine for multi-step automations, supervisor/sub-agent hierarchies, RAG/retriever agents, and a paid VoltOps observability console.

**Why for Verso:** VoltAgent's explicit separation of *agent loop* (single-agent tool-use cycle) vs *workflow engine* (suspendable multi-step automation) is the same conceptual split Verso is navigating with its tactical↔durable seam. The supervisor pattern — one agent coordinates a team, routes tasks, synthesizes results — is a specific multi-agent coordination model Verso should have a native answer to. VoltAgent also bundles observability (traces, memory inspection, evals) as a platform offering, showing the product surface area Verso's reliability tier needs to cover. Less architecturally novel than Mastra or LangGraph, but useful as a calibration point for what "full batteries-included" looks like in practice.

**What to RE:** (1) GitHub `VoltAgent/voltagent` monorepo — core `Agent` class in `packages/core`; (2) how sub-agents are wired to supervisor (the `agents` prop on a supervising agent); (3) the workflow engine — how suspend/resume is implemented, what the snapshot format is; (4) memory adapters — the `IMemoryAdapter` interface, LibSQL implementation; (5) how evals are defined and run.

**Source pointer:** `https://github.com/VoltAgent/voltagent` — open source, MIT.

**Priority:** P1

---

### Trigger.dev (v3 Agentic)

**What:** Open-source TypeScript platform for durable background jobs and AI workflows. v3 added: CRIU-based checkpoint/resume (tasks survive infrastructure restarts), Waitpoints (pause indefinitely for human approval or external events), Realtime streaming (SSE/WebSocket token streaming to frontend), and AI SDK integration (any `generateText`/`streamText` call inside a task becomes durable).

**Why for Verso:** Trigger.dev v3 is the most concrete production answer to "what does it take to make an AI agent loop durable without rewriting it?" Their Waitpoints are the HITL primitive Verso needs to match ergonomically. The checkpoint mechanism (CRIU at the process level, not serialized state snapshots) is architecturally opposite to Mastra's serialized-workflow approach — and the tradeoffs are real: CRIU survives arbitrary async code but requires container infrastructure; Mastra's snapshot is portable but requires deterministic serializable workflows. Verso must pick a position. The AI SDK plugin pattern (wraps `generateText()` as a Temporal/Trigger Activity transparently) is a design pattern Verso's durable mode could adopt.

**What to RE:** (1) `triggerdotdev/trigger.dev` v3 source — task definition, checkpoint trigger points, CRIU integration; (2) `wait.for()` Waitpoint API — exact signature, how the run suspends and resumes on external signal; (3) Realtime streams — how `metadata.stream()` and `run.subscribe()` work for live token delivery; (4) AI SDK integration — `@trigger.dev/ai` or equivalent plugin, how it wraps AI SDK calls as Activities; (5) run lifecycle states and the worker/coordinator protocol.

**Source pointer:** `https://github.com/triggerdotdev/trigger.dev` — open source, Apache 2.0.

**Priority:** P1

---

### Motia

**What:** Unified backend framework where the primitive is a Step (a file with a config + handler). Steps can be API handlers, event consumers, cron jobs, or background workers — all unified, all observable. Supports TypeScript, Python, JavaScript. Positioned as replacing Nest.js + Temporal + BullMQ with one system.

**Why for Verso:** Motia's event-driven multi-agent pattern — agents communicate by emitting events, Steps consume them — is the loosely-coupled multi-agent coordination model Verso's edge layer might need. The "everything is a Step" primitive is a competing primitive to Verso's "everything is a tool/agent" model: worth understanding the tradeoffs. Motia's language-agnostic design (TS + Python Steps in one app) is directly relevant to Verso's polyglot ambitions. The auto-observability (every Step gets traces for free) is a design goal Verso shares.

**What to RE:** (1) `MotiaDev/motia` — Step definition schema (the config block), event routing engine, how Steps subscribe to events; (2) how AI agent Steps differ from regular Steps (if at all — the thesis is there's no difference); (3) state passing between Steps — shared context vs. event payloads; (4) the runtime binary — how Steps are loaded, scheduled, executed; (5) observability — what's traced automatically, the console UI.

**Source pointer:** `https://github.com/MotiaDev/motia` — open source.

**Priority:** P2

---

### ElizaOS (v2)

**What:** Open-source TypeScript "agentic operating system" — a plugin-first framework for deploying agents to messaging platforms (Discord, Telegram, Twitter, Slack, etc.) and Web3 chains. Three-layer: `@elizaos/core` (agent loop, plugin model, LLM abstraction) → plugin ecosystem (90+ plugins: actions, providers, evaluators, services) → project layer (deployable workspaces).

**Why for Verso:** ElizaOS v2's plugin model — `Plugin` interface with `actions`, `providers`, `evaluators`, `services`, `modelHandlers`, `databaseAdapters`, `routes`, `eventHandlers` — is the most elaborate open-source design for "pluggable everything" in a TS agent framework. Verso's pluggable edges (model providers, memory backends, tool sources) need a comparable plugin contract. The `evaluators` primitive (post-response scoring, deciding what to remember) is a direct parallel to Verso's evals/reliability layer. The `providers` system (injecting runtime context — files, state, user info — into agent prompts) is a worked implementation of Verso's context engineering layer. Niche/crypto-skewed, but the architecture is genuinely instructive.

**What to RE:** (1) `elizaOS/eliza` — `@elizaos/core` package: `AgentRuntime` class, `IAgentRuntime` interface; (2) the `Action` interface — `validate`, `handler`, `examples` fields; (3) `Provider` interface — how runtime context is assembled into a prompt string; (4) `Evaluator` interface — `handler` fires post-response, writes to memory; (5) `IMemoryManager` interface and the default vector-DB-backed implementation; (6) how plugin `priority` and `dependencies` work at load time.

**Source pointer:** `https://github.com/elizaOS/eliza` — open source, MIT. ~18k stars.

**Priority:** P2

---

## Notes

**GenSX** (`gensx-inc/gensx`) — React-component-style workflow composition. Archived by owner October 2025, now read-only. Skip — dead project.

**Temporal (TypeScript SDK)** — Temporal is not an agent framework but a durable execution substrate. The Temporal + AI SDK integration (Activities wrap LLM calls, Workflow is the agent loop) is worth understanding for Verso's seam design, but the teardown would be of Temporal itself, not an agent framework. Read the `temporal.io/blog/building-durable-agents-with-temporal-and-ai-sdk-by-vercel` post as context, don't RE Temporal core.

**Google ADK TypeScript** — Google's Agent Development Kit for TypeScript. Optimized for Gemini/Vertex AI, model-agnostic in theory. Architecturally similar to the Python ADK (already partially covered). Low priority for Verso since it's tightly coupled to Google infrastructure.

**LangChain.js** — The LangChain abstraction layer (chains, runnables). The agent-relevant part is LangGraph.js (covered above). The core LangChain.js abstractions are not Verso-relevant.

**Spectrum (Photon)** — MIT TypeScript SDK for deploying agents to messaging platforms (iMessage, WhatsApp, Telegram). April 2026. Channel/transport abstraction only, no loop or memory architecture. Skip.

**Priority rationale:** P0 targets directly inform a Verso core decision about loop design (Inngest AgentKit), durability model (Cloudflare Agents), or multi-agent primitives (OpenAI Agents JS, LangGraph.js). P1 targets are strong references for specific subsystems (Convex for memory, VoltAgent for batteries-included calibration, Trigger.dev for CRIU vs. snapshot seam decision). P2 targets are architecturally interesting but niche or less directly action-able.
