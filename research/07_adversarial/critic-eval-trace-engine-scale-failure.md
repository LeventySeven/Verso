# Adversarial Review: eval-trace-engine — SCALE & FAILURE lens

**Decision under review:** Verso OWNS an eval/trace layer: VersoSpan 10-kind taxonomy + VersoScore 5-element schema + dotted_order tree key, dual-emit gen_ai.* OTel primary + OpenInference enrichment, one EvalJob engine for online+offline — vs just emitting OTel to Langfuse/Phoenix.

**Lens:** SCALE & FAILURE — enumerate concrete failure modes the resolution does NOT handle. Does the default survive production at 10×, or only the happy path?

**Critic:** adversarial panel, SCALE & FAILURE assignment.

**Date:** 2026-06-05

---

## The Attack

The resolution is architecturally sound for the happy path. The data models are well-sourced; the convergence evidence is genuine. But the design has one load-bearing scale/failure crack that the resolution does not acknowledge: **the asyncio.Queue dev backend and the "pluggable backend swap" story both hide the same unresolved problem — the `PENDING → COMPLETED` dedup and the `streamMaxLen` cap are incompatible with at-least-once delivery when the process restarts mid-queue, and the transition from in-process queue to Redis Streams is not a "swap," it is a correctness boundary the code must be explicitly designed to cross.**

This is the single failure that bites hardest at 10×, but there are four distinct failure modes below it.

---

### Failure Mode 1 — asyncio.Queue + process crash = score loss (the primary crack)

The resolution ships this for dev/v1:

```python
class EvalQueue(Protocol):
    async def submit(self, trace_id: str, rule_id: str) -> None: ...
    async def consume(self) -> AsyncIterator[tuple[str, str]]: ...

# Worker loop
async def eval_worker(queue: EvalQueue, store: TraceStore, rules: dict[str, EvalRule]):
    async for trace_id, rule_id in queue.consume():
        rule = rules[rule_id]
        if random.random() > rule.sampling:
            continue
        await asyncio.sleep(rule.delay_ms / 1000)
        trace = await store.get_trace(trace_id)
        score = await run_judge(rule.scorer, trace)
        await store.write_score(score)
```

The `asyncio.Queue` implementation has no persistence boundary. Items are in-process Python objects. On any process crash — `SIGKILL`, OOM, an unhandled exception that tears down the event loop, a `Ctrl-C` during the `delay_ms` sleep — **all queued `(trace_id, rule_id)` pairs are lost silently**. No dead-letter. No claim-on-timeout. No `maxRetries`. The dedup logic the resolution describes (`skip if JobExecution(config_id, trace_id) already COMPLETED`) protects against double-scoring a completed job, but it has no counterpart for the "job was submitted, enqueued, and then vaporized" case.

The resolution explicitly acknowledges the Redis Streams swap is needed for fault tolerance:
> "For Verso v1 (dogfood, no Redis): use an async asyncio.Queue with a background worker coroutine; the interface is identical, Redis is a pluggable backend swap."

The word "identical" is the problem. The Opik Redis Streams design the resolution copies (`OnlineScoringEngine.java`) has three mechanisms that are absent from `asyncio.Queue` by construction:
1. **`pendingMessageDuration` / `XAUTOCLAIM`** — a message not ACK'd within N minutes is reclaimed by another worker. `asyncio.Queue` has no pending-message concept; a dequeued item that hasn't been ACK'd is gone from the queue.
2. **`maxRetries` + dead-letter** — repeated failures are finite and auditable. `asyncio.Queue` get/put has no retry envelope.
3. **`streamMaxLen` as a durability cap** — Redis Streams are persisted to AOF/RDB. `asyncio.Queue` is heap RAM.

The `Protocol` interface IS identical at call sites. The delivery semantics are NOT. The resolution conflates "same call signature" with "same failure contract." A user who deploys Verso with the `asyncio.Queue` backend under any production-grade load (long-running agents, overnight runs, container restarts under OOM) gets **silent score loss** — traces are written but never scored, with no error surfaced anywhere. The dedup check prevents re-scoring, not un-scoring.

**Threshold where this bites:** The first time the host process restarts while there are items in the queue. For dogfood use (single process, short sessions), this is low frequency. For the first "real" use case — an overnight eval run on a dataset of 500 items — a single OOM mid-run silently drops all unprocessed items with no recovery path. The `asyncio.Queue` backend is not "dev-only safe" the way SQLite-for-traces is dev-only safe; SQLite's writes are fsync'd and survive process restarts. The queue's writes are not.

