# OpenAI Agents SDK + Swarm — Raw Extraction (top-1% framework validation)

Sources (read in full, bounded):
- `/Users/seventyleven/Desktop/researchfms/teardowns/OPENAI_AGENTS_SDK.md` (1501 lines, Rounds 1–3)
- `/Users/seventyleven/Desktop/researchfms/teardowns/OPENAI_SWARM.md` (889 lines, Rounds 1–2)

All findings tagged KNOWN-from-source (the teardown cites file:line of the upstream repo) or INFERRED (my reading of the teardown).

---

## 0. The lineage thesis (KNOWN)

> "The lineage is: **Swarm → OpenAI Agents SDK**. The Agents SDK preserves the 'tool function returning sentinel that swaps agent' idea but wraps it in a `Handoff` dataclass with input schemas, history filters, prompt templates, and tracing spans."

- Swarm = **424 LOC** total (`__init__.py` 4 + `core.py` 292 + `types.py` 41 + `util.py` 87). README banner: *"Swarm is now replaced by the OpenAI Agents SDK… We recommend migrating to the Agents SDK for all production use cases."* Deprecated, no PyPI release, install from git SHA `6af0b4caf3`.
- Agents SDK = **91,557 LOC** across `src/agents/`. Version `0.17.2` (Round 1/2), `0.17.4`/HEAD `d87fec8` (Round 3). "**217× expansion** to add production features."
- The novelty Swarm crystallized fits in **three lines**:
  ```python
  case Agent() as agent:
      return Result(value=json.dumps({"assistant": agent.name}), agent=agent)
  ```
- Verdict on Swarm: *"do NOT replicate Swarm in production… Swarm is the educational fossil — the architectural ancestor of every modern multi-agent framework, preserved in 424 readable LOC."*

INFERRED relevance to Verso: Swarm is the LEAN peer that proves Verso's thesis — the core ReAct loop + tool-return is tiny; everything else is additive. Swarm is *too* lean (no retry, no typed schema, no sessions). Verso already sits at the right rung between Swarm and the full Agents SDK.

---

## 1. The Agent primitive (KNOWN)

**Swarm `Agent`** (Pydantic model, `types.py`): `name`, `model` (default `"gpt-4o"`, hardcoded `types.py:16`), `instructions` (str or callable taking `context_variables`), `functions` (list of plain Python callables), `tool_choice`, `parallel_tool_calls` (default `True`).

**Agents SDK `Agent[TContext]`** (Pydantic-validated dataclass, `agent.py`): `name`, `instructions` (str or callable), `tools`, `handoffs`, `model`, `model_settings`, `input_guardrails`, `output_guardrails`, `output_type` (Pydantic-validated final-output schema), `hooks`, `tool_use_behavior`, `reset_tool_choice`, `mcp_servers`, `mcp_config`, `prompt` (server-managed Responses-API prompt), `handoff_description`.

INFERRED: Verso's `ContextBundle`(instructions/history/tools) + `output_type=` + per-call `model=` swap covers the same surface. Verso's agent is typed and additive; the Agents SDK `Agent` is broader only because it bundles multi-agent (handoffs) and voice/realtime config.

---

## 2. The run loop (KNOWN)

**Swarm** (`core.py:231-292`): `while len(history) - init_len < max_turns and active_agent:` → `get_chat_completion` → if no `tool_calls` break → `handle_tool_calls` → `if partial_response.agent: active_agent = partial_response.agent`. `max_turns` default `float("inf")` (NO limit). System prompt rewritten every turn from `active_agent.instructions`. **Zero try/except — every exception bubbles. No retry, no backoff, no timeout.** README: *"lightweight, highly controllable."*

