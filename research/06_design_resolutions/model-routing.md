# Model layer + routing — Verso Design Resolution

**Subsystem:** `model/` (`‹edge1›` pluggable provider edge)
**PRD section:** §6.4
**Sources:** `03_teardowns/infra-model-gateways.md` (primary) + cross-refs to `infra-model-routing.md`
  (OpenRouter, LiteLLM), researchfms `BIFROST.md` / `PORTKEY.md` / `KONG_AI_GATEWAY.md`

---

## Decisions resolved

### D1 — ProviderProfile shape: hooks + OMIT sentinel

**Choice:**
`ProviderProfile` is a `dataclass` with five polymorphic hooks plus an `OMIT` sentinel that
communicates three-state intent: use provider default / strip field entirely / override with value.

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

# Three-state sentinel for optional fields on a provider request
class _OmitType:
    """Field-level sentinel: strip this key from the outgoing request body."""
    _instance = None
    def __new__(cls): return cls._instance or super().__new__(cls)
    def __repr__(self): return "OMIT"
OMIT = _OmitType()
_OmitType._instance = OMIT   # singleton

@dataclass
class ProviderProfile:
    """Per-provider adapter — the four-method contract from LiteLLM's Config, trimmed."""
    name: str                    # e.g. "anthropic", "openai", "google"
    base_url: str                # canonical endpoint root
    api_version: str | None = None   # e.g. Anthropic "2023-06-01"

    # --- 5 polymorphic hooks (all have sensible defaults) ---

    def prepare_messages(
        self,
        messages: list[dict],
        system: str | None,
    ) -> tuple[list[dict], str | None]:
        """Reorder/split messages for this provider's message-format requirements.

        Default: identity (OpenAI shape). Anthropic override: extract system messages
        to the top-level `system` param. Google override: rename `role:assistant→model`.
        Return (messages, system_param) where system_param=OMIT means omit from body.
        """
        return messages, system

    def build_extra_body(
        self,
        *,
        effort: str | None,          # "low"|"medium"|"high"
        thinking_tokens: int | None, # computed from effort mapping
        tools: list[dict] | None,
        require_parameters: bool,
    ) -> dict[str, Any]:
        """Return provider-specific body keys (merged into the outgoing request).

        Examples: Anthropic adds `{"thinking": {"type":"enabled","budget_tokens": N}}`;
        OpenAI adds `{"reasoning_effort": effort}`. Keys whose value is OMIT are stripped
        before dispatch.
        """
        return {}

    async def fetch_models(self, api_key: str) -> list[str]:
        """Return available model ids for capability/require_parameters checking."""
        return []

    def normalize_response(self, raw: dict) -> dict:
        """Translate provider-native response into OpenAI-shaped dict."""
        return raw

    def normalize_error(self, status: int, body: dict) -> "ProviderError":
        """Map provider error body to a typed ProviderError (see D3 error taxonomy)."""
        from verso.model.errors import ProviderError
        return ProviderError.from_status(status, body)
```

**Rationale:**
LiteLLM's four-method `Config` (`transform_request`, `transform_response`, `get_error_class`,
`get_supported_openai_params`) proved this shape scales to 100+ providers without monolith growth.
The `OMIT` sentinel avoids `None`-ambiguity: `None` means "pass None" (valid for optional params);
`OMIT` means "strip the key" (needed for Anthropic top-level `system`, for `tools` when a
provider doesn't support function calling, for `reasoning_effort` on non-OpenAI). This is cleaner
than LiteLLM's `drop_params` global flag and Hermes's `...` placeholder (researchfms
`HERMES_DEEP_GATEWAY.md`).

Five hooks (vs LiteLLM's four) because `fetch_models` is needed for `require_parameters=True`
validation at init time — cheaper than a runtime 422 mid-agent-run.

**Evidence:**
- `infra-model-routing.md` §LiteLLM, `litellm/llms/base.py` — four-method Config contract
- `infra-model-gateways.md` §Helicone providers.yaml + model-mapping.yaml — flat registry +
  capability-class-tiered equivalence table
- `infra-model-gateways.md` §Envoy `ai_gateway_route.go:214-291` — per-backend `schema` field
  (OpenAI / AWSBedrock / ...) driving dialect translation
- PRD §6.4: "sit above a thin provider abstraction; OpenAI request shape is canonical"

**Alternatives rejected:**
- Subclass-per-provider (LangChain style) — deep inheritance, hard to swap at runtime, DI
  injection is cleaner for a pluggable edge.
- Single mega-normalization function with a `provider` switch — becomes Portkey's 592K-LOC
  monolith trap.

---

### D2 — Default load-balancing algorithm: PeakEWMA + P2C

**Choice:**
Default strategy for multi-provider selection within a ModelPolicy is **PeakEWMA + Power-of-Two-
Choices**. Constants: `decay_τ = 30s`, `seed_rtt = 250ms`. The cost metric per endpoint is
`rtt_ewma × (outstanding + 1)`. Pick two distinct healthy providers at random; route to the lower
cost.

```python
import math, random, time, threading

