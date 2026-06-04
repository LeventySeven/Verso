# External Agentic Products RE

Source: `/Users/seventyleven/Desktop/researchfms/core/14_EXTERNAL_AGENTIC_PRODUCTS_RE.md`
Date of RE pass: 2026-04-26. All claims pinned to commit SHAs. Evidence labels used throughout: KNOWN (read from source), INFERRED (from structure/tests/docs), DESIGNED (replication engineering).

---

## 14_EXTERNAL_AGENTIC_PRODUCTS_RE.md

### Agent Loop Shape

**Dify (fc_agent_runner.py) — Function-calling loop:**
- `iteration_step=1`; `max_iteration_steps = min(app_config.agent.max_iteration, 99) + 1`
- Last iteration removes tools entirely (prevents infinite tool loops at the ceiling)
- Per-iteration: create/save agent thought → organize prompt messages → recalculate max tokens → invoke LLM with tools → stream chunks → extract tool calls → aggregate usage → append assistant message with tool calls into `_current_thoughts` → save thought/tool names/inputs/answer → publish `QueueAgentThoughtEvent` → invoke each tool via `ToolEngine.agent_invoke(...)` → append `ToolPromptMessage` → save observations/tool metadata → update prompt tools
- `AgentMaxIterationError` raised when max is reached with remaining tool calls
- Missing tool calls become error observations (not silently dropped)

**OpenHands V1 SDK — Event-sourced status machine:**
- Not a `while True` loop; statuses are first-class: `IDLE`, `RUNNING`, `PAUSED`, `WAITING_FOR_CONFIRMATION`, `FINISHED`, `ERROR`, `STUCK`, `DELETING`
- Terminal statuses: `FINISHED`, `ERROR`, `STUCK`
- Loop runs while status is in `{RUNNING}`; breaks on `PAUSED` or `STUCK`
- `max_iteration_per_run=500` default
- Stop hooks: when `FINISHED`, stop-hook feedback can inject `"[Stop hook feedback] ..."` as environment/user message and flip status back to `RUNNING` to continue
- `WAITING_FOR_CONFIRMATION` is converted to `RUNNING` just before each step (i.e., confirmation arrival resumes cleanly)
- `ConversationErrorEvent(code="MaxIterationsReached")` emitted on max; re-raises `ConversationRunError`

**Mastra — Agent loop as a resumable workflow (TypeScript):**
- Loop is literally a workflow graph: `llmExecutionStep` → `add-response-to-messagelist` → `map-tool-calls` → `foreach(toolCallStep)` → `llmMappingStep` → `backgroundTaskCheckStep` → `isTaskCompleteStep`
- Makes suspension/resume/approvals/background tools/scoring structurally impossible to forget
- Only new response messages added by tracking `existingResponseModelCount`
- Default tool concurrency: 10; forced to 1 when any tool requires approval/suspension
- Scorers are first-class loop participants (not post-processing): `isTaskCompleteStep` checks scorers and updates `stepResult.isContinued`
- Feedback from scorers injected as an assistant message with metadata `{mode: "stream", completionResult}`

**LangGraph — Pregel-style checkpointed graph:**
- `@entrypoint(checkpointer=...)` + `@task` functions; tasks cache inputs/outputs in checkpoints
- `interrupt()` for HITL pause; `Command(resume=...)` to continue
- `thread_id` in config: `{"configurable": {"thread_id": "..."}}`
- `StateGraph.compile()` → `Pregel`; stream modes include `"checkpoints"` with envelope types `"checkpoint"`, `"task"`, `"task_result"`
- `entrypoint.final(value=..., save=...)`: return one value, save a different (internal) state — crucial for compressed state with public-facing output

**Strands Agents SDK — Compact Python event loop:**
- Clean cycle: user input → model → tools → continue → final
- `event_loop_cycle_id = uuid.uuid4()` per cycle; emits `StartEvent`, `StartEventLoopEvent`
- If interrupt state active or latest message already has `toolUse`: skip model, set stop reason to `tool_use`
- `MaxTokensReachedException` on `max_tokens`; recovery via `recover_message_on_max_tokens_reached`
- Concurrent invocation guarded by `threading.Lock`; unsafe concurrent opt-in required
- Tool cancel: cancel signal generates error `toolResult` for every pending `toolUse` and sets stop reason to `"cancelled"`
- Interrupt stores context (tool use message + tool results), activates interrupt state, sets stop reason to `"interrupt"`

