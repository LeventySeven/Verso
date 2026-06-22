# LlamaIndex — Raw Extraction (retrieval-first agents) — for Verso validation

Source read: `/Users/seventyleven/Desktop/researchfms/teardowns/LLAMAINDEX.md` (1933 lines, 136KB). Versions cited in source: `llama-index-core==0.14.21/0.14.22`, `llama-index-workflows==2.20.0`. All tagging is against VERSO CURRENT STATE. KNOWN = stated in source with file:line evidence; INFERRED = my synthesis.

---

## 1. The core primitive: Workflow-as-Agent (event-FSM) — KNOWN

> "LlamaIndex models an agent as a **finite state machine of typed events**" — `base_agent.py`. `BaseWorkflowAgent` is a `Workflow` subclass with **seven `@step`-decorated async methods** (`base_agent.py:382-724`):

```
@step init_run             AgentWorkflowStartEvent  → AgentInput
@step setup_agent          AgentInput               → AgentSetup
@step run_agent_step       AgentSetup               → AgentOutput   (calls take_step → LLM)
@step parse_agent_output   AgentOutput              → ToolCall | AgentInput | StopEvent | None
@step call_tool            ToolCall                 → ToolCallResult
@step aggregate_tool_results ToolCallResult         → AgentInput | StopEvent | None
```

`DEFAULT_MAX_ITERATIONS = 20` (`base_agent.py:66`). Agent classes on this base: `FunctionAgent` (function-calling models, `llm.astream_chat_with_tools`), `ReActAgent` (text parse for any model), `CodeActAgent` (action = execute Python), `AgentWorkflow` (multi-agent orchestrator).

**VERSO-RELATION: avoid-overkill.** This IS the graph that Verso explicitly refuses ("we don't force the graph", "no 500+ nodes"). Agent-as-FSM-of-events is the LangGraph-class complexity Verso's <200-line ReAct loop is the counter-position to. The *capabilities* it buys (insert-a-step, resume, fan-out) Verso achieves via additive primitives (hooks, durable checkpoint, asyncio) without making the graph the substrate.

---

## 2. Parallel tool calls via event fan-out + `collect_events` join — KNOWN

`parse_agent_output` emits N `ToolCall` events via `ctx.send_event`; the engine spawns N concurrent `call_tool` steps. `aggregate_tool_results` joins them:
```python
num_tool_calls = await ctx.store.get("num_tool_calls", default=0)
tool_call_results = ctx.collect_events(ev, expected=[ToolCallResult] * num_tool_calls)
if not tool_call_results: return None   # not all arrived; engine re-enters on next event
```
Returning `None` is the "don't terminate yet" signal. (`base_agent.py:610-619`, `669-670`.)

**VERSO-RELATION: neutral-context.** Verso runs an async loop; parallel tool dispatch is `asyncio.gather`-shaped (OpenAI Agents SDK does exactly this per the comparison table). LlamaIndex's value-add here is only the event-bus machinery, which is the overkill. The flat asyncio approach is on-thesis.

---

## 3. Tool error → model-visible `is_error` string (NOT raised) — KNOWN

`_call_tool` (`multi_agent_workflow.py:347-378`):
```python
except Exception as e:
    event_exception = _get_waiting_for_event_exception()
    if event_exception and isinstance(e, event_exception):
        raise        # propagate workflow PAUSE events
    tool_output = ToolOutput(content=str(e), tool_name=..., is_error=True, exception=e)
```
"tool exceptions become model-visible error strings (not raised). The model sees `is_error: true` and can recover." Notable nuance: exceptions matching the workflow's pause-and-wait signal (`_get_waiting_for_event_exception()`) are **re-raised**, enabling a tool to pause execution for an external event.

**VERSO-RELATION: verso-already-has.** Verso's error taxonomy + tool error handling + the HITL pause (`ctx.hitl.request`) cover both halves: model-visible recoverable tool errors AND a typed pause signal that must propagate, not get swallowed.

