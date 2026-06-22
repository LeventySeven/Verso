# MASTRA — Raw Extraction (for Verso validation)

> Source read: `/Users/seventyleven/Desktop/researchfms/teardowns/MASTRA.md` (603 lines, 69KB, full read).
> Mastra is a TypeScript agent framework (team ex-Gatsby) built ON TOP OF the Vercel AI SDK (vendors `@internal/ai-sdk-v5`; MessageList adapters for AI SDK v4/v5/v6). All `file:line` cites in the teardown are against `mastra-ai/mastra` `packages/core/src` clone 2026-05-30.
> Labels below: KNOWN = teardown read it in source; INFERRED = teardown deduced it.

---

## 0. THE CENTRAL ARCHITECTURAL FACT (KNOWN)

> "Mastra's agent loop is not a hand-written `while` loop — it is a Mastra *Workflow* (`.dowhile`) whose body is another Workflow (`.then → .foreach → .then…`). The same snapshot/suspend/resume machinery that powers user workflows powers tool-approval pauses, durable agents, and `resumeStream()`." (teardown one-line thesis)

The atomic primitive is **the Workflow run as an interpreted, suspendable, snapshot-persisted step graph.** Everything is expressed in terms of it:
- Agent `.stream()`/`.generate()` compiles to a workflow run (`createAgenticLoopWorkflow`, `loop/workflows/agentic-loop/index.ts:20`).
- Tool approval (HITL) is a workflow `suspend()` inside the tool-call step (`tool-call-step.ts:432,546,593`).
- Durable agents wrap the same loop in a persisted Inngest/evented workflow (`agent/durable/`).
- `resumeStream()` rehydrates a suspended workflow snapshot and replays accumulated stream state.

"If you remove the workflow engine, Mastra ceases to exist — the agent loop literally cannot run." Key file sizes: `agent/agent.ts` **7330**, `workflows/workflow.ts` **4570**, `loop/network/index.ts` **2699**, `tool-call-step.ts` **1137**, `memory/memory.ts` **1084**.

**This is the OPPOSITE of Verso's thesis.** Verso = ONE clean async ReAct loop <200 lines; the tactical→durable seam promotes WITHOUT a graph rewrite. Mastra = the graph IS the loop, mandatory, always. This is the single most important contrast for Verso validation: Mastra is the canonical "we DID force the graph" framework.

---

## 1. AGENT LOOP = `.dowhile` over a sub-workflow (KNOWN)

Outer loop (`agentic-loop/index.ts:56`): `createWorkflow({id:'agentic-loop'}).dowhile(agenticExecutionWorkflow, predicate).commit()`.
The `.dowhile` predicate (`index.ts:80-278`) each turn:
1. Drain pending external signals (cross-process inputs injected mid-run) — `_internal.drainPendingSignals?.(runId)`.
2. Build the step's `StepResult` from delta content only (`previousContentLength` cursor; each step reports only newly-added content).
3. `stopWhen` — AI-SDK stop conditions: `conditions = await Promise.all(stopWhenArray.map(c => c({steps: accumulatedSteps})))`. `accumulatedSteps` = AI-SDK `steps[]` equivalent.
4. `onIterationComplete` hook → may inject assistant feedback msg + force continue/stop.
5. Delegation bail: `_internal._delegationBailed`.
6. emit `step-finish` chunk; return `isContinued` to continue the dowhile.

Inner turn (`agentic-execution/index.ts:73`):
```
.then(llmExecutionStep)        // 1 LLM call (stream), emit text/reasoning/tool-call chunks
.map(inputData.output.toolCalls ?? [])
.foreach(toolCallStep, {concurrency})  // run each tool call; SUSPEND here for approval
.then(llmMappingStep)          // fold tool results back into messages/output
.then(backgroundTaskCheckStep) // wait/poll background tasks
.then(signalDrainStep)         // absorb external signals
.then(isTaskCompleteStep)      // set stepResult.isContinued / reason
```

