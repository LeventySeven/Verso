# Adversarial Review: Model Layer — Scale & Failure Lens

**Decision under review:** Build the model layer in-house — ProviderProfile + 5 hooks + OMIT sentinel,
P2C+PeakEWMA load-balancer (decay_τ=30s), two-axis error-typed cross-model failover — vs delegating
to LiteLLM / a gateway.

**Lens:** SCALE & FAILURE — enumerate concrete failure modes the resolution does NOT handle.

---

## The Attack

The resolution is well-sourced and architecturally sound *for a single-process, low-concurrency,
dogfood-first agent running in one event loop*. Under that regime it probably survives.
The problem is that several of its core mechanisms contain a shared failure mode that the resolution
does not name, does not handle, and does not even acknowledge as an open unknown: **the
PeakEWMA state is process-local and thread-unsafe under async concurrency, which is exactly the
concurrency model Verso runs in.**

The attack has five specific failure modes. They are ordered from "most likely to bite on the first
real dogfood run" to "requires scale-up to surface."

---

### Failure 1 — The locking model is wrong for asyncio (breaks at 2+ concurrent agent steps)

The resolution implements `PeakEwmaEndpoint` with `threading.Lock`. That is a **blocking OS-level
mutex**. In Python asyncio all coroutines share one OS thread. A `threading.Lock` in asyncio code
means: every `load()` call and every `on_complete()` call blocks the event loop while it holds the
lock. Under light load this is invisible. Under any concurrency — two agent steps firing tool calls
simultaneously, a streaming response arriving while a new call dispatches — the event loop stalls
for the duration of every PeakEWMA state read/write, serializing all I/O operations that happen to
be scheduled at that moment.

