# Vercel AI SDK (`ai`) — Raw Extraction (DX / structured-output ergonomics)

Source: `/Users/seventyleven/Desktop/researchfms/teardowns/VERCEL_AI_SDK.md` (424 lines, RE teardown of `vercel/ai` monorepo, clone 2026-05-30, Tier-1A source-first, `file:line` cited). Lens: TIGHT DX primitives + structured-output ergonomics worth mirroring in Verso's API shape. Labels carried from teardown: **KNOWN** = read in source; **INFERRED**; **DESIGNED**.

---

## 1. The two load-bearing primitives (KNOWN)

The teardown thesis: the SDK's two load-bearing primitives are (1) **the `generateText`/`streamText` multi-step tool loop** with a pluggable `stopWhen`/`prepareStep` contract, and (2) **the `LanguageModelV2` provider spec** — a normalized `doGenerate`/`doStream` interface with standardized content parts that lets one loop drive 30+ providers. Third primitive: the client-facing **UI Message Stream** (SSE data-part protocol consumed by `useChat`).

Loop file sizes (KNOWN, `wc -l`): `stream-text.ts` **2426**, `generate-text.ts` **1639**, `stream-language-model-call.ts` **833**, `stream-text-result.ts` **593**, `output.ts` **590**, `step-result.ts` **417**.

---

## 2. The step loop & stop policy — declarative `stopWhen` (KNOWN)

- Default `stopWhen = isStepCount(1)` (`generate-text.ts:228`) — **by default a single LLM call, no agentic loop**; you opt into multi-step by passing `stopWhen: stepCountIs(N)` or a custom condition.
- `stopWhen: Arrayable<StopCondition>`; each `StopCondition({steps}) → boolean | Promise<boolean>` (`generate-text.ts:281`).
- Built-ins: `isStepCount(n)`/`stepCountIs(n)` (stop after N steps), `hasToolCall(name)` (stop once a specific tool was called).
- `isStopConditionMet({stopConditions, steps})` returns true if **ANY** condition is true (`.some()`, `generate-text.ts:96,1180`) → array = OR semantics.
- Replaces old `maxSteps: N` (which still maps to `stepCountIs(N)`).
- **Loop-continue rule (verbatim `generate-text.ts:1171-1181`):** continue iff the last step produced client tool calls AND every client tool call has a result/denial (`clientToolOutputs.length + deniedToolApprovalResponses.length === clientToolCalls.length`) OR deferred provider results pending, AND `stopWhen` hasn't fired. "If the model emitted final text → stop."
- Post-loop flatten: `toolCalls = steps.flatMap(s => s.toolCalls)`, `totalUsage = steps.reduce(add,…)`, `response.messages = [...initialResponseMessages, ...steps.flatMap(s => s.response.messages)]` (`:1185-1244`).

DX taste: stop is **declarative + composable** (array of predicates over `steps[]`), not an imperative `max_steps` int.

---

## 3. `prepareStep` — per-step control hook (KNOWN)

`prepareStep({model, steps, stepNumber, instructions, messages, responseMessages, runtimeContext, toolsContext})` (`generate-text.ts:677`, type `prepare-step.ts:172`) can return overrides for **this step only**: `{model, instructions/system, messages, activeTools, toolChoice, providerOptions, runtimeContext, toolsContext, experimental_sandbox}`. Use cases (verbatim): switch to a cheaper model on later steps, force `toolChoice:'required'` on step 0, shrink `activeTools` as the task narrows, compact `messages` (`prune-messages.ts`). "It is the single most powerful agentic hook."

---

## 4. Structured output ergonomics — `generateObject` / `streamObject` (KNOWN, the DX core)

`generateObject({model, schema?, output?, mode?, prompt})` (`generate-object/generate-object.ts`).

