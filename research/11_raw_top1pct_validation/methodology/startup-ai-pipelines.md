# Raw Extraction — Startup AI Pipelines (reverse-engineered shipping startups)

**Source file:** `/Users/seventyleven/Desktop/researchfms/core/08_STARTUP_AI_PIPELINES.md` (677KB, 9090 lines)
**Track:** methodology · **Unit:** startup-ai-pipelines
**What it is:** Reverse-engineered AI pipelines from real shipping startups (Composio, Hyperspell, JetBrains Junie, Unsiloed, MangoDesk, ZeroEntropy/Nia, OpenEvolve/ShinkaEvolve, TinyFish, Abridge, Supermemory, Stagehand/Browserbase, xAI Grok 4.20, social-sim). Extracted from leaked prompts, SDK source, OpenAPI specs, JAR/binary analysis. Each item below is tagged KNOWN (verbatim from source artifact) or INFERRED per the source doc's own labeling.

Bounded reads only (grep-first). Lines read: 198-257, 490-619, 1040-1130, 4495-4533, 4734-4853, 5178-5288, 5420-5529. Anchors grepped: agent loop, max_steps, retry, backoff, fallback, structured output, streaming/SSE, context, memory, cost.

---

## FINDING 1 — done()-tool termination + maxSteps + ensureDone() grace call (Stagehand / Browserbase) [KNOWN]

The single most Verso-shaped pattern in the file. Stagehand's `V3AgentHandler` loop (KNOWN from `v3AgentHandler.ts:114,377`):

```typescript
// Stop conditions
stopWhen: [
  (result) => result.steps.at(-1)?.toolCalls?.some(tc => tc.toolName === "done"),  // done called
  stepCountIs(maxSteps),  // maxSteps reached (default: 20)
]
// After loop
ensureDone(): if (!doneToolCalled) {
  generateText({ toolChoice: { type: "tool", toolName: "done" } })
}
```

- `AGENT_MAX_STEPS = 20` (v3AgentHandler.ts:114); `CUA_MAX_STEPS = 10` (OpenAICUAClient.ts:141).
- Max-steps hit returns a *structured* result, not a crash: `{ success: false, message: "Agent stopped: reached maximum steps (N)" }`.
- "Done not called → `ensureDone()` forces final assessment call" — i.e. a forced grace generation pinned to `toolChoice: done`.
- Per-step hooks: `prepareStep` (pre-step, can inject a user message — e.g. captcha-solved notice), `onStepFinish` (collect reasoning, map tool results, record replay step for caching).
- `DEFAULT_AGENT_TOOL_TIMEOUT_MS = 45,000` per tool; `AGENT_TEMPERATURE = 1`; `GRACEFUL_SHUTDOWN_PERIOD = 30,000ms`.

**Verso mapping:** verso-already-has. This is almost exactly Verso's loop: `done()` tool termination, `max_steps` cap with grace-call at `max_steps_policy`, per-tool `timeout_seconds`, pre/post-step hooks. Independent production confirmation of Verso's exact loop shape and the grace-call decision.

## FINDING 2 — Tool error fed back to the LLM as text = "the core self-healing loop" (Stagehand) [KNOWN]

§21.8 verbatim: "**Tool execution failures:** Tool timeout wrapper catches error → returns `{ success: false, error: "TimeoutError: <message> <hint>" }` to LLM. LLM retries with different approach. **This is the core self-healing loop.**"

- CUA failures: "On `computer_call` failure → capture screenshot anyway, send `computer_call_output` with error field." (never silently drops; always returns an observation).
- Browserbase HTTP retry table (KNOWN): 401/404 → No auto-retry; 408 → Yes (2 retries); 429/5xx/connection → Yes. `SDK_DEFAULT_RETRIES = 2`.
- 21-type error class hierarchy under one `StagehandError` root (e.g. `MissingLLMConfigurationError`, `UnsupportedModelProviderError`, `TimeoutError`, `AgentAbortError`).

**Verso mapping:** verso-already-has. Verso's `Retry(feedback)` self-healing + tool-error-as-observation + typed error taxonomy (auth/content fail-fast, transient retry) = identical philosophy. The phrase "this is the core self-healing loop" is a quotable external endorsement of Verso's reask-on-error design.

## FINDING 3 — Two-model tiering: cheap model for high-volume low-complexity subtasks (JetBrains Junie) [KNOWN architecture]

§3.3 "Two-Model Architecture": Primary (Sonnet/Opus/GPT-4o) for reasoning, code-gen, complex decisions, edit-gen. Faster model (Haiku/Flash/GPT-4.1-mini) for **context compression, task classification, memory extraction, capability filtering**. "Automatic model selection based on task complexity. The faster model handles high-volume, low-complexity subtasks to reduce cost/latency."

