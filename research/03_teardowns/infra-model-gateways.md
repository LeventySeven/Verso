# Model Gateways & Routers — Verso Research Note

## Cluster: infra-model-gateways

### Systems: Helicone AI Gateway (Rust) · Not Diamond (RoRF + IRT-Router) · Cloudflare AI Gateway (Dynamic Routes) · Envoy AI Gateway (CNCF) · vLLM Semantic Router · Vercel AI Gateway · Martian (RouterBench)

*Sources (cloned `--depth=1` into `/tmp/verso-re-gateway/`, read line-by-line):*
- `github.com/Helicone/ai-gateway` — Rust, Apache-2.0. Workspace crates `weighted-balance`, `latency-router`, `dynamic-router`; `ai-gateway/src/`.
- `github.com/Not-Diamond/RoRF` — Python, routing-on-random-forests. `notdiamond-python` SDK.
- `github.com/envoyproxy/ai-gateway` — Go, Apache-2.0. `api/v1alpha1/`, `internal/extproc/`.
- `github.com/vllm-project/semantic-router` — Go + Rust (candle-binding), Apache-2.0. `src/semantic-router/pkg/`.
- `github.com/withmartian/routerbench` — dataset + notebooks.
- Cloudflare AI Gateway, Vercel AI Gateway, Martian engine — CLOSED; docs + `llms.txt` + blogs + live probes.
- arXiv: IRT-Router `2506.01048`, vLLM SR, "When to Reason" `2510.08731`.

