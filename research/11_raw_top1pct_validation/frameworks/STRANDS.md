# STRANDS (AWS) — Raw Extraction (Verso validation lens)

Source read in full: `/Users/seventyleven/Desktop/researchfms/teardowns/STRANDS.md` (427 lines, RE teardown of `strands-agents/sdk-python`, Python SDK at `strands-py/src/strands`, clone 2026-05-30). All `file:line` cites below are the teardown's, against that tree. Labels KNOWN/INFERRED/DESIGNED are the teardown's.

---

## Thesis (verbatim, teardown §0/header)
> "Strands is AWS's **compact, model-driven, recursive event loop**. The core is ~700 lines (`event_loop/event_loop.py`): invoke model → read `stop_reason` → if `tool_use`, run tools, append results as a user message, **recurse** → repeat until `end_turn` / a budget cap / `max_tokens`. No graph engine, no scratchpad string — the loop IS the recursion, and the model decides everything."

> "Strands is the 'thin loop, fat model' school: correctness lives in the model + the recursion, not in a DSL." (§0, line 13)

This is the SAME bet as Verso's "boring core done right" — a strong external confirmation. Default model: Claude Sonnet 4.6 on Bedrock.

Core file sizes (KNOWN, `wc -l`, line 15): `event_loop/event_loop.py` **716**, `streaming.py` **515**, `agent/agent.py` **1280**, `models/bedrock.py` **1265**, `multiagent/graph.py` **1296**, `multiagent/swarm.py` **1064**, `tools/decorator.py` **833**. (Verso's claim is <200 lines for the loop; Strands' loop is ~716 — Verso is LEANER on the core.)

---

## 1. The execution engine — `event_loop_cycle` (recursion-based)

KNOWN, `event_loop.py:157`, `async def event_loop_cycle(agent, invocation_state, structured_output_context, limits) → AsyncGenerator[TypedEvent]`.

Structure (verbatim from §1.3):
- `_check_limits` at top of every cycle (`:204`).
- Model phase: skip if resuming from interrupt (`agent._interrupt_state.activated`) or if last msg already has toolUse (`_has_tool_use_in_latest_message`).
- Dispatch on `stop_reason`:
  - `max_tokens` → `raise MaxTokensReachedException("unrecoverable … max_tokens limit")` — **HARD FAIL by default** (`:264-278`, "Strands fails hard by default to match other failure types").
  - `tool_use` → `_handle_tool_execution`; **recursion happens INSIDE** that fn (`:62`).
  - `end_turn` → if structured-output pending+unforced, append forcing prompt + recurse; else `EventLoopStopEvent`.
- Exceptions `StructuredOutputException / EventLoopException / ContextWindowOverflowException / MaxTokensReachedException` bubble un-wrapped (`:327`); any other → `ForceStopEvent` then `EventLoopException`.

**Recursion as the loop primitive** (`recurse_event_loop`, `:344`): trivial — emit `StartEvent`, then `async for event in event_loop_cycle(...)` re-yield. Recursion depth = number of tool-use turns. Budget caps + model's `end_turn` terminate it. (Verso uses an explicit async while-loop; Strands recurses. Different shape, same semantics. Verso's iterative form is arguably cleaner for stack/observability.)

### Budget caps — `_check_limits` (`:59`)
Per-invocation `Limits = {turns?, total_tokens?, output_tokens?}`. Reads `agent.event_loop_metrics.latest_agent_invocation` — **scoped to the current invocation so caps don't fire on a reused agent's second call**. Priority on simultaneous trip: **`turns → total_tokens → output_tokens`** (`:64`). Returns a `StopReason` (`"limit_turns"|"limit_total_tokens"|"limit_output_tokens"`) or None.

### Retry budget — module constants (`event_loop.py:54`, KNOWN)
```python
MAX_ATTEMPTS = 6
INITIAL_DELAY = 4
MAX_DELAY = 240  # 4 minutes
```
Backoff schedule `4 → 8 → 16 → 32 → 64` (`_retry.py:28`), 5 retries before failing on 6th. `ModelRetryStrategy` (`_retry.py:21`) is itself a `HookProvider`; retries only on `ModelThrottledException`. `delay = min(initial_delay * 2**attempt, max_delay)`.

