# TypeScript Framework Peers — Verso Research Note
## Cluster: fw-ts-peers
### Systems: Inngest AgentKit · Cloudflare Agents SDK · OpenAI Agents JS · LangGraph.js · Convex Agent · VoltAgent · ElizaOS v2 · Motia
*Sources: cloned `--depth=1` 2026-06-05 into `/tmp/verso-re-tsfw/`: inngest/agent-kit, cloudflare/agents, openai/openai-agents-js, langchain-ai/langgraphjs, get-convex/agent, VoltAgent/voltagent, elizaOS/eliza, MotiaDev/motia. Cross-refs sibling `03_teardowns/fw-*.md` (notably `fw-langchain-langgraph.md` for the Python LangGraph peer) and the source teardowns `researchfms/teardowns/MASTRA.md` + `VERCEL_AI_SDK.md` (Mastra, Vercel AI SDK already covered there; referenced not re-derived).*

> **Why this note exists.** Verso is a Python async ReAct agent framework. Every target here implements a specific mechanism Verso must form a position against: deterministic-vs-LLM routing as a slider (AgentKit), durability as a *deployment target* (CF Durable Objects), handoffs as a first-class primitive (OpenAI Agents JS), typed-state reducer-merge (LangGraph Annotations), reactive-backend-for-agents (Convex), supervisor/subagent + suspendable workflow (VoltAgent), plugin contract for "pluggable everything" (ElizaOS), and event-routing-as-the-only-primitive (Motia). Labels: **KNOWN** = read from source at `file:line`; **INFERRED** = derived from code + docs; **DESIGNED** = my engineering read of the implication for Verso.

---

## Inngest AgentKit

### What It Is

A multi-agent network framework built on Inngest's durable function runtime. Four primitives: **Agent** (instructions + tools + lifecycle hooks), **Network** (holds agents + shared State + a Router), **Router** (chooses next agent — code function OR a routing-Agent that uses an LLM), and **State** (typed `data` object + linear message/result history). The whole orchestration is plain code — there is no graph DSL. When run inside an Inngest function, every LLM call and every ID generation is wrapped in an Inngest step, so the network loop becomes **durably replayable for free**: this is the single most Verso-relevant property.

### The Network Run Loop — Router → Agent → State (KNOWN)

The entire loop lives in `NetworkRun.execute()` (`network.ts:446-791`). Reimplementable sequence:

```
run(input, overrides)                                    # network.ts:146
  → state = overrides.state ?? this.state.clone()        # clone so a network is reusable
  → new NetworkRun(this, state).execute(input)           # network.ts:177

execute(input):                                          # network.ts:446
  1. networkRunId = step.run("generate-network-id", randomUUID)   # :455 — deterministic ID via step
  2. initializeThread()  → createThread() if no threadId          # :480 history hook
  3. history.appendUserMessage() (if configured)                  # :524 persist user msg up front
  4. if hadClientThreadId: loadThreadFromStorage() → history.get() # :536
  5. available = availableAgents()  (filters by agent.lifecycles.enabled)  # :570
  6. next = getNextAgents(input, router)                          # :583  ROUTER CALL #1
       if !next.length: return                                    # empty → done immediately
  7. for agent in next: this.schedule(agent.name)  # _stack.push  # :593
  8. WHILE _stack.length>0 AND (maxIter==0 || _counter<maxIter):  # :597  THE LOOP
       agentName = _stack.shift()                                 # :607  FIFO pop
       agent     = _agents.get(agentName)                         # :611
       if !agent: emit run.completed; return                      # :612 unknown name == stop
       agentRunId/agentMessageId = step.run("generate-agent-ids-${_counter}", ...) # :644 deterministic
       call = await agent.run(input, {network:this, maxIter:0, step:wrappedStep})  # :684 RUN AGENT (maxIter 0!)
       call.id = agentMessageId
       _counter += 1                                              # :708
       this.state.appendResult(call)                              # :711  STATE UPDATE
       next = getNextAgents(input, router)                        # :721  ROUTER CALL #N (re-route every iter)
       for a in next: this.schedule(a.name)                       # :726  push next agent(s)
  9. saveThreadToStorage() → history.appendResults(newResults)    # :734 persist only NEW results
```

**The defining shape: Router runs *between every agent*, not once.** Step 6 routes, step 8 pops one agent and runs it, step 8's tail (`:721`) routes again. Routing and execution strictly alternate. `_stack` is a `string[]` of agent names (`network.ts:67`); `schedule()` is just `_stack.push(name)` (`:442`). The loop terminates when the router returns empty/undefined OR `_counter` hits `maxIter` (`maxIter:0` = unbounded, `network.ts:64,599`).

**Subtle but load-bearing (KNOWN, `network.ts:637,686`):** agents inside a network are always invoked with `maxIter:0`. Comment at `:636`: *"We force Agent to emit structured output in case of the use of tools by setting maxIter to 0."* So an in-network agent does **exactly one inference + its tool calls, then returns to the router** — the network loop, not the agent loop, drives multi-step work. A *standalone* agent (`agent.run()` directly) uses its own `do/while` up to its `maxIter`.

### Router — Code-based and LLM-based Coexist on One Type (KNOWN)

`Network.Router<T> = RoutingAgent<T> | Router.FnRouter<T>` (`network.ts:360`). The two coexist because `getNextAgents()` (`network.ts:793`) branches on `instanceof RoutingAgent`:

- **Code router (`FnRouter`)** — `(args: Args<T>) => MaybePromise<RoutingAgent | Agent | Agent[] | undefined>` (`network.ts:373`). `Args` (`:377`) is the deterministic-routing surface: `{ input, userMessage?, network: NetworkRun<T>, stack: Agent[], callCount, lastResult? }`. `callCount === network.state.results.length`; `lastResult === state.results.at(-1)`. A code router reads `network.state.data` + `lastResult` and returns the next agent — **zero LLM calls**. Returning `undefined` ends the run.
- **Agent router (`RoutingAgent`)** — runs an LLM to pick the next agent. `getNextAgentsViaRoutingAgent()` (`network.ts:871`): `result = await routingAgent.run(input,...)` then `agentNames = routingAgent.lifecycles.onRoute({result, agent, network})` (`:880`), then maps names → agents.
- **Hybrid is native:** a code `FnRouter` may *return* a `RoutingAgent` (`network.ts:851`), so code decides "now use the LLM router"; and a `RoutingAgent` invoked via `.route` runs the agent first then calls onRoute. This is the **deterministic↔LLM routing slider** the Verso brief asked for, expressed as a union type + an `instanceof` branch.

### `onRoute` Hook — How the LLM Router Picks Agents (KNOWN)

`onRoute: (RouterArgs) => string[] | undefined` (`agent.ts:1163`). The default routing agent's `onRoute` (`network.ts:198-222`) inspects the LLM's tool calls:

```ts
const tool = result.toolCalls[0];
if (!tool) return;
if (tool.tool.name === "done")  return undefined;          // exit the loop
if (tool.tool.name === "select_agent") return [tool.content.data];  // route to named agent
```

The default routing agent (`network.ts:190-323`) ships two tools — `select_agent({name, reason?})` and `done({summary?})` — with `tool_choice:"any"` (forces a tool call). Its system prompt is generated at call time from the live agent registry: `<agents>` block enumerates every available agent's `name`/`description`/`JSON.stringify(tools)` (`:289-304`). `select_agent.handler` validates the name against `network.agents` and throws on unknown (`:246`). So the LLM-router decision is: *emit a `select_agent` or `done` tool call*; `onRoute` translates that into the next-agent list or a stop signal.

### State — Typed `data` Proxy + KV + Linear History Hybrid (KNOWN)

`State<T extends StateData>` (`state.ts:36`). Three storage layers:

1. **`data: T`** — a `Proxy` over `_data` (`state.ts:70-79`); the proxy `set` trap is the documented seam for middleware hooks ("record state before/after setting"). This is the **typed** routing surface.
2. **`kv` (deprecated, `state.ts:84-102,179`)** — `Map<string,any>` with `set/get/delete/has/all`. Seeded from `Object.entries(_data)`. Comment: *"KV is deprecated and should be fully typed."* — the framework is migrating from untyped KV to typed `data`.
3. **History — two arrays:** `_results: AgentResult[]` (every inference result, the agentic call log) and `_messages: Message[]` (a linear seed of prior messages). `formatHistory(formatter?)` (`state.ts:145`) reconstructs the conversation = `_messages.concat(_results.map(formatter).flat())`; default formatter = `result.output.concat(result.toolCalls)` (`:221`). `appendResult()` pushes to `_results` (`:161`); `getResultsFrom(startIndex)` slices new-only results for persistence (`:125`). `clone()` deep-copies all three (`:168`) so a `Network` template can spawn many runs.

**How tools write to state (KNOWN, the key seam):** a tool handler's signature is `(input, opts: {agent, network: NetworkRun, step?}) => MaybePromise<TOutput>` (`tool.ts:33,65-68,74-78`). There is **no dedicated state-write API** — a tool mutates `opts.network.state.data.<field> = value` directly (the Proxy intercepts it), and its *return value* becomes the `tool_result` message appended to history. `invokeTools()` (`agent.ts:635`) loops the LLM's `tool_call` messages, looks up `this.tools.get(tool.name)` (throws on missing, `:657`), runs `found.handler(tool.input, {agent, network, step})` (`:734`), wraps to `{data}` or `{error: serializeError(err)}` (`:742,750`). Undefined return → `"${tool.name} successfully executed"` (`:745`). **Verso lesson: state is the side-channel, tool return is the LLM-channel — a tool does both at once.**

### History Persistence — Four Hooks + Client-Authoritative Mode (KNOWN, `history.ts`)

State persistence is delegated to a `HistoryConfig<T>` (`history.ts:35-97`) with four hooks, all step-wrapped when durable: `createThread(ctx) → {threadId}`, `get(ctx) → AgentResult[]`, `appendUserMessage(ctx & {userMessage})`, `appendResults(ctx & {newResults})`. The lifecycle functions wire them into the run loop:
- **`initializeThread`** (`history.ts:198-243`): if `state.threadId` exists + `createThread` defined → ensure it exists (`:208`); if no `threadId` → call `createThread()` for a new one, else fall back to `crypto.randomUUID()` (`:230`).
- **`loadThreadFromStorage`** (`:271-296`): loads `history.get()` results **only if** `threadId` exists AND `state.results.length === 0 && state.messages.length === 0` (`:275-280`) — i.e. only when the client did NOT pre-supply history. `state.setResults(historyResults)`.
- **`saveThreadToStorage`** (`:322-339`): persists **only new results** via `state.getResultsFrom(initialResultCount)` (`:329`) → `history.appendResults({newResults, ...})`, so loaded history is never re-saved.

**The client-authoritative mode (a real design decision, `network.ts:466-543`):** if the client passes `messages`/`results` into `createState`, `history.get()` is *skipped* — the client owns conversation state and sends it each request; `get()` becomes a fallback only for new threads/recovery. `appendUserMessage` persists the user's message *at the start* of the run (before any agent runs, `network.ts:524`) "for resilience" — so a crashed run still has the user intent recorded, enabling regenerate. This split (client-authoritative vs server-authoritative history, chosen per-request by whether the client supplies state) is a clean pattern for Verso's memory layer.

### Deterministic Replay Gate (KNOWN — the durability seam)

AgentKit's durability is "free" because of one trick: **detect the Inngest async context, and if present, route all non-determinism through steps.** `getStepTools()` (`util.ts:34-46`) reads `getAsyncCtx()?.ctx?.step` from `inngest/experimental`. Returns `undefined` outside an Inngest run.

- **LLM call** (`model.ts:50-94`): `if (step) result = await step.ai.infer(stepID, {model, body})` — durable, memoized on replay; `else` raw `fetch()`. The `stepID` passed to `p.infer` is **the agent name** (`agent.ts:450-455`, first arg `this.name`), giving a stable step key per agent per turn.
- **Every random ID** is wrapped: `networkRunId = step.run("generate-network-id", randomUUID)` (`network.ts:455`), agent IDs `step.run("generate-agent-ids-${this._counter}", ...)` (`:644`), even streaming part IDs `step.run("generate-tool-part-id-${messageId}-${tool.name}", ...)` (`agent.ts:668`). Comment at `network.ts:449`: *"Generate network run ID inside Inngest steps to ensure deterministic replay behavior."*
- **Tools are deliberately NOT wrapped in a step** (`agent.ts:724-728` comment): *"each tool can use multiple step tools, eg. `step.run`, then `step.waitForEvent` for human in the loop tasks."* — the tool body itself contains the durable boundaries (so HITL = a tool that calls `step.waitForEvent`).

This is the cleanest open implementation of "same code, runs in-memory locally or durably in production" — the seam is *ambient context detection*, not a separate durable API.

### MCP Tool Sources (KNOWN)

`agent.initMCP()` (`agent.ts:884`) lazily connects MCP servers (idempotent guard `:885`), `listMCPTools()` registers each as a normal `Tool` with `mcp:{server,tool}` metadata (`tool.ts:56-61`). Transports: `streamable-http` (with OAuth `authProvider`, reconnection, `sessionId`), `sse`, `ws`, `stdio` (`agent.ts:959-983`, `tool.ts:129-155`). MCP tools are first-class — once listed they go through the same `invokeTools()` path. `initMCP()` is awaited at the top of `agent.run()` (`:201`).

### Standalone Agent Loop — The Single-Agent ReAct Cycle (KNOWN, `agent.ts:188-440`)