**LlamaIndex AgentWorkflow — Multi-agent handoff + scratchpad:**
- Default max iterations: 20; default early stopping method: `"force"` or `"generate"`
- `"generate"` mode: on max-iterations hit, makes a final LLM call to produce answer
- Scratchpad key: `"scratchpad"` (FunctionAgent); reasoning key: `"current_reasoning"` (ReActAgent)
- ReAct final answer strips `Answer:` prefix; writes reasoning transcript to memory; clears scratchpad
- `allow_parallel_tool_calls=True` for FunctionAgent
- Tool name `"handoff"` reserved; user tools prohibited from using it

**Pydantic AI — Typed graph nodes:**
- `BaseNode.run(ctx) -> BaseNode | End` — graph terminates on `End(data)`
- Return type hints are inspected; missing/invalid hints error at startup (not mid-run)
- `UsageLimits(request_limit, tool_calls_limit, tokens_limit)`; `check_before_tool_call` raises when next call would exceed

**Haystack Agent — Pipeline-component agent:**
- Default `max_agent_steps=100`; default `raise_on_tool_invocation_failure=False`
- Exit conditions: `"text"` (model stops without tool call) or specific tool names; tool exit only succeeds if that tool had no error
- No tool calls: increment counter and break (no extra LLM call)
- Confirmation strategies can rewrite tool call messages and history before execution

**CrewAI — Role/task orchestration:**
- `_invoke_loop`: uses native function calling if LLM supports it and original tools exist; falls back to ReAct text pattern
- Sequential fallback when `result_as_answer` or `max_usage_count` requires first-call handling
- Parallel tool calls: `ThreadPoolExecutor(max_workers=min(8, len(execution_plan)))`

---

### Exact Models (name + provider + role)

- Dify: `DifyPreparedLLM` wraps `ModelInstance`; carries provider, model name, params, stop sequences, output schema, token counts; invokes `ModelInstance.invoke_llm`
- Strands: default model is `BedrockModel` (AWS Bedrock) when unspecified; experimental bidi voice uses `amazon.nova-2-sonic-v1:0` via `InvokeModelWithBidirectionalStream`
- CrewAI unified memory defaults: `llm="gpt-4o-mini"` (OpenAI), storage=`"lancedb"`, OpenAI embedder by default
- Mastra: `Agent` requires a model; supports fallback model arrays with retries; `MastraModelOutput` includes provider, model id, version

---

### Full Tool Registry (names, params, returns)

**OpenHands V1 built-in tools:**
- `FinishTool`, `ThinkTool` (always included when `include_default_tools=True`)
- `InvokeSkillTool` auto-attached when AgentSkills-format skill exists
- Tool regex filter applies; duplicate names rejected
- MCP tools loaded via `ThreadPoolExecutor(max_workers=4)` with timeout `30`
- Tools may only be added, never removed

**Tool call normalization (OpenHands):**
- `parse_tool_call_arguments` sanitizes control characters for JSON
- Malformed JSON repaired where possible; trailing garbage after `}` or `]` removed
- Aliases: `bash`/`command`/`execute`/`execute_bash` → `terminal`; `str_replace`/`str_replace_editor` → `file_editor`
- Shell fallback supports only `find`, `ls`, `pwd`; `grep` fallback builds `grep -RIn --include ... -- pattern path`
- Typo normalization: `security_rort`, `securtiy_risk`, `security_riks` → `security_risk`
- File editor commands inferred from args: `old_str` → `str_replace`; `insert_line` → `insert`; `file_text` → `create`; `path` → `view`

