# RE Targets: Multi-Agent Orchestration + Code-Exec Sandboxes

> Category: `multiagent-and-sandboxes`
> Authored: 2026-06-05
> Verso relevance: orchestration topologies that teach loop/seam architecture; sandboxes that teach how a framework exposes a safe code-execution escape hatch for Code Mode.

---

## Already Covered

The following seed names have existing teardowns in `teardowns/` and do NOT need re-RE for this category:

| File | Lines | What's covered | Verso-relevant finding |
|---|---|---|---|
| `AUTOGEN.md` | 1,581 | Actor-model runtime, typed msg-passing, GroupChat (RoundRobin/Selector/Swarm/MagenticOne), distributed gRPC runtime, DockerCommandLineCodeExecutor, `save_state`/`load_state` | Manual checkpoint (no auto-persistence), actor addressing layer is the hard part |
| `MAGENTIC_ONE.md` | 1,337 | Orchestrator+worker topology, task ledger + progress ledger prompts | Shared task-ledger is the multi-agent state primitive |
| `OPENAI_SWARM.md` | 889 | Handoff-as-tool pattern, context-variable passing, stateless hand-to-hand transfer | Minimal transfer protocol — context_variables dict is the state seam |
| `OPENAI_AGENTS_SDK.md` | 1,500 | Handoff as typed tool call, guardrails, tracing (14 span types), HITL interruption/approval, session backends, agent-as-tool for nesting | Full production multi-agent reference; `NextStepInterruption`/`RunState.approve()` is the HITL seam |
| `AGNO.md` | 852 | Loop-in-Model inversion, Team (delegate_task delegation tool), broadcast/route/tasks modes, Workflow (Step/Parallel/Condition/Loop/Router primitives) | Leader delegates via tool call — same primitive as OAI SDK but with deterministic Workflow layer |
| `SMOLAGENTS.md` | 983 | CodeAgent (executable Python as action), step serialization for replay, `AgentInterrupt`/HITL | Code-as-action (not JSON tool calls) — the alternative action primitive |
| `METAGPT.md` | 1,170 | Role/Environment/Memory SOP-driven orchestration, structured output via Pydantic schemas | SOP as agent specification layer |
| `CREWAI.md` | 2,283 | Crew/Role/Task/Process orchestration, manager-agent for hierarchical crews, task delegation | Hierarchical with manager LLM; task as first-class typed unit |
| `CREWAI_PLUS.md` | 881 | CrewAI + Flows (event-driven Python state machines), `@start`/`@listen`/`@router` decorators | Event-driven state machine wrapping agentic crews — durable seam precursor |
| `LANGGRAPH.md` | 2,063 | Pregel/BSP superstep scheduler, per-step checkpointing, time-travel, `interrupt_before`/`interrupt_after`, SqliteSaver/PostgresSaver, `Send` for dynamic edges | Gold standard for checkpoint-per-step; Checkpointer ABC is the durable-seam interface to copy |
| `PYDANTIC_AI.md` | 789 | `pydantic_graph` state-machine loop (`UserPromptNode → ModelRequestNode → CallToolsNode`), `GraphRun.next()` for external stepping, `FullStatePersistence` snapshot per node, `CallDeferred` + `ApprovalRequired` for HITL, deferred tool results for async | Closest existing model to Verso's tactical↔durable seam: graph is the loop, persistence is pluggable, stepping is external |
| `STRANDS.md` | 427 | Event-loop-cycle (recursive Bedrock Converse), `ConcurrentToolExecutor`, `INTERRUPT` HITL, `FileSessionManager`/`S3SessionManager`, `experimental/checkpoint/` | HITL via interrupt-state save/restore; session manager = durable seam without a graph DSL |
| `AGENCY_SWARM.md` | 1,052 | Agency/Agent/Thread as first-class objects, tool validation, send_message as cross-agent primitive | Thread as the state carrier — no new seam lessons beyond OAI SDK |
| `CAMEL_AI.md` | 802 | Role-playing society, Critic/Judge agents, memory module taxonomy | Society simulation pattern; not directly useful for Verso's seam |
| `TASKWEAVER.md` | 1,153 | Planner + CodeInterpreter agent, code execution as primary action, session-scoped context | Code-first multi-agent — good contrast with JSON-tool-call agents |
| `LETTA.md` | 2,063 | MemGPT virtual context (core/recall/archival memory blocks), self-editing memory via tool calls, compaction model, per-agent persisted storage | Typed memory blocks + agent-managed editing = the memory primitive Verso should study |
| `MODAL.md` | 438 | Container ASGI bridge, gRPC-stream-to-ASGI shim, lifespan manager — closed cloud backend | Container ASGI shim only; cloud backend not reverse-engineerable |
| `MS_AGENT_FRAMEWORK.md` | 357 | Pregel Workflow (superstep runner, per-superstep checkpoint, `graph_signature_hash` validation, Durable Functions + CosmosDB backend), typed HITL via `ctx.request_info`, AutoGen/SK orchestration patterns compiled to Workflow | Best production-grade Pregel implementation; checkpoint validation by graph hash is novel |
| `SEMANTIC_KERNEL.md` | 1,352 | SK process framework, Kernel/Plugin/Filter layers, Sequential/Concurrent/Handoff patterns now compiled to MAF Workflow | Largely superseded by MS_AGENT_FRAMEWORK teardown |
| `GOOGLE_ADK.md` | deep | Runner/session/event-loop, `SingleFlow`→`AutoFlow` by one processor, `transfer_to_agent` enum-constrained tool, state prefix scoping (`app:`/`user:`/`temp:`), ParallelAgent race condition on state | Transfer-by-one-processor is the cleanest multi-agent delta; state prefix scoping is a typed memory pattern Verso should adopt |
| `MISTRAL_AGENTS_API.md` | 855 | Server-side multi-agent (no client loop), declarative handoffs, `code_interpreter` sandboxed Python, `agent.handoff.*` SSE events | Server-side loop vs client-side loop contrast; declarative handoffs = pure routing config |

