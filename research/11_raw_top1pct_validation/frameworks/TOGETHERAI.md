# TogetherAI — Raw Extraction (cost / routing / structured-output / model-serving angle)

Source: `/Users/seventyleven/Desktop/researchfms/teardowns/TOGETHERAI.md` (1791 lines, 101KB).
Extraction lens: model serving + routing, JSON-mode/structured-output/function-calling API shape, agents/inference surface, batching, cost levers. Mapped to Verso's model layer + FailoverModel.
Tag convention: KNOWN = stated in source (often "KNOWN from SDK/pricing page"); INFERRED = source's own inference.

---

## 1. What Together IS (one line)
KNOWN: "Multi-product NVIDIA-GPU-based AI cloud" — custom inference engine + custom kernels (FlashAttention-3/4, megakernel, ATLAS speculative decoding) + fine-tuning (SFT/DPO/LoRA/full/multimodal) + raw GPU cluster rental (H100/H200/B200/L40/RTX-6000) + container deploy ("jigs") + sandboxes + image/video/audio gen + rerankers + embeddings. "They are explicitly *not* a chip company — they sell software that extracts more tokens-per-second from NVIDIA silicon than vLLM does."

API surface: "roughly 50+ distinct endpoints — an order of magnitude bigger than Groq's surface and 5× SambaNova's." Default base URL `https://api.together.ai/v1`. OpenAI-compatible. Stainless-generated Python client.

---

## 2. The OpenAI-compatible model-serving surface (Verso model-layer relevance)
KNOWN endpoints (from resource tree):
```
chat.completions.create   → POST /v1/chat/completions
completions.create        → POST /v1/completions
embeddings.create         → POST /v1/embeddings
rerank.create             → POST /v1/rerank
batches.create/list/retrieve → /v1/batches
models.list/retrieve/upload  → /v1/models
endpoints.create/.../update  → /v1/endpoints (dedicated)
fine_tuning.estimate_price(...) → cost calculator PRE-job-submit
code_interpreter.execute(...) → /v1/code-interpreter
evals.create/list/status     → /v1/evals
```
KNOWN client constants: `MAX_SESSION_LIFETIME_SECS = 180`, `MAX_CONNECTION_RETRIES = 2`, `MAX_RETRIES = 2`, `INITIAL_RETRY_DELAY = 0.5`, `MAX_RETRY_DELAY = 8.0`. Default timeout 600s.

VERSO MAP: Together is "ANY OpenAI-compatible endpoint via base_url" — Verso ALREADY reaches Together via `init_model("openai:...", base_url="https://api.together.ai/v1")`. The retry constants (2 retries, 0.5s→8.0s backoff) match Verso's RetryPolicy shape already.

---

## 3. Chat Completions full parameter surface (structured output + cost knobs)
KNOWN verbatim from `completion_create_params.py`:
```
response_format       ResponseFormat   # text | json_schema | json_object  ← STRUCTURED OUTPUT
tool_choice           ToolChoice
tools                 list[ToolsParam]
function_call         FunctionCall     # legacy; use tool_choice
reasoning             Reasoning        # {"enabled": bool}
reasoning_effort      Literal["low","medium","high"]
safety_model          str              # chained moderation model AFTER generation
compliance            Literal["hipaa"] # server-side routing flag
context_length_exceeded_behavior  Literal["truncate","error"]
chat_template_kwargs  object           # raw kwargs into HF apply_chat_template
logprobs              int              # 0..20 top-k logprobs
min_p / top_k / repetition_penalty    # vLLM-native samplers
echo / seed / n / logit_bias
```

### 3a. Structured output (the JSON-mode fast-path)
KNOWN: `response_format: text | json_schema | json_object`. This is the WHOLE structured-output API — there is NO dedicated grammar/guided-decoding section in the teardown; structured output is a single provider-native field. (INFERRED by me: json_schema implies server-side constrained/guided decoding, but the teardown does not name a grammar engine.)

VERSO MAP: Verso ships `output_type=` with in-loop reask (append ValidationError + re-drive) — a PROVIDER-AGNOSTIC strategy that works on any model. Together's `response_format=json_schema` is a PROVIDER-NATIVE fast-path: when the underlying endpoint supports it, you can pass the schema down and skip a reask round-trip. This is the "provider-native structured-output fast-path" the task asks about. STEAL-ADDITIVE candidate (byte-identical when unused: only engaged when the model adapter advertises native json_schema support).