---

### Failure Mode 2 — dotted_order string explosion on deeply nested multi-agent traces

The resolution adopts:

```python
def make_dotted_order(start_time: datetime, span_id: str, parent: str | None) -> str:
    seg = start_time.strftime(DOTTED_ORDER_TS_FMT) + span_id  # e.g. "20260605T123456789012ZUUID7"
    return f"{parent}.{seg}" if parent else seg
```

Each nesting level appends ~28 characters (`YYYYMMDDTHHMMSS.ffffff` = 21 chars + 36-char UUID7 = 57 chars + 1 dot). LangSmith uses this for human-authored chains that are typically 2–4 levels deep. Verso's multi-agent architecture supports `fan_out` with a default depth cap of 1 but explicitly allows orchestrator-workers patterns. In a `fan_out(tasks, max_concurrency=4)` where each worker spawns tools that each invoke an LLM, you get:

```
AGENT (root)
  └─ TOOL: fan_out dispatcher
       ├─ AGENT: worker-A
       │    ├─ TOOL: search
       │    │    └─ GENERATION: embedding
       │    └─ GENERATION: synthesis
       ├─ AGENT: worker-B (same tree)
       ...
```

That is 5 nesting levels → dotted_order length of `5 × 58 = 290 chars` for the deepest leaf span. At 10× agents each producing this shape in a run, a trace with 500 spans has dotted_order strings averaging ~200 chars. This is not a hard failure — ClickHouse handles long strings — but it has two concrete downstream costs:

**Cost A — INDEX SIZE.** The resolution adopts `CREATE INDEX idx_spans_order ON spans(dotted_order)` in SQLite. A B-tree index on a 200-char string column for a 100K-span eval run costs ~20–40 MB of index just for this column, and prefix-scan queries (`WHERE dotted_order LIKE 'prefix%'` for subtree reconstruction) on a long string B-tree are significantly slower than on a short integer key. Langfuse uses this in ClickHouse where per-column compression makes long strings cheaper; in SQLite there is no columnar compression.

**Cost B — THE REAL FAILURE: sort semantics break when clocks aren't monotonic.** The `make_dotted_order` timestamp is `datetime.utcnow()` (or equivalent). In an `asyncio` multi-task context, two spans created in the same event-loop tick can get the same microsecond timestamp. The UUIDv7 disambiguates within a node, but **across workers in a `fan_out`, the wall clocks of the coordinating coroutines can produce out-of-order segments**. LangSmith uses `dotted_order` on a system where all runs are submitted through a single client SDK with a single clock; Verso's multi-agent fan_out creates child spans across multiple `asyncio.Task` objects that may interleave freely. The dotted_order encodes the timestamp at span CREATION, not completion. A worker-A tool call that starts 50ms after worker-B's tool call but finishes 200ms before it will sort AFTER it in the dotted_order string — which is correct for start-time order but breaks the "sibling order = execution order" assumption. For eval metrics that read the step trace (`trajectory:tool-sequence`), this is a subtle correctness issue, not merely cosmetic.

---

### Failure Mode 3 — 50k-token agentic judge threshold is a static constant on a moving target

The resolution ships:

```python
AGENTIC_JUDGE_THRESHOLD_TOKENS = 50_000
CHARS_PER_TOKEN_HEURISTIC = 4

if len(trace_text) / CHARS_PER_TOKEN_HEURISTIC > AGENTIC_JUDGE_THRESHOLD_TOKENS:
    verdict = await run_tool_equipped_judge(judge, trace_store, trace_id)
else:
    verdict = await run_inline_judge(judge, trace_text)
```

This is sourced verbatim from Opik `OnlineScoringEngine.java` and the teardown confirms it. The problem is not the constant — it is the routing logic. The `tool_equipped_judge` path is described in the resolution as a design decision but **its implementation is not specified**. The resolution says "give the judge tools to query it" but does not specify:

- What tools does the agentic judge receive? (trace-query tools? span-filter tools? structured search?)
- Is the judge running against the same SQLite/ClickHouse `TraceStore`, or a separate read path?
- What happens if the `tool_equipped_judge` itself produces a trace that exceeds 50k tokens? (recursive judge invocation)

