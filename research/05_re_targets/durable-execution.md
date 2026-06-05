# RE Targets — Durable Execution / Workflow Runtimes

**Category:** Durable execution / workflow runtimes (Verso seam substrate — HIGH)
**Verso relevance:** The tactical↔durable seam is the headline primitive. When `durable=True`, Verso needs a checkpoint-resume substrate: a journal that survives crashes, a HITL pause/signal protocol, determinism guardrails, and zero-rewrite ergonomics. These targets teach the exact mechanics.

---

## Already Covered

- **PREFECT** (`teardowns/PREFECT.md`, 1415 lines) — FastAPI server layer only. Scope explicitly excludes the orchestration engine, scheduler, and event system. The checkpoint/flow-run execution engine is NOT covered.

No other durable-execution or workflow-runtime teardowns exist in `teardowns/`. Temporal, Restate, DBOS, Hatchet, Inngest, Trigger.dev, Resonate, Windmill, Cloudflare Workflows, AWS Step Functions, LangGraph checkpointing, and LittleHorse are all uncovered.

---

## RE Targets

### Temporal (Python SDK)

**What it is:** Production-grade durable workflow engine; the gold-standard reference for checkpoint/replay semantics via event history.

**Why for Verso:** Temporal's Python SDK is the most complete existence proof of the tactical↔durable seam: the same `async def` workflow runs in-memory during tests and against a persistent Temporal server in production, no rewrite. Its three-layer architecture (Rust core via PyO3 → custom deterministic asyncio event loop → Python workflow code) is exactly the pattern Verso needs to understand before designing its own seam. Specifically: (1) how the SDK re-imports workflow files into an isolated sandbox per replay to prevent global-state pollution; (2) the Commands-vs-Events distinction — workers emit Commands, server records Events, replay matches generated Commands against historical Events; (3) the HITL signal/query/update trio (`@workflow.signal`, `@workflow.query`, `@workflow.update`, `workflow.wait_condition`) which is the canonical model for Verso's pause-resume interface; (4) the `@workflow.run` + `@activity.defn` decorator split enforcing the determinism boundary (workflow = deterministic orchestration; activity = side-effectful work).

**What to RE:** The sandbox module (`temporalio/worker/workflow_sandbox.py`) — re-import mechanism, passthrough module list, proxy objects intercepting non-deterministic stdlib calls. The custom asyncio event loop (`temporalio/worker/_workflow_instance.py` or equivalent) — how it drives replay by comparing Commands vs Event History. The signal/query/update handler machinery and `wait_condition` semantics. The FFI boundary (`temporalio/bridge/` — PyO3 compiled extension): how protobuf Payloads cross between Python and the Rust core. The `Replayer` class in `samples-python/replay` for testing workflow compatibility.

**Source pointer:** `github.com/temporalio/sdk-python` (main SDK, Python + Rust); `github.com/temporalio/sdk-core` (Rust core, `ARCHITECTURE.md` is load-bearing); `github.com/temporalio/samples-python/tree/main/replay` (replay test harness); `docs.temporal.io/develop/python`

**Priority:** P0

---

### Restate

**What it is:** Rust-based durable execution engine with a journal-per-invocation model; single-binary; Python SDK via service protocol.

**Why for Verso:** Restate's architecture is architecturally distinct from Temporal's event-history replay model and directly relevant to Verso's seam design. Key teaching: (1) the **Bifrost log** — a segmented WAL based on Delos/LogDevice with embedded replicated log → tiered object storage; the processor (query engine) derives all state deterministically from this log, so RocksDB state is ephemeral and recoverable; (2) the **journal-per-invocation** model: every `ctx.run_typed()` call appends a journal entry, and recovery replays by attaching the full journal to a new invocation — no Commands/Events split, just a journal the service code replays against; (3) the **3ms median step latency** — a concrete performance target for Verso's durable mode overhead; (4) the Python SDK (`ctx.key()` workflow identity, implicit journaling, `@user_signup.main()` / `@user_signup.handler()` split for workflow vs signal handlers) is directly analogous to what Verso's `durable=True` decorator path would expose; (5) Restate treats K/V state updates and execution progress as a single atomic write to the log — the exact "checkpoint-as-side-effect-of-execution" pattern Verso should adopt rather than a separate checkpoint step.