**This note is the gateway/router companion to [`infra-model-routing.md`](./infra-model-routing.md)** (OpenRouter + LiteLLM, already teardown'd in researchfms). It does NOT re-cover OpenRouter's `selectProvider` inverse-square weighting, LiteLLM's 10-strategy router, or the researchfms-covered Portkey `tryTargetsRecursively` / Bifrost weighted-key P2C / Kong Lua pipeline. Cross-references to those are inline. The job here: extract the **specific load-balancing math, learned-routing pipelines, routing-DSL schemas, and budget-guard mechanisms** that Verso's model-provider edge needs, at reimplementable depth.

Label key: **KNOWN** = read from source at `file:line`. **INFERRED** = from docs/blog/probe. **DESIGNED** = our engineering fill for a proprietary gap.

---

## Helicone AI Gateway

### What It Is

Open-source Rust gateway (Apache-2.0, `Helicone/ai-gateway`). The entire request path is a **Tower `Service` stack** — every concern (error handling, prompts, cache, rate-limit, buffer, request-context, routing) is a `tower::Layer` wrapping an inner `Service`. The load-balancing core is two algorithms: **PeakEWMA + Power-of-Two-Choices (P2C)** for latency routing (via stock `tower::balance::p2c` + `tower::load::PeakEwmaDiscover`), and a **custom weighted-random balancer** (`crates/weighted-balance`) for weight/canary routing. There is no DB on the hot path; provider health is tracked in-process.

The moat is NOT the provider adapters (those are LiteLLM-style normalization). It is: (1) the P2C+PeakEWMA latency router, (2) the Tower layer composition, (3) the embedded `providers.yaml` + `model-mapping.yaml` that let a request for `gpt-4` transparently land on `anthropic/claude-3-7-sonnet` when that provider wins the latency race.

### The Four Routing Strategies (KNOWN — `ai-gateway/src/router/strategy.rs:26-75`)

A `RoutingStrategyService` enum with four variants, each documented verbatim in source:

```rust
pub enum RoutingStrategyService {
    // 1. receive request → 2. pick TWO random providers → 3. compare latency,
    //    pick lower → 4. if winner lacks the requested model, map via
    //    model-mapping.yaml → 5. send. (Tower stock P2C over PeakEwmaDiscover)
    ProviderLatencyPeakEwmaP2C( Balance<PeakEwmaDiscover<DispatcherDiscovery<provider::key::Key>>, Request> ),

    // weighted random over PROVIDERS (sample 1 by configured weight distribution)
    WeightedProvider( WeightedBalance<WeightedDiscover<DispatcherDiscovery<provider::weighted_key::WeightedKey>>, Request> ),

    // weighted random over (provider, model) PAIRS
    WeightedModel( WeightedBalance<WeightedDiscover<DispatcherDiscovery<model::weighted_key::WeightedKey>>, Request> ),

    // deserialize body → extract model id → pick lowest-latency provider that
    //   actually SERVES that exact model (O(n) min_by(load))
    ModelLatency( LatencyRouter ),
}
```

Selection mapping (`strategy.rs:84-101`): config `BalanceConfigInner::BalancedLatency` → P2C; `ProviderWeighted` → weighted-random provider; `ModelWeighted` → weighted-random pair; `ModelLatency` → exact-model latency router.

### P2C + PeakEWMA — The Exact Math (KNOWN algorithm, KNOWN constants)

Helicone delegates the P2C selection and PeakEWMA load metric to the upstream `tower` crate (`tower::balance::p2c::Balance`, `tower::load::PeakEwma`). The **decay and RTT constants are Helicone's** (`ai-gateway/src/config/discover.rs:37-43`):

```rust
fn default_discover_decay() -> Duration { Duration::from_secs(30) }   // EWMA decay τ = 30s
fn default_rtt()           -> Duration { Duration::from_millis(250) } // seed RTT = 250ms
```

These are passed into the discovery layer at `discover/provider/key.rs:110-113` and `discover/model/key.rs:127-130`:

```rust
let discovery = PeakEwmaDiscover::new(
    inner_discovery,
    app_state.0.config.discover.default_rtt,     // 250ms initial estimate per new endpoint
    app_state.0.config.discover.discover_decay,  // 30s decay window
    CompleteOnResponse,                          // "request complete" = full HTTP response received
);
```

**PeakEWMA load metric** — VERIFIED verbatim against `tower-0.5.3/src/load/peak_ewma.rs` (the exact crate Helicone pins, `tower = "0.5.2"`). The `Cost` each endpoint reports (lower = better):

```rust
// peak_ewma.rs:137-151  Load::load()
let pending = Arc::strong_count(&self.rtt_estimate) as u32 - 1;   // in-flight requests (live Handles)
let estimate = self.update_estimate();                            // decayed RTT, see below
let cost = Cost(estimate * f64::from(pending + 1));               // ← the metric
```

The RTT estimate update (`peak_ewma.rs:236-281`, on each request's `Handle::drop` = response received, and lazily on `load()`):

```rust
let rtt = nanos(recv_at - sent_at);                 // this request's observed RTT
self.rtt_ns = if self.rtt_ns < rtt {
    rtt                                             // PEAK: observed worse than estimate → jump UP instantly
} else {
    let decay = (-elapsed / decay_ns).exp();        // elapsed = now - last_update; decay_ns = 30s
    let recency = 1.0 - decay;
    (self.rtt_ns * decay) + (rtt * recency)         // EWMA: decay DOWN toward observed, over 30s
};
```

This asymmetry is the whole point: a provider that *just got slow* is penalized immediately (estimate jumps to the slow RTT), but a recovered provider only earns back traffic gradually as the EWMA decays over `decay_ns=30s` (`next = old·e^(−Δ/30s) + observed·(1−e^(−Δ/30s))`). New endpoints seed at `default_rtt=250ms`. The `× (pending+1)` term — where `pending` is the live in-flight-handle count (`Arc::strong_count − 1`) — makes a provider with many outstanding requests look proportionally worse at equal RTT, so load spreads *before* latency visibly degrades. A handle drops (and triggers the update) when its response completes (`CompleteOnResponse`).

**The P2C step itself** (stock Tower `p2c`): pick two distinct endpoints uniformly at random, call `.load()` on each (the PeakEWMA cost above), route to the **lower** cost. **Tie-break:** if only one endpoint is ready, use it (no random pick); with `len==1`, index 0. P2C avoids the herd-behavior failure mode of "always route to the globally-least-loaded endpoint" (which causes all concurrent deciders to stampede the same node before its load metric updates).

**Why P2C over global-min:** with N deciders and 1 shared min, every decider sends to the same node in the window before its load updates → thundering herd. With P2C, the probability any single node is the worse-of-2 for *all* deciders collapses geometrically. This is the textbook Mitzenmacher result and is exactly why Bifrost (researchfms `BIFROST.md`) also chose P2C.

### Reimplementation — P2C + PeakEWMA in ~40 lines (DESIGNED, from the KNOWN math above)

The quality bar for this teardown: a senior engineer can reimplement P2C+PeakEWMA from the section. Here it is (Python):

```python
import math, random, time

class PeakEwmaEndpoint:
    def __init__(self, default_rtt=0.250, decay=30.0):   # seconds — Helicone's 250ms / 30s
        self.rtt = default_rtt; self.decay = decay
        self.update_at = time.monotonic(); self.pending = 0

    def load(self):                                       # cost = decayed_rtt * (pending + 1)
        return self._decayed() * (self.pending + 1)

    def _decayed(self):                                   # lazy decay toward 0 since last update
        now = time.monotonic(); d = math.exp(-(now - self.update_at) / self.decay)
        self.rtt *= d; self.update_at = now; return self.rtt

    def on_complete(self, observed_rtt):                  # call when a request finishes
        now = time.monotonic()
        if self.rtt < observed_rtt:
            self.rtt = observed_rtt                        # PEAK: jump up instantly
        else:
            d = math.exp(-(now - self.update_at) / self.decay)
            self.rtt = self.rtt * d + observed_rtt * (1 - d)   # EWMA: decay down toward observed
        self.update_at = now

def p2c_pick(endpoints):                                  # Power-of-Two-Choices
    ready = [e for e in endpoints if e.healthy]           # health monitor evicts unhealthy (out of band)
    if len(ready) <= 1: return ready[0] if ready else None
    a, b = random.sample(ready, 2)                        # two distinct at random
    return a if a.load() <= b.load() else b               # route to lower cost (tie → a)
```

`pending` is incremented on dispatch, decremented (and `on_complete` called with the measured RTT) when the response returns. This is the entire latency LB.

### The Custom Weighted Balancer (KNOWN — `crates/weighted-balance/src/`)

For canary/weight routing Helicone forked Tower's balancer (copyright header preserved, `balance/mod.rs:1-25`) into `WeightedBalance`. The selection is **weighted reservoir sampling**, NOT P2C:

```rust
// balance/mod.rs:192-220  ready_index()
match self.services.ready_len() {
    0 => Ok(None),
    1 => Ok(Some(0)),                      // single ready → take it
    len => {
        let sample_fn = |idx| {            // weight of endpoint at ready-index idx
            let (key, _svc) = self.services.get_ready_index(idx).expect("invalid index");
            key.weight()                   // Weight(u32)
        };
        // rand::seq::index::sample_weighted — O(n), pick 1 by weight
        let sample = rand::seq::index::sample_weighted(&mut self.rng, len, sample_fn, 1)?;
        Ok(Some(sample.index(0)))
    }
}
```

`Weight` (`weight.rs:27-43`) is a fixed-point integer so it can be `Hash + Eq`:

```rust
pub struct Weight(u32);
impl Weight {
    pub const MIN:  Weight = Weight(0);        // 0.0 → never selected
    pub const UNIT: Weight = Weight(10_000);   // 1.0 == 10_000 internal units
    pub const MAX:  Weight = Weight(u32::MAX); // +∞
}
// From<f64>: w<0 or NaN → MIN; w==∞ → MAX; else round(w * 10_000)
// f64::div(Weight::MIN) → INFINITY  (so a 0-weight endpoint has infinite "cost")
```

`SmallRng` seeded once per balancer (`balance/mod.rs:109`). The `ready_index` is **sticky between `poll_ready` and `call`**: once selected in `poll_ready`, the chosen endpoint is re-checked for readiness on the next `poll_ready`; if it fell out of the ready set (e.g. health monitor evicted it), a new one is sampled (`balance/mod.rs:248-283`). This is the same "select-then-confirm-ready" discipline Tower uses to avoid dispatching to a stale endpoint.

### The Tower Service Stack — Exact Layer Order (KNOWN — `ai-gateway/src/router/service.rs:74-83`)

This is the single most reusable artifact for Verso. The router builds **one stack per `EndpointType`** (chat, embeddings, …), composing layers outside-in:

```rust
let service_stack = ServiceBuilder::new()
    .layer(ErrorHandlerLayer::new(app_state.clone()))      // 1. outermost — catches everything below
    .layer(prompt_layer.clone())                           // 2. prompt templating (Helicone prompts)
    .layer(cache_layer.clone())                            // 3. cache: return early on hit (no LB call)
    .layer(ErrorHandlerLayer::new(app_state.clone()))      // 4. SECOND error handler — see note
    .layer(rl_layer.clone())                               // 5. rate limit (GCRA / tower_governor)
    .map_err(|e| ApiError::from(InternalError::BufferError(e)))
    .layer(buffer::BufferLayer::new(MIDDLEWARE_BUFFER_SIZE))// 6. buffer: make the inner stack Clone+multi-task
    .layer(request_context_layer.clone())                  // 7. attach request context (model id, org, …)
    .service(routing_strategy);                            // 8. innermost — P2C/weighted/latency balancer
```

Layer-order lessons for Verso:
- **Cache is ABOVE the rate-limiter and balancer.** A cache hit returns before any quota is consumed or any provider is selected — caching is free of rate-limit and load-balancer cost. (Contrast: if you put cache *below* rate-limit, cache hits still burn quota.)
- **Two `ErrorHandlerLayer`s** — one outermost (catches prompt/cache errors and normalizes them to the OpenAI error envelope) and one just above rate-limit (so a rate-limit rejection is shaped into the OpenAI error body, `config/rate_limit.rs:59-110`, `type:"rate_limit_exceeded"`).
- **`BufferLayer` sits directly above the balancer.** Tower balancers are `&mut self` in `poll_ready` (they own the RNG and the ready-cache), so they are not `Clone`; `Buffer` turns the non-clonable balancer into a clonable, multi-task front by funneling calls through an mpsc channel. `MIDDLEWARE_BUFFER_SIZE` is the channel capacity.
- **`request_context` is innermost-but-one** — the balancer needs the parsed model id (in request extensions) to do `ModelLatency` exact-model selection, so context attachment must happen before the balancer's `call`.

### Rate Limiting — GCRA, NOT token/dollar in OSS (KNOWN — `ai-gateway/src/config/rate_limit.rs`)

[CORRECTION 2026-06-05] The targets brief says Helicone rate-limits "by requests, tokens, or dollars." In the **open-source** gateway the hot-path limiter is **GCRA request-rate limiting only**, via `tower_governor` (`rate_limit.rs:21-24, 39-115`). Token-count and dollar-amount limiting are Helicone *cloud* features, not in this repo's request path. The OSS config:

```rust
pub struct GcraConfig {
    pub refill_frequency: Duration,  // default 1s — time to refill the whole quota
    pub capacity: NonZeroU32,        // default 500 — burst size
}
// per-cell period = refill_frequency / capacity  (rate_limit.rs:43-52)
// → GovernorConfigBuilder.period(per_cell).burst_size(capacity)
```

GCRA = Generic Cell Rate Algorithm (a leaky-bucket variant): `period = refill_frequency / capacity` is the time to regenerate one cell; `burst_size = capacity` is how many cells can accumulate. Key extracted per API key (`RateLimitKeyExtractor`). Store is `InMemory` (default) or `Redis` (`rate_limit.rs:121-125`) — Redis store lets the limit be shared across gateway replicas. On exceed → HTTP 429 with OpenAI-shaped body `{"error":{"message":"Too many requests","type":"rate_limit_exceeded"}}`.

### Provider/Model Registry — Capability via the Mapping (KNOWN — `config/embedded/providers.yaml`, `model-mapping.yaml`)

`providers.yaml` (155 lines) is a flat registry: per provider, a `models` list + `base-url` + optional `version`. There are **no per-model capability flags** (no `supports_tools`, `supports_streaming`) — capability is implicit in the model-mapping. Providers present: `openai`, `anthropic` (`version: "2023-06-01"`), `gemini`, `mistral`, `groq`, `deepseek`, `xai`, `hyperbolic`, `ollama` (`http://localhost:11434/`), `bedrock` (region-pinned URL).

`model-mapping.yaml` (894 lines) is the **equivalence table** that powers cross-provider failover. Each canonical model maps to an *ordered list of fallback equivalents on other providers*:

```yaml
gpt-4:
  - "anthropic/claude-3-7-sonnet"
  - "gemini/gemini-2.5-pro"
  - "ollama/deepseek-r1"
  - "mistral/mistral-large"
  - "xai/grok-3"
  - "groq/llama-3.3-70b-versatile"
  - "bedrock/us.deepseek.r1-v1:0"
  - "deepseek/deepseek-chat"
gpt-4o-mini:
  - "anthropic/claude-3-5-haiku"
  - "gemini/gemini-2.0-flash"
  - "mistral/mistral-small"     # small request → small equivalents
  - "groq/llama-3.1-8b-instant"
```

This is the mechanism behind strategy step 4 ("if the P2C-winning provider lacks the requested model, map it to a model offered by that provider"). The mapping is **tiered by capability class** — `gpt-4` maps to large models, `gpt-4o-mini` maps to small/fast ones — so a latency-routed request to a different provider still lands on a same-class model.

### Cache Key Generation — Multi-Bucket FxHash (KNOWN — `middleware/cache/service.rs:507-627`)

```rust
fn get_hasher(parts: &Parts, body: &Bytes, seed: Option<&str>) -> FxHasher {
    let mut hasher = FxHasher::default();
    if let Some(s) = seed { s.hash(&mut hasher); }            // optional cache-namespace seed
    if let Some(pq) = parts.uri.path_and_query() { pq.hash(&mut hasher); }
    body.hash(&mut hasher);                                   // FULL request body in the key
    hasher
}
```

Key = `FxHash(seed ++ path_and_query ++ body) ++ bucket_index`. Cache supports **N buckets** (`CacheConfig.buckets`, default `1`, max `MAX_BUCKET_SIZE=10`, `config/cache.rs:3-4`). On lookup, all buckets are probed **in parallel** (`FuturesUnordered`, `service.rs:511-540`) with bucket order shuffled for fairness; first Fresh hit wins. On full miss, pick the first empty bucket (or `rand % buckets`) and store there. Multiple buckets let identical requests hold *different cached responses* — useful for non-deterministic LLM output where you want cache hits but also response variety. Store backends (`config/cache.rs:31-58`): `InMemory{max_size: 256MB}` or `Redis`. This is a **exact-match** cache (body byte-equal), not semantic — contrast LiteLLM's embedding-based `RedisSemanticCache` (see `infra-model-routing.md`).

### Retry Middleware — backon Backoff (KNOWN — `ai-gateway/src/config/retry.rs`)

Retries are a Tower layer driven by a `backon` backoff iterator, configured as a discriminated enum:

```rust
pub enum RetryConfig {
    Exponential { min_delay: 1s, max_delay: 30s, max_retries: 2, factor: 2.0 },  // + with_jitter()
    Constant    { delay: 1s, max_retries: 2 },
}
const DEFAULT_RETRY_FACTOR: f32 = 2.0;
```

`as_iterator()` yields the delay sequence: exponential = `ExponentialBuilder.with_min_delay(1s).with_max_delay(30s).with_max_times(2).with_factor(2.0).with_jitter()` (jitter on by default — avoids retry-storm synchronization); constant = fixed `delay` × `max_retries`. Defaults: 2 retries, 1s→30s exponential, factor 2. This is the per-request retry; it composes *inside* the load balancer (a retry re-runs `poll_ready`, which can pick a *different* P2C endpoint on the retry — retry + rebalance in one).

### The Dynamic-Router Crate — Keyed Sub-Router Dispatch (KNOWN — `crates/dynamic-router/src/router/mod.rs`)

A third routing crate (also forked from Tower, copyright preserved): `DynamicRouter` dispatches to a *named sub-router* selected by a `Key` extension on the request (`RouterNotFound(String)` error if the key has no router). Where `LatencyRouter`/`WeightedBalance` pick an *endpoint*, `DynamicRouter` picks a whole *routing strategy instance* by key — this is how Helicone supports many independently-configured routers (different model pools, strategies, rate limits) behind one gateway process, selected per request. Verso's analogue: a top-level router keyed on agent-role that dispatches to per-role `ProviderEdge` configs.

### Health & Rate-Limit Monitors — Rolling Counter (KNOWN — `metrics/rolling_counter.rs`)

Provider health is a `RollingCounter` (`rolling_counter.rs:6-40`): `buckets` `AtomicU32` counters over a `window`, each bucket = `window / buckets` seconds, with a `laps` array (`AtomicU64`) so stale buckets from a previous lap are zeroed lazily. The health monitor and rate-limit monitor feed `Change::Insert`/`Change::Remove` events into the balancer's `Discover` stream (`balance/mod.rs:140-163`), so an unhealthy provider is *evicted from the ready set* rather than penalized — the balancer simply never sees it until it recovers and is re-inserted. This is cleaner than a "cooldown timer" (cf. LiteLLM's `DEFAULT_COOLDOWN_TIME_SECONDS=5`): eviction is driven by an out-of-band monitor, not by inline failure counting in the request path.

### For Verso

- **Adopt PeakEWMA-P2C as the default latency strategy for Verso's `ProviderEdge`.** The exact recipe is small: per-provider keep `rtt_estimate` (seed 250ms) and `outstanding` count; `load = rtt_estimate * (outstanding+1)`; update RTT asymmetrically (jump up on a slower observation, decay down with `exp(-Δ/30s)`); on each call pick 2 providers at random, route to lower load. ~80 lines of Python. This is strictly better than round-robin or global-least-loaded for a multi-provider edge under concurrency.
- **The asymmetric "peak" update is the key insight** — react to slowdowns instantly, recover trust slowly. A naive symmetric EWMA lets a provider that briefly recovered get instantly stampeded. Verso should copy the up-fast/down-slow asymmetry verbatim.
- **Copy the Tower layer order conceptually:** error-normalize (outer) → cache (return before quota/LB) → rate-limit → buffer → context → balancer (inner). In Verso terms: the context-budget guard and cache check belong *above* the load balancer; a cache hit must not consume run-budget. (Verso's tactical↔durable seam maps cleanly: cache+budget are durable-layer concerns checked before the tactical provider call.)
- **Model-equivalence mapping for cross-provider failover.** When Verso fails over `gpt-4` → another provider, it must land on a *same-capability-class* model. A static `model-mapping.yaml`-style table (large→large, small→small), tiered by class, is the right artifact — not "fall back to whatever's cheapest."
- **Health via out-of-band eviction, not inline cooldown.** A background monitor that inserts/removes providers from the candidate set keeps the hot path free of failure-counting logic. This is cleaner than LiteLLM's inline cooldown handler for Verso's edge.
- **Exact-match cache with optional buckets** is the cheap default; reserve semantic cache (embedding lookup) for a later tier. The full-body FxHash key + N-bucket parallel probe is ~40 lines.
- **GCRA for request-rate, separate token/cost guard for budgets.** Helicone separates request-rate (GCRA) from token/dollar budget (cloud-only). Verso should keep these as two distinct guards: a fast GCRA request limiter on the edge, and a token/cost budget guard in the context layer (see Cloudflare Budget Limit and Envoy token-rate-limit below for the budget side).

---

## Not Diamond — RoRF + IRT-Router (learned routing)

### What It Is

Not Diamond is the **learned-classifier** answer to "how do you write `route(context) -> ModelSpec` that isn't round-robin or latency-sort?" It powers OpenRouter's `openrouter/auto` (cross-ref `infra-model-routing.md` §Auto-routing). Two open-source artifacts give the full algorithm:

1. **RoRF** (Routing on Random Forests) — `Not-Diamond/RoRF`. Embed the prompt → a `sklearn.RandomForestClassifier` predicts which of two models (a *pair*: usually strong vs weak) will produce the better answer → a `threshold` knob slides the cost/quality tradeoff. This is what runs locally; 12 pre-trained routers on HF.
2. **IRT-Router** (ACL 2025, arXiv `2506.01048`) — a multi-LLM router built on psychometric Item Response Theory: each LLM gets a latent **ability vector**, each query gets **difficulty + discrimination** parameters, and routing predicts P(model answers correctly) across N candidates. Adds **online warm-up** for unseen queries via kNN embedding interpolation.

The live API (`notdiamond-python`) is a closed superset of RoRF.

### RoRF — The Exact `route()` Path (KNOWN — `rorf/controller.py`, `rorf/router/`)

**The pipeline (`controller.py:81-104`):**

```python
def route(self, prompt) -> str:
    recommended_model, _, _ = self.predict_proba(prompt)
    return recommended_model

def predict_proba(self, prompt):
    if isinstance(prompt, str):
        prompt_embedding = self.embedding_model.get_prompt_embeddings([prompt])  # 1×D vector
    else:
        prompt_embedding = prompt
    label_scores = self.router_model.predict_proba(prompt_embedding)[0]   # 4-class RF → 4 probs
    model_a_prob = label_scores[0] + label_scores[1]   # P(A wins) + P(NO_MODEL / both-fail)
    model_b_prob = label_scores[2] + label_scores[3]   # P(BOTH win)  + P(B wins)
    if model_a_prob >= self.threshold:                 # threshold ∈ [0,1]
        recommended_model = self.model_a               # usually the STRONGER/pricier model
    else:
        recommended_model = self.model_b               # weaker/cheaper
    return recommended_model, model_a_prob, model_b_prob
```

**The feature vector IS the raw embedding.** There is no hand-crafted feature engineering — `get_features` (`dataloader.py:79`) sets `features = prompt_embeddings[prompt_i]` directly. The RF eats the full embedding (1024-dim for jina-v3, 1024 for voyage-large-2, 1536 for OpenAI text-embedding-3-small).

**The 4-class label scheme (KNOWN — `dataloader.py:60-81`)** — this is the non-obvious core. Training data has a per-model `{model}/score`. For each prompt the label is:

```python
if   model_a_score >  model_b_score: label = 0   # A strictly better
elif model_a_score == model_b_score:
     if model_a_score == 0:          label = 1    # NO_MODEL  (both scored 0 — both failed)
     else:                           label = 2    # BOTH_MODEL (both scored equal & nonzero — both succeeded)
else:                                label = 3    # B strictly better
```

So the RF is a **4-way classifier over {A-wins, both-fail, both-win, B-wins}**, and `predict_proba` collapses it: `model_a_prob = P(0)+P(1)`, `model_b_prob = P(2)+P(3)`. The intuition baked into the grouping: send to A (strong) when A wins *or when both fail* (give the strong model the hard one); send to B (cheap) when both succeed *or B wins* (don't pay for the strong model on easy queries). This grouping is the entire routing policy — memorize it.

**Embedding pipeline — jina vs voyage vs openai (KNOWN — `embeddings.py`):**

| Provider | Model | How | Notable |
|---|---|---|---|
| `jina` | `jinaai/jina-embeddings-v3` | LOCAL via `AutoModel.from_pretrained(trust_remote_code=True)`; `.encode(prompts, task="classification")` | free, no API; the **`task="classification"` adapter** matters — jina-v3 has task-specific LoRA adapters |
| `voyage` | `voyage-large-2-instruct` | Voyage API, `batch_size=128`; **prepends `"Cluster the text: "`** to every prompt | the instruct-prefix is load-bearing for this model |
| `openai` | `text-embedding-3-small` | OpenAI API, `batch_size=2048`; strips `\n`, `<|endoftext|>`; truncates to **8150 tokens** (`cl100k_base`) | |

Router-name parsing (`controller.py:55-66`): `rorf-<embed>-<model_a>-<model_b>` → split on `/` then `-`; `method` must be `rorf`, `embed` ∈ {jina, voyage, openai}. The classifier ships as `classifier.pkl` (pickled `RandomForestClassifier`), pulled from HF via `hf_hub_download(repo_id, "classifier.pkl")` or read locally (`controller.py:106-124`).

**RF hyperparameters (KNOWN — `trainer.py:29-33`, `rorf.py:89-95`):**

```python
RandomForestClassifier(
    max_depth=20,        # default
    max_features=1.0,    # use ALL embedding dims at each split
    n_estimators=100,    # default
    n_jobs=-1,
    random_state=420,
)
```

### Pre-Trained Routers + Two Routing Modes (KNOWN — README, `controller.py:106-124`)

12 pre-trained routers ship on HF as `classifier.pkl` + `config.json`, across **6 model pairs × 2 embedders** (jina/voyage). The pairs reveal the two distinct use cases (README's two findings):

- **Strong↔weak** (cost reduction, same quality): `rorf-jina-llama31405b-llama3170b`, `rorf-jina-gpt4o-gpt4omini`, `rorf-jina-llama31405b-claude35sonnet`, `…-gpt4o`, `…-mistrallarge` → route the easy queries to the cheap model, hard ones to the strong model; *"reduce costs while maintaining the strong model's performance."*
- **Strong↔strong** (quality gain): `rorf-jina-claude35sonnet-gpt4o` → route each query to whichever strong model is better *for that query*; *"reduce costs while **outperforming both** individual models."* This is the non-obvious one — a router over two peers beats either alone because no single model dominates across all query types.

The model format is just a pickled `sklearn.RandomForestClassifier` (~MB) + a `config.json` recording `{llms, embedding_provider, max_depth, n_estimators, …}`. Loadable from local path or `hf_hub_download` (`controller.py:113-124`). `batch_calculate_win_rate` (`controller.py:68-79`) embeds all prompts once, then runs `predict_proba` per prompt to get each prompt's `model_a_prob` — used by threshold calibration and for bulk analysis.

### Threshold Calibration — Quantile of Win-Rates (KNOWN — `calibrate_threshold.py`)

The `threshold` is not guessed; it's **calibrated to hit a target % of calls to model A** on YOUR data, in two steps:

```python
# Step "generate": run the router over a calibration set, store each prompt's model_a_prob
win_rates = controller.batch_calculate_win_rate(calibration_df["Input"].tolist())
calibration_df[router] = win_rates  # push to HF as "<dataset>-rorf-thresholds"

# Step "calibrate": pick the threshold as the (1 - target_pct) quantile of win-rates
threshold = thresholds_df[router].quantile(q=1 - args.model_a_pct)
# e.g. want 50% of calls to A → threshold = median win-rate;
#      want 20% to A → threshold = 80th-percentile win-rate (only the top-20%-confident queries go to A)
```

This is the directly-applicable Verso knob: a single scalar that slides cost↔quality, set empirically so a known fraction of traffic hits the expensive model.

### Live API — `/v2/modelRouter/modelSelect` (KNOWN — `notdiamond-python/llms/request.py:54-78`)

The hosted router is a strict superset of RoRF — it routes over N (not 2) models and accepts a richer payload:

```python
url = f"{nd_api_url}/v2/modelRouter/modelSelect"   # nd_api_url = https://api.notdiamond.ai
payload = {
    "messages": [...],                              # full chat history (the routing input)
    "llm_providers": [cfg.prepare_for_request() ...],# candidate pool: [{provider, model}, ...]
    "metric": metric.metric,                        # only "accuracy" supported in SDK
    "max_model_depth": int,                         # how far down the ranking to fall if top model is DOWN
    "hash_content": bool,                           # hash prompt before sending (privacy)
    # optional:
    "tools": [{"type":"function","function":{...}}],# OpenAI tool format → routing considers tool support
    "tradeoff": "cost" | "latency",                 # bias the ranking
    "preference_id": str,                           # dashboard-configured routing preference
    "previous_session": str,                        # link requests (multi-turn continuity)
}
```

Response parse (`request.py:106-120`): `{"providers": [{provider, model}, ...], "session_id": ...}` — `providers[0]` is the pick; the ordered list IS the fallback chain up to `max_model_depth`. Feedback loop closes via `POST /v2/report/metrics/feedback` (`metrics/request.py:24`) with `{session_id, provider, feedback: {<metric>: int}}` — this is how online routing improves: the router's quality signal comes from posted feedback keyed by `session_id`, the same id returned at route time. `model_select` defaults: `timeout=60`, `max_retries=3` (client retries the *route* call with a plain `for n_retry in range(1, max_retries+1)` loop, `request.py:190-204` — no backoff; returns `(None, "NO-SESSION-ID")` on final failure).

**The candidate-pool schema (KNOWN — `notdiamond-python/llms/config.py:176-184`)** — each candidate the client sends carries cost/latency/context hints the server-side router uses:

```python
def prepare_for_request(self):   # one entry in llm_providers[]
    return { "provider": self.provider, "model": self.model, "is_custom": self.is_custom,
             "context_length": self.context_length,        # tokens — lets router exclude models that can't fit
             "input_price": self.input_price,              # $/token (else default from settings.PROVIDERS[provider]["price"])
             "output_price": self.output_price,
             "latency": self.latency }                     # observed/expected latency hint
```

`LLMConfig` (`config.py:67-184`) is the candidate type: `{provider, model, system_prompt?, context_length?, input_price?, output_price?, latency?, api_key?, openrouter_model}`. Custom prices/latency override the built-in `settings.PROVIDERS[provider]["price"][model]` table. `__hash__`/`__eq__` key on `provider/model` only. `from_string("openai/gpt-4o-mini")` parses the same `{provider}/{model}` slug Cloudflare/Helicone use. So the server router is told, per candidate: capability (context window), cost (input/output price), and a latency prior — exactly the inputs a cost/quality/latency router needs, with `tradeoff:"cost"|"latency"` biasing the objective. The SDK enumerates a large built-in pool (`NDLLMProviders` enum, `providers.py` — OpenAI gpt-3.5→4.1-nano, Anthropic claude-3→sonnet-4.5, Mistral, Google, Replicate, …) so the router can pick across providers, but custom `LLMConfig`s let you supply your own pool with your own prices.

### IRT-Router — Psychometric Routing (KNOWN from arXiv `2506.01048`)

Where RoRF is pairwise, IRT-Router scales to N models by borrowing Item Response Theory (the same math used to score standardized tests). **MIRT** (multidimensional IRT) predicts whether LLM `Mⱼ` answers query `qᵢ` correctly:

```
P̂(qᵢ, Mⱼ) = σ( aᵢᵀ · θ_Mⱼ − bᵢ )            # σ = logistic sigmoid
  θ_Mⱼ ∈ ℝᴺ   latent ABILITY vector of model j   = Wθ · e_Mⱼ
  aᵢ   ∈ ℝᴺ   DISCRIMINATION vector of query i   = Wa · e_qᵢ   (how much each ability dim matters)
  bᵢ   ∈ ℝ    DIFFICULTY scalar of query i        = Wb · e_qᵢ
```

Each `θ, a, b` is a learned linear projection (`W·e`) of the model embedding `e_Mⱼ` / query embedding `e_qᵢ`. **NIRT** (neural variant) adds a relevance gate and an MLP interaction:

```
xᵢⱼ = r_qᵢ ⊙ (θ_Mⱼ − bᵢ) × aᵢ              # r_qᵢ = binary relevance vector from UMAP/HDBSCAN clustering
P̂(qᵢ, Mⱼ) = σ( φ( W₁ · xᵢⱼ + b₁ ) )         # φ = neural interaction layer
```

**Online query warm-up (the directly-applicable cold-start fix):** for an unseen test query, blend its embedding with the average embedding of its k nearest *training* queries before projecting:

```
e_qᵢ ← (1 − λ)·e_qᵢ + λ·e_qᵢ^warm        # e_qᵢ^warm = mean embedding of k-NN training queries
                                          # k = 5;  λ tuned (sensitivity in paper App. B)
```

This regularizes a novel query toward the parameter region the IRT model was actually trained on — without retraining. **Constants (KNOWN):** embedding = `bert-base-uncased` (768-d); latent dim `N = 25`; k = 5; Adam `lr=0.002`, batch 512; trained on 488,600 (query, model) interaction tuples (24,430 queries × 20 LLMs). **Numbers:** MIRT-Router ID 80.67% acc at $0.42 vs GPT-4o-only 77.53% at $12.93 (≈30× cheaper, higher accuracy); OOD 87.12% at $0.14 beating RouterBench's 85.50% at $0.26.

### Reimplementation — RoRF route() from scratch (DESIGNED, from the KNOWN source above)

A senior engineer can rebuild the whole RoRF router in ~25 lines (this is the proof the teardown is deep enough):

```python
import pickle, numpy as np
from transformers import AutoModel   # jina-v3 local, keyless

class VersoRoRF:
    def __init__(self, classifier_pkl, model_a, model_b, threshold):
        self.rf = pickle.load(open(classifier_pkl, "rb"))      # sklearn RandomForestClassifier (4-class)
        self.embed = AutoModel.from_pretrained("jinaai/jina-embeddings-v3", trust_remote_code=True)
        self.model_a, self.model_b, self.threshold = model_a, model_b, threshold

    def route(self, prompt: str) -> str:
        e = np.asarray(self.embed.encode([prompt], task="classification"))   # 1×D, the FEATURE vector
        p = self.rf.predict_proba(e)[0]                          # [P(A-wins), P(both-fail), P(both-win), P(B-wins)]
        model_a_prob = p[0] + p[1]                               # A-wins OR both-fail → give A the hard ones
        return self.model_a if model_a_prob >= self.threshold else self.model_b

    @staticmethod
    def calibrate(win_rates, target_a_pct):                      # set threshold to hit a target A-fraction
        return float(np.quantile(win_rates, q=1 - target_a_pct))
```

Training (for a custom pair): label each (prompt) by the 4-class scheme (`A>B→0`, `A==B==0→1`, `A==B>0→2`, `A<B→3`) over your eval scores, embed prompts, fit `RandomForestClassifier(max_depth=20, max_features=1.0, n_estimators=100, random_state=420)`. That's the entire system.

### For Verso

- **A learned `route()` is a small, swappable strategy.** RoRF proves the whole thing is: `embed(prompt) → RF.predict_proba → group 4 classes into A/B → compare to threshold`. Verso's `route(context) -> ModelSpec` interface should default to config rules but accept a pickled classifier as a drop-in. The classifier is ~5 MB, runs in <1 ms, needs no GPU.
- **The 4-class label grouping is the routing policy** — copy it verbatim for a strong/weak pair: route to strong when `P(A-wins)+P(both-fail) ≥ threshold`. The "both-fail → send to strong" logic is the non-obvious part most hand-rolled routers miss.
- **`threshold = quantile(win_rates, 1 - target_A_pct)`** is exactly the cost/quality knob Verso's model-edge should expose: one scalar, calibrated on the team's own traffic to guarantee a fixed fraction of calls hit the expensive model. This maps directly to Verso's per-node `ModelPolicy`.
- **Jina-v3 local embeddings = free, keyless routing.** For Verso's keyless/local ethos (cf. the user's bad-research keyless re-arch), `jina-embeddings-v3` with `task="classification"` runs locally with no API key — the router classifier needs only this one embedding call per route decision. Prefer it over voyage/openai for a self-hosted Verso edge.
- **IRT-Router's online warm-up bootstraps Verso's eval harness.** A new agent task type (unseen query) can be routed immediately by interpolating toward the k=5 nearest *evaluated* tasks (`e ← 0.5·e + 0.5·e_warm`) — no retraining, directly applicable to Verso bootstrapping routing before its eval corpus is large. The latent-ability formulation (`σ(aᵀθ − b)`) is also a clean way to model "this agent role is good at hard-reasoning tasks but weak at tool-formatting" as a per-role ability vector.
- **Route over the message history, accept `tools` + `tradeoff` + `previous_session`.** The live `modelSelect` schema is the right shape for a Verso router primitive: route on full context (not just last turn), let `tools` presence bias toward tool-capable models, let `previous_session` pin multi-turn continuity, return the *ranked* list as the fallback chain (`max_model_depth`-deep). Close the loop with a `feedback(session_id, metric)` call so routing quality is learned from Verso's own eval signal.

---

## Cloudflare AI Gateway — Dynamic Routes (the routing DSL)

### What It Is

Cloudflare's managed gateway runs on Workers. The 2025 refresh added **Dynamic Routes**: a directed-graph routing DSL where a request flows through typed nodes (Start → Conditional/Percentage/Limit → Model → End) until it hits a Model node that calls a provider. This is the **most concrete public spec for a routing DSL** and maps almost 1:1 onto what Verso's model-provider edge needs. Closed source, but the route schema is fully documented + the API is probeable. Cross-ref: this is the visual/declarative encoding of the same semantics Portkey's `ConditionalRouter` expresses imperatively (researchfms `PORTKEY.md`).

### The Route Graph JSON Schema (KNOWN — Cloudflare API `dynamic_routing` resource + JSON-config docs)

A route is a flat list of `elements` (nodes) wired by `elementId` references in each node's `outputs`:

```jsonc
{
  "id": "<route id>",
  "name": "<route name>",
  "elements": [ /* nodes, each with id, type, properties?, outputs */ ]
}
```

Node (element) shape: `{ id, type, properties?, outputs }`. The node types (KNOWN — API schema):

| `type` | Purpose | `properties` | `outputs` |
|---|---|---|---|
| `start` | entry point (exactly one) | — | `next: {elementId}` |
| `conditional` | if/else branch | `conditions` (MongoDB-style expr, below) | `true: {elementId}`, `false: {elementId}` |
| `percentage` | probabilistic A/B split, ≤5 outputs | — | `Record<"NN%", {elementId}>` — keys must **sum to 100** |
| `rate` (a.k.a. Limit) | quota guard, **count OR cost** | `key`, `limit`, `limitType: "count"\|"cost"`, `window` | `success: {elementId}`, `fallback: {elementId}` |
| `model` (Inference) | call a provider/model | `provider`, `model`, `timeout` (ms), `retries` | `success: {elementId}`, `fallback: {elementId}` |
| `end` | terminate, return response/error | — | `{}` (empty) |

**The key architectural reveal: Rate Limit and Budget Limit are the SAME node type** (`rate` / Limit), discriminated by `limitType`. `"count"` = request-count quota (classic rate limit); `"cost"` = dollar-budget quota (Budget Limit). Both share the identical config surface — `key` (what to bucket by), `limit` (the cap), `window` (seconds), and the **same `success`/`fallback` edge pair**. When the quota is *not* exceeded → `success` edge (proceed to the model); when exceeded → `fallback` edge (route to a cheaper model or `end`). This is a *soft, graceful* budget guard: exceeding the budget does **not** error — it reroutes down the `fallback` branch.

### The Conditional Node — MongoDB-Style Operators (KNOWN — JSON-config docs)

Conditions reference three field namespaces — **request body**, **headers**, and **metadata** (arbitrary key-value context the app attaches per request: `userId`, `orgId`, `plan`, …) — using a MongoDB-query operator grammar:

```jsonc
{
  "id": "cond-1",
  "type": "conditional",
  "properties": {
    "conditions": { "metadata.plan": { "$eq": "free" } }   // single comparison
  },
  "outputs": { "true": {"elementId": "cheap-model"}, "false": {"elementId": "premium-model"} }
}
```

Operators (KNOWN): `$eq`, `$ne`, `$in`, plus the boolean combinators `$and`, `$or` for nesting. Field paths are dotted (`metadata.plan`, `body.<json-path>`, header refs). So a routing rule reads almost exactly like the Verso use case from the targets brief:

```jsonc
// "if agent_type == 'planner' AND token_budget > 5000 → opus, else haiku"
{ "$and": [ { "metadata.agent_type": { "$eq": "planner" } },
            { "metadata.token_budget": { "$gt": 5000 } } ] }
// ($gt available alongside $eq/$ne/$in for numeric comparisons)
```

### `/compat` — Provider Normalization (KNOWN — live probe + docs)

The OpenAI-compatible endpoint normalizes one request shape across all providers:

```
POST https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/compat/chat/completions
body: { "model": "{provider}/{model}", "messages": [...] }    // e.g. "anthropic/claude-sonnet-4-5", "openai/gpt-5.2"
```

The provider is encoded as a `{provider}/{model}` prefix inside the standard OpenAI body — the gateway strips the prefix, looks up the provider, and translates the OpenAI request into that provider's native dialect (same normalization job as LiteLLM's `Config.transform_request`, cf. `infra-model-routing.md`). **Live probe (KNOWN, 2026-06-05):** unauthenticated `POST .../compat/chat/completions` returns a structured `AiGatewayError` envelope, not a generic 401 page:

```json
{"success":false,"result":[],"messages":[],"error":[{"code":2009,"message":"Unauthorized"}],
 "name":"AiGatewayError","httpCode":401,"internalCode":2009,"message":"Unauthorized","description":"Unauthorized"}
```

Note `internalCode:2009` — the gateway carries an internal error-code taxonomy distinct from HTTP status (same pattern vLLM uses: status-in-body); confirmed identical on both `/compat/chat/completions` and the Universal Endpoint. 2026 added **Unified Billing**: third-party model spend (OpenAI etc.) billed through the Cloudflare invoice + a transaction fee — which is what makes the `cost`-type Limit node enforceable (Cloudflare sees the real per-request cost because it brokers payment).

### The Universal Endpoint — Array-of-Providers Fallback (KNOWN — docs + live probe)

Before Dynamic Routes, Cloudflare's fallback primitive was the **Universal Endpoint**: `POST .../v1/{account_id}/{gateway_id}` with a request body that is an **ordered array** of provider configs, tried in sequence until one succeeds:

```jsonc
[
  { "provider": "openai", "endpoint": "chat/completions",
    "headers": { "Authorization": "Bearer ...", "Content-Type": "application/json" },
    "query": { "model": "gpt-4o-mini", "messages": [...] },
    "config": { "requestTimeout": 2000, "maxAttempts": 2, "retryDelay": 500, "backoff": "exponential" } },
  { "provider": "anthropic", "endpoint": "v1/messages", "headers": {...}, "query": {...} }   // fallback
]
```

`cf-aig-step` response header reports which array index served (0 = first, 1 = first-fallback, …) — the same role as Vercel's `modelAttempts` audit. Per-element `config` overrides timeout/retry/backoff. This is the imperative twin of a Dynamic Route's `model.fallback` edges, and a clean public spec for an inline fallback chain.

### `cf-aig-*` Control Headers (KNOWN — request-handling + caching docs)

The gateway is steered entirely by request headers (no SDK needed) — the reusable control surface:

| Header | Purpose | Constraints |
|---|---|---|
| `cf-aig-request-timeout` | per-request timeout (ms); timed from *first* response byte | — |
| `cf-aig-max-attempts` | retry count | max **5** |
| `cf-aig-retry-delay` | retry delay (ms) | max **5000ms** |
| `cf-aig-backoff` | `constant` \| `linear` \| `exponential` | final retry waits for full completion regardless |
| `cf-aig-cache-ttl` | cache duration (s) | min **60s**, max **1 month** |
| `cf-aig-skip-cache` | bypass cache | `true` |
| `cf-aig-cache-key` | custom cache key (override default) | arbitrary string |
| `cf-aig-cache-status` (response) | `HIT` \| `MISS` | — |

The retry semantics matter: timeout is measured from the *first byte* (TTFB), not full completion — so a model that streams slowly isn't killed mid-stream, only one that's slow to *start* is retried. And the final retry attempt has no timeout (waits for completion) — a deliberate "last chance, let it finish" policy worth copying for agent calls where a late success beats a hard failure.

### Route Invocation — `model: "dynamic/<route>"` (KNOWN — usage docs)

A client selects a Dynamic Route the same way it selects a model: by setting the `model` field to `dynamic/<route-name>` on the standard compat endpoint — **no special header or path**:

```jsonc
POST https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/compat/chat/completions
{ "model": "dynamic/my-route", "messages": [...],  "metadata": { "agent_role": "planner", "token_budget": 8000 } }
```

So the routing-DSL invocation reuses the exact same `{namespace}/{name}` model-string convention as a direct `{provider}/{model}` call (`anthropic/claude-...`) — `dynamic/` is just another namespace. The graph then runs server-side, reading `metadata.*` in its Conditional nodes.

### A Worked Route Graph (DESIGNED — assembled from the documented element schema)

Stitching the documented element shapes into the Verso example from the targets brief ("planner+big-budget → opus, else haiku, with a $-budget guard"):

```jsonc
{ "id": "verso-planner-route", "name": "planner-route", "elements": [
  { "id": "s",    "type": "start",       "outputs": { "next": { "elementId": "budget" } } },
  { "id": "budget","type": "rate",        "properties": { "key": "metadata.run_id", "limitType": "cost",
                                                          "limit": 5.00, "window": 3600 },
                   "outputs": { "success": { "elementId": "cond" }, "fallback": { "elementId": "haiku" } } },
  { "id": "cond", "type": "conditional", "properties": { "conditions": { "$and": [
                       { "metadata.agent_role": { "$eq": "planner" } },
                       { "metadata.token_budget": { "$gt": 5000 } } ] } },
                   "outputs": { "true": { "elementId": "opus" }, "false": { "elementId": "haiku" } } },
  { "id": "opus", "type": "model", "properties": { "provider": "anthropic", "model": "claude-opus-4.7",
                       "timeout": 60000, "retries": 2 },
                   "outputs": { "success": { "elementId": "end" }, "fallback": { "elementId": "haiku" } } },
  { "id": "haiku","type": "model", "properties": { "provider": "anthropic", "model": "claude-haiku",
                       "timeout": 30000, "retries": 1 },
                   "outputs": { "success": { "elementId": "end" }, "fallback": { "elementId": "end" } } },
  { "id": "end",  "type": "end", "outputs": {} } ] }
```

The `budget` Limit node (`limitType:cost`, keyed on `metadata.run_id`, $5/hr) checks-before-dispatch and routes to `haiku` on exceed; the `cond` node branches planner→opus; both models fall back to haiku→end on failure. This is the complete Verso routing-DSL example, runnable on Cloudflare's documented schema.

### Reimplementation — Budget-Limit Pre-Call Guard in ~25 lines (DESIGNED, from Cloudflare `limitType:cost` + Envoy check-before/charge-after + Vercel async write-back)

The gate's other explicit deliverable. A graceful, check-before/charge-after dollar-budget guard (the unified count-or-cost Limit node):

```python
import time

class BudgetGuard:
    """limitType: 'count' or 'cost'; window seconds; keyed (e.g. by run_id/tenant)."""
    def __init__(self, redis, limit, window_s, limit_type="cost"):
        self.r, self.limit, self.window, self.kind = redis, limit, window_s, limit_type

    def admit(self, key, est_cost) -> bool:          # CHECK before dispatch
        spent = float(self.r.get(self._k(key)) or 0.0)
        return (spent + (est_cost if self.kind == "cost" else 1)) <= self.limit

    def charge(self, key, actual_cost):              # CHARGE after response (async/batched)
        k = self._k(key)
        self.r.incrbyfloat(k, actual_cost if self.kind == "cost" else 1)
        self.r.expire(k, self.window)                # rolling window via TTL

    def _k(self, key):                               # window bucket
        return f"budget:{self.kind}:{key}:{int(time.time() // self.window)}"

# usage in the routing graph (Cloudflare Limit-node semantics):
#   if not guard.admit(run_id, estimate_cost(req)):  route_to(fallback_cheap_model)   # exceed → reroute, NOT error
#   else:                                            resp = call(primary); guard.charge(run_id, resp.cost)
```

Cost estimate can use Envoy's CEL-style cache-aware formula: `(input − cached)·rate + cached·rate·0.1 + cache_creation·rate·1.25 + est_output·rate`. The `est_output` before the call is a heuristic (e.g. `max_tokens`); reconcile with `actual_cost` from the response usage (force `stream_options.include_usage=true` so it's always present). This is Cloudflare's `rate` node + Envoy's two-phase cost + Vercel's async write-back, unified.

### For Verso

- **Adopt the node-graph as Verso's routing DSL surface.** The `{id, type, properties, outputs}` element + `elementId`-edge model is exactly right for a serializable, inspectable Verso route. Verso's `route(context)` can compile to / interpret this graph. Six node types cover everything: entry, branch, split, quota-guard, model-call, exit.
- **Unify rate-limit and budget-limit into ONE guard node with `limitType`.** This is the cleanest design decision in the whole spec — don't build separate `RateLimit` and `BudgetLimit` primitives. Build one `LimitNode {key, limit, limitType: "count"|"cost", window}` with `success`/`fallback` edges. Verso's per-run token/cost budget and per-key request rate become the same node, differing only by `limitType`.
- **Budget exceed = reroute, not error.** The `fallback` edge on exceed is the right default: when an agent run blows its budget, route to a cheaper model (or terminate gracefully), don't throw. This is a *pre-call guard* — check the running cost against `limit` *before* dispatching the model call, take `fallback` if it would exceed. Implementation: maintain a per-`key` rolling cost counter over `window` seconds (a Redis `INCRBYFLOAT` with TTL, cf. LiteLLM's spend tracker in `infra-model-routing.md`); on each request, `if counter + est_cost(request) > limit → fallback`.
- **MongoDB-operator conditions are a good condition grammar for Verso.** `{field: {$op: value}}` with `$eq/$ne/$in/$gt` + `$and/$or` is compact, serializable, and familiar. Verso's Conditional should reference `metadata.*` (agent_role, task_id, token_budget), request body, and headers — the same three namespaces.
- **`{provider}/{model}` prefix in the body is the simplest provider-selection encoding.** No separate provider field, no header — the model string itself carries routing. Verso's internal request format should accept `"{provider}/{model}"` and split it at the edge (matches Helicone's `model-mapping.yaml` keys too).
- **Percentage node for safe rollouts.** A `percentage` node with weights summing to 100 is the canary mechanism (route 10% of `planner` traffic to a new model). Verso should expose this for A/B-testing model/prompt changes inside an agent graph without code change.

