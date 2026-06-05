# Adversarial Critique — multiagent-sandbox / SCALE & FAILURE
*Decision under review: Ship in v1 — 3 opt-in multi-agent topologies (subagent_delegate / fan_out / orchestrator_workers, depth-cap 1) + CodeSandbox escape hatch (microsandbox local default, E2B/Daytona adapters)*
*Lens: SCALE & FAILURE*
*Date: 2026-06-05*

---

## The attack

**The v1 decision bundles two architecturally independent bets — multi-agent state coordination + sandbox infrastructure — into one ship/defer gate. On the SCALE & FAILURE lens, both halves carry concrete failure modes the resolution does not handle. The compound claim that these are "safe to ship" for a solo dogfood-first project rests on three assumptions that break at 10×.**

---

### Failure 1 — Non-idempotent tool double-fire under fan_out + durable seam interaction

`fan_out` dispatches N workers via `asyncio.gather` under a `Semaphore(max_concurrency=5)`. Each worker is a full ReAct loop that runs inside the **durable harness** when `durable=True` — every tool call writes to `verso_step_outputs` via write-before-advance. This is fine for a single agent.

The problem: the resolution specifies `fan_out` as a tactical-layer primitive (asyncio.gather, no explicit checkpoint semantics). The `Orchestration(orchestrator_workers)` pattern has workers write to a **shared typed state store** (a `dict[str, Any]`). Neither the `fan_out` spec nor the `Orchestration` spec addresses what happens when a durable harness is crashed **mid-fan-out**.

On recovery, the lead agent's `verso_step_outputs` has the `fan_out` step marked as "in progress" or absent (it never completed). The lead re-enters the game loop and re-fires `fan_out`. Some workers had already completed and written their results to the shared state store before the crash — their `verso_step_outputs` entries are present with `ON CONFLICT DO NOTHING`. The write-before-advance invariant correctly skips those. But other workers had executed their **non-idempotent tool calls** (send an email, POST to an external API, write to a database) **without** having reached the `verso_step_outputs` write (the crash happened in the gap between "tool ran" and "checkpoint written"). Those tools **fire again** on recovery — the classic double-fire.

The production-topology resolution (`D3`) says: "write the step checkpoint in the **same transaction** as the tool's writes (DBOS transaction-piggyback) — exactly-once semantics for DB-touching tools at zero extra round-trip." This works for a **single-agent** Postgres-touching tool. It does not generalize to:

- **External APIs** (no shared transaction boundary — email sends, Stripe charges, GitHub PRs)
- **Multi-agent scenarios** where each worker has its own `verso_step_outputs` namespace but the parent's fan_out step straddles them
- The **shared state store** (`dict[str, Any]`) which has no transaction linkage to any individual worker's checkpoint table

