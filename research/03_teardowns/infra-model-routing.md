# Cluster: infra-model-routing
## Model routing / gateway — OpenRouter + LiteLLM

Sources: `teardowns/OPENROUTER.md` (6,916 lines, Tier 1B — live API + OpenAPI spec + docs corpus)
         `teardowns/LITELLM.md` (4,126 lines, Tier 1A — cloned source at `649eb2d`, 592K LOC)

---

## OpenRouter

### What it is

An LLM API aggregator: one OpenAI-compatible endpoint (`POST /api/v1/chat/completions`) that routes to 300+ models across 60+ providers. It is NOT a model provider. Core value: provider routing with fallback, unified billing in USD credits, response normalization, advanced routing controls (latency, throughput, price, ZDR, BYOK).

Infrastructure: Cloudflare Workers for edge routing (close to caller), edge-cached API-key auth, Google Cloud Storage for I/O logging, Cloudflare for DDoS. Routing service itself is a closed-source Node.js/TypeScript service.

### Agent loop shape

No internal agent loop. OpenRouter is a **request-response routing layer**, not an agent runner. The "loop" lives in the caller. OpenRouter operates at single-request scope. The only loop-like behavior is the fallback chain (sequential provider tries) and the server-tool execution loop (model calls `openrouter:web_search`, gets results, calls again — this is a micro-loop within one request).

### Tool system

Three categories of tools, cleanly separated:

```typescript
// Server tools — OpenRouter executes, not the client
{ type: "openrouter:web_search", parameters?: { max_results?: 1-25, engine?: "auto"|"native"|"exa"|"firecrawl"|"parallel", allowed_domains?: string[], excluded_domains?: string[] } }
{ type: "openrouter:datetime" }                              // no params, no cost
{ type: "openrouter:image_generation", parameters?: { model?, quality?, size?, output_format?: "png"|"jpeg"|"webp", ... } }

// User-defined tools — client executes (standard OpenAI function-call schema)
{ type: "function", function: { name, description, parameters: JsonSchema } }

// Plugins — always-run transforms (not model-decided)
{ id: "context-compression" }   // auto-enabled for ≤8192-context models
{ id: "response-healing" }       // JSON repair for providers lacking structured_outputs; non-streaming only
```

Tool table by dimension:

| | Server Tools | Plugins | User-Defined Tools |
|--|--|--|--|
| Trigger | Model decides | Always | Model decides |
| Executor | OpenRouter | OpenRouter | Client app |
| Per-request calls | 0 to N | Once | 0 to N |
| Specified via | `tools` array | `plugins` array | `tools` array |
| Type prefix | `openrouter:*` | N/A | `function` |

Key insight for Verso: `require_parameters: true` in `ProviderPreferences` is **critical** for agent reliability. Without it, a fallback provider silently drops unsupported params (e.g. `tools`) and returns a text answer instead of a tool call — breaking the agent loop with no error. Always set this for tool-using agents.

### Routing engine — the core product

**Default load balancer** (no `sort` or `order` specified):
1. Uptime filter: providers with significant outages in last 30 seconds are deprioritized (not excluded)
2. Inverse-square price weighting: `P(provider) = (1/price²) / Σ(1/price²)`. Provider at $1/M gets 9x more traffic than provider at $3/M. Cheap providers dramatically preferred.
3. Fallback ordering: remaining providers serve as ordered fallbacks on failure.

Algorithm verbatim (DESIGNED replica):
```typescript
function selectProvider(candidates: ProviderEndpoint[], prefs: ProviderPreferences): ProviderEndpoint[] {
  const healthy = candidates.filter(p => p.uptime_last_30m > UPTIME_THRESHOLD);
  const degraded = candidates.filter(p => p.uptime_last_30m <= UPTIME_THRESHOLD);
  const preferred = healthy.filter(p => meetsThresholds(p, prefs));
  const fallback = healthy.filter(p => !meetsThresholds(p, prefs));
  const weights = preferred.map(p => 1 / (parseFloat(p.pricing.prompt) ** 2));
  const totalWeight = weights.reduce((a, b) => a + b, 0);
  const probabilities = weights.map(w => w / totalWeight);
  const selected = weightedSample(preferred, probabilities);
  return [selected, ...preferred.filter(p => p !== selected), ...fallback, ...degraded];
}
```

`ProviderPreferences` schema (the full routing control surface):
```typescript
interface ProviderPreferences {
  order?: string[];               // Ordered provider slugs: ["anthropic", "openai"]
  allow_fallbacks?: boolean;      // default true; false = fail immediately on first error
  only?: string[];                // whitelist
  ignore?: string[];              // blacklist
  quantizations?: ("int4"|"int8"|"fp4"|"fp6"|"fp8"|"fp16"|"bf16"|"fp32"|"unknown")[];
  data_collection?: "allow" | "deny";  // "deny" = ZDR-light (no training)
  zdr?: boolean;                  // Zero Data Retention (stricter)
  enforce_distillable_text?: boolean;
  require_parameters?: boolean;   // CRITICAL FOR AGENTS — skip providers not supporting all params
  sort?: "price" | "throughput" | "latency" | { by: ..., partition: "model"|"none" };
  preferred_min_throughput?: number | { p50?, p75?, p90?, p99? };  // soft
  preferred_max_latency?: number | { p50?, p75?, p90?, p99? };     // soft
  max_price?: { prompt?: number; completion?: number; request?: number; image?: number }; // HARD limit
}
```