**Pydantic AI built-in tools:**
- `WebSearchTool`, `XSearchTool`, `CodeExecutionTool`, `WebFetchTool`, `ImageGenerationTool`, `MemoryTool`, `MCPServerTool`, `FileSearchTool`
- Config-required: `FileSearchTool`, `MCPServerTool`, `MemoryTool`

**Haystack ToolInvoker:**
- Defaults: `raise_on_failure=True`, `convert_result_to_json_string=False`, `enable_streaming_callback_passthrough=False`, `max_workers=4`
- State injection: LLM args override state values; `inputs_from_state` mapping or parameter names; live `State` injectable when annotated as `State` or `Optional[State]`
- Tool output dicts merged into state via `outputs_to_state`

**LlamaIndex handoff tool:**
- `FunctionTool.from_defaults(async_fn=handoff, return_direct=True)` — handoff is a return-direct tool
- Validates target and `can_handoff_to`; stores `next_agent` and returns a prompt

**Mastra tool call step:**
- Active tool enforcement hides inactive tools; hidden calls fail with `ToolNotFoundError` with exact-name message
- Approval schema: `{approved: boolean}`; denial returns `"Tool call was not approved by the user"`
- Suspension emits `tool-call-approval` or `tool-call-suspended`; stores metadata, flushes messages, suspends with `__streamState`
- Agent tools receive all messages and thread/resource ids; non-agent tools receive input messages only
- Approval metadata stored in last assistant message metadata keyed by tool name; includes: tool call id, tool name, args, type, run id, resume schema, suspend payload

---

### Context Assembly / Compaction / Budgets

**OpenHands:**
- `prepare_llm_messages(state.events, condenser=self.condenser, llm=self.llm)` called every step
- Static system prompt (Jinja2 rendered) separate from dynamic context block — keeps static content in provider prompt cache
- Condenser: if returns condensation object, emits condensation event and returns without calling model
- Context window overflow → `CondensationRequest` emitted; malformed conversation/history → `CondensationRequest`
- `_prompt_cache_key` pinned to conversation id (OpenAI prompt cache)

**Dify:**
- `VariablePool` bootstrapped with env vars and user input mappings at workflow start
- Child graph execution can reuse or override parent `VariablePool`
- Token budget via `LLMQuotaLayer` attached to every graph run (not per-node)

**Pydantic AI:**
- Message model includes `CompactionPart` as first-class message part type

**Mastra:**
- Suspended stream state extracted from workflow snapshot context when payload includes `__streamState`
- Processor states persist across loop iterations in a map
- `flushMessagesBeforeSuspension` ensures thread exists and flushes pending messages before any suspension

**Strands:**
- Default conversation manager: `SlidingWindowConversationManager` unless model state is server-side
- Voice history byte caps: per-message `50 * 1024`, total `200 * 1024`

**LlamaIndex:**
- FunctionAgent: LLM response appended to scratchpad; tool results appended with role `"tool"` and `tool_call_id`; scratchpad flushed to memory after turn
- ReActAgent: reasoning key `"current_reasoning"` cleared after final answer; final answer writes reasoning transcript to durable memory

---

### Memory (what persists, TTLs, backend)

**CrewAI unified memory (most concrete constants in the codebase):**
- Root scope: `"/crew/{crew_name}"`; optional embedder override
- Backend: LanceDB; embedder: OpenAI by default; LLM: `gpt-4o-mini`
- Scoring formula:
  ```
  score = 0.5 * semantic_score
        + 0.3 * (0.5 ** (age_days / 30))    # recency, half-life 30 days
        + 0.2 * record.importance             # default importance 0.5
  ```
- Consolidation threshold: 0.85; consolidation limit: 5
- High confidence threshold: 0.8; low confidence threshold: 0.5
- Complex query threshold: 0.7; exploration budget: 1
- Query analysis threshold: 200 (class) / 250 (config)
- Recall oversample factor: 2; batch dedup threshold: 0.98
- Recall: oversamples `limit * 2`; thread pool max 4; long queries use up to 3 distilled queries; candidate scopes capped at 20
- Deep exploration: extract top 5 results, track missing gaps, re-search, synthesize

