# RE Targets — Wildcard: Newest 2026 Agent-Infra (Not In Prior Categories)

**Category:** `discovery-wildcard`
**Purpose:** Surface genuinely novel 2026 launches in agent infrastructure that are not already covered
by a prior category file and teach Verso something specific.
**Date compiled:** 2026-06-05

---

## Already Covered

The following appeared in the search sweep but are already claimed by a prior category file or an
existing teardown. Do not duplicate.

| Name | Where covered |
|---|---|
| DBOS (dbos-transact-py) | `durable-execution.md` — P0, Postgres-native checkpoint/seam |
| Temporal Python SDK (Replay 2026 features) | `durable-execution.md` — P0, event-history replay, signal/update |
| Inngest | `durable-execution.md` — P1, SHA-1 step hashing, memoization protocol |
| LangGraph Checkpointing | `durable-execution.md` — P0, superstep Pregel model |
| Hatchet | `durable-execution.md` — P0, four durable primitives |
| Resonate | `durable-execution.md` — P1, generator-yield model |
| Restate | `durable-execution.md` — P0, journal-per-invocation |
| Mem0 | `memory-systems.md` — P0, AUDN extraction loop |
| Graphiti / Zep | `memory-systems.md` — P0, bi-temporal knowledge graph |
| Hindsight | `memory-systems.md` — P0, Postgres-only TEMPR stack |
| Honcho | `memory-systems.md` — P1, peer-centric async reasoning |
| Burr (Apache) | `py-frameworks.md` — P0, state-machine seam |
| Marvin 3.0 | `py-frameworks.md` — P0, Task + Thread context scoping |
| Griptape | `py-frameworks.md` — P1, off-prompt TaskMemory |
| fastmcp | `tools-mcp.md` — P0, MCP server/client reference |
| Arcade.dev | `tools-mcp.md` — P1, auth-interrupt HITL pattern |
| Langfuse | `eval-observability.md` — P0, trace schema + eval scheduler |
| Microsoft Agent Framework (AutoGen+SK merge, v1.0 GA) | `teardowns/MS_AGENT_FRAMEWORK.md` (357 lines, **thin**) |
| Google ADK + AX (Agent Executor) | `teardowns/GOOGLE_ADK.md` (648 lines) — note: AX is a separate runtime not yet covered |
| Agentspan | NOT yet in any file — but it wraps Conductor (Java server) and provides thin Python/TS SDK on top; the underlying primitive is Conductor-OSS, not a novel agent loop. Lower value for Verso than pure Python alternatives — see Notes. |

---

## RE Targets

### Anthropic Managed Agents — Session/Harness/Sandbox Triad

**What it is:** Anthropic's production hosting layer for Claude agents, described in their engineering
blog "Scaling Managed Agents: Decoupling the brain from the hands" (April 8 2026). Three first-party
virtualised entities: Session (append-only event log), Harness (the loop that drives Claude and routes
tool calls), Sandbox (isolated container for code execution). Harness and Sandbox are decoupled so any
Harness instance can resume any Session.

**Why for Verso:** This is the most important architecture paper published in the agent-infra space in
2026 and directly addresses Verso's headline design question. The Session/Harness/Sandbox triad is the
only published production account of how to implement the **tactical↔durable seam at scale**: the
Session is the durable event log; the Harness is the loop that runs against it (stateless, horizontally
scalable); the Sandbox is the side-effectful execution environment. Key numbers: p50 time-to-first-token
dropped ~60% and p95 dropped >90% after decoupling. Lazy sandbox init — provisioned only when Claude
emits a tool call, not at session start — is the right default for Verso's seam too. The credential
vault/proxy pattern (OAuth tokens never enter the sandbox; harness routes tool calls through an MCP
proxy that injects credentials at the network boundary) is the production answer to Verso's auth-gated
tool design. The persistent memory model (versioned FUSE-mounted filesystem, not a vector DB API) shows
an alternative to vector retrieval for session-spanning state. The engineering blog is public; the
Claude Agent SDK open-source repo partially exposes the harness contract.