### 3b. Together-unique params
- `safety_model: str` — KNOWN. "single API call chains generation through a moderation model. Server-side composition that users don't have to build." Examples: `Llama-Guard-3-8B`.
- `compliance: "hipaa"` — KNOWN. "server-side routing flag; setting it sends the request to HIPAA-compliant pods." NOVEL: "Per-request HIPAA routing... Other providers handle compliance via account-level agreements, not per-request."
- `context_length_exceeded_behavior: "truncate"|"error"` — KNOWN. "Lets the user choose what happens on context overflow; most providers just 400 on overflow."
- `chat_template_kwargs` — KNOWN. Example `{"enable_thinking": True}` to toggle reasoning on DeepSeek.
- Backend fingerprint: "min_p, top_k, repetition_penalty... match vLLM's SamplingParams exactly" — vLLM-derived engine.

---

## 4. COST LEVERS (the core of this extraction)

### 4a. Precision tiers = cheap-model-on-easy-steps, same architecture
KNOWN: Together deploys the SAME model at 3 precisions in parallel, customer chooses:
| Tier | Precision | Cost example |
|------|-----------|--------------|
| Reference | FP16/BF16 | Highest |
| Turbo | FP8 (nvfp4/mxfp4) | $0.88 for Llama-3 70B Turbo |
| Lite | INT4 | $0.10/M for 8B Lite |
KNOWN: "they deploy the *same* model architecture at *different* precisions in parallel, and let the customer choose. This isn't free — they have to maintain 3 variant deployments per model."

VERSO MAP: This is a PROVIDER-SIDE version of "cheap-model-on-easy-steps." Verso already does per-call model swap (`model=` per call + `agent.override()`). The Together insight is that the cheap option can be the SAME model at lower precision — selectable by passing a different model string (e.g. `...-Turbo` vs `...-Lite`). No new Verso primitive needed; it's just naming convention on the model string Verso already passes through.

### 4b. Batch API — 50% discount
KNOWN: "Batches | `batches` | Bulk inference at 50% discount." "50% discount on most models — non-time-sensitive workloads at half the cost." `batches.create()/list()/retrieve() → /v1/batches`. `files` endpoint stores batch inputs (JSONL).

VERSO MAP: A batch/offline-inference path is NOT in Verso's shipped primitives (Verso is an online ReAct loop). Batching is a throughput/cost mechanism for non-interactive bulk eval/labeling. POSSIBLE steal for the EVALS wedge (run `Eval.unit` over a large dataset at 50% cost via provider batch endpoint) — but it is provider-specific and async-poll-shaped (600s timeout), which cuts against the lean online-loop thesis. Tagging avoid-overkill-leaning / neutral: a batch adapter is additive but it's a different execution model, not the loop.

### 4c. Serverless per-token pricing (May 2026, KNOWN verbatim)
| Model | Input $/M | Output $/M |
|-------|-----------|-----------|
| GLM-5.1 | $1.40 | $4.40 |
| Qwen3.6-Plus | $0.50 | $3.00 |
| Kimi K2.6 | $1.20 | $4.50 |
| DeepSeek V4 Pro | $2.10 | $4.40 |
| Llama 3.3 70B | $0.88 | $0.88 |
| Qwen3.5 9B | $0.10 | $0.15 |
| Gemma 4 31B | $0.20 | $0.50 |
Embeddings: multilingual-e5-large-instruct $0.02/M. Whisper Large v3 $0.0015/audio-min.
COST SPREAD: cheapest token (Qwen3.5 9B in @ $0.10/M) is ~21× cheaper than priciest (DeepSeek V4 Pro in @ $2.10/M) — quantifies the lever of routing easy steps to a small model.

### 4d. fine_tuning.estimate_price — cost calculator PRE-submit
KNOWN: `fine_tuning.estimate_price(...) → cost calculator pre-job-submit`. A dry-run cost estimate before committing a job.
VERSO MAP: Verso has no cost-estimation primitive. INFERRED-relevance: a pre-flight cost/token estimate for an agent run is on-thesis-adjacent (evals/observability) but Together's is fine-tune-specific. Neutral.