**What to RE:** `crates/` in the main Rust repo — particularly the bifrost/log crate and the service-protocol crate (defines the wire format between service and server). `restatedev/sdk-python` — the `Context` object implementation, how `ctx.run_typed()` creates journal entries, the `WorkflowContext` vs `ObjectContext` vs `ServiceContext` distinction, how the Python HTTP handler bridges to the Restate server. The service protocol spec (`service-protocol/` directory) — the exact journal entry format (protobuf? JSON?). Performance numbers from the "from first principles" blog post: 3ms median, 10ms under load, 94K actions/sec.

**Source pointer:** `github.com/restatedev/restate` (Rust server); `github.com/restatedev/sdk-python` (Python SDK); `restate.dev/blog/building-a-modern-durable-execution-engine-from-first-principles`

**Priority:** P0

---

### DBOS (dbos-transact-py)

**What it is:** Postgres-native durable Python workflow library — no separate orchestration server, just annotate functions with `@DBOS.workflow()` / `@DBOS.step()` and Postgres becomes the checkpoint store.

**Why for Verso:** DBOS is the cleanest existence proof of the "one flag, no rewrite" seam. The PydanticAI integration shows exactly the pattern Verso targets: `DBOSAgent(agent)` wraps `agent.run()` into a durable workflow with model calls and tool calls as checkpointed steps. Teaching points: (1) the **transaction piggybacking trick** — `@DBOS.transaction()` runs the step inside a Postgres transaction and writes the checkpoint as part of that same transaction commit, giving exactly-once semantics for DB-touching steps at zero overhead; (2) the **three-write cost model** — one write per step output + two writes per workflow (start + end) — a concrete baseline for Verso's durable mode overhead; (3) `DBOS.recv(channel, timeout)` / `DBOS.send(destination, message, topic)` as the HITL primitive — a named pub/sub channel backed by Postgres, not a Temporal-style signal; (4) `SetWorkflowID(key)` as the idempotency context manager — maps cleanly to Verso's workflow identity; (5) `fork_workflow(workflow_id, start_step)` for manual restart from a specific step — the operator escape hatch Verso needs; (6) `DBOS.sleep(duration)` — durable sleep via Postgres-backed timer, survives process restarts. The Postgres-only backend (no Redis, no Kafka) is attractive for self-hosted Verso deployments.

**What to RE:** `dbos/` source directory — decorator implementation (`_workflow.py`, `_step.py`, `_transaction.py`), the checkpoint write path, Postgres schema (table names, column types for workflow state and step outputs). The `recv`/`send` HITL implementation. The recovery algorithm at startup (how interrupted workflows are detected and re-queued). The `DBOSClient` programmatic control API (`list_workflows`, `fork_workflow`, `retrieve_workflow`). `supabase.com/blog/durable-workflows-in-postgres-dbos` for the Postgres schema visualization.

**Source pointer:** `github.com/dbos-inc/dbos-transact-py`; `docs.dbos.dev/architecture`; `docs.dbos.dev/python/tutorials/workflow-tutorial`; `pydantic.dev/articles/pydantic-ai-dbos` (integration pattern)

**Priority:** P0

---

### Hatchet

**What it is:** Open-source MIT-licensed workflow/task orchestration engine with explicit durable task primitives (SleepFor, WaitForEvent, Memo, RunChild) mapped to a durable event log.

**Why for Verso:** Hatchet has the clearest Python API surface for the durable primitive set Verso needs to expose. Teaching points: (1) the **four checkpoint primitives** — `ctx.aio_sleep_for(timedelta)`, `ctx.wait_for_event(key)`, `ctx.memo(key, fn)`, `ctx.run_child(workflow)` — each appends an entry to the durable event log; this is the exact API shape for Verso's durable ReAct loop checkpoints; (2) the **DAG vs durable task distinction** — DAGs predeclare shape statically (simpler, cheaper, deterministic by construction); durable tasks build shape at runtime via child spawning (dynamic, suited to ReAct loops where the next action depends on LLM output); Verso needs both modes and Hatchet's source shows how to implement both on the same event log; (3) **"or groups"** — wait for either a sleep OR an event, whichever fires first — necessary for Verso's HITL timeout patterns; (4) worker slot release during sleep/wait — the mechanism for zero-resource waiting; (5) the event key / filter expression model (`on_events=["user:create"]`, CEL filter expressions) for event-driven workflow triggers; (6) Go/PostgreSQL server is self-hostable, open-source, studied against real workloads.

