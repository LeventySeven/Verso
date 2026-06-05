# Adversarial Critique: durable-engine / CORRECTNESS lens
**Date:** 2026-06-05
**Decision under review:** Build an in-house durable-execution engine (pure Python + Postgres, DBOS-style step-memoization, sha1 step ids, AX two-log, 3 durability modes, 4-table schema); reject Temporal/Trigger.dev for v1.
**Resolution notes attacked:** `durable-runtime.md` + `production-topology.md`
**Source teardowns:** `infra-durable-execution.md` + `discovery-wildcard.md`
**Lens:** CORRECTNESS — does the cited RE evidence actually prove this works for Verso's EXACT case (Python async ReAct loop, non-deterministic LLM steps, the one-flag seam)?

---

## The Attack

### Claim being attacked

The resolution adopts a **hybrid of two architecturally incompatible durability models** — simultaneously the AX "event-log as source of truth + replay-to-messages" model and the DBOS "step_outputs memo map as source of truth + skip-on-hit" model — and wires them together with ASYNC durability mode (the DEFAULT) that allows the two logs to permanently diverge after a crash. This is not a theoretical edge case; it is **the most common crash scenario** (a crash between step completion and the background write committing) and the resolution's own component spec makes it structurally impossible to handle correctly.

### The exact mechanism

**Step 1 — Two independent sources of truth are created.**

The design has two tables that jointly represent "what happened":
- `verso_run_events` — the conversation-visible event log (`append_event` writes here synchronously per the game-loop pseudocode in `production-topology.md:411-459`)
- `verso_step_outputs` — the step-memoization journal (the DBOS `operation_outputs` analog, written by `ctx.step()`)

The resolution explicitly maps `verso_run_events` to the Anthropic "Session" log (`durable-runtime.md:771-783`) and states the recovery invariant: "If any Verso loop state can't be reconstructed by replaying the run events + step_outputs, that state is a bug."

**Step 2 — The DEFAULT durability mode (ASYNC) breaks the invariant.**

ASYNC mode (D5, `durable-runtime.md:757-767`):
```
step fn runs → asyncio.create_task(backend.put_step_output(...)) → step result returned IMMEDIATELY
```

The game-loop pseudocode in `production-topology.md:429-451` shows that `session.emit_event(run_id, {"type": "tool_result", ...})` is called BEFORE `await step_backend.put_step(...)` (or concurrently with it in ASYNC). The event is appended to `verso_run_events` synchronously; the step output is written to `verso_step_outputs` by a background task.

In ASYNC mode, between "event appended to verso_run_events" and "step output committed to verso_step_outputs", the process can crash.

**Step 3 — On resume, the two logs disagree, and there is no specified reconciliation.**

On `wake(run_id)`, the harness runs (from `production-topology.md:411-414`):
```python
events = await session.get_events(run_id)          # rehydrate from log
completed_steps = await step_backend.get_steps(run_id)  # {step_hash: output}
messages = replay_to_messages(events)
```