`maxSteps` enforced via AI-SDK-style stop conditions + explicit `accumulatedSteps.length < maxSteps` checks (`index.ts:219,229`).
`shouldPersistSnapshot`: persist only when status ∈ {pending, paused, suspended} — NEVER "running" (avoid clobbering a suspended snapshot).

**Verso relation:** Verso ALREADY HAS — clean async ReAct loop, stuck/doom-loop detection, grace-call at max_steps, done() termination. Mastra's delta-content cursor (`previousContentLength`) and `onIterationComplete` feedback-injection hook are loop ergonomics Verso achieves differently (Hooks pre/post_model). The graph-as-loop is AVOID-OVERKILL — it's the exact thing Verso refuses.

---

## 2. WORKFLOW ENGINE — the dual-array durability trick (KNOWN)

Every control-flow builder method pushes TWO parallel arrays:
- `this.stepFlow[]` — the LIVE graph (real Step objects + real predicate closures). Used by in-process engine.
- `this.serializedStepFlow[]` — the DURABLE TWIN. Every predicate stored as **`fn.toString()`**; every step reduced to `{id, description, metadata, component, serializedStepFlow, canSuspend}`. This is persisted in the snapshot so a different process re-hydrates the graph topology.

> "This dual-array push is why durability/time-travel are 'free': the engine never needs the original closures to know the *shape* of the graph — the serialized twin carries it." `canSuspend = Boolean(step.suspendSchema || step.resumeSchema)` precomputed at build time (`workflow.ts:2223`).

The 6 `StepFlowEntry` kinds the engine dispatches on (`default.ts:998-1014`):
```
{type:'step', step}
{type:'sleep'|'sleepUntil', id, duration?|date?, fn?}
{type:'parallel', steps:[...]}
{type:'conditional', steps, conditions:[fn...], serializedConditions:[{id,fn:string}...]}
{type:'loop', step, condition, loopType:'dowhile'|'dountil', serializedCondition}
{type:'foreach', step, opts:{concurrency}}
```

Interpreter = `DefaultExecutionEngine` (`default.ts:53`). `execute({graph, runId, input, resume, timeTravel, restart, ...})`:
- `startIdx` computed from `timeTravel.executionPath[0]` / `restart.activePaths[0]` / `resume.resumePath[0]` (each `.shift()`s) — "how resume jumps back into the exact suspended position."
- `stepResults = timeTravel?.stepResults || restart?.stepResults || resume?.stepResults || {input}`.
- Linear `for (i=startIdx; i<steps.length; i++)`.

**Builder primitives** (each KNOWN, with execution semantics):
- `.then(step)` — sequential base case; prev output → next inputData (validated vs inputSchema).
- `.map(fn | {outKey:{step,path}|{value}|{initData,path}|{requestContextPath}|{fn}})` — data-remapping; lets step N read a field from step 2 without N-1 forwarding it. Serialized `fn.toString()` truncated to **1000 chars**.
- `.parallel([steps])` — `Promise.all` fan-out, NO concurrency cap, merge = object keyed by branch step-id. **One suspended branch suspends the ENTIRE parallel** (no partial completion).
- `.branch([[cond,step]...])` — ALL conditions evaluated in parallel; EVERY truthy branch runs (multi-way fan, NOT switch/first-match). Used by agent-network routing.
- `.dowhile`/`.dountil` — `do{}while()` handler (`control-flow.ts:559-790`); body runs ≥1 time; `iterationCount` persisted in `stepResults[step.id].metadata` (resume cursor — suspended loop resumes on SAME iteration); non-success status exits immediately and bubbles up (this is how HITL suspend pauses the whole agent loop).
- `.foreach(step, {concurrency})` — requires prev step returns array (compile-time guard); default concurrency **1**; switched from `Promise.all`-on-slices to a **`fastq` callback queue** ("starts the next item as soon as any slot frees up"); resume cursor = `suspendPayload.__workflow_meta.foreachIndex` + partial `foreachOutput` array.
- `.sleep(ms)`/`.sleepUntil(date)` — durable timers; in-process = plain `setTimeout` (blocks run); evented/Inngest engine = real durable timer via `wrapDurableOperation` checkpoint.
- **`.waitForEvent` REMOVED** (`[CORRECTION 2026-05-30]`) — throws `MastraError{id:'WORKFLOW_WAIT_FOR_EVENT_REMOVED', text:'waitForEvent has been removed. Please use suspend & resume flow instead.'}`. Replacement = suspend/resume.