**Agents SDK** modern loop (Round 3, `run_internal/run_loop.py:671`, refactored out of the old `_run_impl.py` into a 22-module `run_internal/` package). An explicit state machine over **4 `NextStep` dataclasses** (`run_steps.py:154-169`):
- `NextStepHandoff(new_agent)` — transfer tool invoked → switch `current_agent`, loop.
- `NextStepFinalOutput(output)` — no tool calls / `tool_use_behavior` short-circuit → run output guardrails, return.
- `NextStepRunAgain` — tools ran → loop to feed results back.
- `NextStepInterruption(interruptions: list[ToolApprovalItem])` — a tool needs human approval → pause, return resumable state.

`DEFAULT_MAX_TURNS = 10` (`run_config.py:33`, nullable since RunState schema 1.10). `MaxTurnsExceeded` raised at `:889`.

INFERRED: Verso ships exactly this loop shape — one async ReAct loop, `done()` termination, `max_steps` with grace-call policy, `StopReason`. The 4-`NextStep` union maps to Verso's `StopReason` taxonomy; Verso refuses the multi-agent `Handoff` branch by design ("we don't force the graph"). The `NextStepInterruption` branch = Verso's `ctx.hitl.request` pause/resume.

---

## 3. Handoffs — the signature feature, vs Verso's "no forced multi-agent" (KNOWN — most important section)

### Swarm handoff = return-type detection (5 lines)
`handle_function_result` (`core.py:71-87`): a tool returns an `Agent` instance → wrapped as `Result(value=json.dumps({"assistant": agent.name}), agent=agent)` → run loop swaps `active_agent`. No special API, no class, no decorator. Properties: one active agent at a time; full history passed to new agent (no filtering); no "return to caller" (examples give every agent a `transfer_back_to_triage` tool); LLM is unaware of the swap (only sees tool message `{"assistant": "Agent B"}`); `context_variables` persists (mutable shared state).

### Agents SDK handoff = typed `Handoff` dataclass dispatched on a tool call
`handoff()` constructor (`handoffs/__init__.py:222-333`):
```python
def handoff(agent, tool_name_override=None, tool_description_override=None,
            on_handoff=None,            # side-effect callback (1 or 2 args, validated at construction)
            input_type=None,            # optional Pydantic type → strict JSON schema
            input_filter=None,          # Callable[[HandoffInputData], HandoffInputData] — history shaping
            nest_handoff_history=None,  # wrap prior transcript into a nested summary
            is_enabled=True) -> Handoff: ...
```
- Tool name: `transform_string_function_style(f"transfer_to_{agent.name}")` → `"Refunds Agent"` becomes `transfer_to_refunds_agent`.
- Tool description: `f"Handoff to the {agent.name} agent to handle the request. {handoff_description}"`.
- `ensure_strict_json_schema(input_json_schema)` is **ALWAYS** called even when `input_type is None` (schema `{}`). Currently hardcoded strict.
- `weakref.ref(agent)` stored (`:332`) to avoid circular-reference memory leaks; strong ref lives only in the `_invoke_handoff` closure.
- Tool-message response is `{"assistant": agent.name}` — **byte-identical to Swarm** (constructed by `Handoff.get_transfer_message`).

`HandoffInputData` (frozen dataclass, `handoffs/__init__.py:41-83`) — the contract `input_filter` operates on, with three-tier history split: `input_history` (original `Runner.run` input), `pre_handoff_items` (before current turn), `new_items` (during the handoff-triggering turn), plus `run_context` and override `input_items`. `.clone(**kwargs)` for mutation. Common filters: strip irrelevant tool calls, compress old history to a summary, drop everything except original user query.

### Swarm vs Agents SDK handoff table (verbatim from source)
| Aspect | Swarm | Agents SDK |
|---|---|---|
| Mechanism | Tool returns `Agent` | Tool call dispatched to `Handoff` object |
| Input schema | None | Pydantic `input_type`, strict JSON schema |
| History filter | Always full history | `input_filter: HandoffInputData → HandoffInputData` |
| Side effects | None | `on_handoff(ctx, input)` callback |
| Disable per turn | Remove function | `is_enabled: bool \| Callable` |
| Nested history | N/A | `nest_handoff_history` summarization |
| LLM-visible name | Python function name | `transfer_to_<snake_cased_agent_name>` |
| Prompt template | None | `RECOMMENDED_PROMPT_PREFIX` |
| Tracing | None | `HandoffSpanData` |