**What to RE:** (1) `anthropic.com/engineering/managed-agents` — full architecture text, extract the
exact Session/Harness/Sandbox interface contract and the lazy-sandbox init trigger condition.
(2) `github.com/anthropics/claude-code` and the Claude Agent SDK — the Harness loop implementation,
how it serialises tool calls to/from the Session log, how it detects which Sandbox is needed.
(3) The memory API: how the `memory/` FUSE directory is exposed to the container, the read/write
lifecycle across session restarts.
(4) Behavioral probing: start a managed-agents session, send a request that requires code execution,
measure time-to-first-token and compare with one that doesn't — confirms the lazy-init story.
(5) Check `teardowns/CLAUDE_AGENT_SDK.md` (2465 lines) for the SDK-level harness loop that's already
been read; what's missing is the Session log format and Sandbox lifecycle at the managed-infra level.

**Source pointer:** `anthropic.com/engineering/managed-agents` (public engineering blog, primary source);
`github.com/anthropics/claude-code` (open source harness code); `teardowns/CLAUDE_AGENT_SDK.md` (existing
teardown — extend it with Session/Sandbox layer, don't re-do it).

**Priority:** P0 — directly models Verso's seam: event-log session, stateless harness, lazy sandbox,
credential boundary. Published numbers give Verso a latency target.

---

### Google AX (Agent Executor) — Event-Log + Snapshotting Distributed Runtime

**What it is:** Open-source distributed agent runtime launched May 2026 (`github.com/google/ax`). AX
coordinates agentic loops with an event log + snapshotting backend; local and remote actors communicate
via a Router; checkpoints can be forked (`ax fork`) to branch trajectories. Separate from Google ADK
(which is covered) — AX is the runtime layer underneath, framework-agnostic.

**Why for Verso:** AX is the only open-source implementation of a distributed event-log runtime for
agents that is explicitly separate from the framework (it wraps ADK agents, LangGraph agents, OpenAI
Agents SDK agents). This is the architecture pattern Verso's `durable=True` backend should study as an
alternative to Temporal's event-history replay: AX's event log + snapshotting avoids the determinism
sandbox requirement entirely — any code can run in the actor because the log records outputs, not
replays inputs. The `ax fork` trajectory branching is the cleanest published implementation of
checkpoint-as-branch for eval and what-if scenarios — directly relevant to Verso's eval/reliability
feature. AX is currently in preview and actively changing, which makes reading the source now (before
APIs stabilise) the highest-value time to do it.

**What to RE:** `github.com/google/ax` — (1) the event log format (protobuf schema? JSON?), (2) the
snapshot format and how recovery picks the latest valid snapshot, (3) the Router/Controller/Actor
topology — what the Controller stores vs what each Actor sees, (4) `ax fork` implementation — how a
checkpoint is cloned and diverged, (5) the resumable streaming protocol (`ax attach` semantics —
replay events the client missed since sequence N), (6) how AX wraps an ADK agent (pass-through vs
message transform), (7) the HITL pause mechanism — how an actor suspends awaiting an external signal.

**Source pointer:** `github.com/google/ax` (open source, Apache-2.0, preview);
`cloud.google.com/blog/products/ai-machine-learning/agent-executor-googles-distributed-agent-runtime/`.

**Priority:** P1 — teaches the event-log-not-replay alternative to Temporal; `ax fork` is a direct
implementation of Verso's checkpoint-branch eval primitive. Still preview; source reading is the right
approach, not behavioral probing.

---

### Centaur (Paradigm/Tempo) — Multiplayer Self-Hosted Agent Runtime

**What it is:** Open-sourced May 2026 by Paradigm (`github.com/paradigmxyz/centaur`). A production
self-hosted agent runtime: Slack-interfaced, multi-user, Kubernetes-sandboxed, Postgres-checkpointed,
credential-proxied via `iron-proxy`. Core: FastAPI control plane + per-thread sandbox containers +
Python tool plugins with auto-generated REST endpoints + Postgres step checkpointing.

**Why for Verso:** Centaur is a rare production account (18 months of internal use at a major fund)
of an agent runtime that solves three Verso concerns simultaneously: (1) the **credential boundary**
— `iron-proxy` sits between the sandbox and the internet, intercepting outbound requests to inject
credentials; the agent never holds API keys; this is the most concise open implementation of Verso's
auth-gated tool proxy; (2) the **tool-as-plugin model** — drop a Python class in `tools/`, it auto-
registers with REST endpoints; this is the reference for Verso's `@tool` auto-discovery contract;
(3) **stateless control plane + Postgres checkpoints** — every service is stateless, all state in
Postgres, step-level checkpointing on a per-thread workflow engine; surviving restarts with no
orchestration server is exactly what Verso's `durable=True` targets. Also: the NetworkPolicy default-
deny sandbox with per-thread network isolation is the production answer to Verso's sandboxed tool
execution question. Paradigm ran Centaur in production for 18 months before open-sourcing — the
AGENTS.md is written for agent-assisted development, making the code especially readable.

**What to RE:** `github.com/paradigmxyz/centaur` — (1) the FastAPI control plane: session lifecycle
endpoints, how session state is stored in Postgres, the session-to-sandbox mapping, (2) `iron-proxy`:
the credential injection implementation (how it knows which credential to inject per destination host),
(3) the `tools/` plugin system: how Python classes auto-register, what the `@tool` base class looks
like, how REST endpoints are generated, (4) the workflow engine: Postgres checkpoint schema, resume-
from-step implementation, (5) the NetworkPolicy per-thread isolation: how k8s NetworkPolicy is
programmatically created and torn down per thread. The architecture page at `centaur.run/architecture`
is the starting doc.

**Source pointer:** `github.com/paradigmxyz/centaur` (MIT, open source);
`paradigm.xyz/2026/05/open-sourcing-centaur-multiplayer-self-hosted-secure-agents`;
`centaur.run/architecture`.

**Priority:** P1 — teaches credential proxy, tool-as-plugin auto-discovery, and stateless-control-
plane + Postgres-checkpoint together in one readable codebase. More directly actionable for Verso's
`@tool` + auth-gated-tools design than any other open-source runtime in 2026.

---

### Salus (YC W26) — Runtime Guardrails Proxy

**What it is:** Pre-execution validation proxy for agent tool calls. Founded 2026, YC W26, $4M raised.
Integration: change base URL, Salus intercepts every tool call before execution, validates against
versioned policies + an evidence cache (all prior tool outputs + conversation history), returns
structured feedback on block. 58% of blocked calls recover and complete the task. Works with any
tool-calling framework.

**Why for Verso:** Salus is the first product that isolates the **pre-action validation layer** as its
own independently deployable primitive — not baked into a framework, not a guardrail module. This is
directly relevant to Verso's `@tool` design: should Verso's tool executor have a pre-call hook that
can be wired to a policy validator? Salus's evidence cache (accumulates all prior tool outputs +
conversation history per run, and validates proposed actions against it) is a novel implementation of
the **run-scoped state** that Verso's durable seam maintains anyway — the insight is that this state
is also the natural grounding set for action validation. The structured-feedback-on-block model (agent
gets an explanation it can use to self-correct, not an opaque HTTP error) matches Verso's error-
handling design goal. The 58% recovery rate is a benchmark Verso's tool executor retry logic should
target. Closed product but thin integration surface (proxy pattern) makes behavioral RE viable.