This is not a documentation gap — it is an unresolved correctness boundary. At 10× concurrent agents, the probability that multiple traces simultaneously hit the 50k threshold and trigger concurrent `tool_equipped_judge` runs is non-trivial. The `tool_equipped_judge` is the expensive path (multiple LLM calls, tool execution, potentially a second agent loop); if it is not rate-limited or concurrency-capped independently of the main agent concurrency, it can saturate the provider's rate limits. The resolution specifies `batch_size` for the consumer group but no concurrency limit for the agentic judge path.

**The specific failure at 10×:** An eval run on 200 traces where 40 exceed 50k tokens fires 40 concurrent `tool_equipped_judge` coroutines. Each makes 3–5 LLM calls. That is 120–200 concurrent LLM calls from the eval engine alone, competing for the same rate-limit bucket as the agents under test. The scoring run cross-contaminates the agent runs it is supposed to be scoring.

---

### Failure Mode 4 — `delay_ms` is a fixed sleep, not a flush-confirmation; it races the trace write on the prod path

The resolution's online eval queue includes:

```python
await asyncio.sleep(rule.delay_ms / 1000)  # DEFAULT_EVAL_DELAY_MS = 2_000
trace = await store.get_trace(trace_id)
```

The 2-second delay is copied from Langfuse `evalService.ts:676` where it exists because Langfuse's architecture has a known latency between trace ingest (the SDK call) and ClickHouse availability (the async ingest pipeline: SDK → Kafka → ClickHouse consumer). The delay is a HEURISTIC for an asynchronous pipeline where the write and the read happen on different machines through a message queue.

Verso's architecture is different: in the SQLite dev backend, the span write and the `store.get_trace` read happen on the same process with `aiosqlite`. The 2-second sleep adds 2 seconds of latency per eval job for no correctness benefit — the write is synchronous and immediately readable. The `asyncio.sleep` holds the consumer group slot for 2 seconds, reducing effective throughput of the eval worker by (1 - delay_fraction) for any job that runs fast (fast judges on short traces).

More importantly: in the prod backend (ClickHouse for spans + Postgres for eval job state), there IS a latency between span write and ClickHouse visibility — but it depends on the ingest buffer (`max_block_size`, typically 65,536 rows or 1 second, whichever comes first). The fixed 2-second delay may be too short for a heavily loaded ClickHouse where the ingest buffer hasn't flushed, or 20× too long for a lightly loaded one. The resolution hardcodes this constant without acknowledging that it is only correct for Langfuse's specific Kafka pipeline and is wrong (in both directions) for Verso's storage topologies.

**The failure at 10×:** Under load, 10 concurrent agent runs each emit spans at ~5 steps/run. The eval queue accumulates (trace_id, rule_id) pairs. Each pair sleeps 2 seconds before the trace fetch. With `batch_size=1` (the unspecified default), the consumer processes one job at a time: submit→sleep(2s)→fetch→score→write. At 10 concurrent agents, each finishing a 5-step run every ~30 seconds, the eval queue receives ~10 jobs/30s = 1 job every 3 seconds. With 2s sleep + judge latency (~3–5s for a fast judge), the consumer cannot keep up with the ingest rate. Eval jobs pile up. The `asyncio.Queue` has no back-pressure mechanism; the queue grows unboundedly until the process OOMs, at which point failure mode 1 activates and all backlogged jobs are silently dropped.

---

### Failure Mode 5 — `UnrecoverableError` on judge schema failure silently drops the score with no observable signal

The resolution ships:

> "On `safeParse` failure → `UnrecoverableError` (no retry — model can't fix a schema mismatch; log and skip)."

Copied from Langfuse's `evalService.ts` where a schema-parse failure throws `UnrecoverableError` and the `JobExecution` row is updated to `status: FAILED` in Postgres — **a durable, queryable, alertable failure record**. The Langfuse design also has `blockEvaluatorConfigs` (`:747+`) which stops a broken eval config from burning money indefinitely.

In Verso's design, the `UnrecoverableError` path ends with "log and skip." Log to where? The `eval_worker` coroutine has no error-state output beyond a log line. The `EvalJob` table has `status: Literal["RUNNING", "COMPLETED", "FAILED"]` but the worker code does not update it on `UnrecoverableError` — the `write_score` call is never reached. The `EvalRun.score_summaries` will simply be missing that metric for affected traces, with no indication of why.