**What to RE:** `github.com/hatchet-dev/hatchet` — the Python SDK's `DurableContext` class implementation; the event log schema in the Go server (PostgreSQL tables backing the durable log); how `aio_sleep_for` releases and reclaims worker slots; `WaitForEvent` cross-worker delivery mechanism; the DAG execution path vs durable task path in the executor; `docs.hatchet.run/home/durable-execution`, `durable-sleep`, `durable-events`, `architecture`.

**Source pointer:** `github.com/hatchet-dev/hatchet` (MIT, open); `docs.hatchet.run/home/durable-execution`; `docs.hatchet.run/home/durable-events`; `docs.hatchet.run/home/durable-sleep`

**Priority:** P0

---

### LangGraph Checkpointing

**What it is:** LangGraph's `BaseCheckpointSaver` interface + `PostgresSaver` / `InMemorySaver` backends — a superstep-based checkpoint system implementing the Pregel/BSP execution model.

**Why for Verso:** LangGraph is the dominant Python agent framework already in use, and its checkpointing layer is the closest existing implementation of Verso's `durable=True` seam for a ReAct-style agent loop. Teaching points: (1) the **`durable=False` → `durable=True` toggle**: swapping `InMemorySaver` for `PostgresSaver` at `graph.compile(checkpointer=...)` is the exact single-flag model Verso targets — study the interface contract that makes this swap seamless; (2) the **superstep/Pregel model**: each superstep is a single "tick" where all scheduled nodes execute in parallel; a checkpoint is saved atomically after each superstep; `put_writes` saves per-node pending writes within a superstep so failed nodes can be skipped on resume without re-running successful siblings; (3) the **`StateSnapshot` format**: `{values, next, config{thread_id, checkpoint_ns, checkpoint_id}, metadata{source, step, writes}, tasks}` — the exact checkpoint payload shape Verso should adopt or adapt; (4) the **three durability modes** (`"exit"` / `"async"` / `"sync"`) — a latency vs durability tradeoff axis Verso needs to expose; (5) `interrupt_before=["tools"]` / `interrupt_after=["node"]` vs the newer `interrupt()` primitive (LangGraph v0.4, April 2026) — the evolution from static compile-time interrupt points to dynamic mid-node interrupts is directly applicable to Verso's HITL design; (6) **channel-versioned storage** in `PostgresSaver` — each channel stored separately and versioned so a new checkpoint only writes changed channels, minimizing write amplification.

**What to RE:** `github.com/langchain-ai/langgraph/libs/checkpoint/` — `BaseCheckpointSaver` abstract class, `put` / `put_writes` / `get_tuple` / `list` signatures and semantics. `libs/checkpoint-postgres/` — PostgreSQL schema (`checkpoints` table + `checkpoint_writes` table), the versioned channel storage optimization. `libs/langgraph/` — the Pregel executor, superstep loop, how `interrupt()` is implemented vs old `interrupt_before/after`. `langgraph-checkpoint` PyPI package for the stable interface.

**Source pointer:** `github.com/langchain-ai/langgraph/libs/checkpoint-postgres/langgraph/checkpoint/postgres/__init__.py`; `github.com/langchain-ai/langgraph`; `docs.langchain.com/oss/python/langgraph/durable-execution`; `docs.langchain.com/oss/python/langgraph/interrupts`

**Priority:** P0

---

### Resonate (resonatehq)

**What it is:** "Distributed Async Await" — durable execution via Durable Promises (named checkpoints) + Python generator-based coroutines; single-binary server; open protocol.

