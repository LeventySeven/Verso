# Next top agentic INFRA startups RE

Source file: `core/17_NEXT_TOP_AGENTIC_INFRA_STARTUPS_RE.md` (2,558 lines, dated 2026-04-26)
Scope: 10 production agentic-infra companies — gateway, typed-prompt compiler, workflow engine, observability, evals, voice agents, async automation.

---

## core/17_NEXT_TOP_AGENTIC_INFRA_STARTUPS_RE.md

### Composite Architecture (the production stack)

- The right layering: `agent → gateway → model`, NOT `agent → OpenAI SDK`.
- Every model call needs: routing, retry, tracing, cost/token metadata, and before/after policy hooks.
- Full production stack ordered: Gateway → Guardrails → Router → Models → Normalizer → Trace → Eval → Deploy → Typed-agent-graph → Tools → State.
- Minimum 7 components: gateway, trace-store, eval-runner, typed-prompt-runtime, workflow-engine, voice-contract, async-agent-api.

---

### 1. Portkey Gateway — LLM provider traffic as a programmable control plane

**Agent loop / routing:**
- `strategy.mode` ∈ `["single", "fallback", "loadbalance", "conditional"]` — the four canonical routing modes.
- **Load balance**: weighted random selection. Missing weight defaults to 1. `randomWeight = Math.random() * totalWeight`. Iterates targets, subtracts weights.
- **Fallback**: iterates `targets` in order; stops on `response.ok` OR when `x-portkey-gateway-exception: true` header is present (gateway exceptions are NOT masked as provider failures). If `onStatusCodes` provided, fallback only continues when response status is in that list.
- **Conditional routing**: evaluates operators `$eq/$ne/$gt/$gte/$lt/$lte/$in/$nin/$regex/$and/$or` over context `{metadata, params, url}`. CRITICAL QUIRK: key resolution is TWO-LEVEL ONLY — e.g. `metadata.user_id`, `params.model`. Deeper paths silently fail.

**Retry handler (from `retryHandler.ts`):**
- Uses `async-retry` with `randomize: false`.
- Uses `AbortController` for per-request timeout.
- Timeout emits synthetic 408: `{"error":{"message":"Request exceeded the timeout sent in the request: <timeout>ms","type":"timeout_error","param":null,"code":null}}`.
- 429 with `followProviderRetry`: reads `retry-after` header family (`POSSIBLE_RETRY_STATUS_HEADERS`), converts seconds→ms; if retry-after exceeds `MAX_RETRY_LIMIT_MS` or remaining timeout, sets `retrySkipped=true` and bails cleanly.
- Connection timeout errors → synthetic 503. Unknown TypeErrors → synthetic 500.
- Retry result object: `{response, attempt, createdAt, skip}` — preserves `createdAt` for tracing/cost code.

**Config schema (`requestBody.ts` + Zod):**
```
strategy.mode: "single"|"loadbalance"|"fallback"|"conditional"
retry.attempts: number
retry.on_status_codes?: number[]
retry.use_retry_after_header?: boolean
cache.mode: "simple"|"semantic"
cache.max_age?: number
request_timeout?: number
targets?: config[]
```
Per-target fields: `provider`, `apiKey`, `virtualKey`, `weight`, `retry`, `overrideParams`, `urlToFetch`, `afterRequestHooks`, `beforeRequestHooks`, `defaultInputGuardrails`, `defaultOutputGuardrails`, `strictOpenAiCompliance`, `modelPricingConfig`.

**Plugins/guardrails:**
- Two hook types: `beforeRequestHook`, `afterRequestHook`.
- Guardrails return boolean verdict. Failure can fail the request OR return HTTP 246 (soft-fail status).
- Plugin manifest: id, description, functions, supported hooks, type `"guardrail"`, credentials.
- `conf.json` enables via `plugins_enabled` + credentials; `npm run build-plugins` generates index imports.

**Runtime / cache selection:**
- Node + `REDIS_CONNECTION_STRING` → `createCacheBackendsRedis`.
- `conf.cache === true` → `memoryCache()` middleware.
- OpenAI-compatible routes: `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/messages`, `/v1/responses`, `/v1/audio/*`, `/v1/images/*`, `/v1/files`, `/v1/batches`, `/v1/fine_tuning/jobs`.
- `notFound` → `{"message":"Not Found","ok":false}` 404. `onError` → `{status:"failure",message}` 500.