class PeakEwmaEndpoint:
    """Per-provider load estimate. Thread-safe via a lock on state mutation."""
    def __init__(self, name: str, default_rtt: float = 0.250, decay: float = 30.0):
        self.name = name
        self._rtt = default_rtt      # seconds
        self._decay = decay          # decay window τ in seconds (Helicone: 30s)
        self._at = time.monotonic()
        self._outstanding = 0
        self._healthy = True
        self._lock = threading.Lock()

    @property
    def healthy(self) -> bool:
        return self._healthy

    def load(self) -> float:
        """cost = decayed_rtt × (outstanding + 1). Lower = better."""
        with self._lock:
            now = time.monotonic()
            d = math.exp(-(now - self._at) / self._decay)
            self._rtt *= d           # lazy decay toward 0 since last update
            self._at = now
            return self._rtt * (self._outstanding + 1)

    def on_start(self) -> None:
        with self._lock:
            self._outstanding += 1

    def on_complete(self, observed_rtt: float) -> None:
        """Call when the provider call finishes. observed_rtt = wall-clock seconds."""
        with self._lock:
            if self._rtt < observed_rtt:
                self._rtt = observed_rtt          # PEAK: jump UP instantly on slowdown
            else:
                now = time.monotonic()
                d = math.exp(-(now - self._at) / self._decay)
                self._rtt = self._rtt * d + observed_rtt * (1 - d)  # EWMA: decay DOWN
                self._at = now
            self._outstanding = max(0, self._outstanding - 1)

def p2c_pick(endpoints: list[PeakEwmaEndpoint]) -> PeakEwmaEndpoint | None:
    """Power-of-Two-Choices. Pick two distinct healthy endpoints, route to lower load."""
    ready = [e for e in endpoints if e.healthy]
    if not ready:
        return None
    if len(ready) == 1:
        return ready[0]
    a, b = random.sample(ready, 2)
    return a if a.load() <= b.load() else b
```

**Constants (KNOWN from `ai-gateway/src/config/discover.rs:37-43`):**
- `decay_τ = 30s` (Helicone `default_discover_decay`)
- `seed_rtt = 250ms` (Helicone `default_rtt`)
- Update trigger: `CompleteOnResponse` — on full response received, not TTFB

**Rationale:**
The asymmetric "peak" update is the entire insight: react to a provider getting slow *instantly*
(jump up), but trust recovery only after `exp(-Δ/τ)` decay (earn back traffic slowly). A naive
symmetric EWMA lets a briefly-recovered provider get immediately stampeded. P2C avoids the
thundering-herd failure of "always route to global-min" — with N concurrent deciders, the
probability any single endpoint is the worse-of-2 for ALL collapses geometrically (Mitzenmacher
result). Bifrost (`researchfms/BIFROST.md`) also chose P2C for the same reason, cross-validating
the choice independently.

**Evidence:**
- `infra-model-gateways.md` §Helicone §P2C+PeakEWMA — exact source (`discover.rs:37-43`,
  `peak_ewma.rs:236-281`)
- researchfms `BIFROST.md` — independent P2C adoption for identical reasoning

**Alternatives rejected:**
- Round-robin — ignores latency, treats all providers as equally healthy.
- Global-least-loaded — thundering herd under concurrency.
- `sort: 'ttft'` (Vercel-style latency sort) — good for single-request, not for concurrent agent
  workloads where per-endpoint outstanding count matters.

---

### D3 — Cross-model failover: two-axis model×provider + error-typed chains

**Choice:**
Failover is a two-axis nested search: **backup models** (`models[]`) × **provider order**
(`providers[]`), executed strictly sequential, first-success-wins. Error classification governs
which axis to advance on.

```python
from dataclasses import dataclass, field
from enum import Enum

class ErrorClass(Enum):
    RATE_LIMIT      = "rate_limit"         # 429 → try next provider for same model
    CONTEXT_WINDOW  = "context_window"     # prompt too long → try next MODEL
    CONTENT_POLICY  = "content_policy"     # safety refusal → try next MODEL
    SERVER_ERROR    = "server_error"       # 5xx → try next provider
    TIMEOUT         = "timeout"            # → try next provider
    MALFORMED_TOOL  = "malformed_tool"     # tool call parse failure → try model with known-good tool support
    AUTH            = "auth"               # 401/403 → do NOT retry (permanent)

@dataclass
class ModelSpec:
    provider: str    # e.g. "anthropic"
    model: str       # e.g. "claude-sonnet-4-6"
    canonical_slug: str  # e.g. "anthropic/claude-sonnet-4-6"

@dataclass
class ModelPolicy:
    """Per-node routing policy. Attached to Agent or individual steps."""
    primary: ModelSpec
    models: list[ModelSpec] = field(default_factory=list)  # ordered backup models
    providers: list[str] = field(default_factory=list)     # preferred provider order
    only: list[str] = field(default_factory=list)          # hard provider whitelist
    sort: str | None = None                                # "cost"|"ttft"|"tps"|None
    require_parameters: bool = True                        # CRITICAL: enforce tool support
    data_collection: bool | None = None                    # opt-out of provider training
    max_price_per_1k_tokens: float | None = None           # hard cost ceiling per call
    # Error-typed overrides: which models to prefer on specific error classes
    on_context_window: list[ModelSpec] = field(default_factory=list)
    on_content_policy: list[ModelSpec] = field(default_factory=list)
    on_malformed_tool: list[ModelSpec] = field(default_factory=list)
