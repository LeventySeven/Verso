# RE Targets: Model Routing / Gateways

**For:** Verso — async ReAct agent framework with tactical↔durable seam, context engineering, typed memory, evals, native @tool.
**Relevance lens:** What does each gateway teach about (a) failover/retry/load-balance logic Verso's model-provider edge should embed, (b) budget/cost enforcement that belongs in Verso's context layer, (c) semantic routing that a Verso router primitive could expose, (d) require_parameters / schema-enforcement patterns for tool calls?

---

## Already Covered

The following targets have dedicated teardowns in `teardowns/` and are **not re-proposed**:

| File | What's covered | Depth |
|---|---|---|
| `teardowns/PORTKEY.md` (1,142 L, R2 done) | Hono app, `tryTargetsRecursively`, `ConditionalRouter` operator semantics, `selectProviderByWeight`, retry handler, cache middleware, hooks engine, 80+ header map, Anthropic adapter verbatim, streaming pipeline | Full — R2 exhaustive |
| `teardowns/LITELLM.md` (4,126 L, R2 done) | Router.py 10-strategy breakdown (simple-shuffle, least-busy, lowest-latency, usage-based-routing-v2 Redis-atomic TPM/RPM), DualCache, proxy_server.py budget enforcement, 20 verbatim provider adapters | Full — R2 exhaustive |
| `teardowns/OPENROUTER.md` (6,916 L) | ProviderPreferences schema, sort strategies, Auto Router, Auto Exacto, fallback chains, semantic cache, BYOK, OTLP broadcast, server tools arch | Full |
| `teardowns/KONG_AI_GATEWAY.md` (808 L, R2 done) | 8-stage Lua filter pipeline, ai-proxy handler, normalize-request, cost calculation, ai_plugin_ctx, `ai_introspect_body` subprocess LLM calls | Full — R2 done |
| `teardowns/BIFROST.md` (940 L, R2 done) | Sync.Pool prewarm, fasthttp config, atomic CAS plugin reload, P2C key selection, peek-first-chunk-for-error retry, Starlark MCP code-mode, comparison with Envoy AI Gateway | Full — R2 done |
| `teardowns/ORQ.md` (801 L, R2 done) | JWT auth, GCP infra, Angular dashboard, Kuma/Envoy upstream signal, Bartolo OpenAPI codegen, eval-as-flagship | Done |
| `teardowns/NEXOS_AI.md` (711 L, R2 done) | ORY Hydra+Kratos auth, Cloudflare R2 storage, GPU cluster, multi-region (US/EU/OTHER) | Done |

---

## RE Targets

### Not Diamond (RoRF + IRT-Router)

**what:** ML-native model router — prompt→embedding→random-forest or IRT model outputs which LLM to call. Powers OpenRouter's `/auto` mode. Pre-trained routers on HuggingFace; custom training on your data.

**why_for_verso:** Verso's router primitive (the pluggable edge that picks which model provider to call) could embed a learned classifier rather than hand-coded rules. Not Diamond's RoRF and IRT-Router papers are the only open-source implementations of this pattern. Directly answers: "how do you build a `route()` function that isn't just round-robin or latency-sort?" The `threshold` parameter maps directly to a Verso cost-vs-quality knob on the model-provider edge. IRT-Router's cold-start warm-up via semantic similarity is directly applicable to Verso's eval harness bootstrapping.

**what_to_RE:** (1) `Not-Diamond/RoRF` — full source: `Controller.route()` call path, embedding pipeline (jina vs voyage), random forest feature vector construction, threshold calibration algorithm, pre-trained model format on HuggingFace. (2) `Not-Diamond/IRT-Router` (ACL 2025 arxiv:2506.01048) — MIRT-Router and NIRT-Router implementations, online query warm-up via semantic similarity. (3) Live API — probe `/v2/router` for schema, what features are sent server-side that aren't in the OSS client.

**source_pointer:** `github.com/Not-Diamond/RoRF`, `github.com/Not-Diamond/notdiamond-python`, arxiv `2506.01048`, `openrouter.ai/docs/guides/routing/routers/auto-router` (live integration docs)

**priority:** P0 — directly shapes Verso's model-router primitive design.

---

### Martian (withmartian)

**what:** Closed model router / "LLM operating system" — real-time prompt analysis routes to best model for cost+quality. ~$1.3B valuation (2026). Powers enterprise routing for Accenture. RouterBench (open-source benchmark dataset, 405K inference outcomes across 8 domains) is their public artifact.

**why_for_verso:** Martian's "model mapping" approach — routing as a learned mapping from prompt features to model capability space — is a different architecture than Not Diamond's pairwise classifier. Their RouterBench dataset is the best public eval corpus for testing any Verso router. The distinction between Martian's offline-trained routing model vs online adaptation is directly relevant to Verso's eval/reliability layer: should routing decisions feed back into calibration?