**Output strategies** (`getOutputStrategy({output, schema, enumValues})`, `output-strategy.ts:392-410` — returns 1 of 4 strategy objects, each exposing `jsonSchema`, `validatePartialResult`, `validateFinalResult`, `createElementStream`):
1. `output: 'object'` (default when schema is an object) — single object matching `schema`. (`:103-131`)
2. `output: 'array'` — **wraps the array in `{elements:[...]}`** because "most LLMs will not be able to generate an array directly" (verbatim `:139-141`). JSON Schema emits `{type:'object', properties:{elements:{type:'array', items:<itemSchema>}}, required:['elements'], additionalProperties:false}` (draft-07). Streams element-by-element: the last element is suppressed unless `isFinalDelta` (`:185-187`) because a mid-stream trailing element is incomplete; emits only NEW elements since `publishedElementCount`, prefixing `[`, joining `,`, closing `]` on final (`:197-216`). (`:133-297`)
3. `output: 'enum'` (default when `InferSchema<SCHEMA> extends string`) — wraps in `{result: string}`. Streaming trick: `possibleEnumValues = enumValues.filter(v => v.startsWith(partial.result))` — **prefix-filters the enum as tokens arrive**; commits when exactly one candidate remains (`possibleEnumValues.length > 1 ? result : possibleEnumValues[0]`, `:358-377`). No element stream in enum mode (throws). (`:299-389`)
4. `output: 'no-schema'` — `jsonSchema: undefined`; free-form JSON, validators pass through. (`:65-101`)

**Modes** `mode: 'auto'|'tool'|'json'` — `'json'` sets provider `responseFormat:{type:'json', schema}`; `'tool'` defines a single synthetic tool + forces `toolChoice` to it; `'auto'` picks per model capability.
- **`[CORRECTION 2026-05-30]`**: current `generate-object.ts` **always uses provider native JSON response format** — `model.doGenerate({responseFormat:{type:'json', schema: jsonSchema, name: schemaName, description: schemaDescription}, ...})` (`:355-368`). The synthetic-forced-tool path is no longer the dispatch; relies on `LanguageModelV2`'s `responseFormat:'json'` (native structured output where available, prompt-injected JSON via `inject-json-instruction.ts` where not). "mode" effectively collapsed to JSON-response-format + per-strategy validation. KNOWN.

**`experimental_output` on `generateText`/`streamText`** (`output.ts`, 590 L) — a single agent call returns both prose+tools AND a typed object.

`streamObject` streams a **deep-partial** of the object via the strategy's `validatePartialResult` on each `parsePartialJson` of accumulated text (the `partialObjectStream`); `elementStream` (array mode) yields completed elements.

---

## 5. Schema repair — exact one-shot retry (KNOWN, ergonomic)

`parseAndValidateObjectResultWithRepair` (`parse-and-validate-object-result.ts:77-111`):
```
try { return parseAndValidateObjectResult(text) }       // safeParseJSON → validateFinalResult
catch (error) {
  if (repairText != null && NoObjectGeneratedError.isInstance(error)
      && (JSONParseError.isInstance(error.cause) || TypeValidationError.isInstance(error.cause))) {
    const repaired = await repairText({ text, error: error.cause })   // user-supplied
    if (repaired === null) throw error
    return parseAndValidateObjectResult(repaired)          // exactly ONE re-parse, no loop
  }
  throw error
}
```
`experimental_repairText` fires **only** on JSON-parse OR type-validation failure (not content-filter), gets `{text, error}`, returns repaired text or `null`, SDK re-runs the same parse+validate ONCE. Failure error: `NoObjectGeneratedError{message, cause, text, response, usage, finishReason}` (`:33-40,53-60`) — **carries raw `text`** for post-mortem. KNOWN.

DX note: this is deliberately a ONE-SHOT repair, not a loop — contrast Verso's in-loop reask which re-drives the whole model call.

---

## 6. `tool()` — the tool DX surface (KNOWN)

`tool({inputSchema, outputSchema?, execute?, …})` (`provider-utils/src/types/tool.ts`):
- `inputSchema: FlexibleSchema<INPUT>` (`:93`) — **Zod, Valibot, or raw JSON Schema** (`jsonSchema(...)`). Converted to provider JSON Schema by `prepareTools`.
- `outputSchema?: FlexibleSchema<OUTPUT>` (`:30/47`) — optional; if absent inferred from `execute`'s return; **required when no `execute`** (a client-side tool whose result the host supplies, `:45-49`).
- `execute?: (input, options) → OUTPUT | Promise<OUTPUT> | AsyncIterable<...>` (`:39`) — `options = {toolCallId, messages, abortSignal, experimental_context (toolsContext)}`. **May stream partial outputs.**
- **lifecycle hooks fire in order** (KNOWN): `onInputStart(opts)` (`:118`) when arg-streaming begins → `onInputDelta({inputTextDelta,...})` (`:126`) per arg-token → `onInputAvailable({input,...})` (`:136`) when full input parsed (**fires even if no `execute`** — start UI before exec) → `execute` → `toModelOutput`.
- **`toModelOutput?: ({toolCallId, input, output}) → LanguageModelV2ToolResultOutput`** (`:149-168`) — the **result-shaping hook**: maps raw tool output to what the MODEL sees next turn (e.g. summarize a 50KB result to a sentence); if absent result is sent as JSON. Runs inside `convertToModelMessages`, so you must pass the SAME `tools` ToolSet to both `convertToModelMessages` and `streamText` (verbatim warning `:147`). KNOWN.
- `type?: undefined|'function'` (client-executed) vs `'provider'` (`providerExecuted:true`, optional `supportsDeferredResults` `:306`).
- `dynamicTool(...)` (`:375-378`) — `{...tool, type:'dynamic'}`; runtime-schema tool, types fall back to `unknown`.
- **`[CORRECTION 2026-05-30]`**: per-tool `needsApproval` is **DEPRECATED** (`:103-106`: "Tool approval is handled on a `generateText`/`streamText` level now") — approval moved to loop level. KNOWN.

