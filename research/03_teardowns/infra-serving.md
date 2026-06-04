# Inference Serving — Verso Research Note
## Cluster: infra-serving
### Systems: vLLM · llama.cpp · Together AI
*Sources: /Users/seventyleven/Desktop/researchfms/teardowns/VLLM.md (2260 lines), LLAMACPP.md (1845 lines), TOGETHERAI.md (1793 lines)*

---

## vLLM

### What It Is

vLLM is the dominant open-source GPU inference server. Its two core innovations are PagedAttention (KV-cache as paged blocks, eliminating up to 80% fragmentation) and continuous batching (batch recomposed every scheduler step, so long requests never block short ones). Everything else — OpenAI-compatible API, FlashAttention backends, LoRA support — is standard. The moat is the scheduler + KV-cache manager.

### Engine Architecture: Two-Process Split

vLLM V1 runs as two OS processes communicating over ZeroMQ + msgpack:

1. **API process** (`AsyncLLM`) — asyncio event loop, HTTP-facing, runs `InputProcessor`, `OutputProcessor`, `RequestOutputCollector` queue per request. Receives `EngineCoreOutputs` from the GPU process via ZMQ; yields tokens to the SSE formatter.
2. **GPU process** (`EngineCore`) — sync inner loop, owns the scheduler and model executor. No asyncio. The loop: `schedule() → execute_model() → sample_tokens() → update_from_output()`. Communicates via ZMQ push/pull.

This split eliminates the Python GIL bottleneck. V1 vs V0 throughput: ~1.7×.

### Scheduler — The Full Loop

**State machine per request:** `WAITING → RUNNING → FINISHED_STOPPED / FINISHED_LENGTH / FINISHED_ABORTED / FINISHED_ERROR`. No swap-to-CPU in V1 — preemption is recompute-only (prior docs said swap; this is a verified correction).

**Two-phase schedule per step (verbatim from `vllm/v1/core/sched/scheduler.py:929`):**
- Phase 1: drain RUNNING requests (decode + chunked-prefill continuations), in self.running order
- Phase 2: admit WAITING requests only if no preemptions this step and not paused

**Budget enforcement per step (two independent caps):**
- `max_num_batched_tokens` (default 2048) — total token slots across all scheduled requests
- `max_num_seqs` (default 128) — total sequences in one batch

**Chunked prefill** (`enable_chunked_prefill=True` by default): long prompts split across multiple steps, interleaved with decode tokens from other requests. Constants:
- `max_num_partial_prefills = 1` (default; controls how many partially-prefilled seqs allowed)
- `long_prefill_token_threshold = auto: int(max_model_len * 0.04)` when >1 partial prefills
- `scheduler_reserve_full_isl = True` — admission gate checks full prompt fits before admitting

**Batch queue for pipeline parallelism** (`batch_queue_size > 1`): overlaps scheduling of next batch with GPU execution of current batch. FIFO deque, `maxlen = batch_queue_size`. Eliminates pipeline bubbles.

**Scheduler policy:** `"fcfs"` (default) or `"priority"` (custom `Request.__lt__` comparator). Custom scheduler class injectable via `scheduler_cls`.

### KV-Cache Manager

**PagedAttention block design:**
- Default block size: 16 tokens/block (from `CacheConfig.DEFAULT_BLOCK_SIZE = 16`)
- Physical block: `KVCacheBlock(block_id)` with a GPU memory slot
- `BlockHash = NewType("BlockHash", bytes)` — SHA-256 (default) or xxHash of token IDs; **chained hash** (each block's hash depends on all ancestor blocks' content, not just its own tokens)
- `FreeKVCacheBlockQueue` — doubly-linked list; front = oldest (LRU eviction order)

**Prefix caching** (`enable_prefix_caching=True` by default): `get_computed_blocks()` looks up block hashes to find already-computed prefix. Caching skipped when `prompt_logprobs is not None` (would produce incomplete coverage). Max cacheable = `request.num_tokens - 1` (last token must be recomputed for logits).

**Copy-on-write for shared prefixes:** blocks with `ref_cnt > 1` are never mutated. When a request's decode diverges into a shared block, a new physical block is allocated and the shared block copied. `ref_cnt` decrements on request completion.

**Preemption (V1 ONLY = RECOMPUTE):** preempted request re-enters WAITING; KV blocks are freed. There is no swap-to-CPU path in V1.

**GPU memory allocation:**
- Dummy forward pass → peak activation memory measured
- `num_blocks = floor(available_memory * gpu_memory_utilization / (block_size * num_layers * num_heads * head_dim * 2 * dtype_size))`
- Physical tensors: `[num_blocks, num_heads, block_size, head_dim]` per layer
- `gpu_memory_utilization` default: **0.92** (92%)

**KV cache dtype options:** `auto`, `float16`, `bfloat16`, `fp8`, `fp8_e4m3`, `fp8_e5m2`, `nvfp4`, plus TurboQuant variants. Both weights AND KV-cache can be quantized (doubles effective context capacity).

### SamplingParams — Every Constant