**The failure at 10×:** A model that frequently produces schema-mismatched outputs (e.g., an Anthropic model that sometimes returns a structured output in a different field order, triggering Pydantic's strict mode) silently fails N% of eval jobs. The `score_summaries` appear to show good metric coverage with normal values — but those are the successful N, not the population. There is no alert, no counter, no `FAILED` job count exposed in the eval run result. The CI gate (`result.passes(thresholds={"factuality": 0.8})`) passes because the denominator `n` in `ScoreSummary` only counts completed scores. A 20% silent failure rate on judges passes a threshold check that was calibrated on 100% completion.

---

## Does It Break the Decision?

**No — not fully.** The decision's core thesis (own the schema, emit natively, use a single EvalJob engine) is correct and the data models are sound. The failure modes above are in the **operational layer** (queue durability, judge concurrency, delay heuristic, error observability), not in the schema design.

However, **failure mode 1 breaks the "dev backend is safe for dogfood" assumption** in a specific and non-obvious way: the `asyncio.Queue` backend silently drops eval jobs on any process restart, which is qualitatively different from SQLite-for-traces (which survives restarts). This is the only failure that rises to "breaks the decision as stated" because the resolution explicitly presents the `asyncio.Queue` as a safe v1 default, when it is safe only for interactive sessions that complete without interruption.

The other four failure modes are REVISE-worthy: the judge concurrency cap for the agentic path is missing; the `delay_ms` constant is misappropriated from a different pipeline topology; the `UnrecoverableError` path needs a durable failure record; and the dotted_order clock-skew issue needs a tiebreaker for fan_out spans.

---

## Evidence Checked

- `evals-trace.md` Decision 5 (`online.py` worker loop, asyncio.Queue protocol, delay_ms constant, `UnrecoverableError` handling) — read in full.
- `eval-observability.md` §Opik §OnlineScoringEngine.java (`pendingMessageDuration`, `XAUTOCLAIM`, `maxRetries`, `streamMaxLen`) — confirmed the three fault-tolerance mechanisms are absent from asyncio.Queue by design.
- `eval-observability.md` §Langfuse §evalService.ts (`:612` dedup, `:621` sampling, `:635` JobExecution PENDING, `:676` delay, `:747` `blockEvaluatorConfigs`, `UnrecoverableError`) — confirmed the Langfuse design writes a durable failure record; Verso's design does not.
- `evals-trace.md` Decision 8 (SQLite schema, no mention of queue persistence) — confirmed no queue-persistence mechanism in the spec.
- `evals-trace.md` Decision 2 (`make_dotted_order`) and `eval-observability.md` §LangSmith (`run_trees.py:1245`) — confirmed LangSmith uses this in a single-process SDK context; the multi-task fan_out clock-skew concern is a Verso-specific extension not present in the LangSmith use case.
- PRD §5.5 and §8 (Phase 1: eval wedge; no mention of queue durability requirement) — confirmed the PRD does not address this gap.

---

## Recommendation

**REVISE** — four targeted changes, no architectural reversal:

1. **Give `asyncio.Queue` a SQLite-backed persistence layer for v1 dev.** The fix is small: on `submit`, write `(trace_id, rule_id, status="PENDING")` to a `eval_queue` SQLite table before enqueuing in memory; on `write_score` success, update to `status="COMPLETED"`; on startup, re-enqueue all PENDING rows. This is 30 lines and makes the dev backend crash-safe, closing failure mode 1 without requiring Redis.

2. **Cap agentic judge concurrency explicitly.** Add `max_concurrent_agentic_judges: int = 2` to `EvalRule` (or globally to `EvalQueue`). The agentic judge path is the expensive one; it must not inherit the agent's `max_concurrency` budget. This closes failure mode 3 and prevents rate-limit cross-contamination.

3. **Replace `asyncio.sleep(delay_ms)` with a `store.await_trace_complete(trace_id, timeout_ms)` poll.** For the SQLite backend, the trace is immediately readable — no sleep needed. For ClickHouse, poll `SELECT count(*) FROM spans WHERE trace_id=? AND status='OK'` until non-zero or timeout. This makes the delay adaptive and correct across storage backends, closing failure mode 4.

4. **Promote `UnrecoverableError` to a durable `FAILED` job record.** The `eval_worker` must catch `UnrecoverableError`, update `DatasetRunItem.error` (or an `eval_job_runs` table), and count failures in `EvalRun.score_summaries` as `n_failed`. Expose `result.passes(thresholds=..., require_completion_rate=0.95)` in the CI gate API so a 20% silent failure rate is not a green CI check.