**what_to_RE:** (1) `withmartian/routerbench` — benchmark dataset format, task domain taxonomy (8 domains), quality metric schema, how per-model scores are structured. (2) `martianprotocol/martianrouter` — any open-source router config/YAML schema. (3) Live API probe — `withmartian.com/api`, error-mine for Pydantic schemas, model/judge/router distinction from their SDK. (4) Accenture "Switchboard" integration — any public docs on how enterprise routing policies are configured.

**source_pointer:** `github.com/withmartian/routerbench`, `github.com/martianprotocol/martianrouter`, `withmartian.com` (closed — probe via API + SDK), VentureBeat/Accenture post for enterprise routing policy design

**priority:** P1 — RouterBench dataset is high-value for Verso evals; router architecture is largely closed but worth probing.

---

### Cloudflare AI Gateway (Dynamic Routes)

**what:** Cloudflare-hosted managed gateway running on Workers. August 2025 refresh added Dynamic Routes (visual if/else rule engine with node types: Start, Conditional, Percentage, Model, Rate Limit, Budget Limit, End), unified billing through Cloudflare invoice, and provider translation layer (OpenAI client → any provider via `/compat`).

**why_for_verso:** Dynamic Routes' node-graph rule schema is the most concrete public spec for how a routing DSL should be structured. The `Conditional → Percentage → Model` graph exactly maps to what Verso's model-provider edge needs: "if agent_type == 'planner' AND token_budget > 5000, route to opus-4 with p=0.8 else route to haiku with p=1.0." The Budget Limit node type is directly implementable in Verso's context layer as a pre-call guard. The provider translation layer (`/compat` endpoint) is the cleanest public design for Verso's provider normalization.

**what_to_RE:** (1) `developers.cloudflare.com/ai-gateway/features/dynamic-routing/` — complete JSON schema for route configs (node types, condition operators, action payloads). (2) The `Conditional` node's condition language: what fields are referenceable (request body, headers, metadata), what operators exist, nested logic support. (3) Budget Limit node — how cost is tracked per-request (token counting, pricing table lookup), what happens on exceed (hard block vs soft cap). (4) `/compat` endpoint — the provider translation layer: how request schemas are normalized, which fields are provider-specific.

**source_pointer:** `developers.cloudflare.com/ai-gateway/` (closed — probe via docs + `llms.txt` + API), `blog.cloudflare.com/ai-gateway-aug-2025-refresh/`

**priority:** P0 — the Dynamic Routes node schema is the most concrete public design for Verso's routing DSL.

---

### Vercel AI Gateway

**what:** Managed gateway on Vercel Fluid compute (multi-region AWS, in-region Redis for quota, OIDC auth). ~100 models, automatic provider failover (Anthropic → Bedrock → Vertex for same model), per-function quota via Redis, budget enforcement. Not open-source.

**why_for_verso:** Two specific things: (1) The "same model, multiple provider" automatic failover pattern — when you request `claude-sonnet-4`, Vercel transparently tries Anthropic, then Bedrock, then Vertex. This is a concrete answer to "how should Verso's model-provider edge handle provider outages without the agent code knowing?" (2) The in-region Redis quota check pattern — how to do per-request budget enforcement with sub-millisecond overhead using async background refresh. The `production index` blog (April 2026) shows real routing data: 22.2% of requests end with tool call, 58.9% of tokens in tool-call requests — useful calibration for Verso's context budget defaults.

**what_to_RE:** (1) `vercel.com/docs/ai-gateway` — complete model list, fallback chain definition syntax, budget config schema. (2) The "same model, multiple provider" failover: how provider priority is defined, what metadata comes back (which provider served, fallback attempts, latency breakdown). (3) Redis quota pattern: what keys are used (per-team? per-function? per-model?), what the TTL/eviction strategy is, how batched writes work after response. (4) `vercel.com/blog/ai-gateway-production-index` — aggregate routing data (model distribution, tool-call rates) as Verso calibration baseline.

**source_pointer:** `vercel.com/docs/ai-gateway` (closed — probe via docs), `vercel.com/blog/ai-gateway-production-index`, `vercel.com/blog/how-ai-gateway-runs-on-fluid-compute`

**priority:** P1 — failover-by-model-alias and Redis quota patterns are directly replicable in Verso's provider edge, even without source.

---

### Helicone AI Gateway (Rust)