### RECOMMENDED_PROMPT_PREFIX (verbatim, `extensions/handoff_prompt.py`)
```
# System context
You are part of a multi-agent system called the Agents SDK, designed to make agent
coordination and execution easy. Agents uses two primary abstraction: **Agents** and
**Handoffs**. An agent encompasses instructions and tools and can hand off a
conversation to another agent when appropriate. Handoffs are achieved by calling a
handoff function, generally named `transfer_to_<agent_name>`. Transfers between
agents are handled seamlessly in the background; do not mention or draw attention
to these transfers in your conversation with the user.
```
(Shipped with the typo "two primary abstraction" — singular.) Helper: `prompt_with_handoff_instructions(prompt)`.

### Agent-as-tool — DISTINCT from handoff (KNOWN, `agent.py:508`)
`agent.as_tool(tool_name, tool_description, ...)` returns a `FunctionTool` that runs the sub-agent via `Runner.run` and returns its final output as a **string**. Control does NOT transfer — parent stays in charge. Has its own `max_turns`, `hooks`, `session`, `needs_approval`, `StructuredToolInputBuilder` (typed structured input validated against `parameters` Pydantic type). Source highlights this as novel: *"Most other frameworks conflate them"* (control transfer vs function call).

INFERRED — Verso relation: This is the sharpest contrast point. Verso's NON-GOALS explicitly reject forced multi-agent / orchestrator-as-primitive / "no 500+ nodes." The Agents SDK handoff is a *full control transfer between peer agents* — exactly the graph/multi-agent shape Verso refuses by default. The agent-as-tool pattern (sub-agent invoked synchronously, returns a string) is the ONLY multi-agent shape compatible with Verso's thesis, and Verso already expresses it trivially: a `@tool` that internally drives another loop and returns text — no `Handoff` primitive, no `transfer_to_X`, no prompt-prefix needed. **Verso should NOT adopt the Handoff dataclass** (avoid-overkill: it's the forced-graph it counter-positions against). The history-filter idea (`input_filter`) is interesting but Verso's `prune()` already shapes context additively.

---

## 4. Guardrails (KNOWN, `guardrail.py` 344 LOC)

Four flavors, all with **tripwire short-circuit via typed exceptions**:
- `InputGuardrail[TContext]` — `guardrail_function(ctx, agent, input)`, `run_in_parallel: bool = True` (runs concurrent with model call). Sequential ones (`run_in_parallel=False`) run BEFORE the model call.
- `OutputGuardrail[TContext]` — runs after model declares final output.
- `ToolInputGuardrail` — validates tool args before invocation.
- `ToolOutputGuardrail` — validates tool result before sending to model.

Output of any guardrail: `GuardrailFunctionOutput(output_info: Any, tripwire_triggered: bool)`. Tripwires raise `InputGuardrailTripwireTriggered` / `OutputGuardrailTripwireTriggered` / `ToolInputGuardrailTripwireTriggered` / `ToolOutputGuardrailTripwireTriggered`. Even when no tripwire trips, diagnostic results are collected into `RunResult.input_guardrail_results` / `output_guardrail_results`. Decorators `@input_guardrail` / `@output_guardrail` with bare or kwarg forms; default name falls back to `func.__name__`.

INFERRED — Verso relation: Verso ships `Hooks(pre/post_model, pre/post_tool, on_stop, ask, should_continue)` + `PermissionDecision` 4-valued (allow/deny/ask/defer) + output validators + `quarantine` trust-tier. The pre/post-tool guardrail with a tripwire is functionally Verso's `pre_tool` hook returning deny. The PARALLEL input guardrail (run concurrent with the model call to hide latency) is a small, on-thesis nuance Verso may or may not have explicitly. Mostly **verso-already-has**.

---

## 5. Sessions / Memory (KNOWN, `memory/`)

Swarm: **zero persistent memory**. README: *"does not store state between calls."* `history` is a user list; `context_variables` a user dict; prescribed memory pattern is `swarm.run(messages=prev.messages + new_message)`.

Agents SDK `Session` Protocol (`memory/session.py:14`) — four async methods: `get_items(limit=None)`, `add_items(items)`, `pop_item()` (undo/correction), `clear_session()`. Three+ backends:
- `SQLiteSession` — two tables `agent_sessions` + `agent_messages` (items as JSON rows, autoincrement `id` ordering; `pop_item` deletes max id; `ON DELETE CASCADE`; per-file `threading.RLock` registry). Default `db_path=":memory:"`.
- `OpenAIConversationsSession` — server-side OpenAI Conversations API, no client state.
- `OpenAIResponsesCompactionSession` — wrapper that triggers OpenAI's `responses.compact` endpoint past a length threshold.

**Auto-load/auto-save (KNOWN, `run.py:527,571`):** `prepare_input_with_session` prepends stored items before the first model call; new items written back via `session.add_items`. `session_persistence_enabled = session is not None and server_conversation_tracker is None` — **sessions and server-managed conversations are mutually exclusive** (Responses API tracks server-side via `conversation_id`).

INFERRED — Verso relation: Verso ships typed 4-tier memory (FACT/...), temporal recall, `recall_as_of` time-travel, `reflect()` consolidation, sqlite/sqlitevec/inmem, ADD-only with supersede. Verso's memory is RICHER than the Agents SDK's flat message-log sessions. The `pop_item` undo and the OpenAI `responses.compact` server-side compaction are NON-GOALS-adjacent (Verso explicitly rejects LLM-summarization-compaction-by-default). **verso-already-has** / partly **avoid-overkill**.

---

## 6. Tracing / Observability (KNOWN, `tracing/`)

Swarm: `debug=True` → ANSI stdout via `debug_print` (`util.py:5-10`). That's the entire observability layer.

Agents SDK: posts batched spans to `https://api.openai.com/v1/traces/ingest` (`processors.py:34`), visible in OpenAI's Traces dashboard, zero setup. Disable via `RunConfig(tracing_disabled=True)` or `OPENAI_AGENTS_DISABLE_TRACING=1`. **14 span data types** (13 concrete + abstract `SpanData` base): Agent/Task/Turn/Function/Generation/Response/Handoff/Custom/Guardrail/Transcription/Speech/SpeechGroup/MCPListTools. OTel-style parent-child via Python contextvars. Constants: `_OPENAI_TRACING_MAX_FIELD_BYTES = 100_000` (truncate w/ `"... [truncated]"`), batch `max_batch_size=128`, `schedule_delay=5.0s`, `export_trigger_ratio=0.7`, retry `max_retries=3, base_delay=1.0` exponential.

INFERRED — Verso relation: Verso ships `VersoSpan + OTel` and the eval wedge ("prod==eval, captured failure IS a regression test"). The Agents SDK's vendor-locked `api.openai.com/v1/traces/ingest` endpoint is exactly what Verso should NOT do (vendor lock-in). Verso's OTel spans are vendor-neutral. **verso-already-has**; the OpenAI-dashboard coupling is **avoid-overkill**.

---

## 7. Tools / function-tools (KNOWN)

Swarm `function_to_json` (`util.py:31-87`): tool schema from `inspect.signature` + `__doc__`, **no Pydantic**. 7-entry type map; everything else (incl. `Optional[int]`, `List[str]`, Pydantic models, Enums) falls back to `"string"` — *"a known wart — production users hit it quickly."* No per-parameter description, no nested objects/enums/constraints. `context_variables` special param: scrubbed from the JSON schema sent to the model (`core.py:52-56`) but injected into the Python call if present in `func.__code__.co_varnames` (over-inclusive — catches locals too).

Agents SDK `@function_tool`: Pydantic `TypeAdapter.json_schema()` → `ensure_strict_json_schema()` (`strict_schema.py`) enforcing OpenAI strict mode (all objects `additionalProperties:false`, optionals as nullable-required, `anyOf/oneOf/allOf` normalized, refs inlined via jsonref). `FunctionTool` has **17 fields** (vs Swarm's 3): incl. `params_json_schema`, `strict_json_schema=True`, `is_enabled`, `tool_input_guardrails`, `tool_output_guardrails`, `needs_approval`, `timeout_seconds`, `timeout_behavior` (`"error_as_result"` default | `"raise_exception"`), `timeout_error_function`, `defer_loading`, `_failure_error_function`. *"17 fields vs 3. This is what production-readiness costs."*

`tool_use_behavior` (`agent.py:345`): `"run_llm_again"` (default) | `"stop_on_first_tool"` | `StopAtTools({"stop_at_tool_names":[...]})` | `ToolsToFinalOutputFunction` → declares *which tools' outputs are final answers* without a custom loop. `reset_tool_choice: bool = True` (`agent.py:367`) — after a tool fires, reset `tool_choice` to `"auto"` to prevent tool-call infinite loops.

14 tool classes (Round 2 §R2.12): FunctionTool, FileSearchTool, WebSearchTool, ComputerTool, HostedMCPTool, CodeInterpreterTool, ImageGenerationTool, LocalShellTool, ShellTool, ApplyPatchTool, CustomTool, ToolSearchTool. Hosted tools declared in the Responses API request and executed server-side by OpenAI.

INFERRED — Verso relation: Verso ships `@tool` (docstring→schema), jsonish 4-stage parse waterfall, coerce, per-tool idempotent/max_attempts/timeout_seconds, quarantine trust-tier, builtins. The `timeout_seconds`/`timeout_behavior` and per-tool `is_enabled` gating map directly to Verso's per-tool config. `tool_use_behavior="stop_on_first_tool"`/`StopAtTools` = Verso's `done()` + termination policy. **verso-already-has.** The hosted server-side tools (FileSearch/WebSearch/Computer/CodeInterpreter/ImageGen) are OpenAI-platform-specific — NON-GOAL for Verso (not MCP-first, native @tool is THE path). `reset_tool_choice=True` default is a small, on-thesis anti-loop nuance worth confirming Verso has.

---

## 8. Structured output (KNOWN)

`Agent.output_type` = Pydantic-validated final-output schema. On `NextStepFinalOutput`, output validated against `output_type`; malformed → `ModelBehaviorError`. Strict JSON schema enforced.

INFERRED — Verso relation: Verso ships `output_type=`, in-loop reask (append ValidationError + re-drive), output validators, `Retry(feedback)` self-healing. Verso's in-loop reask is arguably stronger than the Agents SDK's raise-on-invalid. **verso-already-has.**

---

## 9. Streaming (KNOWN)

Swarm: custom generator yielding `{"delim":"start"}` / deltas / `{"delim":"end"}` / `{"response": Response(...)}`; hand-rolled `merge_chunk` to reassemble streamed tool-call argument deltas. Note: `run_and_stream` is missing the `and active_agent` loop guard the blocking variant has — a latent divergence.

Agents SDK: `Runner.run_streamed` → `RunResultStreaming.stream_events()` yields 3 event classes: `RawResponsesStreamEvent` (token deltas), `RunItemStreamEvent` (11 named sub-events incl. the intentionally-misspelled `"handoff_occured"` — *"we can't change it because that would be a breaking change"*), `AgentUpdatedStreamEvent` (fires when `current_agent` changes after a handoff). Protocol is a Python async iterator, not SSE (SDK consumes OpenAI's SSE internally and re-emits).

INFERRED — Verso relation: Verso ships typed true-delta events (message/reasoning/tool.start/tool.result/done) + SSE. Verso's events are cleaner (no misspelled-but-frozen literals). The `AgentUpdatedStreamEvent` only exists because of multi-agent handoffs Verso doesn't have. **verso-already-has.**

---

## 10. Model layer (KNOWN, `models/`)

Swarm: OpenAI-only, default `gpt-4o` hardcoded, `model_override` per call. Any other provider needs an OpenAI-compatible proxy client.

Agents SDK: `OpenAIResponsesModel` (default, **stateful** via `previous_response_id` + `conversation_id` — does NOT resend full history), `OpenAIChatCompletionsModel` (**stateless**, needs a `Converter` for item↔message translation, resends history), `LitellmModel` (100+ providers via LiteLLM). `MultiProvider` routes a model string → provider. Default `gpt-5.4-mini` (`OPENAI_DEFAULT_MODEL` env override). GPT-5 reasoning-effort regex table (11 patterns, `default_models.py:50`), `verbosity="low"` default for all GPT-5 settings. `parallel_tool_calls` three-way True/False/omit.

INFERRED — Verso relation: Verso ships anthropic/openai/google adapters + ANY OpenAI-compatible endpoint via `base_url`, `init_model("provider:model")`, `FailoverModel + RetryPolicy` (typed errors, auth/content fail-fast), per-call `model=` swap + `agent.override()`. Verso's failover + typed error taxonomy is on par or stronger. **verso-already-has.** OpenAI's Responses-API server-side conversation state (`previous_response_id`) is provider-specific lock-in Verso need not chase.

---

## 11. Durable execution / HITL — RunState (KNOWN, Round 3, `run_state.py` 3,305 LOC) — the biggest post-R1/2 addition

`RunState[TContext, TAgent]` = *"the durable pause/resume boundary for human-in-the-loop flows… stores enough information to continue an interrupted run."* Captures: `_current_turn`, `_current_agent` + `_starting_agent` (stable id, not pickle), `_original_input`, `_model_responses`, `_context` (approvals + usage), `_generated_items` + `_session_items`, `_max_turns`, `_conversation_id`/`_previous_response_id`, `_generated_prompt_cache_key`, `_reasoning_item_id_policy: Literal["preserve","omit"]`, all four guardrail-result lists, `_current_step: NextStepInterruption`, `_last_processed_response`, `_tool_use_tracker_snapshot`, `_trace_state`, `_sandbox`.

**Schema versioning:** `CURRENT_SCHEMA_VERSION = "1.10"` (Python; JS at `1.12`), `SUPPORTED_SCHEMA_VERSIONS` frozenset, `SCHEMA_VERSION_SUMMARIES` per-version change notes; deserialization is schema-gated (refuse/migrate incompatible snapshots). `to_json/to_string/from_json/from_string`; agents+tools referenced by **stable identity keys, not pickled**; custom contexts need a `context_serializer`.

**HITL cycle:** tool with `needs_approval=True` → `ToolApprovalItem` (not executed) → `ProcessedResponse.has_interruptions()` → `NextStepInterruption` → loop breaks, returns resumable `RunResult`. `state.get_interruptions()` → `state.approve(item, always_approve=False)` / `state.reject(item, rejection_message=...)`. Approvals keyed by `(tool_name, call_id)`; `always_approve=True` whitelists all future calls. Persist `state.to_json()` anywhere; resume via `Runner.run(agent, input=state)` (`Runner.run` accepts a `RunState` as its input), `resolve_interrupted_turn()` re-applies decisions and continues from the exact pause point. *"OpenAI's answer to durable agent execution (cf. Temporal/LangGraph checkpointing) — fully in-library, serializable to JSON, schema-versioned, no external workflow engine required."*

INFERRED — Verso relation: This is **dead-on Verso's durable seam**. Verso ships `SqliteCheckpointStore`, checkpoint-each-step (crash-recoverable), `resume()` in a FRESH process, `ctx.deps` typed injection, `ctx.hitl.request` pause/resume (idempotent-up-to-request), `history()/fork()` time-travel, `repair_history` resume-guard. The Agents SDK validates Verso's design choices independently. Two specific things worth noting as **steal-additive candidates** (high bar): (a) **schema-versioned serialized state with a `SUPPORTED_SCHEMA_VERSIONS` gate + per-version change summaries** — a forward/backward-compat discipline so a checkpoint written by an old Verso version is explicitly refused-or-migrated rather than silently mis-deserialized; byte-identical when unused (just a version int + a frozenset check). (b) **`always_approve` / remember-all-future-calls-of-this-tool keyed by `(tool_name, call_id)`** — Verso already has `ask_once` with durable `on_approve/on_remember`, so this is likely **verso-already-has**. The agent/tool-by-stable-identity-key (not pickle) serialization is a sound pattern Verso's checkpoint store should already follow.

---

## 12. MCP / Voice / Realtime / Sandbox (KNOWN, condensed)

- MCP: 3 transports (stdio, SSE, streamable HTTP) + `HostedMCPTool`; `MCPUtil.get_all_function_tools` converts MCP tools → `FunctionTool`, optionally strict-mode; collision-prefix via `include_server_in_tool_names`.
- Voice: `VoicePipeline` (STT→Agent→TTS), Whisper/TTS-1 defaults, 4 event types.
- Realtime: parallel `RealtimeAgent`/`RealtimeRunner`/`RealtimeSession` over WebSocket (PCM16/G711 audio).
- Sandbox: Firecracker/E2B-style microVM isolation for `LocalShellTool`/`ApplyPatchTool`/`ComputerTool`; S3/R2 mount providers.

INFERRED — Verso relation: All four are platform/modality expansions. Verso's NON-GOALS: not MCP-first (native @tool is THE path; MCP is opt-in adapter — Verso already has `tool_from_schema` raw/MCP). Voice/Realtime/Sandbox are out of Verso's scope by design. **avoid-overkill / neutral-context.**

---

## 13. What the LEAN SDKs get RIGHT (the validation payload)

1. **Swarm: the loop and the tool-return ARE the whole framework.** 424 LOC, readable in 20 min. Validates Verso's "<200-line core, the boring core done right."
2. **Swarm: stateless by design** — all state (`history`, `context_variables`, `active_agent`) constructor-deep-copied and returned. *"Trivial to test, trivial to serialize between turns."* Validates Verso's additive/event-sourced seam.
3. **Agents SDK: handoff stays a TOOL CALL, not a new control plane.** Even the production version expresses multi-agent as `transfer_to_X` tool calls — no graph DSL, no node engine. The wire behavior `{"assistant": name}` is identical to Swarm's. This is the strongest external evidence for Verso's "we don't force the graph" — even OpenAI's production multi-agent is just tools.
4. **Agents SDK: `agent.as_tool` (sub-agent → string) is distinct from handoff.** The non-control-transfer composition pattern is the Verso-compatible one, and it needs zero new primitive.
5. **Agents SDK: `tool_use_behavior`/`StopAtTools` declares termination policy** instead of writing a finalization loop — same spirit as Verso's `done()`.
6. **Agents SDK: RunState is in-library, JSON-serializable, schema-versioned durable execution** — *"no external workflow engine required"* — exactly Verso's "one flag, no graph, no rewrite" durable seam, independently arrived at.
7. **Agents SDK: `reset_tool_choice=True` default** quietly prevents tool-call loops — a tiny anti-doom-loop default in the same family as Verso's stuck-detection.

## 14. What Verso must NOT copy (overkill / NON-GOAL)
- The `Handoff` dataclass as a first-class control-transfer primitive (forced multi-agent / orchestrator — counter-positioned).
- 14 hosted/OpenAI-platform tool classes (FileSearch/WebSearch/Computer/CodeInterpreter/ImageGen/Shell/ApplyPatch/etc.) — platform lock-in, not framework core.
- Vendor-locked tracing endpoint `api.openai.com/v1/traces/ingest`.
- `OpenAIResponsesCompactionSession` server-side LLM-summarization compaction (Verso explicitly rejects compaction-by-default).
- Voice/Realtime/WebSocket/Sandbox subsystems — modality/infra expansion outside Verso's scope.
- 91k LOC of surface — the "217× expansion" is mostly multi-agent + voice + realtime + hosted-tools, none of which Verso's thesis wants.