Key routing behaviors:
- `max_price` is a **hard** limit (503 if no provider meets it); performance thresholds are **soft** (move non-meeting providers to end of list, never fail outright)
- `require_parameters: true` skips providers not supporting all request params — always use for tool-calling agents
- `data_collection: "deny"` routes only to non-training providers; `zdr: true` is stricter subset
- BYOK keys always override `order`, regardless of position in array; BYOK endpoints tried first
- Cache sticky routing: after a request with cached content, subsequent requests route to same provider to keep cache warm (explicit exception to load balancer)

### Model identity — virtual variant suffixes

Model IDs follow `{namespace}/{model-name}:{variant}`. Variants are NOT separate models; they mutate routing behavior:

| Suffix | Equivalent provider config | Agent use |
|--------|---------------------------|-----------|
| `:nitro` | `sort: "throughput"` | Latency-critical tool executors |
| `:floor` | `sort: "price"` | Bulk readers, batch processors |
| `:free` | Filter `pricing.prompt == "0"` | Dev/CI testing |
| `:extended` | Extended context variant | Full-history orchestrators |
| `:thinking` | Reasoning enabled | Planning phase, critic |
| `:exacto` | Tool-call success rate routing | JSON-accuracy-critical sub-agents |

Suffixes can be chained: `openai/gpt-5.4-mini:free:online`. `:exacto` is also applied automatically when `tools` is present in the request (Auto Exacto routing).

### Auto-routing systems

**`openrouter/auto`** — powered by NotDiamond (third-party routing intelligence). Analyzes prompt complexity + task type + model capabilities; user can restrict pool via `allowed_models: ["anthropic/*", ...]`. No markup over selected model's normal cost.

**Auto Exacto (`:exacto`)** — automatically reorders providers when `tools` is present. Ranking signals (highest to lowest): tool-calling success rate from real production traffic → provider throughput/latency → internal benchmark data.

**`openrouter/free`** — 5-step pipeline: capability filter → random selection from free pool (not weighted). Rate limits lower.

**`openrouter/body-builder`** — converts natural language to structured API JSON for parallel multi-model execution. No charge for body-builder step.

### Fallback chains

```json
{
  "model": "anthropic/claude-sonnet-4.6",
  "models": ["anthropic/claude-sonnet-4.6", "anthropic/claude-opus-4.6", "google/gemini-3.1-pro-preview", "openai/gpt-5.4"],
  "provider": { "allow_fallbacks": true, "require_parameters": true }
}
```

Trigger conditions: context length exceeded, content moderation refusal, 429 (rate limit), 502/503 (provider error), any provider error. Models tried sequentially; no hop limit (exhausts full array). `response["model"]` reveals which model was used — how you detect fallback activation in the agent loop. Billing is based on model that processed, not model requested.

### Prompt caching

Supported providers: Anthropic, OpenAI, DeepSeek, Gemini, Grok, Groq, Moonshot AI.

Request format:
```json
{"messages": [{"role": "system", "content": [{"type": "text", "text": "...", "cache_control": {"type": "ephemeral", "ttl": "1h"}}]}]}
```

TTL: `"5m"` (default Anthropic) or `"1h"` (2x write price). Min tokens: OpenAI 1024, Anthropic 1024–4096.

Cache pricing:
| Provider | Cache Writes | Cache Reads |
|----------|-------------|-------------|
| OpenAI | Free | 0.25x–0.50x input |
| Anthropic (5m TTL) | 1.25x input | 0.9x input |
| Anthropic (1h TTL) | 2x input | 0.9x input |
| DeepSeek | Same as input | Discounted |

Cache visible in: `usage.prompt_tokens_details.cached_tokens` and `usage.prompt_tokens_details.cache_write_tokens`.

Cache sticky routing: OpenRouter routes subsequent requests for the same model to the same provider to keep the cache warm. This is an explicit exception to the default load balancer.

### Reasoning/thinking tokens

Unified `reasoning` object across all providers:
```json
{ "reasoning": { "effort": "high", "max_tokens": 4000, "exclude": false, "enabled": true } }
```

Effort → token allocation (Claude): `max(min(max_tokens * ratio, 128000), 1024)`.

| Effort | Allocation |
|--------|-----------|
| `xhigh` | 95% |
| `high` | 80% |
| `medium` | 50% |
| `low` | 20% |
| `minimal` | 10% |
| `none` | 0% |

Multi-turn reasoning: pass back `reasoning_details` from previous response to preserve reasoning continuity across turns. Essential for tool-use workflows with reasoning models.

### Streaming protocol

