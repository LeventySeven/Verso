# Adversarial Review — Deferred Tool Loading (Scale & Failure Lens)

**Decision under review:** Build a deferred tool-loading layer: above 20 tools/source, 5 fixed
meta-tools (Strata 4-stage) + a keyless field-weighted BM25+ ranker; only the namespace manifest
eagerly injected.

**Lens:** SCALE & FAILURE — enumerate concrete failure modes the resolution does not handle.

**Reviewer:** red-team critic panel, solo-builder / dogfood-first context.

---

## The attack

The deferred-loading design is structurally correct and well-sourced, but it has **one
production-breaking failure mode that the resolution does not handle** and **two secondary
failure modes that will bite at 10× load.** The primary attack:

### Primary attack — the 4-stage protocol adds 2–3 mandatory extra LLM round-trips on EVERY
### tool-use path; at concurrent agent runs this collapses into latency stacking, not amortization

The resolution presents the Strata 4-stage sequence (`discover → get_tool_details → execute_tool`)
as the default for any source with >20 tools, and names the cost as "context reduction."  What it
does not price is the **latency and call-count cost** paid on every invocation path:

**The mandatory overhead per tool use:**
1. LLM turn 1 → `discover_tools` call (BM25 search, returns name list)
2. LLM turn 2 → `get_tool_details` call (fetches one schema)
3. LLM turn 3 → `execute_tool` call (actual execution)

Before the tool result is in context the loop has consumed **3 LLM round-trips** instead of 1.
The resolution cites only the happy case: "context reduction."  At even 10 concurrent agent runs,
those 3× the LLM calls hit the provider rate-limit ceiling 3× faster for the same unit of real
work.  At 100 concurrent runs (which a dogfood Verso reaching any audience will see), the
deferred-loading path produces **3× token spend and 3× rate-limit exposure for the
same number of tasks completed.**  This is not a hypothetical extrapolation — it is the exact
arithmetic of the protocol as specified.

**The BM25 discover stage does not reliably collapse to a no-op for known tools.**

When the agent already knows the tool it needs (e.g. a second call to `github:create_issue`
in the same run), the protocol still forces `discover_tools` first.  There is no
"I already know this tool's schema" short-circuit in the 5-meta-tool set as specified.  The
resolution mentions the 300s `_DEFAULT_CACHE_TTL` in the MCPAdapter but that caches the raw
tool LIST from the upstream — it does NOT skip the `discover → inspect → execute` round-trips
at the meta-tool level; those are LLM reasoning steps, not cached HTTP responses.

**The opaque `params` string in `execute_tool` is a double-fire footgun for non-idempotent tools.**

`execute_tool` takes `params: Annotated[str, "JSON string with all parameters. Use '{}' if none."]`.
When the model generates malformed JSON in `params`, the flow is:
- Stage 3 `json.loads` raises → `TextContent("Error: Invalid JSON in params")` returned
- Model self-corrects, re-issues `execute_tool`
- If the upstream partially executed before the error (e.g. a slow external API that accepted the
  request but timed out returning the result), the re-issued call fires the action **a second time**

The resolution marks `execute_tool` as `destructive=True, idempotent=False`.  Correct annotation,
but the deferred protocol's own opaque-params design makes double-fire the *default self-correction
path* for any parse error.  The `ToolMeta.idempotent=False` flag tells the executor not to
auto-retry — but `execute_tool`'s self-correction loop is driven by the **LLM**, not the executor.
The executor's `max_attempts=1` guard does not protect against LLM-initiated re-calls to
`execute_tool` after a JSON parse error.  The executor guards retries on TOOL_RUNTIME_RETRY;
a fresh LLM call to `execute_tool` is a new dispatch, not a retry.  The non-idempotency
protection has a gap exactly at the seam the deferred protocol creates.

---

### Secondary attack A — BM25 discover is a cold-start cliff for schemas with minimal text

The field-weighted BM25 index is built at adapter initialization.  If the upstream MCP server
returns tool schemas with sparse or missing `description` fields (not uncommon — Smithery registry
shows many servers with minimal tool docs), the BM25 index degrades to name-only matching.
At weight 30 for `name` and `description`, a catalog where every tool has a one-word description
collapses to substring matching.  For a 100-tool catalog with terse descriptions, `discover_tools`
will return top-50 names that may be mostly irrelevant noise, forcing the LLM to attempt
`get_tool_details` on tools that aren't the right ones, adding another round-trip.

The resolution acknowledges this only implicitly ("embeddings opt-in").  The cold-start
failure — where BM25 is **worse than embedding search precisely when the tool catalog is most
opaque** — is not surfaced as a risk.  At 10× (larger catalogs, more terse schemas), BM25 will
systematically misrank, and the 3-round-trip overhead becomes 5+ as the LLM compensates.

---

### Secondary attack B — the threshold constant `DEFERRED_LOADING_THRESHOLD = 20` is DESIGNED
### (not calibrated) and the resolution acknowledges it has no empirical backing for Verso