---

## Envoy AI Gateway (CNCF) — token budgets + CEL MCP auth

### What It Is

A CNCF project (Bloomberg + Tetrate + Tencent) layering AI semantics on top of Envoy Gateway. It runs as an **External Processor (ExtProc)**: a Go gRPC service that Envoy calls to mutate requests/responses. Two CRDs do the routing work — `AIGatewayRoute` (model routing + per-route token-cost capture) and `MCPRoute` (MCP federation + CEL tool authorization) — while it reuses Envoy Gateway's stock `BackendTrafficPolicy` for the actual rate-limit enforcement. The two artifacts worth extracting: (1) **token/cost rate-limiting that survives streaming**, (2) **CEL-based per-tool MCP authorization**. Apache-2.0, Go, `api/v1beta1`.

### Token Cost Capture — `llmRequestCosts` (KNOWN — `api/v1beta1/shared_types.go:105-160`, `ai_gateway_route.go:99-207`)

An `AIGatewayRoute` declares *what costs to extract* from each response into Envoy dynamic-metadata; the `BackendTrafficPolicy` then *enforces* a budget against those metadata keys. The cost types (the `LLMRequestCostType` enum):

```go
// kubebuilder:validation:Enum=OutputToken;InputToken;CachedInputToken;CacheCreationInputToken;TotalToken;ReasoningToken;CEL
type LLMRequestCost struct {
    MetadataKey string             // where to store this cost, e.g. "llm_input_token"
    Type        LLMRequestCostType // one of the 7 enum values
    CEL         *string            // only when Type==CEL — an arbitrary cost formula
}
```