SSE format normalized to OpenAI's stream format across all providers:
```
data: {"id":"gen-...","object":"chat.completion.chunk","model":"openai/gpt-4o","provider":"OpenAI","choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}
data: {"id":"gen-...","object":"chat.completion.chunk","choices":[{"delta":{"content":""},"finish_reason":"stop"}],"usage":{...}}
data: [DONE]
```

Key behaviors:
- OpenRouter emits `: OPENROUTER PROCESSING` SSE comment during long ops (valid per spec, safely ignored; prevents client timeout)
- `usage` appears only in final non-`[DONE]` chunk
- `provider` field added to all chunks (not in OpenAI native format)
- Mid-stream errors: `error` object in chunk body + `finish_reason: "error"` + HTTP 200 (cannot change HTTP status mid-stream)
- Streaming cancellation: stops billing for OpenAI/Anthropic/Fireworks; does NOT stop billing for Bedrock/Groq/Google

Mid-stream error shape:
```typescript
{ id, object, model, provider, error: { code, message }, choices: [{ delta: { content: "" }, finish_reason: "error" }] }
```

### Structured outputs / response healing

Native structured outputs: OpenAI (GPT-4o+), Google Gemini, Anthropic Sonnet 4.5+, Fireworks, most open-source.

Response healing plugin for providers lacking native support:
```json
{ "plugins": [{ "id": "response-healing" }], "response_format": { "type": "json_schema", "json_schema": {...} } }
```
Repairs: missing brackets, trailing commas, unquoted keys, JSON embedded in markdown, text preceding JSON. Constraints: non-streaming only; does NOT fix truncated JSON (token-limit hit).

### Error system

```typescript
interface ErrorResponse { error: { code: number; message: string; metadata?: Record<string, unknown> } }
```

HTTP codes:
- 400: bad request / CORS
- 401: invalid credentials
- 402: insufficient credits (blocks ALL subsequent requests)
- 403: content moderation
- 408: timeout
- 429: rate limited
- 502: provider invalid response
- 503: no provider meets routing requirements

Zero Completion Insurance: if response has 0 completion tokens + blank/null finish_reason or `finish_reason: "error"`, OpenRouter deducts zero credits automatically. Retry immediately — transient cold-start or scaling event.

Detection:
```python
def check_zero_completion(response: dict) -> bool:
    usage = response.get("usage", {})
    choice = response["choices"][0]
    return (usage.get("completion_tokens", 0) == 0 and not choice.get("finish_reason"))
```

### Rate limiting

Rate limits are **global per account** — not per API key. Additional API keys do not increase limits. Free models have stricter (undisclosed) RPM. Paid accounts: primarily credit-based; high-concurrency possible if balance is sufficient.

Management keys with per-key credit limits (workaround for runaway agents):
```python
POST /api/v1/keys
{ "name": "tool-executor-key", "limit": 50, "limitReset": "monthly" }
```

### Observability — Broadcast system

OTLP-based. Per-request spans include: token usage, cost, timing, model/provider, request/response content (unless Privacy Mode).

Custom metadata via `trace` field:
```json
{ "trace": { "trace_id": "...", "trace_name": "...", "generation_name": "...", "department": "finance" } }
```

Destinations: Langfuse, Braintrust, Datadog, Grafana, Arize, PostHog, Sentry, S3, Snowflake, Weights & Biases, Webhooks (all OTLP-compatible).

Agent tracking pattern: tag each agent role with `trace.metadata.agent_role` and aggregate per role in observability backend.

### Multi-agent routing patterns (from the supplement)

Per-agent-role provider configs:

**Orchestrator** (sticky Anthropic for cache warm, no data collection, require_parameters):
```python
{ "order": ["anthropic"], "allow_fallbacks": True, "data_collection": "deny", "require_parameters": True }
```

**Tool Executor** (throughput sort, hard price cap, require_parameters):
```python
{ "sort": "throughput", "allow_fallbacks": True, "require_parameters": True, "preferred_max_latency": {"p90": 1.5}, "max_price": {"prompt": 0.000002, "completion": 0.000015} }
```

**Long-Context Reader** (price sort, 1% data discount if non-sensitive):
```python
{ "sort": "price", "allow_fallbacks": True, "data_collection": "allow", "max_price": {"prompt": 0.000001} }
```

**Critic** (no fallbacks — different model family = uncalibrated evaluation):
```python
{ "order": ["anthropic"], "allow_fallbacks": False, "data_collection": "deny", "require_parameters": True }
```

Quantization guidance per role:
| Agent Role | Recommended | Reasoning |
|------------|------------|-----------|
| Orchestrator | `["fp16", "bf16"]` | Planning errors cascade — quality critical |
| Tool Executor | `["int8", "fp8", "fp16"]` | JSON quality matters; int4 unreliable |
| Long-context Reader | `["int8", "fp8"]` | Cost > edge-case quality |
| Code Agent | `["fp16", "bf16", "fp32"]` | Code is binary — compiles or not |
| Critic | `["fp16", "bf16"]` | Evaluation calibration needs full precision |

