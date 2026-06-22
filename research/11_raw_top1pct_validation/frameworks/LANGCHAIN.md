# LANGCHAIN — Raw Extraction (frameworks track)

Source read: `/Users/seventyleven/Desktop/researchfms/teardowns/LANGCHAIN.md` (1820 lines, 112KB).
Repo teardown of `langchain-ai/langchain @ 365c36c2 / e208f38` (2026-05). 211,042 lines of `.py` excluding tests; 11 top-level packages.

Verso lens: this is the canonical "popular because first, abstractions too heavy" case. Mostly an OVERKILL CATALOG of what Verso's "no graph, one clean loop, additive primitives" thesis must refuse. A few durable ideas worth keeping are flagged.

---

## A. THE ANTI-PATTERN CATALOG (what LangChain over-abstracts — Verso must avoid)

### A1. Runnable / LCEL as universal interface (the core over-abstraction)
- KNOWN: "LangChain provides one composable primitive — the **Runnable**" — every external interaction (LLM call, tool, vector lookup, output parser, prompt template) is a concrete Runnable implementing `invoke / ainvoke / stream / astream / batch / abatch`, composed with `|`. Pitch = "same as Unix pipes."
- The `|` operator is a 2-line method on the `Runnable` ABC (`base.py:619-638`): `__or__` returns `RunnableSequence(self, coerce_to_runnable(other))`. `__ror__` makes `dict | runnable` work (dict coerced to `RunnableParallel`).
- `coerce_to_runnable` (`base.py:6489-6513`) dispatches: Runnable→self, async-generator→`RunnableGenerator`, callable→`RunnableLambda`, dict→`RunnableParallel`, else `TypeError`.
- `RunnableSequence.__init__` (3089-3128) does recursive-flatten so `(a|b)|(c|d)` becomes flat `RunnableSequence(a,b,c,d)`. Internal storage split into `(first, middle, last)` is "purely a typing trick … solely for type checking purposes" (docstring 3082-3087).
- `_RUNNABLE_SEQUENCE_MIN_STEPS = 2`.
- The Runnable runtime family: `RunnableParallel` (fan-out via `ThreadPoolExecutor` sync / `asyncio.gather` async, `max_workers=min(32, os.cpu_count()+4)`), `RunnableBranch` (first-match-wins conditional dispatch, 461 lines), `RunnableLambda` (~870 lines), `RunnableGenerator`, `RunnableBinding`, plus `.pick / .with_config / .with_retry / .with_fallbacks / .bind / .map / .astream_events / .astream_log`.
- VERSO RELATION: avoid-overkill. Verso has ONE clean async ReAct loop (<200 lines), not a universal composition algebra. The `|` pipe DSL is exactly the "graph/DSL by default" Verso refuses. Replication estimate in the source: ~600 lines for just the `Runnable` ABC, ~6,000-8,000 lines for the full LCEL runtime + parsers + prompts + core retrievers (no integrations).

### A2. Chains-of-chains (legacy, deprecated but still load-bearing)
- KNOWN: `langchain_classic.chains.base.Chain` (806 lines, deprecated since 0.3) — stateful object with `input_keys`/`output_keys`, callbacks, memory, `_call(inputs)->outputs`. Subclasses: `LLMChain`, `SequentialChain`, `RetrievalQA`, `ConversationalRetrievalChain`, `ConversationChain`, `MapReduceChain`. "Effectively obsolete now that `Runnable` covers the same surface."
- VERSO RELATION: avoid-overkill. The two-layer Chain-then-Runnable history IS the heavy-abstraction story. Verso must never grow a parallel stateful-chain primitive.

### A3. TWO parallel agent stacks (the concession evidence)
- KNOWN: LangChain split into two agent stacks around v0.3:
  - v0 `langchain_classic.agents.AgentExecutor` — original ReAct `while` loop, "Deprecated but still widely deployed."
  - v1 `langchain.agents.create_agent` (`libs/langchain_v1/`) — "a thin shim over **LangGraph's** Pregel runtime." Adds a middleware system.
