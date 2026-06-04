# fw-crewai-letta — CrewAI + Letta: Verso Design Intelligence

Cluster: `fw-crewai-letta`
Sources: `teardowns/CREWAI.md` (R1–R3, ~2,300 lines), `teardowns/LETTA.md` (R1–R3, ~2,000 lines)
Date extracted: 2026-06-04

---

## CrewAI

### What it is

A role-based multi-agent framework. Every agent is a Pydantic model with three required fields: `role`, `goal`, `backstory`. These are injected verbatim into the LLM system prompt. Tasks carry `description`, `expected_output`, and an assigned agent. `crew.kickoff(inputs={...})` executes tasks in one of exactly two modes: `Process.sequential` (serial, each task feeds context forward) or `Process.hierarchical` (auto-injected manager agent delegates via tool calls to workers). The repo is also two frameworks in one: `Crew/Agent/Task/Process` (the original) + `Flow/@start/@listen/@router` (the new declarative pipeline). They share the LLM layer and event bus but have separate execution models.

### Agent loop shape

`CrewAgentExecutor.invoke` → `_invoke_loop` → branches on `llm.supports_function_calling()`:
- **Native tools path** (`_invoke_loop_native_tools`, `crew_agent_executor.py:449`): `while iter < max_iter (default 25)` → LLM call with OpenAI/Anthropic tool schema → if tool_calls list, execute each, append ToolMessages → else `AgentFinish`.
- **ReAct text path** (`_invoke_loop_react`, `crew_agent_executor.py:313`): `while not AgentFinish` → LLM call → parse text for `Thought/Action/Action Input/Observation/Final Answer` via regex → if `AgentAction`, run tool, append observation → if `AgentFinish`, exit. On `max_iter` exceeded: force-run the LLM one final time without tool options to extract a best-guess `Final Answer`.

**Termination conditions:**
1. `AgentFinish` parsed (text path) or model returns content with no tool calls (native path).
2. `has_reached_max_iterations(iterations, max_iter=25)` → force-final.
3. Context length exceeded (`is_context_length_exceeded(e)`) → summarize oldest messages and continue.
4. `OutputParserError` after `_max_parsing_attempts` retries → `ToolUsageError` propagated.
5. Tool with `result_as_answer=True` → short-circuit to `AgentFinish`.

**Constants (KNOWN):**
```python
Agent.max_iter = 25                          # default, agent loop cap
Agent.max_retry_limit = 2                    # per agent, for unknown errors
Task.guardrail_max_retries = 3               # per task, validate-and-retry
Task.max_retries = 0                         # output-format retries
ToolUsage._max_parsing_attempts = 3          # (2 for bigger models)
ToolUsage._remember_format_after_usages = 3  # (4 for bigger models)
ToolUsage SequenceMatcher ratio gate = 0.85  # fuzzy tool-name correction
OPENAI_BIGGER_MODELS = [gpt-4, gpt-4o, o1-preview, o1-mini, o1, o3, o3-mini]
CrewPlanner default model = "gpt-4o-mini"
```

### Tool system

**`BaseTool`** (`crewai/tools/base_tool.py`) is a Pydantic model:
```python
class BaseTool(BaseModel):
    name: str
    description: str
    args_schema: type[BaseModel] | None = None
    result_as_answer: bool = False
    cache_function: Callable | None = None  # True = always cache
    max_usage_count: int | None = None      # None = unlimited
```

`@tool` decorator: wraps a Python function with type hints + docstring → auto-generates `args_schema` via `BaseTool.__init_subclass__`. The schema generator inspects `_run` signatures, builds Pydantic models from annotations/defaults, and registers them in a global `_TOOL_TYPE_REGISTRY: dict[str, type]`.

**`ToolUsage` parse/repair engine** (`tool_usage.py`, 1,027 LOC) — the layer between "parsed an Action string" and "ran the tool":
1. **Fuzzy name correction**: `SequenceMatcher(None, sanitize(tool.name), sanitize(asked_name)).ratio() > 0.85` — silently fixes `web_serch` → `web_search`.
2. **4-stage input-repair ladder** (`_validate_tool_input`): `json.loads` → `ast.literal_eval` → `json5.loads` → `repair_json(skip_json_loads=True)`.
3. **LLM-assisted re-parse** (`_function_calling`): if above fails and `function_calling_llm` is set, ask a second LLM to emit `{"tool_name": "...", "arguments": {...}}` with a hard constraint that `tool_name` must exactly match one of the available tools.
4. **Result cache**: keyed `(sanitize(tool_name), json.dumps(arguments))`, gated by optional `cache_function(args, result)`.
5. **Repeated-usage guard**: if `(tool_name, arguments)` equals `tools_handler.last_used_tool`, return cached result to stop infinite identical tool loops.
6. **"Remember the format" re-injection**: every `_remember_format_after_usages`-th tool result re-appends the full tool-list + ReAct format prompt to nudge a drifting agent.

**MCP integration**: `MCPServerAdapter` (`crewai_tools/adapters/mcp_adapter.py:31`) — takes `StdioServerParameters | dict` (Stdio or SSE/StreamableHTTP), delegates to `MCPAdapt(serverparams, CrewAIAdapter(), connect_timeout=30)`. `CrewAIAdapter` converts each MCP tool's JSON Schema into a `BaseTool` with auto-synthesized `args_schema`. Lifecycle: context manager auto-started in `__init__`, auto-stopped via `close_mcp_server` after-kickoff callback injected by `@CrewBase`.

**Pre-built tool library** (`crewai_tools`): 78 tools covering SerperDev search, web scraping, S3, MySQL, Exa, BrowserBase, etc. Each is a `BaseTool` subclass.

### Context assembly

