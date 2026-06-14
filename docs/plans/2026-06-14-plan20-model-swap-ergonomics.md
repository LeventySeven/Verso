# Verso — Plan 20: write logic once, swap the model freely (per-run override + string model)

> Goal (user's words): "separate model choice and logic so the user writes logic once and can change the model as many times as he wants." Verified against how **Pydantic AI** and **LangChain/LangGraph** actually do it (`research/notes/final_report_model-swap-agent-frameworks-*.md`). Finding: Verso **already** nails the part Pydantic AI does best and LangChain *leaks* on — one uniform `Model` Protocol that `init_model` (string→Model), `FailoverModel` (fallback-as-Model), and `FakeModel` (test-as-Model) all collapse to; the loop is coded against the protocol, never a provider. The missing affordance is the *second* pattern both ship: **swap the model on one agent without rebuilding it.**

What both frameworks have that Verso lacks:
- **Pydantic AI:** `agent.run(..., model=Model|str|None)` per-call **+** `agent.override(model=...)` context manager (the override CM is *also* the test seam: `with agent.override(model=TestModel()):`).
- **LangChain:** `config={"configurable": {"model": ...}}` threaded through `.invoke()` (stringly-typed — the research flags this as a footgun; we copy the *typed* Pydantic AI shape instead).

**Honest caveat (put it in the docs, don't hide it):** swapping the model swaps **wiring, not capability** — a model that can't tool-call or won't emit valid JSON will still fail. Neither framework solves that; they decouple construction/wiring and expose capability honestly. Verso already has `inspect()` for transparency; we add a one-line caveat, not a speculative capability matrix (YAGNI).

**Done (machine-checkable):** `uv run pytest -q` green + `uv run ruff check verso tests` clean — every prior test passes UNMODIFIED. 258 currently pass. Additive: `Agent(model=<Model instance>)` + `run(task)` with no `model=` are byte-identical to today.

> **STATUS: SHIPPED 2026-06-14.** Batch X implemented test-first, independently rechecked (APPROVED — the reviewer *mutation-tested* it: reverting the reask-threading line, the override-selection line, or the `override()` `finally` each makes a test fail, proving the tests catch the regressions), and pushed. `uv run pytest -q` → **266 passed, 1 skipped**; `ruff` clean. Confirmed: the no-`model=` path and `Agent(model=<instance>)` are byte-identical; the lazy `from verso import init_model` resolves with no circular import.

---

## ✅ Task 1 — string model + per-run/scoped override on `Agent`  *(Batch X; `verso/agent.py`)*

Add one private resolver and thread an optional `model` through the run surfaces.

- [ ] **Failing test** (`tests/test_model_swap.py`): see scenarios below.
- [ ] **Implement** in `verso/agent.py`:
  - **`__init__`**: change the annotation to `model: Model | str` and resolve a string once: `self.model = _resolve(model)` where the resolver is:
    ```python
    def _resolve(model):
        if isinstance(model, str):
            from verso import init_model      # lazy: avoids the agent<->__init__ import cycle
            return init_model(model)
        return model
    ```
    Make `_resolve` a module-level function in `agent.py` (used by `__init__`, the methods, and `override`). When `model` is already a `Model`, it's returned unchanged (byte-identical).
  - **`_run`**: add `model=None`; `m = _resolve(model) if model is not None else self.model`; build `ctx` + call `run_loop` with `m` (and `model=getattr(m, "model_id", "")` in the ctx). 
  - **`run`**: add keyword `model: Model | str | None = None`; pass it to `_run(task, model=model)` AND to the reask `self._run(reask, model=model)` (so the override holds across structured-output reasks — important).
  - **`stream`**: add `model: Model | str | None = None`; resolve and pass to `run_stream` + the stream ctx's `model=` field.
  - **`resume`**: add `model: Model | str | None = None`; pass `_resolve(model) if model is not None else self.model` to `resume_loop` (so a paused/forked run can resume on a *different* model — composes with Plan 17 time-travel: `fork(at_step=N)` → `resume(new, model="openai:gpt-4o")`).
  - **`override`**: a `@contextmanager` method (import `contextlib.contextmanager`):
    ```python
    @contextmanager
    def override(self, *, model):
        """Temporarily swap the model for runs nested in this block (tests/evals/scoped swaps).
        For a single concurrent call prefer run(..., model=...) — override mutates self.model, so it is
        scoped/sequential, not for overlapping runs."""
        prev = self.model
        self.model = _resolve(model)
        try:
            yield self
        finally:
            self.model = prev
    ```
- [ ] Run + commit: `feat(agent): per-run model override + string model + override() — swap models without rebuilding`

### Test scenarios (`tests/test_model_swap.py`) — REAL assertions, offline `FakeModel`
1. **string model at construction**: `Agent(model="anthropic:claude-x")` → `agent.model` is an `AnthropicModel` with `model_id=="claude-x"` (resolved via `init_model`). And `Agent(model="openai:gpt-4o").model` is an `OpenAIModel`.
2. **`Model` instance still works (byte-identical)**: `Agent(model=FakeModel([...]))` unchanged.
3. **per-run override picks the override model, not the constructed one**: build `agent = Agent(model=fm_default, tools=[])` where `fm_default` would return "DEFAULT"; `await agent.run("x", model=fm_other)` where `fm_other` returns "OTHER" → result.output=="OTHER"; and a subsequent `await agent.run("x")` (no override) returns "DEFAULT" (the override didn't stick). Use two distinct `FakeModel`s.
4. **override applies across structured-output reasks**: with `output_type` + a `FakeModel` that needs one reask, `run(..., model=fm_override)` uses `fm_override` for BOTH the first try and the reask (assert via the override model's call count / that the default model was never called).
5. **`override()` context manager**: `with agent.override(model=fm_test): r = await agent.run("x")` → uses `fm_test`; after the block `agent.model is fm_default` (restored, even if the body raises — test the finally with a `try`).
6. **resume on a different model**: pause a run (ASK gate, durable), then `agent.resume(token, approve=True, model=fm_b)` finishes via `fm_b` (assert its output). (Confirms the resume override path.)
7. **stream override**: `agent.stream("x", model=fm_b)` yields the `done` event whose result came from `fm_b`.

## Verification plan
**Automated:** `uv run pytest -q && uv run ruff check verso tests` → green; prior tests unmodified; `Agent(model=<instance>)`/`run(task)` byte-identical.
**Manual:** `a = Agent("anthropic:claude-sonnet-4-6", tools=[...]); await a.run(q); await a.run(q, model="openai:gpt-4o"); await a.run(q, model="groq:llama-3.3-70b-versatile")` — same logic, three models, zero rebuilds.

## Done criteria
One `Agent` (logic fixed) runs against any model by string or instance — per call (`run/stream/resume(model=)`), or scoped (`override()`), or as the default (`Agent(model=)`). Matches Pydantic AI's typed shape (the research's top-ranked pattern); avoids LangChain's stringly-typed `configurable` footgun. Additive; loop untouched; thesis intact.

## Out of scope
- **Pre-registered named alternatives** (LangChain `configurable_alternatives`, "fast"/"smart" aliases) — trivially user-doable with a dict of models + `run(model=models["fast"])`; not worth an abstraction (YAGNI).
- **A capability/profile matrix** — the honest caveat is a doc line + `inspect()`; a real matrix is speculative until dogfood asks.
- **contextvar-based async-safe `override`** — the per-run `model=` arg is the concurrency-safe path; `override()` is documented as scoped/sequential (matches the 95% test/eval use).