The **`CEL` cost type is the powerful one** — a per-request cost formula over token counts, evaluated *after* the response is known (`shared_types.go` doc-comment, verbatim variables):

```
# CEL variables: model (string), backend ("name.namespace"),
#   input_tokens, cached_input_tokens, cache_creation_input_tokens,
#   output_tokens, total_tokens, reasoning_tokens  (all unsigned int)
# Must return a signed/unsigned int (negative = error).

"model == 'llama' ? input_tokens + output_token * 0.5 : total_tokens"
"backend == 'bar.default' ? (input_tokens - cached_input_tokens)
                            + cached_input_tokens * 0.1
                            + cache_creation_input_tokens * 1.25
                            + output_tokens
                          : total_tokens"
```

This is **prompt-cache-aware dollar accounting expressed declaratively**: cached-read input charged at 0.1×, cache-creation at 1.25×, exactly mirroring Anthropic's cache pricing (cf. `infra-model-routing.md` OpenRouter cache table). The CEL returns a synthetic "token" number that becomes the rate-limit cost unit.

### Token Counting Across Streaming — The ExtProc Trick (KNOWN — `internal/extproc/processor_impl.go:335-339, 788-877`)

The hard problem: how do you count output tokens for a **streaming** SSE response when the client might not have asked for usage? Envoy AI Gateway's answer (`processor_impl.go:337-339`):