```

**Failover algorithm (adapted from Vercel two-level + Portkey `tryTargetsRecursively`):**

```python
async def call_with_failover(
    policy: ModelPolicy,
    request: ProviderRequest,
    registry: "ProviderRegistry",
) -> tuple["ProviderResponse", list["AttemptRecord"]]:
    attempts: list[AttemptRecord] = []
    # Build candidate list: [primary] + error-class overrides + policy.models
    candidate_models = _resolve_candidates(policy, request)

    for model_spec in candidate_models:
        providers_for_model = _resolve_providers(model_spec, policy, registry)
        for provider_name in providers_for_model:
            start = time.monotonic()
            try:
                resp = await registry.call(provider_name, model_spec, request)
                attempts.append(AttemptRecord(
                    canonical_slug=model_spec.canonical_slug,
                    provider=provider_name,
                    success=True,
                    response_time_ms=(time.monotonic() - start) * 1000,
                    status_code=200,
                ))
                return resp, attempts
            except ProviderError as e:
                attempts.append(AttemptRecord(
                    canonical_slug=model_spec.canonical_slug,
                    provider=provider_name,
                    success=False,
                    response_time_ms=(time.monotonic() - start) * 1000,
                    status_code=e.status_code,
                    error_class=e.error_class,
                    error_message=str(e),
                ))
                if e.error_class == ErrorClass.AUTH:
                    raise  # permanent, don't continue
                if e.error_class in (ErrorClass.CONTEXT_WINDOW, ErrorClass.CONTENT_POLICY,
                                      ErrorClass.MALFORMED_TOOL):
                    break  # advance to next MODEL, not next provider
                # else: RATE_LIMIT / SERVER_ERROR / TIMEOUT → try next provider
    raise AllProvidersExhausted(attempts)
```

**Error-typed routing rules:**
| ErrorClass | Action | Rationale |
|---|---|---|
| `RATE_LIMIT` | Next provider for same model | Same-model retry on different provider |
| `CONTEXT_WINDOW` | Jump to `on_context_window` chain | Different model is needed |
| `CONTENT_POLICY` | Jump to `on_content_policy` chain | Different model may accept |
| `MALFORMED_TOOL` | Jump to `on_malformed_tool` chain | Provider lacks tool support |
| `SERVER_ERROR` / `TIMEOUT` | Next provider for same model | Transient |
| `AUTH` | Raise immediately | Permanent — no point retrying |

**Evidence:**
- `infra-model-gateways.md` §Vercel — `models[]` × `order[]` two-axis failover + `modelAttempts`
  audit trail (verbatim schema extracted)
- `infra-model-routing.md` §Portkey — `tryTargetsRecursively` error classification
- PRD §6.4: "error-typed fallback lists (context-window vs content-policy vs general)"
- researchfms `OPENROUTER.md` §ProviderPreferences — `require_parameters` field to exclude
  providers that drop `tools`

**Alternatives rejected:**
- Same-model retry only — repeats the same failure mode. "Same-model retry repeats failures"
  (PRD §6.4).
- Flat fallback list without error-typing — `CONTEXT_WINDOW` should jump model, not retry the
  same model on a different provider that also can't fit the prompt.

---

### D4 — `require_parameters=True`: enforcement point

**Choice:**
`require_parameters=True` is enforced at **policy resolution time** (before the first call), not
inline on error. At `Agent.__init__`, the registry validates that every model in `primary` +
`models[]` satisfies the features the agent needs. A model that doesn't support `tools` when the
agent has tools registered is removed from the candidate list with a warning — it is never reached
in the failover chain.

```python
def _validate_policy(
    policy: ModelPolicy,
    agent_has_tools: bool,
    registry: "ProviderRegistry",
) -> ModelPolicy:
    """Filter out candidates that can't serve this agent's requirements."""
    required_caps = set()
    if agent_has_tools:
        required_caps.add("tools")
    if policy.require_parameters:
        valid_primary = _check_caps(policy.primary, required_caps, registry)
        if valid_primary is None:
            raise PolicyConfigError(
                f"{policy.primary.canonical_slug} does not support {required_caps}. "
                "Set require_parameters=False to allow (loop will break on malformed tool calls)."
            )
        valid_fallbacks = [m for m in policy.models
                           if _check_caps(m, required_caps, registry) is not None]
        if len(valid_fallbacks) < len(policy.models):
            warnings.warn(
                f"{len(policy.models) - len(valid_fallbacks)} fallback model(s) dropped: "
                "do not support required capabilities."
            )
        return replace(policy, models=valid_fallbacks)
    return policy
```

**Rationale:**
OpenRouter's `ProviderPreferences.require_parameters` ("Only use providers that support all
parameters in the request" — `infra-model-routing.md`) prevents the silent failure mode where a
fallback provider strips `tools`, the model responds with plain text instead of a tool call, and
the loop breaks with no error. That failure mode is impossible to diagnose post-hoc. Catching it at
init is always better than catching it mid-run.

**Evidence:**
- `infra-model-routing.md` §OpenRouter §ProviderPreferences — `require_parameters: true` field
  spec
- PRD §6.4: "`require_parameters=True` is CRITICAL for tool agents (a fallback provider that
  silently drops `tools` returns text instead of a tool call and breaks the loop with no error)"

---

### D5 — Budget guard: unified Limit node, check-before/charge-after

**Choice:**
A single `BudgetGuard` with `limit_type: "count" | "cost"` unifies request-rate and dollar-budget
enforcement. Check before dispatch (admit if headroom exists); charge after response with actual
cost. Exceed → reroute to fallback model, **never error**.

```python
import time
from dataclasses import dataclass
from typing import Protocol

class BudgetStore(Protocol):
    """Pluggable backend — Redis in prod, in-memory dict in dev."""
    async def get(self, key: str) -> float: ...
    async def incr(self, key: str, amount: float, window_s: int) -> None: ...