**Replica blueprint (canonical gateway call):**
```ts
async function gatewayCall(req, cfg, ctx) {
  const normalized = normalizeConfig(cfg);
  const target = await resolveTarget(normalized, req, ctx);
  const guardedReq = await runHooks("beforeRequestHook", req, target);
  const providerReq = transformToProviderRequest(guardedReq, target.provider);
  const raw = await retryRequest(providerReq.url, providerReq.init, target.retry);
  const normalizedResp = await normalizeProviderResponse(raw, target.provider);
  return runHooks("afterRequestHook", normalizedResp, target);
}
```

---

### 2. BAML / BoundaryML — Prompt strings compiled into typed functions

**Core primitive:**
```rust
function ChatAgent(message: Message[], tone: "happy"|"sad") -> StopTool | ReplyTool {
    client "openai/gpt-4o-mini"
    prompt #"
        Be a {{ tone }} bot.
        {{ ctx.output_format }}
        {% for m in message %}
        {{ _.role(m.role) }}
        {{ m.content }}
        {% endfor %}
    "#
}
```
- Agent loop outside BAML is a normal `while` loop calling BAML functions with accumulated state.
- Streaming first-class: `b.stream.ChatAgent(...)` — chunks are TYPED PARTIALS with optional fields.
- Static client strategies: retry, fallback, round-robin — all declared, not imperative.
- Works even when providers lack native tool calling.

**Compiler pipeline (from `baml_language/ARCHITECTURE.md`):**
```
Source → Lexer → Tokens → Parser → CST → AST
AST → HIR (names/scopes)
HIR → PPIR (stream type expansion, synthetic AST items)
PPIR → TIR (type inference/checking, no new AST nodes)
TIR → MIR (control-flow graph)
MIR → BexVM bytecode
```
- Salsa-powered incremental compilation. NOT a linear "copy and enrich" pipeline.
- Key invariant: downstream of AST there is NO concept of "LLM function" — they become regular functions with declarative metadata.
- Every BAML function compiles to THREE generated companions: `render_prompt`, `build_request`, `parse`.

**Structured output parser (from `bex_sap`):**
- `jsonish::parse(raw_string, Default::default(), true)` — handles JSON-like, markdown-wrapped JSON, multiple JSON objects, partial/streaming.
- `TyResolvedRef::coerce(&ctx, target_ty, &parsed)` — scored coercion with repair metadata.
- Flag scoring is ADDITIVE. Example penalty: `DefaultButHadUnparseableValue` scores +2. Incompleteness has NO penalty.
- Repair flags: `ObjectFromFixedJson`, `DefaultButHadUnparseableValue`, `ObjectToString`, `ObjectToPrimitive`, `InferedObject`, `DefaultFromInProgress`, `DefaultButHadValue`, string-to-int/bool/null/float conversions, `NoFields`, incomplete-streamed-value.

**Runtime VM (from `bex_vm/README.md` and `bex_engine/README.md`):**
- Stack-based bytecode interpreter. Inspired by CPython + Lox.
- `MAX_FRAMES = 256`.
- `VmExecState` variants: `Complete(Value)`, `ScheduleFuture(ObjectIndex)`, `Await(ObjectIndex)`, `Notify(WatchNotification)`.
- Heap object types: string, array, map, instance, variant, function, class, enum, media, **future**.
- GC: epoch-based. VMs register at call start; GC advances epoch; old-epoch VMs park at safepoints; resume with forwarded references.
- `BexEngine` owns heap, bytecode program, op context, env vars. `call_function(&self,...)` enables concurrency. BexEngine mediates between `BexVm` and `sys_types`; they never call each other directly.

**Replica blueprint (minimum BAML-lite):**
```python
class LLMFunction:
    name: str
    input_schema: dict
    output_schema: dict
    client: ClientStrategy
    prompt_template: str

    def render_prompt(self, args, ctx): return jinja_render(self.prompt_template, args | {"ctx": ctx})
    def build_request(self, rendered, client): return provider_adapter(client).to_request(rendered)
    def parse(self, raw_text):
        value = jsonish_parse(raw_text, allow_markdown=True)
        return coerce_to_schema(value, self.output_schema)
```
Must copy: function-as-prompt primitive, generated companion trio, stream partial type expansion, jsonish parser with repair metadata, coercion scoring, static client strategies.

---

### 3. Vellum Workflows SDK — Statically typed workflow graphs with pause/resume

**Core primitive:**
```python
class MyNode(BaseNode):
    class Outputs(BaseNode.Outputs):
        result: str
    def run(self): return self.Outputs(result="Hello, World!")

class MyWorkflow(BaseWorkflow):
    graph = MyNode
    class Outputs(BaseWorkflow.Outputs):
        result = MyNode.Outputs.result
```