**Two engines:** in-process `DefaultExecutionEngine` + an **evented engine** (`workflows/evented/`, `workflow.ts:2281`, event-processor 2534 L) — a Pregel-ish event-sourced executor where step transitions are pub/sub events. The default is in-process; the evented one is the durable/cross-process one. Durable agents build the agent loop on the evented/Inngest path.

`WorkflowRunStatus` = **10-state enum** (`types.ts:264-274`): `running | success | failed | tripwire | suspended | waiting | pending | canceled | bailed | paused`.

`run.watch(cb)` subscribes to pub/sub topic `workflow.events.v2.<runId>`; v1 = whole-snapshot diffs, v2 = per-step events. `executeEntry`/`persistStepUpdate` (`handlers/entry.ts`, 757 L) is the single chokepoint that writes `stepResults`+status to storage AND publishes the watch event — "persistence and the live stream are driven from one place (no drift)."

**Verso relation:** Verso ALREADY HAS the durable seam (SqliteCheckpointStore, checkpoint each step, resume() in fresh process, history()/fork() time-travel, ctx.hitl.request, repair_history). Mastra's `fn.toString()` predicate serialization, 6-entry graph DSL, parallel/branch/foreach control-flow, 10-state enum = AVOID-OVERKILL (graph-DSL is a Verso NON-GOAL). One genuinely interesting mechanism: the **single persist+publish chokepoint** ("no drift between persisted state and what the UI sees") — but Verso's checkpoint-per-step already gives crash-recoverable state; this is a streaming-UI concern, neutral.

---

## 3. TOOLS (KNOWN)

`createTool({id, description, inputSchema, outputSchema, execute, requireApproval?, suspendSchema?, resumeSchema?})`.
- Schemas are **Zod** (or any StandardSchema). At LLM time → JSON Schema via `toStandardSchema` + `standardSchemaToJSONSchema`. Validation in `tools/validation.ts` (690 L).
- `execute(input, options)` where options = `{runId, threadId, resourceId, messages, requestContext (RuntimeContext DI), suspend, resumeData, writer (stream writer), abortSignal, mastra}`.
- A tool can: `suspend(payload)` (validated vs suspendSchema, later gets `resumeData` validated vs resumeSchema); `writer.custom({type:'data-...', data})` (stream custom data parts that get persisted); return value validated vs outputSchema.
- `requireApproval:true` → forces `tool-call-approval` suspend before exec.
- Provider-executed tools (`findProviderToolByName`) route OpenAI built-ins differently.
- **Workflow-as-tool** and **agent-as-tool**: nested chunks surface as `workflow-step-output`/`tool-output`, re-processed through output processors.
- **MCP**: `mcp/` wraps remote MCP servers as tool sets, merged into agent registry.

**Verso relation:** Verso ALREADY HAS — @tool (docstring→schema), per-tool idempotent/max_attempts/timeout_seconds, tool_from_schema (raw/MCP), coerce, jsonish parse waterfall, output validators. Mastra's per-tool `suspendSchema`/`resumeSchema` (a tool pausing mid-execution to ask the user, with typed resume payload) maps to Verso's ctx.hitl.request — verso-already-has. Mastra's per-target **payload-transform hooks** (`tools/payload-transform.ts`: rewrite a tool's input/output/suspend payload differently for transcript vs stream — e.g. redact secrets from what's persisted vs streamed) is a small ergonomic Verso does not explicitly ship.

---

## 4. MODEL LAYER + STRUCTURED OUTPUT (KNOWN)