@dataclass
class BudgetGuard:
    store: BudgetStore
    limit: float          # e.g. 5.00 ($) or 1000 (requests)
    window_s: int         # rolling window in seconds
    limit_type: str = "cost"   # "cost" | "count"
    fail_open: bool = True     # if store unavailable, admit (don't block the agent)

    def _key(self, run_key: str) -> str:
        bucket = int(time.time()) // self.window_s
        return f"budget:{self.limit_type}:{run_key}:{bucket}"

    async def admit(self, run_key: str, est_cost: float = 0.0) -> bool:
        """CHECK before dispatch. Returns True if the request is within budget."""
        try:
            spent = await self.store.get(self._key(run_key))
            charge = est_cost if self.limit_type == "cost" else 1.0
            return (spent + charge) <= self.limit
        except Exception:
            return self.fail_open   # store error → admit (fail-open)

    async def charge(self, run_key: str, actual_cost: float) -> None:
        """CHARGE after response completes (or after end-of-stream for streaming)."""
        amount = actual_cost if self.limit_type == "cost" else 1.0
        try:
            await self.store.incr(self._key(run_key), amount, self.window_s)
        except Exception:
            pass   # store error → swallow, don't fail the response path

    @staticmethod
    def cache_aware_cost(
        input_tokens: int,
        cached_tokens: int,
        cache_creation_tokens: int,
        output_tokens: int,
        reasoning_tokens: int,
        *,
        input_rate: float,         # $/token
        output_rate: float,
        cache_read_multiplier: float = 0.1,
        cache_write_multiplier: float = 1.25,
    ) -> float:
        """Cache-aware dollar cost. Envoy CEL formula verbatim (ai_gateway_route.go).

        Anthropic cache pricing: cached reads at 0.1×, cache creation at 1.25×.
        Adjust multipliers per provider.
        """
        return (
            (input_tokens - cached_tokens) * input_rate
            + cached_tokens * input_rate * cache_read_multiplier
            + cache_creation_tokens * input_rate * cache_write_multiplier
            + output_tokens * output_rate
            + reasoning_tokens * output_rate  # reasoning tokens billed as output
        )
```

**Integration with the routing DSL:**
```
On each provider call:
  1. guard.admit(run_key, est_cost=max_tokens * output_rate)
     → False: route to fallback model (cheaper tier or end), NOT raise
  2. call primary model (force stream_options.include_usage=true — see D8)
  3. guard.charge(run_key, actual_cost=cache_aware_cost(...)) at end-of-stream
```

**Evidence:**
- `infra-model-gateways.md` §Cloudflare — `rate` node, `limitType: "count"|"cost"`,
  `success`/`fallback` edges, "exceed → reroute not error"
- `infra-model-gateways.md` §Envoy — `cost.request=0` (check) / `cost.response=metadata`
  (charge), `BackendTrafficPolicy` token budget example
- `infra-model-gateways.md` §Vercel — "in-region Redis quota, async batched write-back"
- `infra-model-gateways.md` §Envoy CEL formula — `(input−cached)·rate + cached·0.1 + cc·1.25 +
  output`

**Alternatives rejected:**
- Pre-charge (reserve est_cost before call, reconcile after) — complex, hard to get right in
  async streams, not how any RE'd system does it.
- Separate `RateLimitGuard` and `BudgetGuard` classes — the Cloudflare architecture proves these
  are the same node with `limitType` discriminating; splitting doubles the code for no benefit.
- Error on budget exceed — degrades UX sharply; reroute-to-cheaper is always better for an agent.

---

### D6 — Routing algorithm: default rule-based, learned routing as opt-in

**Choice:**
**Default:** priority-ranked rule-based routing from `ModelPolicy` fields (provider order, sort,
only, error-typed chains). This is synchronous, keyless, zero-latency.

**Opt-in learned routing:** `ModelPolicy.learned_router: LearnedRouter | None = None`. When set,
`route(context) → ModelSpec` is called before the PeakEWMA-P2C selection. Two implementations
ship in-box:
1. `RoRFRouter` — pickled `sklearn.RandomForestClassifier` over Jina-v3 local embeddings
2. `ConfidenceCascade` — run cheap model; if `0.65·logprob + 0.35·margin < threshold`, escalate

```python
from dataclasses import dataclass
from typing import Protocol

class LearnedRouter(Protocol):
    """Pluggable route(context) → ModelSpec contract."""
    async def route(self, messages: list[dict]) -> "ModelSpec | None":
        """Return the preferred ModelSpec, or None to fall through to default."""
        ...

@dataclass
class RoRFRouter:
    """Not Diamond RoRF: embed → 4-class RF → threshold → model_a or model_b.

    Runs locally via Jina-v3 (no API key, no GPU).
    classifier_path: local .pkl or HuggingFace repo id (auto-downloaded).
    """
    model_a: "ModelSpec"   # strong / expensive model
    model_b: "ModelSpec"   # cheap / fast model
    threshold: float       # calibrate via RoRFRouter.calibrate_threshold()
    _classifier = None
    _embed_model = None

    def _lazy_load(self):
        import pickle
        from transformers import AutoModel
        if self._classifier is None:
            self._classifier = pickle.load(open(self.classifier_path, "rb"))
        if self._embed_model is None:
            self._embed_model = AutoModel.from_pretrained(
                "jinaai/jina-embeddings-v3", trust_remote_code=True
            )

    async def route(self, messages: list[dict]) -> "ModelSpec | None":
        import asyncio, numpy as np
        self._lazy_load()
        prompt = " ".join(m.get("content", "") for m in messages if m.get("role") == "user")
        loop = asyncio.get_event_loop()
        emb = await loop.run_in_executor(
            None,
            lambda: self._embed_model.encode([prompt], task="classification")
        )
        probs = self._classifier.predict_proba(np.asarray(emb))[0]
        # 4-class label: 0=A-wins, 1=both-fail, 2=both-win, 3=B-wins
        # "send to A when A wins OR when both fail (give the hard ones to strong)"
        model_a_prob = probs[0] + probs[1]
        return self.model_a if model_a_prob >= self.threshold else self.model_b

    @staticmethod
    def calibrate_threshold(win_rates: list[float], target_a_pct: float) -> float:
        """Set threshold so target_a_pct fraction of calls go to model_a.

        win_rates: list of model_a_prob values from a calibration corpus.
        target_a_pct: e.g. 0.30 → 30% of traffic to the expensive model.
        """
        import numpy as np
        return float(np.quantile(win_rates, q=1.0 - target_a_pct))