**LangGraph:**
- Checkpointer keyed by `thread_id`; `previous` holds last final value for same thread
- Task outputs cached in checkpoint (input hash + output for idempotent retry)

**OpenHands:**
- `EventLog` + `FIFOLock` + autosave; events written as JSON files with cache pages; cache size 25
- 1 MB event warning; secrets replaced except top-level protected fields
- `activated_knowledge_skills` and `invoked_skills` tracked in `ConversationState`

**LlamaIndex:**
- Default memory: `ChatMemoryBuffer.from_defaults(llm=...)` per agent
- Scratchpad (within turn) separate from durable memory (persists across turns)

**Mastra:**
- Workflow snapshots for suspension/resume (only persisted when suspended, not on every step)
- Processor states map persists across loop iterations within a single run

---

### System Prompts (verbatim/near-verbatim)

**OpenHands:**
- Static system prompt rendered from Jinja2 template (`system_prompt.j2`); kept separate from dynamic context for prompt caching
- Security policy rendered from `security_policy.j2`
- Dynamic context: separate block, injected each turn
- Agent context can append knowledge-skill suffix

**Mastra routing agent:**
- Prompt built from: available agents, workflows, tools, schemas, and instructions
- Router outputs JSON with `selectionReason` and `finalResult`
- Router may only pick available agents/workflows/tools
- User sees only `finalResult`; `selectionReason` is internal
- Routing excludes memory processors but keeps user-configured processors

**Dify agent node:**
- Plugin agent strategy defines the actual prompt structure; AgentNode resolves provider/name and builds params from variable pool + node data + strategy definitions

**LlamaIndex:**
- `setup_agent` prepends system prompt; injects state into last text block once; emits `AgentSetup`
- State prompt: injected once per setup, not per turn

---

### Error Handling Paths

**OpenHands:**
- Function-call validation errors → user `MessageEvent` with error text (model retries with correction)
- Reasoning-only or empty response → corrective nudge injected: runtime tells model the last response lacked a function call or message
- Context overflow → `CondensationRequest` (not a crash)
- Max iterations → `ConversationErrorEvent(code="MaxIterationsReached")`; raises `ConversationRunError`
- Tool exception → `AgentErrorEvent`

**Strands:**
- `AfterModelCallEvent` can trigger retry; max-token recovery explicit
- Cancel signal generates error `toolResult` for every pending `toolUse`
- Retry: `ModelRetryStrategy(max_attempts=6, initial_delay=4, max_delay=240)` (also event loop constants: `MAX_ATTEMPTS=6`, `INITIAL_DELAY=4`, `MAX_DELAY=240`)
- `TripWire` exception: re-thrown, not retried; error raised only after all fallback models exhausted

**Dify:**
- Unknown exceptions → `GraphRunFailedEvent`
- Structured output parse failure → `OutputParserError`
- Max iterations with remaining tool calls → `AgentMaxIterationError`

**Mastra:**
- Fallback models tried sequentially; `TripWire` not retried
- Error chunks set a deferred error so error processors can intercept
- If approval evaluation errors → approval is required (fail-safe)
- Tool not found error when active-tool enforcement hides a called tool

**CrewAI:**
- Max usage: error message says "tool reached usage limit" and instructs model to use alternatives
- Parser exceptions, context length, unknown errors all caught in `_invoke_loop`
- Background memory saves drained in `finally` block

**Haystack:**
- `raise_on_tool_invocation_failure=False` at agent level by default; tool invoker default `raise_on_failure=True`
- Exit condition "tool exit" only succeeds if the tool had no error

**LlamaIndex ReActAgent:**
- Parser errors produce retry messages (re-fed to model)

---

### Exact Constants

