# Verso — Plan 17: Time-travel for the durable seam (checkpoint history + fork)

> The last reserved Tier-3 durable capability (PRD §"Out of scope" → `time-travel list/fork(at_step=N)`). The durable seam already checkpoints every step and resumes paused runs; this makes that history **inspectable** (`history()`) and **branchable** (`fork(at_step=N)`) — the canonical durable-execution debugging primitive (LangGraph `get_state_history`/fork, Temporal history), on-thesis: no graph, no step-memoization (re-run from the fork point, never silently skip).

**Goal:** a user can list a durable run's per-step trajectory and branch a new run from any past step (e.g. "retry from step 3 with a different approval"), without forking the framework.

**Done (machine-checkable):** `uv run pytest -q` green + `uv run ruff check verso tests` clean — proving each item below, AND **every prior test passes UNMODIFIED** (additive gate). 217 currently pass.

> **STATUS: SHIPPED 2026-06-14.** Both tasks implemented test-first, independently rechecked (verdict APPROVED), and pushed. `uv run pytest -q` → **227 passed, 1 skipped**; `ruff` clean. Verified: the `checkpoint` table / `load` / blob bytes are byte-identical, a legacy `.db` opens with no migration, and `verso/core/loop.py` was not touched (the `pending is None` continue path already existed).

**The additive / byte-identical invariant (load-bearing):**
- `save(cp)` / `load(trace_id)` / `delete(trace_id)` keep their exact current observable behavior. `load` still returns the *latest* checkpoint.
- The existing sqlite `checkpoint` table schema is **untouched** — history lives in a NEW `checkpoint_history` table created with `IF NOT EXISTS`, so a pre-Plan-17 `.db` opens and resumes with zero migration (its `history()` is just empty for old traces).
- `resume_loop` / `_drive` / the loop are **not touched** — `resume_loop` already continues a `pending is None` checkpoint from `cp.step+1` (the tool-resolution block is guarded by `if cp.pending is not None`), so fork-then-resume works through the existing path.

**Key discovery:** continue-from-a-pending-less-checkpoint is ALREADY supported by `resume_loop` (line ~168 guard). Time-travel therefore needs no core-loop change — only the store + two `Agent` methods.

---

## ✅ Task 1 — Per-step retention + `history()` on the CheckpointStore contract  *(`verso/durable/{checkpoint,sqlite,inmem}.py`)*

Retain one checkpoint per `(trace_id, step)` so the trajectory survives; keep `load` returning latest.

- [ ] **Failing test** (`tests/test_durable_timetravel.py`): drive a multi-step durable run; `store.history(trace_id)` returns the per-step checkpoints in ascending `step` order; `store.load(trace_id)` still returns the last one; `delete(trace_id)` clears history too; `history("unknown")` → `[]`. Cover BOTH `InMemoryCheckpointStore` and `SqliteCheckpointStore` (parametrize or two tests).
- [ ] **Implement**:
  - `checkpoint.py`: add `def history(self, trace_id: str) -> list[Checkpoint]: ...` to the `CheckpointStore` Protocol.
  - `sqlite.py`: add (additive) `DDL_HISTORY = "CREATE TABLE IF NOT EXISTS checkpoint_history (trace_id TEXT NOT NULL, step INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY (trace_id, step))"`; create it in `__init__`. In `save`, after the existing `checkpoint` upsert, also `INSERT OR REPLACE INTO checkpoint_history(trace_id, step, data) VALUES(?,?,?)` with the SAME serialized `data` blob (factor the dict-build into one local so the two writes can't drift). `history(trace_id)`: `SELECT data FROM checkpoint_history WHERE trace_id=? ORDER BY step` → deserialize each (reuse the same decode as `load`). `delete`: also `DELETE FROM checkpoint_history WHERE trace_id=?`. **Do not change the `checkpoint` table or `load`.**
  - `inmem.py`: add `self._history: dict[str, dict[int, Checkpoint]] = {}`. `save`: keep the `_cps[trace_id]` latest write; also `self._history.setdefault(cp.trace_id, {})[cp.step] = copy.deepcopy(cp)`. `history(trace_id)`: return `[copy.deepcopy(c) for _, c in sorted(self._history.get(trace_id, {}).items())]`. `delete`: also `self._history.pop(trace_id, None)`. (Deep-copy in/out, same as today.)
- [ ] Run + commit.

## ✅ Task 2 — `Agent.history()` + `Agent.fork()`  *(`verso/agent.py`; export nothing new — methods on Agent)*

- [ ] **Failing test** (`tests/test_durable_timetravel.py`): (a) `agent.history(token)` returns the trajectory (list of `Checkpoint`, ascending step). (b) `fork`: pause a run, `new = agent.fork(token, at_step=N)` returns a NEW token ≠ token; the original run's `history(token)` is unchanged; `resume(new, ...)` continues the branch and finishes; resuming the ORIGINAL still works independently (branches don't interfere). (c) `fork` from a non-paused step then `resume(new)` continues (replay from that step — proves the `pending is None` continue path). (d) `fork(token, at_step=<missing>)` raises.
- [ ] **Implement** on `Agent` (both require `self.checkpointer`, else `ValueError` like `resume`):
```python
def history(self, token: str) -> list:
    """The per-step checkpoint trajectory of a durable run (ascending step). [] if unknown."""
    if self.checkpointer is None:
        raise ValueError("history requires an Agent constructed with a checkpointer")
    return self.checkpointer.history(token)

def fork(self, token: str, *, at_step: int | None = None) -> str:
    """Branch a new run from `token`'s state at `at_step` (default: latest). Returns the new token.
    Clones the checkpoint under a fresh trace_id; the original is untouched. Continue the branch with
    resume(new_token, ...) — it re-runs from the fork point (no step-memoization)."""
    if self.checkpointer is None:
        raise ValueError("fork requires an Agent constructed with a checkpointer")
    if at_step is None:
        src = self.checkpointer.load(token)
    else:
        src = next((c for c in self.checkpointer.history(token) if c.step == at_step), None)
    if src is None:
        raise ValueError(f"no checkpoint to fork from token={token!r} at_step={at_step!r}")
    import dataclasses, uuid
    new_token = uuid.uuid4().hex
    self.checkpointer.save(dataclasses.replace(src, trace_id=new_token))
    return new_token
```
  (`dataclasses.replace` deep-enough? `Checkpoint.history` is a list of dicts — `replace` shares the ref, but the store deep-copies/serializes on save, so the branch is independent once saved. Confirm in the test by mutating nothing and asserting independence.)
- [ ] Run + commit.

## Verification plan
**Automated:** `uv run pytest -q && uv run ruff check verso tests` → green; every prior test passes unmodified. A pre-Plan-17 sqlite `.db` (old schema) still `load`s + `resume`s — assert by writing via the old-shaped row path or by confirming `IF NOT EXISTS` + untouched `checkpoint` table.
**Manual:** pause a run, `fork(at_step=1)`, resume the branch one way and the original another → two independent outcomes from one trajectory.

## Done criteria
`history()` lists a durable run's steps; `fork(at_step=N)` branches an independent run from any step; both are additive (no checkpointer ⇒ methods raise a clear error; never invoked ⇒ byte-identical). No core-loop change. Thesis intact (no graph, no hidden memoization).

## Out of scope (still deferred)
Step-output **memoization** on resume (skip already-run side-effect-free steps — fork here RE-RUNS, honestly); durable **streaming** resume; typed-state reducer channels; pgvector/Mem0 (infra-gated). Auto-pruning of history (unbounded by design; prune via `delete`).