The resolution declares `fan_out` has order-preservation and a cancellation sentinel (`SubagentResult(stop_reason="cancelled")`), but it explicitly leaves the double-fire behavior under durable fan_out as an "open unknown" (#5: "what `results[i]` is for the cancelled worker"). This is underspeci­fied in exactly the case that bites at 10× concurrent tasks: a partial fan-out crash with heterogeneous tool idempotency.

**At 10×:** 50 fan-out tasks, 5 at a time, worker process crashes at task 23. Tasks 1-22 are safe. Task 23 had called `send_invoice()` (non-idempotent, external API) and died before checkpointing. On recovery it fires again. The user gets a duplicate invoice. The framework has no mechanism to prevent this except requiring users to make every tool idempotent — but the resolution explicitly says `non-idempotent tools → max_attempts=1` for **single-agent** dispatch, and there is no equivalent constraint enforcement for workers inside a fan_out.

---

### Failure 2 — Microsandbox KVM availability: the "zero-infra" claim breaks on shared cloud hosts

The resolution's strongest point for microsandbox as default is "no cloud account, hardware-grade isolation, `pip install`." The critical load-bearing assumption is **KVM availability on the host**.

microsandbox uses libkrun via KVM (`rootless KVM` — no root required, but KVM device must be accessible). On:
- **macOS** (the author's current platform, Darwin 25.2.0): libkrun uses the Hypervisor framework (not `/dev/kvm`), which does not require KVM. This works.
- **Linux bare metal / dedicated VPS**: `/dev/kvm` is present. This works.
- **Shared cloud VMs (AWS t-family, GCP e2, standard Heroku/Render dyno, most free/cheap tiers, GitHub Codespaces standard)**: KVM is **not exposed** to the guest. `microsandbox` falls back to... nothing. The Sandbox.create() call fails with a hypervisor error at runtime, not import time.

The resolution's "pip install microsandbox is genuinely self-contained" (from the teardown) is true — the binary is embedded. But self-contained does not mean functional. The `msb` binary calls `krun_start_enter()` which requires a hypervisor; without one it errors.

The result: any user who runs Verso on a standard cloud instance (the overwhelmingly common deployment environment when moving from local dev to "runs on a server") hits a hard runtime error on the **first sandboxed tool call** — the lazy sandbox provision that the production-topology resolution correctly identifies as a "latency hitch." This is not a latency hitch; it is a silent capability hole. The adapter protocol falls back to... E2B, which requires `E2B_API_KEY`, which was the explicit reason E2B was rejected as the default. The Daytona adapter requires a running Daytona server.

**At 10×:** a solo developer builds on Verso locally (macOS / Linux bare metal), dogfoods Code Mode successfully, then deploys to a cheap cloud instance. First `run()` with a sandboxed tool fails at runtime with a hypervisor error. There is no graceful degradation path in the spec — the CodeSandbox `create()` method raises, the durable loop catches it as `SandboxDead`, marks it a tool-call error, and proceeds with `sandbox = None`. The loop continues but Code Mode is silently non-functional. The user sees an unhelpful "sandbox died" error, not "KVM not available on this host."

The resolution documents this as an "open unknown" (#1: "the `verso.internal` domain-rule resolution needs an integration test") but that unknown is the smoltcp DNS alias, not KVM availability. **KVM availability is not mentioned as an unknown at all** in the resolutions — it is an implicit assumption that will silently break on the most common scale-up path.

---

### Failure 3 — Shared typed state store is an in-memory dict with no concurrent-write semantics

The `Orchestration(orchestrator_workers)` topology has workers write to a `shared typed state store (a dict[str, Any])`. The resolution says: "typed access helpers, not message-passing" and "last-writer-wins default." The `SharedTypedState` is "a thin wrapper over whatever the durable runtime's checkpoint store provides" — but this is an open unknown (#4: "needs a decision after Phase 2's durable substrate lands").

In the interim, `shared_state` is an in-memory `dict`. Under `fan_out(max_concurrency=5)` running inside `asyncio.gather`:

- Five workers are concurrently writing to `shared_state["results"]`.
- asyncio is single-threaded, so dict mutations are safe from race conditions *if every write is an `await`-free atomic assignment*. But in practice workers call `shared_state["results"].append(result)` — a two-operation sequence (read list + append) that is not atomic. Under high concurrency with intermediate `await` points (the workers are making LLM calls), another worker can mutate the list between the read and the append.
- Even with Python's GIL, `list.append` on a shared list across tasks with interspersed awaits is not safe — the GIL is released at `await` points.

The resolution spec shows `Orchestration.shared_state` as a `@property` returning `SharedTypedState` described as a "typed dict with version stamps and optional conflict-resolution." None of this is implemented yet — it is explicitly deferred ("needs a decision after Phase 2"). So v1 ships `Orchestration` backed by a bare in-memory dict with "last-writer-wins default" and no concurrent-write protection.

**At 10×:** a research fan_out with 10 workers all appending their results to a shared list. Under asyncio with LLM call awaits, two workers attempt `shared_state["research_results"].append(result)` with an `await` between their reads and appends. The list ends up with 9 entries instead of 10 — one result silently dropped. There is no error, no warning, no missing-result detection.

This is not a theoretical concern. It is the standard asyncio shared-mutable-state bug. The resolution acknowledges the store is unimplemented ("DESIGNED") but does not flag this as a production-blocking limitation of shipping `Orchestration` in v1 without the store.

---

### Failure 4 — Depth-cap enforcement has no cross-process scope

`max_depth: int = 1` is enforced by a `depth` parameter passed through the call stack: `subagent_delegate(..., depth=0, max_depth=1)` increments `depth` and raises `DepthCapExceeded` at `depth >= max_depth`. This is correct for **in-process** delegation.

The durable runtime changes the scope. A durable agent runs as a `wake(run_id, ...)` invocation in a **worker process**. When it calls `subagent_delegate`, the sub-agent is submitted as a **new run** with a new `run_id`. The sub-agent wakes in its own worker process. The `depth` parameter is passed as... what? The resolution does not specify whether `depth` survives the `submit()` → `wake()` boundary. It is not in the `verso_runs` schema. It is not in `SubagentResult`.

If `depth` is not persisted to the durable run record, then:
- Durable sub-agent runs have `depth=0` by default.
- A sub-agent can call `subagent_delegate` with `depth=0, max_depth=1` — no error.
- The depth cap is enforced only in tactical (in-process) mode; durable multi-agent workflows are uncapped.

**At 10×:** a durable orchestration task where workers are configured with `max_depth=2` (the spec allows `max_depth` up to `MAX_DEPTH_CAP=3`). Each worker runs durably in its own process. Depth counter is not in the run schema. Workers spawn sub-workers without hitting the cap. The token and cost blow-up is exponential: depth-3 with fan_out of 5 at each level = 125 concurrent LLM-running processes, each with `max_steps=25`, each making LLM calls. `max_budget_usd` is the only guard, and it is checked at the lead agent level — there is no mechanism to aggregate spend across a durable worker pool and enforce the cap cluster-wide.

---

### Failure 5 — Postgres as single bottleneck for fan_out write throughput

The durable runtime uses Postgres with `SELECT ... FOR UPDATE SKIP LOCKED` row-level locking. The step write is `INSERT INTO verso_step_outputs ... ON CONFLICT DO NOTHING`. For single-agent workloads this is fine — one writer, sequential steps.

Under `fan_out(max_concurrency=5)` with 5 workers each completing steps concurrently:
- All 5 workers are writing to `verso_step_outputs` simultaneously.
- All 5 workers are also potentially writing to `verso_run_events` (the conversation log) simultaneously.
- The `SEQ_ALLOCATION = MAX(seq)+1 per run` strategy (AX's `sqlite.go:82-90`) is a **serializing scan**: each worker must read the current max seq for its run, increment, and insert — this is not a SEQUENCE (which would be concurrency-safe) but a MAX()+1 pattern. Under concurrent workers for the same `run_id`, this creates a write serialization bottleneck: concurrent MAX()+1 allocations collide and one must retry.

The `RECOVERY_POLLER_INTERVAL_S=0.5s` + `WORKER_LEASE=30s` constants are sized for single-agent runs recovering from crashes — not for a fleet of concurrent workers all hitting the same `verso_run_events` table with sequential-seq writes.

**At 10×:** `fan_out(tasks=50, max_concurrency=10)` — 10 workers all writing `tool_result` events to `verso_run_events` for the same `run_id`. The MAX()+1 seq allocation is a hot-row contention point. Postgres row-level lock on the max-seq scan serializes all 10 writes. Worker throughput degrades linearly with concurrency instead of scaling. The `KEEPALIVE_PING_INTERVAL_SEC=50` and `REQUEST_TIMEOUT_S=60.0` constants (copied from E2B for single-sandbox sessions) are not relevant to this bottleneck — the problem is the event log write serialization.

The resolution specifies `verso_run_events(run_id, seq)` with `PRIMARY KEY(run_id, seq)` and `SEQ_ALLOCATION = MAX(seq)+1` but does not address whether workers in a fan_out share a `run_id` (the lead's) or have their own. If they share the lead's `run_id`, the seq-allocation contention is real. If each worker has its own `run_id`, then the lead has no unified event log to replay — the Session/Harness split breaks.

---

## Does it break the decision?

**Partially. The decision does not collapse entirely, but it has two issues that bite before production and one that is a real correctness hole.**

**What survives:** The core framing — ship 3 opt-in topologies depth-capped at 1, microsandbox as local default, adapter protocol — is architecturally sound. The teardown evidence for the three-backend adapter pattern is solid. The decision to defer these to Phase 3 (not v1 core) already contains most of the risk. The depth-cap-1 default is the right call. `SubagentResult` typed compact summary as the return type is correct.

**What does not survive unchallenged:**

1. **Failure 1 (non-idempotent double-fire under durable fan_out)** is a real correctness hole that the resolution does not address. Shipping durable + fan_out + non-idempotent tools is incorrect without an explicit "durable fan_out requires idempotent workers OR exactly-once semantics at the tool level" contract. The resolution's `max_attempts=1` guard exists only for single-agent dispatch; it is not carried into the multi-agent layer.

2. **Failure 2 (microsandbox KVM availability)** is a missing failure mode. The resolution's "zero-infra" claim is valid on macOS/bare-metal but not on shared cloud VMs. This needs explicit documentation and a runtime capability check at `CodeSandbox.create()` time — not a hard error, but a clear error message with a fallback path suggestion, before the user hits it in production.

3. **Failures 3, 4, 5** are real scale concerns but are partially mitigated by the Phase 3 deferral and the solo/dogfood scope. Failure 3 (shared state concurrency) is a bug waiting to happen once `Orchestration` is used at any concurrency; failure 4 (depth cap cross-process) is a design gap that needs a schema field before durable multi-agent ships; failure 5 (seq-allocation contention) is a performance concern, not a correctness issue, and can be fixed by using a Postgres SEQUENCE instead of MAX()+1.

---

## Evidence checked

- `sandboxes-multiagent.md` §microsandbox: "rootless KVM" — verified that libkrun requires a hypervisor (KVM on Linux, Hypervisor.framework on macOS). No mention of shared-cloud KVM unavailability.
- `production-topology.md` D3: "write the step checkpoint in the **same transaction** as the tool's writes" — transaction-piggyback applies only to Postgres-touching tools, not external APIs.
- `sandboxes-multiagent.md` §6 (Decision 6): fan_out described with `asyncio.gather + Semaphore`; open unknown #5 explicitly acknowledges the cancellation-result contract is unresolved, but does not name double-fire as a concern.
- `production-topology.md` D10: single-writer-per-run guard exists; no equivalent for fan_out workers sharing a run_id.
- `_RESOLUTIONS.md` §1A #4: multi-agent confirmed Phase 3; depth-cap-1 confirmed; `SubagentResult` confirmed. `depth` parameter is not in the resolved `verso_runs` schema (verified against the C4 schema resolution — schema has `agent_version`, `executor_id`, `recovery_attempts`, but no `depth` or `parent_run_id` despite `parent_run_id` being mentioned in `durable-runtime.md` as present — this is a C4 resolution gap).
- microsandbox teardown `spawn.rs:90`: "rootless child-process spawn" — KVM required, no fallback documented.
- `sandboxes-multiagent.md` Open Unknown #1: smoltcp DNS alias, not KVM availability — confirms KVM is not flagged as an unknown.
- `production-topology.md` schema: `SEQ_ALLOCATION = MAX(seq)+1` — not a Postgres SEQUENCE, confirmed as a hot-row contention pattern under concurrent writers.

---

## Recommendation

**REVISE, not REJECT.** The three topologies + sandbox adapters are the right call to include in v1 scope with Phase 3 implementation. The architecture is sound. Two concrete fixes before Phase 3 build:

1. **Add an explicit durable-fan_out contract:** "workers dispatched inside a durable fan_out must be idempotent OR use a transaction-piggybacked checkpoint (DBOS pattern). Non-idempotent workers in a durable fan_out are explicitly unsupported in v1 — document this at the API surface, not just in design notes." Add a `idempotent=True` flag to `fan_out()` that, when `False`, raises a warning when `durable=True` is active. This is a 10-line API change that prevents a class of invisible bugs.

2. **Add a KVM capability check to `MicrosandboxAdapter.create()`:** attempt a hypervisor probe at first create and raise `SandboxBackendUnavailable("microsandbox requires KVM or Hypervisor.framework. On shared cloud VMs, set backend='e2b'.")` with a clear fallback message. This is a single runtime check, not an architectural change.

3. **Replace `MAX(seq)+1` with a Postgres SEQUENCE per run** in the `verso_run_events` schema (or use `INSERT ... RETURNING` with a SEQUENCE column). This is a schema-level fix that eliminates the fan_out write-contention hot-row before it becomes a measured bottleneck.

4. **Add `current_depth INT DEFAULT 0` to `verso_runs`** so the depth cap survives the submit→wake process boundary in durable mode. The `subagent_delegate` implementation must read `parent_run_id → verso_runs.current_depth + 1` and write it on the child run record before dispatching. This is a single column + one read in `subagent_delegate`.

Items 3 and 4 are schema changes that are cheap now and expensive after the schema ships in production.