**Why for Verso:** Resonate is the most philosophically distinct model in this space and the one most directly analogous to Verso's desired developer experience. Teaching points: (1) the **`durable=True` flag per call** — `yield ctx.run(fn, arg).options(durable=True)` makes a single function call a durable checkpoint without changing the call signature; `durable=False` runs it transiently; this is the exact one-flag toggle Verso targets, applied at the per-call level rather than per-agent level; (2) the **Durable Promise as first-class HITL primitive** — `promise = yield ctx.promise(id="approval-id")` creates a named, externally-resolvable promise; external systems call `resonate.promises.resolve(id="approval-id", data=...)` to unblock it; this is cleaner than Temporal's signal model for async human approval flows; (3) the **generator/yield model for checkpointing** — Python generators (`yield`) map naturally to coroutine suspension points; each `yield ctx.run(...)` is a checkpoint; the `@resonate.register` decorator marks a generator as durable; no custom event loop or sandbox required; (4) `ctx.time.time()` / `ctx.random.random()` as determinism-safe replacements for `time.time()` / `random.random()` — Verso needs the same pattern; (5) the **open Durable Promise specification** (`resonatehq/durable-promise-specification`) — a protocol any backend can implement, meaning Verso could implement a Resonate-compatible checkpoint store; (6) the **Async RPC protocol** — transport-agnostic (HTTP, GCP Pub/Sub, Kafka planned), relevant for Verso's pluggable backend edge.

**What to RE:** `github.com/resonatehq/resonate-sdk-py` — the `Context` object implementation, how `ctx.run()` creates durable promises, how the generator scheduler drives execution, the `durable=True` option path. `github.com/resonatehq/resonate` — server internals, promise store schema, the Async RPC protocol format. `github.com/resonatehq/durable-promise-specification` — the open standard, minimum viable API surface for a checkpoint backend.

**Source pointer:** `github.com/resonatehq/resonate-sdk-py`; `github.com/resonatehq/resonate`; `github.com/resonatehq/durable-promise-specification`; `docs.resonatehq.io/develop/python`

**Priority:** P1

---

### Inngest

**What it is:** Managed durable workflow platform with open-source server; step-based execution with SHA-1 hashed step IDs for memoization; Python SDK (`inngest-py`).

**Why for Verso:** Inngest's SDK specification (`docs/SDK_SPEC.md`) is one of the most precisely documented checkpoint protocols in the space. Teaching points: (1) the **SHA-1 hashed step ID scheme** — step IDs are `hex(sha1(human_readable_name))`, with loop iterations suffixed `:n` before hashing — a concrete deterministic step-identity mechanism Verso needs for its durable event log; (2) the **memoization-via-Call-Request model** — the server returns `{steps: {hash: {data: any}}}` in every Call Request; the SDK checks each step against this map before executing, returning cached results instantly; this is the server-side half of the checkpoint contract that Verso's durable backend must implement; (3) the **206 Partial Content streaming** — when a step completes, the SDK returns 206 with the step result; the Inngest server executes the step (or async opcode) in a separate request and passes the result back; this round-trip model is how serverless functions achieve durability without persistent processes; (4) the **opcode taxonomy** — StepRun (sync), Sleep (duration string / ISO date), WaitForEvent (CEL filter + timeout), InvokeFunction, SendEvent, AiGateway — a complete vocabulary for durable agent actions; (5) the **two-queue-per-function architecture** — each function gets two queues; workers are shared-nothing; relevant for Verso's concurrency model.

**What to RE:** `github.com/inngest/inngest/blob/main/docs/SDK_SPEC.md` (critical — the full execution protocol spec); `inngest/inngest-py` Python SDK source — step hashing, memoization lookup, opcode emission; the `Executor` package in `pkg/` — how step state is written to the State Store; the State Store interface (what database backs it).

**Source pointer:** `github.com/inngest/inngest/blob/main/docs/SDK_SPEC.md`; `github.com/inngest/inngest-py` (Python SDK); `github.com/inngest/inngest` (server, `pkg/executor/`)

**Priority:** P1

---

### Trigger.dev v3

**What it is:** Managed durable compute platform using CRIU (Checkpoint/Restore In Userspace) to freeze and restore container state at `wait.*` call sites.