Recurs across the file:
- Unsiloed extraction tiers: `alpha (fast), beta (balanced), gamma (default), delta (advanced)` (§6.2), plus `model-v1/v2/v3 (faster/balanced/quality)` for RAG chat.
- ZeroEntropy/Nia: `tracer-fast` = Claude Haiku (no extended thinking, no `thinking_chunk` events); `tracer-deep` = single Opus with extended thinking.
- Stagehand: per-call temperature differs by task — `AGENT_TEMPERATURE = 1` but `EXTRACT_TEMPERATURE = 0.1` (extraction wants determinism).
- Stagehand defaults: `DEFAULT_MODEL_NAME = "openai/gpt-4.1-mini"`, `SERVER_V4_DEFAULT_MODEL = "openai/gpt-4.1-nano"` — cheap models are the *default*, big model opt-in.

**Verso mapping:** verso-already-has (mechanism), neutral-context (policy). Verso ships per-call `model=` swap + `agent.override()` + `init_model("provider:model")`, so a user can route compression/classification to a cheap model trivially. Verso deliberately does NOT ship a *learned/auto* router (NON-GOAL: "no learned routers", "not a router/planner cult") — these startups do "automatic model selection," which Verso correctly refuses as a built-in primitive.

## FINDING 4 — OpenAI-compatible SSE delta envelope is the de-facto streaming wire format [KNOWN]

Multiple independent startups converge on the same streaming shape — `{"choices":[{"delta":{...}}]}` OpenAI-compatible chunks — rather than inventing bespoke protocols:

- Nia/ZeroEntropy (§9.x, KNOWN): `event: message` / `data: {"choices":[{"delta":{"tool_calls":[...]}}]}` for tool calls; `delta.content` for text; `delta.sources` for sources; `event: done` terminal.
- Tavily (§11.x, KNOWN from `_render_stream()`): envelope `data:{"choices":[{"delta":{...}}]}\n\n`, 5 event types in sequence ending in content delta; explicitly "OpenAI-compatible format, not a Tavily-specific SSE schema." `"object": "chat.completion.chunk"`.
- xAI Grok (§20.11): SSE over HTTP, events `response.created` / `response.output_item.added` / `response.output_text.delta` / `response.output_item.done` / `response.completed`, terminal `data: [DONE]`. Note: "Tool calls returned atomically in single chunk (NOT streamed)."
- ZeroEntropy SDK `_streaming.py` is "a generic SSE decoder — zero tracer-specific type constants. Application layer handles event routing" (i.e. keep the decoder dumb, route events in app code).

**Verso mapping:** verso-already-has. Verso ships typed true-delta events (message/reasoning/tool.start/tool.result/done) + SSE. Confirms Verso's event taxonomy matches the field's de-facto vocabulary; the "generic decoder, app routes events" note matches Verso's typed-event design.

## FINDING 5 — Context-budget-triggered summarization that PRESERVES negative constraints (Supermemory + Junie) [KNOWN]

Supermemory coding-agent integration (§17.3, KNOWN): "At **80% context usage**, triggers structured summarization preserving: literal requests, end goals, files touched, remaining work, **negative constraints (things forbidden or that failed)**."

JetBrains Junie `CompressHistoryProcessor` (§3.5): "Compresses old conversation turns / Preserves recent context (10-20 turns)." Junie `MemoryCompactor`: "Maintains memory budget." `MemoryExtractor` does 3 reflection types: Error (what went wrong + how to avoid), Trajectory (successful paths), User (preferences).

withSupermemory middleware (§17.3) per-turn injection: extract last user msg → LRU cache (max 100, key `containerTag:threadId:mode:normalizedMessage`) → on miss `POST /v4/profile` → dedup static>dynamic>search → format as markdown → inject into system prompt. Three modes: `profile`/`query`/`full`. `aggregate:true` (§17.5) condenses multiple memories into one slot to beat the limit=k precision/recall cliff.

**Verso mapping:** verso-already-has (mechanism) + steal-additive (one detail). Verso's `prune()` masks (never silent-drops) and `reflect()` consolidates — same family. The specific, transferable idea NOT explicit in Verso: when compacting, **explicitly carry forward "negative constraints" (things forbidden / things that already failed)** as a first-class preserved field. Verso already keeps masked tool outputs recoverable, but does not name a "what failed / what is forbidden" slot in its compaction contract. Cheap, additive, byte-identical when unused.

## FINDING 6 — Refuse-the-graph evidence + meta-tools to avoid context bloat (Composio, Stagehand, Hyperspell) [KNOWN]

