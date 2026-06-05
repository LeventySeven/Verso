# RE Targets: Python Agent Frameworks (Peers / Competitors)

**Category:** `py-frameworks`
**Purpose:** Identify which Python agent frameworks teach Verso something specific about its four headline concerns — the tactical↔durable seam, context engineering, typed memory, and evals/reliability — and which are already covered.
**Date compiled:** 2026-06-05

---

## Already Covered

The following have substantive teardowns in `teardowns/` (≥400 lines, Tier-1A source-read, file:line cites). Skip for fresh RE — reference the existing teardown instead.

| File | Lines | What it covers |
|---|---|---|
| `LANGCHAIN.md` | 1820 | LCEL Runnable graph, RunnableSequence, memory, callbacks |
| `LANGGRAPH.md` | 2063 | StateGraph, checkpointing (Postgres/Redis), HITL interrupt/resume, Pregel supersteps |
| `CREWAI.md` + `CREWAI_PLUS.md` | 2283+ | Crew/Role/Task, multi-agent collaboration patterns, sequential/hierarchical/consensual flows |
| `LETTA.md` | 2063 | MemGPT-lineage, paged memory (archival/recall/in-context), agent-server-as-service model |
| `LLAMAINDEX.md` | 1933 | QueryPipeline, workflows, tool routers, agent ReAct, structured extraction |
| `CLAUDE_AGENT_SDK.md` | 2465 | Skills/hooks/subagent dispatch, tool-use loop, context compaction, MCP integration |
| `BROWSER_USE.md` | 1899 | Browser-action agent loop, DOM context assembly, vision tools |
| `COMPOSIO.md` + deep files | 4000+ | Auth management, tool registry, MCP triggers, router |
| `PYDANTIC_AI.md` | 789 | pydantic_graph state-machine loop (BaseNode→typed transitions), FullStatePersistence per-node, streaming, Logfire integration |
| `AGNO.md` | 852 | Loop-in-Model design, zero-cost constructor, Background memory futures, Memory v2 as second LLM |
| `GOOGLE_ADK.md` | 648 | Async-generator event stream tree, runner/session, eval framework, A2A protocol |
| `OPENAI_AGENTS_SDK.md` | 1500 | Typed handoffs as tool calls, input/output guardrails, Runner loop, tracing (14 span types) |
| `OPENAI_SWARM.md` | 889 | Swarm handoff-via-return, minimalist multi-agent blueprint |
| `AUTOGEN.md` | 1581 | Actor-model runtime (AgentId, typed message-passing), GroupChat patterns (RoundRobin/Selector/Swarm/MagenticOne) |
| `DSPY.md` | 1566 | Signature+Module+Teleprompter compiler, prompt optimization, BootstrapFewShot, MIPROv2 |
| `SMOLAGENTS.md` | 983 | Code-as-action (CodeAgent), LocalPythonExecutor (AST-walker), ToolCallingAgent, multi-agent nesting |
| `HAYSTACK.md` | 1220 | Typed-DAG @component pipeline, priority-queue scheduler, breakpoints/snapshots, Agent-as-component |
| `SEMANTIC_KERNEL.md` | 1352 | Kernel plugin registry, filter pipeline (3 chains), Stepwise planner, handoff function synthesis |
| `MS_AGENT_FRAMEWORK.md` | 357 | FunctionInvocationLayer (max_iterations=40), Workflow graph (Pregel supersteps, HITL ports), SK+AutoGen convergence — **thin, worth extending** |
| `STRANDS.md` | 427 | Recursive event_loop_cycle, MAX_ATTEMPTS=6, hooks, experimental checkpoint, SessionManager — **thin, worth extending** |
| `AGENCY_SWARM.md` | 1052 | Role-based self-building teams, custom BaseTool pattern |
| `CAMEL_AI.md` | 802 | Role-play dialogue loop, Society of Mind simulation, task/critic agents |
| `MAGENTIC_ONE.md` | 1337 | Orchestrator + Ledger plan/replan pattern, specialized workers (WebSurfer, FileSurfer, Coder, Terminal) |
| `TASKWEAVER.md` | 1153 | Code-interpreter-first agent, session/round/post architecture, experience pool |