### `_recover_message_on_max_tokens_reached.py`
When `max_tokens` truncates mid-tool-call, repairs the partial assistant message (drops incomplete toolUse) so the conversation stays valid even though the cycle raises. (KNOWN — directly parallels Verso's `repair_history` resume-guard / orphan tool-call repair. verso-already-has.)

### HITL via tool interrupts (`_handle_tool_execution`, ~`:555`)
A tool can **raise an interrupt** (human input). The loop saves `{tool_use_message, tool_results}` into `agent._interrupt_state` and stops; on resume the **model phase is skipped** (saved `tool_use_message` reused). This is the same idempotent pause/resume Verso ships as `ctx.hitl.request`. verso-already-has.

---

## 2. Models — wide matrix, Bedrock default
`models/` (KNOWN): `bedrock.py`(default), `anthropic.py`, `openai.py`, `openai_responses.py`, `litellm.py`, `gemini.py`, `mistral.py`, `ollama.py`, `llamaapi.py`, `llamacpp.py`, `sagemaker.py`, `writer.py`, `_openai_bedrock.py`. All implement `Model`: `async stream(messages, tool_specs, system_prompt, **kwargs) → AsyncGenerator[StreamEvent]` + `structured_output(...)`.

BedrockModel (`bedrock.py`): `DEFAULT_BEDROCK_MODEL_ID = "global.anthropic.claude-sonnet-4-6"` (`:42`). `streaming: bool = True` (`:114`). **Guardrails first-class** (`:95-137`): `guardrail_id/version/trace`, redact_input default True / redact_output default False, `guardrail_latest_message`. Prompt caching via `cachePoint` blocks. (Guardrails-wired-into-converse is AWS-specific overkill for Verso to copy verbatim; Verso's hooks + trust_tier cover the generic case.)

---

## 3. Tools — `@tool` (docstring → spec)
`tools/decorator.py` (833 L). `FunctionToolMetadata` (`:79`): `docstring_parser.parse(func.__doc__)` for name+description (`:110`), per-arg descriptions from docstring Args (`:111`), Pydantic `create_model(...)` from signature → `inputSchema.json`. **"the docstring IS the tool description and the type hints ARE the schema — zero boilerplate."** Identical philosophy to Verso's `@tool`. verso-already-has.

Description priority (CE-1, `:161-167`): **Annotated-string > docstring-param-desc > `f"Parameter {name}"`**.

`context_param` (CE-1, `:93,104,175-180`): a named param (e.g. `tool_context`) is injected at call time with `ToolContext{agent, tool_use, invocation_state}` instead of appearing in the schema; must match the configured name exactly or it raises. **This is how a tool reaches the agent/session handle without polluting its public JSON schema.** Verso has `ctx.deps` typed injection in the durable seam, but a per-tool, schema-excluded injected handle is a clean named primitive worth noting (likely steal-additive if Verso lacks a tool-level injected context handle).

Other machinery: hot-reload via `watchdog` `ToolWatcher` (`watcher.py`); `tool_choice` plumbed to provider (force/disable per call); MCP merged into registry; `validate_and_prepare_tools` (`_validator.py`) splits valid/invalid before execution — **invalid tool uses get an immediate error `ToolResult` so the model can self-correct** (CE-2). verso-already-has (jsonish waterfall + coerce + reask cover this).

ToolUse/ToolResult (`types/tools.py`): `ToolUse{toolUseId, name, input}`, `ToolResult{toolUseId, status:'success'|'error', content:[ContentBlock]}` — Converse-shaped.

### Tool executors — concurrency (§13)
`ConcurrentToolExecutor` (default, `concurrent.py:19`, `agent/agent.py:63`): builds a task per tool use and `await asyncio.gather(*tasks, return_exceptions=True)` (`:90`) — **all tool calls in one turn run concurrently; one failing tool doesn't abort the others** (per-task exception capture). Results keyed by `toolUseId`, appended as ONE user message of `toolResult` blocks, so concurrent completion order is irrelevant. `SequentialToolExecutor` (`sequential.py:18`) for ordering/side-effect deps. **Pluggable executor is a clean primitive.** (Verso runs tools in its loop; in-turn parallel tool execution with per-task exception isolation MAY be a genuine additive gap — steal candidate, byte-identical when unused if default stays sequential-or-existing.)

---

## 4. Structured output — forced tool (two-phase)
`tools/structured_output/`. `Agent.structured_output(MyPydanticModel, prompt)` = **register the Pydantic model as a synthetic tool and force the model to call it**.

`StructuredOutputContext` (`_structured_output_context.py:19`): tracks `forced_mode`, `force_attempted`, `tool_choice`, `structured_output_prompt`. Flow (`event_loop.py:303-323`):
1. Model first allowed to call the SO tool **naturally**.
2. If it `end_turn`s without calling it → `set_forced_mode(tool_choice)` (`:77-87`): `forced_mode=True`, `force_attempted=True`, **`self.tool_choice = tool_choice or {"any": {}}`** (Converse "any tool" choice). Append `structured_output_prompt`, recurse.
3. Still not called after forcing → `raise StructuredOutputException` (`:305`).

**[CORRECTION 2026-05-30, CE-5]**: the actual `DEFAULT_STRUCTURED_OUTPUT_PROMPT = "You must format the previous response as structured output."` (`_structured_output_context.py:16`) — a single sentence. (The long multi-bullet prompt in §4 was conflated with the summarizer prompt.)

Verso ships `output_type=` + in-loop reask (append ValidationError + re-drive) + output validators + Retry(feedback). The **two-phase natural→forced-`{"any":{}}` escalation** is a subtly different mechanism (force-any-tool vs re-ask-with-error). verso-already-has the goal; the explicit "let it call naturally, then force tool_choice" escalation is neutral-context (Verso's reask is arguably stronger/model-agnostic already).

---

## 5. Context / memory — conversation managers
`agent/conversation_manager/`. Base constants (`conversation_manager.py:16`): `DEFAULT_COMPRESSION_THRESHOLD = 0.7`, `DEFAULT_CONTEXT_WINDOW_LIMIT = 200_000`.

1. `NullConversationManager` — no-op.
2. `SlidingWindowConversationManager` (`:20`): `window_size = 40` (`:36`); `should_truncate_results = True` (`:37`) truncates oversized tool results; `proactive_compression` (`:59,85`) calls `reduce_context()` when usage > 0.7 of 200k **before** hitting the hard limit; on `ContextWindowOverflowException`, `reduce_context(e=…)` (`:195`) trims to retry.
3. `SummarizingConversationManager` (`:54`): summarizes old messages with a **dedicated LLM call**; `summary_ratio = 0.3` (clamp 0.1–0.8), `preserve_recent_messages = 10`, optional `summarization_agent` / `summarization_system_prompt`.

**LLM-summarization compaction is on Verso's NON-GOALS list** ("no-LLM-summarization-compaction-by-default"). Strands ships it as opt-in (default is sliding-window/truncate, not summarize). So Strands' DEFAULT confirms Verso's stance (don't summarize by default); its Summarizing manager is the exact thing Verso explicitly refuses as a default. avoid-overkill. NOTE: Strands truncates tool results (like Verso's `prune()` masking), and `should_truncate_results` parallels Verso's "mask old tool outputs, never silent-drop." verso-already-has on the prune mechanism.

---

## 6. Streaming — typed events (dict subclasses, 31 classes)
`types/_events.py`. **[CE-4 CLARIFICATION]**: full set is **31 classes** (`grep '^class' → 31`), all **`dict` subclasses** (`class TypedEvent(dict)`, `:28`) — the event IS its payload; `callback_handler` reads well-known keys.
- Lifecycle: `InitEventLoopEvent, StartEvent, StartEventLoopEvent, ModelStopReason, EventLoopStopEvent(stop_reason,message,metrics,request_state)` (`:219`, terminal), `ForceStopEvent, EventLoopThrottleEvent, AgentResultEvent`.
- Deltas (extend `ModelStreamEvent`): `TextStreamEvent → {"data":text,"delta":delta}` (`:153`), `ToolUseStreamEvent → {"type":"tool_use_stream","delta","current_tool_use"}`, `ReasoningTextStreamEvent → {"reasoningText","delta","reasoning":True}`, `ReasoningRedactedContentStreamEvent`, `ReasoningSignatureStreamEvent`, `CitationStreamEvent`, `ModelStreamChunkEvent`.
- `ModelStreamEvent.prepare()` (`:139`) merges invocation_state when delta present; `is_callback_event` True only for non-empty events (`:134`) — **empty deltas don't spam the callback.**
- Tool: `ToolResultEvent, ToolStreamEvent, AgentAsToolStreamEvent (:327), ToolCancelEvent(tool_use,message) (:352), ToolInterruptEvent`.
- Message: `ModelMessageEvent, ToolResultMessageEvent, StructuredOutputEvent (:249)`.

Strands streams **typed Python events, not SSE** (`callback_handler` callable consumes them; default prints `event.get("data","")`). Verso ships typed true-delta events (message/reasoning/tool.start/tool.result/done) **plus** SSE. verso-already-has; Verso is broader (SSE included). The "events are dict subclasses so event IS payload" is a design choice, neutral-context.

---

## 7. Durability — SessionManager via hooks
`session/`. `SessionManager(HookProvider, ABC)` (`session_manager.py:31`) persists by **subscribing to hooks**: `add_callback(MessageAddedEvent, append_message)` (`:46`), `add_callback(MessageAddedEvent, sync_agent)` + `add_callback(AfterInvocationEvent, sync_agent)` (`:49,52`). Implementations: `FileSessionManager` (JSON), `S3SessionManager`, `RepositorySessionManager + SessionRepository` (custom). `read_agent(session_id, agent_id)` rehydrates. `AgentState` = separate KV bag for arbitrary persisted state. `experimental/checkpoint/` adds richer checkpointing.

> "Because persistence is hook-driven, durability is **transparent** — attach a `SessionManager` and every message/turn is saved with no loop changes." (§7, line 215)

**This is a direct confirmation of Verso's tactical↔durable seam thesis** — promote ephemeral to durable with no loop rewrite. Strands does it via hooks subscribing to `MessageAddedEvent`; Verso via the durable seam + `SqliteCheckpointStore` + one flag. Same outcome, equally additive. verso-already-has. Strands checkpoints per-MESSAGE; Verso checkpoints per-STEP (crash-recoverable, resume in fresh process). Verso's checkpoint granularity + `resume()` in a fresh process + `history()/fork()` time-travel is RICHER than Strands' default SessionManager (which is hook-append). Strands' richer checkpoint is in `experimental/`.

---

## 8. Multi-agent — Swarm, Graph, agents-as-tools, A2A (the heaviest surfaces)
`multiagent/`.
- **Swarm** (`swarm.py:1064 L`): shared-context handoff network; `SharedContext` KV; injected `handoff_to_agent` tools. Caps (`:245`): `max_handoffs=20, max_iterations=20, execution_timeout=900.0, node_timeout=300.0, repetitive_handoff_detection_window=0`. `should_continue` (`:191`) stops on caps + anti-ping-pong check (`:215-223`).
- **Graph** (`graph.py:1296 L`): a **DAG** of agents by edge dependencies; `GraphNode/GraphEdge` (edge has optional `condition`), `GraphBuilder.add_node/add_edge`, topological execution, `max_node_executions` cap, conditional branching.
- **Agents-as-tools** (CE-6, `agent/agent.py:681`): `Agent.as_tool(name, description, preserve_context=...)` → `_AgentAsTool`; sub-agent runs its OWN event loop, events bubble as `AgentAsToolStreamEvent` carrying the sub-agent ref. `preserve_context` = sub-agent sees parent convo or starts fresh.
- **A2A** (`multiagent/a2a/`): real Agent-to-Agent protocol server+client for cross-framework interop.

**Graph + Swarm are exactly what Verso's NON-GOALS refuse** ("not a graph-DSL by default", "no orchestrator-as-primitive", "just build agents, brutal, no 500+ nodes"). Note Strands keeps the GRAPH OUT of the core loop and LAYERS it (1296 L graph.py is separate, on hooks) — so even Strands, a graph-shipping framework, agrees the graph is NOT the core primitive. avoid-overkill. The `agents-as-tools` pattern (sub-agent IS a tool, runs its own loop) is the LEAN multi-agent path and is more on-thesis than Swarm/Graph — but Verso treats any tool (incl. a wrapped sub-agent) as a tool already, so this is achievable without a new primitive. neutral-context / verso-already-has.

---

## 9. Hooks — the extension spine (15 event types)
`hooks/`. `HookProvider.register_hooks(registry)` + `HookRegistry.add_callback(EventType, fn)`. **`add_callback(EventType | None | [list], fn)`** — `None` = ALL events (CE-3, `:194`). `invoke_callbacks(event) → (event, interrupts)`; **events with `should_reverse_callbacks=True` fire in REVERSE registration order** (`:278`) — middleware-onion LIFO teardown.

15 event types: `AgentInitializedEvent, BeforeInvocationEvent, AfterInvocationEvent, MessageAddedEvent, BeforeToolCallEvent, AfterToolCallEvent, BeforeModelCallEvent, AfterModelCallEvent, MultiAgentInitializedEvent, Before/AfterNodeCallEvent, Before/AfterMultiAgentInvocationEvent`.

**Load-bearing mutable fields** (CE-3):
- `BeforeToolCallEvent` (`_Interruptible`): **`selected_tool` mutable ⇒ swap the tool implementation** (sandboxing/mocking/policy substitution), `tool_use` mutable ⇒ rewrite input, can **`cancel_tool`** (`:158`, `_can_write=["cancel_tool","selected_tool","tool_use"]`).
- `AfterToolCallEvent`: **`result` mutable** ⇒ rewrite result.
- `AfterModelCallEvent`: can set `stop_response` to request a model-call retry.

> "`SessionManager`, `ModelRetryStrategy`, steering, and telemetry are all just `HookProvider`s registered on these events." (CE-3)

Verso ships `Hooks(pre/post_model, pre/post_tool, on_stop, ask, should_continue)` + `PermissionDecision` 4-valued + `ask_once`. **Mutable `selected_tool` (swap a tool's implementation in a before-hook) is the one extension lever Verso may genuinely lack** — Verso's pre_tool hook can allow/deny/ask/defer but the teardown emphasizes Strands lets a hook REDIRECT a call to a different implementation. If Verso's pre_tool can't substitute the tool fn, this is a clean additive, byte-identical-when-unused lever. steal candidate (verify against Verso first). Reverse-order (LIFO) callback firing for teardown events is a small clean detail (neutral-context).

---

## 10. MCP — background-thread session (CE-7)
`MCPClient(ToolProvider)` (`tools/mcp/mcp_client.py:104`). Takes a **`transport_callable: () → MCPTransport`** so one client wraps stdio/SSE/streamable-HTTP interchangeably. MCP `ClientSession` runs on a **dedicated background thread** (`_background_thread_session`, `:156`); sync methods marshal coroutines via `_invoke_on_background_thread(coro).result()` (`:435`) — isolates the async MCP session from the agent loop. `list_tools_sync(pagination_token)` returns `PaginatedList[MCPAgentTool]` with `nextCursor` — full MCP pagination; tools merge into registry like local `@tool`s.

Verso's MCP is an opt-in adapter (native `@tool` is THE path) — MCP-first is a NON-GOAL. So Strands' deep MCP machinery (background-thread quarantine, pagination) is mostly avoid-overkill for Verso's default path, though the **transport-callable abstraction** (one client, any transport) is a tidy shape (neutral-context).

---

## 11. Exact constants table (KNOWN, teardown §10)
| Constant | Value | Source |
|---|---|---|
| MAX_ATTEMPTS | 6 | event_loop.py:54 |
| INITIAL_DELAY / MAX_DELAY | 4s / 240s | event_loop.py:55-56 |
| backoff | 4→8→16→32→64 | _retry.py:28 |
| default model | global.anthropic.claude-sonnet-4-6 | bedrock.py:42 |
| DEFAULT_COMPRESSION_THRESHOLD | 0.7 | conversation_manager.py:16 |
| DEFAULT_CONTEXT_WINDOW_LIMIT | 200_000 | conversation_manager.py:17 |
| sliding window_size | 40 | sliding_window…py:36 |
| summary_ratio | 0.3 (clamp 0.1–0.8) | summarizing…py:64,94 |
| preserve_recent_messages | 10 | summarizing…py:65 |
| Swarm max_handoffs/iterations | 20/20 | swarm.py:245 |
| Swarm execution/node timeout | 900.0/300.0 s | swarm.py:247-248 |
| limit priority | turns→total_tokens→output_tokens | event_loop.py:64 |
| default tool executor | ConcurrentToolExecutor | agent/agent.py:63 |
| max_tokens policy | raise MaxTokensReachedException (hard) | event_loop.py:272 |

---

## Leanness verdict
Strands is a STRONG confirmation of Verso's boring-core bet: explicit "thin loop, fat model," graph/multi-agent kept OUT of the core and layered on hooks, durability made transparent via hook subscription (no loop rewrite — same as Verso's seam), `@tool` docstring→schema with zero boilerplate (identical to Verso). Where Strands diverges from Verso's NON-GOALS — Graph/Swarm DSLs, default LLM-summarization compaction, AWS Bedrock guardrails — those are exactly the surfaces Verso refuses, and even Strands keeps them out of the ~716-line core. Verso's core is LEANER (<200 vs ~716) and richer on the durable seam (per-step checkpoint, fresh-process resume, fork/time-travel vs per-message hook-append).