@dataclass
class ConfidenceCascade:
    """vLLM SR small→large escalation: run cheap model; escalate if low confidence.

    confidence = logprob_weight * mean_logprob + margin_weight * answer_margin
    Constants from vLLM SR config.yaml: logprob_weight=0.65, margin_weight=0.35, threshold=0.72.
    """
    small: "ModelSpec"
    large: "ModelSpec"
    threshold: float = 0.72
    logprob_weight: float = 0.65
    margin_weight: float = 0.35

    def confidence(self, logprobs: list[float], margin: float) -> float:
        import math
        mean_lp = sum(logprobs) / len(logprobs) if logprobs else -math.inf
        return self.logprob_weight * math.exp(mean_lp) + self.margin_weight * margin
```

**Rationale:**
Not Diamond RoRF proved the entire learned routing path is: embed(prompt) → RF.predict_proba →
4-class label group → threshold. It runs in <1ms on CPU (jina-v3 is the only dep; no API key).
The 4-class grouping (send to strong when A-wins OR both-fail; send to cheap when both-win or
B-wins) is the non-obvious insight most hand-rolled routers miss. `threshold = quantile(win_rates,
1 - target_a_pct)` is the exact cost/quality knob, calibrated on the team's own traffic.

Confidence cascade complements RoRF: where RoRF predicts up-front which model will win,
confidence cascade uses the cheap model's own output quality to decide whether to escalate. vLLM SR
constants (`0.65 logprob + 0.35 margin, threshold 0.72`) are directly usable.

Both are behind the `LearnedRouter` protocol so neither is mandatory — rule-based routing is the
default and always works without any ML dependency.

**Evidence:**
- `infra-model-gateways.md` §Not Diamond §RoRF — `controller.py:81-104`, 4-class label
  (`dataloader.py:60-81`), threshold calibration (`calibrate_threshold.py`), Jina-v3 local
  embeddings (`embeddings.py`)
- `infra-model-gateways.md` §vLLM SR §Decisions DSL — `confidence_method: hybrid`,
  `hybrid_weights: {logprob_weight: 0.65, margin_weight: 0.35}`, `threshold: 0.72`
- PRD §6.4: "A first-class... Not Diamond as opt-in"

**Alternatives rejected:**
- IRT-Router as default — needs a trained embedding+linear projection per model pair; too heavy for
  initial setup; adopt as an upgrade path after the eval corpus exists.
- Always-on learned routing — adds a latency step to every call; opt-in keeps the hot path cheap.

---

### D7 — Reasoning-effort dial: effort level → token budget, per provider

**Choice:**
`effort: "low" | "medium" | "high"` is the user-facing knob. The framework maps it to
provider-specific parameters. The mapping is per-`ProviderProfile`, overridable.

```python
# Default effort → token mapping (tunable per deployment)
EFFORT_TOKENS: dict[str, int] = {
    "low":    1_024,
    "medium": 8_192,
    "high":   32_768,
}

# Per-provider build_extra_body implementations:

class AnthropicProfile(ProviderProfile):
    def build_extra_body(self, *, effort, thinking_tokens, tools, require_parameters):
        body = {}
        if effort is not None and thinking_tokens:
            body["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_tokens,
            }
        if tools and require_parameters:
            body["tools"] = tools
        return body

class OpenAIProfile(ProviderProfile):
    def build_extra_body(self, *, effort, thinking_tokens, tools, require_parameters):
        body = {}
        if effort is not None:
            body["reasoning_effort"] = effort  # "low"|"medium"|"high" → o-series models
        if tools and require_parameters:
            body["tools"] = tools
        return body

class GoogleProfile(ProviderProfile):
    def build_extra_body(self, *, effort, thinking_tokens, tools, require_parameters):
        body = {}
        if effort is not None and thinking_tokens:
            body["generationConfig"] = {
                "thinkingConfig": {"thinkingBudget": thinking_tokens}
            }
        return body
```

**Per-step reasoning gate (the "When to Reason" pattern):**
The effort dial should be driven per-step by a lightweight complexity signal, not set globally per
run. Default: `effort=None` (provider default). The `should_reason(messages, step_n)` helper
classifies whether the current step needs extended thinking.

```python
# Constants from vLLM SR config.yaml + "When to Reason" arXiv 2510.08731
REASONING_HARD_CANDIDATES = [
    "complex reasoning", "multi-step math", "logical deduction",
    "proof", "theorem", "counterexample", "algorithm design",
]
REASONING_EASY_CANDIDATES = [
    "simple lookup", "factual question", "summarize", "reformat",
    "translate", "yes or no",
]
REASONING_THRESHOLD = 0.75   # similarity threshold to fire needs_reasoning signal