```python
# vllm/sampling_params.py (KNOWN, verbatim)
n: int = 1                    # Max = VLLM_MAX_N_SEQUENCES (default 16384)
temperature: float = 1.0      # < 1e-5 → greedy; < 1e-2 → clamped to 1e-2 with warning
top_p: float = 1.0            # forced to 1.0 for greedy
top_k: int = 0                # 0 or -1 = all tokens
min_p: float = 0.0            # minimum prob relative to most likely token
seed: int | None = None       # -1 treated as None
presence_penalty: float = 0.0       # range [-2.0, 2.0]
frequency_penalty: float = 0.0      # range [-2.0, 2.0]
repetition_penalty: float = 1.0     # must be > 0.0
max_tokens: int | None = 16   # must be >= 1 if set (NOTE: default is 16, not None)
min_tokens: int = 0
ignore_eos: bool = False
logprobs: int | None = None   # -1 = all vocab_size; True → 1
prompt_logprobs: int | None = None  # forces skip_reading_prefix_cache=True
```

### OpenAI API Server (FastAPI)

**Multi-dialect router:** a single vLLM engine speaks three vendor dialects — OpenAI Chat (`/v1/chat/completions`), OpenAI Responses API (`/v1/responses`), Anthropic Messages API (`/v1/messages`), and legacy Completions. Each dialect has its own `protocol.py` and `serving.py` that translate into a shared `SamplingParams` object and emit the vendor-specific SSE format.

**Capability-gated routing:** `build_app` mounts routes only for tasks the loaded model supports (`get_supported_tasks()`). Pooling-only models get no generation routes.

**Request lifecycle (per-request prep pipeline):**
1. Parse body → `_check_model` (model name → base model or LoRA adapter, 404 if neither)
2. `_base_request_id`: `X-Request-Id` header or fresh `random_uuid()`
3. `_maybe_get_adapters`: auto-select multimodal LoRA by content-type matching (only when exactly one adapter matches)
4. `request.to_sampling_params()` → `SamplingParams`
5. `engine.generate(prompt, sampling_params, request_id, lora_request, trace_headers)` → async generator
6. SSE formatter or aggregate into response object

**`@with_cancellation` decorator (the real disconnect pattern):**
```python
# vllm/entrypoints/utils.py:57-99
# Races two asyncio tasks: (1) the actual handler, (2) an http.disconnect listener
# asyncio.wait(FIRST_COMPLETED) → cancel the loser
# request.is_disconnected() is documented as BROKEN under middleware — never use it
```
Client disconnect → `asyncio.CancelledError` in `generate()` → `await engine.abort(request_id)` → frees KV blocks. Cancel propagates all the way to GPU via ZMQ.

**SSE wire format (KNOWN verbatim from `chat_completion/serving.py`):**
```
# FIRST chunk (role + empty content):
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

# Per-token DELTA chunks (model_dump_json(exclude_unset=True)):
data: {"id":"chatcmpl-...","choices":[{"index":0,"delta":{"content":"hello"},"finish_reason":null}]}

# FINAL usage chunk (only if stream_options.include_usage):
data: {"id":"chatcmpl-...","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}

data: [DONE]
```

`stream_interval` (default 1): buffer N tokens before emitting an SSE event. `RequestOutputKind.DELTA` = only new tokens per chunk (default). `RequestOutputKind.CUMULATIVE` = full text so far (expensive for long outputs).

**`RequestOutputCollector`:** per-request asyncio queue. The background `output_handler` coroutine coalesces `EngineCoreOutputs` from ZMQ and pushes into it. `VLLM_V1_OUTPUT_PROC_CHUNK_SIZE` env var limits outputs processed per event loop iteration (prevents GIL blocking on large batches, uses `await asyncio.sleep(0)` between chunks).

**Watchdog (`launcher.py:144-167`):** 5-second loop checks `engine.errored and not engine.is_running`. If true and `VLLM_KEEP_ALIVE_ON_ENGINE_DEATH` is not set, flips `server.should_exit`. This is the only mechanism that catches fatal engine errors during streaming (since a 200 is already sent, post-200 exceptions are swallowed into SSE error chunks). A Verso LLM gateway must build this same two-part contract.

**Error envelope (KNOWN, uniform across six handlers):**
```python
class ErrorInfo(OpenAIBaseModel):
    message: str
    type: str
    param: str | None = None
    code: int  # HTTP status code carried inside body

class ErrorResponse(OpenAIBaseModel):
    error: ErrorInfo
```
Six handlers registered: `HTTPException`, `RequestValidationError`, `EngineGenerateError` (per-request, recoverable), `EngineDeadError` (fatal → triggers watchdog shutdown), `GenerationError` (500, no stack trace — expected error), `Exception` (catch-all).

**Pure-ASGI middleware (anti-BaseHTTPMiddleware pattern):**
- `AuthenticationMiddleware`: pre-hashes configured API keys as SHA-256 digests; `secrets.compare_digest` in a constant-time loop; skips OPTIONS and non-guarded paths; raw `__call__(scope, receive, send)` to avoid BaseHTTPMiddleware buffering bug
- `XRequestIdMiddleware`: wraps `send` to inject `X-Request-Id` header on `http.response.start` — no body buffering

**MCP integration (KNOWN):** vLLM's tool server wiring in `init_generate_state` (`:75-83`): if `--tool-server` is a URL, attaches an `MCPToolServer().add_tool_server(url)` at startup. Tool execution is MCP-client-side from vLLM's perspective.