- The v1 rewrite means "The agent loop is no longer a `while` in this file — it lives in the LangGraph Pregel runtime." Termination is "**not** a counter on this side — it's controlled by LangGraph's `recursion_limit` (default 25 supersteps)."
- VERSO RELATION: avoid-overkill / leanness EVIDENCE. This is the literal "abstractions were too heavy → we rewrote on a graph runtime" arc. Verso's tactical↔durable seam is the counter-design: promote with ONE flag, no rewrite onto a separate Pregel/graph engine.

### A4. The callback manager (latency tax)
- KNOWN: `callbacks/manager.py` (2,792 lines). "Every Runnable/Chain/Agent/Tool method calls `callback_manager.on_*_start` and `on_*_end`." 12 hook methods.
- HONEST GAP (from source §10): "LangChain v0 wraps almost every operation in a callback manager that walks a parent chain. Cold-path overhead is real (typically **10-50ms per Runnable hop**)."
- VERSO RELATION: avoid-overkill. The per-hop callback-walk is the cost of the universal-interface dogma. Verso's hooks (pre/post_model, pre/post_tool, on_stop) are byte-identical-when-unused, not a mandatory wrapper on every primitive.

### A5. RunnableConfig implicit context propagation
- KNOWN: `RunnableConfig` TypedDict (`config.py:49-120`, `total=False`). `var_child_runnable_config: ContextVar` + `ensure_config()` make tags/metadata/callbacks propagate down a chain WITHOUT explicit passing — `copy_context()` + `context.run(step.invoke)` per step.
- Constants: `CONFIG_KEYS` = 8 keys; `COPIABLE_KEYS` = 4; `DEFAULT_RECURSION_LIMIT = 25`.
- VERSO RELATION: avoid-overkill. Magic ContextVar propagation is implicit-state action-at-a-distance. Verso uses explicit typed `ctx.deps` injection.

### A6. Legacy memory zoo (all `@deprecated since 0.3.1, removal 2.0.0`)
- KNOWN: `memory/` (2,201 lines). 9+ classes: `ConversationBufferMemory`, `BufferWindowMemory` (last `k`), `TokenBufferMemory`, `ConversationSummaryMemory` (rolling LLM summary), `SummaryBufferMemory`, `ConversationEntityMemory`, `ConversationKGMemory` (KG triples, delimiter `<|>`), `CombinedMemory`, `VectorStoreRetrieverMemory`. Plus 30+ chat-history backend adapters.
- VERSO RELATION: avoid-overkill (the proliferation) BUT Verso-already-has the durable equivalent: typed 4-tier memory, temporal, RRF recall, reflect() consolidation. LangChain itself deprecated the whole zoo in favor of "LangGraph Checkpointer + BaseStore + SummarizationMiddleware."

### A7. LLM-summarization compaction by default
- KNOWN: `SummarizationMiddleware` (658 lines), `before_model` hook fires when token count > `max_tokens_before_summary` (default **4000**), invokes a separate `summary_model` (often cheaper) and replaces older messages with a `SystemMessage` summary.
- VERSO RELATION: avoid-overkill. LLM-summarization-compaction-by-default is explicitly on Verso's NON-GOALS list. Verso's `prune()` masks old tool outputs deterministically (never silent-drops, never an extra LLM call).

### A8. Output-parser hierarchy + retry parsers
- KNOWN: `StrOutputParser`, `JsonOutputParser` (partial-streaming via `parse_partial_json`), `PydanticOutputParser` (dual Pydantic v1+v2), `JsonOutputToolsParser`, `PydanticToolsParser`, `OutputFixingParser` (`max_retries=1`), `RetryOutputParser` (`max_retries=1`). ~800 lines.
- VERSO RELATION: mostly verso-already-has. Verso ships jsonish 4-stage parse waterfall + output_type= + in-loop reask (append ValidationError + re-drive) + Retry(feedback). LangChain's separate fixing/retry PARSER objects are more surface for the same job.

### A9. Pydantic v1/v2 dual paths (permanent bug source)
- KNOWN HONEST GAP: "both Pydantic v1 and v2 paths exist throughout `tools/base.py`. This is a permanent source of subtle bugs."
- VERSO RELATION: neutral-context (cautionary). Evidence that dual-support sprawl is a tax.