**The brief explicitly lists as already in teardowns:** LangChain, LangGraph, CrewAI, Letta, Composio, LlamaIndex, Claude Agent SDK, Browser-Use — confirmed above.

---

## RE Targets

### Burr (Apache Burr — apache/burr)

**What it is:** State-machine-first Python agent framework. Every application is an explicit `ApplicationBuilder`-assembled graph of `@action`-decorated functions with typed `State`, persistence, and a built-in observability UI. Apache Incubating as of 2025.

**Why for Verso:** Burr is the cleanest open-source implementation of the **tactical↔durable seam**. It separates the *graph definition* (`GraphBuilder`) from the *application instance* (which binds persistence, identifiers, and entry point) — meaning the same graph runs in-memory (no persister) or durably (SQLite/Redis/Postgres persister) by swapping one constructor arg. The `halt_before`/`halt_after` mechanism is the HITL model Verso needs to study. Its `@action` decorator pattern (pure function → pure state transition) is close to Verso's `@tool` philosophy. It has no competing Python frameworks that model this exact seam — LangGraph uses checkpoints-inside-nodes, Pydantic AI snapshots inside the runner, but Burr makes the state machine boundary the explicit unit.

**What to RE:** (1) `ApplicationBuilder.with_state_persister()` — how the in-memory/durable seam is actually implemented (is it a wrapper, a subclass, a context manager?); (2) the `halt_before`/`halt_after` state machine pause protocol and how it surfaces to the caller; (3) the `@action` contract (`reads`, `writes` typed state keys) and how state is typed/validated; (4) the persistence interface (`BaseStatePersister` + built-in backends) and the state serialization format.

**Source pointer:** `github.com/apache/burr` — fully open source (Apache-2.0), Python package in `burr/` directory, ~10k LoC. Also `burr.apache.org` docs.

**Priority:** P0 — directly models Verso's core seam decision.

---

### Marvin (PrefectHQ/marvin — v3.0)

**What it is:** Ambient-intelligence / task-centric Python agent library by Prefect. Marvin 3.0 merged the ControlFlow engine (Prefect-backed task orchestration) with Marvin 2.0's ergonomic high-level functions (`cast`, `classify`, `extract`, `generate`). The agentic engine uses Pydantic AI for LLM calls; structured output is the primary primitive, not the loop.

**Why for Verso:** Marvin's `Task` + `Thread` model is the strongest example of **task-centric context engineering** in the Python ecosystem. A `Task` has an explicit objective, a result type (Pydantic model), and an assigned set of agents. A `Thread` is an isolated conversation context that multiple tasks share — this is a direct implementation of Verso's "typed memory" and "context scoping" concerns. Marvin 3.0's conversion of ControlFlow's `@flow` into Prefect flows also shows how to integrate a pure Python agent with a durable workflow engine without a custom graph DSL.

**What to RE:** (1) `Thread` implementation — how it stores and retrieves conversation history, whether it's an object or a context manager; (2) `Task` result typing — how Pydantic type annotations become the LLM's output schema; (3) the agent loop — which file drives model calls, how multi-agent round-robin/moderation is implemented; (4) integration seam with Pydantic AI (`marvin/engine/` or similar).

**Source pointer:** `github.com/PrefectHQ/marvin` (MIT). Archived ControlFlow at `github.com/prefect-archive/ControlFlow` for the pre-3.0 engine, which is still architecturally instructive.

**Priority:** P0 — directly teaches typed context scoping and task-result-as-type contract.

---

### Griptape (griptape-ai/griptape)

**What it is:** Modular Python agent framework with explicit Pipeline (sequential), Workflow (parallel DAG), and Agent (single-task) structure types, plus a unique `TaskMemory` mechanism that keeps large tool outputs off the prompt. Acquired by Foundry (M&E software) in February 2026; open-source (Apache-2.0) remains intact.