When `agent.run()` is called *outside* a network (or with `maxIter > 0`), the agent runs its own ReAct loop — this is the loop the network suppresses with `maxIter:0`. The `do/while` (`agent.ts:321-369`):
```
result = new AgentResult(name, [], [], now, prompt, history, "")   # :305 empty seed
iter = 0
do:
  if lifecycles.onStart: {prompt, history, stop} = onStart({agent, network, input, prompt, history})  # :323
     if stop: return result                                        # :332 user can short-circuit the LLM
  inference = performInference(p, prompt, history, run, ...)        # :341 → p.infer (step.ai.infer if durable)
  lastActionable = inference.output.filter(m => m.type!="reasoning").pop()   # :352 skip reasoning msgs
  hasMoreActions = tools.size>0 && lastActionable && lastActionable.stop_reason != "stop"   # :356
  result = inference; history = [...inference.output]; iter++       # :362-368
while (hasMoreActions && iter < maxIter)                            # :369
if lifecycles.onFinish: result = onFinish({agent, network, result}) # :371
saveThreadToStorage(...)                                            # :385 persist new results
```
**Termination is stop-reason-based, not iteration-based** (iteration is the cap): the loop continues while the model's last non-reasoning message has `stop_reason !== "stop"` AND the agent has tools AND `iter < maxIter`. **Reasoning messages are explicitly filtered before the stop check** (`:352`) — comment `:350`: a `ReasoningMessage` has no `stop_reason` and would cause an infinite loop. `invokeTools()` is called inside `performInference`'s downstream (the tool results become `history` for the next iteration). This is the canonical single-agent ReAct loop Verso is building.

### Lifecycle Hooks — The Per-Agent Interception Points (KNOWN, `agent.ts`)

`Agent.Lifecycle<T>` hooks fire at fixed points: `enabled({agent, network}) → bool` (gates agent availability in `availableAgents()`, `network.ts:126`); `onStart({agent, network, input, prompt, history}) → {prompt, history, stop}` (`:323`, mutate the prompt/history before each inference, or `stop` to skip the LLM); `onResponse({agent, network, result}) → result` (`:468`, post-inference, pre-tool); `onFinish({agent, network, result}) → result` (`:371`, end of loop). `Agent.RoutingLifecycle<T>` adds `onRoute: RouterFn<T>` (`agent.ts:1163`) — called by the *network*, not the agent. So an Agent has 4 hooks (enabled/onStart/onResponse/onFinish); a RoutingAgent additionally exposes onRoute. These are Verso's middleware-seam reference.

### Agent vs RoutingAgent Classes + Prompt Assembly (KNOWN)

`RoutingAgent<T> extends Agent<T>` (`agent.ts:1017`) adds `type="routing"` and a required `RoutingLifecycle` (with `onRoute`). It is a *normal agent* that the network treats as a router. `agentPrompt()` (`agent.ts:833-880`) builds the message array sent to the model: `[{role:system, content: system (string or system({network}) fn)}, {role:user, content: inputContent}?, {role:assistant, content: assistant}?]`. A per-request `userMessage.systemPrompt` is **appended** to the agent's system content (`:861-863`). Critically (`:837`) the agent prompt **does NOT include network state** — state is added separately via `state.formatHistory()` and concatenated as `history` in `performInference` (`prompt.concat(history)`, `model.ts` / `agent.ts:452`). So the wire input = `[agent system + user + assistant] ++ [formatted state history]`.

### Streaming Protocol — Event Taxonomy + Monotonic Sequence (KNOWN, `streaming.ts`)

AgentKit's streaming is a **publish-based event stream** (not raw SSE) — a `publish` callback receives `AgentMessageChunk`s. The event taxonomy (`streaming.ts:47-313`): lifecycle (`run.started`, `run.completed`, `run.failed`, `run.interrupted`), step (`step.started`, `step.completed`, `step.failed`), part (`part.created`, `part.completed`, `part.failed`), deltas (`text.delta`, `tool_call.arguments.delta`, `tool_call.output.delta`, `reasoning.delta`, `data.delta`), HITL (`hitl.requested`, `hitl.resolved`), and meta (`usage.updated`, `metadata.updated`, `stream.ended`, `error`). Each event has a `scope: "network" | "agent"` and is stamped with a **monotonic `sequenceNumber`** from a shared counter (`publishEvent`, `:474`) plus `timestamp` and an `id = "publish-${seq}:${event}"` (`:519`). Network and agent contexts **share one sequence counter** (`createContextWithSharedSequence`, `network.ts:665`) so events across the whole run are totally ordered. Part IDs are generated to be ≤40 chars (OpenAI tool-call-id limit, `:524-529`), and inside a durable run **every part-ID generation is wrapped in a step** (`agent.ts:668`) for replay stability. `simulateChunking` (`:353`) splits a completed response into 50-char delta chunks to fake token streaming (the model layer doesn't yet do true token streaming — `model.ts:44` TODO). Publishing errors are swallowed (`:499`) — streaming is best-effort and never breaks execution.

**For Verso:** AgentKit is the closest peer to Verso's "non-graph, code-first orchestration" philosophy and its strongest single idea is the **ambient-context durability seam** — detect the durable runtime and transparently route non-determinism through it, leaving the agent/router code identical. Verso should: (1) copy the **Router-between-every-agent** loop shape (route → run one agent with its own mini-loop disabled → append result → re-route) as the multi-agent default — it's simpler than a graph and the router is just a function that reads typed state; (2) adopt the **Router union type** (`CodeFn | LLMRouter`) so deterministic and LLM routing are the *same slot*, switchable per-run, with `instanceof`-style dispatch; (3) make the **typed-state Proxy** the only state API and treat tool *return* (LLM-visible) and `state.data` mutation (router-visible) as two distinct channels a tool writes simultaneously; (4) leave **tools un-wrapped by the durability layer** so a tool can own its own checkpoint boundaries (HITL = a tool that awaits an external event), exactly AgentKit's choice. The thing to *reject*: AgentKit forces in-network agents to `maxIter:0`, pushing all iteration to the network loop — Verso may want agents to retain their own multi-step loop *and* be re-routable, which AgentKit gives up.

---

## Cloudflare Agents SDK

### What It Is

A TypeScript SDK where **every agent IS a Cloudflare Durable Object** (DO): one DO instance per agent identity, an embedded per-instance SQLite DB as the state store, WebSocket connections (with hibernation), built-in scheduling/queues, MCP client, and type-safe RPC over WebSocket. `Agent<Env, State>` (`index.ts:1405`) extends the partyserver `Server` (which extends `DurableObject`). The durability model is the extreme opposite of AgentKit's: durability is a **deployment target**, not an ambient capability. There is no in-memory mode — the agent's memory is a SQLite file that survives eviction, and the agent code runs only when the DO is awake.

### Internal SQL Schema — `cf_agents_*` Tables (KNOWN, verbatim from `_ensureSchema()` `index.ts:1701-1994`)

All DDL is gated by a schema-version row stored inside `cf_agents_state` itself (`CURRENT_SCHEMA_VERSION = 9`, `index.ts:954`; `SCHEMA_VERSION_ROW_ID = "cf_schema_version"` `:956`). On every DO wake the constructor calls `_ensureSchema()`, which short-circuits all DDL if `schemaVersion >= CURRENT_SCHEMA_VERSION` (`:1718`). The tables:

```sql
-- STATE: single-row store. id="cf_state_row_id" (STATE_ROW_ID :957) holds the JSON state blob.
-- Row existence is the "state was set" signal (no separate dirty flag).
CREATE TABLE cf_agents_state (id TEXT PRIMARY KEY NOT NULL, state TEXT);   -- :1706

-- SCHEDULES: the cron/delayed/interval task table the alarm reads.
CREATE TABLE cf_agents_schedules (
  id TEXT PRIMARY KEY NOT NULL DEFAULT (randomblob(9)),
  callback TEXT, payload TEXT,
  type TEXT NOT NULL CHECK(type IN ('scheduled','delayed','cron','interval')),  -- :1745
  time INTEGER, delayInSeconds INTEGER, cron TEXT, intervalSeconds INTEGER,
  running INTEGER DEFAULT 0, created_at INTEGER DEFAULT (unixepoch()),
  execution_started_at INTEGER, retry_options TEXT,
  owner_path TEXT, owner_path_key TEXT);                                  -- :1741

-- QUEUES: ordered durable task queue (FIFO by created_at).
CREATE TABLE cf_agents_queues (
  id TEXT PRIMARY KEY NOT NULL, payload TEXT, callback TEXT,
  created_at INTEGER DEFAULT (unixepoch()), retry_options TEXT);          -- :1732

CREATE TABLE cf_agents_mcp_servers (id, name, server_url, callback_url,
  client_id, auth_url, server_options);                                   -- :1720

-- WORKFLOWS: Agent↔Workflow integration tracking.
CREATE TABLE cf_agents_workflows (id, workflow_id UNIQUE, workflow_name,
  status CHECK(status IN ('queued','running','paused','errored','terminated',
  'complete','waiting','waitingForPause','unknown')), metadata, error_name,
  error_message, created_at, updated_at, completed_at);                   -- :1849
  -- + idx_workflows_status, idx_workflows_name

-- 2026 FIBER PRIMITIVES (the durable-execution additions) ──────────────
CREATE TABLE cf_agents_runs (id, name, snapshot TEXT, created_at);        -- v3 :1891 (runFiber row, deleted on completion)
CREATE TABLE cf_agents_facet_runs (owner_path, owner_path_key, run_id,
  created_at, PRIMARY KEY(owner_path_key, run_id));                       -- v5 :1904 (root-side index of descendant facets)
CREATE TABLE cf_agents_fibers (                                           -- v8 :1921 managed-fiber ledger
  fiber_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE, name TEXT NOT NULL,
  status TEXT NOT NULL, snapshot TEXT, metadata_json TEXT, error_message TEXT,
  created_at INTEGER NOT NULL, started_at INTEGER, completed_at INTEGER);
  -- + idx_fibers_status_created, idx_fibers_name_status_created, idx_fibers_status_completed
CREATE TABLE cf_agent_tool_runs (run_id PRIMARY KEY, parent_tool_call_id,
  agent_type, input_preview, input_redacted DEFAULT 1, status, summary,
  output_json, error_message, interrupted_reason, child_still_running,
  display_metadata, display_order DEFAULT 0, started_at, completed_at);   -- :1951 (subagent tool-call ledger)
```

**The `sql` template tag (KNOWN `index.ts:1674-1691`):** `sql<T>(strings, ...values)` builds a `?`-placeholder query by `strings.reduce(...)` and runs `[...this.ctx.storage.sql.exec(query, ...values)] as T[]`. It is parameterized (placeholders, not interpolation) so it is injection-safe, and it returns a *materialized array* (spreads the cursor eagerly) — wrapping errors in `SqlError(query, e)`. This is the only state-access primitive; `setState`, `schedule`, `queue` all build on it.

### `setState` → Persist + Broadcast in One Call (KNOWN)

`setState(state)` (`index.ts:2583`) → guards readonly connections (`agentContext.getStore().connection`), then `_setStateInternal(state, "server")` (`:2529`):
1. `validateStateChange()` (sync gating hook);
2. `this._state = nextState` + `INSERT OR REPLACE INTO cf_agents_state (id, state) VALUES ('cf_state_row_id', JSON.stringify(nextState))` (`:2539`) — **synchronous SQLite write**;
3. `_broadcastProtocol(JSON.stringify({state, type: CF_AGENT_STATE}), exclude_source)` (`:2545`) — pushes the new state to every connected client *except* the one that set it;
4. `ctx.waitUntil(... onStateChanged hook ...)` (`:2556`) — the post-persist hook runs out-of-band and **cannot affect persistence or broadcast** (errors swallowed into `onError`).

So state mutation is **transactionally local (SQLite) + reactively pushed (WebSocket broadcast)** — this is CF's answer to "reactive backend for agents," done at the DO boundary. Client mirror: a `CF_AGENT_STATE` message from a connection calls `_setStateInternal(parsed.state, connection)` (`:2120`) so clients can also drive state.

### `@callable` — Type-safe RPC over WebSocket (KNOWN)

`@callable(metadata?)` (`index.ts:458`) is a method decorator that registers the method in a module-level `callableMetadata = new WeakMap<Function, CallableMetadata>()` (`:244`). The dispatch is in the WebSocket `onMessage` handler (`:2135-2204`): an incoming `RPCRequest {type:RPC, id, method, args}` (`:165`) is dispatched by `methodFn = this[method]`; throws `"Method X does not exist"` if not a function, `"Method X is not callable"` if `!this._isCallable(method)` (`:2145` — the gate that prevents RPC reaching arbitrary methods). If `metadata.streaming`, it constructs a `StreamingResponse(connection, id)` and calls `methodFn(stream, ...args)` (`:2158`); otherwise `result = await methodFn.apply(this, args)` and sends `{done:true, id, result, success:true, type:RPC}` (`:2180`). Errors → `{error, id, success:false, type:RPC}` (`:2190`). This is RPC-over-an-existing-socket, not a separate HTTP route — the same hibernatable WebSocket carries state-sync, RPC, and chat protocol frames.

### Scheduling — `schedule` / `scheduleEvery` / `queue` (KNOWN)