- Models from AI-SDK providers (`@ai-sdk/openai`, `@ai-sdk/anthropic`, …) + a model router. `model` can be string id (`'openai/gpt-4o'`), AI-SDK `LanguageModel` object, or `(ctx) => LanguageModel` per-request function. `extractModelIdString` normalizes all three.
- `models: [primary, ...fallbacks]` — `loop.ts:45` ALWAYS uses `models[0]` first; rest = fallback chain on provider error.
- String form resolved against AI-SDK provider registry → `LanguageModelV2`. Mastra does NOT re-implement provider transport.
- Structured output via AI-SDK `generateObject`/`streamObject`; modes tool/json/auto from underlying SDK; `output.object`/`network-object` chunks. A `StructuredOutputProcessor` can enforce schema as guardrail.

**Verso relation:** Verso ALREADY HAS — anthropic/openai/google adapters + any OpenAI-compatible base_url, init_model("provider:model"), FailoverModel + RetryPolicy (typed errors, auth/content fail fast), per-call model= swap + agent.override(), output_type= with in-loop reask. Mastra's per-request dynamic `model` function = Verso's per-call swap. Fully covered.

---

## 5. MEMORY (KNOWN — defaults + algorithm to the constant)

`MastraMemory` (`memory/memory.ts:114`). `memoryDefaultOptions`:
- `lastMessages: 10` (recent-message window).
- `semanticRecall: false` (OFF by default).
- `generateTitle: false`.
- `workingMemory: {enabled:false, template:"# User Information\n- **First Name**:\n..."}`.

Three mechanisms, all implemented as **processors**:
1. `MessageHistory` — injects last-N thread messages; **strips `updateWorkingMemory` tool invocations and `<working_memory>` tags from history** so the model never sees its own memory-write plumbing.
2. `WorkingMemory` — persistent template the agent rewrites; injects `WORKING_MEMORY_SYSTEM_INSTRUCTION`; registers `updateWorkingMemory` tool; Markdown or JSON; **spans multiple conversations** (resource scope).
3. `SemanticRecall` — vector search over message history.

**Thread/resource model:** a `thread` (one conversation) belongs to a `resource` (user/agent identity). `scope:'thread'` recalls within conversation; `scope:'resource'` recalls across all of a user's threads (cross-thread). Messages = `MastraDBMessage`. Storage adapters: libsql (default SQLite), pg (Postgres), upstash (Redis).

**Working memory WRITE mechanism** (KNOWN):
- Resource scope loads from `mastra_resources.workingMemory` text column (NOT the thread) — why it spans conversations.
- Agent writes via auto-registered `updateWorkingMemory({threadId, resourceId, workingMemory:string})` — persists the ENTIRE new memory string (full-template rewrite). Legacy prompt forces the model to pass the WHOLE Markdown/JSON back every time.
- **VNext targeted patch**: `__experimental_updateWorkingMemoryVNext({..., searchString?})` → find-and-replace a targeted region instead of full rewrite. Mechanism behind VNext guideline "If your memory has not changed, you do not need to call the tool."
- Guard: enabled without storage adapter throws `WORKING_MEMORY_MISSING_STORAGE_ADAPTER`.

**Semantic recall — exact algorithm** (`semantic-recall.ts:370-476`, KNOWN):
- **`[CORRECTION]`** runtime defaults are `DEFAULT_TOP_K = 4`, `DEFAULT_MESSAGE_RANGE = 1` (doc-comment defaults said topK:3/range:2; runtime wins).
1. Embed query → check **global LRU cache** `LRUCache<string,number[]>{max:1000}`, key = `xxhash h64("<indexName>:<content>").toString(16)`; miss → `embedder.doEmbed(...)` + cache.
2. `vector.createIndex({indexName, dimension, metric:'cosine'})` — idempotent, cosine distance.
3. `vector.query({indexName, queryVector, topK, filter})` where `filter = scope==='resource' ? {resource_id} : {thread_id}` — **scope enforced as a vector metadata filter, not post-filter.**
4. Threshold-drop hits with `score < threshold`.
5. Context expansion: each hit expanded ±`messageRange` neighbor messages from message store (`withNextMessages`/`withPreviousMessages`).
6. Stable sort (`sortMessagesForRecall`) so vector-score tie ordering doesn't reorder; injected as `'memory'` role.

