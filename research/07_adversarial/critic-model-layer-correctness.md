# Adversarial Critique — model-layer (CORRECTNESS lens)

**Decision under review:** Build the model layer in-house: ProviderProfile + 5 hooks + OMIT sentinel,
P2C+PeakEWMA load-balancer (decay_τ=30s), two-axis error-typed cross-model failover.

**Lens:** CORRECTNESS — Does the cited RE evidence actually prove this works for Verso's EXACT case
(Python async ReAct loop, non-deterministic LLM steps, the one-flag seam, dogfood scale)?

**Sources verified:** cloned `Helicone/ai-gateway`, `Not-Diamond/RoRF`, `vllm-project/semantic-router`
all `--depth=1`; read `tower-0.5.3` from local cargo cache at
`~/.cargo/registry/src/.../tower-0.5.3/src/load/peak_ewma.rs`.

---

## The Attack

Two independent correctness failures exist in the resolution. The more serious one concerns
`ConfidenceCascade`; the second is a concrete misread of the Tower source in the Python
PeakEWMA reimplementation.

### Failure 1: ConfidenceCascade is mechanically wrong for a ReAct loop (D6)

The resolution presents `ConfidenceCascade` (D6) as a **shipped in-box component** whose constants
come directly from vLLM SR config.yaml (`logprob_weight=0.65, margin_weight=0.35, threshold=0.72`).
This attribution misrepresents what vLLM SR actually does.

**What vLLM SR does:** the `confidence` algorithm in vLLM SR config.yaml
(`decisions: algorithm: type: confidence, escalation_order: small_to_large`) is a **pre-call
routing decision** executed by an Envoy ExtProc filter *before any model call is made*. The
router classifies the *query* to predict which model will win, optionally using cached calibration
data, and routes to the correct model the **first time**. The router does not call a model to get
its logprobs — it has its own lightweight mmBERT-32k classifiers running in-process via candle FFI
(see vLLM SR `candle-binding/semantic-router.go`: `classify_text_with_probabilities`, no LLM call
at all). The logprob/margin signal in the vLLM SR DSL is an *intrinsic output quality signal*
from a prior model output in the session, not a signal extracted by calling the cheap model as a
probe.

**What Verso's ConfidenceCascade requires:** in Verso's design, `ConfidenceCascade` must actually
call the small model (`self.small`), receive its response, extract `logprobs` and `margin` from
that response, compute `0.65·exp(mean_logprob) + 0.35·margin`, and then decide whether to call
the large model again. This is a **post-call escalator**, not a pre-call router. It doubles the
latency and cost of every escalated step.

Three correctness failures follow from this:

