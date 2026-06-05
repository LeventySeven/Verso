# Adversarial Critique: seam-mechanism — CORRECTNESS lens

**Decision under review:** `durable=True` appends exactly ONE `PersisterHook` (a `PostRunStepHook`); the ReAct loop body is byte-identical both ways (Burr `application.py:2565`). The "one-line diff, zero loop changes" seam test holds.

**Lens:** CORRECTNESS — does the cited RE'd evidence actually prove this works for Verso's exact case? Verify load-bearing file:line claims. Find any place the mechanism is technically wrong or fails to compose with the other Verso subsystems.

---

## The Attack

The decision makes two inter-dependent claims:

1. **Claim A (source-level):** Burr `application.py:2565` proves the seam is a single `PersisterHook` appended to a `LifecycleAdapterSet`; the loop body has zero awareness of persistence.
2. **Claim B (design-level):** Verso's ReAct loop body will be "byte-identical" in tactical vs durable mode.

**Claim A is verified and correct.** Claim B is not supported by the rest of the resolution document, and the two are in direct contradiction.

### What Burr actually proves at `application.py:2565` (VERIFIED)

Cloned `apache/burr` at HEAD. The mechanism is as cited:

```python
# application.py:2565 — _set_sync_state_persister
self.lifecycle_adapters.append(persistence.PersisterHook(self.state_persister))
```

```python
# persistence.py:214 — PersisterHook (the ENTIRE seam)
class PersisterHook(PostRunStepHook):
    def post_run_step(self, ..., state, action, result, exception, **kw):
        status = "completed" if exception is None else "failed"
        self.persister.save(partition_key, app_id, sequence_id, action.name, state, status)
```

```python
# application.py:991-1002 — loop fires hook from outside the action body
finally:
    if _run_hooks:
        self._adapter_set.call_all_lifecycle_hooks_sync(
            "post_run_step",
            app_id=self._uid, ..., state=new_state, result=result, exception=exc,
        )
```

The loop infrastructure fires the hook in a `finally` block. The `@action` function body — the thing analogous to Verso's ReAct loop body — never calls anything related to persistence. The persist hook is entirely outside the action body. **This part is correctly cited.**

### Where the evidence fails to prove Verso's claim B

The resolution makes the design concrete in D9 (`The ctx.step() Call Contract`):

```python
# durable-runtime.md D9
async with ctx.step("llm_call_{n}", kind=StepKind.LLM_CALL) as s:
    s.result = await model.call(bundle)

# And tool calls:
async with ctx.step(f"tool_{tool_name}_{n}", kind=StepKind.TOOL_CALL) as s:
    s.result = await tool.run(...)
```

This is explicitly stated: *"The LLM call is ALWAYS wrapped in `ctx.step(...)` so a crash mid-inference does not re-call the model on resume."*

Compare to the PRD §5.1 loop pseudocode (the claimed "byte-identical" body):

```
while not cancelled and budget.remaining:
    bundle = assemble_context(...)
    response = await model.call(bundle)      # NO ctx.step() here
    if response.tool_calls:
        results = await dispatch(response.tool_calls)   # NO ctx.step() here
    else:
        return finalize(response)
```

**The loop bodies are not byte-identical.** The durable loop body wraps every `model.call` and `dispatch` in `ctx.step()`. The tactical loop body does not. This is a direct contradiction between api-and-peers.md Decision 1 ("byte-identical, never branches on `if durable`") and durable-runtime.md D9 ("the LLM call is ALWAYS wrapped in `ctx.step()`").

### Why this matters technically (not just terminologically)

The Burr mechanism works because the step boundary coincides with the action boundary — the persistence hook fires once per action, entirely outside the action body. The action body is invariant because the checkpointing unit == the loop unit.

In Verso, the checkpointing unit (one LLM call or one tool call) is **finer-grained than the loop unit** (one full ReAct iteration = one LLM call + zero-or-more tool calls). Burr's `PersisterHook` pattern cannot checkpoint at sub-iteration granularity; it fires once per step, where a step IS a complete action. If Verso uses a `PostRunStepHook` per ReAct iteration, it cannot memoize the LLM call independently from the tool call within the same iteration. If it uses `ctx.step()` inline for sub-iteration checkpointing, the loop body is not byte-identical.

The design correctly chose `ctx.step()` inline (DBOS/Centaur pattern) over `PostRunStepHook` (Burr pattern) — but then incorrectly cited Burr's `application.py:2565` as the proof that "the loop body is byte-identical." Burr is the right reference for the *principle* (seam through lifecycle hook); it is not the right reference for the *implementation* Verso is actually building.

### The actual seam model Verso is building

The design in D9 is coherent and well-grounded in DBOS/Centaur/Inngest. The seam works through **polymorphism on `RunContext`**:

- `TacticalRunContext.backend` = `InMemoryBackend` → `ctx.step()` does a dict lookup (near-zero cost), yields the callable, stores result in memory dict, never hits IO.
- `DurableRunContext.backend` = `PostgresBackend` → `ctx.step()` does `GET step_output` (DB read), yields on cache miss, persists result on completion.