**Graph runtime (from `graph.py`):**
- `Graph` fields: `_entrypoints`, `_edges`, `_terminals`, `_trigger_edges`.
- `Node >> Node` syntax via `__rshift__`. Static graph — no dynamic event bus.
- Trigger edges are DISTINCT from normal node-to-node edges.
- Parallelism and branches are explicit in graph construction.
- Empty-port nodes are terminal; cannot be connected onward.

**Workflow metaclass (from `workflows/base.py`):**
- Stable deterministic IDs from class names:
```python
workflow_class.__id__ = uuid4_from_hash(workflow_class.__qualname__)
workflow_class.__output_ids__ = {
    ref.name: uuid4_from_hash(f"{workflow_class.__id__}|id|{ref.name}")
    for ref in workflow_class.Outputs
}
```
This enables code/UI sync — same class name always produces same graph ID.

**Runner internals (from `runner.py`):**
- Init params: `workflow`, `inputs`, `state`, `entrypoint_nodes`, `external_inputs`, `previous_execution_id`, `cancel_signal`, `node_output_mocks`, `max_concurrency`, `timeout`, `init_execution_context`, `trigger`, `execution_id`, `event_max_size`.
- Cannot provide both `state` and `external_inputs`.
- `external_inputs` resumes at parent node for the external input descriptor.
- `previous_execution_id` uses configured resolvers + falls back to default state.
- Thread/queue model: `_workflow_event_outer_queue`, `_workflow_event_inner_queue`, `_concurrency_queue`, `_background_thread_queue`, `_active_nodes_by_execution_id`.
- `max_concurrency` limits active node count.
- Timeout thread emits workflow rejection: `"Workflow execution exceeded timeout of <seconds> seconds"`.

**Event stream (from `events/stream.py`):**
```python
class WorkflowEventGenerator:
    def __init__(self, event_generator, span_id): ...
    @property
    def span_id(self): return self._span_id
    def __iter__(self): return self
    def __next__(self): return next(self._event_generator)
```
Event stream exposes `span_id` as top-level metadata while remaining iterator-compatible.

**Remote deployment API:**
- `POST v1/workflow-deployments/{id}/execute-stream` (base: `predict.vellum.ai`).
- Body: `inputs`, `trigger`, `release_tag`, `external_id`, `metadata`, `previous_execution_id`.
- Response: line-delimited JSON, each non-empty line parsed as `WorkflowEvent`. Bad lines swallowed.
- HTTP errors: 400 `BadRequestError`, 404 `NotFoundError`, 500 `InternalServerError`.

**Evaluation constants (from `evaluations/constants.py`):**
```python
DEFAULT_POLLING_INTERVAL_MS = 500
DEFAULT_MAX_POLLING_DURATION_MS = 30 * 60 * 1000  # 30 minutes
```
- `wait_until_complete()` polls until state leaves `QUEUED` or `RUNNING`. Raises on timeout, `FAILED`, `CANCELLED`.

---

### 4. Langfuse — Every agent execution as a structured trace graph

**Storage split (from `docker-compose.yml`):**
- Postgres: transactional application state (metadata).
- ClickHouse: analytics/traces/events. URLs: `CLICKHOUSE_URL=http://clickhouse:8123`, migration: `clickhouse://clickhouse:9000`.
- Redis: queues/cache.
- S3/MinIO: event upload (`events/`), media (`media/`), batch export (`exports/`).

**Worker queue topology (from `worker/src/app.ts`):**
- Express worker API with helmet, cors, JSON middleware.
- Queues registered via `WorkerManager.register`:
  - `TraceUpsertQueue` (sharded), `CreateEvalQueue`, `DatasetRunItemUpsert`
  - `EvalExecutionQueue` (sharded), `LLMAsJudgeExecutionQueue` (sharded)
  - `CoreDataS3ExportQueue`, `MeteringDataPostgresExportQueue`
  - `TraceDelete`, `ScoreDelete`, `DatasetDelete`, `ProjectDelete`
  - `PostHogIntegrationQueue`, `MixpanelIntegrationQueue`, `BlobStorageIntegrationQueue`
  - `DataRetentionQueue`, `DeadLetterRetryQueue`
  - `OtelIngestionQueue`, `EventPropagationQueue`, `NotificationQueue`

