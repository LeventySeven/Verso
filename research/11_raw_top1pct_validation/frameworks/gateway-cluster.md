# gateway-cluster — Raw Extraction (OpenRouter · LiteLLM · Portkey · Bifrost)

Track: frameworks. Unit: gateway-cluster. Focus: routing / failover / semantic-cache / budget-guard cost primitives, mapped to Verso's `FailoverModel` + `RetryPolicy` + per-call `model=` swap + `agent.override()`.

Sources read (raw, on disk):
- `/Users/seventyleven/Desktop/researchfms/teardowns/OPENROUTER.md` (6916 lines)
- `/Users/seventyleven/Desktop/researchfms/teardowns/LITELLM.md` (4126 lines)
- `/Users/seventyleven/Desktop/researchfms/teardowns/PORTKEY.md` (1142 lines)
- `/Users/seventyleven/Desktop/researchfms/teardowns/BIFROST.md` (940 lines)

KNOWN = stated in source. INFERRED = my synthesis.

---

## 1. FAILOVER / FALLBACK primitives

### OpenRouter (KNOWN)
- Fallback chain is a request field: `models?: string[]  // ["primary-model", "fallback1", ...]` (line 151) and `allow_fallbacks?: boolean // default true; if false, fail if first provider fails` (line 210).
- `provider.order: ["anthropic","openai","google"]` — tries in order; "If first fails (error, rate limit, downtime), tries next" (line 270-276).
- Trigger conditions (line 450-453): error, downtime, **rate limiting (429 from provider)**.
- **INFERRED in source**: "No documented retry backoff between fallback hops; likely immediate failover to preserve TTFT" (line 464). i.e. fallback is failover, NOT retry-with-backoff.
- "Zero completion insurance: if response has 0 tokens + no finish_reason → retry or return free" (line 1006) — a failure-mode guard: empty/cold-start responses are not billed and trigger retry.

### LiteLLM (KNOWN)
- `fallbacks` = list of dicts `[{"gpt-4": ["gpt-3.5-turbo"]}]`; router picks deployment via strategy, on failure (after `num_retries`) consults fallback model GROUP (line 540-542).
- **Max chain depth = `ROUTER_MAX_FALLBACKS = 5`** (`constants.py:13`, `int(os.getenv("ROUTER_MAX_FALLBACKS", 5))`).
- **Cooldown** (line 544-551): a deployment is excluded from `healthy_deployments` if `>= allowed_fails` failures in `cooldown_time` window. Defaults: `DEFAULT_ALLOWED_FAILS = 3` (per minute), `DEFAULT_COOLDOWN_TIME_SECONDS = 5`, `DEFAULT_FAILURE_THRESHOLD_PERCENT = 0.5` (50% failure rate triggers cooldown). State in `router_utils/cooldown_cache.py`, per-deployment or per-model-group.
- `DEFAULT_MAX_RETRIES = 2` (constants.py).