**Not covered (seed names):** E2B, Daytona, microsandbox, Cloudflare Sandboxes / Dynamic Workers, Parlant, Temporal, DBOS, Inngest.

---

## RE Targets

### E2B

**What it is:** Hosted Firecracker-microVM sandbox infrastructure for AI agent code execution; each sandbox is an isolated VM started from a pre-warmed snapshot in ~150ms; open-source infra repo (`e2b-dev/infra`) with closed cloud orchestrator.

**Why for Verso:** Verso's Code Mode needs a safe escape hatch for executing agent-generated code. E2B is the production reference for *how* to offer that: Firecracker microVM per request, UFFD-backed lazy snapshot resume, gRPC real-time channel from agent to sandbox, filesystem + process + network API surface that maps cleanly to a Python `Sandbox` object. The Python SDK API (`sandbox.commands.run()`, `sandbox.filesystem.*`, template snapshots) defines the contract Verso should expose for its code-execution adapter. The open infra repo shows the resume mechanism (Userfaultfd page-fault handler + 4 KiB diff deduplication against base templates) — this is the implementation Verso's sandbox adapter would wrap.

**What to RE:** The `e2b-dev/infra` repo (Go, 86%): specifically `fc.Process` struct lifecycle, the UFFD snapshot/resume path (memfd + lazy page-fault handler, `uffdReady` channel), Nomad + Consul integration, sandbox daemon wire protocol (REST for lifecycle, gRPC for real-time). Then `e2b-dev/E2B` (Python SDK): `Sandbox` class, `commands.run()`, `filesystem`, `process`, template API — the surface that becomes Verso's `CodeSandbox` protocol. Secondary: how templates are built (custom Docker images + snapshot) and how session TTL/timeout is configured.

**Source pointer:** `github.com/e2b-dev/infra` (Go infra, open-source); `github.com/e2b-dev/E2B` (Python/TS SDK, open-source); `github.com/e2b-dev/code-interpreter` (high-level code-interpreter SDK); `e2b.dev/docs` for API reference. Cloud backend closed, but infra repo is the architecture.