### 4e. Dedicated-endpoint cost knobs
KNOWN from `endpoint_create_params`:
- `disable_speculative_decoding: bool` — "Together enables speculative decoding by default; users can opt out per endpoint. (Why opt out? Spec decoding can hurt latency on small-input requests.)"
- `inactive_timeout: int|None` — "endpoints can auto-stop after N minutes idle, saving cost. Set to 0/null for always-on." (scale-to-zero)
- `autoscaling {min_replicas, max_replicas}`.
These are infra-level (Verso non-goal: not the kernel/serving infra). Neutral-context only.

---

## 5. ATLAS — adaptive speculative decoding (serving moat, NOT a Verso primitive)
KNOWN: "ATLAS (AdapTive-LeArning Speculator System)... static speculative-decoding draft models become stale as the production token distribution drifts. ATLAS continuously trains the draft model on live traffic." Draft model proposes 2–8 tokens. Published claim: "up to **400% inference speedup**" (source flags as upper bound; real steady-state 2–3×). "continuous online retraining — the adaptive speculator is updated during production runtime, not just at deploy time."

VERSO MAP: Pure serving-layer infra. Verso is "not the model/kernel." Neutral-context; explains WHY a provider-native endpoint can be cheaper/faster than self-host (justifies routing to provider-native fast-paths).

---

## 6. Megakernel & engine speedup (context)
KNOWN: megakernel "compiles an entire transformer forward pass into a single CUDA kernel... Standard vLLM launches ~64+ kernels per token... up to 3.6× faster end-to-end." Engine claims 2.8–4.5× over vanilla vLLM. Serverless gives "3–4× faster throughput on the same hardware" vs raw rental. Neutral-context (serving infra).

---

## 7. Agents / inference surface
KNOWN: `code_interpreter.execute(...)` — "Sandboxed code execution (for agent tool use)", billed $0.0446/vCPU-hr + $0.0149/GiB-RAM-hr, "designed to be a tool that agents can call. Comparable to Modal/E2B sandboxes." `evals` endpoint exists — "rare among inference providers — most don't ship an eval framework as an API."
VERSO MAP: code_interpreter is a sandboxed-tool-as-a-service — Verso's @tool + quarantine trust-tier covers the agent side; the sandbox itself is infra. The `evals` API is interesting context (a provider shipping evals validates Verso's evals-as-wedge thesis) but it's a hosted product, not a primitive to copy. Neutral.

---

## 8. Error format / retry shape (FailoverModel relevance)
KNOWN error JSON (OpenAI-shaped):
```json
{"id":"oj4j...-2kFH...-<cf-ray>","error":{"message":"Invalid API key provided...","type":"invalid_request_error","param":null,"code":"invalid_api_key"}}
```
Cloudflare-fronted (`server: cloudflare`). Composite request id correlates CF ray + backend trace.
VERSO MAP: Standard OpenAI error taxonomy — Verso's error taxonomy + typed errors (auth fails fast) already handle `invalid_api_key`-type codes. FailoverModel can already fail over from a Together base_url to another. verso-already-has.

---

## 9. Net cost-effectiveness primitives a lean framework should expose (synthesis)
1. Provider-native structured-output fast-path: pass `response_format=json_schema` down when the adapter supports it; fall back to Verso's reask loop otherwise. STEAL-ADDITIVE (byte-identical when unused).
2. Cheap-model-on-easy-steps: already covered by per-call `model=` swap; Together shows the cheap variant can be same-model-lower-precision (just a model-string convention). verso-already-has.
3. Batching at 50% cost: real lever, but async/offline execution model — out of scope for the online loop; possible evals-side adapter only. avoid-overkill-leaning.
4. Pre-flight cost estimate: not present in Verso; weakly on-thesis (observability). neutral.

---

## 10. Honest leanness signal
Together's value is 99% serving infrastructure (kernels, spec-decode, GPU fleet, fine-tune) — explicitly the layer Verso refuses ("not the model/kernel, no Rust, not an SDK"). The ONE thing at Verso's altitude is the OpenAI-compatible request surface, where the only net-new idea is the provider-native `response_format=json_schema` fast-path. Everything else (50+ endpoints, jigs, clusters, ATLAS) is exactly the breadth-for-its-own-sake Verso's thesis cuts. Strongly SUPPORTS the lean thesis: a framework does not need to own any of this — it needs one clean adapter that can pass a schema through and fail over.