`ToolSet = Record<string, Tool>`. `toolsContext` (a.k.a. `experimental_context`) is a typed DI value threaded into every `execute`; mutate only via `prepareStep` (`generate-text.ts:309`).

Invalid model tool calls → `{type:'tool-error', dynamic:true}` outputs so the model can self-correct (`parse-tool-call.ts`, `generate-text.ts:985`).

---

## 7. Tool approval / HITL — loop-level (KNOWN)

`generate-text.ts:891-1003` + `tool-approval-configuration.ts`. A tool declares `needsApproval` OR the call passes a `toolApproval` config that **takes precedence** (`:325`). On needs-approval: SDK emits a `tool-approval-request` part with generated `approvalId` (`:926,938`) instead of executing. Host responds `tool-approval-response {approvalId, approved, reason}`. Next call: `collectToolApprovals` matches responses→calls, executes approved; **denied** calls push a `tool-error` output ("execution denied") so the model sees the denial (`:615-628`). `deniedToolApprovalResponses` count toward loop-continue accounting (`:1001`).

---

## 8. `LanguageModelV2` provider spec (KNOWN, verbatim `language-model-v2.ts:14`)

```ts
type LanguageModelV2 = {
  readonly specificationVersion: 'v2';
  readonly provider: string;          // e.g. 'openai.chat'
  readonly modelId: string;
  supportedUrls: Record<string, RegExp[]> | PromiseLike<…>;   // URLs model fetches natively
  doGenerate(options): PromiseLike<{
    content: Array<LanguageModelV2Content>;   // ORDERED parts
    finishReason; usage; providerMetadata?; request?; response?; warnings;
  }>;
  doStream(options): PromiseLike<{ stream: ReadableStream<LanguageModelV2StreamPart>; ... }>;
};
```
- `"do"` prefix is deliberate ("prevent accidental direct usage by the user", `:49`) — users call `generateText`, not `model.doGenerate`.
- **Content parts** (`language-model-v2-content.ts:9`): `Text | Reasoning | File | Source | ToolCall | ToolResult` — ordered union is the V2 innovation (V1 returned `{text, toolCalls, reasoning}` as separate fields; V2 preserves interleave/order).
- **`finishReason`** (7-value, normalized `{unified, raw}`): `stop | length | content-filter | tool-calls | error | other | unknown`. Loop reasons over `unified`; provider keeps `raw`.
- **Stream parts** (`language-model-v2-stream-part.ts:11`): `stream-start`, `text-start/delta/end`, `reasoning-start/delta/end`, `tool-input-start/delta/end`, `tool-call`, `tool-result`, `file`, `source`, `response-metadata`, `finish` (usage+finishReason), `raw`, `error`.
- `LanguageModelV2CallOptions`: `{prompt, tools, toolChoice, maxOutputTokens, temperature, topP, topK, frequencyPenalty, presencePenalty, stopSequences, seed, responseFormat (text|json+schema), providerOptions, headers, abortSignal}`. **`responseFormat:{type:'json', schema}`** = how structured output is requested at provider level.
- **Middleware**: `wrapLanguageModel({model, middleware})` intercepts `doGenerate`/`doStream`. Built-ins: `extractReasoningMiddleware` (parse `<think>` tags), `simulateStreamingMiddleware`, `defaultSettingsMiddleware`, logging/caching. RAG-injection/caching/guardrails wrap any model uniformly.

---

## 9. The Agent class — thin config wrapper → `ToolLoopAgent` (KNOWN)