| Framework | Constant | Value |
|-----------|----------|-------|
| Dify | `WORKFLOW_CALL_MAX_DEPTH` | config-driven |
| Dify | `WORKFLOW_MAX_EXECUTION_STEPS` | config-driven |
| Dify | `WORKFLOW_MAX_EXECUTION_TIME` | config-driven |
| Dify | `GRAPH_ENGINE_MIN_WORKERS` | config-driven |
| Dify | `GRAPH_ENGINE_MAX_WORKERS` | config-driven |
| Dify | `GRAPH_ENGINE_SCALE_UP_THRESHOLD` | config-driven |
| Dify | `GRAPH_ENGINE_SCALE_DOWN_IDLE_TIME` | config-driven |
| Dify | `max_iteration` | `min(app_config.agent.max_iteration, 99) + 1` |
| OpenHands | `max_iteration_per_run` | 500 (default) |
| OpenHands | `MCP tool creation timeout` | 30 s |
| OpenHands | `ThreadPoolExecutor max_workers` (tool/MCP init) | 4 |
| OpenHands | Stuck detector window | 20 recent events after last user message |
| OpenHands | Stuck: repeated action/observation threshold | 4 |
| OpenHands | Stuck: action/error loop threshold | 3 |
| OpenHands | Stuck: monologue threshold | 3 |
| OpenHands | Stuck: alternating pattern threshold | 6 |
| OpenHands | `tool_concurrency_limit` default | 1 |
| OpenHands | Tag max length | 256 chars |
| OpenHands | Event cache size | 25 pages |
| OpenHands | Event 1 MB warning | 1 MB |
| Strands | `max_attempts` | 6 |
| Strands | `initial_delay` | 4 s |
| Strands | `max_delay` | 240 s |
| Strands | Voice per-message byte cap | 50 * 1024 |
| Strands | Voice total byte cap | 200 * 1024 |
| Mastra | Default tool concurrency | 10 (forced to 1 on approval) |
| Mastra | Completion timeout default | 600000 ms (10 min) |
| Mastra | Scorer passes threshold | `score === 1` |
| Mastra | Routing network default max iterations | 1 (unless caller passes max steps) |
| LlamaIndex | Default max iterations | 20 |
| Haystack | Default `max_agent_steps` | 100 |
| Haystack | ToolInvoker `max_workers` | 4 |
| CrewAI | Memory `llm` | `gpt-4o-mini` |
| CrewAI | Memory semantic weight | 0.5 |
| CrewAI | Memory recency weight | 0.3 |
| CrewAI | Memory importance weight | 0.2 |
| CrewAI | Memory recency half-life | 30 days |
| CrewAI | Memory consolidation threshold | 0.85 |
| CrewAI | Memory consolidation limit | 5 |
| CrewAI | Memory default importance | 0.5 |
| CrewAI | Memory high confidence threshold | 0.8 |
| CrewAI | Memory low confidence threshold | 0.5 |
| CrewAI | Memory complex query threshold | 0.7 |
| CrewAI | Memory recall oversample factor | 2 |
| CrewAI | Memory batch dedup threshold | 0.98 |
| CrewAI | Memory candidate scopes cap | 20 |
| CrewAI | Memory thread pool max | 4 |
| CrewAI | Deep exploration top results | 5 |
| CrewAI | Distilled queries (long) | up to 3 |
| CrewAI | Parallel tool calls max | `min(8, len(execution_plan))` |

---

### Multi-Agent Coordination

**LlamaIndex handoff pattern:**
- `handoff` is a return-direct tool (`FunctionTool` with `return_direct=True`)
- Validates target + `can_handoff_to` before switch; stores `next_agent` in context
- Root agent required for multi-agent setup; non-default agents require non-default name and description
- `ctx.collect_events` aggregates tool results including handoff

**Mastra routing network:**
- Routing agent prompt built from available agents/workflows/tools/schemas/instructions
- Router outputs `{selectionReason, finalResult}`; user sees only `finalResult`
- Sub-agent config derived from parent so parent can run sub-agent as background task

**CrewAI hierarchical process:**
- Auto manager generated with i18n role/goal/backstory; gets `AgentTools(agents=self.agents).tools()`; `allow_delegation=True`
- Manager cannot be in agents list; requires `manager_llm` or `manager_agent`
- Hierarchical + sequential process runners

**OpenHands:**
- `AgentDelegateAction` in legacy app repo; event log subscribed to by `AGENT_CONTROLLER`, `RESOLVER`, `SERVER`, `RUNTIME`, `MEMORY`, `MAIN`, `TEST`