**Priority: P0** — directly shapes Verso's Code Mode sandbox adapter design.

---

### Daytona

**What it is:** Open-source "composable computer" sandbox platform (65k+ GitHub stars, Apache 2.0) for AI agents; each sandbox is a full isolated computer (dedicated kernel, filesystem, network stack, vCPU/RAM/disk) with stateful snapshot/resume; written in TypeScript (42%), Go (15%), Python SDK.

**Why for Verso:** E2B vs Daytona is the key comparison for Verso's sandbox choice: E2B = microVM + strong isolation + ephemeral-first; Daytona = container-based + stateful workspace + long-running sessions (no 24h cap vs E2B's 24h). Daytona's daemon-inside-sandbox architecture (a code-execution agent running inside the sandbox that handles `process.code_run()`) is the pattern for Verso's "agent controls its own execution environment." The Python SDK (`daytona.create()`, `sandbox.process.code_run()`, snapshot/resume API) defines an alternative surface to E2B. The open-source server makes the full architecture readable.

**What to RE:** `github.com/daytonaio/daytona` — the NestJS API server (sandbox CRUD, snapshot triggers), the Go CLI and daemon-inside-sandbox (the code-execution agent: how it handles `process.code_run`, filesystem ops, language runtime management), and the snapshot/resume mechanism. Python SDK: `Daytona`, `DaytonaConfig`, `Sandbox`, `sandbox.process`, `sandbox.filesystem` — the full API surface. Compare snapshot semantics to E2B's UFFD model.

**Source pointer:** `github.com/daytonaio/daytona` (open-source, full stack); `pip install daytona` for Python SDK; `daytona.io/docs` for API reference.

**Priority: P0** — direct alternative to E2B; Verso needs to pick one or make both pluggable; understanding both fully is required.

---

### microsandbox

**What it is:** Local-first, self-hosted microVM sandbox library (Apache 2.0, ~4,700 stars, built in Rust by Zerocore AI / YC X26); uses `libkrun` hypervisor for hardware isolation; no server daemon — sandboxes spawn as child processes of the calling process; sub-100ms boot; OCI image compatible.

**Why for Verso:** microsandbox is the "zero-infrastructure" pole of the sandbox spectrum — you `pip install microsandbox` and VMs spawn as child processes. No remote API, no orchestrator, no credentials. This is the pattern for Verso's *local dev* Code Mode: run real isolated code locally without any cloud dependency. The embedded, rootless architecture (no daemon required) is novel vs E2B (cloud) and Daytona (server+daemon). The Python/TS/Go/Rust SDK (builder pattern: `Sandbox::builder("image").create()`, `.exec()`, `.stop_and_wait()`) defines the simplest possible sandbox surface. The MCP server integration (sandboxes expose Skills as MCP tools) is a concrete example of sandbox↔tool-system integration.

**What to RE:** `github.com/superradcompany/microsandbox` — the Rust core: how `libkrun` is invoked, child-process spawning, rootless operation, OCI image handling, networking isolation (programmable from outside). Python SDK: builder pattern, `exec()` return type, process/filesystem API. The MCP integration layer (Skills): how a running sandbox becomes an MCP server with tools.

**Source pointer:** `github.com/superradcompany/microsandbox` (open-source, Rust + multi-language SDKs).

**Priority: P1** — strong reference for local/dev sandbox adapter; P0 if Verso wants a zero-infrastructure local Code Mode.

---

### Cloudflare Dynamic Workers + Sandboxes GA

**What it is:** Two complementary Cloudflare primitives (both GA April 2026): (1) **Dynamic Workers** — V8-isolate-based ephemeral code sandboxes that spawn in milliseconds from LLM-generated JS strings at runtime, 100x faster than containers; (2) **Cloudflare Sandboxes** — persistent full Linux environments (powered by Containers) for long-horizon agent work (install deps, run tests, multi-language builds), with snapshot-based recovery (2s restore vs 30s cold start).