**Tuned BullMQ constants (production tuning, not decoration):**
- Trace delete + eval execution: `maxStalledCount: 3`, `lockDuration: 60000`, `stalledInterval: 120000`.
- Metering export: max 1 per 30 seconds.
- Note: default BullMQ lock/stall settings caused too much lock-renewal/high-CPU sensitivity — these are production fixes.

**Minimal pipeline shape:**
```
ingest_trace → normalize_event → upsert_trace_clickhouse
             → propagate_event
             → maybe_create_eval_jobs
             → maybe_export_blob
             → dead_letter_on_failure
```

**Minimal tables:** projects, traces, observations, scores, datasets, dataset_items, dataset_run_items, prompts, prompt_versions, eval_jobs, llm_as_judge_runs.

---

### 5. Arize Phoenix — OTel/OpenInference trace substrate + streamed eval

**Server architecture (from `src/phoenix/server/app.py`):**
- FastAPI + Strawberry GraphQL + gRPC server + SQLAlchemy async DB.
- `BulkInserter` + DML event handler. Prometheus metric `SPAN_QUEUE_REJECTIONS`.
- OTLP span encode/decode.
- DataLoaders: annotations, datasets, experiments, spans, traces, token/cost, prompt versions, session traces.
- Daemons: `DbDiskUsageMonitor`, `ExperimentRunner`, `ExperimentSweeper`, `GenerativeModelStore`, `SpanCostCalculator`, `TraceDataSweeper`.

**GraphQL eval surface (from generated GraphQL):**
- `chatCompletionOverDataset` — subscribes to streamed experiment execution.
- Subscription chunk types: `TextChunk`, `ToolCallChunk`, `ChatCompletionSubscriptionExperiment`, `ChatCompletionSubscriptionResult`, `ChatCompletionSubscriptionError`, `EvaluationChunk`.
- Each result includes: span (id, tokenCountTotal, costSummary.total.cost, latencyMs, traceId), tool calls (id, function name, arguments), evaluations (name, label, score, annotator kind, explanation, metadata).
- Phoenix treats playground/dataset execution as STREAMED EXPERIMENT, not static eval batch.

**Integration coverage:** OpenAI Agents SDK, Claude Agent SDK, LangGraph, Vercel AI SDK, Mastra, CrewAI, LlamaIndex, DSPy, Pydantic AI, Autogen, Smolagents, MCP, Portkey — broad first-class support.

---

### 6. Braintrust — Evals as first-class CI/CD artifacts

**Canonical eval pattern:**
```ts
Eval("Say Hi Bot", { data, task, scores: [LevenshteinScorer] });
```

**Queue internals (from `js/src/queue.ts`):**
- `DEFAULT_QUEUE_SIZE = 15000`.
- Unbounded by default; bounded only when `enforceQueueSizeLimit(true)` called.
- CRITICAL: comment says "drops oldest" but implementation drops NEW items when bounded and full:
  ```ts
  if (items.length >= maxSize) dropped.push(item);
  ```
  Copy the implementation, not the comment.

**Instrumentation plugin (from `js/src/instrumentation/core/plugin.ts`):**
- `BasePlugin`: `enable()`/`disable()` idempotent. Subscribes via `iso.newTracingChannel`.
- WeakMap from event object to `{span, startTime}`.
- Non-streaming: start → log input/metadata; asyncEnd → log output/metrics, end span; error → log error, end span.
- Streaming: patches async iterable, records FIRST CHUNK TIME, aggregates chunks on `aggregateChunks`, logs output/metrics, ends span.
- Dataset dimensions: id, id+version, id+environment, id+snapshotName.
- Experiment invariants: must specify project/projectId; cannot open and update simultaneously.

---

### 7. Helicone — Gateway plus observability in the same request path

**Service topology (from `FULL_AGENT_LOOP.md`):**
```
Client → Gateway Worker (port 8789) → LLM Provider
             ↓
           Jawn (port 8585)
      /      |      \
Postgres  ClickHouse  MinIO
             ↓
           Web UI (port 3000)
```

**Worker types by port:**
| Port | Type | Use |
|------|------|-----|
| 8787 | `OPENAI_PROXY` | OpenAI-specific proxy |
| 8788 | `HELICONE_API` | Helicone API worker |
| 8789 | `GATEWAY_API` | Generic any-provider gateway |
| 8790 | `ANTHROPIC_PROXY` | Anthropic-specific proxy |
| 8793 | `AI_GATEWAY_API` | Unified routing with billing |

**Request headers:** `Helicone-Auth: Bearer <api-key>`, `Helicone-Target-Url: <provider-base-url>`, plus provider-native auth.