**Microsoft AG-UI:**
- `AgentFrameworkWorkflow` stores workflow by thread id in `_workflow_by_thread: dict[str, Workflow]`
- Direct `AGUIChatClient` sends tool definitions only — client tools are NOT auto-executed
- Agent wrapper + middleware intercepts and executes client tools locally
- Interrupt card: event name `"WorkflowInterruptEvent"`

---

### Streaming Protocol

**Dify:**
- `StreamChunkEvent(selector=[node_id, "text"])` for text accumulation
- `StreamCompletedEvent(NodeRunResult(...))` on stream end
- `AgentLogEvent` for tool logs (deduped by log id, enriched with icon metadata)
- TEXT / JSON / LINK / VARIABLE / FILE / BLOB / IMAGE all typed in `ToolInvokeMessage` stream
- Final outputs: text, usage, files, JSON, variables, tool info, agent log metadata, inputs, LLM usage

**Mastra:**
- Typed stream chunks; tool-call input streaming hooks: `onInputStart`, `onInputDelta`, `onInputAvailable`
- Background task chunks emit progress/tool-result/tool-error
- `onChunk` only for: text, reasoning, source, tool-call, input-streaming, and raw (gated) chunks
- Abort signal checked on each chunk

**Strands stream normalization (before loop logic sees anything):**
- Blank assistant text around `toolUse` removed
- Invalid tool names replaced with `INVALID_TOOL_NAME`
- Tool input JSON parsed at content block stop; invalid JSON becomes `{}`
- Message stop overrides `end_turn` → `tool_use` if content contains `toolUse`

**Microsoft AG-UI events:**
- `TextMessageEndEvent`, `ToolCallArgsEvent`, `ToolCallEndEvent`, `ToolCallStartEvent`

**LlamaIndex:**
- Events: `AgentInput`, `AgentSetup`, `AgentStream`, `AgentStreamStructuredOutput`, `AgentOutput`, `ToolCall`, `ToolCallResult`, `AgentWorkflowStartEvent`

---

### HITL / Approvals

**LangGraph:** `interrupt()` + `Command(resume=...)` — cleanest primitive  
**OpenHands:** `WAITING_FOR_CONFIRMATION` as a first-class status; security analyzer predicts risk level; `confirmation_policy` in state  
**Mastra:** suspend workflow with `resumeLabel=toolCallId`; persist `__streamState`; `flushMessagesBeforeSuspension`; `resume(toolCallId, {approved: true|false})`  
**Pydantic AI:** deferred tool requests split into approvals and calls as two separate collections  
**Microsoft AG-UI:** `"WorkflowInterruptEvent"` card event  

---

### Observability / Safety

**Dify:**
- `ObservabilityLayer` attached when OTel enabled; spans on every graph/node/tool/model event
- `LLMQuotaLayer` as a graph layer (not per-node)
- SSRF proxy mandatory for HTTP request nodes
- Code limits: `CODE_MAX_STRING_LENGTH`, `CODE_MAX_NUMBER`, `CODE_MIN_NUMBER`, `CODE_MAX_PRECISION`, `CODE_MAX_DEPTH`, array/object length limits

**OpenHands:**
- Security analyzer analyzes tool risks; if absent risk is `unknown`
- `blocked_actions` and `blocked_messages` in state
- Secrets replaced in event log except top-level protected fields

**Microsoft:**
- Purview policy middleware can block agents and chat clients (governance as middleware, not output filter)

**Strands:**
- Model span, `BeforeModelCallEvent`, `AfterModelCallEvent`; usage metrics collected per cycle

---

### Session Repair

**Strands `RepositorySessionManager`:**
- Repairs histories by removing leading orphan `toolResult` messages
- Inserts missing `toolResult` for orphaned `toolUse` ids
- (An underrated production feature — broken conversation histories are common)

---

### Cross-Product Composite Architecture (DESIGNED)