**Why for Verso:** Griptape's `TaskMemory` / off-prompt storage is the most developed implementation of **context engineering by exclusion** in any open-source Python framework. When a tool returns a large output, Griptape stores it in a named `TaskMemory` artifact and injects only a reference token into the prompt — the LLM must explicitly call a memory-access tool to read it. This is directly relevant to Verso's context engineering design (what goes in the context window vs. what stays in memory). No other teardown in this repo covers this pattern at code level. The Pipeline/Workflow/Agent structure typing is also instructive for Verso's "pluggable edges" concept.

**What to RE:** (1) `TaskMemory` implementation — how the artifact store works, what the reference token looks like in the prompt, how the memory-access tool is synthesized; (2) `RuleSets` and `Rule` objects — Griptape's prompt-injection layer for behavioral constraints; (3) `Pipeline.run()` vs `Workflow.run()` — the sequential vs parallel execution model and how tasks hand off; (4) Driver abstraction — how provider-agnostic memory and embedding backends are plugged in.

**Source pointer:** `github.com/griptape-ai/griptape` (Apache-2.0). Docs at `docs.griptape.ai`.

**Priority:** P1 — strong reference for off-prompt context management, a pattern Verso needs to decide on.

---

### Atomic Agents (BrainBlend-AI/atomic-agents)

**What it is:** Minimal Python agent framework built on Instructor + Pydantic. Each agent has an explicit `input_schema` (Pydantic), `output_schema` (Pydantic), `system_prompt_generator`, and `context_providers`. The entire system is statically typed via Pydantic generics; v2.0 added generic type parameters for agent+tool composition.

**Why for Verso:** Atomic Agents is the most direct proof-of-concept for Verso's `@tool` typed contract: in Atomic Agents, tools have typed input/output schemas, and the agent's result is a Pydantic model, not a string. The `ContextProvider` abstraction — a class that injects dynamic context into the system prompt at runtime — is a clean implementation of Verso's "first-class context engineering" goal. No state machine, no graph engine — just typed I/O at every boundary. Studying what this buys and what it can't do (e.g. no native checkpointing) calibrates Verso's design tradeoffs.

**What to RE:** (1) `BaseAgent.__call__` — the loop; how many turns, how termination is decided; (2) `ContextProvider` protocol — the exact interface and how multiple providers compose; (3) how Instructor's structured-output mechanism is wrapped (`.chat()` or equivalent); (4) v2.0 generic type parameter mechanism for `BaseAgent[InputSchema, OutputSchema]`.

**Source pointer:** `github.com/BrainBlend-AI/atomic-agents` (MIT). Docs at `brainblend-ai.github.io/atomic-agents/`. PyPI `atomic-agents` v2.8.0+.

**Priority:** P1 — directly implements typed context injection and typed tool I/O contracts at small scale, useful as a calibration target for Verso's API surface.

---

### Mirascope (Mirascope/mirascope)

**What it is:** Self-described "LLM anti-framework." Provides a `@llm.call` decorator that wraps a plain Python function into a provider-agnostic LLM call with typed return (Pydantic response model). No agent runtime is required — tools, streams, and structured outputs are decorator arguments. The "React" analogy is deliberate: Mirascope is the component library, not the app framework.

**Why for Verso:** Mirascope solves the problem Verso's `@tool` decorator needs to solve: how to make a plain Python function into a typed, provider-agnostic LLM primitive without requiring the user to inherit from a base class or register in a registry. The decorator-composition model (one function, multiple decorator facets: provider, response_model, tools, stream) is the clearest open-source example of this design pattern. It also shows how to handle the provider-agnostic return type (`CallResponse`) when the underlying provider objects differ. Studying Mirascope clarifies whether Verso's `@tool` decorator approach is sufficient or needs a richer registration mechanism.

**What to RE:** (1) `@llm.call` implementation — how the decorator captures provider, model, and return type at definition time; (2) `CallResponse` unification — how divergent provider response objects are normalized; (3) Agent state management — Mirascope agents use `BaseMessageParam` history; how that is accumulated and scoped; (4) how `response_model=` maps to Instructor under the hood.