The resolution's own Open Unknowns section (#1) says: "The right number depends on average schema
size per tool and the target model's context window. Strata's claimed 60–80% context reduction
needs empirical measurement on Verso's own registry before committing to this threshold."

Below 20 tools, full eager injection applies.  Above 20, the full 3-LLM-turn overhead kicks in.
This means:

- A source with exactly 19 tools pays zero overhead.
- A source with exactly 21 tools pays 3× LLM turns per use.

The **step function** at the threshold creates a cliff rather than a gradient.  For Verso's
dogfood phase (likely 20–50 tools across a few MCP sources), a developer adding their 21st
tool suddenly experiences 3× the latency on every tool use.  That discontinuity will surface as
a confusing DX bug, not a legible tradeoff.  The resolution does not propose a gradual
threshold (e.g., lazy schemas only above 50 tools, partial injection between 20 and 50) nor
does it commit to measuring before locking the threshold.

---

## Does it break?

**Partially.** The design does not fail to work — the 3-stage protocol produces correct results.
But it breaks the **performance and cost assumptions** the resolution implicitly relies on:

- The "context reduction" win (60–80%, from Strata marketing) is real on the **token/context axis**.
- It is not free on the **latency and LLM-call-count axis**, and the resolution does not price that.
- At 10× concurrent agents, the 3× call multiplier becomes the dominant cost.
- The non-idempotent double-fire risk is a correctness gap, not just a performance gap.

The resolution survives as a Phase 3 feature (PRD §8 places MCP adapter + deferred loading in
Phase 3 — "opt-in scale, after dogfooding").  At dogfood-phase load (single developer, small
registry), none of these failure modes materialize.  **If shipped into Phase 0/1 as a default
behavior (which the resolution's `DEFERRED_LOADING_THRESHOLD = 20` wording implies is
always-on), the latency stacking and double-fire footgun are real production risks.**

---

## Evidence checked

- Resolution `tools-mcp.md` Decision 7: confirmed the 5 meta-tools and 4-stage protocol are the
  **default** for any source >20 tools.  No latency cost is mentioned.  Open Unknown #1 confirms
  the threshold is DESIGNED with no empirical calibration.
- Resolution `tools-mcp.md` `execute_tool` definition (line ~356-364): confirmed `params` is an
  opaque JSON string, `destructive=True, idempotent=False`.  The executor's
  `max_attempts=1` guard for non-idempotent tools is at `ToolDispatcher._call_one` — but this
  guards the **executor retry path**, not a fresh LLM-initiated `execute_tool` call.  The gap
  is confirmed.
- Teardown `infra-tools-mcp.md` Strata section, `tools.py:246-292`: confirmed stage 3
  `execute_action` does `json.loads` each param string and returns `TextContent("Error: Invalid
  JSON in {param_name}")` on failure — exactly the recovery path that leads to re-issue.
- Teardown `infra-tools-mcp.md` cross-system synthesis table: five systems, none of them
  benchmark latency overhead of the meta-tool protocol.  The "15% accuracy improvement" and
  "60–80% context reduction" are Klavis marketing figures (INFERRED label) — no call-count or
  latency numbers are cited anywhere in the evidence base.
- PRD v1 §8: Phase 3 placement of MCP adapters + deferred loading confirmed.  The resolution
  did not clarify whether the `DEFERRED_LOADING_THRESHOLD = 20` constant is a Phase 3 artifact
  or a Phase 0 default.
- Teardown `infra-tools-mcp.md` mcp-use section: confirmed `max_steps=5` default (low call
  budget), noting call-count overhead is a design concern shared by practitioners.

---

## Recommendation

**REVISE — three targeted fixes before PRD lock:**

1. **Add a schema-based fast-path for already-known tools.**  When the agent is on its second or
   later call to a tool it already resolved in this session, skip `discover` and `get_tool_details`
   and go directly to `execute_tool` using the cached schema from the `DeferredLoader`'s own
   session state.  This collapses the 3-turn overhead to 1 turn for repeat calls — the common
   case in any realistic agent run.  The `DeferredLoader` already caches `_tools_cache` per
   adapter; add a session-level "already-inspected" map keyed by `(namespace, action)`.

2. **Harden `execute_tool` against LLM-driven double-fire for non-idempotent actions.**
   Before dispatching, emit a pre-execution checkpoint that includes the call signature.
   On re-receipt of the same `(namespace, action, params_hash)` within the same run without an
   intervening successful result, return the cached result rather than re-executing.  This mirrors
   the `repeated-(tool,args) short-circuit` already specified in PRD §5.3 for the general dispatch
   path — extend it explicitly to the `execute_tool` meta-tool dispatch path.

3. **Replace the hard step-function threshold with a graduated injection policy.**  Below 20
   tools: full eager injection (current).  20–50 tools: inject schemas for `read_only` tools
   eagerly (low schema weight, useful for planning), defer only `destructive` tool schemas.
   Above 50 tools: full deferred protocol.  The 50-tool number is still DESIGNED but the
   graduated policy eliminates the DX cliff and gives the dogfooding author a chance to observe
   where the step actually matters before the threshold is locked.