```
HTTP/SSE API
  -> Run Router
  -> Conversation/Event Store
  -> Graph or Agent Runtime
  -> Model Gateway
  -> Tool Executor Pool
  -> Memory Service
  -> Approval/Suspension Service
  -> Scorer/Eval Service
  -> Event Stream back to client
```

Storage layers:
- **Postgres**: conversations, graph definitions, workflow runs, event logs, tool calls, approvals, scorer results, checkpoints
- **Redis Streams**: command channels, cancel/pause/resume, hot event fanout; key shape `workflow:{task_id}:commands`
- **Object store**: files, screenshots, tool artifacts, trace attachments
- **Vector store**: long-term memory (pgvector for simple deployments; LanceDB for CrewAI-style scored memory)

10 runtime principles extracted from cross-product analysis:
1. Every run has a `thread_id`
2. Every state transition emits an event
3. Every tool call has a stable id
4. Every approval/suspension has a `resume_label`
5. Model streams are normalized before loop logic
6. Tool results are appended as observations/messages, not hidden side effects
7. Max iterations, max steps, quota, timeout, and scorer stop conditions are independent
8. Static prompts and dynamic context are separated for prompt caching
9. Context overflow emits a condensation request, not a crash
10. Stuck detection runs after the latest user message only

---

### Anti-Patterns (confirmed by multi-framework RE)

- Hidden state in a single in-memory chat array
- Tool execution without stable tool call ids
- Human approval as an exception path (vs. first-class status)
- Parallel tool execution without resource locks when tools mutate shared state
- RAG as a replacement for agent memory (RAG retrieves documents; memory stores run-specific facts/decisions)
- Model streaming directly into business logic before normalization
- Max-iteration checks without stuck detection
- Client tool definitions that imply server execution (AG-UI makes this distinction explicit)
- One giant manager prompt for every product (runtime state machines matter more than role text)

---

## → Verso Implications

**Loop design:**
- Verso's core loop MUST be a state machine, not a `while True`. Adopt OpenHands status enum verbatim: `IDLE`, `RUNNING`, `PAUSED`, `WAITING_FOR_CONFIRMATION`, `FINISHED`, `ERROR`, `STUCK`. These statuses are the API contract between the loop and every external consumer.
- Implement `max_iterations=500` as the default ceiling; lower limits (e.g., 20 for lightweight agents, 100 for pipelines) as named presets. Always enforce, never skip.
- Implement Dify's last-iteration tool removal: `max_steps = min(user_limit, 99) + 1`; remove all tools on final step to force model to respond with text.

**Event sourcing:**
- All state must be rebuildable from an append-only event log. No hidden mutable transcript. Adopt OpenHands schema: `agent_runs` + `agent_events(run_id, seq, event_type, source, payload)`. `seq` is monotonic within a run — enables replay and audit.
- Pin OpenAI prompt cache key to `conversation_id` (OpenHands does this explicitly). Makes prompt caching reliable across turns without any special handling.

**Tool normalization:**
- Implement a stream normalizer that runs BEFORE the loop sees any provider output. Copy Strands: remove blank text around `toolUse`, replace invalid tool names with `INVALID_TOOL_NAME`, parse JSON at content block stop, coerce `end_turn` to `tool_use` when content contains tool use. Providers emit quirky streams; the loop should never know.
- Implement argument repair: sanitize control characters, fix malformed JSON, remove trailing garbage. Copy OpenHands alias normalization table (bash/command/execute → terminal, etc.) as a first-class layer.

**HITL / Approvals:**
- Approval is a first-class status (`WAITING_FOR_CONFIRMATION`), not an exception or callback. Resume must be keyed by `tool_call_id` with a `resume_label`. Never require the client to know which tool was pending — only the `resume_label` matters.
- Force tool concurrency to 1 whenever any tool in the current call set requires approval (Mastra rule). Parallel HITL is a correctness trap.
- Split deferred tool requests into approvals-list and calls-list (Pydantic AI). Verso's approval API surface: `resume(run_id, resume_label, {approved: bool})`.