**Source pointer:** `github.com/Mirascope/mirascope` (MIT). Python implementation in `mirascope/python/`. Docs at `mirascope.com/docs`.

**Priority:** P1 — directly teaches the decorator-as-tool-contract pattern that is Verso's primary tool path.

---

### PocketFlow (The-Pocket/PocketFlow)

**What it is:** 100-line, zero-dependency Python framework. Core primitive: `Node` (a Python class with `prep → exec → post` lifecycle), connected into a `Flow` by action-labeled edges. Flows compose hierarchically (Flow-as-Node). No LLM calls in the core — pure orchestration graph.

**Why for Verso:** PocketFlow is the extreme-minimalist reference point. It shows what the irreducible core of an agent graph is, stripped of every abstraction. This is directly useful for Verso's "clean async ReAct loop as default" goal: if the loop is the right primitive, what does the minimum viable loop look like? PocketFlow also demonstrates the `prep → exec → post` node lifecycle pattern, which is an alternative to Verso's `@tool` path worth understanding (and explicitly deciding to adopt or reject). The "Flow as Node" nesting is the simplest multi-agent composition model in the ecosystem.

**What to RE:** (1) Full 100-line core — read `pocketflow/__init__.py` literally line by line; (2) how action-labeled edges implement conditional branching; (3) the async `AsyncFlow`/`AsyncNode` extension; (4) what the framework does NOT do (no memory, no context, no evals) — the negative space is as instructive as the positive.

**Source pointer:** `github.com/The-Pocket/PocketFlow` (MIT). ~100-line core, then templates folder. Paper: `arxiv.org/pdf/2504.03771`.

**Priority:** P1 — minimum-viable-loop reference; Verso should be able to say exactly where it diverges from this floor.

---

### Julep (julep-ai/julep)

**What it is:** Open-source platform for serverless AI workflows with durable, multi-step task execution. Core: `Agent` (identity + memory config), `Task` (YAML/JSON-defined multi-step workflow), `Session` (persistent conversation context with configurable memory). Backend uses Temporal as the workflow engine. "Firebase for AI agents."

**Why for Verso:** Julep is the reference implementation of **persistent session as first-class primitive**, distinct from per-request agents. Its `Session` stores conversation history across indefinite pauses/resumes, has configurable memory modes (recall/archival/in-context), and tasks can execute autonomously while the session remains open. This directly addresses Verso's "same agent in-memory OR event-sourced via one flag" seam — Julep chose Temporal under the hood. Studying the session/task/agent separation also clarifies how Verso should decompose its own memory model.

**What to RE:** (1) `src/scheduler/` — how Temporal activities wrap each task step; (2) `Session` memory modes implementation — what SQL schema / vector store backend backs archival memory; (3) Task step types (prompt / tool_call / evaluate / wait_for_input / foreach / map_reduce / if-else) and how each maps to a Temporal activity; (4) Agent identity vs Session state separation — where does per-agent knowledge end and per-session context begin?

**Source pointer:** `github.com/julep-ai/julep` (Apache-2.0). Architecture: `src/` is a polyglot monorepo (TypeScript API, Python scheduler, Go services).

**Priority:** P2 — interesting as a "Temporal-backend for agents" reference, but closed infrastructure portions limit what RE can extract. Good calibration for memory model design.

---

### Microsoft Agent Framework (microsoft/agent-framework) — Extension

**What it is:** GA April 2026. Unified successor to Semantic Kernel + AutoGen. Two primitives: `ChatAgent` (function-calling loop, max_iterations=40) and `Workflow` (Pregel superstep graph with HITL approval ports). Python + .NET.

**Why for Verso (extension):** The existing teardown (`MS_AGENT_FRAMEWORK.md`, 357 lines) is thin. The `Workflow` graph is the most important section for Verso: it implements a Pregel/BSP multi-agent graph with typed state, supersteps, and human-approval ports — the closest Microsoft has gotten to the tactical↔durable seam. The `_compaction.py` module (context compaction, not yet covered) is directly relevant to Verso's context engineering goals.