> *"The request is a streaming request, and the IncludeUsage option is set to false … we need to ensure that the token usage is calculated correctly without being bypassed."* → `forceBodyMutation = u.onRetry() || u.parent.forceBodyMutation`

It **rewrites the request body to force `stream_options.include_usage = true`** (via the translator's `RequestBody` mutation) so the upstream provider is *guaranteed* to emit a final usage chunk — the client can't opt out of token accounting. Then `buildDynamicMetadata` (`processor_impl.go:788`) runs **only at `body.EndOfStream==true`** (after the full stream completes; never on partial/failed responses) and emits the costs into the `io.envoy.ai_gateway` metadata namespace. Two-tier precedence (`:792-839`): route-scoped `requestCosts` (matched by `RouteName`, optional `Backend`/`Model` filters) override `GlobalRequestCosts`; unmatched keys are simply not emitted. It also stamps `model_name_override`, `backend_name`, `ai_service_backend_name` (the `namespace/name` short form the rate-limit descriptor keys on), `route_name`, `response_model`.

### Enforcement — `BackendTrafficPolicy` Token Rate Limit (KNOWN — `examples/token_ratelimit/token_ratelimit.yaml`)

Enforcement is stock Envoy Gateway `BackendTrafficPolicy` with `rateLimit.type: Global`, one rule per token-type, each with its **own budget** ("rate limited separately"):

```yaml
rateLimit:
  type: Global
  global:
    rules:
      - clientSelectors:
          - headers: [{ name: x-tenant-id, type: Distinct }]   # budget PER unique tenant
        limit: { requests: 10, unit: Hour }                     # 10 "tokens"/hour/tenant (input)
        cost:
          request:  { from: Number, number: 0 }                # request path consumes 0 — only CHECK
          response: { from: Metadata,                           # response path consumes the token count
                      metadata: { namespace: io.envoy.ai_gateway, key: llm_input_token } }
      # … repeated for llm_output_token (100/h), llm_total_token (1000/h),
      #    llm_cached_input_token (100/h), llm_cel_calculated_token (1000/h)
```

The two-phase cost trick is the key mechanic: **`cost.request.number: 0`** means the *request* path consumes nothing (so the rate-limit budget is only *checked*, not pre-charged), and **`cost.response.from: Metadata`** charges the *actual token count* from the dynamic-metadata key *after* the response. So you check-before, charge-after — the budget reflects real usage, and a request is admitted iff the running budget has headroom. `clientSelectors.headers[].type: Distinct` makes the budget per-unique-header-value (per tenant). This is a more precise design than a flat per-minute request cap.

### CEL MCP Authorization — Per-Tool Policy (KNOWN — `api/v1beta1/mcp_route.go:347-375`, `mcp_route_authorization.yaml`)

`MCPRoute.securityPolicy.authorization.rules[]` is the answer to "this agent may only call these MCP tools under these constraints." Each rule has a `source` (JWT scopes/claims), a `target` (backend + tool name), and an optional **CEL** predicate over the MCP call:

```yaml
authorization:
  rules:
    - source: { jwt: { scopes: [echo] } }
      target: { tools: [{ backend: mcp-backend-authorization, tool: echo }] }
      cel: 'request.mcp.params.arguments.text.matches("^Hello, .*!$") && request.headers["x-tenant-id"] == "t-123"'
    - source:
        jwt:
          scopes: [sum]
          claims:                                   # claim-value constraints, incl. array claims
            - { name: tenant, valueType: String, values: [acme, globex] }
            - { name: org.departments, valueType: StringArray, values: [engineering, development] }
      target: { tools: [{ backend: ..., tool: sum }] }
    - target: { tools: [{ ..., tool: countdown }] }  # no source → all sources allowed
    - source: { jwt: { scopes: [all-access] } }      # no target → all targets allowed
```

CEL attributes available (KNOWN — `mcp_route.go:356-367`): `request.headers` / `request.headers_all`, `request.mcp.method` (`tools/list`, `tools/call`), `request.mcp.backend`, `request.mcp.tool` (tool name w/o backend prefix), `request.mcp.params` (object incl. `arguments`, `_meta`). So a policy can gate not just *which tool* but *which argument values* — e.g. `request.mcp.tool in ["list_issues"]` or constraining `params.arguments.*` by regex. Default-deny: a rule with no matching source/target denies. This is exactly the tool-governance layer Verso needs for its MCP adapter.

### MCP Federation + Tool Filtering (KNOWN — `mcp_route.go:45-186`)

An `MCPRoute` federates **multiple MCP backends** behind one `path` (default `/mcp`, Streamable HTTP transport) — each `backendRefs[]` entry is one upstream MCP server with its own `path`, `securityPolicy` (credential injection), `forwardHeaders` (extract+rename client headers for per-user auth passthrough — e.g. forward a personal access token without OAuth, ≤32 headers), and a **`toolSelector`** (`MCPToolFilter`):

```go
type MCPToolFilter struct {
    Include      []string  // exact tool names to expose
    IncludeRegex []string  // RE2 patterns to include  (mutually exclusive with Include)
    Exclude      []string
    ExcludeRegex []string
}
// "Exclude rules take precedence over include rules (deny-wins). A tool must match an
//  include rule AND not match any exclude rule to be allowed."
```

So the gateway presents a *merged, filtered* tool catalog from N MCP servers to the LLM — exact or RE2-regex include/exclude, deny-wins. This is the federation layer (one route = many MCP servers, unified tool list) on top of the CEL per-call authorization above. Two-layer tool governance: `toolSelector` decides *what tools exist* (catalog filtering), CEL `authorization.rules` decide *who may call them with what args* (per-call gating).

### For Verso (MCP)

- **Federate MCP servers behind one route with per-backend tool filtering.** Verso's MCP adapter should let one logical tool-route aggregate N MCP servers, each with an include/exclude (exact + regex, deny-wins) `toolSelector` to curate the catalog, plus `forwardHeaders` for per-user credential passthrough. Combine catalog filtering (toolSelector) with per-call CEL authorization for two-layer governance.

### Model Routing + Per-Backend Credential Injection (KNOWN — `ai_gateway_route.go:214-291`, `backendsecurity_policy.go:16-79`)

`AIGatewayRoute` routes by the **`x-ai-eg-model` header** — the gateway extracts the model name from the request body and stamps it as a header, so route rules match on it (`token_ratelimit.yaml`: `headers: [{type: Exact, name: x-ai-eg-model, value: rate-limit-funky-model}]`). An `AIGatewayRouteRule` has `backendRefs` (target `AIServiceBackend`s or `InferencePool`s — the Tier-2 self-hosted endpoint picker), `modelsOwnedBy` + `createdAt` (synthesizes a `/v1/models` listing). Each `AIServiceBackend` declares its API `schema` (`OpenAI`, `AWSBedrock`, …) so the gateway translates the OpenAI-normalized request into the backend's dialect (same job as LiteLLM `transform_request`).

Credentials are injected by `BackendSecurityPolicy` — a discriminated union by `type` (one-of, enforced by CEL `XValidation`): `APIKey` (→ `Authorization` header), `AWSCredentials` (→ SigV4 signing), `AzureAPIKey`, `AzureCredentials`, `GCPCredentials`, `AnthropicAPIKey`. So the agent never holds provider keys — it calls the gateway, and the gateway attaches the right credential per backend. This is the clean separation Verso wants: the agent's request is provider-agnostic; the edge owns provider credentials and dialect translation.

### For Verso

- **Route by a normalized model header, translate per-backend.** Extract the model from the body, stamp `x-ai-eg-model`, match routes on it, and let each backend declare its `schema` for translation. Verso's edge should do the same: one OpenAI-normalized internal request, model-name-based routing, per-backend dialect adapters — never duplicate the request shape per provider.
- **Credentials live at the edge, injected per backend.** `BackendSecurityPolicy`'s one-of credential union (APIKey/AWS-SigV4/Azure/GCP/Anthropic) means agent code is key-free. Verso should hold provider credentials in its provider-edge config and inject them at dispatch — the agent declares "call model X", the edge attaches the credential and signs (SigV4 for Bedrock).
- **Separate cost *capture* from cost *enforcement*.** Envoy splits "extract these token counts into metadata" (`llmRequestCosts`) from "enforce a budget against them" (`BackendTrafficPolicy`). Verso should do the same: a response-parsing step that records `{input, output, cached, cache_creation, reasoning, total}` tokens into the run context, and a separate budget guard that reads those. This decoupling lets one capture feed many budget rules.
- **Force `stream_options.include_usage=true` on every streaming call.** This is the single most important reusable trick. Verso's LLM call layer must *rewrite* the request to force usage emission so token/cost accounting cannot be bypassed by a streaming client — otherwise budget enforcement silently fails on streamed responses (which is most agent calls). Accumulate from the final usage chunk; charge the budget at end-of-stream only.
- **CEL (or a CEL-like mini-expr) for cost formulas AND tool auth.** The `LLMRequestCost.CEL` formula (`input - cached) + cached*0.1 + cache_creation*1.25 + output`) is the correct way to express *cache-aware* dollar cost declaratively, per model/backend. Verso should let a per-node cost function be a small expression over the token-type variables, not hard-coded arithmetic. The same CEL engine governs MCP tool calls — one expression language for both budget and authorization.
- **Per-tool MCP authorization with argument-value constraints.** `{source: jwt-scopes/claims, target: {backend, tool}, cel: <arg/header predicate>}` with default-deny is the model for Verso's tool-governance layer: an agent's identity (role/scopes) gates *which* MCP tools it may call AND *which argument values* are allowed (`params.arguments.text.matches(...)`). This is materially deeper than "allow/deny tool by name" — it constrains the call payload. Verso's MCP adapter should adopt this rule shape verbatim.
- **Check-before / charge-after budgeting** (`cost.request=0`, `cost.response=actual`) is the right granularity for token budgets: admit on headroom, charge real usage. Maps to Verso's two budget levels — a global per-run budget (Envoy Tier-1 global rate limit) and a per-step context budget (Tier-2 fine-grained), both using the same check-before/charge-after counter.

---

## vLLM Semantic Router — signal-driven routing + safety gates

### What It Is

A signal-driven router for "Mixture-of-Models", deployed (like Envoy AI Gateway) as an Envoy **External Processor** — a Go gRPC service Envoy calls per request. The whole routing policy is a **declarative `config.yaml`** (2,181 lines in the reference) with two halves: (1) a rich **signal taxonomy** that extracts dozens of typed signals from each request (keywords, embeddings, domains, complexity, jailbreak, PII, structure, conversation shape, …), and (2) a **decisions** DSL that combines signals (AND/OR rules + priority) into a model choice + plugins (system-prompt injection, semantic-cache, tool-filtering, hallucination gate). The classifiers are small **mmBERT-32k** fine-tuned models running on CPU. Apache-2.0, Go + Rust (`candle-binding`). Cross-ref: this is the infra-layer analogue of Not Diamond's learned router (above) — same "embed/classify the prompt → pick a model" idea, but as a config-driven Envoy filter rather than a Python classifier.

### Deployment — Envoy ExtProc gRPC (KNOWN — `src/semantic-router/pkg/extproc/server.go:150,221`)

```go
ext_proc.RegisterExternalProcessorServer(s.server, s.service)         // standard Envoy ExtProc gRPC service
func (rs *RouterService) Process(stream ext_proc.ExternalProcessor_ProcessServer) error { ... }
```

It implements Envoy's stock `ExternalProcessor` bidirectional stream (`ProcessingRequest`/`ProcessingResponse` over gRPC) — so the routing logic is *decoupled from agent code*, observable, and hot-swappable. The router is held in an atomic `current.Load()`; on config change a new router is built, warmed up, and atomically `Swap`ped in (`server.go:235-275`), with the old one closed — **zero-downtime config reload** (file or Kubernetes-driven). Routing decisions return as header/body mutations on the request before Envoy forwards to the chosen backend.

### The Signal Pipeline (KNOWN — `config/config.yaml` `routing.signals`)

Every signal is a typed extractor producing a named boolean/score. The categories (verbatim from config):

- **`keywords`** — 4 string-match methods, each with its own threshold: `bm25` (BM25 score ≥ `bm25_threshold: 0.1`), `ngram` (`ngram_threshold: 0.4`, `ngram_arity: 3`), `fuzzy` (Levenshtein, `fuzzy_threshold: 82`), exact. `operator: OR/AND` over the keyword list.
- **`embeddings`** — semantic-similarity signals: a list of `candidates` phrases, fire if cosine-sim ≥ `threshold` (e.g. `technical_support: 0.75`, `account_management: 0.72`), `aggregation_method: max|any`. Supports `query_modality: text|image|audio` for multimodal routing.
- **`domains`** — MMLU-category intent classification (`mmlu_categories: [business]`), each domain may carry `model_scores: [{model, score, use_reasoning}]` — the per-domain quality prior.
- **`complexity`** — `needs_reasoning` (threshold 0.75) with `hard`/`easy` candidate phrases and a `composer` (OR over context/domain conditions). Drives the thinking-vs-non-thinking decision (the "When to Reason" pattern, arXiv `2510.08731`).
- **`structure`** — regex/keyword features with predicates: `many_questions` (count `[?？]` ≥ 4), `numbered_steps`, `first_then_flow` (ordered sequence detection, multilingual), `constraint_dense`/`format_directive_dense` (keyword *density* > 0.08 relative to text units).
- **`conversation`** — agent-loop shape: `multi_turn_user` (≥2 user msgs), `has_tools` (≥1 tool def), `active_tool_use` (`assistant_tool_cycle` ≥ 1 — i.e. tool-result continuation inside an agent loop), `has_developer_msg`, `heavy_non_user` (>5 non-user msgs).
- **`context`** — token-window signals (`long_context: min 32K, max 256K`).
- **`reasks`** — dissatisfaction detection: current turn repeats the prior N user turns (`lookback_turns`, threshold 0.8) → escalate.
- **`language`**, **`fact_check`**, **`user_feedbacks`**, **`preferences`**, **`events`**, **`kb`** (knowledge-base targeting).

### Safety Signals — Jailbreak + PII (KNOWN — `config.yaml:389-409`, `2074-2111`)

The safety signals are the directly-applicable guardrail layer:

```yaml
jailbreak:
  - name: prompt_injection
    method: hybrid                  # ML model + pattern match
    threshold: 0.8                  # signal threshold
    include_history: true           # scan the whole conversation, not just last turn
    jailbreak_patterns: ["ignore previous instructions", "reveal the hidden prompt", "jailbreak mode"]
    benign_patterns:  ["explain the policy", "summarize the safety rules"]   # false-positive guards
pii:
  - name: restricted_pii
    threshold: 0.85
    include_history: true
    pii_types_allowed: [EMAIL_ADDRESS]   # everything else PII → blocked/rerouted
```

The classifier models (KNOWN — `config.yaml` `prompt_guard`/`classifier`/`pii` blocks):

| Signal | Model | Threshold | Runs on |
|---|---|---|---|
| jailbreak | `mmbert32k-jailbreak-detector-merged` (+ `jailbreak_type_mapping.json`) | `0.7` (model) / `0.8` (signal) | CPU |
| domain/intent | `mmbert32k-intent-classifier-merged` (+ `category_mapping.json`, fallback `other`) | `0.5` | CPU |
| PII | `mmbert32k-pii-detector-merged` (+ `pii_type_mapping.json`) | `0.9` | CPU |
| fact-check | `mmbert32k-factcheck-classifier-merged` | `0.65` | CPU |
| hallucination detect | `mom-halugate-detector` | `0.82`, `min_span_length 2`, `nli_entailment_threshold 0.75` | CPU |
| feedback | `mmbert32k-feedback-detector-merged` | `0.7` | CPU |

All are **mmBERT-32k** (`use_mmbert_32k: true`, `use_modernbert: false`) on CPU — tiny, fast classifiers, no GPU for the routing decision. Jailbreak/PII are `method: hybrid` (ML score OR pattern match). These gate routing: a jailbreak hit can reroute to a containment model; PII can reroute to an on-prem backend (via the `kb`/`decisions` containment groups, `config.yaml:418-435`).

### In-Process Inference — candle-binding FFI (KNOWN — `candle-binding/semantic-router.go`)

All classifiers/embeddings run **in-process** via a Rust (`candle`) FFI, not a separate model server — so a routing decision is one cgo call, no network hop. The C ABI (verbatim `extern` decls):

```c
bool init_mmbert_32k_jailbreak_classifier(const char* model_id, bool use_cpu);   // per-classifier init
bool init_mmbert_32k_pii_classifier(const char* model_id, bool use_cpu);
ClassificationResult            classify_text(const char* text);                 // domain/intent
ClassificationResultWithProbs   classify_text_with_probabilities(const char* text);
BertTokenClassificationResult   classify_bert_pii_tokens(const char* text, const char* id2label_json);  // token-level PII spans
int get_embedding_smart(const char* text, float quality_priority, float latency_priority, EmbeddingResult*);
int get_embedding_2d_matryoshka(const char* text, const char* model_type, int target_layer, int target_dim, EmbeddingResult*);
int get_embedding_with_dim(const char* text, float quality_priority, float latency_priority, int target_dim, EmbeddingResult*);
TokenizationResult tokenize_text(const char* text, int max_length);
```

Two reusable ideas: (1) **`get_embedding_smart(text, quality_priority, latency_priority)`** — the embedder itself takes a quality↔latency tradeoff so the router can request a cheaper/faster embedding when the routing decision is low-stakes; (2) **`get_embedding_2d_matryoshka(text, layer, dim)`** — Matryoshka embeddings truncatable to `target_dim`, so the same model serves a cheap 256-d vector for fast signals and a full vector for precise ones. PII is **token-level** (`classify_bert_pii_tokens` returns spans + `id2label`), not just a document flag — so it can redact specific spans, not block the whole request.

### Semantic Cache (KNOWN — `config.yaml` semantic-cache plugin + `pkg/cache/`)

Per-decision semantic cache (plugin `semantic-cache`): `similarity_threshold` (0.69–0.82 across decisions), `ttl_seconds` (300–86400; global default 86400, max 2592000=30d), backend `milvus` (`milvus:19530`) or in-memory/HNSW (`pkg/hnsw/`), with a pluggable `eviction_policy.go`. Cache key is the embedded request; a hit returns the cached response if cosine-sim ≥ threshold. Unlike Helicone's exact-match FxHash cache, this is *semantic* (paraphrase-tolerant) — same as LiteLLM's `RedisSemanticCache` (`infra-model-routing.md`) but the threshold is tuned *per routing decision* (a business-route caches at 0.82, a fuzzier support-route at 0.69).

### Decisions DSL — Signals → Model (KNOWN — `config.yaml:553-672`)

A `decision` combines signals into a routing choice, with `priority` (higher wins) and a selection `algorithm`:

```yaml
- name: legal_confidence_route
  priority: 190
  rules: { operator: OR, conditions: [{type: domain, name: law}, {type: fact_check, name: needs_fact_check}] }
  modelRefs:
    - { model: qwen3-8b,  use_reasoning: true, reasoning_effort: medium, weight: 0.4 }
    - { model: qwen3-32b, use_reasoning: true, reasoning_effort: high,   weight: 0.6 }
  algorithm:
    type: confidence                    # route by model confidence, escalate if weak
    confidence:
      confidence_method: hybrid
      threshold: 0.72
      hybrid_weights: { logprob_weight: 0.65, margin_weight: 0.35 }   # confidence = 0.65·logprob + 0.35·margin
      escalation_order: small_to_large   # try cheap model, escalate to big if low-confidence
      cost_quality_tradeoff: 0.45
  plugins:
    - { type: hallucination, configuration: { enabled: true, use_nli: true, hallucination_action: header } }
```

Selection algorithms: `static` (fixed model), `confidence` (run cheap model, escalate to larger if confidence < threshold — a **confidence-based cascade**, where confidence = weighted logprob + answer-margin). Plugins per decision: `system_prompt` (inject role prompt), `semantic-cache` (`similarity_threshold: 0.82`, `ttl_seconds: 7200`), `tools` (filter the tool list — `allow_tools`/`block_tools`, `semantic_selection: true`), `tool_selection` (semantic top-k tool retrieval from `tools_db.json`, `top_k: 5`), `hallucination` (NLI-based fact gate). The **`projections.scores`** block (`config.yaml:503-551`) computes a `weighted_sum` of signal values (e.g. `request_difficulty = 0.18·tech_support + 0.36·needs_reasoning:hard + 0.18·long_context + …`) then maps to `threshold_bands` with `sigmoid_distance` calibration (`slope: 10.0`) — a learned-ish difficulty score from hand-weighted signals.

### "When to Reason" — Per-Query Thinking Gate (KNOWN — arXiv `2510.08731`)

The reasoning gate (vLLM SR's `complexity.needs_reasoning` signal + `use_reasoning`/`reasoning_effort` on `modelRefs`) implements the "When to Reason" result: classify each query's reasoning need (a difficulty estimate from the complexity signal, threshold 0.75) and **apply extended thinking only when beneficial** rather than to every query. The headline numbers vs always-reasoning: **+10.2pp accuracy on MMLU-Pro**, **−47.1% latency**, **−48.5% token consumption**. So selective reasoning is both cheaper *and* more accurate — always-on reasoning hurts on easy queries (over-thinking) as well as costing more. The mechanism in config: the `needs_reasoning` complexity signal (hard/easy candidate phrases + composer over context/domain) decides; matched → `modelRefs` with `use_reasoning: true, reasoning_effort: high|medium`, else `use_reasoning: false`.

### Prompt Compression Plugin (KNOWN — `pkg/promptcompression/`, config compaction block)

The router also carries a context-compaction step (`config.yaml` `novelty_weight: 0.1`, `position_depth: 0.1`, `preserve_first_n: 3`, `preserve_last_n: 2`) — it scores messages by novelty + positional importance, always preserving the first 3 and last 2 messages, dropping low-novelty middle turns. This is a routing-time context-budget control (drop redundant context before the model call), distinct from the per-decision `emits.retention` (`ttl_turns`, `prefer_prefix_retention`) which controls cross-turn memory retention.

### For Verso

- **Per-step reasoning gate = the "When to Reason" pattern, directly in Verso's ReAct loop.** Before each ReAct step, classify whether *this* step needs extended thinking (a cheap complexity signal: hard/easy candidate similarity, threshold ~0.75) and set `reasoning_effort` accordingly. The −48.5% tokens / −47.1% latency / +10.2pp-accuracy result means this is not just a cost optimization — always-on thinking *hurts* accuracy on easy steps. This is the single most Verso-relevant finding in this cluster: Verso's ReAct loop should gate thinking per-step, not per-run.
- **Routing as a signal pipeline + decisions DSL is the right architecture for Verso's router primitive.** The two-stage shape — extract typed signals → combine via priority'd AND/OR rules into a model+plugins choice — is exactly the pluggable `route(context) -> ModelSpec` Verso wants, but made declarative and inspectable. Verso should adopt the `{signals, decisions}` config split: signals are reusable extractors; decisions are the policy.
- **The `conversation` signals map 1:1 to Verso's agent loop.** `active_tool_use` (assistant_tool_cycle ≥ 1), `has_tools`, `multi_turn_user`, `heavy_non_user` are precisely the agent-state signals Verso's router should key on — e.g. route tool-continuation turns to a fast tool-capable model, route planning turns to a reasoning model. This is the framework-native version of "route by request characteristics."
- **Confidence-based cascade (`small_to_large` escalation) is a strong default selection algorithm.** Run the cheap model; if `confidence = 0.65·logprob + 0.35·margin < 0.72`, escalate to the larger model. This is directly implementable in Verso's provider edge and complements Not Diamond's threshold knob — use the cheap model's *own confidence* to decide whether to escalate, rather than predicting up-front.
- **Safety-signal-as-routing-condition belongs in Verso's guardrail layer.** A tiny CPU mmBERT jailbreak detector (threshold 0.7, hybrid ML+pattern, `include_history: true`) and a PII detector (threshold 0.9, `pii_types_allowed` allowlist) that *reroute* (to containment / on-prem) rather than just block is the right guardrail design. The hybrid pattern+model approach with `benign_patterns` to suppress false positives is worth copying verbatim. These run in <10ms on CPU — cheap enough for every agent step.
- **`needs_reasoning` complexity signal = Verso's "should this ReAct step use extended thinking?" decision.** The `complexity` signal (hard/easy candidate phrases, threshold 0.75, composer over context+domain) is the template for Verso's per-step reasoning gate. Combine with the `reasoning_effort` field on `modelRefs` to set thinking budget per decision.
- **Deploy the router as a decoupled service with atomic hot-reload.** The ExtProc + atomic `Swap` pattern (build new router → warm up → atomic swap → close old) is how Verso's durable mode should push updated routing/budget policy to running agents without restart — a clean alternative to TrueFoundry's NATS config bus for a single-process Verso.

---

## Vercel AI Gateway — same-model multi-provider failover

### What It Is

A managed gateway on Vercel Fluid compute (multi-region AWS, in-region Redis for quota). ~100 providers (`alibaba`…`zai`). Closed source, but the failover and metadata contract are fully documented. The two reusable patterns: (1) **two-level automatic failover** — a model array × a provider order, so a request for one model transparently tries multiple providers *and* multiple backup models; (2) **in-region Redis quota with async batched write-back**. Cross-ref: this is the same "model-alias → ordered provider list" idea as Helicone's model-mapping and OpenRouter's `models[]` fallback chain (`infra-model-routing.md`), but with the cleanest public metadata contract.

### Two-Level Failover Syntax (KNOWN — Vercel docs, AI SDK `providerOptions.gateway`)

```typescript
const result = streamText({
  model: 'openai/gpt-5.5',                                   // PRIMARY model
  providerOptions: {
    gateway: {
      models: ['openai/gpt-5.4-nano', 'anthropic/claude-opus-4.7'],  // ordered fallback MODELS
      order: ['azure', 'openai'],                            // ordered preferred PROVIDERS (per model)
      only:  ['azure', 'openai'],                            // hard whitelist of providers
      sort:  'cost',                                         // or 'ttft' (latency), 'tps' (throughput)
      caching: 'auto',                                       // auto cache-marker injection (Anthropic/MiniMax)
      byok: { anthropic: [{ apiKey: process.env.ANTHROPIC_API_KEY }] },  // per-request BYOK
    },
  },
});
```

**The failover algorithm (KNOWN — docs "How failover works"):** strictly sequential, nested loop:
```
for model in [primary, *models]:                # outer: backup MODELS in order
    for provider in resolve_providers(model, order/only/sort):   # inner: PROVIDERS for that model
        try: return call(model, provider)        # first success wins
        except: continue
# all exhausted → error
```
So `model:'openai/gpt-5.5'` with `order:['azure','openai']` tries gpt-5.5@azure → gpt-5.5@openai → (next model)@azure → … The default (no options) dynamically picks providers by recent uptime + latency.

### The Failover Metadata Contract (KNOWN — `modelAttempts` / `providerAttempts`)

The response carries a full audit trail of every attempt — the single most useful artifact for an agent framework:

```jsonc
"modelAttempts": [
  { "canonicalSlug": "google/gemini-3.1-pro-preview",  // normalized "creator/model-name"
    "modelId": "vertex:gemini-3.1-pro-preview",         // provider-internal "provider:model"
    "success": false, "providerAttemptCount": 2,
    "providerAttempts": [
      { "attemptNumber": 1, "provider": "vertex", "modelId": "vertex:gemini-3.1-pro-preview",
        "success": false, "credentialType": "system", "responseTimeMs": 15679.64,
        "error": "Internal error encountered.", "statusCode": 500 },
      { "attemptNumber": 2, "provider": "google", "success": false, "responseTimeMs": 284.30, "statusCode": 500 } ] },
  { "canonicalSlug": "anthropic/claude-opus-4.7", "modelId": "anthropic:claude-opus-4-7",
    "success": true, "providerAttemptCount": 1,
    "providerAttempts": [ { "attemptNumber": 1, "provider": "anthropic", "success": true,
        "statusCode": 200, "responseTimeMs": 4521.78, "providerResponseId": "msg_01ABC..." } ] }
]
```

Note the **two model identifiers**: `canonicalSlug` (gateway-normalized `creator/model-name`) vs `modelId` (provider-native `provider:model`) — the same canonical slug can be tried on N providers, each with its own modelId and timing. This is exactly how an agent detects *which* provider/model actually served and how many attempts it cost.

The full `gateway.routing` metadata object (KNOWN — provider-filtering docs) wraps `modelAttempts` with the routing decision trail:

```jsonc
"gateway": {
  "routing": {
    "originalModelId": "anthropic/claude-sonnet-4.6",
    "resolvedProvider": "anthropic", "resolvedProviderApiModelId": "claude-sonnet-4.6",
    "fallbacksAvailable": ["bedrock", "vertex"],
    "planningReasoning": "System credentials planned for: anthropic. Total execution order: anthropic(system)",
    "finalProvider": "anthropic", "modelAttemptCount": 1, "totalProviderAttemptCount": 1,
    "modelAttempts": [ /* as above */ ],
    "sort": { "option": "cost",                                  // only present when sort active
              "executionOrder": ["anthropic","bedrock","vertex"],
              "metrics": { "anthropic": 0.003, "bedrock": 0.003, "vertex": 0.005 },  // per-provider sort metric
              "deprioritizedProviders": [] } },
  "cost": "0.0045405",          // inference cost, decimal STRING (BYOK/ZDR surcharges excluded)
  "marketCost": "0.0045405",    // market-rate cost
  "generationId": "gen_01A2..."  // for the Generation Lookup API
}
```

Each `providerAttempt` also carries `credentialType: "system"|"byok"` — so a failed BYOK attempt that succeeds on a system credential shows both (`{byok:Unauthorized}` then `{system:success}`), making credential-failover visible.

### Filtering / Ordering / Sorting Semantics (KNOWN — provider-filtering docs)

Three composable provider controls under `providerOptions.gateway`:
- `order: string[]` — provider slugs to try first, in order; others follow.
- `only: string[]` — hard whitelist; **error** if none available for the model. Combined with `order`: `only` filters first, `order` ranks within → "intersect order with only" (e.g. `only:[anthropic,vertex] + order:[vertex,bedrock,anthropic]` → `vertex → anthropic`).
- `sort: 'cost'|'ttft'|'tps'` — rank by lowest cost / lowest median time-to-first-token / highest median tokens-per-second. Combined with `order`: ordered providers promoted to front, rest follow sorted. Combined with `only`: sort within the restricted set.

**Sort × health is the load-balancing rule:** healthy providers sort purely by metric; **degraded/recovering** providers get a *penalty* added to their metric (pushed lower); **down** providers always sort last regardless of metric. This is the same "evict/penalize unhealthy then optimize" pattern as Helicone's health-monitor eviction + PeakEWMA — sort optimizes the chosen objective *subject to* a health guard rail.

The `sort.deprioritizedProviders` field in the response metadata names exactly which providers were penalized for degraded health on this request — so the audit trail shows not just what served, but what was *avoided* and why. The `gateway.routing.planningReasoning` string ("System credentials planned for: anthropic. Total execution order: anthropic(system)") is a human-readable trace of the routing decision — useful for debugging why a particular provider/credential was chosen.

These controls are also available over the **OpenAI-compatible Chat Completions API** (not just the AI SDK): set them under `providerOptions`, or use the top-level `provider` shorthand — `"provider": { "sort": "tps" }` — directly in the request body, so any OpenAI client can drive Vercel's routing without the AI SDK. The **default** (no options at all) dynamically picks providers by recent uptime + latency — i.e. an implicit health-aware latency sort, the same objective as Helicone's PeakEWMA but computed from aggregate fleet telemetry rather than per-client RTT.

### Redis Quota — In-Region, Async Write-Back (INFERRED — Fluid-compute blog)

Documented but without key formats: each Vercel region runs **its own Redis cluster**; the request path "verifies quotas through in-region Redis" (local read, low latency); "writes and usage increments are **batched and written back to Redis after responses complete**." So the hot path does a cheap quota *read*, the response path does a *deferred batched increment* — the same check-before/charge-after shape as Envoy's token rate-limit and LiteLLM's `INCRBYFLOAT` spend flush (`infra-model-routing.md`). Exact keys/TTLs are not disclosed (server-side black box); the **pattern** — per-region local quota cache + async batched write-back — is the takeaway.

### For Verso

- **Model-array × provider-order is the right failover shape for Verso's `ProviderEdge`.** A primary model + ordered backup `models[]`, each resolved against an ordered `order[]` of providers, with strictly-sequential first-success-wins. This is more expressive than a flat fallback list: it separates "try a different *provider* for the same model" (transient outage) from "try a different *model*" (capability/capacity fallback). Verso should model both axes.
- **Emit a `modelAttempts`/`providerAttempts` audit trail on every call.** Verso's LLM call wrapper must return the full attempt history — `{canonicalSlug, modelId, provider, attemptNumber, success, statusCode, responseTimeMs, error, providerResponseId}` — so the agent (and observability) can see which model served, how many attempts, and the latency/error of each. This is non-negotiable for debugging multi-agent runs and for cost attribution. Keep the two-id distinction (Verso-normalized slug vs provider-native id).
- **In-region quota read + async batched write-back.** For Verso's per-run/per-team budgets, read the quota from a local cache on the hot path (fail-open if Redis is slow), and batch the usage increment to the durable store *after* the response. This keeps budget enforcement off the critical latency path while staying eventually-accurate — the right tradeoff for an agent framework where a 1-2s stale budget is acceptable but added per-call latency is not.
- **`caching: 'auto'` provider-aware cache markers.** Verso's context layer should auto-inject the right cache-control markers per provider (Anthropic ephemeral cache_control, etc.) rather than making the agent author do it. Pairs with the prompt-cache stickiness rule from `infra-model-routing.md`.
- **Sort-with-health-penalty is a complete LB recipe.** `sort: 'cost'|'ttft'|'tps'` + degrade-penalty + down-last is a simpler alternative to PeakEWMA-P2C when you have provider-level health and metric data: rank by the objective, penalize unhealthy. Verso's edge could offer both (P2C for fine-grained latency, sort for explicit cost/throughput objectives), selectable per node.

### Production calibration baseline (KNOWN — Vercel production-index blog, Apr 2026)

The targets brief asked for these as Verso context-budget defaults — concrete real-world agent-traffic numbers:
- **22.2%** of requests end with a tool call (up from 11.4% in Oct 2025); **58.9%** of all tokens are in tool-call requests (up from 31.6%) → tool-using requests are ~**2.6× more token-heavy** than plain ones. *Verso default: budget the tool-using path for ~2.6× the tokens of a non-tool turn.*
- **~3.5%** of requests complete only after a fallback (5.1% of tokens, 4.9% of cost) → fallback is a real, non-trivial path; Verso must treat failover as expected, not exceptional, and size retry budgets accordingly.
- Model diversity scales with volume: teams at 10M+ req/mo use **~35 models**; 1M–10M use ~18; 1K–10K use **~3**. → a Verso router's candidate pool grows with scale; start with 3, design for 35.
- Spend share (Apr 2026): Anthropic 61% / Google 21% / OpenAI 12% by spend; by tokens Google 38% / Anthropic 26% / OpenAI 13% / xAI 10% (Google cheaper-per-token, Anthropic pricier-per-token) — useful priors for default model selection.

---

## Martian — RouterBench (the eval corpus)

### What It Is

Martian is a closed commercial router ("LLM operating system"); its public artifact is **RouterBench** (`withmartian/routerbench`, arXiv `2403.12031`) — a benchmark + dataset for evaluating *any* multi-LLM router. The router engine itself is closed, but RouterBench's **dataset format and oracle/cascade evaluation harness** are the highest-value piece for Verso: they're the calibration corpus and the eval methodology for a Verso router. The dataset (HF `withmartian/routerbench`) is ~405K inference outcomes across 8 task domains and 11 models.

### Dataset Format — Wide Table (KNOWN — `convertors/martian_evals_convertor.py`, `routers/`)

Raw logs (OpenAI-evals jsonl: `spec.completion_fns`, `sample_id`, `type∈{sampling,match,metrics}`, `data.{prompt,sampled,correct,score}`) are converted to a **wide per-prompt table** (`convert_to_wide_format`), one row per prompt, with per-model columns:

| Column | Meaning |
|---|---|
| `prompt` | the input (stringified message list) |
| `eval_name` | task/domain identifier (8 domains, e.g. MMLU, MT-Bench, GSM8K…) |
| `sample_id` | unique prompt id |
| `{model}` | **performance score in [0,1]** for that model on that prompt (the quality label) |
| `{model}\|model_response` | the model's actual response text |
| `{model}\|total_cost` | the dollar cost of that (prompt,response) for that model |
| `oracle` | best-achievable routing result (from `generate_oracle_routing_results`) |

Scoring normalization (KNOWN — `process_api_logs`): `accuracy`/`score` used directly; `sacrebleu_sentence_score/100`; multiple-choice `A..E` → `1.0 − (ord(choice)−ord('A'))/4.0`. Cost (KNOWN — `abstract_router.py`): `cost = prompt_tokens·prompt_rate + completion_tokens·completion_rate + request_cost` via `tokencost` (`TOKEN_COSTS[model]{prompt,completion,request}`).

### The Cascade Router (the reference routing baseline) (KNOWN — `routers/run_cascading_router.py`)

RouterBench ships a **cascade router** as the canonical cost/quality baseline — directly reusable as a Verso strategy:

```python
# rank models cheapest→priciest by per-token cost (amortized request cost over avg response length)
model_completion_cost[m] = prompt_rate(m) + completion_rate(m) + request_cost(m)/avg_response_len(m)
llms = sorted(models, key=lambda m: model_completion_cost[m])              # cheap first

# performance bar = top-5% quantile of all model scores on this eval
performance_threshold = np.quantile(all_scores.flatten(), q=0.95)

for prompt in dataset:
    for llm in llms:                                # ascend the cost ladder
        if cumulative_cost >= max_cost_per_response and already_tried_one: break
        answer_accepted = (score(llm, prompt) >= performance_threshold)   # judge accepts?
        # evaluator_error_rate models a noisy judge: flips the accept decision w.p. ε
        if answer_accepted: break                   # stop at first model clearing the bar
```

Two knobs that matter: `performance_threshold_quantile=0.95` (accept only top-5%-quality answers) and `evaluator_error_rate` (ε models a *noisy judge* — flips accept/reject with probability ε, so the eval measures router robustness to imperfect quality signals). Other routers in the repo: `knn_router`, `mlp_router`, `svm_router` (all `AbstractRouter.batch_route_prompts(prompts) -> [model_name]`), using cached embeddings (`embedding/cache.py`, MongoDB or local).

### KNN Router + the AIQ Metric (KNOWN — `routers/knn_router.py`, `evaluation/AIQ.py`)

The **KNN router** is the simplest learned baseline and a clean Verso template: fit `sklearn.NearestNeighbors(n_neighbors=50, metric="cosine", leaf_size=30)` on training-prompt embeddings; for a new prompt, find its 50 nearest training prompts and pick the model that's best (highest score / best cost-quality) across that neighborhood. It amortizes the per-request cost over `average_response_length` per model (same `prompt_rate + completion_rate + request_cost/avg_len` formula as the cascade). No training step beyond the index fit — pure instance-based routing.

**AIQ (Average Improvement in Quality)** is RouterBench's headline metric (`AIQ.py`): plot each router as points on the (cost, quality) plane across its parameter sweep, take the **non-decreasing convex hull** (the achievable Pareto frontier — `get_non_descreasing_convex_hull_of`), and compute the **area under that curve** (`np.trapz`). A higher AUC = better cost/quality tradeoff across the whole budget range, not just at one operating point. This is the right way to compare routers: not "accuracy at fixed cost" but "area under the cost-quality Pareto frontier."

### For Verso

- **RouterBench is Verso's router calibration corpus.** Any Verso routing strategy (the Helicone P2C edge, the Not Diamond RoRF classifier, a confidence cascade) should be benchmarked on the RouterBench wide-table: the per-model `score` and `total_cost` columns let you compute the cost/quality Pareto frontier offline, *without paying for inference*, because every (prompt, model) outcome is pre-recorded. This is the missing eval harness for Verso's router primitive.
- **Adopt the wide-table format for Verso's own eval store.** One row per task, per-model `{model}` score + `{model}|cost` + `{model}|response`, plus an `oracle` column. This is the exact schema Verso's eval harness should emit so routing decisions can be replayed and scored against the oracle (best-possible) and against any candidate router offline.
- **The cascade router is a strong, judge-free-ish default.** Rank models cheap→expensive, run ascending, stop at the first whose answer clears a quality bar (here a confidence/score threshold). It's the same shape as vLLM SR's `small_to_large` confidence escalation — Verso should offer it as a built-in strategy, with the quality bar pluggable (self-confidence, an NLI gate, or an LLM judge). The `evaluator_error_rate` insight matters: a router is only as good as its quality signal, so Verso must measure routing quality under a *noisy* judge, not a perfect one.
- **Amortized per-token cost ranking** (`prompt_rate + completion_rate + request_cost/avg_response_len`) is the correct way to order models by cost when there's a fixed per-request fee — fold the request fee into the per-token rate using the expected response length. Verso's cost-based routing should use this, not raw per-token price.
- **Measure routers by AIQ (area under the cost-quality Pareto frontier), not point accuracy.** A Verso router with a tunable threshold should be evaluated by sweeping the threshold, plotting (cost, quality), taking the non-decreasing convex hull, and integrating. This is the apples-to-apples way to compare RoRF-threshold vs P2C vs cascade vs confidence-escalation on the same corpus — and it's a single number Verso's eval harness can report per router.
- **KNN routing is the zero-training-cost learned baseline.** `NearestNeighbors(50, cosine)` over evaluated-task embeddings + pick the neighborhood's best model is trivial to implement and needs no model training — a good first learned router for Verso before investing in RoRF/IRT. It also doubles as the IRT-Router warm-up's kNN lookup (above).

---

## Cross-System Synthesis → Verso

The seven systems converge on a small set of mechanisms Verso's model-provider edge should implement. Ranked by directness:

1. **Default load balance = PeakEWMA + P2C** (Helicone, also Bifrost in researchfms). `load = rtt_ewma · (outstanding+1)`; asymmetric update (jump-up-fast on slowdown, decay-down with `exp(-Δ/30s)`); pick-2-route-to-better. ~80 lines, no GPU, strictly beats round-robin/global-min under concurrency.

2. **Learned `route()` is a drop-in classifier** (Not Diamond RoRF + IRT-Router). `embed(prompt) → RF.predict_proba → 4-class group → threshold`. `threshold = quantile(win_rates, 1−target_A_pct)` is the cost/quality knob. Jina-v3 local embeddings keep it keyless. IRT-Router's `e ← (1−λ)e + λ·e_kNN` warm-up bootstraps routing before the eval corpus exists.

3. **Routing DSL = typed node graph** (Cloudflare) or **signals → decisions** (vLLM SR). Cloudflare: `{Start, Conditional($eq/$ne/$in/$and/$or), Percentage, Limit(count|cost), Model, End}` wired by `elementId`. vLLM SR: extract typed signals (incl. agent-loop signals `active_tool_use`/`has_tools`) → priority'd AND/OR decisions → model+plugins. Both serializable and inspectable.

4. **Budget guard = unified Limit node, check-before/charge-after** (Cloudflare `limitType:count|cost`; Envoy `cost.request=0 / cost.response=metadata`; Vercel in-region Redis async write-back; LiteLLM `INCRBYFLOAT`). One guard, two modes (request-count vs dollar/token). Exceed → reroute to `fallback` (graceful), not error. CEL/expr cost formula makes it cache-aware (`(input−cached) + cached·0.1 + cache_creation·1.25 + output`).

5. **Two-axis failover + full audit trail** (Vercel). Backup `models[]` × ordered `providers[]`, sequential first-success. Emit `modelAttempts`/`providerAttempts` with per-attempt provider/status/latency/error so the agent sees what served and what it cost.

6. **Safety as a routing condition** (vLLM SR). Tiny CPU mmBERT jailbreak (thr 0.7, hybrid ML+pattern, `include_history`) + PII (thr 0.9, allowlist) detectors that *reroute* (containment/on-prem) rather than block. <10ms/step.

7. **Tool governance = CEL per-tool auth** (Envoy MCP). `{source: jwt-scopes/claims, target: {backend, tool}, cel: <arg/header predicate>}`, default-deny — gates which tool AND which argument values an agent may call. Directly for Verso's MCP adapter.

8. **Force `stream_options.include_usage=true`** (Envoy) so token/cost accounting can't be bypassed on streamed responses (most agent calls). Charge budget at end-of-stream.

9. **Tower-style layer order** (Helicone): error-normalize → cache (return before quota/LB) → rate-limit → context → balancer. Cache + budget guard sit *above* the provider call. Hot-reload routing via atomic swap (vLLM SR) — no restart.

10. **Eval offline against RouterBench** (Martian). Wide table (`{model}` score + `{model}|cost`) replays any router on 405K pre-recorded outcomes → cost/quality Pareto with zero inference spend. Adopt this as Verso's router calibration harness.

These build on, not duplicate, `infra-model-routing.md` (OpenRouter `selectProvider` inverse-square weighting + `ProviderPreferences`; LiteLLM 10-strategy router + cooldown + `max_iterations_limiter`) and researchfms `PORTKEY.md`/`BIFROST.md`/`KONG_AI_GATEWAY.md`.