**What to RE:** (1) Integration protocol: `pip install salus`, read the Python SDK source to understand
the exact interception model — does it wrap the tool call function or intercept at the HTTP client
level? (2) Behavioral probing: route an agent through the Salus proxy, send tool calls that violate
a policy, capture the structured block response format (exact JSON schema), (3) The evidence cache
scope — is it per-session, per-run, per-thread? What headers/IDs identify the scope?, (4) Policy
definition format — what does a Salus policy look like (YAML? CEL? natural language?), (5) The
repair/rewrite path — when Salus rewrites rather than blocks, what does the rewritten tool call look
like? What model performs the rewrite?

**Source pointer:** `usesalus.ai`; `ycombinator.com/companies/salus`; `pip install salus` (SDK source);
closed product — probe via proxy route.

**Priority:** P1 — teaches the pre-action validation hook design. The evidence-cache-as-grounding
insight is novel and directly actionable for Verso's tool executor.

---

### Microsoft Agent Framework v1.0 — Agent Harness + Durable Extensions

**What it is:** The April 2026 GA merge of AutoGen + Semantic Kernel into a single SDK (`github.com/
microsoft/agent-framework`). New at BUILD 2026 (June 2026): Agent Harness as a first-class concept
(skills, context, memory, middleware), Hosted Agents, CodeAct sandbox integration, Python Functional
Workflow API (`@workflow` + `@step` decorators over plain async functions), and durable-task extension
(Postgres/Cosmos checkpoints). GA for Python + .NET.