The loop body is identical in source text. It is not identical in execution semantics. Whether this qualifies as "byte-identical" is a definitional question — in practice, calling it "byte-identical" communicates a guarantee (the loop has no branching, no awareness) that is true at the source level but misleading at the semantic level because the behavior of `ctx.step()` on a cache hit is qualitatively different (returns immediately without running the function vs runs the function).

**The key correctness risk the resolution does not address:** For the seam to hold, `InMemoryBackend.get_step_output()` must always return `None` (no cache hit) so that in tactical mode `ctx.step()` always runs the wrapped function — the tactical loop must behave as if the steps are uncached. This is true by design (in-memory backend has no stored outputs between runs) but it means the "identical" tactical and durable paths are only semantically equivalent at run start. On a durable resume, `ctx.step()` returns the cached result immediately without calling the function. If the code inside `async with ctx.step(...) as s:` contains side effects beyond the single function call — any state mutation in the `with` body between the `yield` and exit — those side effects run in tactical mode but are skipped on durable resume. The design spec for D9 does not guard against this: it allows arbitrary caller code inside the `with` block, not just `s.result = await fn()`.

### Verdict on the load-bearing citation

`burr/core/application.py:2565` proves: **a post-step lifecycle hook can be added to a loop without changing the loop body.** CONFIRMED.

`burr/core/application.py:2565` does NOT prove: **that Verso's specific design (sub-iteration `ctx.step()` wrapping) achieves the byte-identical loop property.** The cited mechanism is a hook fired by loop infrastructure; the implemented mechanism is an inline context manager invoked by loop body code. These are architecturally different seam models.

The resolution over-claims the scope of the Burr evidence: it uses `application.py:2565` as proof of "zero loop changes" for an implementation that has a fundamentally different checkpoint granularity than Burr's.

---

## Does It Break the Decision?

**Partially.** The decision SURVIVES as a design intent: the seam IS implementable through `RunContext` polymorphism, the `InMemoryBackend` IS the tactical runtime, and the loop source text IS the same. The DBOS/Centaur precedent (not Burr) is the correct citation for this.

The decision is WRONG on one concrete claim: "byte-identical (Burr `application.py:2565`)" is a misattribution. Burr's mechanism hooks per-iteration from outside; Verso's mechanism wraps sub-iteration calls from inside. The Burr citation proves the principle but not the specific mechanism. A reader who checks `application.py:2565` and then reads the D9 spec will find the implementation inconsistent with the cited source.

There is also an unaddressed risk: the `async with ctx.step()` block allows arbitrary code inside the context manager body beyond just `s.result = await fn()`. Any side effects inside the block that are not the captured result will execute in tactical mode but be skipped on durable resume, silently diverging the two paths. This is not a loop-level issue but a correctness risk in user-facing `ctx.step()` usage that the resolution does not document as a constraint.

---

## Evidence Checked

- `/tmp/burr-verify/burr/core/application.py:2565` — `_set_sync_state_persister()` — VERIFIED as cited
- `/tmp/burr-verify/burr/core/application.py:949–1003` — `Application._step()` loop body and `finally` hook dispatch — VERIFIED: loop body has zero persistence awareness; hook fires from infrastructure
- `/tmp/burr-verify/burr/core/persistence.py:214–234` — `PersisterHook` is 4 lines, `PostRunStepHook` — VERIFIED as cited
- `research/06_design_resolutions/durable-runtime.md` D9 — `ctx.step()` as `async with` inside the loop body — contradicts "byte-identical" claim in `api-and-peers.md` Decision 1
- `docs/PRD_v1.md §5.1` — loop pseudocode has no `ctx.step()` calls — inconsistent with D9's "ALWAYS wrapped"
- `research/03_teardowns/fw-py-peers.md:20–64` — Burr seam mechanism description — correctly described in teardown

---

## Recommendation

1. **Fix the citation**: Replace `"byte-identical (Burr application.py:2565)"` with `"loop source text is identical; semantics differ through RunContext polymorphism (DBOS _core.py / Centaur workflow_engine.py:338-435 are the correct citations for sub-step memoization)"`. Burr proves the principle, not the Verso mechanism.

2. **Reconcile the loop pseudocode**: PRD §5.1 should show the `ctx.step()` wrapper around `model.call` and `dispatch`, or add a note that the pseudocode is the tactical path and the durable path wraps each call in `ctx.step()`. Leaving them inconsistent will confuse whoever implements the loop.

3. **Document the `ctx.step()` body contract explicitly**: The `async with ctx.step()` block must contain ONLY the single function call and result assignment. Arbitrary code inside the block (state mutations, logging side effects, multi-step logic) will execute in tactical mode but be skipped on durable resume. Add this as a constraint with a clear error message or enforcement in the `_StepWriter` context manager.

4. **The design itself is sound**: The `InMemoryBackend` / `PostgresBackend` polymorphism through `RunContext` is the correct seam model for sub-iteration granularity. DBOS and Centaur are the right precedents. Keep the design; fix the attribution and the documentation gap.