**Provider registry model (from `INTEGRATE_PROVIDER_TO_GATEWAY.md`):**
```ts
class DeepInfraProvider extends BaseProvider {
  readonly displayName = "DeepInfra";
  readonly baseUrl = "https://api.deepinfra.com/";
  readonly auth = "api-key" as const;
  buildUrl(): string { return `${this.baseUrl}v1/openai/chat/completions`; }
}
```
Model config includes: provider model ID, pricing by threshold (input/output cost-per-token, cache read/write multipliers), rate limits (rpm, tpm, tpd), context length, max completion tokens, supported parameters.

**Helicone vs Portkey distinction:**
- Portkey = gateway code path (routing/retry/hooks).
- Helicone = gateway + analytics ownership (async log to separate backend).

---

### 8. Vapi — Voice agent as configuration object

**Assistant contract (from `CreateAssistantDto.ts`):**
- Core runtime components: `transcriber`, `model`, `voice`, `firstMessage`, `firstMessageMode`, `voicemailDetection`, `analysisPlan`, `artifactPlan`, `startSpeakingPlan`, `stopSpeakingPlan`, `monitorPlan`, `hooks`, `compliancePlan`.
- `firstMessageMode` default: `assistant-speaks-first`. Mode `assistant-speaks-first-with-model-generated-message` generates opener from conversation state.
- `maxDurationSeconds` default: **600 seconds**.
- `modelOutputInMessagesEnabled` default: **false**.
- Server URL precedence: (1) assistant server URL → (2) phone number server URL → (3) org server URL.
- Observability currently supports Langfuse only.

**Call orchestration modes:**
1. single assistant
2. squad
3. workflow

**Tool contract (from `FunctionTool.ts`):**
- `async: true` → assistant moves forward without waiting for server result.
- Static `parameters` merged into request body (Liquid-templated).
- `rejectionPlan`: regex or Liquid conditions over recent messages.
- Tool webhook includes call, assistant, phone number objects + variables.
- Target URL precedence: tool URL → assistant URL → phoneNumber URL → org URL.

**Per-call overrides:** `AssistantOverrides` allows `"tools:append"` (safe append, not replace) and `variableValues` with LiquidJS syntax. Reserved default variable: `customer`.

**Voice agent state machine:**
```
call.created → first_message_mode → listen(STT) → endpoint/startSpeakingPlan
→ model turn → tool call? webhook sync/async
→ speak(TTS) → interruption? stopSpeakingPlan
→ loop until endCallPhrases/maxDuration/voicemail/transfer
→ artifactPlan + analysisPlan → server end-of-call-report
```

---

### 9. Retell — Voice agents as response engines + explicit state machines

**Agent creation constants (from `agent_create_params.py`):**
- `ambient_sound_volume`: range `[0,2]`, default 1.
- `backchannel_frequency`: range `[0,1]`, default 0.8.
- `begin_message_delay_ms`: valid `[0,5000]`.
- `end_call_after_silence_ms`: min 10000, default **600000 ms** (10 minutes).
- `interruption_sensitivity`: range `[0,1]`, default 1; 0 = never interrupted.
- IVR detection checks first **3 minutes**.
- `data_storage_retention_days`: 1 to 730; unset = retained forever.
- `webhook_timeout_ms`: configurable per agent.

**LLM / response engine (from `llm_create_params.py`):**
- `model_temperature` range `[0,1]`, default **0** (lower recommended for tool calling).
- `model_high_priority`: uses high-priority pool for lower/more consistent latency at higher cost.
- Text model defaults to `gpt-4.1` if unset.
- Models list (current): `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`, `gpt-5`, `gpt-5-mini`, `claude-4.5-sonnet`, `claude-4.6-sonnet`, `claude-4.5-haiku`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`.
- Speech-to-speech models: `gpt-realtime-1.5`, `gpt-realtime`, `gpt-realtime-mini`.

**State machine (CRITICAL):**
- `general_prompt` always appended to system prompt regardless of state.
- With states: system prompt = general_prompt + state.prompt; tools = general_tools + state_tools + transition_tools.
- State transition IS IMPLEMENTED AS A TOOL CALL: tool name = `transition_to_{destination_state_name}`.
- `StateEdge` has: `description` (when to transition), `destination_state_name`, `parameters` (JSON Schema object for extraction).
- `starting_state` required if states non-empty.

**RAG config:**
```python
class KBConfig:
    filter_score: float  # similarity threshold
    top_k: int           # max chunks