**Why for Verso:** The existing teardown (`MS_AGENT_FRAMEWORK.md`, 357 lines) is explicitly flagged
as thin and predates the v1.0 GA and BUILD 2026 announcements. The new content that Verso must read:
(1) The **Functional Workflow API** (`@workflow` + `@step` over plain async functions with native
Python control flow) is a direct implementation attempt of Verso's "no rewrite, same code" seam —
studying how Microsoft solved the determinism problem without Temporal's sandboxed event loop is high
value; (2) The **Agent Harness** concept (skills, context providers, memory providers, middleware
pipeline) is the most complete published taxonomy of what a production Python agent harness needs —
`AgentModeProvider`, `TodoProvider`, `BackgroundAgentsProvider`, `FileMemoryProvider`, etc.; (3) The
**durable-task extension** (`azure/durable-task` SDK) — checkpoint storage model, the Durable Task
Scheduler service, how it differs from LangGraph's Pregel supersteps; (4) The **middleware pipeline**
for filtering, logging, function interception — directly relevant to Verso's pre/post tool hooks.

**What to RE:** `github.com/microsoft/agent-framework` — (1) `python/` directory: the `@workflow` and
`@step` Functional Workflow API source (how determinism is ensured without a sandbox), (2) harness/
directory or equivalent: the SkillsProvider, ContextProvider, MemoryProvider interfaces, (3) the
middleware/filter pipeline — how function invocation interception is implemented, (4) checkpoint
integration with `azure/durable-task` — the `FileCheckpointStorage` and `CosmosCheckpointStorage`
implementations (pickle-based serialization for non-JSON-native Python objects). Also read the BUILD
2026 announcement blog (`devblogs.microsoft.com/agent-framework/microsoft-agent-framework-at-build-
2026-announce/`) for architecture intent before reading source.

**Source pointer:** `github.com/microsoft/agent-framework` (MIT, open);
`devblogs.microsoft.com/agent-framework/microsoft-agent-framework-at-build-2026-announce/`;
`devblogs.microsoft.com/agent-framework/microsoft-agent-framework-at-build-2026/`;
`learn.microsoft.com/en-us/agent-framework/workflows/checkpoints`.
Extend `teardowns/MS_AGENT_FRAMEWORK.md` — do NOT create a new file.

**Priority:** P1 — thin teardown already exists; BUILD 2026 features add the harness taxonomy and
Functional Workflow API that directly model Verso's seam and hook system.

---

### Cloudflare Agents Week 2026 — Actor-Model Runtime + Agent Memory Primitives

**What it is:** Cloudflare's "Agents Week" (April 2026) shipped a complete agent infrastructure stack
as edge-native network primitives: Dynamic Workers (compute), Dynamic Workflows (durable orchestration),
Agent Memory (managed extraction + retrieval service backed by Durable Objects + Vectorize + Workers AI),
Browser Run (rebuilt browser-use primitive), and Project Think preview (actor-based kernel runtime).
Each agent IS a Durable Object with per-instance SQLite storage, hibernation, and wake-on-event.