**A. Anthropic (likely Verso's primary model) does not expose logprobs.** The `confidence()`
method requires `logprobs: list[float]` — token-level log probabilities. Anthropic's API does
not return per-token logprobs. With `logprobs=[]`, `mean_lp = -math.inf`, `exp(-inf) = 0`, and
`confidence = 0 + 0.35·margin`. The confidence metric degenerates to `0.35·margin` — half the
intended signal is always zero. When the small model is Anthropic (the most likely choice for
Verso given the PRD's example `anthropic:claude-sonnet-4-6`), the escalation logic fires on margin
alone and the threshold of 0.72 is unreachable (`0.35 × 1.0 = 0.35 < 0.72`), meaning the cascade
**always escalates** when Anthropic is the small model, defeating the cost-saving purpose entirely.

**B. The margin signal is undefined for tool calls.** In a ReAct loop, the majority of model
responses are tool calls (JSON), not answer choices. The `margin` parameter is defined as
"difference between top-2 answer choices" — a concept from multiple-choice QA evaluation.
For a tool call response, `margin` is undefined. The resolution offers no definition or fallback
for what `margin` means when `finish_reason == "tool_calls"`, which is the dominant case in
Verso's agent loop (Vercel calibration data: 22.2% of requests end in tool calls, consuming 58.9%
of tokens — so tool-call steps are the expensive ones, exactly where the cascade would fire).

**C. The latency cost inverts the benefit.** vLLM SR's algorithm *saves* a call to the large
model when the cheap model's signal says "easy query." Verso's `ConfidenceCascade` always pays
for the small model call, then sometimes pays for the large model call on top. For streaming
responses (which Verso uses), the small model's response must be fully received before the
`confidence()` check can fire — adding the small model's full RTT (1–5s for a tool call) before
the decision to escalate. The resolution's own PRD targets steps of 1–2s; adding a serial small
model call for confidence-checking contradicts this on every escalated step.

**Verdict on Failure 1:** `ConfidenceCascade` cannot be a correct in-box component as specified
because: (a) its primary source mechanism (vLLM SR) is categorically different (pre-call
classifier vs. post-call escalator), (b) it fails entirely when Anthropic is the small model
(no logprobs), and (c) it has no defined behavior for tool call responses. Shipping it as an
in-box router with vLLM SR constants would produce silent misbehavior (always-escalate with
Anthropic; undefined confidence on tool calls). It needs to be demoted to DEFER/opt-in with
explicit constraints: "only usable with providers that expose logprobs; only for text-generation
steps, not tool-call steps."

---

### Failure 2: Python PeakEWMA on_complete() misreads Tower source (D2)

The resolution claims the Python `PeakEwmaEndpoint` is "DESIGNED, from the KNOWN math above"
and presents it as a faithful reimplementation of Tower's `peak_ewma.rs`. A direct line-by-line
comparison reveals a concrete divergence.

**Tower source (tower-0.5.3, line 279, unconditional):**
```rust
// in RttEstimate::update(), AFTER the if/else for peak vs EWMA:
self.update_at = now;   // ← ALWAYS executed, both PEAK and EWMA paths
```

**Resolution Python D2 `on_complete()` (the PEAK branch):**
```python
if self._rtt < observed_rtt:
    self._rtt = observed_rtt          # PEAK: jump UP
    # ← self._at is NOT updated here
else:
    now = time.monotonic()
    d = math.exp(-(now - self._at) / self._decay)
    self._rtt = self._rtt * d + observed_rtt * (1 - d)
    self._at = now                    # ← only updated in ELSE
self._outstanding = max(0, self._outstanding - 1)
```

`self._at` (the update timestamp) is only updated in the EWMA branch. After a PEAK event
(provider gets slow), `self._at` remains at the time of the last EWMA update, not the time of
the spike.

**Consequence:** on the next `load()` call (or next `on_complete()` EWMA event), `elapsed = now
- self._at` is larger than it should be (it includes time since the last EWMA update AND the
spike time). This produces a larger `d = exp(-elapsed/τ)` decay factor, which means the
provider's RTT estimate drops faster than Tower would allow. In other words: **after a spike, the
Python PeakEWMA recovers provider trust faster than the Rust original** — the "earn back traffic
slowly" property is partially undermined.

At Verso's dogfood scale (2–3 providers, 4–6 concurrent sub-agents), the practical consequence
is limited: the thundering-herd protection the algorithm provides still works directionally, just
with faster recovery. But the resolution claims KNOWN fidelity to Tower source at a specific
file:line (`peak_ewma.rs:236-281`) — and at the most load-bearing part of D2 (the asymmetric
update that is "the entire insight"), the Python code is not faithful to that source.

**Corrected Python on_complete() (matching Tower):**
```python
def on_complete(self, observed_rtt: float) -> None:
    with self._lock:
        now = time.monotonic()        # compute now BEFORE the branch
        if self._rtt < observed_rtt:
            self._rtt = observed_rtt  # PEAK: jump up
        else:
            d = math.exp(-(now - self._at) / self._decay)
            self._rtt = self._rtt * d + observed_rtt * (1 - d)
        self._at = now                # ← unconditional, matching Tower line 279
        self._outstanding = max(0, self._outstanding - 1)
```

---

### Supporting correctness observations (non-breaking at dogfood scale)

**threading.Lock in async context:** The `PeakEwmaEndpoint` uses `threading.Lock` for
thread safety. In Verso's single-threaded asyncio event loop, `threading.Lock` is safe if all
callers are in the same thread. However, Verso's tool dispatch uses `asyncio.get_event_loop
().run_in_executor()` for sync tools. If `p2c_pick()` is called from a thread pool executor,
`threading.Lock.acquire()` can block the calling thread (not the event loop, but the thread
pool worker). The correct primitive for an async framework is `asyncio.Lock`, which is
awaitable. At dogfood scale this is latent, not acute.

**`CACHE_STICKY_STEPS = 5` has zero source backing.** The constants table marks it DESIGNED.
The `infra-model-routing.md` source for sticky routing (OpenRouter) says "stick to same provider
for cache warmth" but supplies no step count. The number 5 is not grounded in any RE'd system.
The resolution itself acknowledges this in open unknown #1 — the critique concurs that this
constant requires empirical validation before it should be a published default.

**RoutingState not persisted across durable-mode crash-resume.** In durable mode, when the agent
resumes from a checkpoint, `RoutingState` resets (it is "not persisted beyond a run" by design).
This means KV cache warmth on the provider's side is lost after a crash-resume: the resumed
agent may route to a different provider than the one that had the warm cache, wasting all the
cache-creation tokens charged before the crash. This is a behavioral inconsistency between
tactical and durable modes, though not a functional correctness bug.

---

## Does It Break the Decision?

**The core in-house build decision (D1/D3/D4/D8/D9/D10) survives.** The ProviderProfile +
OMIT sentinel, two-axis failover, require_parameters enforcement, force-stream-usage, retry
defaults, and AttemptRecord audit trail are all correctly sourced and mechanically sound for
Verso's ReAct loop. The evidence for these components is genuine and the implementations
are faithful to their sources.

**D2 (PeakEWMA-P2C) survives with a one-line fix.** The algorithm is fundamentally correct
and the constants are verified. The `update_at` bug is a real divergence from Tower source
but is a one-line correction. At dogfood scale the impact is negligible.

**D6 ConfidenceCascade does NOT survive as a shipped in-box component.** The vLLM SR evidence
it cites proves a different mechanism (pre-call classifier, not post-call escalator). The
component cannot work at all with Anthropic as the small model (no logprobs), and has undefined
behavior on tool-call responses (the dominant case in Verso's ReAct loop). Shipping it as in-box
with vLLM SR constants would produce silent misbehavior in Verso's primary configuration.

**The overall decision — build in-house vs. delegate — still holds.** The failures are in
specific optional components (ConfidenceCascade, PeakEWMA update path), not in the foundational
choice to build a thin in-house model layer. LiteLLM/gateway delegation fails the solo builder
thesis for the same reasons the resolution states. The fix is to correct D6 and D2, not to
reverse the in-house decision.

---

## Evidence Checked

All load-bearing file:line claims verified against real source:

| Claim | Location | Verdict |
|---|---|---|
| `decay_τ=30s` | `discover.rs:37-43` | CONFIRMED — exact match |
| `seed_rtt=250ms` | `discover.rs:41-43` | CONFIRMED — exact match |
| Tower PeakEWMA cost = `rtt × (pending+1)` | `peak_ewma.rs:138-144` | CONFIRMED |
| Tower `pending = Arc::strong_count − 1` | `peak_ewma.rs:138` | CONFIRMED |
| Tower `update_at` set unconditionally | `peak_ewma.rs:279` | CONFIRMED — Python D2 misses this |
| Tower `CompleteOnResponse` update trigger | `discover.rs:72` | CONFIRMED |
| RoRF `route()` at `controller.py:81-104` | `/tmp/rorf-re/rorf/controller.py` | CONFIRMED |
| RoRF 4-class labels at `dataloader.py:60-81` | `/tmp/rorf-re/rorf/router/dataloader.py` | CONFIRMED |
| RoRF `random_state=420` at `rorf.py:89-95` | `/tmp/rorf-re/rorf/router/rorf.py:94` | CONFIRMED |
| vLLM SR `logprob_weight=0.65, margin_weight=0.35, threshold=0.72` | `config/config.yaml:648-652` | CONFIRMED |
| vLLM SR `needs_reasoning` threshold=0.75 | `config/config.yaml:343` | CONFIRMED |
| vLLM SR ConfidenceCascade = ExtProc pre-call, not post-call escalator | `semantic-router.go` | CONFIRMED — CONTRADICTS D6 use |
| Helicone pinned `tower = "0.5.2"` (lock resolves to 0.5.2) | `Cargo.lock` | CONFIRMED — teardown verified against 0.5.3, minor mismatch, no algorithm difference |
| Anthropic does not expose logprobs | API docs | CONFIRMED — no `logprobs` field in Anthropic Messages API |

---

## Recommendation

**Fix D2 (one line):** In `PeakEwmaEndpoint.on_complete()`, move `self._at = now` OUTSIDE the
if/else to be unconditional, matching Tower `peak_ewma.rs:279`. The algorithm is otherwise
correct.

**Revise D6:** Demote `ConfidenceCascade` from "two implementations ship in-box" to DEFER/opt-in
with explicit preconditions: (1) provider must expose per-token logprobs, (2) step type must be
text-generation (not tool-call dispatch). Remove the vLLM SR constants from the justification —
they come from a pre-call routing mechanism, not a post-call escalator. Consider replacing with
`RoRFRouter` as the sole opt-in learned router for v1 — it runs pre-call, is keyless, works with
any provider, and doesn't require logprobs.

**Do not reverse the in-house decision.** The foundational architecture (ProviderProfile, D1,
D3–D5, D7–D10) is correctly sourced and fit for Verso's exact case. The two specific failures
are fixable without changing the top-level design.