```

**MCP connection:**
```python
class Mcp:
    name: str
    url: str
    headers?: dict
    query_params?: dict
    timeout_ms?: int  # default 120000 ms
```

**Agentic warm transfer:** Retell has bridge transfer + cancel transfer as separate tool types. Secondary transfer agent talks, then bridges (original caller → transfer target, ends transfer agent) or cancels (returns original caller to main agent, ends transfer agent). This is real multi-agent voice workflow.

**Tool types:** end call, transfer call, check availability (Cal.com), book appointment (Cal.com), agent swap, press digit, send SMS, custom HTTP tool (GET/POST/PUT/PATCH/DELETE with response variable extraction via JSON paths), code tool, extract dynamic variable, bridge transfer, cancel transfer, MCP tool.

**Conversation flow (visual graph layer, `conversation_flow_create_params.py`):**
- Node types: conversation node, subagent node, end node, function node, code node.
- Edges: normal edges, always edges, skip-response edges. Transition conditions: prompt/equation/other variants.
- Separate from Retell LLM states — the higher-level visual orchestration layer.

---

### 10. Gumloop — Async automations exposed as HTTP jobs

**Flow API (from `GumloopClient.js` + docs):**
- Base URL: `https://api.gumloop.com/api/v1`.
- `runFlow(flowId, inputs, pollInterval=1000, timeout?)` → converts inputs to `[{input_name, value}]`, POST `/start_pipeline`, read `run_id`, poll `GET /get_pl_run?run_id=...`.
- Terminal states: `DONE` → return outputs; `FAILED`/`TERMINATING`/`TERMINATED` → throw joined log.
- Flow states: `STARTED`, `RUNNING`, `TERMINATED`, `FAILED`, `DONE`.

**Agent API contract (from official docs):**
```
POST /api/v1/start_agent
{ gummie_id, message, user_id, project_id, interaction_id? }
→ { interaction_id, status: "processing" }

GET /api/v1/agent_status/{interaction_id}?user_id=...&project_id=...
→ ASYNC_PROCESSING | COMPLETED | FAILED
```
- Continue conversation: pass previous `interaction_id` (must be terminal: `COMPLETED` or `FAILED`; `gummie_id` must match).
- On completion: `messages` (full conversation) + `response` (convenience final text).
- Message part types: text (`{id, type:"text", text}`), tool invocation (`{type:"tool_invocation", toolCallId, toolName, toolCallState, result:{args, result}}`), file part, error part.
- Polling recommendation: every 2–5 seconds; avoid more than 1/sec; timeout 5–10 min; exponential backoff for concurrent requests.

---

### Cross-System Patterns (directly from the file)

**Pattern 1 — Agents need a gateway before they need more prompts:**
Every model call needs: routing → retries → tracing → cost/token metadata → provider/model registry → before/after hooks.

**Pattern 2 — Observability is an event DATABASE, not logs:**
Separate ingest / trace+span storage / token+cost calculator / eval runner / prompt+dataset linkage / export+retention. Storage split: ClickHouse (analytics), Postgres (metadata), S3 (large payloads).

**Pattern 3 — Eval systems are dataset execution engines:**
All four (Braintrust, Phoenix, Langfuse, Vellum) converge on: versioned dataset → task/executable → experiment run → score/evaluation → trace link → run state polling/streaming.
```sql
experiments(id, project_id, dataset_id, version, created_at)
experiment_runs(id, experiment_id, dataset_item_id, repetition, status)
scores(id, run_id, name, label, score, explanation, metadata)
trace_links(run_id, trace_id, span_id)
```

**Pattern 4 — Typed prompt runtimes beat raw JSON mode:**
The missing middle between "prompt management" and "agent framework": compile → render_prompt → build_request → parse (with repair/coercion scoring) → stream partials with generated stream types.

**Pattern 5 — Voice agents are turn-taking state machines:**
Not "chat plus TTS". Requires: first-speaker mode, STT endpointing, denoising, interruption sensitivity, silence timeout, backchannel frequency, TTS fallback, voicemail/IVR detection, tool execution speech, post-call analysis, artifacts, server webhooks.

**Pattern 6 — Async agent APIs standardize on start/poll/continue:**
Two variants: async polling (start → id → poll → terminal) and streaming (start → line-delimited events → terminal). Both need: idempotent interaction ID, resumable polling, terminal-state continuation, sanitized message/tool-result schema.

---

## → Verso Implications

### Gateway layer (from Portkey/Helicone)