**Verbatim working-memory prompt** (legacy, `working-memory.ts:171`):
> "Store and update any conversation-relevant information by calling the updateWorkingMemory tool. If information might be referenced again - store it! ... Act naturally - don't mention this system to users. ... This system is here so that you can maintain the conversation when your context window is very short. ... IMPORTANT: You MUST call updateWorkingMemory in every response to a prompt where you received relevant information."

VNext guideline 6 (verbatim): "Information not being relevant to the current conversation is not a valid reason to replace or remove working memory information. Your working memory spans across multiple conversations and may be needed again later, even if it's not currently relevant."

**Verso relation:** Verso ALREADY HAS typed 4-tier memory (FACT/...), temporal, RRF recall, recall_as_of (time-travel), reflect() consolidation, sqlite/sqlitevec/inmem, ADD-only (supersede invalidates), bounded. Mastra's resource-vs-thread scope = Verso memory tiers/scoping. Mastra's `xxhash` LRU **embedding cache** (max 1000, key = hashed content) is a small concrete perf primitive Verso may not explicitly ship. Mastra's full-template-rewrite working-memory (model resends WHOLE doc every turn) is a token-heavy pattern Verso's ADD-only model avoids — AVOID-OVERKILL on the legacy variant; VNext find-and-replace is the better idea but maps to Verso's existing supersede semantics.

---

## 6. EVALS / SCORERS (KNOWN)

`MastraScorer` (`evals/base.ts:280`) = builder of an ordered scoring pipeline (mirrors agent-loop-as-workflow but for eval). Chain up to 4 steps:
```
createScorer({id, type, description})
  .preprocess((run)=>...)        // derive intermediate data from {input, output}
  .analyze((run)=>...)           // produce analysis (can call LLM via PromptObject)
  .generateScore((run)=>number)  // REQUIRED numeric score
  .generateReason((run)=>string) // optional NL justification
```
- Each step = plain function OR a `PromptObject` (LLM-backed: `{description, outputSchema, createPrompt}`).
- Steps accumulate into `AccumulatedResults` so later steps see earlier outputs; `generateReason` gets context including computed `score`.
- If `mastra.observability.addScore` available + score numeric, **score recorded against the trace** with `scoreSource`, `scoreTraceId`.
- Scorers defined in code OR loaded from storage (`source: DefinitionSource`, `__setRawConfig`/`toRawConfig`) — first-class PERSISTED objects, runnable against live traces (`evals/scoreTraces/`).
- Missing id → `MASTR_SCORER_FAILED_TO_CREATE_MISSING_ID`.

> "This is how Mastra closes the calibration loop: define a scorer ... attach it to an agent, and every run is automatically scored and the score attached to the OTel trace."

**Verso relation:** Verso ALREADY HAS the eval wedge — Eval.unit/judge/pass_k/best_of_n/calibrate/predicts/bucket/lift/from_trace; TrajectoryCheck; LLMJudge(examples=); Assertion; VersoSpan + OTel; "prod==eval, captured failure IS a regression test." Mastra's 4-step scorer DSL (preprocess→analyze→generateScore→generateReason) is a near-mirror of Verso's judge/score story. Mastra's **score-attached-to-OTel-trace + scorers-runnable-against-live-traces** = Verso's from_trace + VersoSpan. Strongly validates Verso's eval-first thesis; nothing to steal — Verso's is at parity or richer.

---

## 7. RAG / RELEVANCE / RERANK (KNOWN)

Core ships the relevance interface: `RelevanceScoreProvider { getRelevanceScore(query, text) → number }` (`relevance/relevance-score-provider.ts:2`). Providers: `MastraAgentRelevanceScorer` (LLM scores query↔doc), `CohereRelevanceScorer` (rerank-v3.5), `zeroentropy`.