---

## B. DURABLE IDEAS WORTH KEEPING (and where Verso already has them)

### B1. init_chat_model("provider:model") string router
- KNOWN: `init_chat_model(model, **kwargs)` — `model` string is `"<provider>:<model_name>"` (e.g. `"openai:gpt-4o"`, `"anthropic:claude-sonnet-4-5"`, `"groq:llama-3.3-70b"`). Lazily imports the right partner package. Supported (read from if/elif): openai, anthropic, azure_openai, azure_ai, google_vertexai, google_genai, bedrock, bedrock_converse, cohere, fireworks, together, mistralai, huggingface, groq, ollama, deepseek, xai, perplexity, openrouter.
- VERSO RELATION: verso-already-has. Verso ships `init_model("provider:model")` + any OpenAI-compatible base_url. Identical idea.

### B2. with_structured_output — provider-portable, three strategies
- KNOWN: `with_structured_output(schema, include_raw=False)` picks: (1) `method="function_calling"` (bind tool, force tool_choice); (2) `method="json_schema"` (native, OpenAI `response_format`); (3) `method="json_mode"` (JSON mode + Pydantic post-validation). v1 `AutoStrategy` picks by model profile; `ToolStrategy` vs `ProviderStrategy`.
- `FALLBACK_MODELS_WITH_STRUCTURED_OUTPUT` list lets AutoStrategy assume native support when profile data is missing.
- VERSO RELATION: verso-already-has. Verso ships output_type= with provider-aware routing + in-loop reask. The model-profile-driven AutoStrategy fallback table is a minor detail Verso need not copy.