The Helicone implementation (the source the resolution RE'd) avoids this because it is a **Rust
async Tower service**: the PeakEWMA state is behind a `Mutex<T>` that `async_std`/`tokio` makes
non-blocking with `lock().await`. In Python, the direct translation is `asyncio.Lock`, not
`threading.Lock`. The resolution's code uses the wrong primitive and the resolution text does not
discuss this at all.

Concrete failure scenario: at 5 concurrent tool calls per step — normal for an agent that fans out
web searches — every call serializes through the PeakEWMA lock on both `load()` (which decays RTT
in-place with a side-effectful write) and `on_complete()`. The result is a self-induced serialization
bottleneck in the one place that is supposed to improve throughput. The P2C benefit (spread load
across healthy providers) is negated because the selection step itself is serialized.

The fix is one line: `threading.Lock()` → `asyncio.Lock()` + `async with`. But the resolution does
not identify the issue, does not mark it as KNOWN/INFERRED/DESIGNED, and ships the wrong primitive.

---

### Failure 2 — BudgetGuard.admit() is a TOCTOU race under concurrency (breaks at 2+ concurrent runs)

`BudgetGuard.admit()` reads the current spend, checks `spent + charge <= limit`, and returns `True`.
`BudgetGuard.charge()` is called later, after the response completes. These are two separate
`await` calls with no transaction boundary between them. Under concurrency — two agent runs
starting simultaneously with nearly identical budget headroom — both can pass `admit()` before
either calls `charge()`, and both can overspend the budget by up to `2×` in the worst case.

The resolution's `InMemoryBudgetStore` uses an in-memory dict and (implicitly) Python's GIL for
"thread safety," but that only protects individual dict mutations, not the read-check-increment
sequence. The resolution defers `RedisBudgetStore` to Phase 2, but the race exists in-memory right
now, before Phase 2.

The canonical fix is an atomic INCR-and-check (Redis `INCRBYFLOAT` + `GET` in a Lua script or
pipeline) or a per-key `asyncio.Lock`. The resolution offers neither. It does note (Open Unknown 4)
that in-memory is "dev-correct and zero-infra," but this frames the risk as a deployment concern
rather than a correctness bug that exists *today* on a single process running two agents.

Concrete failure scenario: the user runs two agents simultaneously — a research agent and a code
agent — with a shared `$5.00` budget. Both `admit()` at nearly the same cost; both see $4.80 spent;
both proceed; total spend reaches $4.80 + call_A + call_B, overshooting $5.00 by up to the cost of
one full call. The `fail_open=True` default means budget errors swallow silently. The user sees a
$6+ bill when they set a $5 cap.

---

### Failure 3 — PeakEWMA does not handle streaming correctly; the `CompleteOnResponse` assumption breaks for SSE agents (wrong latency signal)

The resolution copies Helicone's `CompleteOnResponse` trigger verbatim: `on_complete(observed_rtt)`
is called when the "response completes." For non-streaming calls this is unambiguous. For streaming
calls — which is *most agent calls* (Verso's `agent.stream()` is a first-class path, Phase 0) —
"complete" means "SSE stream closed." A provider that starts streaming in 200ms but takes 30s to
finish all tokens will have its `on_complete` called with `observed_rtt ≈ 30s`. The next P2C
selection will see this endpoint's EWMA at ~30s, immediately demoting it, even though TTFB was fine
and the slowness was token generation, not network/provider degradation.

This creates the opposite of the intended behavior: **providers serving long reasoning traces (the
exact case `effort="high"` and `on_malformed_tool` chains are designed for) will be systematically
penalized by the latency router** because their wall-clock completion time is long. The fast-reaction
"peak" behavior will fire on every high-effort call and take 30s × decay_τ=30s to recover. On a
run with 10 high-effort steps, the P2C router will progressively route away from the provider that
is actually doing the most work correctly.

The resolution does not mention TTFB vs wall-clock streaming. The Envoy teardown explicitly
flags this (the `cf-aig-request-timeout` header "timed from first response byte, not full
completion"), and the Helicone `CompleteOnResponse` is fine for Helicone because it is a
pass-through proxy, not the endpoint consuming the stream. For Verso, which *is* the stream
consumer, the correct signal is TTFB (time to first token), not total completion time.

Concrete failure scenario: a two-provider setup (Anthropic + OpenAI). Anthropic `claude-sonnet-4-6`
starts streaming in 150ms but takes 25s for a long reasoning trace. OpenAI `gpt-5.1` starts in
400ms and finishes in 8s. After one high-effort step, Anthropic's PeakEWMA rtt = 25s (peaked);
P2C routes away to OpenAI for the next N steps. The user's cache-sticky-steps=5 preference is
overridden because the sticky provider's PeakEWMA cost is catastrophically high. Provider failover
that the user did not want, driven by a broken latency signal.

---

### Failure 4 — 1M-token context + `effort="high"` creates a cost-estimation black hole that breaks the BudgetGuard pre-check

`BudgetGuard.admit()` uses `est_cost = max_tokens * output_rate` as the pre-dispatch estimate. For
streaming calls the actual cost is unknown until `end-of-stream`. The resolution's own cost formula
(`cache_aware_cost`) requires `input_tokens`, `cached_tokens`, `cache_creation_tokens`, and
`output_tokens` — none of which are known before the call.

The resolution papers over this with `est_cost = max_tokens * output_rate` as a "heuristic," but
this estimate is systematically wrong in two directions that both bite at scale:

1. **Underestimate on reasoning models**: `effort="high"` causes `reasoning_tokens` to be billed at
   output_rate but the caller cannot know how many reasoning tokens will be used before the call.
   A `max_tokens=32768` `effort="high"` call can cost 2–3× a naive `max_tokens * output_rate`
   estimate because reasoning tokens add to the actual billed output. The BudgetGuard pre-check
   passes; the post-charge overshoots the budget.

2. **Overestimate on cached inputs**: the resolution's `cache_aware_cost` applies `0.1×` to
   cached tokens, but the `admit()` heuristic uses full `output_rate` for the entire input. For a
   1M-token context that is 90% cache-hit, the admit estimate is ~10× the true cost, so the
   BudgetGuard is far too conservative — it blocks calls that would be cheap.

These are not edge cases. They are the *exact regime* Verso is designed to operate in: long
multi-step agent runs (many cached tokens) with optional high-effort synthesis steps (reasoning
tokens). The BudgetGuard as designed is correct only for short, non-reasoning, non-cached calls —
the minority of Verso's actual workload.

The open unknown section acknowledges BudgetStore but not cost estimation accuracy. This is
a structural gap, not a deferred decision.

---

### Failure 5 — Non-idempotent tool double-fire under the retry layer (agent-level semantic corruption)

The retry layer (`call_with_retry`, attempts=6, initial=4s) fires on `RATE_LIMIT`, `SERVER_ERROR`,
and `TIMEOUT`. The failover layer fires on those same error classes across providers. Neither layer
checks whether the model response was partially consumed (i.e., whether the LLM had already begun
streaming a tool call before the connection dropped).

For a streaming agent call that dies mid-stream — say, the provider returns 10 tool-call tokens
then the connection resets (HTTP 500 or TCP teardown) — the framework raises a `TIMEOUT` or
`SERVER_ERROR`. The retry fires. The model is re-called with the *original request* (no partial
context), produces a fresh tool call, and the tool fires. If the original partial stream was far
enough along to have partially executed a tool (or worse, if the agent loop was tracking
intermediate state), the re-call produces a semantically duplicate action.

The resolution's `AttemptRecord` trail is excellent for observability but it does not contain the
partial response bytes. The `call_with_failover` code returns either a `ProviderResponse` or raises
— there is no "partial response + retry decision" branch. The question "was this a response
mid-stream or a connection-level error before any tokens were returned?" is not asked and not
recorded.

This is the non-idempotent tool double-fire problem. It does not exist in Helicone (a proxy, it
just retries the HTTP request; the LLM is stateless per-call). It does not exist in LiteLLM (same
reason). It specifically exists in Verso because Verso *is the agent loop* — it has semantic state
about what the model was in the middle of doing, and retrying a provider call is not equivalent
to retrying an HTTP request when that call was producing a tool invocation.

The resolution marks `MALFORMED_TOOL` as a `break` (advance to next model) but does not handle
the mid-stream partial tool call case at all. For destructive tools (write to DB, send email,
execute code), a double-fire is a correctness failure, not a performance concern.

---

## Does It Break?

**The design survives dogfood-solo** (one agent, one event loop, no concurrency, non-streaming or
short responses, no reasoning models, $-budget not enforced). This is exactly the Phase 0 use case
the resolution is designed for, and for that regime it is fine.

**The design breaks — or produces meaningfully wrong behavior — the moment any of these conditions
appear:**

| Condition | Failure mode triggered |
|---|---|
| 2+ concurrent agent steps or tool calls | Failure 1 (wrong lock) + Failure 2 (TOCTOU budget) |
| Streaming calls with reasoning / long output | Failure 3 (TTFB vs wall-clock EWMA signal inversion) |
| 1M-token context or `effort="high"` budget enforcement | Failure 4 (cost estimate wrong by 2–10×) |
| Retry on mid-stream partial tool call | Failure 5 (non-idempotent tool double-fire) |

All four conditions are **in-scope for Phase 0** (streaming is Phase 0; concurrent tools are Phase 0;
`effort="high"` is Phase 0; retries with tools are Phase 0). None of them are Phase 2/3 concerns.

The resolution's language ("battle-tested defaults," constants from production Helicone source) is
accurate about the *origin* of the constants, but the constants were battle-tested in a Rust async
gateway that is a pass-through proxy, not a Python agent framework that is the stream consumer and
semantic state holder. The translation gap is where the failures live.

---

## Evidence Checked

1. **`model-routing.md` D2** — `PeakEwmaEndpoint` uses `threading.Lock`, confirmed at the
   code block in D2. No `asyncio.Lock`. No discussion of event-loop compatibility.

2. **`model-routing.md` D5** — `BudgetGuard.admit()` reads then returns; `charge()` is separate.
   TOCTOU is not named. Open Unknown 4 frames this as a deployment concern, not a race condition.

3. **`infra-model-gateways.md` Helicone section** — `CompleteOnResponse` confirmed
   (`discover.rs:37-43`, `peak_ewma.rs:236-281`). The teardown is for a *proxy*; Verso is the stream
   consumer. The resolution does not address this distinction.

4. **`infra-model-gateways.md` Cloudflare section** — `cf-aig-request-timeout` "timed from
   first response byte." This explicit TTFB-vs-completion distinction is documented in the source
   teardown but not carried over to the resolution's EWMA update trigger.

5. **`model-routing.md` D5** — `cache_aware_cost()` uses post-call token counts. `admit()` uses
   `max_tokens * output_rate` as a pre-call heuristic. Reasoning tokens are not included in the
   pre-call estimate. Confirmed gap — not an open unknown in the resolution.

6. **`model-routing.md` D9** — `call_with_retry` retries on `TIMEOUT`/`SERVER_ERROR` with the
   original request. No partial-stream detection. `call_with_failover` has no mid-stream error
   branch. The `AttemptRecord` records `error_class` but not partial bytes.

7. **Source verification** — did NOT re-clone Helicone or Tower to re-verify `peak_ewma.rs` or
   `threading::Mutex` vs `asyncio.Lock`. The teardown cites verbatim source at `peak_ewma.rs:236-281`
   and `discover.rs:37-43`; the translation error from Rust `Mutex` to Python `threading.Lock` is
   evident from the resolution's own code block without needing re-clone.

---

## Recommendation

**Verdict: REVISE** — the design is correct for the solo-dogfood happy path but contains four
concrete failure modes that will surface in Phase 0 (streaming, concurrent tools, cost enforcement).
The fixes are all small and mechanical; none require redesign:

1. **`threading.Lock` → `asyncio.Lock` + `async with`** in `PeakEwmaEndpoint`. All methods that
   touch `_rtt`, `_outstanding`, `_at` must become `async def` with `async with self._lock`.
   This is a one-file change in `balancer.py`.

2. **Atomic budget increment**: replace the read-check pattern in `InMemoryBudgetStore` with an
   `asyncio.Lock` per key, or use a `defaultdict + asyncio.Lock`. Redis path already has atomic
   `INCRBYFLOAT`; in-memory needs the same guarantee. Add this fix and remove the "dev-correct"
   framing — it is not correct under any concurrency.

3. **TTFB-aware EWMA**: for streaming calls, record `on_start_time` and emit
   `on_first_token(ttfb_s)` as the PeakEWMA RTT signal, not wall-clock completion time. Wall-clock
   completion can optionally feed a separate `completion_time` metric for observability but must not
   be the load signal. Add `ttfb_s: float | None` to `AttemptRecord`.

4. **Cost estimation accuracy**: add `est_reasoning_tokens: int = 0` to `ProviderRequest`; use it in
   the pre-call estimate. For cached contexts, track `last_cached_tokens` in `RoutingState` and use
   it in `admit()`. Mark Open Unknown 5 (not 4) as the active gap; add a calibration TODO.

5. **Non-idempotent retry guard**: before retrying a streaming call on `TIMEOUT`/`SERVER_ERROR`,
   check whether any tokens were received (`partial_bytes > 0`). If yes, do not retry with
   `attempts > 1`; either fail fast to the next provider (advance the failover chain) or add a
   deduplicated "was partial tool call emitted?" check in the agent loop. At minimum, document this
   as a KNOWN limitation with destructive tools.

The underlying architectural choice — build in-house rather than delegate to LiteLLM — remains
defensible. LiteLLM would solve failures 1–4 (it handles async correctly, has atomic Redis spend
tracking, measures TTFB separately, and does not pre-estimate costs). But LiteLLM also ships 592K
LOC of monolith that conflicts with the keep-it-simple thesis. The in-house path is correct; it
just needs the five fixes above before streaming + concurrent tools are turned on.