def should_reason_step(messages: list[dict], threshold: float = REASONING_THRESHOLD) -> bool:
    """Return True if this step should use extended thinking.

    Implements vLLM SR complexity.needs_reasoning: embed the last user/tool message,
    compare cosine-sim to hard/easy candidate phrases, fire if hard-sim > threshold.
    In a fast path without an embedder, fall back to keyword presence.
    """
    last_content = " ".join(
        m.get("content", "") for m in messages[-3:] if m.get("role") in ("user", "tool")
    )
    # Keyword fast-path (no embedder required)
    hard_hits = sum(kw in last_content.lower() for kw in REASONING_HARD_CANDIDATES)
    easy_hits = sum(kw in last_content.lower() for kw in REASONING_EASY_CANDIDATES)
    return hard_hits > easy_hits
```

**Why this matters:** The "When to Reason" arXiv `2510.08731` result (vLLM SR teardown):
always-on extended thinking vs selective: **+10.2pp accuracy on MMLU-Pro**, **−47.1% latency**,
**−48.5% token consumption**. Over-thinking *hurts* on easy steps; the per-step gate is both
cheaper AND more accurate.

**Evidence:**
- `infra-model-gateways.md` §vLLM SR §"When to Reason" — arXiv 2510.08731, constants `0.75`
  threshold, +10.2pp / −47.1% / −48.5% numbers
- `infra-model-gateways.md` §vLLM SR §Decisions DSL — `use_reasoning: true`,
  `reasoning_effort: medium|high` on modelRefs
- PRD §6.4: "Reasoning-effort dial as a first-class knob (`effort="low|medium|high"` → token
  mapping)"

---

### D8 — Cache-sticky routing + force usage on streaming

**Choice (two mechanics, one rule):**

**Cache-sticky routing:** once a provider serves a request successfully, *prefer* that provider for
the next N steps in the same run. This preserves KV-cache state on the provider's side — a context
restart with a different provider is a full cache miss even if the new provider is otherwise
identical. Implementation: extend `ModelPolicy` with `cache_sticky_steps: int = 5`; store the
last-serving provider per run-id in `RunContext`; on the next call, promote it to front of the
provider list.

```python
@dataclass
class RoutingState:
    """Mutable routing state stored in RunContext. Not persisted beyond a run."""
    last_provider: str | None = None
    last_model: str | None = None
    sticky_steps_remaining: int = 0
    total_attempts: int = 0

def promote_sticky_provider(
    providers: list[str],
    state: RoutingState,
    sticky_steps: int,
) -> list[str]:
    """Move the last-used provider to the front of the candidate list if still within sticky window."""
    if state.last_provider and state.sticky_steps_remaining > 0 and state.last_provider in providers:
        state.sticky_steps_remaining -= 1
        return [state.last_provider] + [p for p in providers if p != state.last_provider]
    return providers
```

**Force `stream_options.include_usage=true`:** every outgoing request to a streaming endpoint must
have this flag injected by the provider adapter, regardless of what the caller requested. Token and
cost accounting cannot be bypassed.

```python
class ProviderAdapter:
    def prepare_request(self, req: dict, *, stream: bool) -> dict:
        if stream:
            req = dict(req)
            req.setdefault("stream_options", {})
            req["stream_options"]["include_usage"] = True  # FORCE, per Envoy pattern
        return req
```

Usage is accumulated from the **final streaming chunk** (the chunk where `finish_reason` is set),
charged to the `BudgetGuard` after stream completes.

**Evidence:**
- `infra-model-routing.md` §OpenRouter — "prompt-cache stickiness" field, provider cache-sticky
  logic
- `infra-model-gateways.md` §Envoy `processor_impl.go:335-339` — force body mutation
  `stream_options.include_usage=true`; charge only at `body.EndOfStream==true`
- `infra-model-gateways.md` §Vercel — `caching: 'auto'` provider-aware cache-marker injection

---

### D9 — Retry defaults + tool-name sanitization

**Choice:**
Retry defaults from Helicone + OpenHands cross-validation:
- `attempts = 6` (PRD §6.4, "battle-tested")
- `initial_delay_s = 4.0`
- `max_delay_s = 240.0`
- `factor = 2.0`
- `jitter = True` (always — avoids retry-storm synchronization)

Tool-name sanitization: `/` and `.` → `_` in tool names before sending to providers; maintain a
reverse map to restore original names in the loop.

```python
import asyncio, random, math

async def call_with_retry(
    fn,
    *,
    attempts: int = 6,
    initial_delay: float = 4.0,
    max_delay: float = 240.0,
    factor: float = 2.0,
    jitter: bool = True,
    retryable: set[str] | None = None,
):
    """Exponential backoff + jitter. retryable: set of ErrorClass values to retry."""
    if retryable is None:
        retryable = {ErrorClass.RATE_LIMIT, ErrorClass.SERVER_ERROR, ErrorClass.TIMEOUT}
    delay = initial_delay
    last_exc = None
    for attempt in range(attempts):
        try:
            return await fn()
        except ProviderError as e:
            last_exc = e
            if e.error_class not in retryable or attempt == attempts - 1:
                raise
            actual_delay = delay
            if jitter:
                actual_delay = delay * (0.5 + random.random())  # ±50% jitter
            await asyncio.sleep(actual_delay)
            delay = min(delay * factor, max_delay)
    raise last_exc

def sanitize_tool_name(name: str) -> tuple[str, str]:
    """Return (sanitized, original). Providers reject '/' and '.' in tool names."""
    sanitized = name.replace("/", "_").replace(".", "_")
    return sanitized, name