`@mastra/rag` (separate package, not core):
- Chunk strategies (8): `recursive | character | token | markdown | html | json | latex | semantic-markdown`. Base defaults: **`maxSize=4000`, `overlap=200`**, default char separator `'\n\n'`. Guard: `overlap > maxSize` throws.
- Each strategy can attach an LLM `extract` stage (`title`/`summary`/`questions`/`keywords`/`schema`) enriching chunk metadata.
- **Weighted rerank fusion** (`rerank/index.ts`): default weights `{semantic:0.4, vector:0.4, position:0.2}` (validated to sum to 1 via big.js). Per candidate i of N:
```
semanticScore = scorer.getRelevanceScore(query, text)   // LLM/Cohere, 0..1
vectorScore   = candidate.score                          // original vector similarity
positionScore = 1 - i/N                                  // earlier = higher
finalScore    = 0.4*semantic + 0.4*vector + 0.2*position
```
Optional query-magnitude adjustment: if queryEmbedding supplied, L2 magnitude > 10 → ×1.1, > 5 → ×1.05. Sort desc, truncate to `topK` (default 3).
- Production path: `vector topK → weighted rerank fusion → topK`.

**Verso relation:** Verso ALREADY HAS RRF retrieval + RRF recall. Mastra's weighted score-fusion (semantic+vector+position weights) is a DIFFERENT fusion than RRF — a specific rerank math. The pluggable `RelevanceScoreProvider` rerank interface (Cohere/LLM/zeroentropy) is a small additive abstraction. Chunkers live in a separate package (Verso is right to not bundle a document pipeline). The rerank-provider interface is steal-ADDITIVE-candidate but borderline (Verso's RRF already covers fusion; adding a pluggable rerank provider is additive + byte-identical-when-unused).

---

## 8. PROCESSORS — the guardrail/transform pipeline (KNOWN)

Processors run AROUND the loop, not inside: `inputProcessors` mutate messages before first LLM call; `outputProcessors` mutate streamed chunks before client + before persistence. Methods: `processInputMessages`, `processOutputStream(part)`, `processOutputResult`. Orchestrator = `ProcessorRunner` (`runner.ts:273`).
- **A whole Workflow can BE a processor** (`executeWorkflowAsProcessor`) — a guardrail can itself be a multi-step agentic pipeline.
- A processor returns `{part, blocked, reason, tripwireOptions, processorId}`. `abort()` throws a `TripWire` → `{type:'tripwire', payload:{reason, retry, metadata, processorId}}` and stops. **Tripwire `retry`**: a processor can request a retry of the LLM turn instead of a hard block.

Built-in library (each a class implementing `Processor`, KNOWN):
| Processor | Purpose | Key constants |
|---|---|---|
| `CostGuardProcessor` | abort when cumulative LLM cost > budget | `maxCost` USD (>0); `scope:'run'|'resource'` (default resource); window default **7 days**; `strategy:'block'(TripWire)|'warn'` |
| `ModerationProcessor` | LLM content moderation | OpenAI omni-moderation; `threshold` default **0.5** |
| `PromptInjectionDetector` | detect/neutralize injection | `threshold` default **0.7**; `strategy:'block'|'warn'|'filter'|'rewrite'` (rewrite returns rewritten_content) |
| `PiiDetector` | detect/redact PII | categories + redaction |
| `TokenLimiterProcessor` | cap output tokens | `limit`; `strategy:'truncate'(default)|'abort'`; `countMode:'cumulative'|'per-step'` |
| `StructuredOutputProcessor` | enforce schema on output | Zod, coerce/validate, re-prompt |
| `SystemPromptScrubber` | strip leaked system-prompt text | |
| `SkillsProcessor`/`SkillSearchProcessor` | inject relevant skills (markdown capability files) via semantic search | |
| `ToolSearchProcessor` | dynamically select which tools to expose (semantic match) | "avoids dumping 100 tools into every call" |
| `ResponseCacheProcessor` | cache identical responses | keyed on input |
| `LanguageDetector` | detect/route by language | |
| `UnicodeNormalizer` | NFKC normalize (homoglyph/spoofing defense) before model | |
| `RegexFilter` | block/redact by regex | |
| `ToolCallFilter` | allow/deny specific tool calls | |
| `BatchPartsProcessor` | coalesce stream parts (batch text-deltas) | |
| `WorkspaceInstructions` | auto-load `AGENTS.md` into context | |
| `MessageSelection` | trim/filter history | |
| `PrepareStep` | recompute tools/model/messages per step | the AI-SDK `prepareStep` hook |