**Why for Verso:** The two-tier design is directly instructive for Verso: V8 isolates for fast ephemeral tool-function execution (when the tool IS the code), full Linux sandboxes for long-running agent sessions (when the agent lives in the sandbox). The Dynamic Worker Loader API's `globalOutbound: null` for network isolation and credential-injection via egress proxy is the security model for Verso's sandbox integration. The Cap'n Web RPC bridge (generated JS calls typed TypeScript parent methods across isolate boundaries without perceiving isolation) is the cleanest example of "typed tool calls across a security boundary."

**What to RE:** Cloudflare blog posts (`blog.cloudflare.com/dynamic-workers/`, `blog.cloudflare.com/sandbox-ga/`) are the primary source — architecture is documented but the implementation is closed. Focus on: the Dynamic Worker Loader API surface (code string input, environment bindings, `globalOutbound`, RPC stubs), the Durable Object Facets model (per-dynamic-worker SQLite DB), and the Sandboxes API (persistent Linux env, snapshot/restore semantics, PTY support, filesystem watching). The Sandbox SDK docs (`developers.cloudflare.com/sandbox/`) are public. Limitation: V8 isolate internals and the Workers runtime are closed source.

**Source pointer:** `blog.cloudflare.com/dynamic-workers/`; `blog.cloudflare.com/sandbox-ga/`; `developers.cloudflare.com/sandbox/` (SDK docs); `cloudflare.com/products/sandboxes/`. Closed runtime — probe via blog + SDK docs.

**Priority: P1** — the two-tier isolate+container model is the reference architecture for Verso's ephemeral vs persistent code execution modes.

---

### Parlant

**What it is:** Open-source (Apache 2.0) agent control framework by emcie-co focused on per-turn behavioral guardrails via declarative Guidelines (condition-action pairs with dependency/exclusion relationships); dynamically narrows context each turn to only matching guidelines; targets compliance-critical, customer-facing agents.

**Why for Verso:** Parlant's *guideline matching engine* is a concrete implementation of what Verso calls "context engineering at the framework level." The mechanism — evaluate all guidelines each turn, select matching ones, inject only the relevant instructions + tools into the LLM context — is the operationalization of "context narrowing" as a first-class primitive. Verso's context engineering layer should know this pattern. The Journeys system (multi-turn SOPs with state transitions and branching) is a simpler alternative to LangGraph's graph for conversation workflows. The Observations model (tools only activate when their matching observation fires, not always available) is a novel tool-presence filtering pattern that reduces false-positive tool invocations.

**What to RE:** `github.com/emcie-co/parlant` — the guideline evaluation engine (how conditions are matched per turn, the dependency/exclusion graph), the context assembly step (what gets injected vs excluded), the `Journeys` state machine, the `Observations` → tool-activation binding, the composition modes (fluid vs strict/canned). Python client API: `create_guideline`, `create_journey`, `create_observation`, `@p.tool` decorator. The per-turn narrowing algorithm is the architectural core — trace it from user message to assembled context.

**Source pointer:** `github.com/emcie-co/parlant` (open-source, Python); `parlant.io/docs` for API reference.

**Priority: P1** — teaches Verso's context-engineering layer a concrete guideline-matching + per-turn narrowing pattern not present in any already-covered framework.

---

### Temporal (Python SDK + AI agent patterns)

**What it is:** Distributed durable execution platform (not a framework); workflows are Python functions decorated with `@workflow.defn`; activities (`@activity.defn`) are the non-deterministic units (LLM calls, tool calls); the server records an immutable Event History; replay reconstructs in-memory state without re-executing completed activities; workers are long-running processes that poll task queues.