The agent's prompt is assembled per-task from prompt "slices" held in `translations/en.json` (the i18n registry — every default prompt lives there, not scattered in code). The system message:
```
You are {role}. {backstory}
Your personal goal is: {goal}
[tools slice — only when tools exist]
[memory slice — only when recall hit something]
```
The user message per task:
```
Current Task: {input}
[task_with_context slice — only if upstream task outputs exist]
[This is the expected criteria for your final answer: {expected_output}]
```
Context injection: `_get_context(task, prior_outputs)` either concatenates all prior outputs or, if `task.context` is explicitly set (list of upstream `Task` objects), only those. Context blindness is addressed by the delegation tool description: *"they know nothing about the task, so share absolutely everything you know, don't reference things but instead explain them."*

**Context length overflow** (`respect_context_window=True`): `handle_context_length` summarizes the oldest messages in the message list when `is_context_length_exceeded(e)` is raised by LiteLLM. Not model-managed — exception-triggered.

### Memory

Four-store legacy model + newer "Unified Memory":
- `ShortTermMemory` — current-crew context, SQLite-backed (or embedchain-compatible store).
- `LongTermMemory` — across-runs persistence with quality scores.
- `EntityMemory` — named entities extracted during execution (type + description).
- `ExternalMemory` — optional mem0.ai adapter.

**Unified Memory** (`Memory` class, opt-in, `crewai/memory/unified_memory.py:56`) with LanceDB backend:

Save flow (`EncodingFlow`, 5-step CrewAI Flow):
1. Batch embed (one embedder call for all items).
2. Cosine dedup (pairwise cosine matrix, drop items above `consolidation_threshold=0.85` of an earlier item).
3. Parallel find-similar (concurrent searches against stored records).
4. Parallel LLM analysis (N concurrent calls per item): `MemoryAnalysis(suggested_scope, categories, importance, extracted_metadata)` + `ConsolidationPlan(keep/update/delete/insert_new)`.
5. Execute plans (batch re-embed updates + bulk insert).

Recall scoring:
```python
score = semantic_weight * cosine
      + recency_weight * exp(-elapsed_days * ln(2) / half_life_days)
      + importance_weight * importance

# defaults
semantic_weight = 0.5
recency_weight = 0.3
importance_weight = 0.2
recency_half_life_days = 30
confidence_threshold_high = 0.8
confidence_threshold_low = 0.5
complex_query_threshold = 0.7
exploration_budget = 1        # extra deep-recall round if confidence too low
consolidation_limit = 5       # max nearby memories compared for consolidation
```

Memory is saved as the last step of `task.execute_sync` after guardrail and output-format parsing.

### System prompts (verbatim fragments)

Role-playing slice (system message body):
```
You are {role}. {backstory}
Your personal goal is: {goal}
```

Tools slice (appended when tools exist):
```
You ONLY have access to the following tools, and should NEVER make up tools that are not listed here:
{tools}
IMPORTANT: Use the following format in your response:
Thought: you should always think about what to do
Action: the action to take, only one name of [{tool_names}], just the name, exactly as it's written.
Action Input: the input to the action, just a simple JSON object, enclosed in curly braces, using " to wrap keys and values.
Observation: the result of the action
Once all necessary information is gathered:
Thought: I now know the final answer
Final Answer: the final answer to the original input question
```

Max-iterations final-answer coercion:
```
Thought: I now can give a great answer
Final Answer: my best complete final answer to the task.
```

Guardrail retry injection:
```
### Previous attempt failed validation: {guardrail_result_error}
...
Try again, making sure to address the validation error.
```

Format-error slice (parse failure feedback):
```
I did it wrong. Invalid Format: I missed the 'Action:' after 'Thought:'. I will do right next, and don't use a tool I have already used.
```

Hierarchical manager prompt (verbatim):
```
role:      Crew Manager
goal:      Manage the team to complete the task in the best way possible.
backstory: You are a seasoned manager with a knack for getting the best out of your team.
           You are also known for your ability to delegate work to the right people, and to
           ask the right questions to get the best out of your team. Even though you don't
           perform tasks by yourself, you have a lot of experience in the field, which allows
           you to properly evaluate the work of your team members.
```

### Error/retry paths