**what:** Open-source Rust gateway (Apache 2.0), 96.7% Rust codebase, ~30MB binary, P95 < 5ms, 3k+ RPS on modest hardware. Implements P2C (Power of Two Choices) + PeakEWMA load balancing. YAML config. Pluggable cache backends (in-memory, Redis, S3). Tower middleware. Rate limiting by requests, tokens, or dollars.

**why_for_verso:** This is the cleanest open-source implementation of P2C + PeakEWMA in the gateway space — algorithms Bifrost also uses but in Go. Reading the Rust source gives Verso the exact math: P2C randomly picks 2 providers and routes to the better one (prevents herd behavior), PeakEWMA tracks latency trends to predict slowdowns before they hit. These algorithms belong in Verso's provider edge as the default load-balancing strategy. The Tower middleware architecture is also directly relevant: Tower's `Service` trait is the right abstraction for composable Verso middleware (retry, cache, rate-limit, route as stacked layers).

**what_to_RE:** (1) `Helicone/ai-gateway` — full Rust source: P2C algorithm implementation (how "better" is defined, tie-breaking), PeakEWMA decay factor and window, the Tower service stack order (which middleware wraps which). (2) `config/embedded/providers.yaml` — complete provider list and capability flags. (3) Rate limiting implementation: token counting per-provider, dollar-amount tracking (pricing table location), sliding window vs token bucket choice. (4) Cache key generation for semantic caching if present.

**source_pointer:** `github.com/Helicone/ai-gateway` (open source, Rust, Apache 2.0)

**priority:** P0 — P2C + PeakEWMA source is directly implementable in Verso's provider edge; Tower middleware stack is the right architecture model for Verso's composable call pipeline.

---

### Envoy AI Gateway (CNCF)

**what:** CNCF project (Bloomberg + Tetrate + Tencent, 95+ contributors), built on Envoy Proxy as an External Processor. Two-tier architecture: Tier 1 (auth, global token rate limiting, provider routing) + Tier 2 (fine-grained self-hosted model control, InferencePool endpoint picker). 87.9% Go. Token-level rate limiting via `BackendTrafficPolicy` CRD. 16+ providers. CEL-based MCP authorization (v0.5). Kubernetes-native.

**why_for_verso:** The BackendTrafficPolicy CRD design is the most mature public spec for declarative, per-route token budget enforcement. The CEL-based MCP authorization (v0.5, 2026) is directly applicable to Verso's MCP adapter — how do you write a policy that says "this agent may only call these MCP tools with these parameter constraints"? The two-tier architecture (global rate limit at Tier 1 vs fine-grained at Tier 2) maps to Verso's two budget levels: global per-run budget (Tier 1) vs per-step context budget (Tier 2). The token rate limiting YAML (`examples/token_ratelimit/token_ratelimit.yaml`) is a concrete schema to read.

**what_to_RE:** (1) `envoyproxy/ai-gateway` — `internal/` and `api/` directories: BackendTrafficPolicy CRD schema (full YAML spec), token rate limit algorithm (how tokens are counted across streaming responses), provider failover via Envoy's cluster health checking. (2) CEL authorization for MCP: the policy language, what request attributes are available in CEL context, how tool name/parameter constraints are expressed. (3) The Go External Processor code: how it intercepts Envoy requests, what the request/response transformation pipeline looks like. (4) `examples/token_ratelimit/` for the declarative config patterns.

**source_pointer:** `github.com/envoyproxy/ai-gateway` (open source, Go, Apache 2.0), `aigateway.envoyproxy.io/docs/`

**priority:** P1 — CEL-based MCP auth and BackendTrafficPolicy CRD are directly applicable to Verso's tool-governance layer; token rate limiting schema is a concrete design reference.

---

### TrueFoundry AI Gateway

**what:** Enterprise gateway (TypeScript/Hono, closed source for control plane). Notable architecture: NATS as config bus between control plane and gateway pods; all auth/rate-limit/routing checks are in-memory (no DB on hot path); sliding window token bucket (5-second granularity, 12 buckets per 60-second window); sticky routing for KV cache optimization; 250+ RPS per pod on 1 vCPU / 1 GB RAM with ~3ms added latency.

**why_for_verso:** Two specific patterns: (1) The NATS-based config bus — Verso's durable mode needs a mechanism to push updated routing/budget policies to running agents without restart; NATS pub/sub with 10-minute full republish for eventual consistency is a clean design for this. (2) The sliding window token bucket (5-second granularity, 12-bucket sum) is the exact algorithm Verso should implement for per-run token budgets — it's more precise than per-minute limits and handles bursty agent workloads correctly. The KV-cache sticky routing (route to same provider instance to hit warm KV cache) is a low-level optimization relevant to Verso's context engineering layer.