**Why for Verso:** Temporal is the gold-standard implementation of the *durable seam* concept that is Verso's headline primitive. The Workflow (deterministic coordination) / Activity (side-effecting unit) split is the exact same distinction as Verso's tactical loop vs durable seam — Temporal proves this separation is production-viable at 9.1 trillion lifetime executions. For Verso, the lesson is: (a) what the Activity boundary buys (retry, timeout, exactly-once semantics), (b) how replay works without re-executing LLM calls (event history + memoization), (c) how `@workflow.signal` / `@workflow.update` implement HITL without interrupting the loop, (d) the `temporalio/sdk-python` decorator API as a reference for what Verso's `@durable` decorator should feel like. The Feb 2026 OpenAI Agents SDK integration (wrapping an agent's ReAct loop as a Temporal Workflow) is the exact Verso use case.

**What to RE:** `github.com/temporalio/sdk-python` — `@workflow.defn` + `@activity.defn` decorator mechanics, the `workflow.execute_activity()` call (schedules an activity command into event history, blocks until result), `@workflow.signal`/`@workflow.update` for HITL, the determinism checker (non-determinism detection during replay). Temporal docs AI cookbook: `docs.temporal.io/ai-cookbook/agentic-loop-tool-call-openai-python` (the canonical agent loop pattern). Focus on: what the event history looks like for a ReAct loop with tool calls, how replay skips completed LLM calls, how signal/update enable human approval without crashing the workflow. Limitation: Temporal server is open-source (`github.com/temporalio/temporal`) but very large — focus on Python SDK and the AI agent integration examples.

**Source pointer:** `github.com/temporalio/sdk-python` (Python SDK, open-source); `docs.temporal.io/ai-cookbook/agentic-loop-tool-call-openai-python`; `pydantic.dev/docs/ai/integrations/durable_execution/temporal/`.

**Priority: P0** — Temporal is the canonical implementation of the durable seam that Verso's `--durable` flag must replicate. Reading the Python SDK decorators + event-history replay is mandatory before designing Verso's durable backend protocol.

---

### DBOS (dbos-transact-py)

**What it is:** Lightweight Python library for durable execution backed by Postgres — no external orchestration server required. `@DBOS.workflow` + `@DBOS.step` decorators checkpoint each step's result to Postgres; on crash/restart, completed steps are replayed from DB (never re-executed); deterministic replay guaranteed by constraint that workflows are pure coordination code. Official PydanticAI + LlamaIndex + OpenAI Agents SDK integrations via `DBOSAgent` wrapper.