**What to RE (gap fill):** (1) `_workflows/_workflow.py` — `run_until_convergence`, superstep mechanics, convergence condition; (2) `_workflows/_edge.py` — edge types and conditional routing; (3) `_compaction.py` — what triggers compaction, what the algorithm does; (4) `_sessions.py` — thread/session persistence model; (5) the HITL approval port protocol (how `halt_before` equivalent surfaces to the caller).

**Source pointer:** `github.com/microsoft/agent-framework` (MIT). `python/packages/core/agent_framework/`.

**Priority:** P1 — existing teardown is too thin; the Workflow superstep engine is directly relevant to Verso's durable seam.

---

### Strands (strands-agents/sdk-python) — Extension

**What it is:** AWS's compact, model-driven, recursive event loop agent SDK. Existing teardown covers the core `event_loop_cycle` recursion, retry constants, and tool execution. Thin on: experimental checkpoint/steering, SessionManager persistence, multi-agent Graph/Swarm internals.

**Why for Verso (extension):** The existing teardown (`STRANDS.md`, 427 lines) is thin on the durability half. The `experimental/checkpoint/` module is the most direct implementation of "same agent, durable or not" in the AWS ecosystem. `SessionManager` is also uncovered — it is the in-process analog to Julep's persistent session.

**What to RE (gap fill):** (1) `experimental/checkpoint/` — how checkpoint state is serialized and restored; (2) `session/session_manager.py` — the session lifecycle, what state is kept; (3) `multiagent/graph.py` (1296 LoC) — the multi-agent graph topology and execution model; (4) `experimental/steering/` — what "steering" means in context.

**Source pointer:** `github.com/strands-agents/sdk-python` (Apache-2.0). `strands-py/src/strands/`.

**Priority:** P1 — checkpoint + session manager gap directly relevant to Verso's seam design; existing teardown too thin.

---

## Notes

**What the landscape looks like in mid-2026:**

1. **The seam problem is now the defining split.** Every major framework has picked a position: (a) pure in-memory loop (smolagents, PocketFlow, Atomic Agents, Mirascope), (b) graph-with-checkpointing (LangGraph, Haystack, Pydantic AI/pydantic_graph, MAF Workflow), or (c) external orchestrator (Julep via Temporal, OpenAI Agents SDK via the "sessions" API). Verso's "one flag" seam is novel — no framework does it cleanly at the Python level.

2. **Typed output is now table stakes.** Every framework launched after 2024 uses Pydantic as the output schema layer. The differentiator has shifted to *where* typing occurs: at the tool level (Mirascope, Atomic Agents), at the node level (Pydantic AI), at the task level (Marvin), or at the graph edge level (MAF).

3. **MCP has not displaced @tool.** Despite industry hype, every Python framework in this list either treats MCP as an opt-in adapter (OpenAI Agents SDK, Pydantic AI, Strands) or ignores it. The `@tool` / `@function` decorator remains the primary tool registration path across all frameworks.

4. **Evals are an unsolved gap.** Only DSPy has a first-class eval/optimization loop. Every other framework lists "observability" (tracing, logging) as their eval story. This is a genuine opportunity for Verso.

5. **Context engineering is underdeveloped.** Only Griptape (off-prompt TaskMemory), Haystack (typed socket connections), and Pydantic AI (per-node state snapshots) treat context assembly as an architectural concern. Most frameworks treat context as "the messages list" with no structure.

6. **Microsoft Agent Framework (GA April 2026)** is the enterprise consolidation play — merges SK + AutoGen, adds A2A + MCP integration. It is the most complete framework on paper but also the most complex. Worth watching as a "what enterprise convergence looks like" reference.

7. **Targets NOT worth RE-ing for Verso:** LiveKit Agents (voice/WebRTC, orthogonal domain), Temporal SDK (infrastructure, not an agent framework), Dagster/Prefect/Flyte (data orchestration, not agent orchestration). CAMEL AI, Agency Swarm, TaskWeaver, MetaGPT already covered and don't add new patterns for Verso's concerns.
