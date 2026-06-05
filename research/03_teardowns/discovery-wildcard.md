# Discovery & Wildcard (2026 Frontier Runtimes) — Verso Research Note

## Cluster: discovery-wildcard

### Systems: Anthropic Managed Agents (Session/Harness/Sandbox) · Google AX (Agent Executor) · Centaur (Paradigm) · Salus (YC W26) · Cloudflare Agents Week 2026 (Agent Memory + Project Think)

*Sources: `github.com/google/ax` @ HEAD (Apache-2.0, preview — cloned `--depth=1` 2026-06-05); `github.com/paradigmxyz/centaur` @ HEAD (MIT — cloned 2026-06-05); `anthropic.com/engineering/managed-agents` (blog, INFERRED); `usesalus.ai` + `pip download salus` (SDK source); `blog.cloudflare.com/introducing-agent-memory` + `agents-week-in-review` (blog, INFERRED). Cross-refs: `03_teardowns/fw-claude-sdk-platforms.md` §1 (Claude Agent SDK harness↔CLI protocol), `03_teardowns/coding-claude-code.md` (Claude Code agent loop), `03_teardowns/infra-serving.md` (streaming/cancellation contract).*

> **Label key:** KNOWN = read from source at `file:line`. INFERRED = from a vendor engineering blog / docs (closed source, no code to read). DESIGNED = my reconstruction of a gap for Verso. Anthropic Managed Agents, Salus, and Cloudflare are closed; their depth comes from exhaustive blog reading + SDK probing, honestly labeled.

---

## Anthropic Managed Agents — Session / Harness / Sandbox

> **Closed (first-party hosting).** Source from the engineering blog "Scaling Managed Agents" (`anthropic.com/engineering/managed-agents`), read in full; interface names below are KNOWN-from-blog (the post gives the actual method signatures), the rest INFERRED. This **extends** `fw-claude-sdk-platforms.md` §1 (the Claude Agent SDK = process-orchestrator/protocol-bridge over the `claude` CLI) and `coding-claude-code.md` (the in-binary agent loop). Those two teardowns cover the *SDK↔CLI* seam; this covers the *managed-infra* seam the SDK never exposes: the durable Session log, the stateless Harness, and the lazy Sandbox. It is the single most important published reference for Verso's tactical↔durable seam at scale.

### What It Is

Anthropic's production layer for hosting Claude agents, factored into three decoupled virtualized entities. The headline change vs. the naive design (everything in one container): **the harness no longer lives inside the container.** Decoupling the brain (Harness) from the hands (Sandbox), with the durable record (Session) living outside both, cut **p50 time-to-first-token ~60% and p95 over 90%** (KNOWN, blog) — where TTFT is "the delay between accepting work and producing its first response token." The win comes from not paying container-provision latency on the critical path for the (common) requests that never touch a sandbox.

This maps 1:1 onto Verso's headline question — it is the only published production account of the tactical↔durable seam: **Session = the durable event log; Harness = the stateless, horizontally-scalable loop that runs against it; Sandbox = the side-effectful execution environment, provisioned lazily.**

### The Three-Entity Contract (KNOWN — blog method signatures)

**Session — the durable event log.** "An append-only log of everything that happened." It lives *outside* the harness and survives harness crashes. Interface (KNOWN, verbatim from blog):
- `emitEvent(id, event)` — append; "keeps a durable record of events."
- `getEvents()` — read, "selecting positional slices of the event stream" (i.e. range/slice reads, not just full replay — the substrate for resume-since-N).
- `getSession(id)` — retrieve a session's event log.

The Session is the only durable thing. Everything else is disposable and rebuilt from it. (Directly parallel to AX's `ConversationEvent` log and Centaur's Postgres run/checkpoint tables — three independent 2026 production systems converging on "the append-only event log is the single source of truth.")

**Harness — the stateless loop (the brain).** "The loop that calls Claude and routes Claude's tool calls." Design invariant (KNOWN, verbatim): "**nothing in the harness needs to survive a crash**" — it holds no durable state; all state is in the Session. Recovery interface:
- `wake(sessionId)` — boot a harness (any harness instance) for a session.
- It then `getSession(id)` → loads the event log → resumes "from the last event."

Because the harness is stateless and the Session is external, **any harness instance can resume any session**: a crashed harness is simply replaced and `wake(sessionId)` rehydrates the loop from the log. This is the horizontal-scalability property — harnesses are a fungible, autoscalable pool; the Session is the sticky durable identity. (This is the *server-side* analog of the SDK's `--resume <session-id>` from `fw-claude-sdk-platforms.md:141`: the SDK resume reloads a local JSONL transcript into a fresh CLI subprocess; Managed Agents' `wake(sessionId)` reloads the durable Session log into a fresh harness instance — same pattern, one level up the stack.)

**Sandbox — the side-effect environment (the hands).** "The execution environment where Claude can run code and edit files." Interface (KNOWN, verbatim):
- `provision({resources})` — create a container with a resource spec.
- `execute(name, input) → string` — run a tool; returns a string result.

Crucially, container death is demoted to a recoverable error: a dead container "becomes a tool-call error" rather than a session failure. The harness sees a failed `execute()`, can re-`provision()`, and the loop continues — the durable Session is unaffected.

### Why Stateless-Harness Beats Container-Resident Loop (KNOWN reasoning — blog)

The pre-decoupling design ran the harness *inside* the container, so the agent loop's liveness was tied to the container's. Two failure modes that the decoupling fixes:
1. **Provision-on-the-critical-path.** With the loop in the container, you must boot a container before the first token, even for a pure-text answer. Decoupling + lazy sandbox removes container boot from the median path — the source of the p95 −90%.
2. **Crash = work lost.** A container crash with the loop inside it loses the in-flight loop state. With the loop stateless and the Session external, a crash is recovered by `wake(sessionId)` on a fresh harness — no work lost, because every step was an emitted event. This is also what lets harnesses autoscale: they're a stateless pool behind `wake()`, and the Session is the only sticky identity.

The trade AX/Centaur/Anthropic all accept: you re-derive loop state from the log on resume (a `get_events` + replay) rather than keeping it warm. For agent loops this is cheap relative to the model calls, and it buys fungible, crash-safe, autoscalable workers.

### Lazy Sandbox — Provision on First Tool Call (KNOWN — blog)

The central latency optimization (and the exact default Verso wants): **the sandbox is provisioned by the brain via a tool call, only if it is needed.** Verbatim: "containers are provisioned by the brain via a tool call `(execute(name, input) → string)` only if they are needed." A session that answers from the model alone — no code execution, no file edits — never provisions a container at all, so it skips the entire container-cold-start cost. The trigger is precisely: **Claude emits its first tool call that requires the sandbox** → the harness calls `provision({resources})` → then `execute(name, input)`. This is the mechanism behind the p95 −90% TTFT: the median request's first token is no longer gated on a container boot.