BYOK per-agent strategy: orchestrator and code agent use BYOK keys (proprietary prompts/code should not share OpenRouter's pool); tool executors share the pool (high volume, low sensitivity). Orchestrator + critic sharing the same BYOK Anthropic key = shared cache pool.

### Key replica constants

```typescript
const CONSTANTS = {
  UPTIME_OUTAGE_WINDOW_SECONDS: 30,
  PERFORMANCE_WINDOW_MINUTES: 5,
  LATENCY_STATS_WINDOW_MINUTES: 30,
  COMPRESSION_DEFAULT_CONTEXT_THRESHOLD: 8192,
  COMPRESSION_MIN_CONTEXT_RATIO: 0.5,
  DATA_SHARING_DISCOUNT: 0.01,
  WEB_SEARCH_DEFAULT_MAX_RESULTS: 5,
  WEB_SEARCH_MAX_RESULTS_LIMIT: 25,
  WEB_SEARCH_EXA_PRICE_PER_1000: 4.0,
  ANTHROPIC_REASONING_MIN_TOKENS: 1024,
  ANTHROPIC_REASONING_MAX_TOKENS: 128000,
  MODERATION_FLAGGED_INPUT_MAX_CHARS: 100,
};
```

### Verso lesson (OpenRouter)

**Copy:**
- `require_parameters: true` pattern — agents MUST verify the fallback provider actually supports the params they depend on. Silent parameter dropping is a real failure mode.
- Per-agent-role provider config objects. Verso should have a `ModelConstraints` type that carries `require_parameters`, `data_collection`, `quantizations`, `max_price`, and `sort_strategy` per agent node.
- Cache sticky routing: when prompt caching is active, Verso must pin subsequent turns to the same provider, not re-run the load balancer.
- `allow_fallbacks: false` for critic/evaluator agents — calibration is model-family-specific, not just capability-based.
- Virtual suffix design: `:thinking`, `:exacto`, `:nitro` as declarative shortcuts over the full provider config object. Verso model identifiers could support similar suffix semantics.
- Zero Completion Insurance detection + immediate retry — Verso's LLM call wrapper should check this case explicitly.
- `trace` metadata injection: Verso should propagate `agent_id`, `agent_role`, `task_id`, `session_id` into every LLM call so multi-agent traces are navigable.
- Mid-stream error detection: never rely on HTTP status for streaming errors; always parse chunk-level `error` field and `finish_reason == "error"`.

**Avoid:**
- Account-global rate limits with no per-agent-class isolation. Verso should expose budget partitioning by agent role so a runaway sub-agent can't kill the orchestrator's quota.
- Billing streams that require polling (`GET /api/v1/generation?id=...`) rather than inline response metadata. Verso cost accounting should be synchronous on the response.

---

## LiteLLM

### What it is

Two products in one package: (1) Python SDK (`litellm.completion()`) — universal OpenAI-format interface translating to 97 chat providers, normalizing responses, tracking costs; (2) Standalone LLM gateway proxy (FastAPI, port 4000) — virtual API keys, multi-strategy routing, fallback chains, caching (8 backends), cost tracking (MySQL/Postgres via Prisma), 75+ observability integrations, guardrails, MCP gateway.

Version: 1.85.0 (`649eb2d` 2026-05-14). LOC: ~592,100 Python under `litellm/`. MIT license.

### SDK pipeline (agent loop perspective)

```
litellm.completion(model="claude-3-5-sonnet", messages=[...], tools=[...])
  1. validate_and_fix_openai_messages(messages)
  2. validate_and_fix_openai_tools(tools)
  3. validate_chat_completion_tool_choice(tool_choice)
  4. validate_and_fix_thinking_param(thinking)          # normalize camelCase keys
  5. MCP-tools detection — if tools contains MCP URLs → acompletion_with_mcp
  6. get_llm_provider(model) → (model, provider, api_key, api_base)
  7. ProviderConfigManager.get_config(provider) → Config class
  8. config.map_openai_params(openai_params) → provider-native params
  9. provider handler (elif chain, 90+ branches in main.py:1834–4400+)
  10. ModelResponse or CustomStreamWrapper
  11. cost_calculator from model_prices_and_context_window.json
  12. success_callback / failure_callback (Langfuse, OTel, Prometheus, ...)
  return ModelResponse | CustomStreamWrapper
```

LiteLLM is not an agent loop itself — it's the LLM call primitive that agent frameworks (and Verso) should sit on top of or replace with their own call layer.

### Provider abstraction pattern

Every provider is a `Config` class with four methods:
1. `get_supported_openai_params(model)` — list of OpenAI params this provider accepts for this model
2. `map_openai_params(non_default_params, optional_params, model, drop_params)` — translate to provider-native
3. `transform_request(model, messages, optional_params, litellm_params, headers)` — build HTTP body
4. `transform_response(...)` — parse provider response → `ModelResponse` (OpenAI shape)

**OpenAI** is the reference implementation — no translation needed; 30 base params + model-specific. Every other provider is a subset.

**Anthropic** (2,600 LOC adapter, biggest): 16–18 params. Key translations:

```python
# tools: OpenAI → Anthropic schema
# OpenAI: [{type: "function", function: {name, description, parameters: JsonSchema}}]
# Anthropic: [{name, description, input_schema: JsonSchema}]

# tool_choice:
# OpenAI "auto"     → Anthropic {type: "auto"}
# OpenAI "required" → Anthropic {type: "any"}
# OpenAI {type: "function", function: {name}} → Anthropic {type: "tool", name}

# reasoning_effort → budget_tokens:
# "minimal"→1024, "low"→2000, "medium"→8000, "high"→16000, "xhigh"→32000

# Tool name sanitization: "/" and "." in tool names → "_" (Anthropic rejects special chars)
# Reverse map stashed in litellm_params so tool names round-trip correctly on response side
```

**Gemini** (Vertex AI): messages format converts from OpenAI roles (system/user/assistant/tool) to Gemini's `contents` ([{role: user|model, parts: [...]}]) with system instruction at top level. Tool schema: OpenAI `{type: "function", function: {...}}` → Gemini `{functionDeclarations: [{name, description, parameters}]}`.

**Bedrock**: uses Converse API which normalizes internally, then LiteLLM normalizes its output. Tool schema: `toolSpec.inputSchema.json`.

### Router — the load balancer (`router.py`, 10,897 LOC)

The Router takes a `model_list` of deployments and exposes the same `completion()` API as the SDK, with load balancing, fallback, and cooldown.

Deployment shape:
```python
model_list = [
    {
        "model_name": "gpt-4",                    # logical model group (alias)
        "litellm_params": {
            "model": "azure/gpt-4-deployment-1",  # actual provider model
            "api_key": "...", "api_base": "...",
            "rpm": 1440, "tpm": 240000, "weight": 1,
        },
        "model_info": {
            "id": "uuid-1",
            "tags": ["us", "prod"],
            "guardrails": ["lakera"],             # per-deployment guardrails
        },
    },
]
```

Routing strategies (all share `DualCache` + `CustomLogger` infrastructure; differ only in scoring function):

| Strategy | LOC | State | Scoring |
|---|---|---|---|
| `simple-shuffle` | 64 | None | Weighted random by `weight`→`rpm`→`tpm` (first set wins) |
| `least-busy` | 250 | DualCache: `{group}_request_count` | Lowest in-flight count |
| `lowest-latency` | 621 | DualCache: `{group}_map[id].latency[]` (window=10, TTL=1h) | Avg seconds-per-completion-token; TTFT for streaming |
| `usage-based-routing-v2` | 668 | Redis atomic INCRBY per-minute | Lowest TPM/RPM ratio against configured limit |
| `cost-based-routing` | 330 | DualCache: `{group}_map[id].cost` | Lowest cumulative cost in window |
| `tag-based-routing` | 275 | Stateless | First deployment whose tags overlap request's `metadata.tags` |

**`simple-shuffle` gotcha (source: `router_strategy/simple_shuffle.py:7-14`):** checks ONLY the first deployment for whether `weight` is set — if deployment[0] has `weight` but others don't, the others get weight=0 and are never picked. All deployments must have the same weight field set or none.

**`lowest-latency` key insight:** latency is normalized to seconds-per-completion-token, not raw response time. A deployment producing 1000 tokens in 5s isn't penalized vs one producing 100 tokens in 1s. TTFT used for streaming (optimizes user-perceived speed).

**`usage-based-routing-v2`:** Redis atomic counters. Pre-call RPM check: atomically increments RPM counter and rejects the deployment before calling the LLM if over limit — saves the wasted API call.

Cooldown logic (from `router_utils/cooldown_handlers.py`):
- Triggers on: 429, 401, 408, 404, all 5xx
- Does NOT trigger on: 400, 403, 422 (client-side errors, not deployment's fault)
- Threshold (v2): `failures / (successes + failures) > 0.5` (50%) with minimum 5 total requests
- Duration: `DEFAULT_COOLDOWN_TIME_SECONDS = 5` (seconds; env-configurable)
- Single-deployment protection: if only 1 deployment in group, cooldown suppressed unless ≥1000 requests in window — prevents locking out the only option on transient failures

Fallback chain: `fallbacks=[{"gpt-4": ["gpt-3.5-turbo", "claude-3-5-sonnet"]}]`
- `ROUTER_MAX_FALLBACKS = 5` (max chain depth, env-configurable)
- Error-specific fallbacks: `context_window_fallbacks` for `ContextWindowExceededError`, `content_policy_fallbacks` for `ContentPolicyError`, general `fallbacks` for everything else
- Wildcard deployments: `model_name="openai/*"` catches any OpenAI model

Pre-call checks before dispatching:
1. Context window validation — sum message tokens vs `max_input_tokens` from cost map; trigger `context_window_fallbacks` if exceeded
2. Feature validation — if `tools` set but model doesn't `supports_function_calling`, drop tools or fail
3. Budget validation
4. Rate limit validation (v2 strategies use Redis atomic check)

### Caching architecture

Factory pattern returning one of 8 backends:
```python
LiteLLMCacheType.LOCAL    → InMemoryCache
LiteLLMCacheType.REDIS    → RedisCache
LiteLLMCacheType.REDIS_SEMANTIC   → RedisSemanticCache (embedding-based lookup)
LiteLLMCacheType.QDRANT_SEMANTIC  → QdrantSemanticCache
LiteLLMCacheType.S3       → S3Cache
LiteLLMCacheType.GCS      → GCSCache
LiteLLMCacheType.AZURE_BLOB → AzureBlobCache
LiteLLMCacheType.DISK     → DiskCache
```

`DualCache` (memory + Redis, independent TTLs): short in-memory TTL reduces Redis hops; longer Redis TTL provides cross-process persistence. Used throughout router for cooldown state, latency tracking, TPM/RPM counters.

Cache key generation (`caching/caching.py:276-352`):
- Hashes all OpenAI-API params (model, messages, temperature, top_p, max_tokens, tools, tool_choice, response_format, seed, ...)
- Model-group key collapse: if behind a Router with `caching_groups`, uses the caching group as model identifier (not deployment-specific model) → deployments behind the same logical model share cache hits
- `preset_cache_key` stashed in `litellm_params` after first computation — avoids re-hashing and prevents cache misses from provider-side param renames (e.g. Bedrock `max_tokens` → `max_new_tokens`)

Semantic caching: embed request via `text-embedding-ada-002` (default), lookup in Qdrant/Redis-vector, return cached if cosine similarity > `similarity_threshold`. Skips identical-meaning requests even with different wording. Requires Redis Stack or Qdrant — not a single-process default.

### The Proxy (gateway)

15,524-LOC FastAPI app. Full production LLM gateway:

Auth waterfall (`auth/user_api_key_auth.py`):
1. Extract API key (multiple header formats)
2. Custom auth function (enterprise)
3. Public route bypass
4. JWT validation (if `enable_jwt_auth=True`)
5. OAuth2 validation (if `enable_oauth2_auth=True`)
6. Master key check → admin
7. DB lookup → `LiteLLM_VerificationToken` (hashed key)
8. Budget check (spend < max_budget)
9. Model permission check (`models[]` on key)
10. Rate limit check (RPM/TPM cap)
11. Return `UserAPIKeyAuth` for billing/tagging

Budget levels: per-key, per-user, per-user-per-model, per-team, per-model (Router), global.

Budget enforcement pattern: Redis counter (`INCRBYFLOAT`) incremented per call; flush worker (`DEFAULT_FLUSH_INTERVAL_SECONDS=5`) batches writes to Postgres. Handles 1000+ req/sec of spend tracking without saturating DB.

Hooks (not guardrails — internal proxy rate limiting/budget enforcement):
- **`parallel_request_limiter`** — Redis INCR/DECR around LLM call; caps concurrent in-flight per key
- **`max_budget_limiter`** — blocks pre-call if spend ≥ budget (Redis counter is SoT)
- **`max_iterations_limiter`** — caps total LLM calls per `metadata.session_id` — prevents runaway agent loops
- **`dynamic_rate_limiter` (v3)** — adaptive: if provider returns 429s, auto-reduces proxy RPM cap to avoid hammering provider; self-tunes on observed 429 rate

Guardrails (`proxy/guardrails/`): pre-call and post-call hooks. Built-in: CrowdStrike AIDR, Lakera, AWS Bedrock Guardrails, Presidio (PII), PromptArmor, Aim Security. Can block (raise `ContentFilterError`), modify (PII redaction), or log (audit-only). `ModifyResponseException` returns HTTP 200 with `finish_reason: "content_filter"` — client apps don't break.

Pass-through endpoints: clients can use provider's NATIVE API through LiteLLM (Vertex, Bedrock); proxy validates auth, injects upstream key, forwards unchanged, tracks spend. AWS Bedrock pass-through adds SigV4 signing.

### MCP gateway

Bidirectional:

1. **Proxy IS an MCP server** (`proxy/_experimental/mcp_server/`): exposes model catalog and admin tools (create_key, get_spend) via MCP protocol. Claude Desktop can connect and discover "tools" = models.

2. **Proxy connects to MCP servers**: `tools=[{"type": "mcp", "server_url": "..."}]` detected at `main.py:1199-1258`, hands off to `acompletion_with_mcp`. Fetches tools from MCP server, presents to LLM as function-callable tools, routes tool calls back to MCP server.

Federation model: one LiteLLM proxy federates to N MCP servers AND is federatable by M MCP clients. Hub-spoke architecture.

### Observability — 75+ integrations

`CustomLogger` base class (`integrations/custom_logger.py`) with hooks:
- `log_pre_api_call`, `log_post_api_call`
- `log_success_event`, `log_failure_event`
- `async_log_success_event`, `async_log_failure_event`

Registered via `litellm.success_callback = ["langfuse"]` or `litellm.callbacks = [CustomLoggerInstance()]`.

Integrations: Langfuse, LangSmith, Helicone, OTel, Datadog, Prometheus, Arize, Braintrust, Galileo, deepeval, Athina, S3, GCS, PostHog, Slack alerts, and 60+ more.

**Metadata injection pattern (the key design):** Every request carries `metadata.tags`, `metadata.user_api_key_user_id`, `metadata.team_id`, `metadata.org_id`, `metadata.agent_id`, `metadata.model_group` from auth time onward. Every callback reads these tags. Single source of truth for routing, billing, and logging without a separate orchestration layer.

### Streaming

`CustomStreamWrapper` normalizes all provider SSE formats to OpenAI delta shape:
- OpenAI SSE → pass through
- Anthropic SSE (`event: content_block_delta\ndata: {"delta":{"text":"..."}}`) → OpenAI delta
- Bedrock event stream (JSON events over chunked HTTP) → OpenAI delta
- Vertex AI SSE → OpenAI delta
- Cohere (newline-delimited JSON) → OpenAI delta
- Ollama / vLLM (newline-delimited JSON) → OpenAI delta

`LITELLM_MAX_STREAMING_DURATION_SECONDS` (default: no cap, env-configurable): opt-in wall-clock cap; terminates stream with `Timeout` if exceeded.

Token counts accumulated as chunks arrive; final chunk includes `usage`.

### Exact constants (`constants.py`)

```python
ROUTER_MAX_FALLBACKS = int(os.getenv("ROUTER_MAX_FALLBACKS", 5))
DEFAULT_MAX_RETRIES = 2
DEFAULT_ALLOWED_FAILS = 3
DEFAULT_COOLDOWN_TIME_SECONDS = 5
DEFAULT_FAILURE_THRESHOLD_PERCENT = 0.5          # 50% failure rate triggers cooldown
DEFAULT_FLUSH_INTERVAL_SECONDS = 5               # Redis → Postgres spend flush
DEFAULT_REDIS_SYNC_INTERVAL = 1                  # seconds
DEFAULT_HEALTH_CHECK_PROMPT = "test from litellm"
request_timeout = 600                            # seconds (legacy: 6000)
max_latency_list_size = 10                       # sliding window for latency routing
latency_ttl = 1 * 60 * 60                        # 1 hour — latency window expiry
DEFAULT_FAILURE_THRESHOLD_MINIMUM_REQUESTS = 5   # min requests before cooldown can trigger
SINGLE_DEPLOYMENT_TRAFFIC_FAILURE_THRESHOLD = 1000  # suppress cooldown for single-deployment groups
DEFAULT_SOFT_BUDGET = ...                        # warning threshold (% of budget)
DEFAULT_NUM_WORKERS_LITELLM_PROXY = 1
DEFAULT_IMAGE_TOKEN_COUNT = 250
DEFAULT_MAX_TOKENS = 4096
redis_semantic_cache_embedding_model = "text-embedding-ada-002"
```

### Honest gaps / footguns

1. `simple-shuffle` only checks `healthy_deployments[0]` for whether `weight` is set — if deployment[0] has weights but others don't, others get `0` and are never picked
2. `least-busy` read-modify-write is not atomic in `DualCache` — race condition under high concurrency; use `usage-based-routing-v2` for production multi-process deployments
3. Cost calculator returns cost=0 silently for models not in `model_prices_and_context_window.json`
4. Semantic cache requires Redis Stack or Qdrant — not suitable as a default
5. Proxy requires Prisma + Postgres for production multi-tenant deployment
6. `get_optional_params` and `map_openai_params` are the largest functions in the codebase — correct but unreadable; any custom provider runs through them

### Verso lesson (LiteLLM)

**Copy:**
- Provider `Config` abstraction pattern: `get_supported_openai_params` + `map_openai_params` + `transform_request` + `transform_response`. This is the correct design for multi-provider normalization. Verso's LLM call layer should implement this for Anthropic, OpenAI, and Gemini at minimum.
- `DualCache` (in-memory + Redis, independent TTLs): Verso's caching should use this primitive. Short in-memory TTL for hot path; longer Redis TTL for cross-process consistency.
- Model-group cache key collapse: when Verso has multiple deployments behind one logical model, cache keys should use the group name, not the specific deployment. Prevents cache miss storm on deployment changes.
- Router pre-call context window validation → `context_window_fallbacks`: Verso should validate token count before dispatching and have a separate fallback for context overflow vs. general errors.
- Error-typed fallback chains: three separate fallback lists (context_window, content_policy, general) rather than one. Different errors need different fallback strategies.
- `max_iterations_limiter` per `session_id`: Verso should have a hard cap on LLM calls per agent run/session, configurable per agent node. This is the safety rail against infinite agent loops.
- `dynamic_rate_limiter` adaptive pattern: if Verso's LLM call layer is seeing 429s from a provider, it should backpressure before the next call rather than letting every call attempt and fail.
- Metadata injection at auth time: Verso should inject `agent_id`, `agent_role`, `task_id`, `run_id`, `session_id` into every LLM call's metadata context so all observability callbacks have full attribution without the application code having to pass it.
- Anthropic tool-name sanitization with forward/reverse maps: any character not in `[a-zA-Z0-9_-]` in tool names must be sanitized before sending to Anthropic, and reverse-mapped on response. Verso's tool executor must handle this transparently.
- Auto-dropping `thinking` blocks when the last assistant message has no `thinking_blocks`: Verso's context assembler must implement this — Anthropic rejects requests where `thinking` is enabled in tools params but the previous assistant turn has no thinking blocks.
- Cooldown single-deployment protection: if only one deployment is available, suppress cooldown unless failure rate is catastrophic AND you've had enough traffic. Verso should not cool down the only model it can call.

**Avoid:**
- The 10,897-line `router.py`. Verso's routing should be a small, swappable strategy interface (< 200 lines per strategy) that composes with the rest of the system — not a monolith that accumulates edge cases.
- The 15,524-line `proxy_server.py`. Verso is a framework, not a gateway service. Keep gateway concerns (auth, billing, RBAC) as opt-in integrations, not core.
- Legacy v1 routing strategies alongside v2. Verso should pick a routing strategy design and not carry compat baggage.
- 75 observability integrations in the core. Pick a protocol (OTel) and let integrations be plugins.
- Prisma + Postgres as a dependency for core routing. Verso's persistent state (session memory, eval results, run history) should work with a pluggable store.

**Verso could improve by:**
- Combining OpenRouter's per-request declarative routing control (`ProviderPreferences`, per-agent config objects) with LiteLLM's multi-deployment pool awareness. Today these are separate products; a single framework could express "for this agent node, use model group X with throughput routing, cache sticky to provider Y, with a 50ms TTFT p90 budget, and require tool support."
- Making `require_parameters` validation happen at graph construction time (static analysis of agent graph vs. model capabilities) rather than at request time.
- First-class reasoning budget management: OpenRouter's effort → token_ratio mapping + LiteLLM's per-model param support knowledge, combined into a single `reasoning_budget` config on the agent node.

---

## Verso implications

1. **Use LiteLLM (or its provider abstraction) as the LLM call primitive, not the gateway.** The provider `Config` pattern — 4-method interface, OpenAI as canonical, every other provider as a translation — is the correct design. Verso should sit above this layer and not re-implement it.

2. **Model routing in Verso should be a first-class, per-node config, not a global setting.** Different agent roles need different routing strategies. The orchestrator pins to Anthropic for cache warm. Tool executors need throughput routing with hard price caps. Critics need `allow_fallbacks: false`. Express this as a `ModelPolicy` attached to each node in the graph.

3. **`require_parameters` equivalent is non-negotiable for agent reliability.** Verso's model selector must verify that the chosen model/provider actually supports the features the node requires (tools, structured output, streaming, reasoning). Fail at dispatch time, not after getting a wrong response.

4. **Implement error-typed fallback chains.** Three separate fallback lists: context overflow → larger context model; content moderation → less-strict model; general error → any capable equivalent. A single fallback list conflates these cases.

5. **`max_iterations_limiter` per session is the safety rail against runaway loops.** This is not optional. Verso should expose `max_llm_calls` per agent run as a first-class config parameter, enforced in the durable execution layer.

6. **Cache key generation must collapse by model group, not deployment.** When Verso is routing across multiple deployments behind one logical model, cache keys must use the group identity. Otherwise cache hit rate collapses whenever the load balancer picks a different deployment.

7. **Metadata injection at the framework level.** Verso should propagate `run_id`, `session_id`, `agent_role`, `task_id` into every LLM call automatically. The application developer should never have to pass this manually; it's framework infrastructure.

8. **Streaming mid-error handling must be chunk-level, not HTTP-status-level.** In streaming mode, errors arrive in the chunk body with HTTP 200. Verso's streaming consumer must parse `error` and `finish_reason == "error"` at each chunk, not only on HTTP error status.

9. **Zero Completion Insurance / empty response detection.** Verso's LLM call wrapper should detect 0-completion responses and retry immediately — transient, not a logic error.

10. **Reasoning models require continuity across turns.** When using a reasoning model (`:thinking`, reasoning effort), pass back `reasoning_details` from each response into the next turn's messages. Verso's context assembler must handle this as a first-class concern, not an afterthought.

11. **Prompt cache stickiness must override the load balancer.** Once a provider has warmed the cache for a conversation, Verso must pin that conversation to the same provider for subsequent turns. This is an explicit routing exception to cost/throughput optimization.

12. **MCP as the tool boundary.** LiteLLM's bidirectional MCP gateway pattern (proxy can be an MCP server AND can federate to upstream MCP servers) is the right architecture for Verso: first-class MCP tool integration means agent nodes declare tool requirements by MCP server URL, not by bespoke function schemas. Verso should make MCP the primary tool registration mechanism.