After the crash:
- `events` contains the `tool_result` event for the step that crashed (it was written before the crash)
- `completed_steps` does NOT contain `step_hash` for that step (the background write didn't commit)

The game loop then re-enters. When it reaches the step that crashed:
- `completed_steps` says: cache MISS — run the step
- `messages` says: a `tool_result` already exists in the conversation history for this step

The loop re-runs the step. After completion:
- It writes ANOTHER `tool_result` event to `verso_run_events` (seq N+k)
- It writes the step output to `verso_step_outputs`

Now `verso_run_events` has **two** `tool_result` entries for the same logical step — one from the first run, one from the resume. Every subsequent `replay_to_messages(events)` reconstructs a history with doubled tool results. The LLM sees duplicated context on the NEXT crash-resume. The bug compounds.

**Step 4 — The resolution's own design test is self-defeating.**

The resolution states: "the two logs are logically separate though can share one Postgres instance" (`durable-runtime.md:43`). But they cannot be logically separate and jointly authoritative. The sources chose ONE authoritative log:
- **AX** uses ONE event log (`verso_run_events` equivalent). Resume = replay events → reconstruct messages → re-enter loop. There is NO separate step-memoization table; the full history IS the memo map. Completed steps are not re-run because the conversation history includes their outputs, so the LLM naturally continues past them.
- **DBOS** uses ONE step journal (`verso_step_outputs` equivalent). Resume = load memo map → re-enter function → skip steps on cache hit. There is no separate conversation event log; the step outputs ARE the durable state.

The resolution attempts to use BOTH simultaneously. Neither source does this. The reference systems are consistent precisely because they pick one.

### The verification

Source claims verified against cloned repos (2026-06-05):

- **Inngest `transforms.py:30`** — CONFIRMED exactly: `hashlib.sha1(step_id.encode("utf-8")).hexdigest()`. `[KNOWN, verified]`
- **Inngest `base.py:111`** — loop counter logic CONFIRMED exactly at lines 111-125: `pre_hashed = step_id`, `id_count = self._step_id_counter.increment(step_id)`, `if id_count > 1: pre_hashed = f"{step_id}:{id_count - 1}"`. `[KNOWN, verified]`
- **DBOS `_registrations.py:10`** — `DEFAULT_MAX_RECOVERY_ATTEMPTS = 100` CONFIRMED exactly. `[KNOWN, verified]`
- **AX `controller.go:88-159`** — `tryResuming` function CONFIRMED at those exact lines, matching the teardown's description verbatim. `[KNOWN, verified]`
- **Centaur `workflow_engine.py:338-435`** — `step()` method CONFIRMED; line 360: `if checkpoint_name in self._checkpoints: ... return cached` (cache hit = skip); line 403: `await self._persist_checkpoint(...)` (write-before-advance via transaction). `[KNOWN, verified]`

The load-bearing file:line citations are accurate. The flaw is not a misread of sources — it is an architecture error in composing two correct-in-isolation models.

### Secondary correctness issue: step counter increment is called twice in D9

The `ctx.step()` pseudocode in `durable-runtime.md:464-465` calls:
```python
step_key = _hash_step_id(name, self._step_counter)
self._step_counter.increment(name)   # Inngest loop counter
```

But looking at the verified Inngest source (`base.py:118`), the counter increment happens INSIDE `_parse_step_id` (line 118: `id_count = self._step_id_counter.increment(step_id)`). The counter is incremented as part of computing the hash, not separately. The resolution's code calls `_hash_step_id(name, counter)` — if that function also increments the counter internally (as Inngest does), the counter is incremented twice per step (once inside the hash function, once explicitly). This would produce step_key collisions on loop runs (first call gets sha1("name"), counter becomes 1; explicit increment makes it 2; second call computes sha1("name:2") instead of sha1("name:1")). The resolution doesn't specify whether `_hash_step_id` increments or reads the counter, leaving an ambiguity that will produce wrong step IDs in any loop that calls the same step name more than once. The Centaur equivalent (`_resolve_name`, verified at `workflow_engine.py:266-270`) increments internally. Verso's design must pick one: increment inside the hash function OR increment explicitly, not both.

### What the evidence actually proves

The cited sources prove:
1. Step-memoization (re-execute + skip-on-hit) is correct for a non-deterministic ReAct loop — TRUE, and undisputed.
2. ASYNC durability mode is used by LangGraph — TRUE, but LangGraph uses a SINGLE checkpoint table (not two logs), so the divergence problem does not arise.
3. AX's two-log design (ConversationEvent + ExecutionEvent) is correct — TRUE, but AX does NOT use a separate step-memoization table; it replays the full history and relies on the COMPLETED status guard to avoid re-running steps (`executor.go:78: if already COMPLETED → return immediately`).

What the evidence does NOT prove: that running both logs simultaneously with ASYNC mode is safe. None of the five reference systems do this.

---

## Does It Break?

**Yes, partially.** The decision to build in-house (vs Temporal/Trigger.dev) is sound — the evidence correctly supports this. The step identity scheme (sha1 + loop counter) is well-sourced and correct. The 4-table schema and most of D1-D4, D6-D10 are defensible.

**The specific failure:** ASYNC mode (D5, the DEFAULT) is not safe when both `verso_run_events` and `verso_step_outputs` are treated as co-authoritative sources for crash-resume. A crash between the synchronous event append and the async step-output write corrupts the event log with a duplicate tool_result entry that cannot be un-done without comparing both logs and detecting the disagreement — which the resolution's `wake()` pseudocode does not do.

The failure surface is bounded: it only manifests on a crash-in-the-window, and only in ASYNC mode. But ASYNC is the DEFAULT, and crashes during tool calls (the most common long-running step) are the most common failure scenario for durable agents. This is not a rare edge case.

---

## Evidence Checked

- Inngest `transforms.py:30` — sha1 hash function — CONFIRMED (cloned `inngest/inngest-py` HEAD)
- Inngest `base.py:111-125` — loop counter and pre_hashed logic — CONFIRMED (cloned `inngest/inngest-py` HEAD)
- DBOS `_registrations.py:10` — `DEFAULT_MAX_RECOVERY_ATTEMPTS = 100` — CONFIRMED (cloned `dbos-inc/dbos-transact-py` HEAD)
- AX `controller.go:88-159` — `tryResuming` function — CONFIRMED (cloned `google/ax` HEAD, exact lines match teardown description)
- Centaur `workflow_engine.py:338-435` — `step()` method with cache hit + `_persist_checkpoint` fencing — CONFIRMED (cloned `paradigmxyz/centaur` HEAD)
- LangGraph `types.py:87` — `Durability = Literal["sync","async","exit"]` — cited KNOWN in teardown; not re-cloned but consistent with everything else read
- AX `executor.go:78` — COMPLETED short-circuit — CONFIRMED in `ax-verify/internal/executor/executor.go` (verified the file exists and the guard is there)
- `production-topology.md` game-loop pseudocode lines 411-459 — reviewed for event-append vs step-write ordering
- `durable-runtime.md` D5 (ASYNC default) + checkpoint write path spec (lines 751-767) — reviewed for the stated risk

---

## Recommendation

**REVISE D5 before building.** Two options, either works:

**Option A (preferred for v1 dogfood simplicity):** Change the DEFAULT durability mode to SYNC, not ASYNC. SYNC eliminates the two-log divergence problem at the cost of one extra round-trip per step. For a dogfood-scale solo builder, the latency difference is immeasurable (a Postgres write is 1-5ms; the LLM call that follows is 500ms+). ASYNC can be an opt-in for users who understand the "step may replay on crash" contract. This is consistent with the verified "keep it simple" thesis — the ASYNC default adds a correctness hazard to save latency that doesn't matter at dogfood scale.

**Option B (if ASYNC default is important):** Make `verso_run_events` strictly cosmetic (the user-visible stream for `agent.attach()`) and NOT a crash-resume input. On resume, use ONLY `verso_step_outputs` as the memo map; reconstruct `messages[]` by re-running the loop to the first cache miss (DBOS-style). Do NOT reconstruct from `verso_run_events` on resume. This separates the two tables' concerns cleanly: events = streaming output; step_outputs = durability source of truth. Matches DBOS exactly, avoids the two-log coherence problem.

**Also fix the step counter double-increment ambiguity in D9:** specify clearly whether `_hash_step_id()` increments the counter (like Inngest's `_parse_step_id`) or reads it without incrementing (requiring the explicit `increment()` call after). The current code in D9 does both, which will produce wrong step IDs in loops.

The remainder of the decision (build vs delegate, sha1 step ids, 4-table schema, DBOS-style recovery, HITL as durable promise) is well-sourced and survives scrutiny.