§5 original: `Agent` = a frozen `generateText`/`streamText` settings bundle `{model, system/instructions, tools, stopWhen, prepareStep,…}` exposing `.generate(prompt)`/`.stream(prompt)`. **No new loop. Intentionally minimal** (contrast Mastra's full workflow engine).

**`[CORRECTION 2026-05-30]`**: current impl is **`ToolLoopAgent`** (`agent/tool-loop-agent.ts:38`, 288 L), exported as **`Experimental_Agent`**, settings `Experimental_AgentSettings`. `agent.ts` holds only the `Agent` interface (`version:'agent-v1'`).
- `generate({prompt, messages, options})` (`:176`) and `stream({...})` (`:233`) call `prepareCall(...)` then delegate to `generateText`/`streamText`.
- `prepareCall` (`:79-150`): (1) if `callOptionsSchema` set, `validateTypes(options.options, schema)` — **typed per-call runtime options**; (2) strip settings-level callbacks; (3) `baseCallArgs = {...settings, stopWhen: settings.stopWhen ?? isStepCount(20), ...options}` — **default stop is 20 steps** (`:125`) vs raw `generateText`'s `stepCountIs(1)`; (4) run optional `prepareCall` hook; (5) split out `instructions/messages/prompt/runtimeContext`. Merged lifecycle callbacks: `experimental_onStart`, `onToolExecutionStart/End`, `onStepFinish`, `onEnd`.

---

## 10. Context / memory — deliberately memory-less (KNOWN)

"The AI SDK is deliberately memory-less at the core — it has no thread/resource store." Context = the `messages` array you pass; persistence is the host's job. Provides: `convertToModelMessages(uiMessages)`, `prune-messages.ts` (drop old messages to fit a budget, used via `prepareStep`, 167 L), `convertToLanguageModelPrompt` (assemble + download files model can't fetch via `supportedUrls`). Prompt caching is provider-level via `providerOptions` (Anthropic `cacheControl`) passed straight through. **Ships NO system prompts** — prompt-agnostic infra (`§11`). Only SDK-authored strings: tool-denial messages + synthetic-tool descriptions.

---

## 11. Registry / gateway — string routing (KNOWN)

- `createProviderRegistry(providers, {separator=':'})` (`provider-registry.ts:132-199`) resolves `'<providerId><separator><modelId>'`; **default separator `':'`** (`:143`) → `'openai:gpt-4o'`. `languageModel(id)` splits, looks up provider, calls `provider.languageModel(modelId)`; unknown → `NoSuchModelError`. Same for `textEmbeddingModel`, `imageModel`, `speechModel`, `videoModel`.
- `customProvider({languageModels, textEmbeddingModels, imageModels, fallbackProvider})` (`custom-provider.ts:52`) — consults supplied record first, falls through to `fallbackProvider`, else `NoSuchModelError`. Alias models (`'fast' → openai('gpt-4o-mini')`) or pin provider options per id.
- **AI Gateway** (`packages/gateway`) — `gateway-language-model.ts` etc IS a `LanguageModelV2`, so `createProviderRegistry({gateway})` + `'gateway:anthropic/claude-...'` routes through ONE key; the loop doesn't change. `resolveLanguageModel(id|model)` accepts a string or a `LanguageModelV2`.

---

## 12. UI Message Stream — 27-chunk SSE protocol + client reconstruction (KNOWN)

Two output protocols: `fullStream` (SDK-internal `TextStreamPart` union, server-side) and the **UI Message Stream** (client protocol consumed by `useChat`, served by `toUIMessageStreamResponse()`, SSE of JSON data parts). 27 chunk types (`ui-message-chunks.ts`): start/finish/abort/error, start-step/finish-step, text-start/delta/end, reasoning-start/delta/end/file, source-url/source-document, file, tool-input-start/delta/available/error, tool-output-available/error/denied, tool-approval-request/response, message-metadata, **custom** (`data-*` parts).
- Wire: `data: {"type":"text-delta","id":"...","delta":"..."}\n\n`, terminated `data: [DONE]`.
- **`custom`/`data-*` parts** stream arbitrary structured data mid-generation (status, sources, generative-UI props); **`transient:true` data parts are streamed but NOT persisted** into the message.
- Client reconstruction (`process-ui-message-stream.ts`): `StreamingUIMessageState {message, activeTextParts, activeReasoningParts, partialToolCalls}` replays parts into a mutable message tree with **strict start/delta/end ordering** — `text-delta` errors if no prior `text-start` ("a dropped `text-start` is a hard error, not a silent no-op"). Tool parts = **4-state machine** keyed by `toolCallId`: `input-streaming → input-available → output-available | output-error`.
- `onFinish({messages})` runs with assembled `UIMessage[]` so host persists.