Direct anti-complexity signals from shipping systems:

- Composio (§1.1): instead of loading 1000+ tool schemas (~100K tokens), expose **exactly 6 meta-tools** (~2K tokens): `SEARCH_TOOLS`, `GET_TOOL_SCHEMAS`, `MULTI_EXECUTE_TOOL`, `MANAGE_CONNECTIONS`, `REMOTE_WORKBENCH`, `RECIPES`. "The agent searches for tools at runtime, loads only what it needs."
- Stagehand (§21.10): "**Stagehand is single-agent per instance. Multi-agent patterns require application-layer design.**" — refuses to make multi-agent a core primitive; parallelism is just N independent sessions, "no shared state."
- xAI Grok (§20.4): even in heavy multi-agent mode, "Client-side function calling... NOT supported in multi-agent mode" — they keep the simple tool-call path separate from the orchestration path.
- Hyperspell openclaw plugin (§2.x): memory integrates as "**auto-context injection: query memory before every turn**" — a single pre-turn hook, not a graph node.
- MangoDesk (§7.1, KNOWN): hard fallback when the AI eval service 502s — "Fallback: if Railway 502, direct Supabase update (**no AI eval**)." A shipping startup degrades gracefully to NO model rather than building elaborate retry orchestration.

**Verso mapping:** verso-already-has + neutral-context (validation). Strong external support for Verso's thesis: native `@tool` over MCP-first; single clean loop over graph; multi-agent (if any) as app-layer, not a built-in orchestrator-primitive. Composio's 6-meta-tool dynamic discovery is on Verso's NON-GOAL boundary (MCP-first / tool-router cult) — note it as a pattern Verso deliberately does NOT adopt as core; Verso's answer is native `@tool` + `tool_from_schema` opt-in, not a runtime tool-search router.

---

## SECONDARY / SUPPORTING (numbers worth keeping)

- **Retry constants are boringly uniform across the file** (exponential backoff, small caps): TinyFish `_RETRY_MULTIPLIER=0.5, _RETRY_MAX_WAIT=8.0s, retry_on [408,429,5xx]`; OpenEvolve `RETRY_MAX_RETRIES=2, RETRY_MAX_WAIT_MS=8000`; Abridge `tenacity wait_random_exponential(min=1,max=60), stop_after_attempt(50)`; Zep `max_retries=3, initial_delay=1.0s, max_delay=30.0s, backoff_factor=2.0, jitter=True`; Google client "5-retry exponential backoff (others do not)"; generic web frontends `MAX_API_RETRIES=3, RETRY_BASE_DELAY=2s`. KNOWN. Maps to Verso `RetryPolicy` — confirms small-cap exponential-backoff-with-jitter is the universal default; nobody builds anything fancier.
- **Poll-backoff pattern** (job-based async): `POLL_BACKOFF_FACTOR=1.5`, initial 2s, cap 10s (OpenEvolve/Nia). Job-based SSE: `POST` returns `job_id` immediately, then `GET /.../{job_id}/stream`. KNOWN. (Verso's durable seam covers the resumable side of this; the polling envelope is app-layer.)
- **OpenEvolve agent loop (§10.3, KNOWN architecture):** "Termination: max_iterations reached OR human stops OR all eval cases pass." Eval-driven termination = "all eval cases pass" — eval is the stop condition, echoing Verso's "prod==eval." Steer-during-run: "graceful stop of current workers + restart."
- **Unsiloed schema extraction (§6.2, KNOWN):** `Document + JSON Schema → schema-guided extraction → per field {value, confidence (0-1), page_no}`, output "JSON matching input schema + per-field metadata." Structured output = JSON-schema-in, validated-typed-out. Maps to Verso `output_type=`. The per-field confidence(0-1) is a detail Verso's structured output does not surface.
- **Junie verification loop (§3.x, KNOWN):** "Verification loop: IDE inspections run after every edit → errors injected as context." = verify-before-done gate, exactly Verso's scaffold ratchet / verify gate. Also a 12-strategy edit-match waterfall ending in "12. LLM fallback — if all heuristic strategies fail, ask the LLM" — mirrors Verso's jsonish 4-stage parse waterfall philosophy (cheap deterministic strategies first, model only as last resort).
- **Grok multi-agent debate (§20.3, KNOWN+INFERRED):** consensus over 2-4 rounds, ≤180-token debate budget, `wait` 120s/call & 200s global; on consensus failure "Grok decides unilaterally." This is the heavy-orchestration end of the spectrum Verso refuses as a core primitive (NON-GOAL: no orchestrator-as-primitive). Note as avoid-overkill context.