**Stuck detection:**
- Ship stuck detection before shipping planning. Scan last 20 events after latest user message. Thresholds from OpenHands: repeated action/observation=4, action/error loop=3, monologue=3, alternating pattern=6. Emit `stuck_detected` event; set status to `STUCK`. Never silently loop.
- Add corrective nudge (OpenHands): reasoning-only or empty model responses get a user message telling the model the last response lacked a function call or text output. Do not retry silently.

**Retry / resilience:**
- Default retry: `max_attempts=6`, `initial_delay=4s`, `max_delay=240s` (Strands constants). These are battle-tested; do not invent new ones.
- Fallback models as first-class config (Mastra): ordered list, tried sequentially. Re-throw `TripWire`-class exceptions immediately without retry.
- Implement session repair (Strands): remove leading orphan `toolResult`, insert missing `toolResult` for orphaned `toolUse` ids. This is cheap and prevents confusing model behavior on resumed sessions.

**Memory:**
- Adopt CrewAI's scoring formula as Verso's default long-term memory scoring: `0.5*semantic + 0.3*recency_decay + 0.2*importance`. Constants are empirically tuned; start here.
- Keep scratchpad (within-turn) separate from durable memory (across-turns). LlamaIndex makes this distinction explicit and it maps cleanly to context window vs. vector store.
- Static system prompt and dynamic context are separate string fields (not concatenated). Dynamic context is the only part that changes per turn — this is what goes in the prompt cache's non-cached slot.

**Scorer-driven termination:**
- Scorers are loop participants, not post-processing. Verso should have a `ScorerService` called at `isTaskComplete` that can return `{complete: bool, feedback: string}`. Feedback is injected as an assistant message so the model can self-correct. A scorer passes only when `score === 1` (Mastra threshold).

**MCP toolsets:**
- Treat MCP as a cached toolset with invalidation on `ToolListChangedNotification` (Pydantic AI). Never load MCP tools fresh on every turn.

**Workflow graph (optional escape hatch):**
- When the product needs a no-code/low-code builder, copy Dify's architecture: `VariablePool` + `GraphRuntimeState` + node factory + graph layers (`ExecutionLimitsLayer`, `LLMQuotaLayer`, `ObservabilityLayer`). Node types: START, LLM, TOOL, HTTP_REQUEST, CONDITION, CODE, AGENT, END. Store graph definitions as Postgres JSONB; events in append-only Postgres table; command channels as Redis Streams.
- Graph layers are the correct place for quota and limits — not inside individual nodes.

**Multi-agent routing:**
- Handoff is a return-direct tool call, not a special protocol (LlamaIndex). Verso's multi-agent handoff: `handoff(target_agent_name)` as a registered tool; on call, store `next_agent`, emit `HandoffEvent`, swap active agent.
- Non-root agents MUST have non-default name and description — the router cannot choose between anonymous agents.
- Routing agent prompt includes: available agents, workflows, tools, schemas, instructions. Router output: `{selectionReason, finalResult}`. User sees only `finalResult`.

**Observability:**
- OTel span id on every model call, tool call, and node execution. Use `trace_id` and `span_id` columns in `agent_events` table. Dify's `ObservabilityLayer` is the reference design.
- Event types to emit: `user_message`, `assistant_message`, `tool_call_start`, `tool_call_result`, `tool_approval_required`, `condensation_request`, `stuck_detected`, `max_iterations_reached`, `agent_handoff`, `scorer_feedback`, `session_repaired`.

**Security:**
- SSRF proxy is mandatory for any HTTP tool exposed in a workflow (Dify rule). This is not optional hardening — it is the safety boundary for arbitrary HTTP tools.
- Security analyzer as optional middleware that predicts tool risk level; if absent, risk is `unknown`. Approval policy acts on risk level.
- Governance (e.g., PII policy) should be middleware around the model/tool layer, not a late output filter (Microsoft Purview pattern).

**The core thesis validated by 10 frameworks:**
> A real agentic system is a persistent event machine with a model adapter, typed state, tool registry, approval boundary, loop termination, compaction, stream protocol, and replay/debug trail. The runtime is the product, not the prompt.
> Verso should build the runtime first. The clean ReAct loop is the default path through that runtime — not a simplification of it.