### Portkey (KNOWN)
- `StrategyModes` enum: `FALLBACK`, `LOADBALANCE`, `CONDITIONAL`, `SINGLE` (requestBody.ts).
- FALLBACK iterates `targets[]`, continues to next IF (a) status in `strategy.onStatusCodes` (e.g. `[429,500,502,503,504]`), OR (b) `onStatusCodes` unset AND `!response.ok`. **Stops on `x-portkey-gateway-exception: true`** — "this wasn't a recoverable LLM failure, this was OUR fault" (don't fall back through gateway bugs). (lines 36, 482).
- **Strategies nest recursively** via `tryTargetsRecursively` (~360 LOC, handlerUtils.ts:476-834): `fallback-of-(loadbalance-of-(conditional-of-(...)))` in one JSON config. Each node can carry its own `retry`/`cache`/`hooks`/`timeout`; inheritance flows top-down, child overrides win (lines 217, 297, 454-468).
- **Circuit breaker pre-filter**: before strategy dispatch, filters `targets` where `t.isOpen === true`; if ALL open, skips the filter so the breaker doesn't deadlock the request (lines 33, 478). State store is EXTERNAL (Redis / control plane); OSS exposes hook `handleCircuitBreakerResponse` only (lines 65, 309).

### Bifrost (KNOWN)
- `BifrostRequest.Fallbacks []FallbackProvider` — primary + ordered fallbacks, tried on retryable errors. Each fallback specifies own provider/model/override params (line 250).
- `handleRequest` is the fallback orchestrator (bifrost.go:4501-4586): try primary → `shouldTryFallbacks(req, primaryErr)` (checks error class is retryable: rate-limit/server-error, NOT auth/bad-request) → iterate fallbacks. Each fallback: open OTel span (`SpanKindFallback`, attr `fallback.index`), fresh `FallbackRequestID`, `clearCtxForFallback(ctx)` to wipe per-attempt context keys so new attempt's plugins see clean state, `prepareFallbackRequest`, `tryRequest`.
- **If all fail, returns the PRIMARY's error, not the last fallback's** — "preserves the user-visible root cause" (line 64). (Notable design choice.)
- `shouldContinueWithFallbacks(fallback, err)` — if error fatal (bad request) return immediately, else continue.
- **Key rotation on rate-limit**: `keyProvider(usedKeyIDs)` closure excludes already-tried keys so retries naturally rotate to a fresh key in the pool (line 87, 253).
- Retry defaults (schemas/provider.go): `DefaultMaxRetries = 0` (**retries OFF by default**), `DefaultRetryBackoffInitial = 500ms`, `DefaultRetryBackoffMax = 5s`. Retryable status codes 500/502/... in `core/utils.go` `retryableStatusCodes` map.

**VERSO MAP**: Verso ships `FailoverModel` + `RetryPolicy` (typed errors, auth/content fail fast) + per-call `model=` swap + `agent.override()`. The "fail fast on auth/bad-request, retry on rate-limit/server-error" error-class split is EXACTLY Verso's typed-error taxonomy. Ordered fallback list == FailoverModel. Bifrost's "return the PRIMARY's error not the last" and OpenRouter's "fallback is failover not backoff (preserve TTFT)" are design refinements Verso likely already embodies. **verso-already-has** for the core; the LiteLLM cooldown (eject a deployment after N fails in a window) and Portkey circuit-breaker are stateful health-tracking ACROSS calls — see §5.

---

## 2. LOAD BALANCING / ROUTING strategies

### OpenRouter default load balancer (KNOWN — the standout cost lever)
Three sequential filters (lines 240-250, replica algo lines 1050-1072):
1. **Uptime filter** — providers with outages in last 30s deprioritized (moved to end, not excluded).
2. **Inverse-square price weighting** — among stable providers, routing probability ∝ `1 / price²`. "Provider A at $1/M gets 9x more traffic than Provider C at $3/M (because 1/1² / 1/3² = 9). This makes cheaper providers dramatically preferred." Replica: `weights = preferred.map(p => 1 / (p.pricing.prompt ** 2))`, weighted random sample.
3. **Fallback ordering** — remaining providers are ordered fallbacks.
- Disabled when `sort` or `order` explicitly set.
- `sort` strategies: `"price"` (cheapest first / `:floor` shortcut), `"throughput"`, `"latency"`, or `{by, partition: "model"|"none"}` (line 227-230).
- Performance threshold routing (soft): `preferred_min_throughput: {p50: 100}`, `preferred_max_latency: {p90: 2.0}` over rolling 5-min window; non-meeting providers moved to end (never excludes — "should never prevent your request from being executed").

### LiteLLM routing strategies (KNOWN — `router.py` 10,897 LOC)
Named strategies: `simple-shuffle`, `least-busy`, `usage-based-routing`, `usage-based-routing-v2`, `latency-based-routing`, `cost-based-routing` / `lowest_cost`, `tag-based-routing`, plus experimental `adaptive_router`, `auto_router`, `complexity_router`, `quality_router`.
- `cost-based-routing` (`lowest_cost.py`, 330 LOC): minute-bucketed cost map; picks deployment with lowest cumulative cost in current window.
- `complexity_router`: uses input length / token counts to pick smaller models for simpler queries.
- `quality_router`: routes by observed eval quality scores.
- Pre-call checks: validate context window (sum tokens vs `max_input_tokens`), validate feature support (drop model if `tools` set but `!supports_function_calling`), validate budget.

### Portkey CONDITIONAL routing (KNOWN)
- `ConditionalRouter` (156 LOC, dependency-free) — MongoDB-operator query syntax over `{metadata, params, url}`: `$eq $ne $gt $gte $lt $lte $in $nin $regex $and $or`. Conditions evaluated in order, first match selects `targets.find(t => t.name === then)`, else `strategy.default`, else throws `RouterError`. Example: "if metadata.env==prod && metadata.tier==enterprise → claude-opus, else → gpt-4o-mini" (lines 38, 198, 492-506).
- LOADBALANCE: weighted RNG, `randomWeight = Math.random() * sum(weights)`, stateless per-request.

### Bifrost (KNOWN)
- Weighted-random KEY selection within a provider: `keyselectors.WeightedRandom` (default), `int(weight*100)`, `rand.Intn(total)`, walk accumulating. **~10ns, zero-alloc** (line 33, 251, 327).
- **No conditional routing in OSS core** — needs enterprise governance plugin (line 255, 345).
- Custom selectors pluggable via `config.KeySelector`.

**VERSO MAP**: These are PROVIDER-arbitrage / multi-deployment routing features. Verso is "we don't force the graph," NOT a router/planner cult (NON-GOAL: "not a router/planner cult", "no learned routers"). The inverse-square price-weighted LB, named routing strategies, MongoDB-operator conditional routing, complexity/quality routers — these are gateway-product concerns, **avoid-overkill** for Verso. Per-call `model=` swap + `agent.override()` already give the user explicit control; if they want cost-routing they write 3 lines of Python. The named-strategy zoo is exactly the "complexity for its own sake" Verso cuts.

---

## 3. SEMANTIC CACHING (the one genuine cost lever Verso may lack)

### LiteLLM (KNOWN — most concrete)
- `Cache` factory, **8 backends**: local/in-memory, redis, redis-cluster, **redis-semantic**, **qdrant-semantic**, s3, gcs, azure-blob, disk (caching.py:55).
- Semantic variants embed the request (default `text-embedding-ada-002`, configurable per `redis_semantic_cache_embedding_model` / `qdrant_semantic_cache_embedding_model`), cosine-similarity lookup, return cached response if similarity > `similarity_threshold`.
- `DualCache`: in-memory + Redis in parallel with INDEPENDENT TTLs (`default_in_memory_ttl` short, `default_in_redis_ttl` long) — short in-mem reduces Redis hops, long Redis gives cross-process persistence.
- Cache key = all OpenAI params (model, messages, temperature, top_p, max_tokens, tools, tool_choice, response_format, seed...) + cache model name. **Model-group key collapse**: with `caching_groups`, `gpt-4-deployment-1` and `gpt-4-deployment-2` share cache hits (same logical model) (line 649).
- `preset_cache_key` stashed in `litellm_params` after first computation so provider param renames (Bedrock `max_tokens`→`max_new_tokens`) don't cause cache misses (line 651).

### Portkey (KNOWN + INFERRED)
- In-memory map keyed by `SHA-256(JSON.stringify(body) + '-' + url)`. Statuses: `HIT SEMANTIC_HIT MISS SEMANTIC_MISS REFRESH DISABLED`. TTL default 24h. Streams NOT cached. Redis backend via `REDIS_CONNECTION_STRING`. `x-portkey-cache-force-refresh` header forces miss.
- **Semantic cache enum exists but logic is hosted-only** — "the embedding + ANN lookup is server-side proprietary" (lines 51, 223, 308). INFERRED: embeds request, cosine threshold ~0.92.

### Bifrost (KNOWN — interface in OSS, plugin enterprise)
- Semantic cache is an LLM plugin (`plugins/semanticcache/main.go`). `PreHook` embeds latest user message (`text-embedding-3-small` default), queries vector store (pgvector / dedicated) for nearest neighbors above similarity threshold **default 0.95**; on HIT short-circuits with cached `BifrostResponse`; on MISS, `PostHook` embeds + stores `(embedding, response)` with TTL. **Cache key includes model name** so different models don't share entries.

**VERSO MAP**: Verso ships exact-key/byte caching adjacent primitives (KV-cache-stable prefix, prune masking) and a typed memory tier with RRF recall — but those are CONTEXT engineering, not a *response* cache keyed by request-similarity that short-circuits the model call entirely. A semantic *response* cache (embed prompt → cosine lookup → return prior completion, skip the LLM) is a distinct cost lever. **This is the one steal-additive candidate** IF and only if it's gated behind a flag and byte-identical-when-unused (cache=None → zero behavior change). It overlaps Verso's memory store (sqlitevec already present) so the embedding+ANN substrate exists. Risk: it's adjacent to "no LLM-summarization-compaction-by-default" non-goal in spirit (cache returns a stale answer); must be strictly opt-in.

---

## 4. BUDGET / SPEND GUARD (cross-run cost cap)

### LiteLLM (KNOWN — most complete budget model)
Budget enforcement (`budget_manager.py`, `router_strategy/budget_limiter.py`), levels:
- **Per-key** `LiteLLM_VerificationToken.max_budget`; **Per-user** `max_budget` + `model_max_budget` (dict model→budget); **Per-team** `max_budget`; **Per-model** router-level `model_max_budget_limiter`; **Global** `litellm.max_budget`.
- `DEFAULT_SOFT_BUDGET` — warning threshold, alerts at X% of budget WITHOUT blocking.
- Over budget → `429 Too Many Requests` (or 400, configurable).
- `budget_limiter` (914 LOC): "Skips deployments over budget", Redis per-deployment monthly spend.
- Spend incremented atomically `increment_spend_counters`; Redis counter cache + flush to Postgres on `DEFAULT_FLUSH_INTERVAL_SECONDS = 5`.
- Cost source: `model_prices_and_context_window.json` — **2,303 entries, 40,076 lines**. Fields: `input_cost_per_token`, `output_cost_per_token`, `cache_read_input_token_cost`, `input_cost_per_token_batches` (50% off), `output_cost_per_reasoning_token`, `input_cost_per_audio_token`, `input_cost_per_image_token`, `search_context_cost_per_query`. "the cost map is the framework's most-loved feature" (line 714).

### Portkey / Bifrost (INFERRED / enterprise)
- Portkey: budgets (USD/period) per virtual key, checked before provider call, token usage applied after; `RateLimiterKeyTypes`: VIRTUAL_KEY/API_KEY/WORKSPACE/INTEGRATION_WORKSPACE; control-plane only.
- Bifrost: hierarchical Customer → Team → Virtual Key, each with budget caps (USD/period) + rate limits (req/s, tokens/s). Governance plugin `PreHook` decrements atomic counter, denies over cap; `PostHook` applies actual `response.Usage.TotalTokens`. Enterprise.

### OpenRouter (KNOWN)
- `max_price: {prompt?, completion?, request?, image?}` — `$/million tokens`, a **HARD per-request limit**: "request fails with 503 if no provider meets the price constraint" (line 221, 295). This is a per-REQUEST price ceiling, not a cumulative budget.
- `usage.cost` returned per response (line 580); `cost_details.upstream_inference_cost` for BYOK.

**VERSO MAP**: Verso has eval-side cost/lift accounting (`Eval.lift`, calibrate, bucket) but those teardowns describe a RUNTIME **cross-run / per-session cumulative spend cap that denies the next call when a USD ceiling is hit**. Verso's loop has `max_steps` and `max_context_tokens` (token bounds) but no dollar-budget guard that accumulates across steps/runs. A per-run `max_cost_usd` (accumulate token×price each step, stop with a `StopReason.BUDGET` at the ceiling) is on-thesis: it's a reliability/cost bound exactly like `max_steps`, additive, byte-identical when `max_cost_usd=None`. The full LiteLLM multi-tenant budget DB (per-key/team/user, Postgres, RBAC) is **avoid-overkill** (that's an SDK/gateway-product, a NON-GOAL). But the *single scalar* per-run budget guard + a tiny price lookup is **steal-additive**. OpenRouter's per-request `max_price` hard ceiling is a simpler variant of the same idea.

---

## 5. STATEFUL HEALTH TRACKING (cooldown / circuit breaker)

- **LiteLLM cooldown** (§1): eject deployment after N fails / failure-% in a window, exclude from healthy set, auto-recover after cooldown_time. State in Redis/`DualCache`.
- **Portkey circuit breaker** (§1): per-target open/half-open/closed, pre-filter unhealthy targets, external state store.
- **Bifrost**: TCP keepalive 10s/5s/3 detects dead conns in ~25s before reuse (avoids retry-on-dead-conn tail latency); `MaxConnDuration=300s` forces conn recycle vs NAT silent drops.

**VERSO MAP**: Verso's `FailoverModel` + `RetryPolicy` handle a single call's failover. Cross-call health memory (cooldown/circuit-breaker that remembers a provider is down for the NEXT request) is genuinely absent, BUT it's a multi-deployment-pool concern that presumes a router managing N interchangeable endpoints — adjacent to the "no router cult" non-goal. **avoid-overkill / neutral** unless a user is running a provider pool, which is not Verso's primary shape. The TCP/conn-pool tuning is HTTP-client-layer, below Verso's abstraction (handled by httpx/SDK). neutral-context.

---

## 6. PROMPT-CACHE CONTINUITY (sticky routing for warm cache)

- **OpenRouter** (KNOWN, line 597): after a cached request, "subsequent requests for the same model are routed to the same provider, keeping your cache warm." Explicit routing exception — cache efficiency overrides cost-weighted LB. Anthropic cache pricing: 5m TTL = 1.25x write / 0.9x read; 1h = 2x write / 0.9x read. `order: ["anthropic"]` sticky for prompt-cache warm (line 1579).
- **Bifrost** (KNOWN): session stickiness via KVStore maps `(model, sessionID)` → keyID so a conversation always hits the same upstream key → maximizes Anthropic ephemeral cache HIT rate. Combined with preserving `cache_control: {type:"ephemeral", ttl:"5m"|"1h"}` markers.

**VERSO MAP**: Verso already does provider prompt-cache via KV-cache-stable system prefix (context primitive). Sticky-routing-to-same-provider is a multi-endpoint-pool optimization — only relevant if Verso pooled redundant endpoints, which it doesn't by default. neutral-context / avoid-overkill.

---

## 7. NON-COST context for completeness

- OpenAI shape as lingua franca across all four; bidirectional transforms (Portkey `ProviderConfig` param maps with min/max/default/transform; Bifrost Go-struct converters; LiteLLM normalizes 124 providers → OpenAI `ChatCompletion`).
- Bifrost perf (architectural, not cost): 11µs overhead @ 5kRPS via 6 prewarmed `sync.Pool`s + `atomic.Pointer` lock-free config + per-provider channel+worker-pool + fasthttp + sonic JSON. **Non-goal for Verso** (Python-only, no Rust/Go perf cult).
- Bifrost MCP + Starlark code-mode sandbox: agents emit Python-like scripts calling MCP tools. Verso = native @tool is THE path, MCP opt-in adapter (NON-GOAL: MCP-first). avoid-overkill.
- Bifrost non-blocking enqueue with `dropExcessRequests` (load-shed vs queue): infra-layer, neutral.