**Why for Verso:** Trigger.dev is the only system here using OS-level container checkpointing (CRIU) rather than application-level event sourcing. Teaching points: (1) the **CRIU checkpoint model** — at every `wait.for()` / `wait.forRequest()` / `task.triggerAndWait()` call, the running container is frozen to disk and restored on a new machine when the wait resolves; this is fundamentally different from replay-based durable execution and has different tradeoffs (no determinism requirement; arbitrary code can run in workflow body; but checkpoint artifacts are large and restore adds latency); (2) the **waitpoint taxonomy** — `wait.for(duration)`, `wait.until(date)`, `wait.forRequest(matcher)`, `event.waitForEvent(matcher)`, `task.triggerAndWait(taskRef)`, `task.batchTriggerAndWait([...])` — the complete set of HITL pause primitives Verso needs to cover; (3) **immutable deployment versions** — each deploy creates a version snapshot; running tasks lock to their version; new deploys don't affect in-flight tasks; essential for Verso's upgrade-without-breaking-in-flight-agents requirement; (4) **rollback functions** — explicit undo blocks for non-idempotent mutations, a complement to retry-based recovery.

**What to RE:** `github.com/triggerdotdev/trigger.dev` — the CRIU integration layer (how containers are checkpointed and restored at wait boundaries); the waitpoint primitive implementations; the deployment versioning system; the worker-to-platform protocol; `trigger.dev/blog/v3-announcement` for the design rationale.

**Source pointer:** `github.com/triggerdotdev/trigger.dev`; `trigger.dev/blog/v3-announcement`; `trigger.dev/docs/how-it-works`

**Priority:** P1

---

### Windmill (Workflow as Code)

**What it is:** Open-source (AGPLv3) script/workflow platform with Rust backend; Python `@task` / `@workflow` / `step()` primitives; checkpoint-replay via Postgres job state; 13x faster than Airflow.

**Why for Verso:** Windmill's workflow-as-code layer is the most accessible Python-native checkpoint model to study and the one closest to Verso's `durable=True` surface: (1) the **suspend-on-task model** — when a `@task` call hasn't been cached, the workflow script exits, saves all completed step results to Postgres, fully releases its worker slot, and re-queues when child jobs complete; on resume, all cached steps return instantly; (2) the **`step(name, fn)` inline checkpoint** — runs the function inside the parent process (no child job) but persists the result; lighter weight than `@task`; maps to Verso's in-process checkpoint for cheap steps; (3) the **`waitForApproval()`** HITL primitive — suspends workflow, releases worker, returns `{approved: bool, approver: str, value: any}` when a human acts in the UI; (4) **step key determinism requirement** — the workflow function must call tasks in the same order on replay; non-deterministic values (timestamps, random) must be wrapped in `step()` for stability; (5) the Rust backend (stateless API + Postgres job queue + nsjail sandboxing) is a clean reference architecture for Verso's durable backend option.

**What to RE:** `github.com/windmill-labs/windmill` — Python SDK source (`wmill` package); the Rust worker's checkpoint write/read path; the Postgres job state schema (`completed_job` table); how `step()` keys are derived; `waitForApproval()` implementation; `windmill.dev/docs/core_concepts/workflows_as_code`; `windmill.dev/blog/launch-week-workflow-as-code`.

**Source pointer:** `github.com/windmill-labs/windmill`; `windmill.dev/docs/core_concepts/workflows_as_code`

**Priority:** P1

---

### Cloudflare Workflows (+ Durable Objects)

**What it is:** JS/TS-only durable workflow runtime built on Durable Objects with SQLite-backed per-instance state; V2 (May 2026) scales to 50K concurrent instances.

**Why for Verso:** Despite being JS-only, Cloudflare Workflows has the most precisely documented **checkpoint storage design** in the space and teaches Verso the architecture of the storage layer directly. Teaching points: (1) the **write-before-advance pattern** — step result is written to SQLite (Durable Object storage) inside a `transactionSync()` before the workflow advances; if the DO is evicted after the write but before the next step, replay reads the memoized result and skips re-execution; (2) the **game-loop executor** — `while (last step not completed) { iterate every step; use memoized cache if step ran already }` — the simplest possible replay algorithm; Verso's durable executor is a Python equivalent of this; (3) **Durable Objects alarm for long sleeps** — `scheduler.wait()` for short in-process waits; DO alarms (persistent cron-like callbacks) for multi-day sleeps that survive eviction; the alarm-as-resume-trigger pattern is transport-agnostic and usable in Verso with any job scheduler; (4) **V2 architecture scaling** — each workflow instance is a separate DO backed by SQLite; the control plane refactor enabling 50K concurrent instances is a concrete scaling ceiling benchmark.