- **Verso's transport layer MUST be a gateway, not a thin SDK wrapper.** `agent → gateway → model` is the production primitive; direct SDK calls are for prototypes only. Build the gateway first.
- **Expose exactly four routing modes:** `single`, `fallback`, `loadbalance`, `conditional`. These cover all real production patterns. Do not invent a fifth mode without concrete evidence.
- **Implement weighted random load balance** with `Math.random() * totalWeight` — simple, tested, copyable as-is.
- **Gateway exceptions must NOT be masked as provider failures.** Use a flag (e.g. `x-verso-gateway-exception: true`) to stop fallback loops for config errors vs. transient provider errors.
- **Two-level conditional routing is acceptable for v1** — `metadata.user_id`, `params.model`. Deep path support can come later; document the limitation clearly.
- **Retry handler must produce `{response, attempt, createdAt, skip}`.** `createdAt` is load-bearing for tracing/cost attribution.
- **HTTP 246 soft-fail status** for guardrail failures that should not abort the request — copy this from Portkey. Hard-fail vs soft-fail hooks are a real product need.
- **Two cache backends:** in-memory default, Redis when `REDIS_CONNECTION_STRING` present. Don't complicate further at v1.
- **Synthetic error JSON for timeouts/connection errors:** standardize the error envelope early. Timeout → 408, connection → 503, unknown → 500. Makes client error handling uniform.
- **Provider model registry** (from Helicone): each provider entry = `{displayName, baseUrl, auth, pricingByThreshold, rateLimits{rpm,tpm,tpd}, contextLength, cacheMultipliers}`. This enables cost attribution without calling the provider's pricing API at runtime.

### Typed prompt runtime (from BAML)

- **Verso should treat a prompt as a compiled function, not a string.** The three companions (`render_prompt`, `build_request`, `parse`) are the minimum interface. Don't expose raw prompt strings to agent code.
- **Implement a jsonish parser with repair metadata and coercion scoring.** "JSON mode" is not enough — production LLMs return markdown-wrapped JSON, multiple objects, partial streams. Score-based coercion tolerates imperfect output without silent data loss.
- **Stream partials must be typed.** A streaming response should expose partial-filled schema objects, not raw token chunks. BAML's `PPIR` step synthesizes stream types from regular types — do this at definition time, not runtime.
- **`MAX_FRAMES = 256` for any VM-based execution** — a safe, well-tested ceiling for recursive/nested agent logic.
- **Async I/O modeled as `VmExecState`** variants (`Complete`, `ScheduleFuture`, `Await`, `Notify`) — this is cleaner than callback/promise soup for an embeddable agent runtime.
- **Static client strategies (retry/fallback/round-robin) belong in the prompt function definition**, not in the agent loop. This keeps agent code clean.

### Workflow engine (from Vellum)

- **`Node >> Node` graph syntax** is the right user-facing primitive for workflow definition — readable, declarative, statically analyzable.
- **Deterministic IDs from class names** (`uuid4_from_hash(workflow_class.__qualname__)`) — enables code/UI sync without a separate registry. Copy this trick exactly.
- **Trigger edges are distinct from data-flow edges.** Verso's graph model should encode this distinction to avoid conflating event triggers with data dependencies.
- **External input pause/resume** is a first-class workflow primitive (HITL). The runner must support: pause node execution → wait for external signal → resume with typed input → continue graph. Do not bolt this on later.
- **Four queue separation** in the runner: outer events, inner events, concurrency, background. This separation is the mechanism that makes `max_concurrency`, streaming, and cancellation work correctly.
- **Event stream MUST expose `span_id` as top-level metadata** on the stream object, not embedded in events. Makes tracing trivial.
- **Deployment API shape:** `POST .../execute-stream` with `release_tag` + `previous_execution_id` + line-delimited JSON response. This is the right API contract for versioned workflow deployments.
- **Evaluation polling constants:** 500ms interval, 30-minute max timeout — use these as Verso eval runner defaults.

### Observability / trace store (from Langfuse + Phoenix)

- **Storage split is NOT optional:** ClickHouse for span/trace analytics, Postgres for metadata, S3/MinIO for large payloads and export. A single Postgres will not scale for high-throughput tracing.
- **Every trace operation must go through a queue.** Direct writes to ClickHouse from the request path will cause head-of-line blocking. The topology: `ingest → normalize → upsert_clickhouse → propagate → maybe_eval → dead_letter`.
- **BullMQ tuning matters:** `maxStalledCount: 3`, `lockDuration: 60000`, `stalledInterval: 120000` are production-tuned constants for eval queues. Start with these, don't use BullMQ defaults.
- **Dead-letter queue is mandatory** for eval/trace pipelines. Failures must not be silently dropped.
- **SpanCostCalculator as a background daemon** — cost attribution should be async, not on the hot path.
- **Playground/eval surface should be STREAMED** (`EvaluationChunk` subscription in Phoenix) — not a batch job that returns when done. This is critical for interactive eval UX.
- **Prometheus metric for span queue rejections** (`SPAN_QUEUE_REJECTIONS`) — instrument this from day 1; it's the canary for observability backpressure.