```

**Evidence:**
- `infra-model-gateways.md` §Helicone §Retry — `RetryConfig {min_delay:1s, max_delay:30s,
  max_retries:2, factor:2.0, with_jitter()}` (OSS default)
- PRD §6.4: "exponential backoff + jitter, `attempts=6, initial=4s, max=240s`"

---

### D10 — Attempt audit trail (modelAttempts/providerAttempts)

**Choice:**
Every `call_with_failover` returns a typed `AttemptRecord` list alongside the response. This is
non-optional — the agent loop and observability layer rely on it for cost attribution and
debugging.

```python
@dataclass
class AttemptRecord:
    canonical_slug: str          # Verso-normalized "provider/model"
    provider: str                # actual provider tried
    model_id: str                # provider-native model id
    attempt_number: int
    success: bool
    status_code: int | None
    response_time_ms: float
    error_class: ErrorClass | None = None
    error_message: str | None = None
    provider_response_id: str | None = None  # e.g. Anthropic msg_01...
    credential_type: str | None = None       # "system" | "byok"
    cost_usd: float | None = None            # filled after charge()

@dataclass
class ProviderResponse:
    content: str | list[dict]    # text or tool calls
    usage: "TokenUsage"
    model_id: str
    provider: str
    attempts: list[AttemptRecord]   # the full audit trail
    finish_reason: str
```

**Evidence:**
- `infra-model-gateways.md` §Vercel — `modelAttempts` / `providerAttempts` schema (verbatim
  extracted), `canonicalSlug` vs `modelId` two-id convention, `credentialType`

---

## Component spec

### Public interfaces

```python
# verso/model/__init__.py  (the surface users touch)

def init_model(model_id: str) -> "ModelHandle":
    """Parse "provider:model" slug → ModelHandle (no I/O at init time).

    provider:model format: "anthropic:claude-sonnet-4-6", "openai:gpt-5.1",
    "google:gemini-3-pro", "groq:llama-3.3-70b-versatile", "ollama:llama3.2".
    """
    ...

class ModelHandle:
    """Bound (provider, model) pair with an attached ProviderProfile.

    Not a connection — no state until a call is made.
    """
    canonical_slug: str
    profile: ProviderProfile

class ModelPolicy:
    """Per-agent or per-step routing policy (dataclass, frozen=True)."""
    primary: ModelSpec
    models: list[ModelSpec]           = []
    providers: list[str]              = []
    only: list[str]                   = []
    sort: str | None                  = None    # "cost"|"ttft"|"tps"
    require_parameters: bool          = True
    data_collection: bool | None      = None
    max_price_per_1k_tokens: float | None = None
    on_context_window: list[ModelSpec] = []
    on_content_policy: list[ModelSpec] = []
    on_malformed_tool: list[ModelSpec] = []
    cache_sticky_steps: int           = 5
    learned_router: LearnedRouter | None = None
    budget_guard: BudgetGuard | None  = None

class ProviderRegistry:
    """Holds registered ProviderProfile instances + PeakEWMA state per provider.

    Thread-safe. Profiles registered at startup; state mutated per-call.
    """
    def register(self, profile: ProviderProfile) -> None: ...
    async def call(
        self,
        provider: str,
        model: ModelSpec,
        request: ProviderRequest,
    ) -> ProviderResponse: ...
    def endpoints(self) -> list[PeakEwmaEndpoint]: ...

class ProviderRequest:
    messages: list[dict]
    system: str | None
    tools: list[dict] | None
    effort: str | None              # "low"|"medium"|"high"
    max_tokens: int | None
    stream: bool
    extra: dict                     # pass-through to build_extra_body

class ProviderError(Exception):
    status_code: int
    error_class: ErrorClass
    provider: str
    body: dict
```

### Schema / data types

```python
# verso/model/types.py

@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    @property
    def canonical_slug(self) -> str:
        return f"{self.provider}/{self.model}"
    @classmethod
    def from_string(cls, s: str) -> "ModelSpec":
        # accepts "provider:model" or "provider/model"
        sep = ":" if ":" in s else "/"
        provider, model = s.split(sep, 1)
        return cls(provider=provider, model=model)

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    cache_creation_tokens: int = 0
    reasoning_tokens: int = 0
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

@dataclass
class RoutingState:
    last_provider: str | None = None
    last_model: str | None = None
    sticky_steps_remaining: int = 0
    total_attempts: int = 0
    attempts: list[AttemptRecord] = field(default_factory=list)