Also: `tool-result-reminder.ts` (re-inject tool results the model lost), `trailing-assistant-guard.ts`, `provider-history-compat.ts` (rewrite history across Anthropic/OpenAI tool-call formats), `prefill-error-handler.ts`.

> "the prompt-injection / moderation / PII / cost-guard / unicode-normalizer set is a production safety harness that runs as composable stream transforms with a uniform `TripWire` abort protocol."

**Verso relation:** Verso ALREADY HAS Hooks(pre/post_model, pre/post_tool, on_stop, ask, should_continue), PermissionDecision 4-valued (allow/deny/ask/defer), ask_once, reinforce_objective, trust_tier, prune()/context engineering. Mastra's processor pipeline largely maps to Verso Hooks. BUT several built-ins are genuinely additive safety primitives Verso does not ship as first-class: **CostGuard** (budget-abort with cumulative-per-resource scope + time window), **UnicodeNormalizer** (NFKC homoglyph defense), **ToolSearchProcessor** (semantic tool-subset selection to avoid dumping 100 tools), **tool-result-reminder** (re-inject lost tool results). The `retry`-instead-of-block tripwire (a guardrail re-drives the LLM turn) is a clean pattern. CAUTION: the full 20-processor library + "a Workflow can be a processor" is AVOID-OVERKILL bloat; Verso should cherry-pick, not adopt the pipeline abstraction.

---

## 9. STREAMING — 86 chunk types (KNOWN)

`ChunkType` union = **86 distinct `type:` literals**, each `{type, runId, from:ChunkFrom, payload}`. `ChunkFrom ∈ AGENT|USER|WORKFLOW|...`.
- Lifecycle: `start → step-start → … → step-finish → finish`; `abort`, `error`, `tripwire`.
- Text: `text-start/-delta/-end/text`. Reasoning: `reasoning-start/-delta/-end/-signature`, `redacted-reasoning`.
- Tools: `tool-call-input-streaming-start/-delta/-end`, `tool-call`, `tool-result`, `tool-error`. **HITL:** `tool-call-approval`, `tool-call-suspended`, `tool-execution-approval/-suspended/-abort/-end`, `tool-output`.
- Agent-exec: `agent-execution-start/-end/-abort/-approval/-suspended`.
- Background tasks: `background-task-started/-running/-progress/-output/-completed/-failed/-cancelled/-suspended/-resumed`.
- Objects: `object`, `object-result`, `network-object`, `network-object-result`.
- Routing/network: `routing-agent-start/-end/...`, `network-execution-event-step-finish/-finish`, `network-validation-start/-end`.

`MastraModelOutput` re-shapes chunks to AI-SDK `fullStream`/`textStream` and the AI-SDK **UI Message Stream** for `useChat` clients.

**Verso relation:** Verso ALREADY HAS typed true-delta events (message/reasoning/tool.start/tool.result/done) + SSE. Mastra's 86 chunk types = AVOID-OVERKILL (Verso ships the load-bearing subset). The HITL/background-task chunk families are richer, but they exist because Mastra's everything-is-a-graph generates that surface area; Verso's leaner event set is on-thesis.

---

## 10. RuntimeContext / DI (KNOWN)

`RequestContext` (DI container, `di/index.ts`) = typed key→value map scoped to one request, threaded through the loop and into every tool's `execute` options. Methods: `get/set/has/delete` + iteration, **per-key type inference** (`get('age')` returns `number` not a union), `clone()` for sub-runs. Well-known keys: `MASTRA_RESOURCE_ID_KEY`, `MASTRA_THREAD_ID_KEY`, `MASTRA_VERSIONS_KEY`, internal `__mastra_requireToolApproval`. "a tool reads request-scoped config (tenant id, feature flags, user tier) from requestContext instead of closing over globals."