1. `OutputParserError` (regex parse failure) → `handle_output_parser_exception` → re-inject error slice + retry, up to `_max_parsing_attempts`.
2. `ValidationError` on `response_model` → fall back to string processing.
3. Context length exceeded → summarize oldest messages (exception-triggered, not threshold-triggered).
4. LiteLLM provider errors → re-raised immediately (not caught by CrewAI's error loop).
5. Guardrail failure → re-run the agent with error feedback injected, up to `guardrail_max_retries=3`.
6. Output format parse failure → re-run with `format_instructions` injected, up to `max_retries=0` (default disabled).
7. Stop-word support detection → `stop` param dropped and re-issued if `'stop'` appears in the error message.
8. `LLMGuardrail` (string guardrail auto-wrapped): spins up a throwaway validator agent to judge compliance, returns `LLMGuardrailResult(valid: bool, feedback: str)`.

### Multi-agent coordination

**Sequential process**: tasks run in declared order; prior task output is injected as `context` into the next task's prompt. Static DAG, no dynamic routing.

**Hierarchical process**: a manager agent (auto-generated or user-provided) runs each task. Its only tools are two synthetic delegation tools:
- `Delegate work to coworker(coworker, task, context)` — calls another agent's `execute_task`.
- `Ask question to coworker(coworker, question, context)` — same, framed as a question.
The manager picks which worker to call via the tool-name argument. There is no separate planner — it is one extra agent whose toolbox is delegation, looped through the same `_execute_tasks` as everything else.

**A2A protocol** (`crewai/a2a/`): `Agent.a2a` accepts `A2AServerConfig` (expose this agent over Google A2A HTTP) or `A2AClientConfig` (delegate to a remote A2A agent). Remote agent calls happen via HTTP during the agent's tool execution.

**`@CrewBase` YAML config**: decorator-as-metaclass that loads `config/agents.yaml` + `config/tasks.yaml` relative to the defining file, resolves YAML string references (`tools: [scrape, search]`) to live factory-method objects, wires `@before_llm_call`/`@after_llm_call`/`@before_tool_call`/`@after_tool_call` hooks filtered by agent role or tool name.

### Streaming protocol

CrewAI has no native top-level streaming API. Three layers:
1. **Step callbacks**: `Agent.step_callback(AgentAction|AgentFinish)` fires after each loop iteration; `Crew.task_callback` fires after each task completes.
2. **Event bus** (`crewai/events/`): typed events emitted to `crewai_event_bus.on(EventClass, handler)`. Includes: `LLMStreamChunkEvent`, `ToolUsageStartedEvent`, `ToolUsageCompletedEvent`, `AgentExecutionStartedEvent`, etc.
3. **Token streaming**: `LLM(stream=True)` enables LiteLLM streaming; chunks bubble up via `LLMStreamChunkEvent`. No `graph.stream()`-style top-level API.

**Streaming implementation** (`Crew.kickoff` when `stream=True`, `crew.py:977-1001`): re-entrant trick — spawns a thread that flips `self.stream=False` and calls `kickoff` synchronously; outer call returns a `CrewStreamingOutput` whose iterator is fed by event-bus chunks via `create_chunk_generator`. Not native streaming — the normal pipeline runs in a thread and the event bus is tailed.

### Planning (plan-and-execute mode)

`Crew(planning=True)` runs a pre-execution planner before any task:
- Model: `gpt-4o-mini` (default), overridable via `Crew.planning_llm`.
- Planner agent role: `"Task Execution Planner"`.
- Output: `PlanPerTask(task_number: int≥1, task: str, plan: str)` via structured output.
- Plan injection: plans are **concatenated directly onto `task.description`** before the normal run. Planning is a one-shot LLM call, not a separate execution stage.

### LLM layer

`crewai/llm.py` wraps LiteLLM (100+ providers) as primary, native SDKs (OpenAI, Anthropic, Azure, Bedrock, Gemini) as the hot path. Model routing: model strings like `"openai/gpt-4o-mini"`, `"claude-sonnet-4-5"`, etc. are parsed to pick provider + native vs. LiteLLM path.

`_prepare_completion_params` passes the verbatim dict to `litellm.completion`:
```python
params = {
  "model", "messages", "timeout", "temperature", "top_p", "n",
  "stop",          # gated by supports_stop_words()
  "max_tokens", "presence_penalty", "frequency_penalty",
  "response_format", "seed", "stream", "tools", "reasoning_effort",
  **additional_params
}
# None keys dropped
```

Streaming: `stream_options={"include_usage": True}` forces the final chunk to carry token counts. Tool-call deltas accumulated by index into `defaultdict(int → AccumulatedToolArgs)`.

### What's good about CrewAI

1. **Translations/i18n as the prompt registry** — every default prompt in one JSON file, localizable/forkable without changing code.
2. **Dual-path loop** — auto-detects native tool-calling support and uses the best path for each model. Graceful fallback.
3. **4-stage input-repair ladder** — `json.loads → ast.literal_eval → json5 → repair_json` before giving up on malformed tool input.
4. **Fuzzy tool-name correction** (SequenceMatcher > 0.85) — silently fixes LLM typos.
5. **Guardrail validate-and-retry loop** — first-class output validation at the task level, not patched onto the agent loop.
6. **`@CrewBase` YAML config** — declarative crew config with file-relative path resolution and string-to-object YAML reference binding.
7. **Tool result caching** with optional `cache_function(args, result)` gate — deterministic tool results are never re-executed.

### What's bad / what to avoid

1. **Two incompatible execution models in one repo** (`Crew` + `Flow`) — users must know which one to use; documentation conflates them.
2. **Streaming = run-in-thread + tail-event-bus** — not real streaming; SSE delivery to external clients is bolted on, not native.
3. **Process enum with only two values after years** — hierarchical is one-level supervisor + workers; no multi-level, swarm, or consensus patterns.
4. **No native async agent loop** — `ThreadPoolExecutor` for async tasks; no `async/await` throughout the loop.
5. **ReAct regex parser is fragile** — six fallback paths, `json_repair` for tool-input JSON; inevitable edge-case failures.
6. **No durable interrupts** — `human_input=True` blocks on `input()`, not resumable across processes.
7. **Manager agent MUST NOT have tools** — enforced by `raise Exception("Manager agent should not have tools")` — a hard constraint that limits what a hierarchical manager can do.

---

## Letta (formerly MemGPT)

### What it is

Letta is the production implementation of the MemGPT paper (Packer et al., UC Berkeley, 2023). The novel primitive: **virtual context management** — the LLM does not see all its memory. It sees a curated "core memory" block (editable via tool calls), plus "recall memory" (hybrid search over all past messages), plus "archival memory" (vector store for long-term facts). When context approaches the window limit, a compaction model summarizes old messages before eviction. The LLM's context window is treated as main memory; recall/archival are disk, accessed via tools.

### Agent loop shape (`LettaAgentV3`, `letta_agent_v3.py`)

```python
async def step(input_messages, max_steps=50, ...):  # DEFAULT_MAX_STEPS=50 (constants.py:75)
    _initialize_state()
    # conversation-scoped block overrides (isolated memory per conversation)
    apply_isolated_blocks_to_agent_state(conversation_id)
    curr_in_context = _prepare_in_context_messages_no_persist_async(...)
    for i in range(max_steps):
        # pipelined async credit check from previous iteration
        if credit_task and not await credit_task: stop=insufficient_credits; break
        response = _step(messages=in_context + input_to_persist, ...)
        async for chunk in response: collect letta_messages
        if not should_continue: break
        if i == max_steps-1 and stop_reason is None: stop=max_steps
    if stop_reason is None: stop = end_turn
    return LettaResponse(messages=..., stop_reason=stop, usage=...)
```

**V3 continuation state machine** (`_decide_continuation`, `letta_agent_v3.py:1987-2036`): replaces the old model-controlled `request_heartbeat` boolean. Continue-by-default after any tool call; stop only when:
1. Model emits content with no tool call AND no uncalled required tools → `end_turn`.
2. `TerminalToolRule` tool was called → `tool_rule` stop.
3. `finish_reason == "length"` → `max_tokens_exceeded`.
4. `i == max_steps-1` → `max_steps`.
5. Cancellation/credits/context-overflow → respective stop reasons.

Forced continuation injects `NON_USER_MSG_PREFIX`-tagged messages (`"[This is an automated system message hidden from the user] "`) explaining why the loop continues — a "hidden coach" message to the model.

**Tool rules** (`helpers/tool_rule_solver.py`) — per-step constraint propagator:
- `InitToolRule` — must call X first (first step only: allowed set = init tools only).
- `TerminalToolRule` — calling X ends the loop.
- `ContinueToolRule` — must call X after Y.
- `ChildToolRule` / `ParentToolRule` — directed graph dependencies.
- `MaxCountPerStepToolRule` — limit calls per step.
- `RequiresApprovalToolRule` — pause and ask user.

Each step, `get_allowed_tool_names()` computes the **intersection** of all child/parent/conditional rules' `get_valid_tools(history)` outputs. When exactly one tool is allowed, `should_force_tool_call()` returns true and `force_tool_call` is passed to `build_request_data`. Rule violations produce `StopReasonType.tool_rule_violation`. Also performs **arg prefill**: `InitToolRule.args` at step 0, `ChildToolRule` per-child arg maps when the parent was just called.

**Parallel tool gating** (`letta_agent_v3.py:1111-1128`): parallel tool calls enabled only if NO tool rules exist (except `requires_approval`) AND `llm_config.parallel_tool_calls` is on. Rationale: tool-ordering/terminal/child constraints are incompatible with model firing multiple tools at once.

### Models / routing

17 providers supported (`constants.py:11`): letta, openai, anthropic, ollama, google_ai, google_vertex, azure, groq, together, vllm, bedrock, deepseek, xai, lmstudio, zai, zai_coding, openrouter.

**Auto-mode routing** (`letta_agent_v3.py:1042-1090`): when agent handle is in `AUTO_MODE_HANDLES`:
1. Availability routing — if primary handle rerouted/unavailable, fall back to secondary.
2. Content routing — `apply_reroute_rules` inspects messages and swaps model by content (e.g., vision model when images present).
Resolved model written back to step record for correct billing.

**Summarization routing**: `letta/auto` handle routes to Haiku 4.5 for compaction (cheap, well-suited); larger model for generation. Self-hosted agents use static `llm_config`.

### Tool system

Memory tools are first-class, auto-registered with every agent:

```python
BASE_TOOLS = ["send_message", "archival_memory_insert", "archival_memory_search"]  # deprecated
BASE_MEMORY_TOOLS = ["core_memory_append", "core_memory_replace", "memory", "memory_apply_patch"]
BASE_MEMORY_TOOLS_V2 = ["memory_replace", "memory_insert"]
BASE_MEMORY_TOOLS_V3 = ["memory"]       # v3 omni-tool, Claude-Sonnet-4.6-friendly
BASE_SLEEPTIME_TOOLS = ["memory_replace", "memory_insert", "memory_rethink", "memory_finish_edits"]
MULTI_AGENT_TOOLS = ["send_message_to_agent_and_wait_for_reply",
                     "send_message_to_agents_matching_tags",
                     "send_message_to_agent_async"]
BUILTIN_TOOLS = ["run_code", "run_code_with_tools", "web_search", "fetch_webpage"]
FILES_TOOLS = ["open_files", "grep_files", "semantic_search_files"]
LETTA_PARALLEL_SAFE_TOOLS = {"conversation_search", "archival_memory_search", ...}
# Memory writes are NOT in this set — they serialize
```

The V3 omni-tool `memory(command, path, file_text, old_string, new_string, insert_line, ...)` with `command ∈ {create, str_replace, insert, delete, rename}` — collapses multiple memory tools into one. Claude Sonnet 4.6 prefers one well-designed tool over many small ones; older models used the split sets. Both are kept for backward compatibility.

**Schema generator** (`functions/schema_generator.py`, 903 lines): Python function → JSON Schema. Uses `ast` to parse signatures + Google/NumPy-style docstrings. Always appends `request_heartbeat: bool` to `properties` and `required` (even in V3, where it is hardcoded `False` — the param is still in the schema for compatibility). Max tool name length: `MAX_TOOL_NAME_LENGTH = 48` (Modal deployment constraint). Max tool call ID: `TOOL_CALL_ID_MAX_LEN = 29` (OpenAI constraint).

**Tool sandbox** (3-backend fallback chain, `sandbox_tool_executor.py`):
1. Modal (if tool metadata `"sandbox"=="modal"` and Modal enabled) — one Modal App per tool, polls up to 60s for readiness.
2. E2B (if `sandbox_type == SandboxType.E2B`) — `AsyncSandbox.create(template, metadata={state_hash})`.
3. Local (default) — subprocess + optional venv per sandbox config.

Security invariant: `assert orig_memory_str == new_memory_str, "Memory should not be modified in a sandbox tool"` — sandboxed code may NOT mutate core memory. Results transported as JSON (changed from pickle in commit `1131535` for security).

### Context assembly — the MemGPT "virtual context" mechanism

`compile_system_message` (`services/helpers/agent_manager_helper.py:251-332`) assembles the in-context prompt every turn:
```python
tool_constraint_block = tool_rules_solver.compile_tool_rule_prompts()
memory_metadata = PromptGenerator.compile_memory_metadata_block(
    memory_edit_timestamp, agent_id, previous_message_count,
    archival_memory_size, timezone)
memory_with_sources = in_context_memory.compile(tool_usage_rules=..., sources=..., max_files_open=...)
full_memory = memory_with_sources + "\n\n" + memory_metadata
prompt = system_prompt.replace("{CORE_MEMORY}", full_memory)
```

The `{CORE_MEMORY}` placeholder (`IN_CONTEXT_MEMORY_KEYWORD`) is replaced with compiled memory blocks + the `<memory_metadata>` page-table block — the literal "virtual context" pointer:
```
<memory_metadata>
- AGENT_ID: {agent_id}
- CONVERSATION_ID: {conversation_id}
- System prompt last recompiled: {timestamp in agent timezone}
- {previous_message_count} previous messages between you and the user are stored in recall memory
- {archival_memory_size} total memories you created are stored in archival memory (use tools to access them)
- Available archival memory tags: {comma-joined tags}
</memory_metadata>
```

The system message is rebuilt **every turn** because memory blocks change. The agent never sees a static system prompt.

**Anti-redundant-tool-call instruction** (verbatim, `letta_v2_chat.py`):
```
You respond directly to the user when your immediate context (core memory and files) contain all the information
required to respond. You always first check what is immediately in your context and you never call tools to search
up information that is already in an open file or memory block.
```

### Memory architecture

**Core memory blocks** (`schemas/block.py`):
```python
class Block(BaseModel):
    label: str                                      # e.g. "persona", "human"
    value: str                                      # the editable content
    limit: int = CORE_MEMORY_BLOCK_CHAR_LIMIT       # = 100,000 chars (constants.py:435)
    description: str                                # tells agent how to use this block
    read_only: bool = False
```
Blocks are **first-class DB rows** — the same block can be attached to many agents via `BlocksAgents` junction table. When one agent edits a shared block, `_rebuild_system_prompts_for_connected_agents(block_id)` force-recompiles every connected agent's system prompt. This is the mechanism for multi-agent shared state — a "team memo" attached to N agents is a live consistent shared whiteboard.

Blocks versioned in `block_history` table (undo). Conversation-scoped block overrides via `blocks_conversations` junction (the same agent can maintain different core memory per conversation thread).

**Recall memory** (`conversation_search` tool) — hybrid text + semantic search over the agent's entire message history. DB indexed by `(agent_id, conversation_id, sequence_id)` and `created_at` for time-range queries.

**Archival memory** (`archival_memory_insert`/`archival_memory_search`):
```python
DEFAULT_EMBEDDING_DIM = 1024    # constants.py:93
MAX_EMBEDDING_DIM = 4096        # do NOT change or DBs need reset
DEFAULT_EMBEDDING_CHUNK_SIZE = 300
EMBEDDING_BATCH_SIZE = 200
```
pgvector-backed (`Vector(MAX_EMBEDDING_DIM=4096)`). Tags with `any`/`all` match modes. `source_passages` and `archival_passages` live in separate tables. Per-archive vector backend selectable: `Archive.vector_db_provider ∈ {pgvector, Turbopuffer, Pinecone}`. Archives can be shared across agents via `archives_agents` junction table.

**File memory** (`FILES_TOOLS`): `open_files` mounts file contents as `FileBlock`s in core memory; `grep_files` / `semantic_search_files` for search. `is_open` flag on `FileBlock` controls whether content is in-context. Agent must explicitly close files to evict them.

### Compaction (summarization)

Triggers at `SUMMARIZATION_TRIGGER_MULTIPLIER = 0.9` of context window (constants.py:83) — proactive at 90% to avoid GPT-5 family `max_output_tokens_exceeded` at context edge.

Default mode: `PARTIAL_EVICT_MESSAGE_BUFFER` (not sliding-window). Settings:
```python
mode = PARTIAL_EVICT_MESSAGE_BUFFER
message_buffer_limit = 60
message_buffer_min = 15
partial_evict_summarizer_percentage = 0.30   # evict 30%, keep last 70%
desired_memory_token_pressure = 0.3          # target: ≤30% full after compaction
max_summarizer_retries = 3
```

`_partial_evict_buffer_summarization`:
1. `target_start = round((1.0 - 0.30) * total)` — start of eviction region.
2. Walk forward to next ASSISTANT message (to preserve tool-call/tool-return pairs).
3. Summarize `messages[1:assistant_idx]` via `simple_summary` (routed to Haiku 4.5 for `letta/auto`).
4. Insert summary at index 1 as `role=user` message (just after system message).
5. Count-based (not token-based).

Model is warned before truncation via `NON_USER_MSG_PREFIX` "conversation history will soon reach its maximum length" message.

### System prompts (9 variants)

`letta_v1.py` (25L) — task-focused, no persona framing (verbatim key line):
```
Continue executing and calling tools until the current task is complete or you need user input.
To continue: call another tool. To yield control: end your response without calling a tool.
```

`memgpt_chat.py` / `memgpt_v2_chat.py` — persona-style MemGPT prompts. Key structural elements: "Your ability to edit your own long-term memory is a key part of what makes you a sentient person", then memory-type explanations (core/recall/archival), then tool descriptions.

`memgpt_v2_chat.py` uses XML tags: `<style>`, `<control_flow>`, `<memory>` (with `<memory_editing>`, `<memory_tools>`, `<memory_types>`).

The prompt generator (`prompts/prompt_generator.py`, 224L) picks the base prompt, replaces `{CORE_MEMORY}` with the compiled memory string, and appends available tool descriptions. Rebuilt every turn.

### Multi-agent coordination

Agent-as-microservice pattern. No central orchestrator. Each agent calls other agents like REST APIs via `MULTI_AGENT_TOOLS`. Coordination:
1. Create agent A and agent B.
2. Give A the tool `send_message_to_agent_and_wait_for_reply` pointed at B.
3. A runs, calls B, gets B's response.

`Group` schema (`schemas/group.py`) groups agents into addressable sets. Full taxonomy (`schemas/group.py:61-122`):
- `DynamicGroup` — tagged broadcast
- `SleeptimeGroup` — background consolidation agents

`send_message_to_agent_async` is LOCAL_ONLY (not for Letta Cloud).

**Shared memory blocks** (R2.11): editing a block shared across agents propagates via system prompt recompile to all sharing agents. This is how multi-agent shared state works — not message passing, but shared mutable blocks.

**Sleep-time agents** (`groups/sleeptime_multi_agent_v4.py`): after each main agent run, fires background `SleeptimeMultiAgentV4` instances. Tools: `memory_replace`, `memory_insert`, `memory_rethink`, `memory_finish_edits`. The sleep-time agent reads recent messages, rewrites core memory blocks to integrate new facts, archives older content. This is active memory consolidation — background agent whose entire job is curating another agent's memory. Trigger: `SLEEPTIME_TRIGGER_STEPS` / `SLEEPTIME_TRIGGER_PROBABILITY` (conditional fire to control cost).

### Streaming protocol (SSE)

`StreamingResponseWithStatusCode` (`streaming_response.py:232`) — custom response class for three reasons:
1. **Set HTTP status from inside the stream** — peeks first chunk, sets `status_code` before `http.response.start`.
2. **Keep agent running after client disconnect** — `asyncio.shield` wraps the body when `settings.use_asyncio_shield`; client disconnect flips `_client_connected=False` but shielded task completes and persists.
3. **Keepalive + cancellation decoupled from data** — `add_keepalive_to_stream` with bounded `asyncio.Queue(maxsize=1)`, pings every 30s carrying `run_id` and `last_seq_id`. `cancellation_aware_stream_wrapper` polls `run_manager` every 0.5s and injects `CancelledError` via `generator.athrow()` so the agent loop can clean up.

Wire format (KNOWN, `streaming_service.py` + `streaming_response.py`):
- Normal frame: `data: {<LettaMessage json>}\n\n`
- Keepalive: `data: {"message_type":"ping", "run_id":..., "seq_id":<last>}\n\n`
- Stop-reason (always before terminal): `data: {"message_type":"stop_reason","stop_reason":"end_turn"|...}\n\n`
- Error (named event): `event: error\ndata: {<LettaErrorMessage>}\n\n`
- Cancellation: `event: cancelled\ndata: {"message":"Run was cancelled"}\n\n`
- Terminal: `data: [DONE]\n\n` — always last, synthesized if the agent loop exits without emitting one.

**Resumable SSE over Redis Streams** (background mode):
- Writer: `RedisSSEStreamWriter` assigns monotonic `seq_id`, batches, `XADD stream_key chunk MAXLEN~`. Terminal `[DONE]` guaranteed on every exit path including errors.
- Reader: `redis_sse_stream_generator(run_id, starting_after=last_seq_id, poll_interval=0.1, batch_size=100)` — cursor-based replay via `XRANGE`.
- Reconnect endpoint: `POST /v1/conversations/{id}/stream` resolves run by `run_id` → `otid` (with 250/500/1000ms backoff) → most-recent active run. Enforces 3-hour expiry.
- Duplicate request recovery: Redis mutex on `conversation_id`, same-`otid` requests poll Redis for existing run and replay its stream instead of starting a new one.

`RequestIdMiddleware` is pure-ASGI (not `BaseHTTPMiddleware`) — because `BaseHTTPMiddleware` does not propagate contextvars into streaming response generators (Starlette issue #1729). Stashes `request_id` in both a `ContextVar` (for non-streaming code) and `request.state.request_id` (for streaming generators).

**OpenAI-compat proxy** (`POST /v1/chat/completions`): the `model` field carries the Letta agent ID (must start with `agent-`); only the last `role=="user"` message is used; the `OpenAIChatCompletionsStreamTransformer` converts Letta SSE events to OpenAI `ChatCompletionChunk` objects, filtering out memory/tool frames so the caller sees clean assistant text.

### REST API shape

55 endpoints on `/v1/agents` alone. Key design decisions:
- `PATCH /attach/` and `PATCH /detach/` for many-to-many relations (tools↔agents, files↔agents, blocks↔agents, archives↔agents). REST pattern: action as verb on relation, not `POST/DELETE` on resource.
- All routes double-mounted at `/v1` (schema-visible) and `/latest` (hidden alias).
- Header bundle `get_headers() → HeaderParams` — one `Depends` covers actor_id, project_id, SDK version, experimental flags, billing context — no per-route boilerplate.
- `Annotated[str, Path(...)]` path-param validators with regex — malformed IDs get friendly 422 rewrites (not raw Pydantic messages).
- `operation_id` on every route, consumed by Fern for SDK generation.
- Module-global singleton server (`get_letta_server()` just returns the import) — DB sessions managed inside service layer, not as FastAPI per-request deps.

### What's good about Letta

1. **Memory as tool calls** — the LLM manages its own memory via tools. No magic behind the agent's back. No automatic summarization that the agent can't observe or control.
2. **Virtual context page table** — `<memory_metadata>` block tells the model exactly what it has in recall/archival on every turn. The agent always knows what's outside its window.
3. **Tool-rule constraint solver** — per-step legal action set via rule intersection. `InitToolRule` + `TerminalToolRule` + `ContinueToolRule` give the framework behavioral contracts without hardcoding workflows.
4. **Resumable SSE over Redis Streams** — the most robust streaming/reconnect design in this cluster. Cursor-based replay, duplicate request recovery, `athrow()` for cancellation cleanup.
5. **Sleep-time agents** — background memory consolidation decoupled from the critical path. Active curation of memory, not passive accumulation.
6. **Shared memory blocks** — same DB row attached to N agents, propagating recompiles on write. First-class shared state mechanism.
7. **Grammar-constrained local LLM decoding** — GBNF grammars guarantee valid tool-call JSON from models without native tool-calling support. Works on Llama 3 8B locally.
8. **Sandbox security invariant** — `assert memory_unchanged` after sandbox execution + JSON (not pickle) transport.
9. **OpenAI-compat proxy** — `POST /v1/chat/completions` with `model="agent-..."` wraps a full memory-augmented agent behind the OpenAI wire format.

### What's bad / what to avoid

1. **Massive codebase complexity** — `letta_agent_v3.py` alone is 2,134 lines. The summarizer is 2,116 lines across 9 files. The `agent_manager.py` is 3,599 lines. Deep, but brittle to maintain.
2. **Module-global singleton server** — fine for single-process deployments but breaks clean test isolation and multi-app composition.
3. **Per-request model in memory blocks** — `blocks_conversations` junction for conversation-scoped overrides is correct but adds a join on every `compile_system_message` call.
4. **Postgres + pgvector as mandatory** — archival memory requires Postgres with pgvector. The `Vector(4096)` column cannot be resized without a migration. Locks in infrastructure choice.
5. **`{CORE_MEMORY}` placeholder as the template format** — only `f-string` style replacement is supported; mustache raises `NotImplementedError`. A brittle single-format dependency.
6. **V2 → V3 heartbeat breaking change** — the `request_heartbeat` bool on every tool call was the core MemGPT primitive; V3 silently hardcodes it to `False` and changes the continuation model. This is a semantics-level breaking change that isn't surfaced clearly to users.

---

## → Verso Implications

### Copy from CrewAI

1. **Prompt registry pattern**: store all default prompts in a single structured file (`translations/en.json` equivalent), not scattered across source files. This enables localization, forking, and easy inspection of what text the framework injects. Verso should have a single `prompts.toml` or `prompts.json` that users can override at init time.

2. **Dual-path loop with model capability detection**: auto-detect `supports_function_calling()` per model and dispatch to the native tool-call path vs. ReAct text-parse path. Provide both; the text path is the fallback for all models forever.

3. **4-stage input-repair ladder**: `json.loads → ast.literal_eval → json5 → repair_json` before returning a tool-input parse error. This is cheap insurance against model formatting drift on high-traffic systems. Copy verbatim.

4. **Fuzzy tool-name correction** (SequenceMatcher > 0.85): before reporting "tool not found", check if the model's tool name is a near-match. Log the correction; don't silently fix — but don't fail on a typo either.

5. **`result_as_answer=True` flag on tools**: allows a tool execution to directly short-circuit the agent loop with its output as the final answer. Useful for delegation, HITL, and deterministic outputs.

6. **Guardrail validate-and-retry as a first-class concept at the task level**: `guardrail: Callable | str` on each task with `guardrail_max_retries`. The string form auto-wraps into an LLM validator. This is cleaner than ad-hoc output parsing.

7. **`@tool` decorator that auto-generates args_schema from type hints + docstring**: users should be able to write a plain Python function and register it as a tool. The schema generation should be deterministic and fully inspectable.

8. **YAML config with string-ref resolution** (`@CrewBase` pattern): allow users to declare agents and tasks in YAML, with tool/LLM factory names that resolve to decorated Python objects. Reduces boilerplate for declarative agent graphs.

9. **Repeated-usage short-circuit**: if `(tool_name, arguments)` equals the last call exactly, return cached result. Prevents trivially infinite identical tool loops. One check, big safety net.

10. **Periodic format-reminder re-injection**: after every N tool uses, re-append the tool-list + format instructions to the message. This is cheap and prevents agent drift on long-running tasks.

### Copy from Letta

1. **Virtual context page table**: the `<memory_metadata>` block that tells the model "you have N messages in recall and M in archival — use your tools to reach them" is the most valuable UX idea in this cluster. Verso should always tell agents what they _cannot_ see right now, not just what they can. Implement as a `context_summary` block in the system prompt that updates every turn.

2. **Tool-rule constraint solver**: `InitToolRule`, `TerminalToolRule`, `ContinueToolRule`, `ChildToolRule`, `RequiresApprovalToolRule`. The per-step intersection-of-allowed-tools mechanism makes agents declaratively constrained FSMs rather than free-form ReAct loops. Verso should expose this as an optional `tool_rules: list[ToolRule]` on the agent. Copy the solver exactly.

3. **Continuation state machine** (`_decide_continuation`): rather than a simple `while not done` loop, the termination check is a small function with named stop reasons. Each stop reason maps to a different error/logging/metric path downstream. Verso should name its stop reasons: `end_turn`, `max_steps`, `max_tokens_exceeded`, `tool_rule_stop`, `cancelled`, `error`.

4. **NON_USER_MSG_PREFIX hidden coach messages**: when the framework forces a continuation (e.g., tool rule not satisfied yet), inject a hidden system message explaining why. `"[This is an automated system message hidden from the user] Continuing: tool rule requires {x}."` The model is never confused about why it is being looped.

5. **`request_heartbeat` / continuation boolean** (V2 pattern, for advanced use): expose as an opt-in escape hatch. Most agents should use the rule-based continuation (V3). But for agents that need model-controlled continuation ("continue thinking if you feel uncertain"), the boolean is a clean, auditable mechanism. Put it behind a `heartbeat_enabled: bool = False` flag.

6. **Sleep-time agents as a first-class primitive**: after each agent turn (or on a schedule), run a background memory-consolidation agent against the conversation history. Verso should expose `memory_consolidation_agent: Agent | None` on the agent config. The consolidation agent gets its own tool set (memory write tools only), its own loop cap, and runs fire-and-forget after the main turn.

7. **Resumable SSE over Redis Streams**: Verso's streaming layer should assign monotonic `seq_id` to every frame, persist frames to a Redis Stream with `XADD … MAXLEN~`, and expose a reconnect endpoint with `starting_after: int`. This is the correct design for agent streaming at production reliability. The "belt-and-suspenders `[DONE]`" guarantee (synthesized if the agent exits without emitting one) is also mandatory.

8. **Keepalive frames carrying the last `seq_id`**: clients can track progress through keepalive-only stretches by reading `ping.seq_id`. Copy the `LettaPing` shape.

9. **Duplicate request recovery**: before starting a new step for a `(agent_id, conversation_id)` pair, acquire a Redis mutex. If a run is already in flight for that pair, return the existing run's stream (reconnect, don't duplicate). Copy the `otid` → `run_id` mapping pattern.

10. **Pure-ASGI `RequestIdMiddleware`** (not `BaseHTTPMiddleware`): contextvars don't propagate into streaming generators from `BaseHTTPMiddleware`. If Verso ships a web layer, make the request-ID middleware pure ASGI. Stash request ID in both a `ContextVar` AND `request.state.request_id`.

11. **OpenAI-compat proxy**: `POST /v1/chat/completions` with `model="agent-{id}"`. This lets users use Verso agents from any OpenAI SDK client. The transformer strips internal agent frames and emits clean `ChatCompletionChunk` objects. The implementation is ~150 lines once the Letta SSE format is defined.

12. **Shared memory blocks via junction tables**: instead of copying memory into each agent's context, store blocks as DB rows with attach/detach operations. Multiple agents sharing one block get instant propagation when it changes. First-class for swarm and multi-agent patterns.

13. **Grammar-constrained generation for local models**: GBNF grammars from tool schemas. Required for Verso to work on Ollama/llama.cpp setups without native tool-calling. Expose as `grammar_backend: Literal["none", "gbnf"] = "none"` on the LLM config.

### Avoid from CrewAI

1. **Two incompatible execution models in one repo**: `Crew` (role-play) and `Flow` (event-graph) serve different user models. Shipping both creates mental-model confusion. Verso should have one execution model with escape hatches, not two parallel APIs. If graph execution is needed, make it an explicit opt-in mode of the same loop, not a second framework.

2. **Streaming as run-in-thread + tail-event-bus**: this is not real streaming. SSE should be native to the agent loop, not a wrapper that tails side effects. Verso's loop should be async-native and emit SSE chunks directly.

3. **`raise Exception("Manager agent should not have tools")`**: hard runtime exceptions for configuration errors are bad DX. Validate at construction time with a clear `ValueError` or schema validation error.

4. **No durable interrupts**: `human_input=True` blocking on `input()` is not production-safe. Verso should implement HITL as a proper pause/resume with persistent state, not a blocking I/O call.

5. **Process enum with only two values**: the sequential/hierarchical binary is a useful default but shouldn't be the only option. Verso should let users compose the orchestration pattern rather than selecting from an enum.

6. **Planning as string concatenation onto task.description**: `task.description += plan_text` is fragile. Verso should keep plan and task description as separate fields, composed at prompt-assembly time, inspectable separately.

7. **`ThreadPoolExecutor` for async tasks**: in 2026, agent frameworks should be async-native throughout. Threads for async tasks create `asyncio` - thread boundary bugs and limit concurrency.

### Avoid from Letta

1. **Monolith agent class** (`letta_agent_v3.py` at 2,134 lines): a single class owning loop, memory, tool execution, summarization, routing, and streaming is too large to reason about. Verso should decompose these into distinct composable components.

2. **Postgres + pgvector as a hard dependency**: memory backends should be pluggable. Archival memory might be SQLite + sqlite-vec for self-hosted, Postgres + pgvector for production. Don't pin the DB in the core agent loop.

3. **V2 → V3 breaking change without clear versioning**: changing the core continuation mechanic (heartbeat → rule-based) is a semantics-level breaking change. Verso should version agent behaviors with explicit `agent_version: Literal["v1", "v2"]` or equivalent, not silently change defaults.

4. **Module-global singleton server**: this breaks testability and multi-app composition. Use proper DI or context-passed server objects.

5. **Only `f-string` template format**: a system prompt template format should be explicit and consistent. If you choose `{CORE_MEMORY}` style, document it and support mustache as an alternative (or vice versa). `raise NotImplementedError` for alternative formats is a trap.

6. **`DOUBLE_MOUNT under /v1 and /latest`**: useful for a public API product but adds confusion in a framework library. Keep routing simple unless you're building a multi-version hosted service.

### Verso could improve over both

1. **First-class memory tiers with Verso-native tooling**: Letta's memory design is correct (core/recall/archival) but the implementation is deep and Postgres-heavy. Verso should offer the same three-tier model with pluggable backends: SQLite-backed for dev, Postgres for prod, external adapters for mem0/Zep. Core memory as mutable Pydantic blocks editable via tool calls is the right primitive.

2. **Tool schema as a first-class declaration, not generated at runtime**: CrewAI and Letta both generate tool schemas from Python source code at runtime. Verso should allow users to declare tool schemas explicitly (or auto-generate at class definition time, not at runtime). The schema should be inspectable without running the tool.

3. **Named stop reasons surfaced to the caller**: neither framework consistently returns named stop reasons to the external caller. Verso should always return `AgentResult(output, stop_reason: StopReason, usage: UsageStats)` with `stop_reason ∈ {end_turn, max_steps, guardrail_fail, tool_rule_stop, cancelled, context_overflow, error}`.

4. **MCP as the first-class tool protocol**: CrewAI bolts on MCP via an adapter; Letta has `mcp_client/`. Verso should treat MCP as the primary tool registration mechanism, not a secondary adapter. All built-in Verso tools should be exposed as MCP tools. Third-party MCP servers should be first-class citizens with no adapter friction.

5. **Sleep-time memory consolidation as a scheduler primitive**: Letta's sleep-time agents are ad-hoc background callbacks. Verso should provide a `memory_consolidation_schedule: CronExpression | "after_every_turn" | None` on the agent config, with the consolidation agent running via the same `task.execute` mechanism as regular agents.

6. **Evals as first-class loop guardrails**: CrewAI's guardrail is a validate-and-retry mechanism; Letta has none. Verso should generalize this: `eval: Eval` on tasks, `eval_suite: EvalSuite` on agents, with automatic retry and metric logging. The guardrail retry loop from CrewAI plus named stop reasons from Letta plus a metric sink = a built-in eval harness.

7. **Per-step tool-rule constraints that are user-visible**: Letta's tool-rule solver is powerful but internal. Verso should surface the current legal tool set and the active rules in the agent step output, so developers can debug constraint behavior during development.

8. **Resumable SSE as a first-class transport guarantee**: both frameworks treat SSE reliability as an afterthought (CrewAI: event bus tailing; Letta: Redis Streams but hidden). Verso should design around resumable SSE as the primary streaming contract from day one: seq_id on every frame, Redis or Postgres cursor-based replay, reconnect endpoint with `starting_after` semantics.