**what_to_RE:** (1) `truefoundry.com/docs/platform/gateway-plane-architecture` — NATS message schema (exact fields: input tokens, output tokens, latency, cost, model name), config event types, republish frequency. (2) Sliding window token bucket: exact bucket granularity, how sub-minute limits are expressed in config, overflow behavior. (3) Sticky routing for KV cache: how provider instance affinity is tracked, TTL of sticky assignment, what breaks affinity (provider down → reassign). (4) `github.com/truefoundry` — any open-source repos (infrastructure charts, SDK) that reveal internal interfaces.

**source_pointer:** `truefoundry.com/docs/` (partially documented, closed source), `github.com/truefoundry` (infra charts may be public)

**priority:** P2 — NATS config bus and sliding window bucket are useful patterns but not unique to TrueFoundry; document only if other targets don't cover these.

---

### vLLM Semantic Router

**what:** Open-source (Apache 2.0), 600+ PRs merged since Sept 2025, Iris v0.1 released Jan 2026. Signal-driven routing for Mixture-of-Models: routes based on request characteristics (task type, complexity, modality) to heterogeneous backends (vLLM, OpenAI, Anthropic, Azure, Bedrock, Gemini). Deployed as an Envoy External Processor. Paper: arxiv `2603.04444`. Safety signals: jailbreak detection, PII filtering, hallucination detection as routing conditions.

**why_for_verso:** This is the most complete open-source implementation of semantic routing as infrastructure (not application-layer). Deploying routing as an Envoy External Processor means the routing logic is observable, configurable, and decoupled from agent code — exactly the architecture Verso's provider edge should aspire to. The safety-signal-as-routing-condition pattern (jailbreak → reroute to safe model, PII → reroute to on-prem) is directly applicable to Verso's guardrail layer. The "When to Reason" paper (arxiv `2510.08731`) — routing between thinking and non-thinking modes — is a direct template for Verso's ReAct loop: should this step use extended thinking?

**what_to_RE:** (1) `vllm-project/semantic-router` — signal pipeline: what signals are extracted from requests, how they're encoded, the routing decision function. (2) Envoy External Processor integration: the gRPC service interface, how routing decisions are returned to Envoy, latency budget for the routing call. (3) Safety signal implementation: jailbreak detection model (what model, what threshold), PII filtering approach, how these signals gate routing vs model selection. (4) arxiv `2603.04444` — full paper for the signal-driven routing formulation and the Mixture-of-Modality routing algebra.

**source_pointer:** `github.com/vllm-project/semantic-router` (open source, Apache 2.0), arxiv `2603.04444`, `blog.vllm.ai/2026/01/05/vllm-sr-iris.html`

**priority:** P1 — semantic routing as Envoy External Processor is a strong architecture reference; "When to Reason" paper directly shapes Verso's ReAct step routing.

---

## Notes

**What this category teaches Verso at the framework level:**

1. **Provider edge design** — the unit is not "call model X" but "call model role R with failover chain [X, Y, Z] and budget $B". Portkey's `tryTargetsRecursively`, Bifrost's weighted key selector, and Vercel's model-alias-to-provider-list pattern all converge on this. Verso should build this as a first-class `ProviderEdge` type, not leave it to users.

2. **Budget enforcement granularity** — every mature gateway enforces budgets at three levels: per-request token count (immediate), per-window rolling count (sliding bucket), per-run dollar cap (async check). Verso's context layer needs all three. TrueFoundry's 5-second granularity sliding window is the right middle layer.

3. **Routing as a signal pipeline, not a config file** — Not Diamond and vLLM Semantic Router both treat routing as an ML inference step (embed prompt → score against model capabilities). Verso's router primitive should support a pluggable `route(context) -> ModelSpec` interface that defaults to config-based rules but can be swapped for a learned classifier.

4. **The ConditionalRouter operator semantics** (from Portkey, now fully documented in teardown) are the canonical reference for how to express routing rules. Cloudflare's node-graph schema is the visual encoding of the same semantics. Both are good design references for Verso's routing DSL.

5. **Already-covered gap**: LiteLLM's `usage-based-routing-v2` (Redis-atomic TPM/RPM, §B.6 of teardown) is the most complete OSS implementation of production-safe budget enforcement. Read that section before any gateway RE work.

**Targets deliberately excluded:**
- Requesty — closed, no distinguishing architecture vs Portkey/LiteLLM; marketing-first, no RE surface worth the time.
- Databricks Unity AI Gateway — interesting (MCP governance, CEL policies) but deeply tied to Unity Catalog; Envoy AI Gateway covers the same CEL-MCP pattern in open-source form.
- ORQ, Nexos — already covered in teardowns.
- Helicone observability platform (the main `helicone/helicone` repo) — separate from the AI gateway; covered by general observability RE if needed.