**Why for Verso:** DBOS is the minimal-infrastructure pole of the durable execution spectrum (vs Temporal's distributed server). The `DBOSAgent(agent).run("query")` pattern — wrapping any agent's `.run()` call in a durable workflow with zero changes to agent code — is the exact integration model Verso should offer for its `--durable` flag. The checkpoint mechanism (step result → Postgres row before proceeding) is simpler than Temporal's event history but achieves the same property for single-machine deployments. For Verso: DBOS answers "what's the minimum Postgres schema and decorator API needed to make any Python agent durable?" — which informs the simplest possible Verso durable backend.

**What to RE:** `github.com/dbos-inc/dbos-transact-py` — `@DBOS.workflow` and `@DBOS.step` decorator implementation (what gets written to Postgres, when, and how replay works), the Postgres schema (workflow table + step output table), the recovery algorithm (startup scan for PENDING workflows, replay with checkpointed return values), the Conductor websocket integration (observability only, never in hot path), and the `DBOSAgent` wrapper for PydanticAI. Python API surface: `DBOS.start_workflow_async()`, `DBOS.set_event_async()`, `DBOS.sleep()`.

**Source pointer:** `github.com/dbos-inc/dbos-transact-py` (open-source, Python); `docs.dbos.dev/architecture`; `ai.pydantic.dev/durable_execution/dbos/`.

**Priority: P0** — answers "minimum viable durable seam over Postgres" with zero new infrastructure; directly informs Verso's default durable backend design.

---

### Inngest

**What it is:** Event-driven step-function workflow platform with Python (and TypeScript/Go) SDK; step memoization model: each `step.run(id, fn)` executes once, result persisted, subsequent executions inject stored result and skip; supports durable sleep, fan-out, cron, and event-triggered workflows; official agent-orchestration primitives in 2026 release.

**Why for Verso:** Inngest's `step.run()` memoization model is a third implementation of the durable seam — different from Temporal's event history (full replay) and DBOS's Postgres rows (step-level commit). Inngest's model is request/response based: each function invocation is a fresh HTTP call to the user's server; the platform replays by calling the function again and injecting memoized step results. This is the "serverless durable execution" pattern and directly applicable to Verso if users want to run durable agents in serverless environments (Vercel, Cloudflare Workers, Lambda). The `step.run` / `step.sleep` / `step.waitForEvent` API is the simplest durable primitive surface.

**What to RE:** `github.com/inngest/inngest` — the Python SDK: `@inngest.create_function`, `step.run(id, fn)` (how memoization keys are computed, when the result is stored, how replay injects it), `step.sleep`, `step.waitForEvent` (the HITL primitive). The server-side: how Inngest calls your function, how it knows which steps completed, the state envelope passed on each replay call. Focus on the memoization key scheme (step `id` string + function ID) and the state envelope format — these define the protocol Verso would need to implement for a Inngest-compatible durable backend.

**Source pointer:** `github.com/inngest/inngest` (open-source, Go + multi-language SDKs + server); `inngest.com/docs/features/inngest-functions/steps-workflows`.

**Priority: P1** — third durable-seam implementation pattern; serverless-compatible; teaches Verso the step-memoization model as alternative to full event-history replay.

---

## Notes

**Sandbox landscape summary (for Verso's Code Mode design decision):**

| Platform | Isolation | Startup | Session | Open source | Best for |
|---|---|---|---|---|---|
| E2B | Firecracker microVM | ~150ms (snapshot) | up to 24h | Infra repo open | Cloud-hosted, strong isolation, ephemeral |
| Daytona | Container (kernel shared) | <90ms | Unlimited, stateful | Full stack open | Long-running, stateful agent sessions |
| microsandbox | libkrun microVM | <100ms | Process lifetime | Full open | Local dev, zero infrastructure, rootless |
| Cloudflare Dynamic Workers | V8 isolate | Milliseconds | Per-request | Closed runtime | Ultra-fast ephemeral JS tool execution |
| Cloudflare Sandboxes | Container (full Linux) | 2s from snapshot | Persistent | Closed runtime | Long-horizon agent work on Cloudflare |

Verso recommendation: support E2B (cloud default) + microsandbox (local default) as pluggable `CodeSandbox` backends; read both fully before committing to the adapter protocol.

**Durable seam landscape (for Verso's `--durable` flag design):**

Three distinct implementation models already exist in production — Verso should read all three before designing its durable backend protocol:
1. **Temporal**: Event history → full replay (no re-execution of activities). Best for cross-service, long-running (days+), complex retry/timeout. Heavy infrastructure.
2. **DBOS**: Postgres step-commit → memoized replay. Zero new infrastructure. Single-machine sweet spot. PydanticAI integration is the reference for Verso's wrapper API.
3. **Inngest**: HTTP request/response + step-id memoization envelope. Serverless-compatible. Framework-agnostic. Teaches the "replay by function call + inject completed steps" model.

LangGraph's `Checkpointer` (already covered, `LANGGRAPH.md`) is the graph-native version. PydanticAI's `FullStatePersistence` (already covered) is the node-snapshot version. Verso's durable seam sits between DBOS (simplest) and Temporal (most powerful) — DBOS is the right starting point.

**Multi-agent: what's NOT worth RE-ing again:**
- OpenAI AgentKit (visual builder on top of Agents SDK — no new loop/seam primitives; Agents SDK teardown covers it).
- Northflank (managed platform, closed, blog posts only — no open source to read).
- CAMEL AI, Agency Swarm, OpenAgents — covered; diminishing returns for Verso.
- Dify — covered (344 lines, thin); but Dify's architecture is a visual workflow builder, not a loop/seam pattern.