```

### Constants / defaults

| Constant | Value | Source |
|---|---|---|
| `PEAK_EWMA_DECAY_S` | `30.0` | Helicone `discover.rs:37` |
| `PEAK_EWMA_SEED_RTT_S` | `0.250` | Helicone `discover.rs:43` |
| `RETRY_ATTEMPTS` | `6` | PRD §6.4 (battle-tested) |
| `RETRY_INITIAL_DELAY_S` | `4.0` | PRD §6.4 |
| `RETRY_MAX_DELAY_S` | `240.0` | PRD §6.4 |
| `RETRY_FACTOR` | `2.0` | Helicone + PRD |
| `CACHE_STICKY_STEPS` | `5` | DESIGNED (sticky across the middle of a run) |
| `BUDGET_FAIL_OPEN` | `True` | Verso — store error must not block the agent |
| `CACHE_READ_MULTIPLIER` | `0.10` | Anthropic cache pricing, Envoy CEL formula |
| `CACHE_WRITE_MULTIPLIER` | `1.25` | Anthropic cache pricing, Envoy CEL formula |
| `REASONING_THRESHOLD` | `0.75` | vLLM SR `complexity.needs_reasoning` threshold |
| `CONFIDENCE_THRESHOLD` | `0.72` | vLLM SR `confidence.threshold` |
| `CONFIDENCE_LOGPROB_W` | `0.65` | vLLM SR `hybrid_weights.logprob_weight` |
| `CONFIDENCE_MARGIN_W` | `0.35` | vLLM SR `hybrid_weights.margin_weight` |
| `RORF_RF_MAX_DEPTH` | `20` | RoRF `trainer.py:29` |
| `RORF_RF_ESTIMATORS` | `100` | RoRF `trainer.py:29` |
| `RORF_EMBED_DIM` | `1024` | Jina-v3 classification embedding dim |
| `EFFORT_LOW_TOKENS` | `1_024` | DESIGNED |
| `EFFORT_MEDIUM_TOKENS` | `8_192` | DESIGNED |
| `EFFORT_HIGH_TOKENS` | `32_768` | DESIGNED |
| `MAX_RETRY_BACKOFF_CF` | `5000ms / 5 attempts` | Cloudflare `cf-aig-*` constraints |
| `BUDGET_WINDOW_DEFAULT_S` | `3600` | Cloudflare Limit node example |

### Module layout

```
verso/model/
  __init__.py          → init_model(), ModelHandle, ModelPolicy, ProviderRegistry
  types.py             → ModelSpec, TokenUsage, AttemptRecord, ProviderResponse,
                         ProviderRequest, RoutingState, ErrorClass, OMIT
  profile.py           → ProviderProfile base class + AnthropicProfile, OpenAIProfile,
                         GoogleProfile, GroqProfile
  balancer.py          → PeakEwmaEndpoint, p2c_pick
  failover.py          → call_with_failover, call_with_retry, _resolve_candidates,
                         _resolve_providers, AllProvidersExhausted
  budget.py            → BudgetGuard, BudgetStore (Protocol), InMemoryBudgetStore,
                         RedisBudgetStore, cache_aware_cost()
  routers/
    __init__.py        → LearnedRouter (Protocol)
    rorf.py            → RoRFRouter, calibrate_threshold()
    cascade.py         → ConfidenceCascade
    knn.py             → KNNRouter (zero-training baseline)
  reasoning.py         → should_reason_step(), EFFORT_TOKENS mapping
  validation.py        → _validate_policy(), require_parameters enforcement
  errors.py            → ProviderError, error taxonomy, normalize_error() per provider
```

---

## Open unknowns

1. **`CACHE_STICKY_STEPS = 5` needs empirical validation.** Too low → cache misses on longer runs;
   too high → prevents healthy failover when a provider degrades mid-run. Dogfood with real
   multi-step agents to calibrate. Possibly make it a function of `max_steps`.

2. **RoRF threshold calibration corpus.** The `calibrate_threshold()` call needs a calibration
   dataset (a set of prompts run against both `model_a` and `model_b` with quality scores). For
   v1 personal use, this means running 200–500 representative tasks and scoring them. No substitute
   for this — the threshold cannot be guessed from first principles.

3. **`should_reason_step` keyword fast-path vs embedder path.** The keyword fast-path is ~0ms but
   coarse. The Jina-v3 embedding path is more accurate but adds ~5–15ms per step. Concrete
   question: does the per-step accuracy improvement from the embedding path justify the latency in
   a ReAct loop where steps are already 1–2s? Measure on real agent traces.

4. **`BudgetStore` in-memory vs Redis boundary.** In-memory is dev-correct and zero-infra, but
   doesn't survive a process restart or work across multiple agent workers. Redis is the right prod
   backend. The question is when to require Redis: v1 dogfood on a single process → in-memory is
   fine; when Verso gains the durable runtime and `submit()` jobs → Redis becomes mandatory for
   cross-process budget enforcement. Defer to Phase 2 (durable runtime).

5. **`ConfidenceCascade` requires logprobs.** Not all provider/model combinations expose per-token
   logprobs (e.g. Anthropic claude does not currently expose them). The margin signal (difference
   between top-2 answer choices) is only meaningful for classification/MCQ tasks. For open-ended
   generation, the confidence signal degenerates to just `mean_logprob`. Needs a fallback for
   providers without logprob access — likely: check `response.model_fields_used` or use a separate
   NLI model (vLLM SR `hallucination` plugin) as the quality signal.

6. **`Percentage` node for A/B model testing.** The Cloudflare node graph includes a `percentage`
   node (weights summing to 100, ≤5 outputs) for canary rollouts of new models. This is not in the
   current `ModelPolicy` shape — it requires routing state to accumulate per-deployment percentages
   (likely a Redis counter) rather than per-request. Defer until there is a concrete use case in
   dogfood.

7. **IRT-Router as upgrade path.** The IRT-Router (`kNN warm-up: e ← 0.5·e + 0.5·e_kNN`, latent
   ability vectors per model) is a better-calibrated long-run router than RoRF, but requires an
   eval corpus of 10K+ (query, model, score) tuples to train. Decision: adopt IRT-Router as the
   Phase 3 router upgrade when Verso's eval harness has accumulated enough traces. The `knn.py`
   `KNNRouter` is the bridge — it runs immediately from any eval corpus, no training needed.

8. **Credential injection architecture.** Envoy AI Gateway shows that `BackendSecurityPolicy`
   (credential injection at the edge, one-of APIKey/AWS-SigV4/Azure/GCP/Anthropic) is the clean
   separation: the agent is key-free, the edge attaches credentials. For v1, credentials are in
   env vars on the `ProviderProfile`; for a multi-tenant Verso deployment, a secrets-store
   injection layer (like Envoy's `BackendSecurityPolicy`) is the right architecture. Defer — v1 is
   single-user/single-process.
