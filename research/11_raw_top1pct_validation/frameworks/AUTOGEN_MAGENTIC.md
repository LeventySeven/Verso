# AUTOGEN + MAGENTIC-ONE — Raw Extraction (nothing-is-lost artifact)

Sources read line-by-line:
- `/Users/seventyleven/Desktop/researchfms/teardowns/AUTOGEN.md` (1581 L)
- `/Users/seventyleven/Desktop/researchfms/teardowns/MAGENTIC_ONE.md` (1337 L)

Labels carried through: KNOWN = from source code w/ file:line (per teardown), KNOWN-PAPER = arxiv tables, INFERRED = my extraction judgment.

Verso state tag legend: [HAVE] = Verso already ships, [STEAL] = additive on-thesis gap, [AVOID] = overkill Verso should refuse, [CTX] = neutral context.

---

## 1. What AutoGen v0.4 is

KNOWN. AutoGen rebuilds "agent" as **an actor in a typed message-passing system**. Each agent: has `AgentId(type: str, key: str)`; implements `on_message(message, ctx) -> response`; lives in an `AgentRuntime` (default `SingleThreadedAgentRuntime` = one asyncio queue). Communicates via direct messaging `runtime.send_message(message, recipient=AgentId)` (RPC → Future) OR pub/sub `runtime.publish_message(message, topic=TopicId)` (fan-out). "This is actor model (Erlang/Akka) applied to LLM agents. There's no shared state." [AVOID — orchestrator/actor-runtime as primitive is exactly Verso's NON-GOAL "no orchestrator-as-primitive"; Verso is one async ReAct loop, not a message bus.]

Repo: 69,016 lines of `.py` excluding tests. Multi-package monorepo (autogen-core, autogen-agentchat, autogen-ext, autogen-magentic-one, autogen-studio…). **Now in maintenance mode** — README: "AutoGen is now in maintenance mode. It will not receive new features... New users should start with Microsoft Agent Framework (MAF)." [CTX]

---

## 2. The single-agent loop — `AssistantAgent.on_messages_stream`

KNOWN (`_assistant_agent.py:901`). Steps: (1) add user/handoff msgs to model_context; (2) `_update_model_context_with_memory` (memory queries itself, yields `MemoryQueryEvent`); (3) gen message_id for streaming; (4) first inference via `_call_llm`; emit `ThoughtEvent` if `model_result.thought` present (reasoning models); (5) `_process_model_result` tool-call loop.

### CRITICAL DEFAULT: `max_tool_iterations = 1` (KNOWN `_assistant_agent.py:85`)
"With the default, the agent makes ONE model call, executes its tool calls in parallel, then either reflects or summarizes — no further model calls. This is unlike LangChain which loops until AgentFinish. AutoGen's design pushes multi-step looping into the GroupChat layer instead." [CTX — opposite philosophy to Verso. Verso's ReAct loop IS intra-agent. AutoGen forces multi-step into the team/orchestrator; Verso explicitly refuses the graph.]

### `_process_model_result` (KNOWN `:1118`) tool-call loop termination paths:
1. Model returns `str` → wrap `TextMessage` (or `StructuredMessage` if `output_content_type` set), yield `Response`, exit.
2. Tool call is a handoff → yield `HandoffMessage`, exit (group chat routes to target).
3. `loop_iteration == max_tool_iterations - 1` → break, fall to summarize/reflect.
Tools executed in parallel via `asyncio.gather` over `_execute_tool_call`. [HAVE — Verso has done() termination, output_type in-loop reask, parallel tool exec.]

### Reflect vs summarize after loop (KNOWN `:138-147`):
- `reflect_on_tool_use=False` (default no structured output): concat results with `tool_call_summary_format` (Python format string `{tool_name}/{arguments}/{result}`, default `"{result}"`) → `ToolCallSummaryMessage`. **No second LLM call.**
- `reflect_on_tool_use=True` (default when `output_content_type` set): second LLM inference reflecting on tool results.
- `tool_call_summary_formatter: Callable[[FunctionCall, FunctionExecutionResult], str]` callable form. [HAVE — Verso prune()/context-engineering covers this; the format-string summary is a minor knob.]

---

## 3. Tools — `BaseTool` + `Workbench`

KNOWN. `BaseTool(ABC, Generic[ArgsT, ReturnT])` with `name/description/args_type (Pydantic)/return_type/state`, `async run(args, cancellation_token)`. `FunctionTool(func, description, name, strict=False)` inspects signature → Pydantic model → JSON Schema. [HAVE — Verso @tool docstring→schema.]

`Workbench(ABC)`: `list_tools()`, `call_tool(name, args, ct) -> ToolResult`. Impls: `StaticStreamWorkbench(tools=[...])` (default), `McpWorkbench(server_params)` (autogen-ext[mcp]). KNOWN rationale: **"designed to support DYNAMIC tool sets: an MCP server can add/remove tools while the agent is running, so the workbench is queried at each turn"** — `tools = [t for wb in workbench for t in await wb.list_tools()] + handoff_tools` (`:1088`). [STEAL-candidate but weak — Verso has tool registry + MCP adapter; per-turn re-query of a dynamic toolset is a small additive hook IF MCP-dynamic-tools matters. Bar is high; likely [HAVE]/neutral since Verso's tool list is per-call.]

`ToolResult` has `name, result, is_error, stream` chunks. Honest gap noted: "Tool error handling is minimal. Failures propagate up unless the tool explicitly catches them; there's no handle_tool_error policy like LangChain's." [HAVE — Verso has per-tool idempotent/max_attempts/timeout, quarantine trust-tier — MORE than AutoGen here.]

---

## 4. Handoffs — peer-to-peer routing

KNOWN. `Handoff(BaseModel)`: `target: str`, `description`, `name="handoff_to_<target>"`, `message`. Passing `handoffs=["Bob"]` synthesizes a no-arg Pydantic tool added to `handoff_tools`. LLM calls `handoff_to_Bob()`; `_check_and_handle_handoff` (`:1327`) builds `HandoffMessage(content, source, target)`, exits; Swarm routes next turn to target. [AVOID — handoff-as-control-transfer is multi-agent routing; Verso NON-GOAL is no router/planner cult, no orchestrator-as-primitive.]

---

## 5. Model client abstraction

KNOWN. `ChatCompletionClient(ABC)`: `create(messages, *, tools, json_output, extra_create_args, cancellation_token) -> CreateResult`; `create_stream(...) -> AsyncGenerator[str|CreateResult]`; `model_info() -> ModelInfo`.

`CreateResult`: `finish_reason: Literal["stop","length","function_calls","content_filter","unknown"]`, `content: str|list[FunctionCall]`, `usage: RequestUsage`, `cached: bool`, `logprobs`, `thought: str|None`.

`ModelInfo (TypedDict)`: `vision, function_calling, json_output, structured_output, family, multiple_system_messages` — drives feature gates (vision=False → strip images; function_calling=False → no tools). [STEAL-additive-weak — a typed `model_info` capability TypedDict that gates features (strip images, disable tools, choose SystemMessage vs UserMessage per family) is additive + byte-identical-when-unused. Verso has adapters/error-taxonomy/per-call swap; an explicit *capability descriptor* per model that the loop reads to gate behavior may be a genuine small gap. Bar: high, but on-thesis (context-engineering / reliability).]

Provider clients (hand-written, NO LiteLLM): OpenAI, AzureOpenAI, Anthropic, Ollama, LlamaCpp, SemanticKernel, **ReplayChatCompletionClient** (replays recorded sequence for testing), **CacheChatCompletionClient** (wraps any client w/ cache). [HAVE — Verso has anthropic/openai/google + any OpenAI-compatible base_url, FailoverModel, RetryPolicy. ReplayChatCompletionClient is a test-double = arguably [HAVE] via Verso evals/captured-trace.]

Cross-provider portability detail (KNOWN `_selector_group_chat.py:241`): selector prompt sent as `SystemMessage` for OpenAI, `UserMessage` for other families (`ModelFamily.is_openai(...)`). [CTX — real portability concern; Verso's adapter layer is where this'd live.]

---

## 6. Actor runtime (the heavy machinery — Verso AVOID territory)

KNOWN `SingleThreadedAgentRuntime` (1,029 L). asyncio `Queue` of envelopes: `PublishMessageEnvelope` (pub/sub), `SendMessageEnvelope` (RPC w/ Future), `ResponseMessageEnvelope` (RPC return). Methods: `start/stop/stop_when_idle/stop_when(cond)`, `send_message`, `publish_message`, `register_factory(type, factory, expected_class)`, `register_agent_instance`, `add_subscription`, `agent_save_state/load_state`.

Doc: **"This runtime is suitable for development and standalone applications. It is not suitable for high-throughput or high-concurrency scenarios."** (`:156`). `ignore_unhandled_exceptions=True` default. [AVOID — entire actor runtime + envelope dispatcher + serialization registry + gRPC distributed transport is the kind of machinery Verso's thesis explicitly cuts ("brutal, no 500+ nodes", "we don't force the graph").]

Intervention handlers (`_intervention.py:83`): intercept any message via `on_send/on_publish/on_response`, return `DropMessage` to drop, modified message to mutate, raise to abort. Used for security filters, debugging, rate limiting. [CTX — conceptually like Verso Hooks(pre/post_model, pre/post_tool), but Verso's hooks are loop-level not message-bus-level. Verso [HAVE] the intent.]

`RoutedAgent` + `@message_handler` (KNOWN `:518`): type-based dispatch via Python `__class__`/MRO. [AVOID — typed-message-bus dispatch; not Verso's model.]

`AgentId.type` regex `^[\w\-\.]+\Z`, wire format `type/key`. `TopicId.type` regex `^[\w\-\.\:\=]+\Z` (CloudEvents-compatible, allows `:` and `=` → `chat.message:room=42`). `TypeSubscription.map_to_agent` uses **topic source as agent key** → per-user agent instances `AgentId(type="chatbot", key="user_123")`. [AVOID.]

`GrpcWorkerAgentRuntime` (~856 L): distributed actors over gRPC bidirectional streams; **publishes wire-encoded as CloudEvents v1.0**; protobuf RPC for Send/Response. Host = single point of failure/bottleneck. [AVOID — Python-only, no-distributed-runtime is Verso's lane.]

---

## 7. Group chat patterns (4) — multi-agent coordination

KNOWN. All share `BaseGroupChatManager` (`SequentialRoutedAgent`); the manager IS the loop, agents never talk directly (star topology).

| Pattern | Speaker selection | File |
|---|---|---|
| `RoundRobinGroupChat` | `(idx+1) % len(participants)` cyclic | `_round_robin_group_chat.py:16` |
| `SelectorGroupChat` | LLM picks via `selector_prompt` | `_selector_group_chat.py:50` |
| `Swarm` | last `HandoffMessage.target` | `_swarm_group_chat.py:15` |
| `MagenticOneGroupChat` | orchestrator fact+plan+progress ledger | `_magentic_one/` |

Also `Graph` group chat (DAG of agents, fixed-handoff edges) and `SocietyOfMindAgent` (wraps a whole Team as one agent). [AVOID — all of this is multi-agent orchestration = Verso NON-GOAL.]

### SelectorGroupChat config (KNOWN `:595`):
`model_client`, `selector_prompt`, `allow_repeated_speaker=False`, `max_selector_attempts=3`, `selector_func`, `candidate_func`. On parse fail appends `"Invalid response. Please pick from one of {participants}."` and retries. Default selector prompt verbatim ("You are in a role play game. The following roles are available: {roles}..."). [CTX]

### SocietyOfMindAgent (KNOWN `:111-119`) verbatim default prompts:
- `DEFAULT_INSTRUCTION = "Earlier you were asked to fulfill a request. You and your team worked diligently to address that request. Here is a transcript of that conversation:"`
- `DEFAULT_RESPONSE_PROMPT = "Output a standalone response to the original request, without mentioning any of the intermediate discussion."`
- Flow: run inner team → `[SystemMessage(INSTRUCTION), *inner_transcript_as_user_messages, SystemMessage(RESPONSE_PROMPT)]` → synthesize → `team.reset()`. [AVOID — nested-team-as-agent.]

---

## 8. MagenticOne orchestrator — the dual-ledger pattern (HIGHEST-PRIORITY novelty)

KNOWN `_magentic_one_orchestrator.py` (536 L). Two ledgers:
- **Task Ledger** (outer loop): closed-book *facts* + *plan*, regenerated on stall.
- **Progress Ledger** (inner loop): JSON every turn, 5 questions, **same LLM call that judges progress also nominates speaker + issues instruction → 1 LLM call/turn for routing+progress combined.**

### Per-turn flow (KNOWN `:262-449`):
```
OUTER (handle_start): facts ← LLM(facts_survey); plan ← LLM(plan); broadcast ledger_full; → inner
INNER (per turn):
  n_rounds += 1; if n_rounds > max_turns(20): final_answer
  progress_ledger ← LLM(progress_prompt) -> JSON   (retried up to max_json_retries=10)
  if is_request_satisfied: final_answer; return
  if not is_progress_being_made: n_stalls += 1
  elif is_in_loop:             n_stalls += 1
  else:                        n_stalls = max(0, n_stalls-1)   # HYSTERESIS — heals
  if n_stalls >= max_stalls(3): update_task_ledger(); reenter_outer_loop(); return
  broadcast(instruction_or_question); request_publish(next_speaker)
```

### Stall hysteresis (KNOWN `:393-406`) — ARCHITECTURALLY MEANINGFUL:
"progress *decrements* stall counter (min 0), but loop OR no-progress *increments* it. So one bad turn isn't enough — you need three sequential bad turns." [STEAL-additive — Verso has StopReason.STUCK / doom-loop detection (single-signal). A **decrement-on-progress hysteresis counter** (n_stalls += 1 on no-progress-or-loop, n_stalls = max(0, n-1) on progress, escalate at threshold) is a more forgiving stuck-detector. Additive, byte-identical when threshold never hit, on-thesis (reliability). Genuinely sharper than a flat strike count. HIGH-VALUE.]

### The 5 progress-ledger questions (KNOWN, JSON schema):
`is_request_satisfied`, `is_in_loop`, `is_progress_being_made`, `next_speaker`, `instruction_or_question` — each `{reason: string, answer: bool|string}`. Validated against Pydantic `LedgerEntry` (LedgerEntryBooleanAnswer / LedgerEntryStringAnswer). Passed directly as `json_output=LedgerEntry` when client supports structured output (`:319-321`), else free-form JSON then re-parse. [CTX — the "is_in_loop / is_progress_being_made" self-judged-progress-ledger is an LLM-judge-of-own-trajectory pattern; Verso has TrajectoryCheck + LLMJudge in evals. The novelty is using it INLINE as a control signal.]

### JSON-retry + validation (KNOWN `:316-384`):
`_max_json_retries = 10`. Required-key validation over the 5 keys (each must be dict w/ `answer` + `reason`). `next_speaker.answer` must be a real participant unless task done. Single-agent shortcut (`:342-346`): if `len(participants)==1`, auto-set next_speaker. After 10 retries: `raise ValueError("Failed to parse ledger information after multiple retries.")`. [HAVE — Verso jsonish 4-stage parse waterfall + Retry(feedback) self-healing covers JSON robustness more elegantly than a 10× retry loop.]

### Persistence (KNOWN `:225-245`):
`MagenticOneOrchestratorState(message_thread, current_turn, task, facts, plan, n_rounds, n_stalls)` — serializable Pydantic; paused run resumable mid-task. [HAVE — Verso durable seam: SqliteCheckpointStore, checkpoint each step, resume() in fresh process — far more general than a single hand-rolled state model.]

### Topology (KNOWN `:435-440`): pub/sub star, NOT handoffs. `participant_topic_type` (private inbox), `group_topic_type` (broadcast), `output_topic_type` (UI). Orchestrator at center; "agents never call each other." [AVOID.]

### Constants (KNOWN): `max_turns=20`, `max_stalls=3`, `max_json_retries=10` (M1) / `3` (Magentic-UI), `ORCHESTRATOR_SYSTEM_MESSAGE = ""` (empty — all behavior in per-turn user prompts). [CTX]

### The 6 verbatim orchestrator prompts (KNOWN `_prompts.py:6-149`):
1. **FACTS** (`ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT`): closed-book pre-survey. Priming line is **load-bearing**: *"Keep in mind that you are Ken Jennings-level with trivia, and Mensa-level with puzzles."* 4 headings: GIVEN OR VERIFIED FACTS / FACTS TO LOOK UP / FACTS TO DERIVE / EDUCATED GUESSES.
2. **PLAN** (`..._PLAN_PROMPT`): "devise a short bullet-point plan... there is no requirement to involve all team members."
3. **FULL** (`..._FULL_PROMPT`): broadcast task+team+facts+plan to all on every outer-loop entry; then `GroupChatReset` to every participant.
4. **PROGRESS LEDGER** (`..._PROGRESS_LEDGER_PROMPT`): the 5 questions → strict JSON ("DO NOT OUTPUT ANYTHING OTHER THAN JSON").
5. **FACTS_UPDATE / PLAN_UPDATE** (on stall): "please at least add or update one educated guess or hunch, and explain your reasoning" / "briefly explain what went wrong on this last run (the root cause)... new plan that avoids repeating the same mistakes."
6. **FINAL_ANSWER**: "We have completed the task... provide the final answer... phrased as if you were speaking to the user."
[STEAL-additive-weak — the **closed-book facts pre-survey + explicit-replan-on-stall-with-root-cause** is a reusable scaffold prompt pattern. Verso has scaffolds (load_skills, "# SCAFFOLD()" ratchet, verify-before-done). A "facts/plan ledger" scaffold is additive but borders on planner-cult NON-GOAL; the *root-cause-then-replan-on-stall* prompt is the on-thesis bit.]

KNOWN-PAPER ablation: removing orchestrator (→ RoundRobinGroupChat) drops GAIA 38.0% → 31.9% (~6pp); using o1-preview as orchestrator only = 38.8% (statistically tied). "the orchestrator-ledger pattern is the win, not the underlying model." [CTX]

---

## 9. Magentic-One worker agents (5)

KNOWN (`magentic_one.py:209-221`). All share one `model_client` by default; capability check `_validate_client_capabilities` requires `function_calling=True`, `json_output=True`, warns if not `BaseOpenAIChatCompletionClient`.

### WebSurfer (MultimodalWebSurfer, 988 L) — 13 tools, Set-of-Mark:
9 default tools + 2 conditional (visit_url, web_search, history_back, click, input_text, read_page_and_answer, summarize_page, sleep, hover) + scroll_up/down added **conditionally per turn based on viewport** (KNOWN `:511-516`):
```python
if viewport["pageTop"] > 5: tools.append(TOOL_SCROLL_UP)
if (viewport["pageTop"]+viewport["height"]+5) < viewport["scrollHeight"]: tools.append(TOOL_SCROLL_DOWN)
```
**"the LLM is never given a scroll_up tool when there's nothing above the viewport. This is dynamic tool filtering based on environment state — reduces hallucinated tool calls."** [STEAL-additive — environment-state-conditioned tool availability (only expose a tool when its precondition holds) is a genuinely sharp, additive idea. Verso has trust-tier/quarantine + per-tool config but tools are otherwise static per call. A predicate-gated tool ("available_when") is byte-identical-when-unused, on-thesis (reduces error / context discipline). HIGH-VALUE.]

`reasoning` param REQUIRED on every tool (KNOWN `:18-19`): "A short description of the action... and reason for doing so." Forces CoT inside the tool call; orchestrator sees *why*. [STEAL-additive-weak — a per-tool mandatory `reasoning` arg is a cheap legibility lever; Verso could expose as opt-in tool decorator flag. Additive, on-thesis (evals/legibility).]

Set-of-Mark (KNOWN `_set_of_mark.py`): numbered bounding boxes, **deterministic per-id color seeded by element id** (`random.Random(int(identifier))`) → "same id = same color across runs → less perceptual drift." Constants: VIEWPORT 1440×900, MLM 1224×765 (0.85× for GPT-4v 768px limit), SCREENSHOT_TOKENS=1105. [CTX — browser-vision-specific, out of Verso scope.]

MD5 metadata-hash dedup (KNOWN `:770-818`): don't repeat unchanged page metadata to save tokens / reduce confusion. [CTX — Verso prune() masks old tool outputs; conceptually adjacent [HAVE].]

QA-summarize buffer-growing loop (KNOWN `:874-953`): grow buffer line-by-line, call `model_client.remaining_tokens(messages+[trial])` each iter, stop when remaining ≤ 0 (or ≤1105 for vision). "dynamic context packing." [HAVE — Verso max_context_tokens + prune.]

### FileSurfer (208 L) — 5 read-only tools:
`open_path`, `page_up`, `page_down`, `find_on_page_ctrl_f` (supports `*` wildcards → regex `.*`), `find_next`. **No editing** (editing is Coder's job). Backed by `MarkItDown` (PDF/DOCX/XLSX/PPTX/HTML/image-OCR/audio-Whisper → Markdown). `viewport_size=5120` chars (M1) / 8192 default.
**Path sandboxing (KNOWN `:67-86`) — a real security boundary, not convention:**
```python
def _validate_path(self, path):
    if self._base_path is None: return True
    if os.path.commonpath([os.path.realpath(path), os.path.realpath(self._base_path)]) != base: return False
    return True
```
[STEAL-additive-weak — a `commonpath`-based path-jail predicate for any file-touching tool is additive + on-thesis (agent-security). Verso has trust-tier/quarantine + permission 4-valued; a ready-made path-confinement helper is a small concrete gap.]

### Coder (MagenticOneCoderAgent, 41 L) — NO TOOLS, sealed prompt:
Pure code-generation `AssistantAgent`; execution delegated to ComputerTerminal. Verbatim sealed system message directives: "Don't include multiple code blocks in one response", mandatory language tag (```python/```sh), "do not suggest incomplete code which requires users to modify", and final: **"When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible."** Class docstring: "The prompts and description are sealed, to replicate the original MagenticOne configuration." [CTX — verify-the-answer directive aligns w/ Verso verify-before-done gate [HAVE].]

### ComputerTerminal (CodeExecutorAgent, 893 L) — Docker by default:
Extracts ```python/```sh blocks (regex `r"```(\w+)?\n(.*?)```"`), runs via `code_executor.execute_code_blocks`. **Optional approval gate** (KNOWN `magentic_one.py:198,215`): `approval_func(ApprovalRequest(code=...)) -> ApprovalResponse(approved: bool, reason: str)`; if not approved returns reason instead of executing. "the action-guard primitive." [HAVE — Verso Hooks.ask + PermissionDecision 4-valued (allow/deny/ask/defer) + ask_once durable persistence is MORE general than approval_func.]

5 CodeExecutor impls: Local, **DockerCommandLineCodeExecutor** (image="python:3-slim", timeout=60s/block, auto_remove=True, work_dir mounted, GPU passthrough via device_requests), DockerJupyter, Jupyter, AzureContainer. Doc: **"This is not a security boundary"** — "Magentic-One may be susceptible to prompt injection attacks from webpages" → recommend running entire host in a container. [CTX — sandboxing is real but Verso is Python lib not a sandbox provider; out of scope.]

### UserProxyAgent (optional, hil_mode):
`input_func: Callable[[str], str] | Callable[[str, CancellationToken], Awaitable[str]]`, defaults to blocking `input()`. Doc warning: "Using UserProxyAgent puts a running team in a temporary blocked state until the user responds." Best practice: `HandoffTermination(target="user")` to STOP team, resume externally. [HAVE — Verso ctx.hitl.request pause/resume (idempotent), durable — strictly better than blocking input().]

---

## 10. Context management — `ChatCompletionContext` (the compaction algorithms)

KNOWN (`autogen_core/model_context/`). ABC: `add_message`, `get_messages`, `clear`. 4 variants w/ verbatim `get_messages()`:

- `UnboundedChatCompletionContext`: returns all.
- `BufferedChatCompletionContext(buffer_size=N)`: `messages[-N:]`, then **drop orphan leading `FunctionExecutionResultMessage`** (its FunctionCall was sliced out → providers reject).
- `HeadAndTailChatCompletionContext(head, tail)`: keep first H + last T, drop orphan trailing-FunctionCall-AssistantMessage in head + orphan leading-result in tail, insert literal placeholder `UserMessage("Skipped {num_skipped} messages.", source="System")`. "Models read this and know there was a gap — they don't try to reconstruct it."
- `TokenLimitedChatCompletionContext(model_client, token_limit)` [@experimental, v0.4.10]: **drops from the MIDDLE** — `messages.pop(len(messages)//2)` in a while-loop re-counting tokens, preserving head (system) + tail (recent). "more sophisticated than the standard drop-oldest."

[STEAL-additive — two concrete bits:
(a) **orphan-tool-pair repair on truncation** (drop a dangling FunctionExecutionResultMessage / trailing FunctionCall when a slice splits a tool-call pair). Verso HAS repair_history resume-guard (orphan tool-call/result repair) at the durable seam — so this is largely [HAVE], but applying the same repair inside *context truncation* (not just resume) may be an additive surface.
(b) **middle-drop truncation preserving head+tail** + **explicit "Skipped N messages" sentinel** (never silent-drop). Verso prune() masks old tool outputs and "never silent-drops" — strongly aligned [HAVE]. The middle-pop + visible-skip-count sentinel is an additive prune strategy worth noting. On-thesis (context-engineering).]

---

## 11. Memory — `autogen_core.memory.Memory`

KNOWN. ABC: `query(query) -> MemoryQueryResult`, `add(content)`, `update_context(model_context) -> UpdateContextResult` (the hook AssistantAgent calls before each turn — memory queries itself, adds relevant content as messages), `clear()`. Impls: `ListMemory` (no semantic search), `ChromaDBVectorMemory`, `Mem0Memory`, `RedisMemory`. [HAVE — Verso typed 4-tier memory, RRF recall, recall_as_of time-travel, reflect() consolidation, sqlite/sqlitevec/inmem — far richer.]

State: `agent.save_state()/load_state(state)` JSON dict; `team.save_state()/load_state()`. "essentially the same shape as LangGraph's Checkpointer but **manual** — no automatic per-step persistence, no time-travel between checkpoints; you can only restore the most recent state." [HAVE — Verso checkpoint each step + history()/fork() time-travel is strictly more capable.]

---

## 12. Termination conditions

KNOWN. `TerminationCondition` subclasses, compose with `|` (OR) `&` (AND): `MaxMessageTermination(N)`, `TextMentionTermination(text)` (e.g. "TERMINATE"), `StopMessageTermination()`, `FunctionalTermination(callable)`, `TokenUsageTermination(max_prompt, max_completion)`, `HandoffTermination(target)`, `SourceMatchTermination(sources)`, `ExternalTermination()` (`.set()` from outside), `TimeoutTermination(seconds)`. Example: `MaxMessageTermination(10) | TextMentionTermination("DONE")`. [HAVE — Verso has max_steps_policy, done() tool, StopReason taxonomy. Composable `|`/`&` termination DSL is a nice ergonomic but team-scoped; Verso's loop-level stop reasons cover the intent. Possibly minor [STEAL] for composable stop-conditions, but bordering on overkill.]

---

## 13. Streaming protocol

KNOWN `team.run_stream(task)` yields typed events: `ModelClientStreamingChunkEvent`, `ThoughtEvent`, `MemoryQueryEvent`, `ToolCallRequestEvent`, `ToolCallExecutionEvent`, `StructuredMessage`/`TextMessage`, `HandoffMessage`, `ToolCallSummaryMessage`; team-level `GroupChatStart`/`GroupChatTermination`, `TaskResult(messages, stop_reason)`. [HAVE — Verso typed true-delta events (message/reasoning/tool.start/tool.result/done) + SSE.]

---

## 14. Component serialization — `Component[Config]`

KNOWN (`_component_config.py`, 407 L). ~50 primitives implement `Component[XConfig]` (Pydantic). 3 powers: `dump_component() -> ComponentModel` (`{provider, component_type, version, component_version, description, label, config}`); `load_component(model, expected_type)` (rehydrate by provider path, validate config, `_from_config`); `to_config()/_from_config()`. Powers AutoGen Studio's visual team builder — entire team as one JSON. `${OPENAI_API_KEY}` placeholder interpolated at load (secrets never serialized). `component_provider_override` for renames. [AVOID — declarative team-as-JSON config graph is SDK/Studio machinery; Verso NON-GOAL "not an SDK, not a graph-DSL by default". Don't copy.]

---

## 15. Magentic-UI (2025 successor) — what changed

KNOWN. Same orchestrator-ledger, + co-planning + sentinel-tasks + plan-learning.

`OrchestratorConfig` (47 L) knobs: `cooperative_planning=True` (human approves plan before exec), `autonomous_execution=False`, `allow_for_replans=True`, `max_json_retries=3`, `saved_facts`, `allowed_websites` (URL allowlist), `retrieve_relevant_plans: Literal["never","hint","reuse"]`, `memory_controller_key`, `max_replans=3`, `sentinel_plan`.

- **Co-planning**: plan JSON w/ `needs_plan` bool; clarify-once-then-plan. [CTX]
- **SentinelPlanStep** (the "Tell me When" primitive): `{step_type:"SentinelPlanStep", condition:"<times OR completion-condition>", sleep_duration:"<seconds>"}` — "monitor X every 60s until Y... wakes itself up, runs agent, then sleeps — for hours or days." [STEAL-additive-weak — a durable long-running "monitor until condition" step is interesting but leans toward orchestration/scheduling; Verso durable seam + hitl could express it but it's arguably beyond the boring core. Note, don't rush.]
- **Magentic-UI progress ledger = 3 questions** (not 5): `is_current_step_complete`, `need_to_replan`, `instruction_or_question`+`agent_name`, `progress_summary`. "steps are now first-class (orchestrator tracks step_index)." [CTX]
- **Plan learning**: `retrieve_relevant_plans` never/hint/reuse — top-k past plan as starting point. [AVOID — learned-plan-reuse borders on Verso NON-GOAL "no learned routers".]
- `allowed_websites` URL allowlist gating WebSurfer visit_url/clicks. [HAVE-intent — Verso permission/trust-tier.]

KNOWN-PAPER numbers: M1 GAIA-val 38.0% (3-trial), AssistantBench 27.7%, WebArena 32.8%. Per-level GAIA: L1 56.6% / L2 39.1% / L3 18.1%. Magentic-UI o4-mini: GAIA test 42.52%, AssistantBench 27.60%, WebVoyager 82.2%, WebGames 45.5%. [CTX]

---

## 16. Honest gaps the teardown flags (AutoGen's own NON-features)
- No first-class persistence (manual save_state, no checkpointer protocol, no time-travel). [Verso wins.]
- Single-threaded local runtime "not production-grade" (their words).
- Maintenance mode, no new features.
- Heavy workers (Playwright + Docker).
- Minimal tool error handling (no handle_tool_error policy). [Verso wins.]
- No built-in observability viz (OTel wired, but you point it at Jaeger/Datadog).

---

## 17. Net verdict vs Verso thesis
The actor-runtime + 4 group-chat patterns + MagenticOne orchestrator are textbook "force the graph / orchestrator-as-primitive" — exactly Verso's counter-position. ~9,500 LoC to clone (teardown's own estimate). The genuinely stealable, additive, byte-identical-when-unused, on-thesis bits are SMALL and reliability/context-flavored: (1) stall-hysteresis counter, (2) environment-state-conditioned tool availability, (3) mandatory per-tool `reasoning` arg, (4) typed model capability descriptor gating loop behavior, (5) commonpath path-jail tool helper, (6) middle-drop+visible-skip-sentinel prune strategy. Everything orchestration/runtime/serialization-shaped is AVOID.