- **`schedule(when, callback, payload?, opts?)`** (`index.ts:4146`): `when` is `Date | string(cron) | number(seconds)`. Inserts a `cf_agents_schedules` row, then `_scheduleNextAlarm()`. `callback` is `keyof this` — a method name, validated as a function. Returns a `Schedule<T>`.
- **`scheduleEvery(intervalSeconds, callback, payload?)`** (`:4207`): **idempotent** — same `(callback, intervalSeconds, payload)` returns the existing row instead of duplicating (so it's safe to call in `onStart()`, which runs on *every* wake). Max interval = 30 days (DO alarm cap, `:4214`).
- **`queue(callback, payload, opts?)`** (`:3263`): inserts a `cf_agents_queues` row (`id = nanoid(9)`), fires `_flushQueue()` which drains FIFO `ORDER BY created_at ASC` (`:3308`), `dequeue(id)` deletes a row.
- **The alarm (`_scheduleNextAlarm`, `index.ts:5854`)** is the single timer driving all schedules. It `SELECT time ... WHERE type != 'interval' OR running = 0 OR execution_started_at <= hungCutoff ORDER BY time ASC LIMIT 1` (`:5866`) to find the next due (or overdue) row, then sets the DO alarm. Overdue rows survive eviction (SQLite persists; in-memory alarm doesn't), so on wake the alarm re-fires them. A "hung" running interval (`execution_started_at` older than `hungScheduleTimeoutSeconds=30`, `:1138`) is force-reset. **One alarm timer, N logical schedules in SQLite** — the durable-scheduler pattern.

### Hibernation Lifecycle — When It Wakes, What It Costs (KNOWN code + INFERRED cost from CF docs)

`hibernate: true` is the **default** (`DEFAULT_AGENT_STATIC_OPTIONS.hibernate = true`, `index.ts:1130`). Mechanism (KNOWN): the SDK uses the DO **WebSocket Hibernation API** — connections are accepted in a hibernatable mode and their per-connection metadata is stored as a *WebSocket attachment* (the `index.ts:6175,6194` comments describe "host/root DO's hibernatable sockets and reading them from the … attachments"). When the DO is evicted, all in-memory state (`_keepAliveRefs`, `_runFiberActiveFibers`, the partyserver connection wrappers) is lost, but the SQLite tables and the WebSocket attachments persist. The DO **wakes** on: an inbound WebSocket message, an HTTP `fetch`, an RPC call, or an **alarm firing** (a due `cf_agents_schedules` row). On wake the constructor re-runs `_ensureSchema()` and `onStart()` (`:2419`), then re-hydrates connection wrappers from attachments.

**Cost rationale (INFERRED from CF DO pricing docs):** a DO is billed for **duration** (GB-s) only while *actively executing JS* or while *idle-but-not-hibernatable*. A hibernatable idle DO with open WebSockets incurs **zero duration charges**. CF's own example: 100 WebSocket clients each sending one message/minute costs **$1.91/month** with hibernation vs **$133.24/month** without (a ~70× reduction). Each DO is allocated 128 MB regardless of use; duration overage is $12.50/M GB-s; SQLite is billed by row reads ($0.001/M after 25 B free), row writes ($1.00/M after 50 M free), and stored data ($0.20/GB-month from Jan 2026). **The architectural cost: every `setState` is a SQLite row write and a broadcast; idle is free, but chatty state or sub-second polling converts to row-write + duration billing fast.** This is why CF's design pushes work into *alarms and sparse messages*, never busy loops.

### 2026 Fiber Primitives — `keepAlive` / `runFiber` / `stash` / `onFiberRecovered` (KNOWN)

These are the durable-execution additions that let an agent run long async work *across* eviction without an external workflow engine:

- **`keepAlive(): () => void`** (`index.ts:4402`): increments `_keepAliveRefs`; when it goes `0→1` calls `_scheduleNextAlarm()`, which then caps the next alarm at `keepAliveIntervalMs` (default **30 000 ms**, `DEFAULT_KEEP_ALIVE_INTERVAL_MS = 30_000` `:906`) so the DO heartbeats and stays alive. Returns a disposer that decrements. **Caveat (KNOWN comment `:1474`):** if the DO is evicted anyway, `_keepAliveRefs` is lost — keepAlive prevents *idle* eviction, not forced eviction. `keepAliveWhile(fn)` (`:4447`) wraps a promise with guaranteed dispose.
- **`runFiber(name, fn)`** (`index.ts:5015`): registers a row in `cf_agents_runs` *before* execution, holds `keepAlive()` for the duration, runs `fn(ctx: FiberContext)`, deletes the row on completion. `FiberContext` (`:670`) = `{ id, signal: AbortSignal, stash(data): void, snapshot }`. The fiber runs in an `AsyncLocalStorage` context (`_fiberALS`, `:787`).
- **`stash(data)`** (`FiberContext.stash`, doc `:675`): a **synchronous SQLite write** of a checkpoint into the fiber's `snapshot` column. This is the checkpoint primitive — equivalent to a manual `step` boundary in AgentKit, but stored in the DO's own SQLite.
- **`onFiberRecovered(ctx: FiberRecoveryContext)`** (type `:764`): user hook fired *on wake* when an interrupted fiber row is found. `ctx.snapshot` = last `stash()`ed data (or null), `ctx.recoveryReason = "interrupted"`, `ctx.createdAt` lets the hook gate stale recoveries. Poison-row protection: `fiberRecoveryMaxAgeMs = 24h` (`:1159`), hook timeout `fiberRecoveryHookTimeoutMs = 10 000` (`:1151`).
- **`startFiber(name, fn, opts?)`** (`:5039`): the *managed* variant — idempotent via `idempotencyKey` (UNIQUE in `cf_agents_fibers`), inspectable (`FiberStatus = pending|running|completed|aborted|interrupted|error` `:681`), cancellable, with `waitForCompletion`. This is a durable job ledger inside the DO.

**The fiber model vs AgentKit's step model:** AgentKit memoizes non-determinism through Inngest steps (replay re-runs the function, skipping already-completed steps). CF fibers do **not replay** — the function runs once; on eviction it stops; on wake `onFiberRecovered` hands you the last `stash()` snapshot and you resume *manually* from there. Replay-determinism (AgentKit/Temporal) vs checkpoint-resume (CF fibers) is a real fork Verso must pick between.

### AIChatAgent — The Chat Loop on Top of the DO (KNOWN, `@cloudflare/agents` / `ai-chat/src/index.ts:382`)

`AIChatAgent<Env, State, Props> extends Agent` (`ai-chat/src/index.ts:382`) is the higher-level chat agent. It adds **two SQLite tables of its own** (created in its `_ensureSchema` extension, `:687-695`): `cf_ai_chat_agent_messages` (the chat transcript) and `cf_ai_chat_request_context` (per-request context for tool-call continuations). On wake it loads `rawMessages` and runs `this.messages = autoTransformMessages(rawMessages)` (`:717`, migrates legacy message shapes). The subclass implements **`onChatMessage(onFinish, options)`** (`:931`) — the abstract handler that runs the LLM (typically AI SDK `streamText`); the base class handles persistence via `saveMessages` / `persistMessages` (`:838`), a `_persistedMessageCache` (`:518`) to avoid re-serializing unchanged messages, and a recursion guard so a `saveMessages` call inside the hook doesn't re-trigger it (`:418`). Streamed responses go out over the same hibernatable WebSocket, and the message rows persist so a reconnecting client replays the transcript. **So a CF chat agent = DO + two extra tables + one `onChatMessage` hook**, with all the state/schedule/hibernation machinery inherited.

### Think — The Opinionated Agentic Loop (KNOWN, `@cloudflare/think` / `think/src/think.ts`)

`Think extends AIChatAgent` (`think/src/think.ts`) is the batteries-included agent: a tool-using loop with `maxSteps = 10` default (max tool-call rounds per turn, `:16`), overridable hooks `getTools()`, `beforeTurn(ctx) → overrides` (inspect/override context, tools, model before inference, `:20,1119-1160`), and `afterTurn()`. It runs AI SDK `streamText` with a `stopWhen` that **always retains `maxSteps` as a safety bound** even if the subclass adds its own stop conditions (`:1158`). It merges tools from five sources (`:1127`): built-in **workspace** tools, the subclass's `getTools()`, **session** tools, **MCP** tools (`this.mcp`), **client** tools, plus per-call tools. The model-call knobs are the full AI SDK surface (`maxOutputTokens`, `temperature`, `topP`, `topK`, `presence/frequencyPenalty`, `toolChoice`, `activeTools`). Built-in Think tool families (`think/src/tools/`): **workspace** (`read`/`write`/`glob`/`grep` over the DO's SQLite-backed filesystem, `createWorkspaceTools`), **sandbox** (`createSandboxTools` — code execution), **browser** (`search` + `execute`, `createBrowserTools`), **execute**, and **extensions** (dynamically register new tools at runtime via `createExtensionTools` — the model can define a tool with name/description/parameters and a handler). Long-running Think turns lean on the **chat-recovery** machinery (`chatRecovery` config, no-progress timeouts) and the fiber/keepAlive primitives so a turn survives deploys/eviction. This is CF's answer to a full coding-agent — and it shows the layering: `Agent` (DO + state/schedule/fibers) → `AIChatAgent` (transcript + onChatMessage) → `Think` (tool loop + workspace/sandbox/browser).

### MCP Client (KNOWN, `mcp/`)

The DO is also an **MCP client**: `this.mcp` (an `MCPClientManager`) connects to MCP servers (registered in `cf_agents_mcp_servers`, schema above), with OAuth support (`client_id`, `auth_url`, `callback_url` columns). Connected MCP tools are merged into the Think tool set. So a CF agent can be both an MCP *server* (exposed via `@cloudflare/agents` MCP transport) and an MCP *client* (consuming other servers' tools).

**For Verso:** CF Agents is the reference for "durability as a deployment target." The most Verso-actionable extracts: (1) the **`cf_agents_*` SQLite schema** is a complete, minimal durable-agent state model — one single-row state blob + a schedules table read by one alarm + a FIFO queue table + a fiber ledger. Verso's durable tier could adopt this exact shape against any embedded SQL store, no DO required. (2) **`setState` = sync-write + reactive-broadcast in one call** is the cleanest reactive-backend primitive seen here; Verso should make its durable state setter also push to subscribers, with the source excluded. (3) **`@callable` RPC multiplexed over one WebSocket** (state-sync, RPC, chat all on the same hibernatable socket) is the edge-communication pattern Verso's brief asked about — one socket, message-type-discriminated. (4) **One alarm, N SQLite schedules** is the durable-scheduler pattern: don't hold N timers in memory, hold rows and recompute the next alarm. (5) The **checkpoint-resume fiber model** (`stash` + `onFiberRecovered`) is the architectural alternative to replay-determinism — cheaper to implement (no deterministic-execution contract) but pushes resume logic onto the user. The thing Verso should *reject as a default*: forcing everything through DO eviction means **no hot-path in-memory mode** — every state read/write hits SQLite, and there's no way to keep an agent warm without paying keepAlive duration. Verso's seam (tactical in-memory ↔ durable) is exactly the flexibility CF gives up by making the DO mandatory.

---

## OpenAI Agents SDK (JS/TS)

### What It Is

A lightweight TS port of OpenAI's Python Agents SDK. Primitives: **Agent** (instructions + tools + handoffs + guardrails + outputType), **Handoffs** (typed delegation between agents, surfaced to the model as `transfer_to_*` function tools), **Guardrails** (input/output validators that can tripwire-abort a run), **Tracing** (span-based, hierarchical, batched export), **Sessions** (persistent conversation history), and 2026 additions: **Sandbox/Shell agents** (filesystem + shell tool execution with interrupt/resume) and **agent-as-tool subagents** (`agent.asTool()`). The whole thing is `agents-core` (provider-agnostic) + `agents-openai` (the OpenAI Responses/Chat model adapter) + `agents-realtime` + `agents-extensions`.

### Agent Class — How Handoffs / Tools / Guardrails Are Typed (KNOWN, `agent.ts`)

`Agent<TContext, TOutput>` fields (`agent.ts:278-409`):
- `instructions: string | (runContext, agent) => string | Promise<string>` (`:285`) — the system prompt, static or dynamic.
- `handoffs: (Agent<any,any> | Handoff<any,TOutput>)[]` (`:317`) — a sub-agent OR an explicit `Handoff` wrapper. A bare `Agent` is auto-wrapped via `getHandoff()`.
- `tools: Tool<TContext>[]` (`:340`); `modelSettings: ModelSettings` (`:335`); `inputGuardrails / outputGuardrails` (`:380,386`); `outputType: TOutput` (`:391`, drives structured output); `toolUseBehavior: ToolUseBehavior` (`:409`, controls whether a tool result ends the turn).
- **Type inference:** `Agent.create({handoffs, outputType})` (`:491-502`) infers `TOutput` as the *union* of the agent's own `outputType` and all handoff targets' output types — so the static type of the run result reflects every agent it could hand off to. This is the typed-handoffs property the Verso brief flagged.

### Handoffs as a First-Class Primitive (KNOWN — the defining mechanism)

A handoff is **modeled as a function tool the LLM can call.** `defaultHandoffToolName(agent) = "transfer_to_" + toFunctionToolName(agent.name)` (`handoff.ts:64-67`); description `"Handoff to the {name} agent to handle the request. {handoffDescription}"` (`:76-83`). The `Handoff` class (`handoff.ts:~190-288`) holds `agent`, `agentName`, `onInvokeHandoff(context, args) => Agent | Promise<Agent>`, an `inputFilter?` (rewrites the conversation the next agent sees), and `isEnabled` predicate. `getHandoffAsFunctionTool()` (`:229`) emits `{type:'function', name: toolName, description, parameters: inputJsonSchema, strict}`.

**The handoff trigger (KNOWN, `runner/toolExecution.ts:~1300-1384`):** during tool processing, if the model called a `transfer_to_*` tool, `onInvokeHandoff` resolves `newAgent`; a `RunHandoffOutputItem` carrying `getTransferMessage(newAgent)` is pushed to the items; `runner.emit('agent_handoff', ...)`; the handoff's `inputFilter` (or the run-level `handoffInputFilter`) rewrites `inputHistory`/`preHandoffItems`/`newItems`; and the step result is `{type:'next_step_handoff', newAgent}` (`:1384`). Multiple simultaneous handoffs → the span records an error "Multiple handoffs requested" and the first wins (`:1325-1333`).

### Runner Loop — Active-Agent Switch + Termination (KNOWN, `run.ts:894-1129`)

The loop is a `while(true)` driven by a `state._currentStep` discriminated union (`runner/steps.ts`): `next_step_run_again | next_step_final_output | next_step_handoff | next_step_interruption`.

```
while (true):
  step ??= {type:'next_step_run_again'}
  if step == next_step_interruption: resume interrupted turn (sandbox/HITL); return-or-continue
  if step == next_step_run_again:                                       # run.ts:936
     prepareTurn() → state._currentTurn++  (turnPreparation.ts:229)
        if _maxTurns != null && _currentTurn > _maxTurns:               # turnPreparation.ts:75
           throw MaxTurnsExceededError                                  # :81
     run input guardrails (parallel)
     preparedCall = #prepareModelCall(... tools, serializedHandoffs, outputType ...)  # :981
     guardrailTracker.throwIfError()                                    # tripwire abort
     lastTurnResponse = getResponseWithRetry(model, {...})              # :993 ONE LLM CALL
     processedResponse = processModelResponseAsync(...)                 # :1044 classify tool calls / handoffs / output
     turnResult = resolveTurnAfterModelResponse(...)                    # :1058 run tools, detect handoff/final
     applyTurnResult(...)  → sets state._currentStep                    # :1071
  switch state._currentStep:
     next_step_final_output: runOutputGuardrails(); emit agent_end; return RunResult  # :1087
     next_step_handoff:  state.setCurrentAgent(newAgent);                              # :1106 ACTIVE-AGENT SWITCH
                         end current agent span; _currentStep = next_step_run_again    # :1117 (loop continues)
     next_step_interruption: return RunResult (await human/sandbox)                    # :1119
     next_step_run_again: loop                                                         # :1122
```

**Three load-bearing facts:** (1) **the active agent is just `state._currentAgent`** — a handoff is `setCurrentAgent(newAgent)` + reset agent span, then re-loop; the conversation history carries over (filtered by `inputFilter`), so the new agent continues the same `state`. There is no separate "subgraph." (2) **Termination = `next_step_final_output`** (model produced output matching `outputType` and no tool wants to continue) OR `MaxTurnsExceededError` (`maxTurns` default resolved at `:827`, checked *per turn* in `turnPreparation`). (3) **Guardrails abort via tripwire:** input guardrails run in parallel with model prep; `guardrailTracker.throwIfError()` (`:991`) raises before the response is used; output guardrails run on `next_step_final_output` before returning.

### Sessions — Per-Turn History Assembly (KNOWN, `memory/session.ts`)

`interface Session` (`session.ts:27-74`): `getSessionId()`, `getItems(limit?)` (most-recent `limit` items, chronological), `addItems(items)`, `popItem()`, `clearSession()`, plus optional `prepareHistoryItemForModelInput(item)` (strip provider replay metadata) and `preserveReasoningItemIdsForPersistence()`. Subtypes: `SessionHistoryRewriteAwareSession` (`applyHistoryMutations`) and `OpenAIResponsesCompactionAwareSession` (server-side compaction via `previous_response_id`). `MemorySession` (`memory/memorySession.ts`) is the in-process impl (array + `sessionId = randomUUID()`).

**How context is assembled per turn (KNOWN, `run.ts:598-672`):** when a `session` is passed, `prepareInputItemsWithSession()` (`:607`) loads `session.getItems()` and prepends them to the run input; a `createSessionPersistenceTracker()` (`:598`) records which items have been persisted; after the turn `saveToSession(... getItemsForPersistence())` (`:668`) appends only the *new* items. So the Session is the durable store and `state._generatedItems` is the in-run working set — Session = across-runs memory, `state` = within-run memory. (Storage backend is pluggable: SQLite/Postgres sessions ship in extensions; `MemorySession` is the default.)

### Tracing — Span Model + TracingProcessor (KNOWN, `tracing/`)

Spans are typed by `spanData.type` (`tracing/spans.ts:14-118`): `agent` (`{name, handoffs[], tools[], output_type}`), `generation` (`{input[], output[], model, model_config, usage:{input_tokens,output_tokens,details}}`), `function` (`{name, input, output, mcp_data}`), `handoff` (`{from_agent, to_agent}`), `response` (`{response_id}`), `guardrail`, `custom`, `mcp_tools`, `transcription`/`speech` (realtime). Each `Span` carries `trace_id`, `span_id`, `parent_id` (`spans.ts:267-271`) and exports to JSON via `removePrivateFields()`. **A run produces one trace; an agent turn nests a `generation` span (the LLM call) + `function` spans (tools) + `handoff` spans under an `agent` span** — the loop ends agent spans on handoff (`run.ts:1108-1111`).

`interface TracingProcessor` (`tracing/processor.ts:25-61`): `onTraceStart`, `onTraceEnd`, `onSpanStart`, `onSpanEnd`, `shutdown(timeout?)`, `forceFlush()`. The default is `BatchTraceProcessor` (`:116`): a bounded buffer (`maxQueueSize=1000`, `maxBatchSize=100`, `scheduleDelay=5000ms`, `exportTriggerRatio=0.8` → flush when buffer ≥ 800) that pushes batches to a `TracingExporter` (`:130-143`). In environments without a background loop it warns and requires manual `getGlobalTraceProvider().forceFlush()` (`:149`). The OpenAI exporter ships in `agents-openai`; OTEL/third-party exporters implement `TracingExporter`.

### Sandbox / Shell + Subagents (KNOWN, 2026 additions)

- **Sandbox/Shell:** `Shell` interface (`shell.ts:38+`) executes `ShellAction`s and returns `ShellResult {output: ShellOutputResult[], maxOutputLength?}`; the protocol types come from `types/protocol.ts`. The runner has a dedicated **sandbox interrupt/resume path**: `next_step_interruption` → `prepareSandboxInterruptedTurnResume()` + `resumeInterruptedTurn()` (`run.ts:900-915`), so a shell/computer tool that pauses (e.g. for approval or a long exec) suspends the turn and resumes from the same `state` — the same machinery as HITL tool approval. There is no monolithic `SandboxAgent` *class* in core; it's the shell/computer tools + the interrupt-resume runner path (the snapshot is `RunState`, serialized).
- **Subagent-as-tool:** `agent.asTool({toolName?, toolDescription?, ...})` (`agent.ts:665-720`) wraps an agent as a `Tool` whose handler runs a nested `run()` and returns the sub-agent's final output. This is *delegation-as-tool-call* — distinct from a handoff (which **switches the active agent and hands over the conversation**). The SDK thus offers BOTH coordination models explicitly: handoff (transfer control) vs asTool (call and return).

### Tool Taxonomy (KNOWN, `tool.ts`)

A `Tool` is a discriminated union: **`FunctionTool`** (`tool.ts:223-282`) — `{type:'function', name, description, parameters: JsonObjectSchema, strict, invoke(runContext, input, details) → Promise<string|Result>, needsApproval: ToolApprovalFunction, timeoutMs?, timeoutBehavior?: 'error_as_result'|'raise_exception', deferLoading?}`. `needsApproval` returning true makes the run *interrupt* (HITL approval). `timeoutBehavior` chooses whether a tool timeout becomes a model-visible result or fails the run (`:274`). **`ComputerTool`** (`:405-445`) — wraps a `Computer` (screen/mouse/keyboard) with its own approval function. **`HostedTool` / `HostedMCPTool`** (`:907-952`) — `{type:'hosted_tool'}` tools that run *server-side* on the OpenAI Responses API (web search, file search, hosted MCP with `providerData.type:'mcp'`). So the same `tools[]` array mixes local function tools, computer-use tools, and server-hosted tools — the runner serializes each into the provider's tool format and routes results back uniformly.

### Guardrails — The Tripwire Contract (KNOWN, `guardrail.ts`)

`InputGuardrail` (`guardrail.ts:63-72`) = `{name, execute: (args) => Promise<GuardrailFunctionOutput>}`; `GuardrailFunctionOutput` (`:24-28`) = `{tripwireTriggered: boolean, outputInfo}`. A guardrail runs alongside the agent by default (`:75`, non-blocking parallel) or blocking. When `tripwireTriggered` is true the run aborts (the `guardrailTracker.throwIfError()` in the runner, OpenAI runner loop above). `OutputGuardrail` is symmetric but receives the agent's final output and runs at `next_step_final_output`. Each produces an `InputGuardrailResult {guardrail, output: {tripwireTriggered, outputInfo}}` recorded as a `guardrail` span. **Guardrails are first-class run-aborters, not post-hoc validators** — they can kill a run before the model output is ever consumed.

### Model Interface + RunState Serialization (KNOWN, `model.ts`, `runState.ts`)

`interface Model` (`model.ts:573-585`) is the provider abstraction: `getResponse(request: ModelRequest) → Promise<ModelResponse>` and `getStreamedResponse(request) → AsyncIterable<StreamEvent>`; `ModelProvider` (`:600`) resolves a model by name. `agents-openai` implements this over the Responses/Chat APIs; the loop is provider-agnostic.

**`RunState` is the serializable snapshot that makes HITL/sandbox resume work** (`runState.ts`). It has a **versioned schema** — `CURRENT_SCHEMA_VERSION = '1.12'` (`:94`), with a documented migration history (`:75-90`: 1.0 initial, 1.3 computer-tool approvals, 1.4 toolInput, 1.6 requestId, etc.). The serialized state (Zod schemas, `:120-211`) captures the `currentAgent` (by name reference), `originalInput`, `generatedItems`, `modelResponses`, `currentTurn`, `currentStep`, spans, and pending tool approvals/interruptions. `RunState.toString()`/`fromString()` round-trip the entire run, so an interrupted run (HITL approval, sandbox pause, max-turns) can be **persisted, sent to a client, and resumed later from the exact step** — the runner's `next_step_interruption` path rebuilds from this. This is the serialized-checkpoint durability model (vs CF's stash or AgentKit's replay).

**For Verso:** This SDK is the reference for **handoffs-as-a-typed-primitive vs subagent-as-tool**, the exact distinction Verso's brief asks Verso to take a position on. The reimplementable insights: (1) **model a handoff as a `transfer_to_<agent>` function tool** — the LLM "decides" by calling it, the runner detects the tool name and does `setCurrentAgent(newAgent)`; no separate routing model needed, and the type system can infer the result union from all handoff targets. (2) **The runner is a `while(true)` over a `state._currentStep` discriminated union** (`run_again | final_output | handoff | interruption`) — Verso's ReAct loop should be a state machine over a similar enum, where `handoff` = active-agent swap + re-loop (not recursion) and `interruption` = return-and-await (HITL/sandbox use the *same* path). (3) **Two memory tiers: Session (across runs, pluggable `getItems/addItems/popItem`) vs RunState (within run)** — Verso should keep these distinct; per-turn assembly = `session.getItems()` prepended, persist only new items after. (4) **The span taxonomy (`agent`/`generation`/`function`/`handoff`/`guardrail`) + `TracingProcessor` interface + `BatchTraceProcessor` (buffer 1000, batch 100, 5s, 0.8 trigger)** is a ready-made observability contract — Verso's tracing should emit exactly these span types and ship a batch processor with these defaults. (5) **Guardrails as parallel-running tripwires** that abort the run before the model output is consumed — a cleaner pattern than post-hoc validation. (6) Offer **both** `handoff` and `asTool` — they are not the same and conflating them (as prompt-only frameworks do) loses the typed control-transfer.

---

## LangGraph.js

### What It Is

The TS port of LangGraph — graph-based stateful agent orchestration. A `StateGraph` of **nodes** (functions), **edges** (static + conditional), and a typed **state schema** (Annotation channels) compiles to a **Pregel** runtime (BSP super-steps) with automatic checkpointing, HITL interrupts, and cross-thread long-term memory (`Store`). This is the explicit *foil* for Verso: the most mature typed-state-reducer-merge and interrupt/resume implementation in TS, at the cost of a graph DSL. (Note: as of this clone the core lives in `libs/langgraph-core/`, not `libs/langgraph/` — a recent refactor.)

### Annotation Reducer-Merge — How Typed State Works (KNOWN, `graph/annotation.ts`)

`Annotation.Root({...})` builds a `StateDefinition` — a map of field-name → **Channel** (`annotation.ts:62-85,172`). Each field is one of two channels (`getChannel()`, `:174-195`):
- **`Annotation<T>()`** with no args → `LastValue<T>` (`:166-169`): overwrite semantics. Its `update()` (`channels/last_value.ts:34-46`) accepts **exactly one** write per super-step and **throws `InvalidUpdateError` if two nodes write the same key in one step** (`:38`). So an un-reduced channel is a single-writer slot.
- **`Annotation<T>({reducer, default})`** → `BinaryOperatorAggregate(reducer, default)` (`:182-183`): the reducer-merge. Its `update(values[])` (`channels/binop.ts:65-97`) folds all writes for the step: if empty value, take first; then `this.value = operator(this.value, incoming)` for each subsequent write (`:93`). A special `OverwriteValue` sentinel lets a write *replace* instead of fold (max one overwrite per step, else throws, `:84`). The canonical example is the `messages` reducer: `(left, right) => left.concat(Array.isArray(right) ? right : [right])` with `default: () => []` (`annotation.ts:127-136`).

**Type inference flows through the channels:** `StateType<SD> = { [k]: ExtractValueType<SD[k]> }` and `UpdateType<SD> = { [k]?: ExtractUpdateType<SD[k]> }` (`:37-43`). A node is `RunnableLike<StateType, UpdateType | Partial<StateType>>` (`:45-48`), so a node receives the *fully merged* state and returns a *partial* update; the runtime fans each returned key into its channel's `update()`. **This is the reducer-merge primitive: state is a set of named channels, a super-step collects all node writes per channel, and each channel folds them via its reducer.** `messages: concat`, scalar fields: last-value-wins-but-single-writer. The Verso-relevant insight: the reducer is *per-field*, declared at schema time, and the merge happens *between* super-steps, not inside a node.

### StateGraph compile() → Pregel (KNOWN, `graph/state.ts`)

`StateGraph(annotation)` accumulates `nodes`, `edges` (static `[start,end]`), `branches` (conditional), and `channels` (from the annotation's `_addSchema`, `:674-688`). `.compile({checkpointer?, store?, interruptBefore?, interruptAfter?})` (`:1135-1202`):
1. constructs a `CompiledStateGraph` (a Pregel) with `channels = {...this.channels, [START]: new EphemeralValue()}` (`:1153`), `inputChannels: START`, default `streamMode: "updates"` (`:1160`);
2. `attachNode(START)` then `attachNode(key, node)` for each node (`:1170-1174`) — each becomes a `PregelNode` that *subscribes* to channels and *writes* to channels;
3. `attachBranch(START, SELF, controlBranch)` and per-node control branches (`:1176-1188`) — this is how `Command(goto)` dynamic routing works;
4. `attachEdge(start, end)` for static edges, waiting-edges (join: a node fires only when *all* its source edges have written), and conditional `branches` (`:1189-1199`);
5. `.validate()`.

So **`addConditionalEdges(source, routerFn, pathMap)`** registers a branch whose `routerFn(state)` returns the next node name(s) — evaluated each super-step. The whole graph is a Pregel: in each super-step, all *active* nodes run (potentially in parallel), their writes are collected, channels fold them, then edges/branches decide the next active set. Termination = no active nodes (reached `END`).

### Checkpointing — `BaseCheckpointSaver` (KNOWN, `checkpoint/src/base.ts`)

`abstract class BaseCheckpointSaver<V>` (`base.ts:112`): `serde = new JsonPlusSerializer()`; abstract methods `getTuple(config) → CheckpointTuple` (`:124`), `list(config, opts) → AsyncGenerator<CheckpointTuple>` (`:128`), `put(config, checkpoint, metadata, newVersions) → config` (`:133`), `putWrites(config, writes, taskId)` (intermediate writes linked to a checkpoint, `:143`), `deleteThread(threadId)` (`:153`). `getNextVersion(current)` produces monotonic channel versions (int +1 by default, `:161`). A **checkpoint = a snapshot of every channel's value + per-channel versions**, keyed by `(thread_id, checkpoint_ns, checkpoint_id)`. The PG/SQLite/Redis/Mongo savers (separate `libs/checkpoint-*`) implement these five methods over their store. Because the state is *channels*, the checkpoint is the channel map — small, structured, serializable — vs CF's blob-or-CRIU approaches.

### Interrupt / Resume — Re-entrant Counter (KNOWN, `interrupt.ts`)

`interrupt(value)` (`interrupt.ts:63-113`) is the HITL primitive. It requires a checkpointer (`:75`, throws `MISSING_CHECKPOINTER` otherwise). Mechanism via a per-task `PregelScratchpad`:
- `scratchpad.interruptCounter += 1; idx = counter` (`:84`) — each `interrupt()` call in a node gets a sequential index.
- If a resume value exists for this index (`scratchpad.resume[idx]`), **return it** (`:90`) — the node continues.
- Else if a `nullResume` is queued, consume + push it (`:100-103`).
- Else **throw `GraphInterrupt([{id, value}])`** (`:112`) — this propagates up, the Pregel loop catches it, checkpoints, and surfaces the interrupt to the caller.

**The re-entry model (the subtle, critical part):** resuming with `new Command({resume: X})` **re-runs the interrupted node from the top**. The node re-executes its code; each `interrupt()` call is matched by *index* to a stored resume value — so the first N interrupts return their stored answers and execution proceeds to the (N+1)th. This is why the docs warn: don't wrap `interrupt()` in try/catch (it throws `GraphInterrupt` to suspend), and a node must be **idempotent up to its interrupts** because everything before the resumed interrupt re-runs. `id = XXH3(checkpoint_ns)` (`:111`) keys the interrupt to its position.

`Command` (`constants.ts:447-498`): `{resume?, update?, goto?, graph?}`. `update` = state writes applied as if the node returned them (`:468`, → `_updateAsTuples()` PendingWrites); `goto` = next node name(s) or `Send` object(s) for dynamic routing (`:482`); `graph: Command.PARENT = "__parent__"` (`:484`) sends the command up to the parent graph from a subgraph. So `Command` unifies *resume*, *state-patch*, and *dynamic-route* in one return value.

### BaseStore — Cross-Thread Long-Term Memory (KNOWN, `checkpoint/src/store/`)

`BaseStore` (`store/base.ts`, `store/batch.ts`) is namespace-scoped KV with optional vector search — **separate from checkpoints** (checkpoints = per-thread run state; Store = cross-thread memory). API: `get(namespace: string[], key) → Item | null`, `put(namespace, key, value, index?)`, `delete(namespace, key)`, `search(namespacePrefix, {filter?, query?, limit, offset})`, `listNamespaces(...)` (`batch.ts:70-103`). Namespaces are validated string-arrays (no periods, no empties, `base.ts:19-37`). `IndexConfig` (`base.ts:294-320`): `{dims, embeddings: Embeddings, fields: string[]}` — controls which item fields get embedded for semantic `search(query)`; `filter` supports exact match and `$gt`-style comparison operators (`:145-156`). So Store = a pluggable namespaced document store with optional embedding-based retrieval — the durable-memory backend interface.

### Stream Modes (KNOWN, `pregel/types.ts:24-31`)

`StreamMode = "values" | "updates" | "debug" | "messages" | "checkpoints" | "tasks" | "custom"`. `values` = full state after each super-step; `updates` (default) = only the node-keyed deltas per step; `messages` = LLM token stream (for chat UIs); `custom` = whatever a node writes via the `StreamWriter`; `checkpoints`/`tasks`/`debug` = execution introspection. `stream(input, {streamMode})` can take an array of modes and multiplexes them (`stream/mux.ts`).

### Channel Taxonomy — Beyond LastValue/BinaryOp (KNOWN, `channels/`)

The Annotation layer exposes two channels, but the runtime has more (`channels/`): **`LastValue`** (single-writer overwrite, throws on 2 writes/step), **`BinaryOperatorAggregate`** (reducer fold), **`Topic`** (`topic.ts:7-30` — a pub/sub list channel with `accumulate?: boolean`; if false, emptied after each step → transient message-passing between nodes), **`EphemeralValue`** (`ephemeral_value.ts:7-33` — wiped at end of step if no write; used for `START` input, `state.ts:1155`), **`AnyValue`**, **`UntrackedValue`** (not checkpointed), **`DynamicBarrierValue`** / **`NamedBarrierValue`** (join-synchronization: a node waits until all named writers have written). These barrier channels are how LangGraph implements *waiting edges* (a node fires only when all its sources complete). **The channel is the unit of both state-merge AND inter-node synchronization** — Verso's typed-state design should note that a channel can encode "wait for N writers" (barrier) as well as "fold writes" (reducer).

### `Send` — Dynamic Map-Reduce Fanout (KNOWN, `constants.ts:181`)

`new Send(nodeName, args)` (`constants.ts:181`) returned from a conditional edge or a `Command.goto` spawns a node invocation **with a specific payload**, independent of channel state — enabling map-reduce: a router returns `[new Send("generate_joke", {subject}) for each subject]` (`:144-161`) and the Pregel runs all of them in parallel in the next super-step, their results folding back through a reducer channel. This is the dynamic-parallel-dispatch primitive (vs the static edges declared at compile time). Verso's parallel sub-agent dispatch maps onto exactly this: emit N `Send`-like work items, run them concurrently, reduce results.

### `createReactAgent` — The Graph IS a ReAct Loop (KNOWN, `prebuilt/react_agent_executor.ts`)

The prebuilt agent proves a graph encodes a plain ReAct loop with zero ceremony (`react_agent_executor.ts:855-953`): `new StateGraph(MessagesAnnotation).addNode("tools", toolNode).addNode("agent", callModel).addEdge(START, "agent").addConditionalEdges("agent", shouldContinue, {tools: "tools", [END]: END}).addEdge("tools", "agent")`. `shouldContinue(state)` returns `"tools"` if the last AI message has tool calls, else `END` (`:902-945`). So **agent→(tools?)→agent until no tool calls** — the canonical ReAct loop, expressed as a 3-node graph. Optional `pre_model_hook`/`post_model_hook` nodes (`:882,900`) and a `generate_structured_response` terminal node (`:952`) extend it. The `messages` channel uses `messagesStateReducer` (concat + dedupe-by-id), so each turn appends. This is the direct comparison point: Verso's ReAct loop does the same thing *without* the graph — and the prebuilt agent shows the graph buys you checkpointing/interrupts/streaming-for-free at the cost of the `StateGraph` wiring boilerplate.

**For Verso:** LangGraph.js is the foil — Verso rejects graph-DSL-by-default, so the job here is to extract the *typed-state and interrupt mechanics* without adopting the graph. (1) **The Annotation channel model IS the reusable idea**: state = named channels, each with a per-field reducer declared at schema time (`LastValue` = overwrite single-writer; `BinaryOperatorAggregate` = fold). Verso's typed memory should adopt exactly this — a reducer-per-field, with the merge happening at a well-defined boundary (super-step / turn), and a single-writer error for un-reduced fields. This is strictly better than AgentKit's Proxy-mutation (no merge semantics, last-write-wins silently) for concurrent/multi-agent writes. (2) **Checkpoint = channel-map snapshot + per-channel monotonic versions**, keyed by `(thread, ns, id)`, via a 5-method `BaseCheckpointSaver` — small and structured, the opposite of CF's blob and Trigger's CRIU. If Verso state is channels, Verso checkpoints are nearly free and queryable. (3) **The interrupt re-entrant-counter model** is the JS reference for HITL: `interrupt(value)` throws to suspend, resume re-runs the node and matches interrupts by index. Verso must decide: re-run-from-top (LangGraph: simple, requires idempotent prefixes) vs resume-at-point (CF fiber `stash`/Inngest step: complex, no idempotency requirement). (4) **`Command` unifying resume + state-update + dynamic-goto** is an elegant single return type Verso should copy for its HITL/control-transfer return value. (5) **Store (cross-thread, namespaced, optional embeddings) vs Checkpointer (per-thread run state)** is the correct two-tier memory split — Verso should keep durable cross-session memory (Store) distinct from run-checkpoint state. (6) The **stream-mode multiplexing** (`values`/`updates`/`messages`/`custom`) is the observability contract for a streaming agent; Verso should expose at least `updates` (deltas) + `messages` (tokens) + `custom`. What Verso *rejects*: the Pregel super-step model and graph DSL as the default authoring surface — but the channel/checkpoint/interrupt mechanics underneath are exactly what Verso wants, minus the graph.

---

## Convex Agent Component (`@convex-dev/agent`)

### What It Is

A Convex *component* (not a standalone framework) that gives a Convex app a managed agent layer: persistent threads + messages stored as DB rows, hybrid vector+text search over history, tool calls expressed as Convex functions, and real-time streaming over Convex's reactive WebSocket subscriptions. It is built on the Vercel AI SDK (already covered — see `researchfms/teardowns/VERCEL_AI_SDK.md`) — the AI SDK does the LLM loop; Convex Agent owns *persistence, retrieval, and reactivity*. This is the reference implementation of "reactive backend for agents": agent work runs as durable Convex actions/mutations while clients stay live via subscriptions, no polling.

### Thread / Message Schema (KNOWN, `component/schema.ts`)

Messages and threads are first-class DB rows (`schema.ts:18-169`):
- **`threads`** (`:19-30`): `{userId?, title?, summary?, status, parentThreadIds?}`; indexed by `userId`; **search index `title`** (`searchField:"title", filterFields:["userId"]`). `parentThreadIds` is how a thread is forked/handed off.
- **`messages`** (`:31-84`): `{userId?, threadId, order, stepOrder, embeddingId?, fileIds?, status, agentName?, model?, provider?, message (the AI SDK message), tool: boolean, text?, usage?, sources?, finishReason?, reasoning?}`. Three indexes: **`threadId_status_tool_order_stepOrder`** (`:70` — the primary read path: visible successful messages in `(order, stepOrder)` sequence, with pending separated for streaming), **search index `text_search`** (`searchField:"text", filterFields:["userId","threadId"]`, `:79`), and **`embeddingId_threadId`** (`:84` — join from a vector hit back to the message). `order` = turn number; `stepOrder` = step within a turn (tool call vs tool result differ by +1).
- **Streaming tables:** `streamingMessages` (`:87-130`) holds in-flight stream state (`{kind:"streaming", lastHeartbeat, timeoutFnId} | {kind:"finished", endedAt, cleanupFnId} | {kind:"aborted", reason}`), and **`streamDeltas`** (`:132-138`) holds the ordered delta chunks `{streamId, start (incl), end (excl), parts[]}` indexed `streamId_start_end`. **This is the reactive-streaming mechanism: deltas are DB rows, and the client subscribes to them** — not SSE. A token arrives → a `streamDeltas` row is inserted → Convex pushes the change to every subscribed client. After the stream finishes the deltas are vacuumed and the final `messages` row remains.
- **`memories`** (`:140-148`): `{threadId?, userId?, memory: string, embeddingId?}` — separate long-term memory, vector-indexed.
- **`files`** (`:150-161`): refcounted blob store (`{storageId, hash, refcount, lastTouchedAt}`).

### Vector Tables — One Table Per Dimension (KNOWN, `component/vector/tables.ts`)

Rather than one embeddings table, the component defines **a separate table per supported dimension**: `embeddings_128, embeddings_256, …, embeddings_4096` (`VectorDimensions = [128,256,512,768,1024,1408,1536,2048,3072,4096]`, `tables.ts:70-85`). Each (`table()`, `:40-48`) stores `{model, table, userId?, threadId?, vector: number[], model_table_userId?, model_table_threadId?}` with a `vectorIndex("vector", {vectorField, dimensions, filterFields:["model_table_userId","model_table_threadId"]})`. The denormalized composite filter fields (`model_table_threadId = [model, table, threadId]`) let one vector index serve multiple models/tables/threads while filtering at query time — Convex vector indexes require fixed `dimensions`, hence the per-dimension table split. `validateVectorDimension()` (`:73`) rejects unsupported dims.

### `searchMessages()` — Hybrid Vector + Text via Reciprocal Rank Fusion (KNOWN)

The retrieval-before-inject path (`client/search.ts` + `component/messages.ts`):
1. `fetchContextMessages` assembles context = `[...searchMessages, ...recentMessages]` (`search.ts:94-99`). Recent = last `DEFAULT_RECENT_MESSAGES = 100` (`shared.ts:18`) by `(order, stepOrder)`.
2. Search runs only if `(textSearch || vectorSearch) && limit` (`search.ts:157`). `limit` defaults to **10** (`search.ts:218`). Text length capped at `MAX_EMBEDDING_TEXT_LENGTH = 10_000` chars for embedding (`search.ts:41`).
3. **`textSearch`** (`messages.ts:900-936`): `withSearchIndex("text_search", q => q.search("text", text).eq(threadId | userId)).take(limit)` — Convex BM25-style full-text over the `text` field.
4. **`vectorSearch`** (`messages.ts:722-777`): `searchVectors(embedding, {dimension, model, table:"messages", threadId, limit})`, filtered by `_score > vectorScoreThreshold` (default **0.0**, `search.ts:38`).
5. **Fusion (KNOWN, `messages.ts:751-762`):** Reciprocal Rank Fusion with constant **`k = 10`**. For each vector hit at rank `i`, `score = 1/(i+k) + 1/(textRank+k)` where `textRank = textEmbeddingIds.indexOf(id)` (or ∞ if absent). Sort desc, take top `limit` embeddingIds.
6. **Context expansion (`messageRange`, `DEFAULT_MESSAGE_RANGE = {before:2, after:1}`, `shared.ts:79`):** for each matched message, also fetch the 2 messages before and 1 after — so retrieved snippets carry conversational context, not isolated lines. Final set is sliced to `limit`.

So the inject-context is: **100 recent messages + top-10 RRF-fused (vector⊕text) historical messages, each expanded by [-2,+1] neighbours.** These constants (`100`, `10`, `k=10`, `{before:2, after:1}`, threshold `0.0`) are the exact knobs Verso would calibrate.

### Tool Calls as Convex Functions (KNOWN, `client/createTool.ts`)

`createTool({inputSchema, description, execute, needsApproval?})` (`createTool.ts:136-306`) wraps a Vercel AI SDK `tool()` but sets `__acceptsCtx: true` and injects a **`ToolCtx`** — a Convex `GenericActionCtx` augmented with `{agent?, userId?, threadId?, messageId?}` (`:22-28`). The tool's `execute(ctx, input, options)` therefore runs **inside the Convex action runtime** and can call `ctx.runMutation / ctx.runAction / ctx.runQuery` (`:289-302`) — i.e. **a tool call is a Convex transaction**: reads are consistent, writes are durable and reactive, and the result is type-checked against the Convex data model. `needsApproval(ctx, input, options)` (`:272-285`) gates a tool behind HITL. The Agent injects `ctx/userId/threadId` at call time; defining a tool without ctx (outside an action) throws. This is the type-safety bridge: AI SDK owns the tool *schema and loop*, Convex owns the tool *execution context and durability*.

### Agent Class + the generateText/streamText Pipeline (KNOWN, `client/index.ts`, `client/types.ts`)

`new Agent(component, {name, instructions, languageModel, textEmbeddingModel?, tools?, contextOptions?, storageOptions?, usageHandler?, maxSteps?})` (`types.ts:26-182`). The agent is a *thin orchestrator over the AI SDK*: `createThread(ctx, {userId})` → row in `threads`; `continueThread(ctx, {threadId})` returns a `thread` object whose `generateText/streamText` are bound (`index.ts:336,376`). `generateText(ctx, {threadId, userId}, {prompt|messages, tools?, maxSteps?, contextOptions?, storageOptions?})` (`index.ts:470`):
1. **context assembly** (`fetchContextMessages` + `contextOptions`, `:872`): merge agent-level `contextOptions` with per-call, then pull `[recent + RRF-searched]` messages (the search algorithm above) as the message history.
2. **LLM call**: delegates to AI SDK `generateText`/`streamText` (imported `ai`, `:20`); `maxSteps` is translated to **`stopWhen: stepCountIs(maxSteps)`** (`:1553-1554`) — the AI SDK's multi-step tool loop bound. Records `model`/`provider` via `getModelName`/`getProviderName` (`:1220`).
3. **persistence** (`storageOptions`, default `"promptAndOutput"`): `saveMessages(ctx, {threadId, messages})` (`:749-788`) writes `messages` rows with `(order, stepOrder)`, generating embeddings for non-tool/non-system messages via `textEmbeddingModel` (one of the per-dimension vector tables).
4. **usage**: `usageHandler` callback receives token usage per call.

So the agent loop is the AI SDK's loop; Convex Agent's job is **context-in (hybrid retrieval) and messages-out (durable rows + embeddings)** around it.

### Streaming Internals — Throttled Delta Persistence (KNOWN, `client/streaming.ts`, `deltas.ts`)

When `saveStreamDeltas` is enabled (`index.ts:554`), `streamText` deltas are batched and written to `streamDeltas` rows on a **throttle of `throttleMs = 250` (default, `streaming.ts:160,239`)** — a delta row is flushed only when `Date.now() - latestWrite >= throttleMs` (`:301,373`), so the DB sees ~4 writes/sec, not one-per-token. Each delta row key is `${threadId}-${order}-${stepOrder}` (`deltas.ts:28`) with `start`/`end` chunk indices. The client `useThreadMessages`/`useStreamingUIMessages` hooks subscribe to `streamDeltas` and reassemble. On finish, `streamingMessages.state` flips to `{kind:"finished", endedAt, cleanupFnId}` and the deltas are vacuumed (a scheduled cleanup function), leaving the final `messages` row. A heartbeat (`lastHeartbeat`, `timeoutFnId`) detects stalled streams and aborts them (`{kind:"aborted", reason}`). **This is the durable-reactive streaming contract: throttled delta-rows + a state machine + scheduled vacuum** — the reason it survives crashes and serves multiple clients.

### Thread Handoff (KNOWN)

`threads.parentThreadIds: v.array(v.id("threads"))` (`schema.ts:26`) records thread lineage. One agent passing a thread to another = creating a child thread referencing the parent (or continuing the same `threadId` with a different agent's `instructions`) — context flows via the shared `messages` rows keyed by `threadId`, and `agentName` on each message row (`schema.ts:42`) records which agent produced it. So multi-agent in Convex is *shared-thread, agent-attributed messages* — not handoff-as-control-transfer; the reactive store IS the coordination medium.

**For Verso:** Convex Agent is the reactive-backend reference. Reimplementable extracts: (1) **Streaming via DB-rows-the-client-subscribes-to (`streamDeltas`), not SSE** — a token = an inserted `{streamId, start, end, parts}` row; the reactive layer pushes it. This is a fundamentally different streaming model from vLLM/SSE: it's durable (a crash mid-stream leaves the deltas in the DB for recovery) and multi-client (every subscriber sees it) for free. Verso's durable tier should consider delta-rows-as-stream over a reactive store rather than ephemeral SSE. (2) **The message schema with `(order, stepOrder)` + `tool: boolean` + a single status-tool-order index** is a clean, queryable agent-history model — Verso's typed memory should store messages as rows keyed by turn/step, not as an opaque blob. (3) **Hybrid retrieval = RRF(vector, text) with `k=10`, then ±neighbour expansion, then top-`limit`** is a concrete, copyable RAG-over-history algorithm with every constant exposed (`100` recent, `10` retrieved, `{before:2, after:1}`, threshold `0.0`). Verso's memory layer should adopt RRF fusion (not just cosine) and the neighbour-expansion trick. (4) **Tool-call-as-transaction** (`execute(ctx,...)` runs in the durable runtime, returns type-checked, can read/write the same store) is the tightest tool↔state coupling seen — Verso's durable tool execution should give tools a transactional context handle, not just a fire-and-forget callback. (5) **Per-dimension vector tables + denormalized composite filter fields** is a pragmatic workaround for fixed-dimension vector indexes — relevant if Verso ships a built-in vector memory. What Verso should note as a *constraint*: Convex hardcodes the durable path — there is no in-memory mode, every message and delta is a DB write. That's the same tradeoff as CF: durability for free, but no tactical hot path.

---

## VoltAgent

### What It Is

A batteries-included TS agent framework: declarative `Agent` (provider + tools + memory adapter + sub-agents), a separate **workflow engine** for suspendable multi-step automations, **supervisor/sub-agent hierarchies**, RAG retrievers, and a paid VoltOps observability console. Its explicit structural split — *agent loop* (single-agent tool-use) vs *workflow engine* (suspendable steps) — mirrors the tactical↔durable seam Verso is navigating. `@voltagent/core` holds both; storage/vector/embedding are pluggable adapters (libsql, postgres, supabase, cloudflare-d1, in-memory).

`[CORRECTION 2026-06-05]` The RE brief named the memory interface `IMemoryAdapter`; in current source the interface is **`StorageAdapter`** (`packages/core/src/memory/types.ts:397`). There is no `IMemoryAdapter` symbol.

### Supervisor ↔ Sub-Agent Wiring — `delegate_task` Tool (KNOWN, `agent/subagent/index.ts`)

A supervising agent is given `subAgents: SubAgentConfig[]` + an optional `supervisorConfig`. `SubAgentManager` (`subagent/index.ts:55`) wires them via a single auto-generated tool: **`delegate_task`** (`:766-769`), `"Delegate a task to one or more specialized agents"`. Its handler calls `handoffTask({task, targetAgents, context, parentSpan, conversationId})` (`:319`) which runs the chosen sub-agent(s) — `handoffToMultiple()` (`:710`) runs several in parallel under one shared `conversationId` (`:357,727`). So **the supervisor is a normal agent whose only special tool is `delegate_task`**; the LLM "coordinates" by calling it with target agent names. Sub-agents are unaware of each other (`generateSupervisorSystemMessage` guideline `:268` "Agents are not aware of each other's existence").

`generateSupervisorSystemMessage(baseInstructions, agentsMemory, config)` (`:236-310`) injects a `<specialized_agents>` block listing each sub-agent's name+purpose, a set of ~19 default supervisor guidelines (parallelism-first: *"contact MULTIPLE agents at the same time whenever possible"*; *"Do not mention the name of any agent"*; *"reuse that response"* from `<agents_memory>`), plus the base instructions. **Sub-agent stream events bubble to the supervisor via `fullStreamEventForwarding`** — the supervisor forwards only `["tool-call", "tool-result"]` event types by default (`:622,650`), filtered by `supervisorConfig.fullStreamEventForwarding.types`. This is event-forwarding-based multi-agent observability, not a shared state object.

### Workflow Suspend / Resume — The Snapshot Format (KNOWN, `workflow/types.ts`)

The workflow engine is the *durable* half. Suspension is driven by a `WorkflowSuspendController` (`suspend-controller.ts:26-57`): wraps an `AbortController`; `suspend(reason)` sets `suspended=true` and `abortController.abort({type:"suspended", reason})`. The running workflow observes the signal and unwinds to a checkpoint.

The **snapshot format** is `WorkflowSuspensionMetadata` (`types.ts:17-41`):
```ts
{
  suspendedAt: Date,
  reason?: string,
  suspendedStepIndex: number,           // which step paused
  lastEventSequence?: number,           // for event-stream resume
  suspendData?: SUSPEND_DATA,           // validated against suspendSchema
  checkpoint?: {
    stepExecutionState?: any,           // current step's partial state
    completedStepsData?: any[],         // results of finished steps (preserved)
    workflowState?: WorkflowStateStore,  // shared workflow state snapshot
    stepData?: Record<string, WorkflowCheckpointStepData>,  // for getStepData() after resume
    usage?: UsageInfo,                  // accumulated token usage to this point
  }
}
```
`resume(input?, {stepId?})` (`types.ts:161`) re-enters: by default at `suspendedStepIndex`, or at an explicit `stepId`, with `input` validated against the workflow's `resumeSchema`. **This is serialized-state checkpointing** (like Mastra's snapshot — see `researchfms/teardowns/MASTRA.md`) — distinct from CRIU (Trigger.dev) and from re-run-from-top (LangGraph): the workflow records *which step*, *completed step results*, *shared state*, and *partial current-step state*, then rehydrates them. It requires steps to be serializable but is portable across machines. A workflow can suspend → resume → suspend again (the result type is recursively resumable, `:141-161`).

### `StorageAdapter` — The Pluggable Memory Contract (KNOWN, `memory/types.ts:397-482`)

One interface, four concerns, implemented by libsql/postgres/supabase/d1/in-memory:
- **Messages:** `addMessage(s)(msg, userId, conversationId, ctx)`, `getMessages(userId, convId, opts) → UIMessage<{createdAt}>[]`, `clearMessages`, `deleteMessages(ids,...)` (atomic-if-possible, else clear+rehydrate, `:423`).
- **Conversations:** `createConversation`, `get/getConversations(resourceId)`, `getConversationsByUserId`, `queryConversations`, `countConversations`, `update/deleteConversation`; optional `saveConversationSteps`/`getConversationSteps` (`:449`).
- **Working memory** (a scratchpad string scoped to conversation/user, `:457-474`): `getWorkingMemory/setWorkingMemory/deleteWorkingMemory({conversationId?, userId?, scope: WorkingMemoryScope})` — a separate *agent-managed* memory string distinct from the message log.
- **Workflow state** (`:477-481`): `getWorkflowState(executionId)`, `setWorkflowState`, `updateWorkflowState`, `queryWorkflowRuns`, `getSuspendedWorkflowStates(workflowId)` — **the same StorageAdapter persists the suspension snapshots**, so a suspended workflow survives process restart and can be resumed from any worker that shares the adapter.

This is the unifying insight: **one storage interface backs both the agent's conversation memory AND the workflow's durable suspension snapshots.** Memory, working memory, and durable-execution checkpoints are all rows in the same pluggable adapter.

### Workflow Chain DSL — Typed Step Composition (KNOWN, `workflow/chain.ts`)

The workflow engine's authoring surface is a fluent chain (`createWorkflowChain({...}).andThen(...).andAgent(...)`, `chain.ts:71-111`). Step combinators (`chain.ts:29-42`): **`andThen({execute})`** (a plain function step), **`andAgent(task, agent, config)`** (`:157-224` — run an agent as a step, output validated against an `AgentOutputSchema`), **`andWhen({condition, step})`** (conditional), **`andAll([...])`** (parallel-all), **`andRace([...])`** (parallel-first-wins), **`andTap(...)`** (side-effect, doesn't alter data). Each step's output is typed and threaded into the next step's input (the chain accumulates a typed `DATA`). Any step can `suspend()` (via the `WorkflowSuspendController`), producing the snapshot above. So VoltAgent's durable half is a **typed, suspendable, parallel-capable step chain** where an *agent invocation is just one kind of step* (`andAgent`) — the agent-loop and the workflow-engine compose through this single combinator.

### Agent Hooks + Guardrails + Retriever (KNOWN, `agent/`)

The agent (single-agent) loop runs AI SDK `generateText`/`streamText` with `maxSteps` → `stopWhen` (same pattern as Convex/Think). Around it: **`AgentHooks`** (`agent/hooks.ts`) — `onStart`, `onEnd`, `onToolStart`, `onToolEnd`, `onToolError`, `onPrepareMessages` (mutate the message list before inference, `:542-585`); **guardrails** (`agent/guardrail.ts` + `streaming/guardrail-stream.ts`) — input/output validators including a streaming guardrail that can abort mid-stream; **`BaseRetriever`** (`retriever/retriever.ts`) — a RAG retriever injected as context. Everything is OpenTelemetry-instrumented (`AgentTraceContext`, span kinds). So VoltAgent's single-agent surface mirrors the others (hooks ≈ OpenAI guardrails + ElizaOS lifecycle), and the *distinctive* part remains the explicit agent-loop/workflow-engine split sharing one `StorageAdapter`.

**For Verso:** VoltAgent is the calibration point for "batteries-included" and it cleanly separates the two halves Verso is reconciling. Extracts: (1) **The agent-loop vs workflow-engine split is explicit and worth copying as a conceptual boundary** — single-agent tool-use is the tactical path; the workflow engine (suspendable, snapshotted, durable-state-backed) is the durable path; they share a memory adapter. Verso's seam can be exactly this: same memory backend, two execution modes. (2) **Supervisor = ordinary agent + one `delegate_task` tool** that can fan out to multiple sub-agents in parallel under a shared `conversationId`, with sub-agent `tool-call`/`tool-result` events forwarded up. This is a third multi-agent model (vs AgentKit's router, OpenAI's handoff): *coordination-by-tool-with-parallel-fanout*. Verso should support parallel sub-agent dispatch as a first-class tool, not force sequential routing. (3) **The suspension snapshot format** (`{suspendedStepIndex, completedStepsData, workflowState, stepData, usage}`) is a concrete serialized-checkpoint schema — Verso's durable mode should snapshot exactly these fields (which step, prior results, shared state, accumulated usage) so resume is deterministic and portable. (4) **One `StorageAdapter` for conversation memory + working memory + workflow snapshots** is the right consolidation — don't build three stores; build one interface with message/conversation/working-memory/workflow-state sections. (5) **Working memory as a separate scoped string** (distinct from the message log) is a useful primitive — an agent-owned scratchpad the model rewrites, not appended messages. What Verso can *improve*: VoltAgent's supervisor guidelines are a ~19-line hardcoded prompt; Verso should make the coordination prompt composable, and its event-forwarding filter (`["tool-call","tool-result"]`) configurable per-edge.

---

## ElizaOS (v2)

### What It Is

A plugin-first TS "agentic operating system" for deploying agents to messaging platforms (Discord, Telegram, Twitter, Slack) and Web3 chains. Three layers: `@elizaos/core` (the `AgentRuntime` + plugin model + LLM abstraction) → plugins (actions, providers, evaluators, services, models, routes, events) → projects. Its value for Verso is the **most elaborate open "pluggable everything" contract** in a TS agent framework, plus the **Provider→Action→Evaluator** triad that maps onto context-engineering / tool-execution / post-response-scoring.

### The Plugin Contract — "Pluggable Everything" (KNOWN, `types/plugin.ts:876`)

`interface Plugin` (`plugin.ts:876-965+`) is the kitchen-sink registration unit: `{name, description, mode?:"direct"|"remote", init?(config, runtime), dispose?, applyConfig?, config?, services?: ServiceClass[], componentTypes?, actions?: Action[], providers?: Provider[], evaluators?: RegisteredEvaluator[], responseHandlerEvaluators?, responseHandlerFieldEvaluators?, adapter?: AdapterFactory, models?: {...}, events?: PluginEvents, routes?: Route[], tests?, dependencies?: string[], testDependencies?: string[], priority?: number, schema?}`. Notable: a plugin can supply the **database adapter** (`adapter`, one per character, `:949`), **model handlers** (`models`, the LLM abstraction is itself pluggable), **HTTP routes**, **event handlers**, and run in `"remote"` mode where its surfaces are proxied across a wire envelope (`:883-890`). This is the contract Verso's "pluggable edges" must rival.

### Plugin Priority + Dependencies — DFS Topological Load Order (KNOWN, `plugin.ts:275-365`)

`resolvePluginDependencies(pluginMap)` (`plugin.ts:275`) is a depth-first topological sort with cycle detection: `visited`/`visiting` sets; `visit(name)` recurses into `[...plugin.dependencies, ...(testMode ? testDependencies : [])]` *first* (`:329-335`), then pushes the plugin to `resolutionOrder` (`:339`) — so **dependencies always load before dependents**. A name already in `visiting` is a cycle (logged + skipped, `:45`). `priority?: number` (`plugin.ts:964`) is a separate ordering knob used at the *handler* level (e.g. event handlers sorted `(b.priority||0) - (a.priority||0)`, `runtime.ts:4073`; evaluators default `priority: 100`, `:2842`). So two ordering systems: **dependencies → topological load order; priority → within-surface execution order.**

### Action — `validate` / `handler` / `examples` (KNOWN, `types/components.ts:268`)

`interface Action` (`components.ts:268-297+`): `{name, description, descriptionCompressed?, handler: Handler, validate: Validator, similes?: string[], examples?: ActionExample[][], priority?, tags?, parameters?: ActionParameter[], contexts?: AgentContext[], contextGate?, mode?: ActionMode}`. `validate(runtime, message, state) → boolean` decides if the action is *eligible* this turn; `handler(runtime, message, state, options, callback) → ActionResult` executes it. `examples: ActionExample[][]` is a 2-D array (conversation examples, each a turn sequence) shown to the model to improve action selection. A critical source note (`:404`): **`validate` is advisory and can be bypassed by native tool-calling**, so an action must re-check preconditions inside `handler`. Actions can also be *hooks* that fire at fixed pipeline positions (non-PLANNER `ActionMode`, `:423`) rather than LLM-selected. `contexts`/`contextGate` scope which actions the planner even considers (context-routing classifier).

### Provider — Context → Prompt String (KNOWN, `types/components.ts:532`)

`interface Provider` (`components.ts:532-594+`): `{name, description?, dynamic?, position?: number, private?, get: (runtime, message, state) => Promise<ProviderResult>, relevanceKeywords?, contexts?, alwaysInResponseState?, roleGate?, cacheStable?, cacheScope?}`. `ProviderResult` (`:515-527`) = `{text?: string, values?: Record<string, ProviderValue>, data?: ProviderDataRecord}`. **A Provider is a context-injector:** `get()` returns `text` (spliced into the LLM prompt), `values` (template variables), and `data` (structured, for other components). `position` orders providers in the composed context; `private: true` providers aren't auto-composed (called explicitly); `alwaysInResponseState: true` forces always-on inclusion (like FACTS / CURRENT_TIME, `:576-583`); `dynamic` providers are composed per-turn by the context-routing classifier based on `contexts`/`relevanceKeywords`. `composeState(message, [providerNames])` (`runtime.ts:3458`) runs the selected providers' `get()` and merges their results into the State the planner sees. **This is the worked context-engineering layer: pluggable, ordered, gated, cache-aware providers that each contribute a slice of prompt.**

### Evaluator — Post-Response, Writes Memory (KNOWN, `types/evaluator.ts:44`)

`interface Evaluator<TOutput, TPrepared>` (`evaluator.ts:44-58`): `{name, description, similes?, priority?, providers?: string[], schema: JSONSchema, modelType?, shouldRun(context) → Promise<boolean>, prepare?(context+state) → TPrepared, prompt(context) → string, parse?(output) → TOutput|null, processors?: EvaluatorProcessor[]}`. An Evaluator runs **after the agent responds**: `shouldRun()` gates it, `prepare()` builds inputs, `prompt()` produces an LLM prompt, `parse()` extracts structured output, and each `EvaluatorProcessor.process(context) → ActionResult` (`:36-42`, priority-ordered) acts on the parsed output — typically **writing to memory** (e.g. extracting facts to store, `runtime.createMemory()` / `addEmbeddingToMemory()`, `runtime.ts:7459,8284`). So the Evaluator is the reflection/learning hook: it observes the completed turn, runs its own LLM call against a schema, and persists what should be remembered. This is the direct parallel to Verso's evals/reliability layer — except ElizaOS ties it to memory-writing, not just scoring.

### The Triad as a Pipeline (INFERRED from interfaces + `composeState`)

A turn flows: **Providers** compose the context state (`composeState`) → the planner LLM selects **Actions** (validate-gated, examples-primed) and runs their handlers → after the response, **Evaluators** run (`shouldRun`-gated) and their processors write memory. Providers = input/context engineering; Actions = capability/tool execution; Evaluators = post-hoc reflection + memory write. All three are plugin-contributed and runtime-merged.

### Model Handlers — The LLM Is Itself Pluggable (KNOWN, `runtime.ts`, `plugin.ts:950`)

`Plugin.models` (`plugin.ts:950-955`) is a map `{[modelType]: (runtime, params) => Promise<result>}` — a plugin registers handlers for model *types* (`TEXT_LARGE`, `TEXT_SMALL`, `TEXT_EMBEDDING`, etc., `ModelType`). The runtime's `useModel(modelType, params)` (`runtime.ts:2580+`) resolves a handler via **`getModelFallbackChain(modelType)`** (`:2601`) — a chain so a request for `TEXT_LARGE` can fall back to a smaller model if no large handler is registered. `registerModel(modelType, handler, provider, priority)` (`:4049-4069`) stores handlers; when multiple plugins register the same type they're sorted by `priority` (`:4073`, highest first). Provider resolution also probes env prefixes `["OLLAMA_", "OPENAI_", "ANTHROPIC_", ""]` (`:2601`). **So the LLM call is not hardcoded — it's a plugin-supplied, type-keyed, priority-ordered, fallback-chained handler.** Embeddings use the same mechanism (`getModel(TEXT_EMBEDDING)`, `:2211`). This is the depth Verso's "pluggable model providers" needs: model handlers as first-class plugin surfaces with fallback + priority.

### Service Interface (KNOWN, `types/service.ts:140`)

`abstract class Service` (`service.ts:140-153`): `{static serviceType: string, abstract stop(): Promise<void>}` plus a `static start(runtime)` factory pattern. Services are long-lived singletons (DB connections, platform clients like Discord/Telegram, schedulers) registered by plugins and fetched via `runtime.getService(serviceType)`. Unlike actions/providers/evaluators (which fire per-turn), a service is stateful infrastructure that lives for the runtime's lifetime. A plugin's `runtime.getService` allowlist (`plugin.ts:717`) and `useModel` allowlist (`:719`) sandbox what a (remote) plugin can reach. This rounds out the surface: actions=verbs, providers=context, evaluators=reflection, services=infrastructure, models=LLM, adapter=DB, routes=HTTP, events=pubsub — eight orthogonal plugin contribution types.

**For Verso:** ElizaOS is the plugin-contract reference. Extracts: (1) **The Provider→Action→Evaluator triad is a clean three-phase agent turn** — context-compose, act, reflect-and-remember. Verso's context layer = Providers (pluggable, ordered by `position`, gated by relevance/contexts, cache-aware, returning `{text, values, data}`); Verso's reliability layer = Evaluators (post-response, schema'd LLM call, processors that write memory). This is more structured than bolting evals on as an afterthought. (2) **Two-axis plugin ordering — `dependencies` (DFS topological load order, cycle-detected) + `priority` (within-surface execution order)** — is the right model for "pluggable everything": deps decide *load* order, priority decides *run* order. Verso's plugin loader should do exactly this. (3) **The plugin surface list** (`actions, providers, evaluators, services, models, adapter, routes, events, componentTypes`) is the most complete enumeration of pluggable seams — note especially that the **LLM model handler and the DB adapter are themselves plugins**, which is the depth Verso's "pluggable model providers / memory backends" needs. (4) **`validate` is advisory, re-check in `handler`** is a hard-won lesson: with native tool-calling the model can bypass eligibility gates, so the handler must defend itself — Verso's tools must validate at execution, not just at selection. (5) **Provider `position` + `alwaysInResponseState` + `private` + `dynamic`** give fine control over context assembly (ordering, always-on signals, explicit-only, relevance-gated) — Verso's context engine should expose these knobs. (6) **`remote` plugin mode** (surfaces proxied over a wire envelope) is a pattern for distributing plugin execution — relevant to Verso's edge ambitions. What's ElizaOS-specific and *not* for Verso: the messaging-platform/Web3 service skew and the heavy context-routing-classifier machinery, which only pays off at 90+ plugins.

---

## Motia

### What It Is

A unified backend framework. `[CORRECTION 2026-06-05]` The RE brief (and most public descriptions) describe Motia as **"everything is a Step (a file with a config block + handler), type ∈ {event, api, cron, noop}, communicating via `emits`/`subscribes`."** That model is **gone** in the current repo. Motia has pivoted to a Rust execution engine (`engine/`, Cargo workspace) + multi-language SDKs (`sdk/packages/node|python|rust`), rebranded internally as **"iii"**. The new primitive is **a registered function + a trigger binding**, not a Step file. The classic Step config schema is no longer in source (only stale references survive in some docs). I document the *current* architecture, since that's what the source supports.

### The Current Primitive — `registerFunction` + `registerTrigger` (KNOWN, `sdk/packages/node/iii/src/`)

A worker process connects to the Rust engine over a **WebSocket** (`iii.ts:4` imports `ws`; `sendMessage(MessageType.InvokeFunction, ...)`) and registers two kinds of thing:
- **`registerFunction(id, handler)`** (`types.ts:91-124`) — `id` is namespaced like `"math::add"`; `handler: RemoteFunctionHandler<TInput, TOutput>` is the unit of execution. A function can also be registered as an `HttpInvocationConfig` (external Lambda/Worker) instead of a local handler.
- **`registerTriggerType<TConfig>(triggerType, {registerTrigger, unregisterTrigger})`** (`types.ts:186-189`) — defines a *source* of events (e.g. `cron`, `http`, `queue`, `state`). The handler's `registerTrigger({id, function_id, config})` wires the source to call `iii.trigger({function_id, payload})` when the event fires (`:174-178`). 
- **`registerTrigger({type, function_id, config})`** (docs/triggers) — binds one of your functions to an *existing* trigger type published by another worker: `{type:"http", function_id:"math::add", config:{api_path:"/math/add", http_method:"POST"}}`. **The publishing worker must be connected or registration fails** — trigger types are themselves provided by workers (iii-http, iii-cron, iii-queue, iii-state), so the event-routing fabric is itself plugin-supplied.

### Event Routing — `trigger()` + `TriggerAction` Dispatch Modes (KNOWN, `iii.ts:451`, `iii-types.ts:143`)

`trigger({function_id, payload, action?, timeoutMs?})` (`iii.ts:451`) is the universal invoke. The **`TriggerAction`** (`iii-types.ts:143`) selects the routing/durability mode — this is the closest analogue to the old `emits`/`subscribes`:
- **`{type:'void'}`** — fire-and-forget. `sendMessage(InvokeFunction, {function_id, data, action})` with **no `invocation_id`**, returns `undefined` immediately (`iii.ts:456-466`). 
- **default (request/response)** — generates `invocation_id = crypto.randomUUID()`, registers a pending-invocation map entry with a timeout (`invocationTimeoutMs`), awaits the engine's response message keyed by `invocation_id` (`iii.ts:469-505`). This is synchronous RPC through the engine.
- **`{type:'enqueue', queue: string}`** — routes through a named durable queue for async processing; the engine acknowledges the enqueue and returns an `EnqueueResult {receipt}` (`iii-types.ts:143,293-296`).

So **routing = the engine matching a `function_id` (or a trigger binding) to a registered handler, with the `TriggerAction` choosing sync-RPC vs fire-and-forget vs durable-queue.** The Rust engine (`engine/src/workers/configuration/trigger.rs`) holds the `ConfigurationTriggers` registry (`register_trigger`/`unregister_trigger`, per-id slots) and is the routing authority; SDKs are thin WebSocket clients.

### AI Step vs Regular Step (KNOWN — the thesis, now in its new form)

The original Motia thesis was "an AI agent Step is no different from any other Step." In the current model the equivalent is: **an AI agent is just a registered function whose handler happens to call an LLM.** There is no `AIStep` type, no agent-specific config, no special trigger. An agent function is invoked exactly like any other function (`trigger`/`registerTrigger`), gets the same observability (every function invocation is OpenTelemetry-traced — `iii.ts` imports `@iii-dev/observability`, `registerWorkerGauges`, `getTracer`, `SpanKind`), and communicates with other functions/agents only by triggering them. State is shared via the `state` trigger type (a function reacts to state changes) and explicit `iii.trigger` calls — not a shared in-memory context object. So multi-agent coordination in Motia = **agents emit events (trigger functions) and subscribe to events (register triggers), fully decoupled through the engine.**

### Shared State + Streams — Engine-Owned Primitives (KNOWN, `state.ts`, `stream.ts`)

`IState` (`state.ts:110-121`) is a scoped (namespaced) KV store owned by the engine, not the worker: `get<T>({scope, key})`, `set<T>({scope, key, value})`, `delete`, `list<T>({scope})`, and **`update<T>({scope, key, ...ops})`** — atomic update operations (`:120`). Because state lives in the engine, a `state` *trigger type* lets one function fire when another writes state — this is how Motia does reactive cross-function state without a shared object. `IStream<TData>` (`stream.ts:325-331`) is the engine-managed streaming channel: `get`/`set`/`delete` of stream data plus reader/writer channel refs (`createStreamChannel` returns `{writer, reader}`, `iii.ts:400`). So **state and streams are both engine services consumed over the WebSocket** — durable and shared across all workers, like CF's SQLite-per-DO but centralized in the engine.

### Conditional Triggers + TTL (KNOWN, `engine/src/workers/configuration/trigger.rs`)

The Rust `configuration` trigger worker (`trigger.rs`) shows the routing depth: a trigger carries an optional **`condition_function_id`** (`:47`) — before invoking the bound function, the engine can call a *condition function* to gate the dispatch (declarative conditional routing). Each configuration id keeps a **ref-count of registered triggers**; when it drops to zero AND `ttl_seconds > 0`, a delayed cleanup deletes the configuration entry and emits `configuration:deleted` (`:16-19`) — unless a new registration arrives before expiry (TTL renewal). So even the trigger registry has durable lifecycle semantics (ref-counting + TTL + cleanup events). This is the engine being the routing/lifecycle authority that thin SDKs lack.

**For Verso:** Motia is the loosely-coupled, event-routed extreme — the opposite of a shared-state agent loop. Extracts: (1) **The pivot itself is the lesson:** Motia abandoned the "Step file with config block" abstraction for "registered function + trigger binding + a routing engine." The config-block-per-file model didn't survive contact with a real multi-language, multi-worker runtime — a caution for Verso against over-investing in a file-as-primitive DSL. (2) **`TriggerAction` as the per-call durability selector** (`void` / sync-RPC / `enqueue`) is a clean idea: the *same* invoke API chooses fire-and-forget vs request-response vs durable-queue per call. Verso's tool/agent invocation could carry an analogous action selector instead of separate APIs for sync vs async vs durable. (3) **Trigger types are themselves plugins** (http/cron/queue/state are workers that publish trigger types others bind to) — a maximally-decoupled event fabric where even the event sources are pluggable. Relevant to Verso's edge layer if it wants agents to react to arbitrary external event sources without hardcoding them. (4) **Thin-SDK-over-a-routing-engine (WebSocket) with a central registry** is a deployment topology: the engine owns routing/queues/state, SDKs in any language are clients. If Verso ever goes polyglot, this client-server split (vs in-process framework) is the model. (5) **Every function invocation is OTEL-traced by default** — auto-observability as a property of the invoke path, not opt-in. What Verso should *reject*: full event-decoupling as the *default* for agent coordination loses the shared typed-state that AgentKit/LangGraph use for routing — Motia's model is great for backend fan-out, weaker for a tight ReAct loop that needs to see accumulated state. Verso's shared-state loop is the right default; event-routing is the escape hatch for cross-service fan-out.

---

## Cross-Framework Synthesis → Verso Positions

The eight peers cluster into **four coordination models** and **three durability models** Verso must position against.

### Multi-agent coordination — four models
| Model | Exemplar | Mechanism | When |
|---|---|---|---|
| **Router-between-agents** | Inngest AgentKit | `Router(state) → next agent`, code OR LLM, re-routes every iteration | Shared typed state drives dispatch; non-graph |
| **Handoff (transfer control)** | OpenAI Agents JS | `transfer_to_*` function tool → `setCurrentAgent` + re-loop | One agent active at a time, conversation carries over |
| **Subagent-as-tool (call & return)** | OpenAI `asTool`, VoltAgent `delegate_task` | tool handler runs nested agent, returns output; can fan out parallel | Supervisor keeps control, delegates bounded subtasks |
| **Event-routed (decoupled)** | Motia, ElizaOS services | emit/subscribe through an engine; no shared state | Cross-service fan-out, loose coupling |

Verso should make **router-between-agents the default** (closest to its non-graph philosophy), offer **handoff** and **subagent-as-tool** as explicit distinct primitives (don't conflate them — OpenAI keeps both), and treat **event-routing as the escape hatch** for cross-service work.

### Durability — three models
| Model | Exemplar | How resume works | Cost |
|---|---|---|---|
| **Replay-determinism** | Inngest AgentKit (steps) | Re-run the function; memoized steps skip | Requires deterministic execution |
| **Serialized-checkpoint** | LangGraph (channel snapshot), VoltAgent (step snapshot), Mastra | Rehydrate saved state at the suspension point | Requires serializable state |
| **Checkpoint-resume / process** | CF fibers (`stash`+`onFiberRecovered`), Trigger.dev (CRIU) | Restore last stash / process image, resume manually | No determinism req, but manual resume or container infra |

Verso's seam (tactical in-memory ↔ durable) should pick **serialized-checkpoint as the durable default** (LangGraph's channel-snapshot is the cleanest: small, queryable, portable), because it neither demands deterministic replay (AgentKit/Temporal) nor ties you to a runtime (CF DO / CRIU). The HITL primitive should unify resume + state-update + dynamic-route into one return value (LangGraph's `Command`), and the interrupt mechanic should be re-run-from-top with idempotent prefixes (LangGraph) rather than manual stash-resume (CF) — simpler for users.

### Typed state — the consensus
LangGraph's **per-field reducer channels** (LastValue=single-writer-overwrite, BinaryOperatorAggregate=fold) is the most principled typed-state model and beats AgentKit's silent Proxy-mutation for concurrent writes. Convex's **messages-as-rows with `(order, stepOrder)`** + RRF hybrid retrieval (`k=10`, ±neighbour expansion, 100 recent + 10 retrieved) is the most principled *memory* model. Verso should combine them: reducer-channel typed state for the run, row-structured searchable messages for cross-session memory, with a checkpointer (per-thread run state) distinct from a store (cross-thread memory) — the two-tier split every mature peer (LangGraph, OpenAI Sessions, Convex, VoltAgent) converges on.

### Reactive streaming — the outlier worth copying
Convex streams via **DB-delta-rows the client subscribes to** (`streamDeltas`), not SSE — durable (survives mid-stream crash), multi-client, recoverable. For Verso's durable tier this beats ephemeral SSE; for the tactical tier, SSE (vLLM-style, see `infra-serving`) is fine. CF's **`setState` = sync-write + reactive-broadcast** is the same idea at the state level. Verso's durable state setter should push to subscribers (source-excluded) like both.