**`freeze_gc_heap()` before `yield` in lifespan:** removes the engine/model weights from Python GC scanning, eliminating GC pause-time jitter during serving. Called at `server_utils.py:467`.

### Key Constants Summary

| Constant | Value | Source |
|---|---|---|
| `DEFAULT_BLOCK_SIZE` | 16 tokens | `CacheConfig` |
| `gpu_memory_utilization` | 0.92 | `CacheConfig` |
| `max_num_batched_tokens` | 2048 | `SchedulerConfig` |
| `max_num_seqs` | 128 | `SchedulerConfig` |
| `stream_interval` | 1 (emit each token) | `SchedulerConfig` |
| `max_tokens` default | 16 | `SamplingParams` |
| `temperature` greedy threshold | 1e-5 | `SamplingParams` |
| `temperature` clamp floor | 1e-2 | `SamplingParams` |
| Watchdog interval | 5.0s | `launcher.py` |
| Max sequences per request | 16384 | `VLLM_MAX_N_SEQUENCES` |
| Prefix cache hash | SHA-256 (default) or xxHash | `CacheConfig` |

### Speculative Decoding

vLLM supports: EAGLE (tree-structured draft, uses a small draft model trained to predict the target model's internal states), DraftModel, NGram. All implemented in `vllm/v1/spec_decode/`. `MAX_SPEC_LEN` capped. `RejectionSampler` uses exact acceptance/rejection math: accept draft token if `uniform_sample < min(1, p_target / p_draft)`.

### Quantization

18+ formats including AWQ, GPTQ-Marlin, FP8, GGUF (via llama-cpp-python bridge), compressed-tensors, bitsandbytes, TorchAO, INT4, FP4, NVFP4.

### Verso Lesson — vLLM

**Copy:**
- Dual-task disconnect race (`@with_cancellation`) instead of `request.is_disconnected()` — required for any LLM gateway behind middleware
- Watchdog + swallowed-stream-errors contract: never raise after 200, swallow errors into SSE chunks, watchdog catches dead engine out-of-band
- Pure-ASGI middleware for auth (constant-time SHA-256) and request-id (header wrapping) — BaseHTTPMiddleware buffers streams and breaks SSE
- Capability-gated routing: don't mount routes the loaded model can't serve
- Uniform error envelope with status inside body — JSON and HTTP status never diverge
- `freeze_gc_heap()` before serving to eliminate GC pauses
- Multi-dialect routing as a translation/serialization layer over one shared engine (Verso's inference layer should accept OpenAI + Anthropic + future dialects over one engine handle)
- `RequestOutputCollector` coalescing pattern for backpressure-safe streaming
- Pre-warm handler machinery at startup (`warmup()` call), not lazily on request 1

**Avoid:**
- `request.is_disconnected()` — broken under ASGI middleware
- `BaseHTTPMiddleware` for any middleware that might interact with streaming
- Single uvicorn `--workers N` pattern with a GPU engine — one process per GPU engine, period
- Calling sync `engine.shutdown()` on the event loop — must `run_in_executor`
- Trusting that exception handlers catch streaming failures — they don't, post-200

**Verso could improve by:**
- Making the watchdog interval configurable (vLLM hard-codes 5s)
- Surfacing a `/health` endpoint that distinguishes "engine alive + slots busy" from "engine dead" (vLLM's `/health` is minimal)
- Building the multi-dialect protocol adapter pattern as a first-class concept: Verso agents should be able to target any dialect by swapping the adapter, not the engine

---

## llama.cpp

### What It Is

Pure C/C++ inference engine. The origin of GGUF (universal quantized model format). Every local LLM runtime (Ollama, LM Studio, Llamafile, Jan, GPT4All, text-generation-webui) is a wrapper over llama.cpp. The primary target is single-machine inference: CPU SIMD, Metal (Apple Silicon), CUDA, ROCm, Vulkan.

### Server Architecture: Slots + Queue

**Slot architecture (continuous batching):**
- `n_parallel` slots (default: auto → **hard-coded to 4** when auto, regardless of VRAM/CPU count)
- Each slot: `server_slot` struct with its own llama context, sampler chain, KV cache state, LoRA state, task/task_prev, speculative state, generated text buffers, stop/truncated flags
- `kv_unified = true` when `n_parallel = auto` (unified KV across slots)

**Queue loop:**
- `server_queue::post()` pushes tasks to `queue_tasks`
- Loop: drain pending tasks via `callback_new_task()`, then call `callback_update_slots()` once per loop
- `callback_update_slots()` is where continuous batching / inference across all slots happens
- Deferred tasks can be preferentially popped by `id_slot`; otherwise FIFO
- `idle_sleep_ms` controls sleep interval; queue notifies on state change

**Grammar/structured output:** GBNF grammar parsed and stacked per-slot. `json_schema_to_grammar()` converts JSON schemas to GBNF at request time. Grammar bitmasks applied as logit processors — not a post-sampling filter.

**Context shift (context overflow strategy):** when generation would exceed context:
1. Errors if context shift disabled
2. Aborts for parent/child shared-prompt tasks and multimodal tasks
3. Computes `n_keep` from request or full prompt token count
4. Discards `n_discard` (request param) or half remaining context
5. Removes old KV sequence range; shifts positions via `llama_memory_seq_add`
6. Rewrites prompt tokens; sets `slot.truncated = true`
This is sequence surgery, not summarization.

**Auto-parallelism constant (KNOWN, verbatim from `tools/server/server.cpp`):**
```
n_parallel is set to auto, using n_parallel = 4 and kv_unified = true
```
`-np auto` does NOT inspect VRAM, model size, or CPU count. It always picks 4.

### HTTP Surface (Agent-Relevant)

Full endpoint table (KNOWN from source):
```
POST /v1/chat/completions, /chat/completions    — OpenAI chat
POST /v1/completions, /completions              — legacy completion
POST /v1/responses, /responses                  — OpenAI Responses API (converts to chat internally)
POST /v1/messages, /v1/messages/count_tokens    — Anthropic Messages API (converts to chat internally)
POST /v1/embeddings, /embedding, /embeddings    — text embeddings
POST /rerank, /reranking, /v1/rerank            — document reranking
POST /infill                                     — FIM (fill-in-the-middle)
POST /tokenize, /detokenize, /apply-template    — tokenizer utilities
GET  /slots, POST /slots/:id_slot               — slot status/control
GET  /lora-adapters, POST /lora-adapters        — LoRA hot-swap
GET  /tools, POST /tools                        — built-in tool registry (local only)
POST /cors-proxy                                — CORS proxy (unsafe, local only)
GET  /health, /v1/health                        — server status + slot availability
GET  /metrics                                   — Prometheus (--metrics flag)
GET  /models, /v1/models                        — model list (router mode)
POST /models/load, /models/unload               — router mode model management
```

**Health endpoint semantics (distinct from vLLM):**
- `200 {"status": "ok"}` — all slots idle
- `200 {"status": "no slot available"}` — all slots busy, still accepting (backpressure signal)
- `503 {"status": "loading model"}` — not yet ready

### Multi-Protocol Converter Architecture

All three dialects (OpenAI Responses, Anthropic Messages, OpenAI Chat) converge on a single `handle_completions_impl()` call. Each is a **protocol converter**, not a separate generation engine:

- **Responses API → Chat:** `server_chat_convert_responses_to_chatcmpl()`. Rejects `previous_response_id`. `instructions` → prepended system message. `function_call` → assistant `tool_calls[]`. `function_call_output` → role `tool` message. Wraps each tool as `{"type":"function","function":...}` with `strict=true` if absent. `max_output_tokens` → `max_tokens`. Does NOT implement stateful Responses (no previous-turn state management).

- **Anthropic Messages → Chat:** `post_anthropic_messages()` converts to OpenAI chat, parses through the same OpenAI-compatible parser, runs `handle_completions_impl()` with `TASK_RESPONSE_TYPE_ANTHROPIC`. First-class thinking blocks: reasoning becomes `reasoning_content` on the assistant message. Tool calls become `tool_use` blocks. Stop reason is `tool_use` when final message contains tool calls and stop was EOS/word, else `end_turn` or `max_tokens`.

- **Streaming event name differences:** Partial Responses streaming emits `response.created` and `response.in_progress` only on `n_decoded == 1`. Reasoning deltas use `response.reasoning_text.delta` (differs from Ollama's `response.reasoning_summary_text.delta`).

### Built-In Tool Registry (`/tools`)

KNOWN constants from `tools/server/server-tools.cpp`:
- `read_file`: max full read **16 * 1024** bytes; large files require line ranges
- `file_glob_search`: max **100** results; recursive; `include` default `**`
- `grep_search`: uses C++ `std::regex`; max **100** matching lines
- `exec_shell_command`: `sh -c`; default timeout **10s**; max timeout **60s**; max stdout+stderr **16KB**
- `write_file`: creates parent dirs, overwrites binary
- `edit_file`: `mode` ∈ `replace/delete/append`; applied descending by `line_start`
- `apply_diff`: runs `git apply`; **4096** output cap; **10s** timeout

Security: `exec_shell_command`, `write_file`, `edit_file`, `apply_diff` have `permission_write=true` as metadata only. The server does not enforce this. **A Verso tool gateway must never expose these over a network boundary without an external authorization layer.**

### Router Mode (Process Orchestration)

When `params.model.path.empty()`, llama-server becomes a **model router** — a parent process that spawns child single-model servers as subprocesses and proxies requests to them. Detection:
```cpp
is_router_server = params.model.path.empty()
```
Child lifecycle: allocates a free port, spawns child with `LLAMA_SERVER_ROUTER_PORT=<router_port>` in env, watches stdout for protocol markers that update model status to LOADED or SLEEPING. Router shutdown sends `CMD_ROUTER_TO_CHILD_EXIT` over child stdin; force-kills after `stop_timeout`. Streaming proxy uses a **500ms poll interval** with `should_stop()` cancellation.

This is process-level orchestration, not agent orchestration. It gives a cheap multi-model router: small tool-calling model + large synthesis model + embedding model + reranker, each loaded on demand up to `--models-max N` (default 4).

### Speculative Decoding Per-Request

Unlike most systems where spec-decode is a server-level flag, llama.cpp exposes per-request parameters: `speculative.n_min`, `n_max`, `p_min`, `type`, `ngram_size_n`, `ngram_size_m`, `ngram_min_hits`. A Verso inference abstraction should allow per-request spec-decode configuration.

### n_cmpl (Multiple Completions) — Slot-Limited

`n_cmpl > 1` creates one parent task + `n_cmpl - 1` child tasks. `process_single_task()` must find a parent slot and enough child slots; otherwise defers. Hard constraint: `n_cmpl ≤ n_parallel` (server slots). Exceeding returns an error telling the caller to increase `-np`.

### KV Cache for Hybrid Attention (ISWA)

For mixed sliding-window attention models (Gemma3, newer hybrid architectures):
```
kv_base = non-SWA layers
kv_swa  = SWA layers
size_swa = PAD(min(size_base, hparams.n_swa * n_seq_max + n_ubatch), 256)
```
SWA cache always padded to 256 cells. All sequence operations (`seq_rm`, `seq_cp`, `seq_keep`, `seq_add`, `seq_div`) mirrored to both caches. **Implication:** a scheduler estimating memory from `n_layer × ctx × head_dim` will over/under-estimate hybrid models. Memory estimation for hybrid attention must model base and SWA caches separately.

### Key Constants Summary

| Constant | Value | Source |
|---|---|---|
| `n_parallel` (auto) | **4** (hard-coded) | `server.cpp` |
| `kv_unified` (auto) | `true` | `server.cpp` |
| `n_batch` default | 2048 | `llama_context_default_params()` |
| `n_ubatch` default | 512 | `llama_context_default_params()` |
| `read_file` max | 16,384 bytes | `server-tools.cpp` |
| `file_glob_search` max | 100 results | `server-tools.cpp` |
| `grep_search` max | 100 lines | `server-tools.cpp` |
| `exec_shell_command` default timeout | 10s | `server-tools.cpp` |
| `exec_shell_command` max timeout | 60s | `server-tools.cpp` |
| `exec_shell_command` max output | 16KB | `server-tools.cpp` |
| `apply_diff` output cap | 4096 bytes | `server-tools.cpp` |
| `models-max` (router) | 4 | server parameter |
| Router streaming poll | 500ms | `server-models.cpp` |
| SWA cache alignment | 256 cells | `llama-kv-cache-iswa.cpp` |
| Embeddings: `n_batch <= n_ubatch` | required | `server.cpp` (silently mutated if violated) |

### Agentic Deployment Pattern (DESIGNED from source)

For local multi-agent systems, the recommended llama.cpp production pattern:
```
llama-server router (--models-max 4)
  model A: small tool/router model (n_parallel=4, unified KV)
  model B: large synthesis model
  model C: embedding model (n_batch = n_ubatch — enforce this)
  model D: reranker (requires embedding mode + LLAMA_POOLING_TYPE_RANK)

Application gateway (external to llama.cpp):
  - tool execution auth and rate limits
  - audit logs
  - network boundary (never expose /tools or /cors-proxy externally)
```

### Verso Lesson — llama.cpp

**Copy:**
- Multi-protocol converter architecture: Responses API and Anthropic Messages as translation layers into one generation core, not separate engines
- `/health` that distinguishes "busy" from "dead" (`no slot available` vs `loading model` vs `ok`) — Verso's health contract should be this granular
- Per-request speculative decoding parameters — Verso's LLM call abstraction should expose spec-decode knobs, not hide them
- Built-in tool registry pattern: named tools with `permissions.write` metadata, invoked locally via `POST /tools` — but with external auth gate
- Router-as-process-orchestrator: llama.cpp's model router shows that cheap multi-model routing is just subprocess management + port proxying. Verso's local inference layer could implement the same pattern without needing Kubernetes.

**Avoid:**
- Trusting `-np auto` to scale to hardware — it always picks 4. Benchmark explicitly.
- Assuming "KV cache size = n_layers × ctx × head_dim" — hybrid attention models need separate SWA cache accounting
- Embedding batch size > ubatch size — server silently mutates it, causing confusing throughput plateaus
- Exposing `/tools` on a network boundary — the permission metadata is informational only, not enforced
- Implementing Responses API as stateful — current llama.cpp source explicitly rejects `previous_response_id`

**Verso could improve by:**
- Implementing the full Responses API statefulness that llama.cpp rejects (previous-turn context management is a natural Verso concern — the agent framework owns the state, the LLM server shouldn't need to)
- Exposing slot utilization as a first-class metric (the `/slots` endpoint exists but isn't part of any standard load-balancing protocol — Verso could normalize this)

---

## Together AI

### What It Is

Multi-product NVIDIA-GPU AI cloud: custom inference engine + custom kernels (FlashAttention-3/4, megakernel, ATLAS speculative decoding) + fine-tuning service (SFT + DPO + LoRA + full + multimodal) + GPU cluster rental (K8s/Slurm on H100/H200/B200/L40/RTX-6000) + container deployment platform ("jigs") + sandboxes + image/video/audio generation + rerankers + embeddings + evals. Self-described as "AWS for AI workloads."

The engine is **vLLM-derived** (accepts vLLM's exact `SamplingParams` names: `min_p`, `top_k`, `repetition_penalty`) but **not vanilla vLLM** — Together publishes 2.8–4.5× throughput over vLLM at 8B, 2.6–4.3× at 70B. The delta is the custom kernel stack.

### The Inference Engine Stack

**FlashAttention-4 (Blackwell-native):**
- Warpgroup specialization: 2× softmax warpgroups (pipeline softmax behind MMA), 1 correction warpgroup (rescaling on critical path), 1 data-movement warpgroup (TMA loads)
- Tile size: 128×256×16 BF16/FP16 (2× larger than FA-3's Hopper WGMMA atoms); 2-CTA mode: 256×256×16
- Conditional rescaling: skip `exp()` rescaling when running max shifts less than threshold τ (micro-optimization for sequential softmax tiles)
- Performance: **1.3× faster than cuDNN 9.13**, **2.7× faster than Triton** (forward pass)
- Implementation: CuTe-DSL (Python-defined CUDA, 20-30× faster compile than C++ templates)

**Megakernel:**
Fuses entire transformer forward pass into a single CUDA kernel, eliminating ~64+ kernel launch overhead (one per layer × multiple ops per layer in standard vLLM). Uses CUDA Graph capture + replay. Claimed: **up to 3.6× faster end-to-end**.

**CPD (Cache-aware Prefill-Decode):**
Refinement of chunked prefill that adds KV-cache location awareness during chunked execution, reducing memory thrashing. Claimed **40% throughput boost** vs chunked-prefill alone.

**Quantization tiers (three deployment variants per model):**
| Tier | Precision | Example cost | Notes |
|---|---|---|---|
| Reference | FP16/BF16 | Highest | Benchmarking quality |
| Turbo | FP8/FP4 (nvfp4, mxfp4) | Mid (e.g. $0.88/M Llama-3 70B) | QuIP incoherence processing |
| Lite | INT4 | Lowest (e.g. $0.10/M 8B) | Cost-scale |

Quantized KV-cache: both weights AND KV-cache quantized. Architecture-aware calibration per model family. Fine-grain block-wise scaling (sub-tensor granularity).

### ATLAS — Adaptive Speculative Decoding

Architecture (KNOWN from Together blog):
```
                ┌─────────────────────────────────────┐
                │     Target model (70B+, multi-GPU)   │
                └────────────────┬────────────────────┘
                                 ▲ verify K tokens/step
                                 │
         ┌───────────────────────┴───────────────────────┐
         │   Confidence-aware controller (small NN)       │
         │   Inputs: per-token target confidence,         │
         │           current acceptance rate,             │
         │           workload signal                      │
         │   Outputs: which speculator to use, lookahead K│
         └─────┬───────────────────────────────┬─────────┘
               │                               │
     Static speculator                  Adaptive speculator
     Broad corpus (RedPajama etc.)      Continuously trained on
     Lookahead: 4-8 tokens              live production traffic
     Stable for general workloads       Lookahead: 2-4 tokens
     Lower acceptance on specialized   Higher acceptance on
     current-session workloads         current-session workloads
```

**Performance claims (verbatim):**
- 500 TPS on DeepSeek-V3.1 (fully-adapted scenario)
- 460 TPS on Kimi-K2-0905 (fully-adapted scenario)
- 2.65× faster than standard decoding (steady-state)
- 4× speedup over baseline; "400% improvement: from 105 TPS (FP8 baseline) to 501 TPS on NVIDIA HGX B200"
- RL training: acceptance rate rose from <10% to >80% over 1.4k training steps → 60% reduction in training time

**The on-the-fly adaptation example:** during a multi-hour coding session, the adaptive speculator learns the developer's codebase patterns. After ~100 turns, acceptance rate climbs to >80%, doubling effective tok/s. This session-specific adaptation is the key product insight.

**Infrastructure evidence (crt.sh):** `ft-speculators-training-ui.ft-k8s-stage.cloud.together.ai` in CT logs — a dedicated speculator training UI in the staging K8s fine-tuning cluster. Staging clusters also show Flyte (workflow orchestrator), Kubeflow Pipelines, ArgoCD GitOps, Dex OIDC SSO.

**Why ATLAS is hard to replicate:** you need (1) the training cluster (Flyte + K8s + Prometheus), (2) production-scale inference traffic, (3) the confidence controller, and (4) continuous online retraining infrastructure all running in parallel. Scale-gated.

### API Surface and SDK Constants

**SDK constants (KNOWN from `together==2.14.0`, `together/lib/constants.py`):**
```python
DEFAULT_BASE_URL = "https://api.together.ai/v1"
DEFAULT_TIMEOUT = 600           # 10 minutes (covers batched fine-tune polling)
MAX_SESSION_LIFETIME_SECS = 180
MAX_CONNECTION_RETRIES = 2
MAX_RETRIES = 2
INITIAL_RETRY_DELAY = 0.5
MAX_RETRY_DELAY = 8.0
```

**vLLM-fingerprint parameters unique to Together's chat completions:**
- `min_p: float` — min-probability relative to top token (vLLM sampler)
- `top_k: int` — hard top-K (vLLM)
- `repetition_penalty: float` — (vLLM)
- `chat_template_kwargs: object` — raw kwargs into HF chat template (e.g., `{"enable_thinking": True}` for DeepSeek)
- `context_length_exceeded_behavior: "truncate" | "error"` — Together-specific
- `compliance: "hipaa"` — HIPAA-compliant pod routing
- `safety_model` — chain a moderation model after generation
- `reasoning: {"enabled": bool}` — toggle reasoning
- `disable_speculative_decoding: bool` — opt out of ATLAS per-request

The `chat_template_kwargs` parameter is a strong fingerprint: Together's engine uses HF transformers' `apply_chat_template` system directly.

**Fine-tune lifecycle states (KNOWN from SDK):**
```
"pending" → "queued" → "running" → "compressing" → "uploading" → "completed"
                       ↘ "cancel_requested" → "cancelled"
                       ↘ "error"
```

**Training data formats supported:** JSONL (`conversation` type with `system/user/assistant/tool` roles, or `instruction` type with `prompt/completion`) + **Parquet** with pre-tokenized `input_ids`/`attention_mask`/`labels`/`position_ids` columns (power-user feature; most fine-tune APIs only accept JSONL).

**Jigs autoscaling:** three strategies: HTTP-rate-based, `QueueBacklogPerWorker` (default 1.01 — scale when each worker has >1 request queued; aggressive, ensures sub-second queueing latency), arbitrary Prometheus metric. `min_replicas` / `max_replicas` per deployment.

**Evals API:** full managed evaluation framework — submit dataset + evaluator config + model → returns metrics (similar lifecycle to fine-tuning). Rare among inference providers.

**Code Interpreter (Sandbox):** Firecracker microVM-based (inferred from session API + per-vCPU billing + sub-second session startup). $0.0446/vCPU-hour + $0.0149/GiB-hour. Designed as an agent tool — `code_interpreter.execute(code)` + `sessions.list()`.

### Gateway Architecture

Production stack: Node.js API gateway (Express or Fastify) → Cloudflare CDN/WAF → AWS ALB → backend. Evidence: `x-powered-by: Express` response header, Cloudflare `cf-cache-status`, AWS ALB request-id format.

Cold start mechanism for serverless models (inferred):
1. Model weights pre-loaded to GPU HBM for warm replicas; remaining on local NVMe
2. CUDA Graph capture for common sequence lengths (128, 512, 2048, 8192)
3. Page-locked memory pools for KV-cache
4. Pre-compiled binaries specialized per (model, precision, hardware, seq_len)

### Tensor Parallelism (Inferred)

| Model | Inferred TP | Reasoning |
|---|---|---|
| Llama 3.3 70B Turbo (FP8) | TP=2 | 70B × 1 byte = 70 GB; fits on 2× 80 GB H100 |
| Llama 3.3 70B Reference (FP16) | TP=4–8 | 140 GB; needs 4× H100 |
| Qwen3.5 397B A17B (MoE) | TP=8 | 8× B200 (1440 GB HBM total) |
| DeepSeek R1 (671B/37B active) | TP=8+ on B200/H200 | 671B × 2 = 1342 GB |
| DeepSeek-V4-Pro (512K context) | TP=8 | Long context needs KV-cache memory |

`disable_speculative_decoding` opt-out is available per endpoint — ATLAS can hurt latency on very short inputs or specific workloads where draft acceptance is inherently low.

### Verso Lesson — Together AI

**Copy:**
- `context_length_exceeded_behavior: "truncate" | "error"` as a first-class API parameter — don't silently truncate or silently error; let the caller choose. Verso's LLM tool should expose this.
- `chat_template_kwargs` passthrough — the ability to pass arbitrary kwargs into the chat template enables model-specific features (reasoning mode, etc.) without API versioning. Verso's `llm()` tool call should support an opaque `template_kwargs` passthrough.
- `disable_speculative_decoding` per-request — optimization knobs should be per-request, not just per-server. Verso's inference abstraction should propagate these.
- Evals as a first-class API surface — Verso should have a built-in eval primitive, not require an external tool.
- `QueueBacklogPerWorker: 1.01` as the aggressive autoscaling default — this target is what makes sub-second queueing latency achievable. For Verso's deployment tier, prefer queue-depth-based autoscaling over CPU/memory-based.
- `HIPAA`-routing via a compliance parameter in the API payload — a clean model for routing sensitive traffic without changing the endpoint.

**Avoid:**
- Treating ATLAS as replicable with standard open-source spec-decode (Medusa/EAGLE) — the real ATLAS value is the continuous online retraining, which requires production traffic and a separate training cluster running in parallel. Open-source alternatives give static spec-decode, not adaptive.
- Offering three precision tiers (Reference/Turbo/Lite) as an early product decision — it triples deployment complexity. Start with one precision and add tiers when calibrated.

**Verso could improve by:**
- Building a session-aware adaptive context: rather than retraining a spec-decode model during a session (requires GPU infra), Verso could maintain a session-scoped prefix cache and KV-reuse pool that achieves similar amortized latency wins at the application layer — no custom training infrastructure needed.
- Exposing structured compliance routing (`hipaa`, `eu-only`, etc.) as a first-class routing attribute on agent calls — not just at inference time but at every tool call and data read.

---

## Cross-System Patterns

### Shared: Multi-Protocol Adapter over One Engine

All three systems converge on the same architecture: **one generation engine, multiple protocol adapter layers**. vLLM has dedicated `protocol.py` + `serving.py` per dialect (OpenAI Chat, OpenAI Responses, Anthropic Messages). llama.cpp has converter functions that translate Responses and Anthropic Messages into OpenAI chat before calling `handle_completions_impl()`. Together accepts vLLM's parameter names natively and layers routing/compliance flags on top.

**Verso implication:** the inference abstraction layer should be a thin adapter, not a separate engine per vendor dialect. One internal request format + N adapters (OpenAI, Anthropic, custom).

### Shared: Disconnect Propagation as a First-Class Concern

All three systems handle client disconnect as a first-class concern:
- vLLM: `@with_cancellation` two-task race → `engine.abort(request_id)` → KV block free
- llama.cpp: slot state management; cancelled task `cleanup_pending_task()` before enqueue
- Together: `context_length_exceeded_behavior` and per-request `disable_speculative_decoding` suggest per-request lifecycle control

**Verso implication:** agent runs must propagate cancellation from the HTTP client all the way to GPU engine abort. A `with_cancellation`-equivalent decorator on every streaming handler is non-negotiable.

### Shared: Quota/Budget Enforcement is Per-Step, Not Per-Request

vLLM enforces `max_num_batched_tokens` and `max_num_seqs` per scheduler step, not per request. llama.cpp enforces slot limits (`n_cmpl ≤ n_parallel`). Together's `QueueBacklogPerWorker` is a per-worker queue length.

**Verso implication:** agent token budgets should be enforced at the scheduler level (every step), not just as a pre-flight check at request admission. A request that looks safe at admission can exhaust the budget mid-run.

### Shared: Streaming Error Contract (Post-200 Errors are Invisible)

All three systems send HTTP 200 before the first token. Any error that occurs mid-stream is emitted as a special SSE chunk (or closes the stream). vLLM documents this explicitly and pairs it with an out-of-band watchdog. llama.cpp slots track error state per-slot.

**Verso implication:** Verso's agent streaming must never rely on HTTP status to detect mid-run failures. The agent client must parse the SSE stream for error events. The Verso server must implement a watchdog or equivalent health check that catches failures the HTTP layer never sees.

### Shared: Health Granularity

- vLLM: `/health` is minimal (200 = alive)
- llama.cpp: three-state health (`ok` / `no slot available` / `loading model`)
- Together: queue-based autoscaling via `QueueBacklogPerWorker`

**Verso implication:** Verso's health protocol should expose at minimum: `ready` (model loaded) | `busy` (all slots occupied, still accepting) | `unavailable` (engine dead or loading). The `busy` state is load-shedding signal for upstream routing.

---

## → Verso Implications

1. **One engine, N protocol adapters.** Verso's inference layer must be built as a single internal request type + adapter plugins per vendor dialect (OpenAI, Anthropic, custom MCP-wrapped). Never duplicate the engine per dialect.

2. **`@with_cancellation` is mandatory for every streaming handler.** Use the vLLM two-task race pattern (`asyncio.wait(FIRST_COMPLETED)` vs `http.disconnect` listener). `request.is_disconnected()` is broken under ASGI middleware and must never be used.

3. **Watchdog for dead-engine detection.** Every Verso agent gateway needs an out-of-band watchdog (≥5s loop) that checks `engine.errored and not engine.is_running` and initiates graceful shutdown. Mid-stream errors cannot be surfaced via HTTP status.

4. **Budget enforcement per scheduler step, not per request.** Verso's token budget and cost tracking must be wired into the scheduler loop, not just the admission check.

5. **Per-request spec-decode knobs.** Verso's `llm()` tool abstraction should expose `n_min`, `n_max`, `p_min` for speculative decoding — these are per-request in llama.cpp and per-endpoint in Together. Hiding them as server config only loses real performance control.

6. **`context_length_exceeded_behavior: "truncate" | "error"` as a first-class parameter.** Verso agents must be able to choose what happens on context overflow. Silent truncation causes correctness bugs; silent 400s cause unretriable failures.

7. **Three-state health: `ready` | `busy` | `unavailable`.** Verso's health endpoint must distinguish slot exhaustion from engine failure. This is the signal for upstream load-shedding vs error alerting.

8. **Pure-ASGI middleware for auth and request-id.** Copy vLLM's `AuthenticationMiddleware` (constant-time SHA-256, `secrets.compare_digest`, OPTIONS bypass) and `XRequestIdMiddleware` (raw `send` wrapper). Never use `BaseHTTPMiddleware` in a streaming path.

9. **Freeze GC heap before serving.** Call `gc.freeze()` (Python equivalent of `freeze_gc_heap()`) after model/engine initialization, before `yield` in the lifespan context manager, to eliminate GC pause jitter during agent runs.

10. **`n_parallel = 4` is not "auto-configured".** If Verso uses llama.cpp as a local inference backend, the `-np auto` default hard-codes 4 slots regardless of hardware. Must be benchmarked and configured explicitly.

11. **Evals as a first-class Verso primitive.** Together is the only inference provider with a managed evals API. Verso should treat eval runs as first-class agent tasks — not external tooling — since an agent framework without built-in eval is missing its own calibration loop.

12. **Adaptive context is achievable at the application layer.** Together's ATLAS requires production-scale training infrastructure. Verso can achieve similar amortized latency wins with session-scoped KV-prefix reuse pools and context-aware routing — no custom training cluster required. This is the correct scope boundary for an agent framework.