---

## 4. `return_direct=True` short-circuit — KNOWN

Per-tool flag: "if True, the tool's output IS the final answer; the loop terminates without another LLM call." `aggregate_tool_results` checks `any(r.return_direct and not r.tool_output.is_error)` → `StopEvent`, EXCEPT `tool_name == "handoff"`. Compared in source to Agents SDK `StopAtTools` / `tool_use_behavior="stop_on_first_tool"`.

**VERSO-RELATION: verso-already-has.** Verso has `done()` tool termination + `max_steps_policy` grace-call. A per-tool "this output is final" flag is the same family; `done()` is the cleaner explicit form.

---

## 5. `tool_retriever` — dynamic tool selection (retrieve a subset of tools per query) — KNOWN

`tool_retriever: ObjectRetriever` indexes tools; `get_tools()` calls `await tool_retriever.aretrieve(input_str)` to inject only relevant tools per-query "instead of sending every tool's schema." Source calls this novel; "Agents SDK lacks this directly (you'd implement via `is_enabled` callables)." (`base_agent.py:104-107`, `multi_agent_workflow.py:253-256`.) Note: `tools_by_name` is re-fetched per `call_tool`, so the tool set can change between turns.

**VERSO-RELATION: steal-additive (candidate).** Verso ships RRF retrieval + ContextBundle(tools=...) but the documented use is retrieval over *memory/context*, not over the *tool catalog*. A `tool_retriever`-style hook that RRF-ranks the tool list before building ContextBundle.tools is additive, byte-identical when unused (omit it → all tools), on-thesis (it's context-engineering: shrink tool-schema bloat), and reuses Verso's existing RRF. This is the single highest-value retrieval-ergonomics steal. NOT a graph, NOT a router-cult (it's deterministic RRF over tool descriptions, no learned router).

---

## 6. Single `handoff(to_agent, reason)` function tool — KNOWN

Multi-agent handoff is ONE function tool (not N `transfer_to_X` tools):
```python
async def handoff(ctx, to_agent: str, reason: str) -> str:
    ...
    await ctx.store.set("next_agent", to_agent)
    return handoff_output_prompt.format(to_agent=to_agent, reason=reason)
```
`return_direct=True`, side-effect writes `next_agent` to context store; per-agent `can_handoff_to` allowlist. Source: "the model sees ONE handoff tool instead of N — cleaner schema; loses per-handoff input typing."

**VERSO-RELATION: avoid-overkill.** Multi-agent orchestration / handoffs are an orchestrator-as-primitive pattern; Verso's NON-GOALS exclude "orchestrator-as-primitive" and "router/planner cult." A sub-agent in Verso is just a tool that runs another agent — no handoff-tool, no `next_agent` state machine.

---

## 7. State injection via `state_prompt`, latched once-per-run — KNOWN

`setup_agent` rewrites the **last TextBlock of the last message** (reverse-iterate, preserve image/audio blocks) with `state_prompt.format(state=state, msg=block.text)`, gated by a `formatted_input_with_state` latch reset each run so it fires exactly once. Default prompt:
```
Current state:
{state}

Current message:
{msg}
```
"if state injection re-fired every turn, the prompt would grow with nested Current state... Current message: Current state:..." `state` is a plain dict; tools mutate via `ctx.store.set("state", {...})`.

**VERSO-RELATION: verso-already-has.** Verso has `ctx.deps` typed injection + ContextBundle(instructions=...) + KV-cache-stable prefix. The "rewrite last text block once, leave prefix stable" discipline is exactly Verso's cache-stability law. The once-per-run latch is a good correctness detail Verso's prefix-stability already implies.

---

## 8. Early stopping: `force` vs `generate` — KNOWN

At `num_iterations >= 20`: `force` raises `WorkflowRuntimeError`; `generate` makes one final summary LLM call using `DEFAULT_EARLY_STOPPING_PROMPT` ("You have reached the maximum number of iterations... Do not attempt to use any more tools. Simply summarize what you have learned...").

**VERSO-RELATION: verso-already-has.** Verso's `max_steps_policy` grace-call at max_steps is exactly the `generate` mode; StopReason covers the `force` mode.

---

## 9. Scratchpad / memory split — KNOWN

`FunctionAgent.take_step`: per-run `scratchpad` (list of ChatMessage in `ctx.store[scratchpad_key]`) accumulates the turn's assistant+tool messages but is NOT committed to `memory`; `finalize()` flushes it atomically. "Lets you preserve atomicity of multi-tool turns without leaking intermediate failures."

**VERSO-RELATION: neutral-context.** Verso's history/event-sourced model already separates in-flight loop state from committed history; the durable checkpoint per step is the stronger version. Atomic-flush-on-finalize is an implementation detail, not a missing primitive.

---

## 10. Memory v2 — `Memory` + composable `BaseMemoryBlock` — KNOWN

Old `ChatMemoryBuffer`/`ChatSummaryMemoryBuffer`/`VectorMemory`/`SimpleComposableMemory` are **all deprecated**. New `Memory` (856 LOC):
- `token_limit=30000`, `token_flush_size=3000`, `chat_history_token_ratio=0.7` (≥70% tokens reserved for raw chat), default backend `SQLAlchemyChatStore` (table `llama_index_memory`, SQLite).
- `memory_blocks: List[BaseMemoryBlock]` each with `name`, `priority` (0 = never truncate; 1+ truncated lowest-first), `accept_short_term_memory`, async `_aget/_aput/atruncate`.
- Three shipped blocks: `StaticMemoryBlock` (frozen facts), `FactExtractionMemoryBlock` (LLM extracts `<fact>` tags; condenses when `len(facts) > max_facts=50`), `VectorMemoryBlock` (RAG memory, `similarity_top_k=2`, `retrieval_context_window=5`).
- Blocks rendered into `<memory>...</memory>` Jinja template, inserted into system msg (default) or last user msg.

`FactExtractionMemoryBlock` verbatim extract prompt: "You are a precise fact extraction system... Extract specific, concrete facts... Format each fact as a separate `<fact>` XML tag... Do not include opinions, summaries, or interpretations." Parse: `r"<fact>(.*?)</fact>"`, exact-string dedup.

**VERSO-RELATION: verso-already-has.** Verso ships typed 4-tier memory (FACT/...), temporal, RRF recall, `recall_as_of` time-travel, `reflect()` consolidation, ADD-only supersede, sqlite/sqlitevec/inmem backends. LlamaIndex's `FactExtractionMemoryBlock`≈Verso `reflect()`; `VectorMemoryBlock`≈Verso RRF recall; priority-truncation≈Verso bounded/prune. Verso's FACT typing + temporal `recall_as_of` are strictly richer.

---

## 11. ChatSummaryMemoryBuffer — LLM summarization compaction — KNOWN

`DEFAULT_TOKEN_LIMIT_RATIO=0.75`, walks history in reverse keeping raw until `token_limit`, summarizes the overflow via `SUMMARIZE_PROMPT` ("Write a concise summary about the contents of this conversation"), **writes the summary back into the store** so it isn't re-summarized; atomic assistant/tool pairs (`_handle_assistant_and_tool_messages`). `ChatMemoryBuffer` is the no-LLM version: drops oldest, never lets a window start on TOOL/ASSISTANT (orphaned tool_result guard); single oversized message → return it alone and let the LLM raise ("silent failure mode mitigation").

**VERSO-RELATION: avoid-overkill.** LLM-summarization-compaction-by-default is on Verso's explicit NON-GOALS list. Verso's `prune()` masks old tool outputs (never silent-drops) — a no-LLM, byte-stable strategy. The orphaned-tool-result guard, though, mirrors Verso's `repair_history` resume-guard — confirms Verso already solved the same landmine without summarization.

---

## 12. Response synthesizers (RAG answer shapes) — KNOWN

`response_synthesizers/`: `Refine` (sequential refine loop, `text_qa` then `refine` template), `TreeSummarize` (summarize-the-summaries, recursive, parallel via `asyncio.gather`), `SimpleSummarize` (one call, all chunks concatenated), `Accumulate` (one call per chunk in parallel, returns list), `compact_and_refine`/`compact_and_accumulate` (pre-repack chunks), `Generation` (ignore chunks, parametric only), `NoText`/`ContextOnly` (return nodes/context, no LLM — debugging). Verbatim `DEFAULT_TEXT_QA_PROMPT_TMPL` and chat-style `TEXT_QA_SYSTEM_PROMPT`: "You are an expert Q&A system that is trusted around the world. Always answer the query using the provided context information, and not prior knowledge... Never directly reference the given context."

`Refine` has opt-in `structured_answer_filtering` → `StructuredRefineResponse(answer, query_satisfied: bool)`; skips chunks where `query_satisfied=False` so noise chunks don't degrade the answer. "Streaming not supported with structured answer filtering" (ValueError).

**VERSO-RELATION: avoid-overkill.** These are a RAG-pipeline library's domain (multi-strategy answer synthesis over retrieved chunks). Verso is an agent framework, not a RAG library; the model+tools synthesize answers in-loop. `structured_answer_filtering`'s "drop chunks that don't satisfy the query" is conceptually adjacent to Verso output validators but lives in a query-engine Verso intentionally does not own.

---

## 13. Query-engine decomposition: SubQuestion & MultiStep — KNOWN

`SubQuestionQueryEngine`: few-shot prompt (Uber/Lyft 10-K example) emits `[{sub_question, tool_name}]` — model picks BOTH the sub-question AND which tool answers it; each routed to `tool.aquery`, results fed to TreeSummarize. `MultiStepQueryEngine`: `num_steps=3` sequential, each sub-question conditioned on previous answer; stop when LLM emits "None" (`default_stop_fn`: `"none" in query.lower()`).

**VERSO-RELATION: avoid-overkill.** This is a planner/decomposer over query engines — squarely the "router/planner cult" and "orchestrator-as-primitive" Verso lists as NON-GOALS. A Verso agent decomposes in-loop via plain tool calls; no decomposition prompt-primitive.

---

## 14. Retrievers — incl. QueryFusionRetriever (RRF) — KNOWN

`retrievers/`: `AutoMergingRetriever` (replace leaf clusters with parent when `ratio > 0.5`), **`QueryFusionRetriever`** (LLM generates `num_queries=4` query variants, retrieves each, **fuses via Reciprocal Rank Fusion**), `RecursiveRetriever` (IndexNode → recurse into sub-retriever), `RouterRetriever` (LLM selector picks a retriever, +1 LLM call), `TransformRetriever` (e.g. HyDE — embed a hypothetical answer). HyDE prompt verbatim: "Please write a passage to answer the question. Try to include as many key details as possible."

**VERSO-RELATION: verso-already-has (RRF).** Verso ships RRF retrieval already. LlamaIndex confirms RRF is the industry-standard fusion. The *multi-query-variant generation* feeding RRF (QueryFusion) is a possible micro-add but it costs an LLM call per query and is borderline router-cult; HyDE/RouterRetriever are LLM-cost retrieval tricks Verso should not adopt by default.

---

## 15. Default constants canon (the chunk-size numbers) — KNOWN (`core/constants.py`)

```
DEFAULT_TEMPERATURE=0.1   DEFAULT_CONTEXT_WINDOW=3900   DEFAULT_NUM_OUTPUTS=256
DEFAULT_CHUNK_SIZE=1024   DEFAULT_CHUNK_OVERLAP=20      DEFAULT_SIMILARITY_TOP_K=2
DEFAULT_EMBED_BATCH_SIZE=10   DEFAULT_EMBEDDING_DIM=1536 (ada-002)
SentenceSplitter: SENTENCE_CHUNK_OVERLAP=200 (10× the token splitter), CJK regex "[^,.;。？！]+[,.;。？！]?|[,.;。？！]"
HierarchicalNodeParser chunk_sizes=[2048,512,128]
SemanticSplitter breakpoint_percentile_threshold=95
```
`IngestionPipeline` dedup: sha256(node_content + transform_config) cache key, `remove_unstable_values` strips `<obj at 0x...>` so the hash is stable across processes; `DocstoreStrategy` UPSERTS/DUPLICATES_ONLY/UPSERTS_AND_DELETE; changed doc cascades a vector-store delete before re-embed.

**VERSO-RELATION: neutral-context.** These are document-ingestion/chunking constants — a RAG data-framework concern. Verso's ContextBundle/prune operate on tokens/messages, not document chunking. The stable-hash-across-processes trick (strip repr addresses) is a tidy idea but applies to an ingestion cache Verso doesn't have. KV-cache stability is Verso's analogous concern and is already handled at the prefix level.

---

## 16. Observability — instrumentation dispatcher + OTel — KNOWN

`stream_events()` yields every event written via `ctx.write_event_to_stream` (AgentInput/AgentSetup/AgentStream(+`thinking_delta` for reasoning models)/AgentOutput/ToolCall/ToolCallResult). Separate `llama-index-instrumentation==0.5.0`: `@dispatcher.span` emits SpanEnter/Exit/Drop events with `span_id`/`parent_id` via contextvars; hierarchical-by-`__name__` like stdlib logging; OTel/Phoenix/Langfuse exporters. Event taxonomy: LLMChatStart/End, EmbeddingStart/End, RetrievalStart/End, QueryStart/End, SynthesizeStart/End.

**VERSO-RELATION: verso-already-has.** Verso ships VersoSpan + OTel + typed true-delta streaming events (message/reasoning/tool.start/tool.result/done) + SSE. The `thinking_delta` reasoning-model field maps to Verso's `reasoning` delta event. Verso's eval-from-trace ("captured failure IS a regression test") is stronger than LlamaIndex's pure-observability spans.

---

## 17. Tools & schema — KNOWN

`FunctionTool.from_defaults(fn, async_fn, name, description, return_direct, ...)` auto-derives JSON schema via Pydantic v2 `TypeAdapter` (source: "much better than Swarm's hand-mapped type_map"). `requires_context: bool` injects the workflow Context as a kwarg. MCP via `McpToolSpec(...).to_tool_list_async()` → each MCP tool becomes a `FunctionTool`. Tool types: `FunctionTool`, `QueryEngineTool`, `RetrieverTool`, `ToolSpec`. 500+ tool packages on LlamaHub.

**VERSO-RELATION: verso-already-has.** Verso `@tool` (docstring→schema), `tool_from_schema` (raw/MCP adapter), per-tool idempotent/max_attempts/timeout_seconds. MCP-as-opt-in-adapter matches Verso's exact stance (native `@tool` is THE path). `QueryEngineTool`/`RetrieverTool` (wrap a RAG engine as a tool) is the one retrieval-ergonomics idea worth noting but is just "make retrieval a tool" — Verso already does tools.

---

## Honest leanness read

The source itself documents that LlamaIndex *converged onto* the Workflow/event-FSM as its agent runtime — i.e. it grew the graph. Verso's thesis is the deliberate opposite. The retrieval/RAG machinery (synthesizers, query-engine decomposition, 8 index types, node parsers) is a data-framework's domain that Verso correctly does not own. The genuinely transferable retrieval-ergonomics idea is narrow: RRF-rank the **tool catalog** per query (`tool_retriever`), which Verso can do additively with its existing RRF.