---

## 13. `streamText` internals — overlapped tool exec + dual timeouts (KNOWN)

- `streamText` returns a **stitchable stream** (`createStitchableStream`, `stream-text.ts:1287`) — each step's model stream is `addStream`'d so the consumer sees one continuous `fullStream` across multiple LLM calls.
- `streamStep` (`:1560`) has **two timeouts**: per-step (`stepTimeoutMs`, `:1568`) AND **per-chunk (`chunkTimeoutMs`, reset on every chunk via `resetChunkTimeout`, `:1578`)** — if a provider stalls mid-stream the chunk timeout aborts. More granular than `generateText` (step timeout only).
- `runToolsTransformation` / `execute-tools-from-stream.ts` (219 L): on `tool-input-end` it **kicks off `tool.execute` IMMEDIATELY** — overlapping tool exec with the rest of the model stream — then injects `tool-result`.
- `smooth-stream.ts` (163 L) optional transform: `chunking: 'word'` (default, regex `/\S+\s+/m`) `| 'line' (/\n+/m) | RegExp | Intl.Segmenter (CJK) | ChunkDetector`; `delayInMs = 10` default.
- `stream-text-result.ts` surface: `.textStream`, `.fullStream`, `.toUIMessageStreamResponse()`, `.toTextStreamResponse()`, `.consumeStream()` (drain without reading, fire-and-forget persist), promise accessors `.text/.steps/.usage/.finishReason/.toolCalls/.response`.

---

## 14. Modality call shapes (KNOWN) — all `doX → normalized output`

- `embed({model, value})` → `doEmbed({values:[value]}) → {embeddings:[vec], usage}`. `embedMany({model, values, maxParallelCalls=Infinity, maxRetries})` reads `model.maxEmbeddingsPerCall`; `null|Infinity` → one call, else `splitArray(values, maxEmbeddingsPerCall)` batches, concurrency-capped at `maxParallelCalls`, concatenates preserving input order.
- `generateImage({model, prompt, n=1, maxImagesPerCall, size:'{w}x{h}', aspectRatio:'{w}:{h}', seed, providerOptions})` → batches `doGenerate` until `n`, returns `{images: DataContent[]}`.
- `generateSpeech`, `transcribe → {text, segments, language}`, `generateVideo`, `rerank({model, query, documents, topK})`. All string-routable through the registry/gateway.

---

## 15. Replica blueprint (DESIGNED) + provider-is-3-files proof (KNOWN)

The whole agentic machinery runs unchanged once a provider is written. A provider package = `{convert-to-X-messages, X-language-model.ts (doGenerate/doStream), map-X-finish-reason}` (~3 files). OpenAI `doStream` (`openai-chat-language-model.ts:427`) opens the OpenAI SSE and translates each native chunk into the spec's stream parts (verbatim `:478-595`). Monorepo ships ~30 provider packages. "That is what a real primitive looks like."

---

## DX-taste takeaways for Verso (analysis)

1. **Declarative `stopWhen` array (OR of predicates over `steps[]`)** is a cleaner stop API than a bare int; Verso has stuck/doom-loop + max_steps_policy + done() but stop-condition composition is the notable DX shape.
2. **`prepareStep` per-step override hook** (model/tools/toolChoice/messages for THIS step) — Verso has `agent.override()` + per-call `model=` swap + prune(); a per-step recompute callback is the cohesive shape.
3. **4 output strategies × streaming validators** (object/array/enum/no-schema) with concrete streaming math (array `{elements}` wrapper, enum prefix-filter) — Verso has `output_type=` + in-loop reask + validators; the enum prefix-filter and array element-stream are specific ergonomics.
4. **`toModelOutput` result-shaping hook** — map raw tool output to what the model sees next turn (summarize 50KB→sentence). Verso prunes/masks old tool outputs but a per-tool result-projection hook at emit time is distinct.
5. **One-shot `repairText({text, error})`** — narrow (only JSON-parse / type-validation failure), returns repaired text or null, re-parses ONCE. Verso's Retry(feedback) re-drives the model; this is a cheaper text-only repair before re-driving.
6. **`transient:true` data parts** — stream-but-don't-persist. Verso has typed true-delta events; transient marker is a small additive streaming nicety.