### B3. RRF / EnsembleRetriever (c=60)
- KNOWN verbatim (`retrievers/ensemble.py:304-352`): weighted Reciprocal Rank Fusion, `score(d) = Σ_i w_i / (rank_i(d) + 60)`, constant `c=60` (original Cormack-Buettcher SIGIR'09 value), weights default `[1/N]*N`.
- VERSO RELATION: verso-already-has. Verso ships RRF retrieval already.

### B4. with_retry — exponential backoff with jitter
- KNOWN: `model.with_retry(stop_after_attempt=N)` → `RunnableRetry` (`runnables/retry.py`). Defaults `stop_after_attempt=3`, `wait_exponential_jitter=True`, `wait_exponential_multiplier=1.0`.
- VERSO RELATION: verso-already-has. Verso ships RetryPolicy + FailoverModel with typed errors (auth/content fail fast).

### B5. Two output formats per AIMessage: content + content_blocks
- KNOWN (source §9 "what's novel" #5): every AIMessage carries `content` (provider-native) AND `content_blocks` (standardized cross-provider: `text`, `tool_use`, `image_url`, `reasoning`, …). "Lets the same downstream code handle responses from any model."
- VERSO RELATION: neutral-context / possible steal-additive (low confidence). Verso has typed streaming delta events (message/reasoning/tool.start/tool.result). A standardized cross-provider content-block normalization on the non-stream message object MIGHT be additive IF Verso lacks a single normalized multi-modal message shape — but this is likely already covered by adapter normalization. Default to verso-already-has.

### B6. disable_streaming="tool_calling" auto-fallback
- KNOWN: providers that can't reliably stream tool-call argument JSON auto-fall-back to `invoke()` only when `tools=` bound.
- VERSO RELATION: neutral-context. Minor provider-quirk handling; Verso's adapters can carry equivalent.

### B7. standard-tests conformance suite
- KNOWN: `libs/standard-tests/` — every partner package MUST pass `ChatModelIntegrationTests` covering `invoke`, `stream`, `bind_tools`, `with_structured_output`, `usage_metadata`, image/audio content blocks, system handling, stop sequences. This is what makes 700+ integrations interchangeable.
- VERSO RELATION: neutral-context. The integration surface (700+) is "the actual moat … Writing your own 700 production-grade integrations is a 50-engineer-year company." Verso is deliberately NOT competing on integration breadth (non-goal: not an SDK).

---

## C. v1 MIDDLEWARE SYSTEM (the ordered-hooks idea)

- KNOWN (`middleware/types.py`): `before_agent`, `before_model`, `wrap_model_call(request, handler)` (mutate ModelRequest / retry / swap model / short-circuit), `after_model` (can set `state["jump_to"]="tools"|"model"|"end"`), `wrap_tool_call(request, handler)` (caching/retry/modification/suppression), `after_agent`. All have async variants; all `traceable(...)` decorated.
- Built-in middleware (lines of code): `SummarizationMiddleware` (658), `HumanInTheLoopMiddleware` (412, interrupts before tool for approval), `ModelCallLimitMiddleware` (267), `ToolCallLimitMiddleware` (488), `ModelRetryMiddleware` (312), `ToolRetryMiddleware`, `ModelFallbackMiddleware` (138), `PIIDetectionMiddleware` (376), `ContextEditingMiddleware` (298), plus `FileSearchMiddleware`, `ShellToolMiddleware`, `ToolEmulator`, `ToolSelectionMiddleware`, `TodoMiddleware`.
- VERSO RELATION: mostly verso-already-has + avoid-overkill. The middleware CONCEPT (ordered composable wraps around model/tool calls) maps onto Verso's Hooks (pre/post_model, pre/post_tool, on_stop, should_continue) + per-tool idempotent/max_attempts/timeout + ask_once HITL. The PROLIFERATION of 15 named middleware classes each 100-600 lines, plus `state["jump_to"]` graph-routing, is the overkill Verso refuses — Verso's hooks are byte-identical-when-unused, not a graph-state mutation API.

---

## D. DEFAULTS / NUMBERS (KNOWN, for reference)

- v0 `AgentExecutor`: `max_iterations=15`, `early_stopping_method="force"` (force → literal string `"Agent stopped due to iteration limit or time limit."`; "generate" → one more LLM call), `handle_parsing_errors=False`, `trim_intermediate_steps=-1`.
- v1 LangGraph `recursion_limit=25` supersteps; graceful exit string `"Sorry, need more steps to process this request."`; `state["remaining_steps"]` surfaced to the model.
- `_generate_with_cache` (~300 lines) hashes (prompt, stop, identifying_params) into a `BaseCache`.
- OpenAI integration `base.py` = **5,041 lines** (Azure variant, response API, o1/o3/gpt-5 special-casing, etc.).
- Legacy "conversational" agent prompt opens with "Assistant is a large language model trained by OpenAI. …" and uses `Thought: Do I need to use a tool? Yes|No` — deprecated personality leak (HONEST GAP §10: "Default prompts contain personality language … default error strings leak into model context, prompt templates are fragile to whitespace").
- `CONFIGURABLE_TO_TRACING_METADATA_EXCLUDED_KEYS = frozenset(("api_key",))` — secrets not auto-promoted into trace metadata.

---

## E. PLATFORM / OBSERVABILITY (context)
- LangServe (FastAPI wrapper exposing invoke/stream/batch as REST + Swagger). LangGraph Cloud/Platform (managed compiled StateGraphs). LangSmith (closed-source SaaS, traces/evals/prompt registry; every Runnable `traceable(...)` decorated). `astream_events(version="v2")` IS the LangSmith trace stream.
- VERSO RELATION: neutral-context / NON-GOAL. Verso is not an SDK / not a deployment platform. Eval/trace is first-class in Verso natively (VersoSpan + OTel, prod==eval), not bolted to a closed SaaS.

---

## F. LEANNESS VERDICT
The teardown is overwhelming SUPPORTING evidence for Verso's thesis. LangChain's own v0→v1 history is the canonical "abstractions too heavy → rewrite onto a graph runtime (LangGraph)" arc: a universal `Runnable`/`|` DSL, a 2,792-line callback manager taxing every hop (10-50ms), a deprecated 806-line Chain layer, a deprecated 2,201-line memory zoo, and 15 middleware classes. Source's own replication note: the *core* agent loop is "a long weekend" (~1,500 lines) and the LCEL runtime ~6,000-8,000 lines — but the value ("the actual moat") is 700+ integrations, NOT the framework. Verso correctly competes on the boring core done right, not the abstraction algebra.