**What to RE:** `blog.cloudflare.com/building-workflows-durable-execution-on-workers/` (detailed source with game-loop pseudocode); `blog.cloudflare.com/dynamic-workflows/` (per-tenant V2 architecture); `developers.cloudflare.com/workflows/` (step.do / step.sleep / step.waitForEvent API). Note: no source code to clone (closed infra); RE is documentation + blog analysis only.

**Source pointer:** `github.com/cloudflare/workerd` (Workers runtime, open source — Durable Objects implementation); `blog.cloudflare.com/building-workflows-durable-execution-on-workers/`; `blog.cloudflare.com/dynamic-workflows/`

**Priority:** P1

---

### Resonate Durable Promise Specification

**What it is:** An open protocol specification (`resonatehq/durable-promise-specification`) defining the minimum API for a checkpoint store: create, resolve, reject, cancel, await a named durable promise.

**Why for Verso:** This is the minimal interface that Verso's pluggable durable backend must implement. The spec defines: named promises with idempotency keys, promise states (pending/resolved/rejected/canceled/timedout), the resolve/reject external API (the HITL hook), and the await semantics. If Verso's durable backend implements this spec, it is automatically compatible with any Resonate SDK and vice versa.

**What to RE:** Read the spec cover to cover (`github.com/resonatehq/durable-promise-specification`). Map each operation to Verso's internal checkpoint operations. Identify which operations are missing for Verso (e.g., step ancestry / parent-child promise relationships).

**Source pointer:** `github.com/resonatehq/durable-promise-specification`

**Priority:** P2

---

### AWS Step Functions

**What it is:** Managed serverless workflow engine; state machine ASL (Amazon States Language) JSON; task token HITL pattern.

**Why for Verso:** Step Functions is the incumbent HITL reference — the **task token pattern** is the canonical "pause a workflow and wait for an external human or system to call back" model used in production at scale. Teaching points: (1) the **task token** — when a state executes with `waitForTaskToken`, a unique opaque token is generated and passed to the external system (via SQS, Lambda, etc.); the workflow idles until the external system calls `SendTaskSuccess(token, output)` or `SendTaskFailure(token, error)`; this is the cleanest HITL abstraction because the workflow needs no knowledge of the approval system; (2) **EventBridge integration** — the token is stored in DynamoDB by the initiating Lambda; an EventBridge rule fires on the external completion event; a resolver Lambda looks up the token and calls `SendTaskSuccess`; this three-part choreography is the production HITL pattern Verso should offer as a plug-in integration; (3) ASL's **Choice/Wait/Task state machine** as a reference for what a workflow graph notation needs to express. The main limitation (ASL JSON DSL instead of Python code) is exactly what Verso avoids — but studying it clarifies what Verso's Python API must cover.

**What to RE:** `docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html` (waitForTaskToken semantics); `docs.aws.amazon.com/step-functions/latest/dg/callback-task-sample-sqs.html` (end-to-end HITL pattern with SQS); no source code (fully managed, closed); RE is documentation analysis only.

**Source pointer:** `docs.aws.amazon.com/step-functions/latest/dg/` (public documentation); closed — no source to clone

**Priority:** P2

---

### LittleHorse

**What it is:** gRPC-first microservice orchestration engine; WfSpec + WfRun model; Kafka as durable WAL; Java kernel; Python/Go/Java SDKs.