The lazy-init story is behaviorally confirmable (the brief's probe #4): a request that needs code execution should show higher TTFT than one that doesn't, because only the former pays provisioning. (Probe not run in this environment — Managed Agents has no open endpoint here — but the blog states the mechanism directly.)

### Reimplementing the Seam (DESIGNED — for Verso, grounded in the KNOWN interfaces)

The blog gives the interface, not the bodies. Here is the seam reconstructed at reimplementable depth, every line either KNOWN-shaped (matches a published signature) or DESIGNED (Verso's fill). A senior engineer can build the Session+stateless-Harness from this:

```python
# DESIGNED — the durable Session, matching the KNOWN interface
#   emitEvent(id, event) / getEvents(slice) / getSession(id)
class Session:                       # one row-group per session_id, append-only
    # event = {seq, type, payload, ts}; types: "user", "assistant",
    #         "tool_use", "tool_result", "sandbox_provisioned", "error"
    async def emit_event(self, session_id, event) -> int:    # returns seq
        # append-only; seq = next monotonic int for this session
        ...
    async def get_events(self, session_id, since_seq=0) -> list:  # slice read
        # "selecting positional slices of the event stream" (KNOWN) → since_seq
        ...

# DESIGNED — the stateless Harness; holds NO durable state (KNOWN invariant)
async def wake(session_id, session: Session, sandbox_pool):
    events = await session.get_events(session_id)        # rehydrate from log
    messages = replay_to_messages(events)                # rebuild Claude history
    sandbox = None                                       # LAZY: not provisioned
    while True:
        resp = await anthropic.messages(model, messages) # /v1/messages
        await session.emit_event(session_id,
                                 {"type": "assistant", "payload": resp})
        if resp.stop_reason == "end_turn":
            return
        for tu in resp.tool_use_blocks:
            await session.emit_event(session_id,
                                     {"type": "tool_use", "payload": tu})
            if needs_sandbox(tu) and sandbox is None:     # LAZY TRIGGER
                sandbox = await sandbox_pool.provision({"resources": ...})
                await session.emit_event(session_id,
                                         {"type": "sandbox_provisioned"})
            try:
                result = (await sandbox.execute(tu.name, tu.input)
                          if needs_sandbox(tu) else await run_local(tu))
            except SandboxDead:                           # container death =
                sandbox = None                            #   tool-call error,
                result = {"error": "sandbox died; retry"} #   NOT session death
            await session.emit_event(session_id,
                                     {"type": "tool_result", "payload": result})
            messages.append(tool_result_message(tu, result))
```

The properties this guarantees (all KNOWN-required): (1) a crash anywhere is recovered by re-calling `wake(session_id)` on *any* worker — `get_events` + `replay_to_messages` reconstruct exact loop state, because every decision-relevant fact was `emit_event`'d; (2) the sandbox is `None` until the first `needs_sandbox` tool call, so sandbox-free sessions never provision; (3) `replay_to_messages` is the only nontrivial DESIGNED piece — it folds the event log back into the `messages[]` array `/v1/messages` expects, which is exactly the Claude Code in-context round-trip (`coding-claude-code.md:20`) read from the log instead of memory.

### Tool Calls ↔ Session Serialization (INFERRED + cross-ref)

The blog confirms `emitEvent(id, event)` records events during the loop but does **not** publish the event schema or the tool-call serialization format (KNOWN-absent). What the loop must serialize is dictated by the resume contract ("resume from the last event" must reconstruct loop state): each Claude turn's `tool_use` blocks and their `tool_result`s must be appended as events, so that on `wake()` the replayed log reproduces the exact message history the next `/v1/messages` call needs. This is the same content the Claude Code loop already round-trips in-context (`coding-claude-code.md:20`: "parse tool_use blocks → execute tools → feed results back"); Managed Agents externalizes that round-trip into the Session log. The closest readable analog is AX's `ExecutionEvent{inputs, outputs}` and Claude Code's local JSONL transcript (`~/.claude/projects/<hash>/<session-id>.jsonl`, `fw-claude-sdk-platforms.md:137`) — Managed Agents is that transcript, promoted to a durable network service with slice reads.

### `memory/` FUSE Directory Lifecycle (INFERRED — blog is silent on mechanism)

The blog (this version) does **not** describe the FUSE-mounted `memory/` directory or its cross-restart lifecycle (KNOWN-absent in the read). What the brief describes — a versioned, FUSE-mounted filesystem exposed into the container as session-spanning state, as an alternative to a vector-DB memory API — is consistent with the architecture but unconfirmed by this source, so it is INFERRED and flagged. The architecturally sound reading: persistent agent memory is a *filesystem* the sandbox mounts (so the agent uses ordinary file I/O, not a memory SDK), versioned and re-attached on each new sandbox `provision()` for the same session, with the durable bytes living outside the disposable container (same principle as Session: the container is disposable, the mounted state is durable). This contrasts with Cloudflare Agent Memory's managed extract→embed→Vectorize service (this file, CF section): Anthropic's model (as described in the brief) is "memory is a mounted versioned filesystem," CF's is "memory is a managed retrieval API." Both avoid making the agent author embeddings; they differ on whether memory is files or a service.

### Credential Boundary — Tokens Never Enter Sandbox or Harness (KNOWN — blog)

Two mechanisms, both enforcing "the agent never handles the token":
1. **Git token bundling.** "We use each repository's access token to clone the repo during sandbox initialization and wire it into the local git remote" — so git operations work "without the agent ever handling the token itself." The token is baked into the remote URL at provision time, then the agent just runs `git`.
2. **MCP proxy + vault.** "For custom tools, we support MCP and store OAuth tokens in a secure vault." Architecture (verbatim): "Claude calls MCP tools via a dedicated proxy; this proxy takes in a token associated with the session. The proxy can then fetch the corresponding credentials from the vault." So the proxy holds a *session token* (not the real credential), exchanges it at the vault for the actual OAuth credential, and injects it on the outbound MCP call. The hard invariant (verbatim): "**the harness is never made aware of any credentials**," and tokens never reach the sandbox where generated code runs.

This is the *same architecture* as Centaur's iron-proxy (this file, Centaur section) and the brief's auth-gated tool design: a per-session proxy injects real credentials at the network boundary; the agent and the loop hold only opaque session handles. Three independent 2026 systems (Anthropic MCP proxy, Centaur iron-proxy, Salus-shaped validation proxy) all land on "a credential/policy proxy in front of every tool, agent holds no secret." For Verso this is now an overdetermined design choice, not a guess.

The MCP-proxy credential exchange, reconstructed (DESIGNED, grounded in the KNOWN verbatim flow "proxy takes a session token → fetches credentials from vault → injects"):
```python
# DESIGNED — the dedicated MCP proxy; agent/harness hold only session_token
async def mcp_proxy(session_token, mcp_call):           # one proxy per session
    cred_id = session_to_cred(session_token, mcp_call.server)  # session-scoped
    real_cred = await vault.fetch(cred_id)              # vault holds the secret
    outbound = inject_credential(mcp_call, real_cred)   # at the egress boundary
    return await forward(outbound)                      # agent never sees cred
```
The invariant `the harness is never made aware of any credentials` (KNOWN verbatim) means even the loop process must not see `real_cred` — the exchange happens entirely inside the proxy. Git is the degenerate case: the credential is wired into the git remote URL at `provision()` time, so the agent's `git push` carries the token without the agent ever reading it.

### For Verso

- **The exact seam: Session (durable event log) + stateless Harness + lazy Sandbox.** This IS Verso's tactical↔durable seam, validated at production scale with numbers. Implement: (a) a durable append-only Session with `emitEvent` / range-read `getEvents()` (Verso already has this from the AX/Centaur event-log designs); (b) a Harness loop that holds **zero** durable state — every loop-relevant fact is an event — so `wake(session_id)` on any worker rehydrates it; (c) a Sandbox provisioned only on the first tool call that needs it.
- **"Nothing in the harness survives a crash" is the design test.** If any Verso loop state can't be reconstructed by replaying the Session log, that state is a bug — it makes the harness non-fungible and breaks horizontal scaling. The discipline (every decision-relevant fact is an emitted event) is what makes any-harness-resumes-any-session work.
- **Lazy sandbox is the right default and the headline latency win.** Don't provision an execution environment at session start. Provision on the first tool call that needs it. Verso sessions that answer from the model alone should pay zero container cost — the blog's p95 TTFT −90% is the prize, and it's the single highest-ROI architectural decision in the post. (Cross-ref `infra-serving.md` TTFT contract: this is the agent-loop analog of pre-warming the engine but lazily provisioning per-request resources.)
- **Container death = tool-call error, never session death.** Make the Sandbox disposable: a dead container surfaces as a failed `execute()` the harness can retry by re-provisioning. The durable Session never sees it. Verso's tool-execution errors must be recoverable loop events, not run-fatal.
- **Credential proxy with session-scoped tokens.** The harness and sandbox hold only a *session token*; a proxy exchanges it at a vault for the real credential and injects it at egress. Combined with Centaur's per-host scoping and Salus's pre-call validation, Verso's tool boundary is: validate → resolve session-token→credential → inject per-host → forward, with the agent process never holding a real secret at any step.
- **Set Verso's latency target from these numbers.** p50 TTFT −60% / p95 −90% from decoupling is the published benchmark; Verso's managed tier should target the same shape (decoupling removes container-provision from the median critical path) and measure TTFT = accept-work → first-response-token, the same definition.

---

## Google AX (Agent Executor)

### What It Is

`github.com/google/ax` — Google's open-source (Apache-2.0, explicitly "in active development… significant breaking changes") **distributed agent runtime that is separate from the framework**. It is not an agent SDK; it is the durable substrate underneath one. AX coordinates agentic loops with an **append-only event log + per-execution replay**, routes between local and remote agents over gRPC, runs each conversation as an isolated **SubstrATE actor** (Kubernetes), and exposes `fork` (branch a trajectory), `resume`/`--last-seq` (replay-since-N attach), and confirmation-based HITL. It wraps ADK / Antigravity / A2A agents as registry entries — the loop body is pluggable; the durability seam is AX's.

The decisive architectural fact: **AX records outputs, not inputs.** Unlike Temporal's deterministic-replay model (re-execute the function, intercept side effects, require a determinism sandbox), AX's executor writes every agent output to the log as it happens and, on resume, *feeds the recorded history back as the new prompt* rather than re-running the prior steps. Any non-deterministic code can run in the agent because the log is the source of truth, not a replay of inputs. This is the exact "event-log-not-replay" alternative Verso's `durable=True` backend should weigh.

### The Event-Log Format (KNOWN — `proto/ax.proto`, `executor/sqlite.go`)

Two distinct event types, two distinct logs (`ax.proto:54-86`):

```proto
// ConversationEvent — the user-visible, seq-ordered history (one conversation = N executions)
message ConversationEvent {
  string conversation_id = 1;
  int32  seq             = 2;   // monotonic per-conversation; client tracks last seen
  string exec_id         = 3;
  repeated Message messages = 4;
  State  state           = 5;   // PENDING | FAILED | COMPLETED
}
// ExecutionEvent — the internal replay log for ONE execution (not surfaced to client)
message ExecutionEvent {
  string exec_id = 1;
  string agent_id = 2;
  bytes  agent_config = 3;
  repeated Message inputs  = 4;
  repeated Message outputs = 5;
  State  state = 6;
  google.protobuf.Timestamp timestamp = 7;
}
enum State { STATE_UNSPECIFIED=0; STATE_PENDING=1; STATE_FAILED=2; STATE_COMPLETED=3; }
```

`Message{ role, Content, internal_only }`. `internal_only=true` messages are **persisted to the execution log for resumption but never emitted to the client or any other agent** (`ax.proto:58-61`) — this is how AX carries scratch/tool-plumbing state in the durable log without polluting the conversation. (Cf. Claude Agent SDK's `transcript_mirror` side-channel in `fw-claude-sdk-platforms.md` §1: same idea — durable side-channel that must never reach the message stream.)

**Wire encoding is protojson, NOT binary protobuf.** `executor/eventlog.go:47-48`:
```go
var marshalOpts   = protojson.MarshalOptions{UseProtoNames: true}
var unmarshalOpts = protojson.UnmarshalOptions{DiscardUnknown: true}
```
`DiscardUnknown:true` is the forward-compat hedge for a preview schema. Each event row is a JSON string.

**Storage = SQLite, two tables** (`executor/sqlite.go:51-76`, KNOWN verbatim):
```sql
CREATE TABLE conversation_log (
  conversation_id TEXT NOT NULL, seq INTEGER NOT NULL,
  payload TEXT NOT NULL,                       -- protojson(ConversationEvent)
  PRIMARY KEY (conversation_id, seq));
CREATE TABLE execution_log (
  exec_id TEXT NOT NULL, payload TEXT NOT NULL, -- protojson(ExecutionEvent)
  timestamp DATETIME NOT NULL);
CREATE INDEX idx_execution_log_exec_id ON execution_log(exec_id);
```
- **Seq allocation** (`sqlite.go:82-90`): `SELECT COALESCE(MAX(seq),0)+1 FROM conversation_log WHERE conversation_id=?` then INSERT. No DB autoincrement — seq is computed per-conversation, the PK enforces uniqueness. Concurrency is serialized by the single-writer Controller (below), so the read-then-insert race is structurally avoided, not locked.
- `dsn = path?_pragma=busy_timeout(10000)` (`sqlite.go:35,44`) — 10 s busy timeout; modernc.org/sqlite (pure-Go, CGo-free).
- Replay ordering: conversation events by `seq`; execution events by `timestamp` (`sqlite.go:135,164`).

### Single-Writer Controller + the Resume Algorithm (KNOWN — `controller/controller.go`)

`Controller` (`controller.go:43-49`) is documented as "the **single-writer** orchestrator". One controller owns one `EventLog`. Topology terms: a **Router/substrate** brings up the per-conversation actor; the **Controller** is the single writer of execution+conversation state; the **Actor/agent** is the loop body that only sees the history handed to it (it never reads the log directly — `agent_executor.go` "does NOT load conversation history; the caller passes the relevant messages in start.Messages", `agent_executor.go:33`). That Controller-state-vs-Actor-view split is the property to copy.

**`Exec`** (`controller.go:164-205`): require `conversation_id`; build planner (default `gemini.NewGeminiPlannerAgent`, `controller.go:68-70`); clone registry and inject `__planner` + `gemini` reserved agents; if `agent_id==""` route to `__planner`; then `tryResuming`; if not done, `execute` a fresh `exec_id = uuid`.

**`tryResuming`** (`controller.go:88-159`) is the seam to copy verbatim:
1. Load ALL `ConversationEvent`s for the conversation. Track the single `pendingExecID`: an exec is pending iff it emitted a PENDING event and never a COMPLETED one (a COMPLETED event for that exec clears it). Accumulate `history` from every event's messages.
2. **Replay-since-N (the `ax attach` semantics):** if `req.LastSeq != 0`, re-send every event with `seq > LastSeq` to the handler (so a reconnecting client gets exactly the events it missed), and error `last_seq %d not found` if the watermark isn't in the log (`controller.go:104-122`). This is at-least-once replay keyed on a client-held watermark — no server-side cursor.
3. If `pendingExecID==""` → nothing in flight, return history (caller starts a new exec).
4. Else load `ExecEvents(pendingExecID)`, find the PENDING `ExecutionEvent`, and `execute(...)` it with the recovered `agent_id`/`agent_config`/`history` — i.e. **resume the interrupted execution from its recorded inputs**, not from a code checkpoint.

**`execute`** (`controller.go:207-258`) is the durable write protocol per turn:
1. Append a PENDING `ConversationEvent` with the new inputs (so a crash mid-turn still has the inputs logged).
2. Run the executor; its `outputCapturer` filters `internal_only` messages, appends each batch as a PENDING `ConversationEvent`, gets back a `seq`, and streams `ExecResponse{Outputs, Seq}` to the gRPC handler.
3. On return, append a terminal `ConversationEvent` carrying the final `State` (COMPLETED/FAILED).

### The Executor Loop & Sub-Agent Spawning (KNOWN — `executor/executor.go`, `agent_executor.go`)

`EventLog` interface (`eventlog.go:27-44`): `Append(ConversationEvent)→seq`, `AppendExec(ExecutionEvent)`, `Events(convID)`, `ExecEvents(execID)`, `DeleteEvents(convID)`, `Close()`. Doc: "**replaying the log in order brings the executor back to a consistent state from which execution can resume.**"

`defaultExecutor.Exec` (`executor.go:51-82`): reconstruct per-exec `history` from `ExecEvents` (concatenate every event's `inputs` then `outputs`, last non-zero `State` wins, `executor.go:142-166`). Three guards: (a) if history's tail `WaitsForConfirmation` and the new inputs carry no confirmation answer → emit the question again and return PENDING (HITL idempotence); (b) if `earlierAgentID != start.AgentId` → hard error "**resumption not allowed: agent ID changed**" (you cannot resume a conversation under a different agent); (c) if already COMPLETED → return immediately (replay cache hit).

`defaultExecutor.exec` (`executor.go:84-140`) per turn: log PENDING `ExecutionEvent` with inputs → `agent.Connect(ctx, convID, execID, start, child, outputBuffer)` (the loop body runs, calling `outputBuffer` for each output batch) → log all outputs as ONE PENDING `ExecutionEvent` (`// TODO: Log only at checkpoints` — currently coarse, `executor.go:124`) → if the final output is **not** an unanswered confirmation, log COMPLETED and return STATE_COMPLETED; else return STATE_PENDING (suspended awaiting HITL).

**Sub-agent spawning** — the `child` passed to `Connect` is an `agentExecutor` (`agent_executor.go:47-111`). An agent calls `e.Exec(...)` on it to invoke a sub-agent *within the same execution boundary*. Sub-exec IDs are composed: `newExecID(parent, child) = parent + "-" + child` (`executor.go:36-41`), so the execution log encodes the full call tree by ID prefix. Sub-agents get only `start.Messages` (no log load), write their own pending/outputs/completed execution events for observability, and return PENDING if they bottom out on a confirmation. This is the multi-agent coordination model: a tree of executions sharing one event log, IDs path-encode the hierarchy.

`Agent` interface (`agent/agent.go:35-43`): `Connect(ctx, convID, execID, *AgentStart, Executor, OutputHandler) error` + `Close()`. `LocalAgent` wraps an in-process `ProcessFunc`; `RemoteAgent` dials a gRPC `AgentService.Connect` stream (`ax.proto:104-110`) — same interface, local or remote, the Controller doesn't care which.

### State Machine + Constants (KNOWN)

| Constant / rule | Value | Source |
|---|---|---|
| Event states | `STATE_UNSPECIFIED / PENDING / FAILED / COMPLETED` | `ax.proto:125-130` |
| Wire encoding | protojson, `UseProtoNames:true`, `DiscardUnknown:true` | `eventlog.go:47-48` |
| Storage | SQLite (`modernc.org/sqlite`, CGo-free), 2 tables | `sqlite.go:51-76` |
| Seq allocation | `MAX(seq)+1` per conversation, PK `(conversation_id, seq)` | `sqlite.go:82-90` |
| SQLite busy timeout | 10 s | `sqlite.go:35` |
| Replay order | conversation by `seq`, exec by `timestamp` | `sqlite.go:135,164` |
| Default planner | `gemini.NewGeminiPlannerAgent` (agent id `__planner`) | `controller.go:32,68-70` |
| Reserved agent ids | `__planner`, `gemini` | `controller.go:31-39` |
| Resume guard | reject if `agent_id` changed mid-conversation | `executor.go:74-76` |
| Completed short-circuit | COMPLETED exec returns immediately (no re-run) | `executor.go:78-80` |
| Sub-exec id | `parent + "-" + child` | `executor.go:36-41` |
| In-flight guard | per-conversation, `FailedPrecondition` on collision | `server.go:163-178` |
| Default harness port | `:50053` (SubstrATE `HarnessService.Connect`) | `substrate.go:48` |
| Auto-suspend delay | 50 ms after each Exec/Fork/Delete, 10 s suspend timeout | `server_ate.go:74-90` |
| CreateActor idempotency | `AlreadyExists` swallowed (follow-up turns) | `substrate.go:78-81` |

### Message Content Model + Agent Registry (KNOWN — `content.proto:211-224`, `registry.go`)

The `Message.content` is one `Content` with a `oneof type` (`content.proto:211-224`) — this is AX's universal turn schema, worth copying as Verso's internal message model:
```proto
oneof type {
  ThoughtContent thought = 5;       TextContent text = 10;
  ImageContent image = 11;          AudioContent audio = 12;
  DocumentContent document = 13;    VideoContent video = 14;
  ToolCallContent tool_call = 24;   ToolResultContent tool_result = 25;
  ConfirmationContent confirmation = 26;   // HITL suspend/resume token
}
```
- `ToolCallContent{ id, signature, FunctionCallContent{ name, google.protobuf.Struct arguments } }` and `ToolResultContent{ call_id, signature, FunctionResultContent{ name, Struct response } }` — tool args/results are `google.protobuf.Struct` (arbitrary JSON), and **both carry a `signature` bytes field "for backend validation"** (`content.proto:67-100`): the model-emitted tool call is signed so the backend can verify it wasn't tampered with between turns — a detail Verso should note if it ever round-trips tool calls through an untrusted boundary.
- Multimodal blocks carry either inline `bytes data` or a `uri`, plus a `MediaResolution {LOW..ULTRA_HIGH}` knob (`content.proto:103-135`). `ThoughtContent` (reasoning) is a first-class content type, distinct from `text`.

**Agent registry** (`registry.go`): a `Registry{ agents map[id]Agent, agentInfo map[id]*AgentInfo }` under `sync.RWMutex`. `RegisterLocal(LocalAgentConfig)` / `RegisterRemote(RemoteAgentConfig)` both validate the id (reserved ids `__planner`/`gemini` rejected) and refuse duplicates. The Controller `maps.Clone`s the registry per `Exec` and injects the planner — so each execution gets an immutable snapshot of the agent set. This is how AX stays framework-agnostic: an ADK agent, an A2A agent, a LangGraph agent all register as an `Agent` (local in-process or remote gRPC), and the Controller routes by id without knowing the framework.

### Worked Resume Trace (KNOWN — `controller.go:88-205`)

A crash-resume of a 2-turn conversation, to make the seam concrete:
1. Turn 1 runs: `execute()` appends `ConversationEvent{seq=1, exec=A, msgs=[user], PENDING}`, then per-output `{seq=2, exec=A, msgs=[assistant…], PENDING}`, then terminal `{seq=3, exec=A, COMPLETED}`. Crash before turn 2.
2. Client reconnects, calls `Exec{conversation_id, last_seq=3, inputs=[user2]}`.
3. `tryResuming` loads events 1-3; `pendingExecID` ends `""` (exec A reached COMPLETED, which cleared it). `last_seq=3` is found → no replay needed (client already saw ≤3). Returns `history=[user, assistant…]`, `done=false`.
4. `execute()` starts fresh exec B with `uuid`, appends `{seq=4, exec=B, msgs=[user2], PENDING}`, runs the loop with `history+[user2]`, streams outputs as `{seq=5…, PENDING}`, ends `{seq, exec=B, COMPLETED}`.

If instead the crash hit *mid-turn-1* (exec A had a PENDING but no COMPLETED): step 3's `pendingExecID="A"`, so `tryResuming` loads A's `ExecEvents`, finds the PENDING `ExecutionEvent`, and re-`execute`s A from its recorded inputs — `done=true`, the interrupted execution resumes rather than starting a new one. This is the entire durability story: a single pending-exec marker + replay of the recorded inputs.

### `ax fork` — Checkpoint-as-Branch (KNOWN — `controller.go:270-325`, `cmd/ax/fork.go`, `ax.proto:160-185`)

`ForkConversationRequest{ src_conversation_id, src_seq (0=latest), dest_conversation_id }`. Implementation:
1. Load all `src` events. Error if none.
2. If `src_seq > 0`: walk events, **truncate the slice at the exact seq match** (`events = events[:i+1]`), error `src_seq %d not found` if the watermark isn't an actual event boundary — explicitly rejecting "silently fork all events" on a typo'd/stale checkpoint (`controller.go:287-308`, the comment calls this out by name).
3. Copy each event into a new `ConversationEvent` with `dest_conversation_id` but **preserving the original `seq`, `exec_id`, `messages`, `state`**, appending to the log.

So a fork is a cheap log-copy up to a checkpoint; both branches then diverge by appending new events independently. `dest_conversation_id` is **required** at the server boundary (`server.go:92-94`) because "the substrate router uses it to bring up the actor for the new conversation *before* the request reaches this handler" — the actor must exist before the fork writes land. This is the cleanest published implementation of checkpoint-branch for eval/what-if: no snapshot blobs, just a seq-bounded event replay into a new conversation id. (`TODO(jbd): Replace src_seq with snapshot_id` — they intend to move to opaque snapshot handles later; today it's pure seq.)

### SubstrATE Actor Lifecycle (KNOWN — `harness/substrate.go`, `server/server_ate.go`, `internal/experimental/k8s/ate/`)

Each conversation maps 1:1 to a **SubstrATE actor** (k8s, `github.com/agent-substrate/substrate`). `ate.Client` (KNOWN) exposes three control-plane RPCs on `api.ate-system.svc:443`: `CreateActor(id, templateNS, templateName)`, `ResumeActor(id)→{Actor{AteomPodIp}}`, `SuspendActor(id)`.

`SubstrateHarness.Start` (`substrate.go:72-110`): `CreateActor` is **idempotent** — on follow-up turns the actor already exists, so `codes.AlreadyExists` is expected and swallowed. `ResumeActor` schedules it onto a worker and yields a routable `AteomPodIp`; the harness then dials `AteomPodIp:50053` for the gRPC `HarnessService.Connect` bidi stream. On `Close`, `SuspendActor` returns the actor to the standby pool (`substrate.go:177-192`).

**Suspend-on-idle is automatic and aggressive:** after every `Exec`/`Fork`/`Delete`, the server fires `go suspendActor(conversationID)` (`server.go:74,106,126`), which sleeps **50 ms** then calls `SuspendActor` with a 10 s timeout (`server_ate.go:74-90`). So an actor is live only during an active turn; between turns it's suspended (hibernated), and the next turn resumes it by id. This is the "agent survives restarts" property: the actor is disposable, the SQLite event log is the durable state, the actor id is stable. Build-tagged: `server_ate.go` (`//go:build ate`) vs `server_no_ate.go` (no-op `suspendActor`) — substrate is opt-in via `AX_SUBSTRATE=1`.

### HITL — Confirmation as a Suspend Point (KNOWN — `historyutil/confirmations.go`, `cmd/ax/exec.go:180-245`)

HITL is modeled entirely in the message content. `ConfirmationContent{ id, question, oneof{ ApprovalDecision approval | DeclineDecision decline } }` (`content.proto:40-49`). The loop suspends (returns STATE_PENDING, logs no COMPLETED) whenever the last output is a confirmation with a non-empty `question` and no decision attached (`confirmations.go:21-30`, `executor.go:129-137`). The client (`exec.go:180-245`) detects the confirmation, prompts the user, and re-`Exec`s with a `Message` carrying `ApprovalDecision{approved:true}` or `DeclineDecision{declined:true}` and the same `conf.Id`. On resume, `HasConfirmationAnswer` (`confirmations.go:34-51`) sees the answer in the new inputs and lets the loop proceed. No callback registry, no external signal channel — the suspend/resume is just "the log ends on an unanswered question; the next turn's inputs answer it."

**Server in-flight guard** (`server.go:163-178`): a per-conversation `inFlight map[string]struct{}` under a mutex; concurrent `Exec`/`Fork`/`Delete` on the same conversation returns `FailedPrecondition "already in flight"`. Single-writer is enforced at the RPC boundary, not just by convention.

### For Verso

- **Record outputs, not inputs.** AX's whole durability model is "append every output to the log; on resume, feed the recorded history back as the prompt." This sidesteps Temporal's determinism-sandbox requirement entirely (`durable-execution.md` covers the replay alternative). For Verso's `durable=True`, this is the lower-ceremony seam: a Python agent body runs arbitrary non-deterministic code, and Verso only needs to (a) append each output batch with a monotonic seq, (b) on resume, reconstruct `history` from the log and re-enter the loop. The cost is you re-prompt the model with full history rather than skipping completed steps — acceptable for agent loops, where the LLM call is the expensive non-idempotent step you *want* to avoid repeating, and AX avoids it by only re-running the *pending* exec, not completed ones (the `STATE_COMPLETED` short-circuit at `executor.go:78`).
- **Two logs: conversation (client-facing, seq-ordered) vs execution (internal, replay).** Verso should separate the user-visible turn stream from the internal step/tool-plumbing log. AX's `internal_only` flag (persist-but-don't-emit) is the exact mechanism — Verso's durable log needs a "side-channel" bit so scratch state survives a crash without leaking into the transcript or sub-agent prompts.
- **`--last-seq` replay-since-N is the entire resumable-streaming protocol.** Client tracks the last seq it rendered; on reconnect it sends `last_seq=N`; server re-streams every event with `seq>N` and errors if N isn't a real boundary. No server-side cursor, no session affinity needed — the watermark lives on the client. Verso's streaming reconnect should copy this exactly (cross-ref `infra-serving.md` "disconnect propagation": AX's answer to reconnect is replay-from-watermark, not resume-the-socket).
- **Fork = seq-bounded log copy into a new id.** Verso's eval/what-if branch primitive needs nothing more than "copy events `[0..seq]` to a new conversation id, preserving seqs." No snapshot serialization. The one hard rule worth stealing: reject a fork whose `src_seq` isn't an actual event boundary (don't silently fork-all on a stale checkpoint).
- **Single-writer + in-flight guard.** One writer per conversation, enforced by a `FailedPrecondition` at the RPC layer (`inFlight` map). Verso's durable backend must reject concurrent writers to the same run rather than racing the seq allocator.
- **Actor is disposable; log is durable; id is stable.** SubstrATE suspends the actor 50 ms after each turn and resumes-by-id on the next. Verso's hosted tier can hibernate idle agent containers and rehydrate from the event log on the next message — the container holds no durable state, so a restart is a resume, not a recovery. Provision-on-resume (the `dest_conversation_id`-required-for-fork constraint) is the lesson: the execution environment must exist before the durable writes land.
- **Sub-agent IDs path-encode the call tree (`parent-child`).** Free, debuggable multi-agent topology with zero extra bookkeeping — Verso's sub-agent spawner should compose exec IDs the same way so the log alone reconstructs who-called-whom.
- **HITL = "log ends on an unanswered question."** No signal channel, no external callback registry. The suspend point is data (a confirmation message with no decision); the resume is the next turn's inputs carrying the decision. Verso can model every interrupt (approval, tool-permission, clarification) as this one pattern.

---

## Centaur (Paradigm)

### What It Is

`github.com/paradigmxyz/centaur` (MIT) — Paradigm's self-hosted, multi-user ("multiplayer") agent runtime, open-sourced after ~18 months internal production use at the fund. Slack-fronted; each conversation thread runs a coding-agent harness (Claude Code / Codex / amp / pi-mono) inside a **per-thread Kubernetes sandbox Pod**. The architecture is the most concrete open implementation of three Verso concerns at once: (1) an **egress credential proxy** (`iron-proxy`) so the agent never holds API keys; (2) a **tool-as-plugin** model (`pyproject.toml` + a `_client()` factory → auto-generated REST endpoints); (3) a **stateless FastAPI control plane + Postgres checkpoint/replay workflow engine** that survives restarts with no orchestration server. The whole product is stateless services + Postgres; nothing in a Pod is durable.

The repo is TS at the edges (Slackbot, api-client, harness-events) but the load-bearing services are Python (`services/api`, FastAPI) and Go (`iron-proxy` binary, not vendored — configured by YAML the API renders). The pieces below are read from the Python source.

### iron-proxy — Per-Destination-Host Credential Injection (KNOWN — `proxy_config.py`, `tool_manager.py`, `iron-proxy.yaml`)

iron-proxy is a **MITM TLS forward proxy** (`tls.mode: "mitm"`, its own CA at `/etc/iron-proxy/ca.crt`) that sits between the sandbox and the internet. The sandbox's `HTTPS_PROXY` points at it (`:8080` tunnel) and its DNS (`:53`) resolves everything to the proxy IP. The agent makes ordinary HTTPS calls with *placeholder* credentials (or none); the proxy terminates TLS, **injects/replaces/signs the real credential per destination host**, re-encrypts, and forwards. The agent process never sees a real key. A management API on `:9092` (guarded by `IRON_MANAGEMENT_API_KEY`) reconfigures it live.

The credential map is rendered by the API server (`render_proxy_yaml`, `proxy_config.py:520-570`) from typed secret declarations into iron-proxy "transforms," each scoped by `rules: [{host: H}]` so **a tool's credential is only ever offered to the upstream it belongs to** (`tool_manager.py:104-107` comment: "a tool's credentials are never offered to an unrelated upstream"). Six transform types (each a `SecretDef` dataclass in `tool_manager.py:71-374`):

| Transform | Secret type | What iron-proxy does at egress |
|---|---|---|
| `secrets` (replace) | `HttpSecret(mode=REPLACE)` | Tool writes a placeholder `replacer` token into a header/path/query; proxy swaps it for the resolved value. Scan locations named explicitly via `match_headers`/`match_path`/`match_query`. |
| `secrets` (inject) | `HttpSecret(mode=INJECT)` | Proxy adds the header itself (optional Go-template `formatter` like `Bearer {{.Value}}`) or query param; tool emits nothing. |
| `secrets` (broker) | `BrokeredTokenSecret` | `source:{type:token_broker, credential_id, ttl:"1m"}` — a token broker mints the OAuth2 access token; proxy injects `Authorization: Bearer {{.Value}}`. Proxy-side cache TTL must be < broker token lifetime (`proxy_config.py:80-88`). |
| `gcp_auth` | `GcpAuthSecret` | Loads a GCP SA keyfile, mints OAuth2 tokens for `scopes`, injects `Authorization: Bearer` on `*.googleapis.com` (or scoped hosts). One transform per keyfile → multiple service accounts coexist, routed by host. |
| `oauth_token` | `OAuthTokenSecret` | Mints OAuth2 tokens for a declared grant (fields, token_endpoint, audience). Entries minting the *same* token merge, unioning hosts/scopes. |
| `hmac_sign` | `HmacSignSecret` | HMAC-signs each request (algorithm, encodings, message template, timestamp format) and injects the signature headers — e.g. exchange APIs. |
| `aws_auth` | `AwsAuthSecret` | Re-signs AWS SigV4: the tool signs with *placeholder* keys, the proxy re-signs with the real `access_key_id`/`secret_access_key`/`session_token`, scoped to `allowed_regions`/`allowed_services`. |

Secret *values* are resolved by the proxy from `source` objects (`_build_source`, `proxy_config.py:95-103`): `{type:env, var:NAME}` or `{type:1password|1password_connect, secret_ref:"op://vault/<ref>/credential", ttl:"10m"}`. So the API renders only *references*; the proxy resolves the actual secret at request time from env or 1Password — the secret never transits the API process or the rendered YAML.

Two more hardening details worth stealing: (a) the **header allowlist** (`iron-proxy.yaml`, ~60 entries + regexes like `/^x-[a-z0-9-]*(api-key|apikey|secret|token|auth|key)$/`) strips every request header *not* on the list before egress — so a compromised agent can't smuggle data out via arbitrary headers. (b) **Postgres egress is also proxied**: sandboxes are denied direct DB access; `iron-proxy` runs per-`PgDsnSecret` Postgres listeners on sequential ports from **5432**, terminating the wire protocol and substituting real DSNs (`_build_postgres_listeners`, `proxy_config.py:487-517`), plus a `centaur_core` listener so the tool-server sidecar can reach the core DB through the proxy (`proxy_config.py:111-127`).

### Tool-as-Plugin: Auto-Register + REST Generation (KNOWN — `tool_manager.py`, `tool_server_app.py`, `tool_sdk.py`)

There is **no `@tool` decorator**. A tool is a directory under `tools/<category>/<name>/` with a `pyproject.toml` and a `client.py` exporting a `_client()` factory. Discovery (`ToolManager._collect_tools`, `tool_manager.py:1703-1812`):
1. Walk each `tools_dir`; a child dir with a `pyproject.toml` is a tool, a child dir *without* one is a **category folder** whose children are scanned (one level: `tools/crypto/alchemy/`). Later dirs **shadow** earlier ones by name (private-overrides-public).
2. From `[tool.centaur]` in the `pyproject.toml`: `secrets`/`optional_secrets` (parsed into the `SecretDef` types above), `module` (default `client.py`), `timeout_s`. Host patterns are validated — catch-all domains (`*`, `*.com`) and bare IPs are rejected (`tool_manager.py:1766-1782`).
3. `_load_tool` (`tool_manager.py:2088-2159`) registers the dir as a synthetic package `shared.tools_runtime.<name>`, `importlib`-loads the module, then `_collect_methods` (`:2161-2188`) calls `_client()` once for a cached instance and exposes **every public, non-lifecycle, non-property bound method** as a tool method (`close/connect/disconnect/shutdown` are reserved; `_`-prefixed skipped).

REST generation (`create_rest_router`, `tool_manager.py:2591-2710`): a single `APIRouter(prefix="/tools", dependencies=[verify_api_key])` with **stable routes that dispatch by live lookup** so hot-reload swaps tools without swapping routes. The surface:
- `GET /tools` — list tools the API key is scoped to (and whose required `replace` secrets resolve);
- `GET /tools/{tool}` — `describe_tool`: per-method JSON schema built from `inspect.signature` + docstring (`describe_tool`, `:2190-2228`);
- `POST /tools/{tool}/{method}` — invoke. Body is the kwargs dict; `Accept: text/plain` returns TOON-encoded output instead of JSON.

Before dispatch, **argument validation is structured** (`_tool_arg_validation_error`, `:1393-1460`): unexpected args return `accepted_args` + `did_you_mean` (alias table + `difflib` suggestions); missing required args are named; six path-like arg names (`output_path`, `save_path`, …) are **forbidden** ("Tools may not write API-process files to caller-supplied paths; return Centaur attachments instead", `:1381-1407`). Per-call, a `ToolContext{name, secrets, thread_key, container_id}` is set in a `ContextVar` (`tool_sdk.py:19-39`) so `secret(key)` inside a tool resolves from context → pluggable backend → default. The tool-server runs as a **separate uvicorn target** (`api.tool_server_app:app`) — a loopback sidecar inside each sandbox Pod, with a `watchfiles` watcher hot-reloading on file change (`tool_server_app.py:41-57`). It opens the DB pool through the proxy's core listener and **never owns migrations** (`:76-94`).

### Control Plane: Session Lifecycle as an Intent-Reconciler (KNOWN — migration `008_agent_runtime_control_plane.sql`, `runtime_control.py`)

The session key is `thread_key` (e.g. `slack:<team>:<channel>:<ts>`). The control plane is **stateless FastAPI over Postgres**; there is no in-memory session map. State lives in:
- `agent_runtime_assignments(thread_key, assignment_generation BIGINT, …, PK(thread_key, generation))` — the **session→sandbox map is a generation counter**: each (re)spawn bumps `assignment_generation`, so a session's "current sandbox" is the max-generation active assignment. This is the durable session↔sandbox binding.
- **Intent tables** drive a reconciler instead of direct calls: `agent_spawn_requests`, `agent_release_requests`, `agent_message_requests`, `agent_execution_requests(status CHECK IN ('queued','running','cancel_requested','retry_wait','completed','failed_permanent','cancelled',…))`. A request row is an *intent*; a background reconciler converges Kubernetes to match. This is why the control plane is restart-safe: a crashed API replica leaves the intent rows; another replica reconciles them. Deadline columns (`silence_deadline_at`, `hard_deadline_at`) drive timeout enforcement via a partial index over non-terminal statuses.

### Workflow Engine: Postgres Checkpoint/Replay (KNOWN — `workflow_engine.py`, migration `013_workflow_engine.sql`)

Explicitly "inspired by Cloudflare Workflows and earendil-works/absurd" (`workflow_engine.py:2`). **The handler function IS the workflow**; steps are runtime-discovered via `ctx.step(name, fn)`. The seam (mirrors AX's record-don't-replay but at the *step* granularity, and unlike AX it *does* skip completed steps):

`WorkflowContext.step(name, fn)` (`workflow_engine.py:338-435`):
1. Resolve a checkpoint name, auto-deduplicating loop iterations (`name`, `name#2`, … — `_resolve_name`, `:266-270`).
2. **If a checkpoint exists for that name → return the cached result instantly, do NOT re-run `fn`** (`:360-370`). This is resume-from-step.
3. Else run `fn` (with optional `RetryPolicy{limit, delay, backoff:fixed|exponential, max_delay}` and per-step `timeout`), then `_persist_checkpoint`.

`_persist_checkpoint` (`:272-326`) is the part to copy verbatim — checkpoint write + lease extension in one transaction with **fencing**: `SELECT status, worker_id FROM workflow_runs WHERE run_id=$1 FOR UPDATE`; if the run is `cancelled` or `worker_id != self._worker_id`, raise `CancelledWorkflow` (a stale worker that lost its lease cannot write a checkpoint). Then `INSERT … ON CONFLICT (run_id, checkpoint_name) DO UPDATE` and bump `worker_lease_expires_at = NOW() + lease_s`.

Schema (`013_workflow_engine.sql`, KNOWN):
- `workflow_runs(run_id PK, workflow_name, workflow_version, request_hash, parent_run_id, root_run_id, thread_key, status CHECK IN ('queued','running','sleeping','waiting','completed','failed','cancelled'), input_json JSONB, output_json JSONB, available_at, worker_id, worker_lease_expires_at, …)`. Claim index on `(status, available_at, worker_lease_expires_at)`; a unique partial index on `(workflow_name, trigger_key)` gives idempotent triggering.
- `workflow_checkpoints(run_id FK, checkpoint_name, step_kind, state JSONB, execution_id, child_run_id, PK(run_id, checkpoint_name))`. A **unique partial index on `execution_id`** enforces one checkpoint per agent execution (exactly-once agent turns). `step_kind` ∈ `agent_turn|tool_call|sleep|event|event_wait|child_workflow_start|child_workflow_result|slack_post|…`.
- `workflow_events(event_type, correlation_id, payload, PK(event_type, correlation_id))` — the external-signal inbox for `wait_for_event`.

Suspension is exception-driven: `ctx.sleep` / `wait_for_event` / `wait_for_workflow` persist a checkpoint (a wake time, or a `{_waiting:true, deadline}` marker) then raise `SuspendWorkflow(status='sleeping'|'waiting', available_at)`. The worker catches it, sets the run's `status`+`available_at`, and releases. A reconciler (`WORKFLOW_RECONCILE_INTERVAL_S=0.5`, `WORKFLOW_WORKER_CONCURRENCY=2`, `WORKFLOW_WORKER_LEASE_S=30`) re-claims due runs by lease; `_requeue_expired_running_runs` flips lease-expired `running` rows back to `queued` (crash recovery). A lease heartbeat refreshes at `lease_s/3` while a step runs. **`ctx.call_tool`/`ctx.agent_turn` are checkpointed steps** — so a tool call or a whole agent turn executes exactly once across replays (`:865-909`). An agent turn dispatches an `agent_execution_request`, then *suspends* (`status='waiting'`) until `notify_execution_terminal` wakes it — the durable workflow and the per-thread sandbox execution are decoupled via the event table.

### Per-Thread Kubernetes NetworkPolicy (KNOWN — `sandbox/kubernetes.py:1088-1208`)

Each sandbox gets **two programmatically-created NetworkPolicies**, torn down on release (`_delete_network_policy`, `:877-900`), keyed by label `centaur.ai/sandbox-id`:
1. **Sandbox egress policy** (`policyTypes:[Egress]`, selects the agent Pod by `centaur.ai/managed=true` + `centaur.ai/sandbox-id`): egress allowed **only** to (a) the API Pod on TCP 8000, and (b) its *own* per-sandbox iron-proxy Pod (matched by `_PROXY_LABEL` + same `sandbox-id`) on the proxy port + each tool's `pg_listen_port` + the core PG port. **No direct internet, no other sandbox, no other proxy.**
2. **Proxy policy** (`policyTypes:[Ingress,Egress]`, selects the per-sandbox proxy Pod): ingress only from its own sandbox; egress to API:8000, the internet on :443, Postgres on :5432, and optionally the 1Password Connect Pod.

So the blast radius of a compromised agent is: it can reach the API and its own proxy — nothing else — and every outbound call is credential-injected + header-stripped at that proxy. Each thread gets its own proxy Pod, so credentials are never shared across threads. This is default-deny per-thread isolation built from stock k8s primitives, no service mesh.

### Constants + End-to-End Trace (KNOWN)

| Constant | Value | Source |
|---|---|---|
| iron-proxy TLS mode | `mitm` (own CA) | `iron-proxy.yaml` |
| iron-proxy ports | DNS :53, tunnel :8080, management :9092 | `iron-proxy.yaml` |
| Secret TTL (env/1Password) | 10 m default | `proxy_config.py:77` |
| Token-broker proxy cache TTL | 1 m (< broker lifetime) | `proxy_config.py:88` |
| PG listener base port | 5432, sequential by name | `proxy_config.py:56,130-138` |
| Tool dir layout | `tools/<cat>/<name>/{pyproject.toml,client.py}` | `tool_manager.py:1703-1812` |
| Tool factory | `_client()` → public methods = tool methods | `tool_manager.py:2161-2188` |
| Reserved tool methods | `close/connect/disconnect/shutdown`, `_*` | `tool_manager.py:1369` |
| Forbidden tool args | `output_path/save_path/dest_path/…` | `tool_manager.py:1381-1390` |
| Workflow reconcile interval | 0.5 s | `workflow_engine.py:161` |
| Workflow worker concurrency | 2 | `workflow_engine.py:164` |
| Workflow lease | 30 s (heartbeat at lease/3) | `workflow_engine.py:167,1108` |
| Checkpoint exactly-once | unique partial index on `execution_id` | `013_workflow_engine.sql:82-84` |
| Session→sandbox binding | `(thread_key, assignment_generation)` | `008_…sql:3-21` |

**End-to-end trace** (Slack message → durable agent turn, KNOWN paths): (1) Slackbot posts to API; control plane finds/creates the `thread_key`'s active `assignment_generation`, writes an `agent_spawn_request` intent; the reconciler converges k8s — sandbox Pod + per-sandbox iron-proxy Pod + the two NetworkPolicies. (2) A workflow run is created (`workflow_runs`, status `queued`); the worker claims it by lease. (3) The handler calls `ctx.agent_turn(prompt)` → a checkpointed `agent_turn` step → `enqueue_execution` writes an `agent_execution_request` and the workflow *suspends* (`status='waiting'`). (4) The sandbox harness runs the coding agent; its tools call the loopback tool-server (`/tools/{tool}/{method}`), whose HTTPS egress goes through the per-sandbox iron-proxy, which injects the host-scoped credential. (5) On terminal, `notify_execution_terminal` wakes the workflow; `ctx.step` returns the cached dispatch and the handler reads `result_text`, posts to Slack via a checkpointed `post_to_slack` step. A crash anywhere leaves intent rows + checkpoints; another replica reconciles and the workflow replays, skipping completed steps.

### For Verso

- **Egress credential proxy, not in-process secret injection.** The single most transferable idea: agents (and tools) hold *placeholders*, a sidecar proxy injects/replaces/signs the real credential per destination host at the TLS boundary, with values resolved from env/1Password/a token broker *at request time*. Verso's auth-gated `@tool` should target this: the tool author declares `HttpSecret(host=…, inject_header=…)` (or replace/oauth/hmac/aws variants); Verso renders a proxy config; the credential never enters the agent process or the LLM context. For a non-k8s Verso, the proxy can be a localhost mitmproxy/Go binary with the same per-host `rules` table.
- **Host-scoped credentials are the security primitive.** `rules:[{host:H}]` means SLACK_BOT_TOKEN is offered only to `*.slack.com`, GITHUB_TOKEN only to `github.com`. A prompt-injected agent that tries to POST your GitHub token to `evil.com` gets no token (and the header is stripped by the allowlist). Verso's tool-secret declaration must be host-scoped by construction, never a flat env bag.
- **Tools = directory + `pyproject.toml` + factory; methods auto-become REST.** No decorator, no registration call. Verso's `@tool` can be even lighter: a class whose public methods auto-expose, with `inspect.signature` → JSON schema for the LLM and a structured arg-validation error (`did_you_mean` via `difflib`) before invocation. The "forbidden path args → return attachments instead" rule is a good default for any sandboxed tool runtime.
- **Stable routes + live dispatch = safe hot-reload.** Register routes once; resolve the tool from a dict at request time; a `watchfiles` watcher reloads the registry. Verso's tool hot-reload should follow this so adding a tool never requires restarting the server or rebuilding the router.
- **Checkpoint/replay at step granularity with lease-fencing.** This is the Verso `durable=True` reference implementation in Python+Postgres: `ctx.step(name, fn)` returns the cached result on replay, else runs `fn` and persists `(run_id, checkpoint_name)→state JSONB`; the persist transaction *fences on `worker_id` under `FOR UPDATE`* so a zombie worker can't double-write. Wrap tool calls and agent turns as steps for exactly-once. Unlike Temporal, no determinism sandbox — it's just Python that re-executes top-to-bottom, skipping checkpointed steps. (Cross-ref `durable-execution.md`: this is the same family as DBOS/Inngest step-memoization; Centaur's `execution_id` unique partial index is its exactly-once-agent-turn enforcement.)
- **Control plane = stateless services + Postgres intent tables + reconciler.** No in-memory session map; `thread_key` + `assignment_generation` *is* the session→sandbox binding, in Postgres. Spawn/release/message/execute are *intent rows* a reconciler converges. Verso's hosted control plane should be restart-safe the same way: a crashed replica leaves intents; any replica reconciles. Deadlines (`silence_deadline_at`/`hard_deadline_at`) as columns + a partial index over non-terminal statuses is a clean timeout-enforcement pattern.
- **Per-tenant network isolation from stock k8s NetworkPolicy.** Two policies per sandbox (sandbox→{API, own-proxy} only; proxy→internet), labeled by `sandbox-id`, created/destroyed with the sandbox. No service mesh required. If Verso runs untrusted agent code, this is the egress-control floor: default-deny, allow only the API and the sandbox's own credential proxy.
- **Postgres egress is proxied too.** Don't give a sandbox a DB connection string — give it a proxy listener that holds the real DSN. Verso's sandboxed tools that touch a DB should reach it through the same credential proxy on a per-tool listener port, never a direct connection.

---

## Salus (YC W26)

> **Closed product.** `pip install salus` resolves no package on public PyPI (`pypi.org/pypi/salus/json` → `{"message":"Not Found"}` on 2026-06-05), so the SDK is gated/private and the in-environment behavioral probe could not be run. Everything below is INFERRED from `usesalus.ai` + the YC page, with the live proxy URL/header shape KNOWN from the product page. Labeled accordingly; no fabricated schema.

### What It Is

Salus is a **pre-execution validation layer for agent tool calls, packaged as an independently deployable proxy.** It sits between an agent and the tools it already calls, and on every proposed tool call it validates the call against versioned policies + a per-run **evidence cache** *before* the call executes — blocking, clarifying, repairing, rewriting, or escalating. The pitch: "wraps around your agent and checks its actions at runtime, blocking incorrect ones and providing immediate feedback to guide retries." It is the first product to isolate the **pre-action validation hook** as its own primitive rather than a framework guardrail module — which is exactly the question for Verso's `@tool` executor: should the tool path have a pre-call hook wired to a policy validator grounded on run state?

### Integration Model — Proxy by URL Swap (KNOWN — product page)

The headline integration is **not** the SDK-wrap-the-function model the target brief hypothesized; it's an HTTP proxy by base-URL swap: "One endpoint change. Runtime safety, on." / "Change the URL. The agent does not know the difference." Concretely (KNOWN, product page): point the tool's base URL at `app.usesalus.ai/v1/proxy/[tool-name]` and add an `X-Salus-Proxy-Secret` header. The agent code is unchanged; the proxy intercepts the call, validates, and either forwards to the real upstream or returns a block/repair response. (The `pip install + a few lines of code` path the YC page advertises is INFERRED to be a thin client that configures this proxy + carries framework adapters for OpenAI/Anthropic/Gemini/LangChain/LangGraph/CrewAI/LlamaIndex/Retell/Vapi/MCP/REST — the same "swap the transport, keep the agent" pattern as iron-proxy and the vLLM multi-dialect adapter in `infra-serving.md`, but for *validation* rather than credential injection.)

So Salus and Centaur's iron-proxy are the **same architectural shape** — a policy-aware proxy in front of every tool the agent calls — solving orthogonal problems: iron-proxy injects credentials at egress; Salus validates intent before egress. A complete Verso tool boundary is plausibly *both* proxies chained: validate (Salus-shaped) → inject credential (iron-proxy-shaped) → forward.

### The Validation Pipeline (INFERRED — product + YC pages)

Per proposed tool call, Salus is described as: it "extracts attempted actions, claims, handoffs" and "builds a ledger," then validates the action against policy + the evidence cache, and "clarifies, repairs, rewrites, or escalates." The four outcome verbs are the key taxonomy (richer than a binary allow/deny):
- **clarify** — ask the agent for missing info before allowing;
- **repair / rewrite** — Salus modifies the tool call to a compliant form rather than rejecting it (who performs the rewrite — a model vs. rule — is not disclosed; INFERRED to be an LLM given the "structured feedback" framing);
- **block** — reject and return structured feedback the agent can self-correct from;
- **escalate** — route to a human (HITL), e.g. the sample trace "multiple John records found; caller identity has not been verified."

**Evidence cache** (INFERRED, YC page, quoted): "an evidence cache for each run that every proposed action is validated against," containing "all outputs from prior tool calls and the entire conversation history." Scope = **per run** (not per session or per thread — the run is the validation grounding unit). The insight worth stealing: this is the same run-scoped state a durable agent already maintains; Salus's contribution is recognizing that *the durable run log is also the natural grounding set for action validation* — you validate "is this action consistent with everything that's happened in this run?" against state you're keeping anyway.

**Policy format** (KNOWN-ish, YC page, quoted): "Write constraints in YAML, markdown, or plain English. Salus compiles them into runtime checks that are version-controlled, diffable, and shadow-testable." So policies are authored in three surfaces and *compiled* to runtime checks — natural-language policies imply an LLM-judge compilation step; the diffable/shadow-testable framing implies policies are first-class versioned artifacts you can dry-run against production traffic before enforcing. Additional built-in checks (INFERRED, YC): PII detection, budget/loop protection, idempotency, HITL escalation, content moderation.

**Numbers (KNOWN/INFERRED):** sample traces show **avg latency 28 ms** (KNOWN, product page — the validation round-trip budget); **58% of blocked actions recover and complete the task correctly** (INFERRED, YC page — the self-repair benchmark). Benchmarked on **τ²-bench and ODCV-Bench** (INFERRED, YC page). The 28 ms figure matters: a pre-execution hook on every tool call must be cheap, so the common-case validation is almost certainly *not* an LLM call — likely compiled deterministic checks first, LLM-judge only for NL policies / ambiguous cases.

### Reconstructed Validation Pipeline + Block-Response (DESIGNED — grounded in the KNOWN verbs/fields)

The exact block-response JSON is not published. Reconstructed from the four outcome verbs + "structured feedback to guide a retry" + the sample "Reason" field, this is the shape a Verso pre-call hook should emit (DESIGNED, the wire detail is mine, the verbs/fields are KNOWN):
```python
# DESIGNED — the per-call validator the proxy runs before forwarding
async def validate(tool, args, run_ctx):           # run_ctx = evidence cache
    evidence = run_ctx.prior_tool_outputs + run_ctx.conversation  # per-run scope
    for policy in compiled_policies(tool):         # YAML/md/NL → compiled checks
        verdict = policy.check(tool, args, evidence)
        if verdict.kind == "allow":   continue
        if verdict.kind == "rewrite": args = verdict.new_args; continue  # mutate
        return {                                    # block / clarify / escalate
            "outcome": verdict.kind,                # block|clarify|escalate
            "tool": tool, "blocked_args": args,
            "reason": verdict.reason,               # e.g. "caller identity not verified"
            "policy_id": policy.id, "policy_version": policy.version,
            "feedback": verdict.repair_hint,        # self-correctable instruction
            "evidence_refs": verdict.cited_outputs, # which prior outputs triggered it
        }
    return {"outcome": "allow"}
```
Key design properties the Salus framing implies: (a) `rewrite` mutates and continues, not returns — a near-miss is fixed in place; (b) the block carries `feedback` the agent re-prompts on (this is what makes 58% recover — opaque 403 → 0% recover); (c) `evidence_refs` cite *which* prior tool outputs grounded the verdict (the per-run evidence cache is the grounding set); (d) `policy_version` makes verdicts diffable/auditable. The compiled-policy fast path keeps the common case off the LLM (the 28 ms budget); NL policies compile to an LLM-judge invoked only when deterministic checks are inconclusive.

### For Verso

- **A pre-call validation hook is a first-class tool-executor primitive, not a framework add-on.** Verso's `@tool` executor should expose a `before_call(tool, args, run_state) → Allow | Clarify(msg) | Rewrite(new_args) | Block(feedback) | Escalate()` hook. The four-outcome taxonomy (vs. binary allow/deny) is the design to copy: a block that returns *structured, self-correctable feedback* is what makes the 58% recovery possible — an opaque HTTP 403 gives the agent nothing to retry on (cross-ref `infra-serving.md` error-contract: the agent client must parse structured errors, not status codes).
- **The run log IS the validation grounding set.** Verso's durable seam (the event log from the AX/Centaur sections) already holds every prior tool output + the conversation. Wire the pre-call validator to read that log: "is this action consistent with the run so far?" No separate evidence store needed — the durable log is the evidence cache. This collapses two subsystems (durability + validation) onto one state.
- **Validation as a proxy, chained with the credential proxy.** Verso's tool boundary can be two composed proxies: validate-then-inject. Both are URL-swap proxies invisible to the agent; together they give "the agent holds no secrets AND can't take a policy-violating action" with zero changes to tool code.
- **Policies compiled from NL → cheap runtime checks, LLM-judge only on the margin.** The 28 ms budget forces a tiered validator: deterministic compiled checks on the hot path, LLM-judge reserved for natural-language policies and ambiguous cases. Verso should not put an LLM call in front of *every* tool call; compile the policy and fall back to a judge. Make policies versioned, diffable artifacts that can be shadow-tested against recorded runs before they enforce.
- **`rewrite` is the highest-leverage outcome.** Blocking forces a retry round-trip; rewriting a near-miss tool call into a compliant one (clamp an over-budget amount, scope an over-broad query) keeps the agent moving. Verso's hook should allow the validator to return mutated args, not just allow/deny.

---

## Cloudflare Agents Week 2026 (Agent Memory + Project Think)

> **Closed/JS-native** (TypeScript on Workers; Verso is Python-only). Read for architecture, not code. All INFERRED from the four Cloudflare/InfoQ blog posts; method names KNOWN from the blogs' code samples. `[CORRECTION 2026-06-05]` the target brief's API names `env.AI.agent_memory.add()/.search()` are wrong — the real Agent Memory binding is `env.MEMORY.getProfile("…")` returning a profile with `ingest/remember/recall/list/forget`.

### Agent Memory — Dual-Pass Ingest + Five-Channel RRF Retrieval (INFERRED — `blog.cloudflare.com/introducing-agent-memory`)

A managed memory-as-network-primitive: extraction + retrieval behind one binding, backed by **Durable Object SQLite (raw messages + classified memories) + Vectorize (vectors) + Workers AI (models)**. The two halves:

**Dual-pass ingestion** (asynchronous — "background vectorization runs asynchronously" after the response returns):
1. **Full pass** — chunks messages at **~10K characters with two-message overlap**, processing **up to four chunks concurrently**. Extracts and classifies into four memory types: **Facts** (keyed atomic knowledge), **Events** (time-specific), **Instructions** (procedures), **Tasks** (ephemeral, *excluded from the vector index*).
2. **Detail pass** — for longer conversations (**9+ messages**), overlapping windows that specifically extract concrete values (names, prices, version numbers). Merged with the full pass.
- Extractor model: **Llama 4 Scout (17B, 16-expert MoE)** for the structured classification. Message ID = SHA-256 truncated to 128 bits (dedup key).

**Five-channel parallel retrieval, fused by RRF** (the part most worth stealing): one `recall(query)` fans out to five retrievers in parallel —
1. **Full-text search** (Porter stemming — keyword precision);
2. **Exact fact-key lookup** (query maps directly to a known topic key);
3. **Raw message full-text search** (search stored conversation directly);
4. **Direct vector search** (embed the query, find semantically similar memories);
5. **HyDE vector search** (embed what the *answer* would look like, find memories similar to that hypothetical answer).
Results merge via **Reciprocal Rank Fusion**: fact-key matches get the highest weight; full-text, HyDE, and direct vectors are weighted by signal strength; ties broken by recency (newer first). (No RRF `k` constant is disclosed; KNOWN-absent.)

API (KNOWN from samples): `const profile = env.MEMORY.getProfile("my-project")` then `profile.ingest([...])` / `profile.remember({...})` / `profile.recall("query")` / `profile.list()` / `profile.forget()`. Also reachable via REST for non-Workers agents.

**Agent Memory constants (KNOWN — blog):**

| Constant | Value |
|---|---|
| Chunk size (full pass) | ~10K chars, two-message overlap |
| Concurrency | up to 4 chunks |
| Detail pass trigger | conversations of 9+ messages |
| Extractor model | Llama 4 Scout (17B, 16-expert MoE) |
| Message-ID / dedup | SHA-256 truncated to 128 bits |
| Memory types | Facts / Events / Instructions / Tasks (Tasks not vector-indexed) |
| Vectorization | async, post-response (off critical path) |
| RRF channel weights | fact-key highest; full-text/HyDE/direct by signal; recency tiebreak |
| RRF `k` constant | not disclosed |
| Embedding dims / top-k / TTL | not disclosed |

RRF fusion, reconstructed (DESIGNED — the standard RRF the blog names but doesn't parameterize): each of the 5 channels returns a ranked list; score a memory `m` as `Σ_channel  w_channel / (k + rank_channel(m))` with `w_fact-key` highest, then sum across channels, recency as tiebreak. The novel ingredient vs. textbook RRF is **HyDE as a first-class channel** (embed a hypothetical answer, not the query) and **exact fact-key lookup** as a non-vector channel that dominates when the query maps to a known topic key.

### Project Think — Fibers, Relational Memory Tree, Actor Kernel (INFERRED — `blog.cloudflare.com/project-think`, InfoQ)

The next Agents SDK edition; an **actor-based durable kernel** where each agent is "an addressable entity with its own SQLite database [that] consumes zero compute when hibernated," waking on HTTP/WebSocket/alarm/email with state auto-loaded — per-agent identity + routing are platform-native, **no external load balancer**.

- **Fibers — checkpoint-the-instruction-pointer, not replay-from-snapshot.** "A fiber is a durable function invocation: registered in SQLite *before execution begins*, checkpointable at any point via `stash()`, and recoverable on restart via `onFiberRecovered`." The agent calls `ctx.stash({ findings, step: i, topic })` at arbitrary points; on restart `onFiberRecovered` receives the stash and the fiber **resumes from the stashed checkpoint** rather than re-running the function. `keepAlive()` holds the agent live during a fiber, or it delegates long ops to callbacks and hibernates. **This is a third durability model distinct from both AX (record outputs, re-prompt) and Centaur/Temporal (re-execute, skip checkpointed steps): Think saves the *instruction pointer + local state* and resumes mid-function** — closest to continuation-passing / coroutine snapshotting.
- **Session API = relational memory tree.** "Conversations are stored as trees, where each message has a `parent_id`. This enables forking (explore an alternative without losing the original path)." Parallel reasoning paths branch non-destructively — the same checkpoint-as-branch idea as AX `fork`, but at message granularity inside one agent rather than conversation-copy.
- **Context Blocks — model-managed, editable system-prompt sections that survive hibernation.** `.withContext("memory", { description: "Important facts…", maxTokens: 2000 })`; the model sees a budget meter (`"MEMORY (…) [42%, 462/1100 tokens]"`) and calls `set_context` to update its own persistent memory. Self-editing system prompt as durable state.
- **Self-authored code in Dynamic Workers.** LLM-generated tools run in "a fresh V8 isolate spun up at runtime, in milliseconds, with a few megabytes of memory," with declarative capability grants (network allowlists, workspace access) — no ambient authority. `ExtensionManager` bundles a TS extension (npm deps via `@cloudflare/worker-bundler`), loads it into a Dynamic Worker, registers the tools, and **persists the extension in DO storage so it survives hibernation** — the agent writes and installs its own tools without a platform restart.

### For Verso

- **One `recall(query)` → five retrievers → RRF is the memory-retrieval pattern to copy.** Verso's memory layer should not pick one retrieval mode; run keyword + exact-key + raw + dense + HyDE in parallel and fuse by RRF with per-channel weights (exact-key highest), recency as tiebreak. HyDE-as-a-fifth-channel (embed the hypothetical answer, not the query) is the cheap quality win most systems skip. (Cross-ref `infra-vector-memory.md` / `memory-systems.md` — this is the production "hybrid retrieval behind one API" reference.)
- **Dual-pass async ingest decouples memory writes from the response path.** Extract+classify+embed runs *after* the turn returns, not inline. Verso's memory ingestion must be a background job keyed on a dedup hash, never blocking time-to-first-token. The Facts/Events/Instructions/Tasks taxonomy (with Tasks excluded from the vector index) is a sane default memory schema.
- **Three durability models to choose between, now enumerated.** AX = record outputs + re-prompt from history (re-run nothing completed). Centaur/Temporal = re-execute top-to-bottom, skip checkpointed steps. Think/Fibers = stash the instruction pointer + locals, resume mid-function. For Verso's `durable=True`: the AX/Centaur step-memoization model is the pragmatic Python choice (no continuation capture needed); Fibers' `ctx.stash()` is the right *ergonomics* to expose — let the agent author checkpoint a dict at any point and resume from it, even if the underlying mechanism is step-replay rather than true continuation snapshotting.
- **Agent = addressable actor with its own store, zero compute when hibernated, wake-on-event.** Same lesson as AX's SubstrATE actor: per-agent state isolation needs no coordination server — the agent id routes to a hibernatable instance with a co-located store, woken by events. Verso's hosted tier should make each agent an addressable, hibernatable unit, not a row in a shared process.
- **Model-managed Context Blocks = self-editing durable system prompt.** Giving the model a token-budgeted, persistent prompt section it can `set_context`-update is a clean alternative to a separate memory tool — the memory write *is* a prompt edit. Verso could expose a `ctx.memory` block with a visible budget meter the model maintains itself.

---

## Cross-System Synthesis → Verso

Five independent 2026 frontier runtimes, read together, converge on a small set of decisions for Verso's core seam. Where five systems agree, it's not a guess — it's the design.

### The seam: append-only event log + stateless loop + lazy side-effect env

| System | Durable log | Loop state | Side-effect env | Resume primitive |
|---|---|---|---|---|
| Anthropic Managed Agents | Session (`emitEvent`/`getEvents`) | Harness — **none survives crash** | Sandbox, lazy on 1st tool call | `wake(sessionId)` → replay |
| Google AX | `ConversationEvent`+`ExecutionEvent` (SQLite/protojson) | Controller single-writer; actor view = handed history | SubstrATE actor, suspend 50 ms post-turn | `Exec{last_seq}` + pending-exec replay |
| Centaur | Postgres `workflow_runs`+`workflow_checkpoints` | stateless FastAPI; intent tables | per-thread k8s sandbox Pod | re-claim by lease, replay-skip steps |
| CF Project Think | co-located SQLite + Fibers | actor; `ctx.stash()` checkpoints | Dynamic Worker V8 isolate | `onFiberRecovered` mid-function |
| Salus | (consumes the host's run state) | n/a (validation proxy) | n/a | n/a |

**Three durability models** (pick one for Verso `durable=True`): (a) **record-outputs + re-prompt** (AX — re-run nothing completed, re-derive messages from log); (b) **re-execute + skip-checkpointed-steps** (Centaur/Temporal/DBOS — `ctx.step` memoization, lease-fenced); (c) **stash-instruction-pointer + resume-mid-function** (Fibers — continuation snapshot). The pragmatic Python choice is (b) for the mechanism with (c)'s `ctx.stash()` ergonomics on top. All three reject Temporal's determinism sandbox in favor of "the log is truth."

### The tool boundary: chained proxies, agent holds no secret, validate before egress

Three of the five put a **proxy in front of every tool the agent calls**, agent code unchanged (URL swap), agent holding only opaque session handles:
- **Anthropic MCP proxy**: session token → vault → inject credential; "harness never aware of credentials."
- **Centaur iron-proxy**: host-scoped credential inject/replace/sign at MITM-TLS egress, header allowlist, even Postgres proxied.
- **Salus**: pre-execution validation (allow/clarify/rewrite/block/escalate) grounded on the per-run evidence cache.

Verso's complete tool boundary = **validate (Salus-shaped) → resolve session-token→credential (Anthropic-shaped) → inject per-host (Centaur-shaped) → forward**, all invisible to the agent. Network isolation underneath (Centaur's per-thread NetworkPolicy: sandbox → {API, own-proxy} only) is the default-deny floor for untrusted agent code.

### HITL, fork, and memory are data, not control flow

- **HITL = a suspend point in the log** (AX: "log ends on an unanswered confirmation"; Centaur: workflow `wait_for_event`; Anthropic: a tool-call awaiting result). No callback registry — the resume is the next event carrying the answer.
- **Fork = seq-bounded log copy** (AX `fork`, CF `parent_id` tree) — checkpoint-as-branch for eval/what-if needs no snapshot blobs, just replay `[0..seq]` into a new id.
- **Memory = either a mounted versioned FS** (Anthropic, per the brief) **or a managed extract→embed→5-channel-RRF service** (CF) — both keep the agent from authoring embeddings; Verso's hosted tier should offer the RRF-behind-one-API model (`recall(query)` → keyword+exact-key+raw+dense+HyDE → RRF), async-ingested off the critical path.

### Latency discipline

Anthropic's p50 TTFT −60% / p95 −90% from decoupling is the published target. The mechanism is universal: keep container/sandbox provision off the median critical path (lazy), keep the loop stateless so workers autoscale, and put the cheap validation/credential work in proxies budgeted at ~28 ms (Salus), not LLM calls. Verso's managed tier should measure TTFT the same way (accept-work → first token) and treat lazy-sandbox as the single highest-ROI decision.