### Eval runner (from Braintrust + Langfuse + Phoenix + Vellum)

- **`DEFAULT_QUEUE_SIZE = 15000`** for in-memory eval queue. Drop NEW items when full (not oldest — copy the implementation, not Braintrust's misleading comment).
- **First-chunk timing must be recorded separately from full-response timing** for streaming spans — this is the latency metric that matters for UX.
- **Dataset dimensions: id, id+version, id+environment, id+snapshot.** All four must be addressable independently.
- **Eval experiment invariants to enforce:** must specify project; cannot open and update simultaneously; dataset filter passes through to eval runs.
- **Diagnostics-channel plugin with WeakMap** is the right pattern for zero-overhead instrumentation — the WeakMap avoids retaining spans in memory after the event is done.

### Voice agent contract (from Vapi + Retell)

- **State machine transitions ARE tool calls.** Retell's approach (`transition_to_{state_name}` tool) is the right implementation pattern — it reuses the existing tool-calling mechanism for state routing, reducing special-case code.
- **`general_prompt + state.prompt` concatenation** — this is the minimal correct model for stateful voice agents. State narrows the prompt and tool set without full context replacement.
- **MCP as a first-class tool type** (Retell's `Mcp` class with `url`, `headers`, `query_params`, `timeout_ms=120000`). Verso should treat MCP tools identically to HTTP tools in the tool registry.
- **Hard constants for voice:** default temperature **0** for tool calling; max duration **600s** default; silence-end default **600000ms**; backchannel default **0.8**; interruption sensitivity default **1.0**.
- **Async vs sync tool dispatch** (Vapi): `async: true` lets the agent speak while the tool runs. This is essential for latency-sensitive voice turns.
- **Tool rejection plans** (regex/Liquid over recent messages) prevent bad tool calls from bad users. Build this into Verso's tool dispatch, not as a plugin.
- **`tools:append` override semantics** — per-call tool additions should APPEND to the base set, never replace it. Replacing causes subtle bugs when the base set has critical tools.
- **Post-call analysis and artifacts are separate concerns** — `analysisPlan` (LLM scoring) and `artifactPlan` (recording/transcript) should be configured independently.

### Async agent API (from Gumloop + Vellum)

- **Standardize on start/poll/continue** for long-running agent jobs. Two wire protocols: async polling (id + GET status) and streaming (line-delimited JSON events). Both are needed — expose both.
- **Interaction continuations require terminal-state gate.** Previous interaction must be COMPLETED or FAILED before accepting new message. Enforce at API level, not in docs.
- **Message part schema** (from Gumloop): `{type:"text"|"tool_invocation"|"file"|"error", ...}` — this discriminated union is clean and should be Verso's canonical agent message format.
- **Polling recommendations as documented constants:** poll every 2–5s, never faster than 1s, timeout 5–10 min, exponential backoff for concurrent requests. Bake these into SDK defaults, not just docs.
- **`run_id` / `interaction_id` must be idempotent** — the same ID should be resumable after network failure. Design the interaction table with this in mind from the start.

### Framework-level lessons

- **Verso's escape hatch for graphs (Vellum-style)** is validated: static graph with `>>` syntax, trigger edges, external input pause/resume. This is the legitimate graph case — not arbitrary DAG composition.
- **The "build the gateway first" rule** is confirmed by cross-system evidence: Phoenix, Langfuse, and Braintrust all assume a normalized trace payload that could only come from a gateway that attaches token/cost metadata before logging.
- **BAML's principle — typed functions, not prompt strings — should be Verso's default agent API.** Raw `messages: [...]` calls should be the escape hatch, not the primary interface.
- **Avoid the Langfuse/NIA bloat failure mode:** observability is valuable, but the eval/trace pipeline must be a SEPARATE service from the agent runtime. Don't let trace infrastructure complexity leak into the core loop.
- **The four eval platforms (Braintrust/Phoenix/Langfuse/Vellum) have already converged on the same data model.** Verso does not need to invent a new eval schema — copy the SQL model from Pattern 3 exactly.