**Verso relation:** Verso ALREADY HAS `ctx.deps` typed injection. Mastra's RequestContext = Verso's ctx.deps. The per-key type-inference is a TS-only ergonomic (Python has typed dataclasses / TypedDict). verso-already-has.

---

## 11. MULTI-AGENT / NETWORK (KNOWN)

`loop/network/index.ts` (2699 L) = agent network/routing. A routing agent decides which sub-agent/workflow/tool to invoke next. Sub-agents via `agents:` option, streamed back as `agent-execution-*`/`tool-output` chunks. **agents-as-tools**: a sub-agent registered as a tool runs its own full loop. **A2A**: `a2a/` = Agent-to-Agent protocol for cross-framework calls. Delegation can `ctx.bail()` to stop the parent loop after current iteration.

**Verso relation:** AVOID-OVERKILL — Verso NON-GOALS explicitly include "no router/planner cult, no orchestrator-as-primitive, no learned routers." A 2699-line routing-agent network is exactly the orchestrator-as-primitive Verso refuses. agents-as-tools is achievable in Verso via @tool wrapping an agent call (additive, not a primitive). neutral-context/avoid-overkill.

---

## 12. ERROR / BACKGROUND TASKS (KNOWN)

- All errors = `MastraError{id, domain (LLM|MASTRA_WORKFLOW|SCORER|...), category (USER|SYSTEM|...), text}`, tracked via `logger.trackException`. Examples: `LOOP_MODELS_EMPTY`, `WORKFLOW_EXECUTE_EMPTY_GRAPH`, `ToolNotFoundError`.
- `TripWire` = guardrail-abort signal (not an error), supports `retry`.
- **Background tasks**: a tool can `createBackgroundTask` → runs async, agent loop continues, `backgroundTaskCheckStep` polls/awaits, emits `background-task-progress/-completed/-failed` chunks. `resolveBackgroundConfig` sets poll cadence + wait policy. "how long-running tools (deploys, batch jobs) don't block the conversation."

**Verso relation:** Verso ALREADY HAS error taxonomy (typed errors, auth/content fail fast), RetryPolicy. Mastra's structured `{id, domain, category}` error taxonomy is parity. **Background tasks** (fire-and-poll long-running tool that doesn't block the loop) is a genuinely different primitive Verso does not ship — but it's complex (poll cadence, wait policy, background-task chunk family) and arguably tied to the durable/streaming machinery. steal-additive-candidate but borderline-overkill; flag honestly.

---

## STORAGE SCHEMA (KNOWN, for completeness)
4 tables (`storage/constants.ts`): `mastra_workflow_snapshot` (snapshot = one jsonb blob keyed by workflow_name+run_id), `mastra_threads`, `mastra_messages`, `mastra_resources` (`workingMemory` text column = cross-thread persistence). Adapters libsql/pg/upstash implement same logical tables.

---

## BOTTOM LINE FOR VERSO

Mastra is the cleanest possible counter-example to Verso's thesis: it is the framework that **forced the graph all the way down** — the agent loop, HITL, durability, and resume are ALL one interpreted step-graph engine, and removing the engine kills the agent. This VALIDATES Verso's "we don't force the graph" counter-position by showing exactly what the alternative costs (4570-line workflow.ts, 86 chunk types, 10-state enum, dual-array serialization, `fn.toString()` predicate persistence, two separate execution engines). Most Mastra "primitives" Verso already ships more leanly via the tactical→durable seam. The few genuinely additive, on-thesis, byte-identical-when-unused candidates: CostGuard budget-abort, UnicodeNormalizer, ToolSearchProcessor (semantic tool subsetting), embedding LRU cache, retry-instead-of-block tripwire, pluggable rerank-provider interface, tool payload-transform (redact-on-persist-vs-stream).