**Why for Verso:** Two primitives here are directly relevant to Verso's design, and neither is covered
elsewhere in this repo: (1) **Agent Memory service architecture** — the dual-pass ingestion pipeline
(extract structured memories → embed → store in Vectorize) + five-channel parallel retrieval with
Reciprocal Rank Fusion, running behind a single API call (`env.AI.agent_memory.add()` / `.search()`)
— this is the managed memory-as-network-primitive model Verso should consider for its hosted tier;
(2) **Project Think's actor-based kernel** — agents that survive platform restarts, manage relational
memory trees, and execute self-authored code in restricted sandboxes — the relational memory tree
structure is novel and not present in any other teardown. The Durable Object = Agent runtime (each
Durable Object instance IS one agent instance with its own SQLite, hibernation, and wake-on-event)
is also the cleanest published model of how to implement per-agent state isolation without a
coordination server.

**What to RE:** (1) `blog.cloudflare.com/introducing-agent-memory/` — the dual-pass ingestion pipeline
and five-channel retrieval architecture, (2) `blog.cloudflare.com/agents-week-in-review/` for the
full stack overview, (3) `deepwiki.com/cloudflare/agents/3.1-agent-lifecycle-and-durable-objects` for
the Durable Object = Agent lifecycle model, (4) Project Think announcement at
`infoq.com/news/2026/04/cloudflare-project-think` — the relational memory tree structure and actor
kernel design. JavaScript/TypeScript codebase (Verso is Python-only) but the architectural patterns
translate directly; read for concepts not for code.

**Source pointer:** `github.com/cloudflare/agents` (open source); `blog.cloudflare.com/agents-week-
in-review/`; `blog.cloudflare.com/introducing-agent-memory/`;
`cloudflare.com/agents-week/updates/`.

**Priority:** P2 — JS-native (not directly portable to Python), but the Actor-per-Durable-Object
identity model and Agent Memory dual-pass ingestion are architectural references Verso's memory-as-
primitive design should account for.

---

## Notes

**What makes these targets genuinely novel (not re-tread of prior categories):**

- **Anthropic Managed Agents** is the only published production engineering account of the exact
  Session/Harness/Sandbox tripartite architecture. Every other framework lumps these together. The
  decoupling insight (p95 latency -90%) and the lazy-sandbox model are Verso-shaping numbers.

- **Google AX** is the first framework-agnostic event-log runtime that isn't Temporal. The `ax fork`
  trajectory-branching primitive is not present in any other system and is the right architecture for
  Verso's eval/what-if use case.

- **Centaur** is 18 months of production use turned into readable open-source code. The
  iron-proxy credential boundary + tool-plugin auto-registration is the most concrete open
  implementation of Verso's target tool architecture.

- **Salus** introduces the evidence-cache-as-grounding concept for pre-action validation.
  The 58% recovery rate is a concrete benchmark target.

- **Microsoft Agent Framework BUILD 2026** is being tracked because the existing teardown is
  explicitly thin (357 lines) and the new Functional Workflow API + Harness taxonomy are
  architecturally significant. This is an extension task, not a fresh RE.

- **Cloudflare Agents** is P2 because it's JavaScript-only infrastructure, but the Actor-per-DO
  identity model and the Agent Memory dual-pass ingestion architecture are conceptually novel enough
  to read for reference.

**What was found but excluded:**

- **Agentspan** (github.com/agentspan-ai/agentspan): wraps Conductor (Java/Spring Boot) with a thin
  Python SDK. The durable execution is entirely delegated to Conductor-OSS, which is not novel
  relative to Temporal, Restate, or DBOS. The Python API surface is thin. Low Verso value.

- **LangMem SDK**: spun out of LangGraph 0.3.19 as a long-term memory primitive. Directly covered
  by the LangGraph/LangChain teardowns already in the repo and by `memory-systems.md`. Not novel.

- **Moda (YC W26)**: reliability/monitoring for agents. Overlaps with `eval-observability.md`
  (Langfuse, Braintrust). No novel architectural primitive.

- **Captain (YC W26)**: unified data layer for enterprise RAG. Overlaps with retrieval pipeline
  work already in the repo. Not a framework-level concern.