**Why for Verso:** LittleHorse is the closest open-source analog to Temporal with a Kafka-backed (rather than Temporal's proprietary) durability model. Teaching points: (1) the **WfSpec / WfRun distinction** — WfSpec is the compiled workflow definition (like a bytecode program); WfRun is an execution instance — this compile-then-execute split is how LittleHorse achieves version safety; (2) **Kafka as WAL** — all state transitions are Kafka events; recovery re-applies the event log; a concrete alternative to Postgres-as-checkpoint-store for high-throughput Verso deployments; (3) the **bidirectional gRPC streaming** between kernel and task workers — task dispatch without polling; (4) the **TaskRun / NodeRun model** — each node execution is a durable record, retryable independently; maps to Verso's step/activity boundary. LittleHorse is less relevant to the Python developer experience (SDK is lower-level) but important for understanding the Kafka-WAL durability architecture.

**What to RE:** `github.com/littlehorse-enterprises/littlehorse` — LH Kernel source (Java), particularly the Kafka consumer/producer topology and state machine; Python SDK source; `littlehorse.dev/docs/architecture-and-guarantees/`.

**Source pointer:** `github.com/littlehorse-enterprises/littlehorse`; `littlehorse.dev/docs/architecture-and-guarantees/`

**Priority:** P2

---

## Notes

### What Verso actually needs from this category

The durable seam requires four subsystems studied independently:

1. **Journal / checkpoint store** — the append-only log or key-value store that persists step results. Options: Postgres rows (DBOS, Windmill), event-sourced log (Temporal event history, Restate Bifrost, LittleHorse/Kafka), SQLite per-instance (Cloudflare DO), in-memory dict (tactical mode). Study: DBOS transaction piggybacking, Restate Bifrost, LangGraph channel-versioned PostgresSaver.

2. **Replay / determinism mechanism** — how the runtime re-executes code without re-triggering side effects. Options: event-history Commands-vs-Events matching (Temporal), memoization-by-step-hash (Inngest, Windmill), journal replay (Restate, Hatchet), OS container checkpoint (Trigger.dev CRIU). Study: Temporal sandbox + event loop, Inngest SHA-1 step IDs, Resonate `ctx.time.time()`.

3. **HITL pause protocol** — how the agent suspends mid-loop for human input and resumes after. Options: named Durable Promise resolve (Resonate), signal/wait_condition (Temporal), task token callback (AWS Step Functions), `waitForEvent` with timeout (Hatchet, Inngest, Windmill `waitForApproval`). Study: Temporal signals+queries+updates, Resonate `ctx.promise()`, Hatchet WaitForEvent, Windmill waitForApproval.

4. **The seam interface itself** — the Python decorator or context manager that makes `durable=False` and `durable=True` share the same code path. Study: DBOS `@DBOS.workflow()` + `@DBOS.step()`, Resonate `@resonate.register` + `durable=True` option, LangGraph `compile(checkpointer=InMemorySaver())` vs `compile(checkpointer=PostgresSaver())`.

### Key architectural choices Verso must make (informed by these targets)

- **Event sourcing vs memoization**: Temporal replays the whole workflow against the event log (determinism required, complex sandbox); DBOS/Windmill/Inngest memoize step results (no replay, simpler, but non-deterministic code allowed in workflow body). Verso's `async def` ReAct loop is inherently dynamic — memoization-by-step-hash is more natural than full replay.

- **Step identity scheme**: Inngest's SHA-1 of human-readable name + `:n` loop counter is the most portable scheme. Temporal's approach ties step identity to the event history sequence number (order-sensitive, brittle to refactors). Verso should adopt something closer to Inngest's content-addressed step IDs.

- **HITL primitive shape**: Resonate's named external promise is the cleanest model for Verso because it decouples the agent (creates promise, yields) from the approval system (resolves promise via HTTP). No signal channel, no query, no update — just a named future.

- **Postgres vs separate server**: DBOS proves a Postgres-only backend is production-viable at >40K steps/sec. Verso should offer Postgres-only as the default durable backend (no extra infra) with a pluggable interface for Redis/Kafka for high-throughput deployments.

### Targets deprioritized and why

- **Prefect orchestration engine** (already has FastAPI teardown but not engine): lower priority than the dedicated durable-first systems above; Prefect's engine is Airflow-adjacent (DAG-first, not ReAct-first).
- **Dapr Workflow / Diagrid**: Dapr's durable workflow is a thin layer over a configurable state store; the interesting RE target is the Diagrid python-ai framework-wrapping pattern (P2, add if time allows), not the Dapr runtime itself.
- **Airflow**: DAG/batch-first, not event-sourced, no HITL story. Not relevant to Verso.
- **Prefect Server (orchestration engine, not FastAPI layer)**: Medium priority — useful for understanding flow-run state machine and deployment+worker architecture, but not blocking any Verso core decision.
