# Verso Phase 1 — Plan 6: Evals, the wedge

> **✅ SHIPPED** — implemented test-first, independently rechecked-APPROVED, on `main`.

> **Phase-1 plan set (risk-ordered):** **Plan 6 — evals (this doc, the wedge + the Phase-1 exit criterion)** → Plan 7 — memory → Plan 8 — safety/hooks. They are independent modules; evals is first because it is the headline differentiator and the §13 Phase-1 exit ("an eval suite drives an iteration on the Phase-0 agent").
>
> **For agentic workers:** implement task-by-task with `compound-v:batched-implementation`. Steps use the TDD rhythm (failing test → run → minimal code → run → commit). Do **not** edit a test to make it pass; the suspect is the code, not the test.

**Goal:** ship the eval wedge as a small, real, **in-process** surface on top of the Phase-0 agent: `Eval.unit()` (a feature×scenario assertion suite that runs the agent) with per-step pass rate + `pass^k`, `Eval.judge()` over a pluggable multi-vendor `JudgePanel`, `define_outcome()` (bounded generate→grade→revise), `VersoSpan`/`VersoScore` (a captured-run + score, built by consuming the *existing* `agent.stream()`), and the **OTel `gen_ai.*` projection** (the locked §13/§10 BUILD: dot-form cache attrs, no `RERANKER` span — the export bridge to the composed Langfuse). The heavy *engine* (Langfuse trace store + scheduler / autoevals scorers / Braintrust CI) is **COMPOSED** behind thin interfaces, not built; the in-process surface needs none of it.

**Done (plan-level, machine-checkable):** `uv run pytest -q` green + `uv run ruff check verso tests` clean, where the new tests prove: a feature×scenario `Eval.unit()` suite runs the Phase-0 `Agent` (offline, `FakeModel`) and reports per-case pass/fail; `define_outcome(...)` runs a **bounded** generate→grade→revise loop that provably stops; a `VersoSpan` round-trips through JSONL (the `from_trace` substrate). No new runtime dependency (the composed engines are optional extras).

**Approach / key facts (research fold-in — the implementer has none of my context):**
- The Phase-0 agent already streams typed events — `verso/stream/events.py`: `EventType.{STEP, MESSAGE_DELTA, REASONING_DELTA, TOOL_START, TOOL_RESULT, ERROR, DONE}`; `StreamEvent(type, text, tool, arguments, ok, content, step, error, result)`. The terminal `DONE` event carries the `AgentResult`. **A `VersoSpan` is built by consuming `agent.stream(task)` — there is no core/loop change in this plan.**
- `Agent` (`verso/agent.py:15`): `Agent(model, tools=(), *, instructions=None, max_steps=25, max_context_tokens=None)`; `agent.run(task, *, output_type=None) -> AgentResult`; `agent.stream(task) -> AsyncIterator[StreamEvent]`; `agent.inspect(task) -> ContextBundle` (already returns *exactly what the model sees*, turn 1 — this **is** the "trace renderer shows the raw context window" surface; reuse it, don't rebuild it).
- `AgentResult` (`verso/types.py:26`): `output, stop_reason: StopReason, usage: Usage, steps, parsed`. `StopReason` = `END_TURN | DONE | MAX_STEPS | ERROR`.
- Test substrate: `verso/model/fake.py` `FakeModel([ModelResponse(...), ...])` replays scripted responses and supports `.stream`; `ModelResponse(text, tool_calls, usage)`; `ToolCall(id, name, arguments)`. Tests are `async` (pytest `asyncio_mode=auto`). Commit after each green test. Patterns to follow: small single-responsibility files, `from __future__ import annotations`, dataclasses, no new deps in the core path.
- **§14.8 deltas folded here (the high-value ones only):** the **verifiability hierarchy** (an `Assertion` is preferred over a judge — execution/deterministic checks first; the judge is the fallback where ground truth is intractable); **pass^k** repeat-consistency (reliability is a distribution, not a point); the **eval-gaming guard** (the grader sees the captured `VersoSpan`, never the agent's mutable state — isolate the grader from the agent's write surface); **`from_trace`** = incident→regression (a captured failure *is* a span → freeze it into the suite); the **prod==eval invariant** (evals run the *real* `Agent` via the same stream, never a simplified path); **`--judge-model <other-provider>`** ergonomics + the precision/recall alignment note.
- **BUILD per §13 (do not skip):** the `VersoSpan`/`VersoScore` types **and** the `to_otel_attrs()` projection (`gen_ai.*` dot-form; no `RERANKER`) — this is the native-trace export surface, not a deferral; the three-tier `unit → judge → experiment` shape (Phase 1 builds `unit` + `judge`; `experiment` = the composed Braintrust/A-B, deferred); per-step pass rate (the *metric*, cheap — distinct from PRM hooks).
- **DEFER (lock-interface, build nothing — §14.8):** simulation fixtures (mock-API + LLM-simulated user), per-step **PRM** verification hooks, the second-half (HITL/stateful) eval mode, the `task_duration_estimate` calibration, the live Langfuse scheduler. Note the seam; do not build.

**Divergence rule:** if a load-bearing assumption proves false (e.g. `FakeModel.stream` does not surface `TOOL_START/TOOL_RESULT` cleanly, or a `VersoSpan` cannot be reconstructed from the stream), **stop after ~3 attempts and report back** — do not invent a parallel core event emitter to work around it; that is Plan-7/Phase-2 territory.

**User Review Required:** none. This plan adds a new `verso/evals/` module + tests only; it makes **no** change to `core/loop.py`, the public `Agent` surface, or any shipped behavior. No migrations, no destructive ops, no prod config.

**Tech stack:** unchanged — Python 3.12 (uv), Pydantic v2 available but not required here, pytest + `FakeModel`. The composed engines (`langfuse`, `autoevals`/`deepeval`, `braintrust`) are **optional extras** declared in `pyproject.toml`, imported lazily, never in the test path.

---

## File structure

```
verso/
└── evals/
    ├── __init__.py     # NEW — exports Eval, Assertion, VersoSpan, VersoScore, define_outcome, Judge, LLMJudge
    ├── span.py         # NEW — VersoSpan (captured run, built from the stream) + VersoScore + JSONL round-trip + render
    ├── judge.py        # NEW — Judge protocol + LLMJudge + JudgePanel (post-hoc, pluggable, multi-vendor)
    ├── suite.py        # NEW — Eval: .unit(cases) matrix + .judge(panel) + pass^k + per-step pass rate; Assertion
    ├── outcome.py      # NEW — define_outcome(rubric, max_iterations=3): bounded generate→grade→revise
    └── otel.py         # NEW — VersoSpan/VersoScore → gen_ai.* dot-form attrs (the export bridge to composed Langfuse)
tests/
├── test_evals_span.py        # NEW
├── test_evals_unit.py        # NEW
├── test_evals_judge.py       # NEW
└── test_evals_outcome.py     # NEW
verso/__init__.py             # MODIFY — export the evals surface
pyproject.toml                # MODIFY — add optional-dependency group [evals] (composed engines)
README.md                     # MODIFY — append an evals snippet
```

---

## Task 1: `VersoSpan` / `VersoScore` — capture a run from the stream

**Files:** Create `verso/evals/__init__.py` (empty for now), `verso/evals/span.py`; Test `tests/test_evals_span.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_evals_span.py
import json
from verso import Agent, tool
from verso.evals.span import VersoSpan
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


def _agent():
    # turn 1: call add; turn 2: final answer
    fm = FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage(input_tokens=10, output_tokens=2)),
        ModelResponse(text="the answer is 3", tool_calls=[], usage=Usage(input_tokens=8, output_tokens=4)),
    ])
    return Agent(model=fm, tools=[add], instructions="be terse")


async def test_capture_from_stream_records_tools_stop_output_and_usage():
    span = await VersoSpan.capture(_agent(), "add 1 and 2")
    assert span.tool_names() == ["add"]          # which tools ran, in order
    assert span.ok                               # no tool errored
    assert span.output == "the answer is 3"
    assert span.stop_reason == "end_turn"
    assert span.steps == 2
    assert span.usage_total == 24                # 10+2+8+4
    assert span.trace_id                         # addressable


async def test_jsonl_round_trips():
    span = await VersoSpan.capture(_agent(), "add 1 and 2")
    restored = VersoSpan.from_jsonl(span.to_jsonl())
    assert restored.tool_names() == span.tool_names()
    assert restored.output == span.output
    assert restored.trace_id == span.trace_id


async def test_render_shows_tools_and_final():
    span = await VersoSpan.capture(_agent(), "add 1 and 2")
    out = span.render()
    assert "add(" in out and "the answer is 3" in out
```

- [ ] **Step 2 — run, expect FAIL** (`ModuleNotFoundError: verso.evals.span`): `uv run pytest tests/test_evals_span.py -v`

- [ ] **Step 3 — implement `verso/evals/span.py`:**

```python
# verso/evals/span.py
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field

from verso.stream.events import EventType


@dataclass
class SpanRecord:
    """One captured event in a run (the structured projection of a StreamEvent)."""
    kind: str                      # "tool" | "stop" | "step"
    name: str | None = None        # tool name (kind="tool")
    ok: bool | None = None         # tool ok (kind="tool")
    content: str | None = None     # tool result text (kind="tool")
    step: int | None = None        # kind="step"


@dataclass
class VersoSpan:
    """A captured run — built by consuming `agent.stream()`. The eval ground truth.
    Reconstructed (not the live deltas): tool calls in order, the final result, usage, stop."""
    trace_id: str
    records: list[SpanRecord] = field(default_factory=list)
    output: str = ""
    stop_reason: str = "error"
    steps: int = 0
    usage_total: int = 0

    @classmethod
    async def capture(cls, agent, task: str, *, trace_id: str | None = None) -> "VersoSpan":
        span = cls(trace_id=trace_id or uuid.uuid4().hex)
        async for ev in agent.stream(task):
            if ev.type == EventType.STEP:
                span.records.append(SpanRecord(kind="step", step=ev.step))
                span.steps = ev.step or span.steps
            elif ev.type == EventType.TOOL_RESULT:
                span.records.append(SpanRecord(kind="tool", name=ev.tool, ok=ev.ok, content=ev.content))
            elif ev.type == EventType.DONE and ev.result is not None:
                r = ev.result
                span.output, span.stop_reason = r.output, r.stop_reason.value
                span.steps = r.steps
                span.usage_total = r.usage.input_tokens + r.usage.output_tokens
                span.records.append(SpanRecord(kind="stop"))
        return span

    @property
    def ok(self) -> bool:
        return all(r.ok is not False for r in self.records if r.kind == "tool")

    def tool_names(self) -> list[str]:
        return [r.name for r in self.records if r.kind == "tool" and r.name]

    def to_jsonl(self) -> str:
        head = {"trace_id": self.trace_id, "output": self.output, "stop_reason": self.stop_reason,
                "steps": self.steps, "usage_total": self.usage_total}
        lines = [json.dumps(head, sort_keys=True)]
        lines += [json.dumps(r.__dict__, sort_keys=True) for r in self.records]
        return "\n".join(lines)

    @classmethod
    def from_jsonl(cls, text: str) -> "VersoSpan":
        lines = [json.loads(ln) for ln in text.splitlines() if ln.strip()]
        head, recs = lines[0], lines[1:]
        return cls(trace_id=head["trace_id"], output=head["output"], stop_reason=head["stop_reason"],
                   steps=head["steps"], usage_total=head["usage_total"],
                   records=[SpanRecord(**r) for r in recs])

    def render(self) -> str:
        lines = [f"trace {self.trace_id}  stop={self.stop_reason}  steps={self.steps}  tokens={self.usage_total}"]
        for r in self.records:
            if r.kind == "tool":
                lines.append(f"  tool {r.name}() -> ok={r.ok}  {(r.content or '')[:80]}")
        lines.append(f"  final: {self.output}")
        return "\n".join(lines)


@dataclass(frozen=True)
class VersoScore:
    """The result of one assertion or judge over a span."""
    name: str
    passed: bool
    value: float = 0.0             # judge score in [0,1]; assertions use 1.0/0.0
    kind: str = "assertion"        # "assertion" (deterministic, preferred) | "judge" (fallback)
    detail: str = ""
```

- [ ] **Step 4 — run, expect 3 passed:** `uv run pytest tests/test_evals_span.py -v`
- [ ] **Step 5 — commit:** `git commit -am "feat(evals): VersoSpan/VersoScore — capture a run from the stream + JSONL + render"`

---

## Task 2: `Eval.unit()` — feature×scenario assertions + pass^k (the verifiability hierarchy)

**Files:** Create `verso/evals/suite.py`; Test `tests/test_evals_unit.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_evals_unit.py
from verso import Agent, tool
from verso.evals.suite import Eval, Assertion
from verso.evals.span import VersoSpan
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


def _agent(answer="3"):
    return Agent(model=FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text=answer, tool_calls=[], usage=Usage()),
    ]), tools=[add])


# Deterministic, execution-grade assertions (the preferred tier).
called_add = Assertion("called_add", lambda s: "add" in s.tool_names())
answered_3 = Assertion("answered_3", lambda s: "3" in s.output)


async def test_unit_reports_per_case_pass_fail():
    report = await Eval.unit(
        agent_factory=lambda: _agent(),
        cases={"happy": "add 1 and 2"},
        assertions=[called_add, answered_3],
    )
    assert report.passed                                  # all assertions passed
    assert report.scores["happy"]["called_add"].passed
    assert report.scores["happy"]["answered_3"].kind == "assertion"   # deterministic tier


async def test_unit_surfaces_a_real_failure():
    report = await Eval.unit(
        agent_factory=lambda: _agent(answer="seven"),
        cases={"happy": "add 1 and 2"},
        assertions=[answered_3],
    )
    assert not report.passed
    assert not report.scores["happy"]["answered_3"].passed


async def test_pass_k_reports_distribution_not_a_point():
    # reliability is a distribution: run the same case k times, report the pass rate.
    rate = await Eval.pass_k(lambda: _agent(), "add 1 and 2", answered_3, k=5)
    assert rate == 1.0
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement `verso/evals/suite.py`:**

```python
# verso/evals/suite.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from verso.evals.span import VersoSpan, VersoScore


@dataclass(frozen=True)
class Assertion:
    """A deterministic check over a captured run — the preferred (execution) tier of the
    verifiability hierarchy: execution/structural checks first, the judge only as a fallback."""
    name: str
    check: Callable[[VersoSpan], bool]

    def score(self, span: VersoSpan) -> VersoScore:
        ok = bool(self.check(span))
        return VersoScore(name=self.name, passed=ok, value=1.0 if ok else 0.0, kind="assertion")


@dataclass
class UnitReport:
    scores: dict[str, dict[str, VersoScore]] = field(default_factory=dict)   # case -> name -> score

    @property
    def passed(self) -> bool:
        return all(sc.passed for case in self.scores.values() for sc in case.values())


class Eval:
    @staticmethod
    async def unit(*, agent_factory: Callable[[], "object"], cases: dict[str, str],
                   assertions: list[Assertion]) -> UnitReport:
        """Run `agent` (a fresh instance per case — prod==eval: the real Agent via the same stream)
        over a feature×scenario matrix and score each with deterministic assertions."""
        report = UnitReport()
        for case_name, task in cases.items():
            span = await VersoSpan.capture(agent_factory(), task, trace_id=f"{case_name}")
            report.scores[case_name] = {a.name: a.score(span) for a in assertions}
        return report

    @staticmethod
    async def pass_k(agent_factory: Callable[[], "object"], task: str,
                     assertion: Assertion, *, k: int = 5) -> float:
        """pass^k — repeat the same case k times; return the pass rate (reliability is a distribution)."""
        passes = 0
        for i in range(k):
            span = await VersoSpan.capture(agent_factory(), task, trace_id=f"k{i}")
            passes += int(assertion.score(span).passed)
        return passes / k
```

- [ ] **Step 4 — run, expect 3 passed.**
- [ ] **Step 5 — commit:** `git commit -am "feat(evals): Eval.unit feature×scenario matrix + pass^k; deterministic Assertion tier"`

---

## Task 3: `Judge` — pluggable, post-hoc, different-provider (the fallback tier)

**Files:** Create `verso/evals/judge.py`; Test `tests/test_evals_judge.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_evals_judge.py
from verso.evals.judge import LLMJudge
from verso.evals.span import VersoSpan
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse
from verso.types import Usage


async def test_llm_judge_scores_a_span_posthoc_and_is_isolated():
    # The judge model returns a verdict; the judge sees ONLY the captured span, never the agent's
    # mutable state (the eval-gaming guard). FakeModel returns the judge's JSON verdict.
    judge_model = FakeModel([ModelResponse(text='{"passed": true, "value": 0.9, "detail": "answers the question"}', tool_calls=[], usage=Usage())])
    judge = LLMJudge(model=judge_model, rubric="Does the answer resolve the task?")
    span = VersoSpan(trace_id="x", output="the answer is 3", stop_reason="end_turn", steps=2)
    score = await judge.score(span)
    assert score.passed and score.value == 0.9 and score.kind == "judge"


async def test_judge_failure_is_a_score_not_an_exception():
    judge_model = FakeModel([ModelResponse(text='{"passed": false, "value": 0.1, "detail": "wrong number"}', tool_calls=[], usage=Usage())])
    judge = LLMJudge(model=judge_model, rubric="...")
    score = await (LLMJudge(model=judge_model, rubric="...")).score(VersoSpan(trace_id="x", output="seven"))
    assert not score.passed
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement `verso/evals/judge.py`:**

```python
# verso/evals/judge.py
from __future__ import annotations
from typing import Protocol, runtime_checkable

from verso.evals.span import VersoSpan, VersoScore
from verso.tools.coerce import coerce
from verso.model.base import Model, Message


@runtime_checkable
class Judge(Protocol):
    async def score(self, span: VersoSpan) -> VersoScore: ...


class LLMJudge:
    """Post-hoc LLM judge — NEVER in the hot path. Pluggable model (use a *different* provider
    than the agent under test; `--judge-model <other-provider>`). The judge sees only the captured
    span (the eval-gaming guard: it is isolated from the agent's write surface).

    NOTE for alignment work: when validating a judge against human labels, score it by
    precision/recall, NOT raw agreement (raw agreement misleads under class imbalance — §14.8)."""
    def __init__(self, model: Model, rubric: str, name: str = "judge"):
        self.model, self.rubric, self.name = model, rubric, name

    async def score(self, span: VersoSpan) -> VersoScore:
        prompt = (f"Rubric: {self.rubric}\n\nThe agent produced this final output:\n{span.output}\n\n"
                  'Reply with ONLY JSON: {"passed": bool, "value": 0..1, "detail": str}.')
        resp = await self.model.complete([Message(role="user", content=prompt)], [])
        try:
            v = coerce(resp.text, dict)
            return VersoScore(name=self.name, passed=bool(v.get("passed")),
                              value=float(v.get("value", 0.0)), kind="judge", detail=str(v.get("detail", "")))
        except Exception as e:                       # a judge failure is a score, never an exception into the suite
            return VersoScore(name=self.name, passed=False, value=0.0, kind="judge", detail=f"judge-parse-error: {e}")
```

- [ ] **Step 4 — run, expect 2 passed.** (If `coerce(resp.text, dict)` does not accept a top-level dict, use the existing `jsonish` parse from `verso/tools/jsonish.py` directly — confirm the call shape in `verso/tools/coerce.py` first; do not invent a parser.)
- [ ] **Step 5 — commit:** `git commit -am "feat(evals): pluggable post-hoc LLMJudge (different-provider, span-isolated)"`

---

## Task 4: `define_outcome()` — bounded generate→grade→revise

**Files:** Create `verso/evals/outcome.py`; Test `tests/test_evals_outcome.py`.

- [ ] **Step 1 — failing test:**

```python
# tests/test_evals_outcome.py
from verso import Agent
from verso.evals.outcome import define_outcome
from verso.evals.span import VersoScore
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse
from verso.types import Usage


def _agent(answers):
    return Agent(model=FakeModel([ModelResponse(text=a, tool_calls=[], usage=Usage()) for a in answers]))


async def test_stops_on_pass():
    # grader passes on attempt 2 → exactly 2 generations, loop stops.
    attempts = {"n": 0}
    def grader(span) -> VersoScore:
        attempts["n"] += 1
        return VersoScore("rubric", passed=(attempts["n"] >= 2), value=1.0)
    result = await define_outcome(_agent(["v1", "v2", "v3"]), "task", grader, max_iterations=3)
    assert result.passed and result.iterations == 2


async def test_is_bounded_never_unbounded():
    # grader never passes → must stop at max_iterations, not loop forever.
    result = await define_outcome(_agent(["a", "b", "c", "d"]), "task",
                                  lambda span: VersoScore("rubric", passed=False), max_iterations=3)
    assert not result.passed and result.iterations == 3
```

- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement `verso/evals/outcome.py`:**

```python
# verso/evals/outcome.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from verso.evals.span import VersoSpan, VersoScore


@dataclass
class OutcomeResult:
    passed: bool
    iterations: int
    last_span: VersoSpan | None = None


async def define_outcome(agent, task: str, grader: Callable[[VersoSpan], VersoScore],
                         *, max_iterations: int = 3) -> OutcomeResult:
    """Bounded generate→grade→revise. NEVER an unbounded `while True` (Anthropic define_outcome:
    default 3, hard cap 20). `grader` takes a captured span and returns a VersoScore; on fail the
    task is re-asked with the prior output. Stops on the first pass or at `max_iterations`."""
    if not (1 <= max_iterations <= 20):
        raise ValueError("max_iterations must be in [1, 20]")
    current, span = task, None
    for i in range(1, max_iterations + 1):
        span = await VersoSpan.capture(agent, current, trace_id=f"outcome-{i}")
        score = grader(span)
        if score.passed:
            return OutcomeResult(passed=True, iterations=i, last_span=span)
        current = (f"{task}\n\nYour previous attempt was:\n{span.output}\n\n"
                   f"It did not satisfy the rubric ({score.detail}). Revise and try again.")
    return OutcomeResult(passed=False, iterations=max_iterations, last_span=span)
```

- [ ] **Step 4 — run, expect 2 passed.**
- [ ] **Step 5 — commit:** `git commit -am "feat(evals): define_outcome — bounded generate→grade→revise"`

---

## Task 5: `from_trace` (incident→regression) + exports surface + README

**Files:** Modify `verso/evals/suite.py` (add `Eval.from_trace`), `verso/evals/__init__.py`, `verso/__init__.py`, `pyproject.toml`, `README.md`. Test: extend `tests/test_evals_unit.py`.

- [ ] **Step 1 — failing test (append to `tests/test_evals_unit.py`):**

```python
# --- appended: incident -> regression ---
from verso.evals.suite import Eval
from verso.evals.span import VersoSpan


def test_from_trace_replays_a_saved_span_into_an_assertion():
    # A captured production failure IS a span; freeze it into the permanent suite.
    failed = VersoSpan(trace_id="incident-42", output="seven", stop_reason="end_turn", steps=1)
    jsonl = failed.to_jsonl()
    report = Eval.from_trace(VersoSpan.from_jsonl(jsonl), [answered_3])
    assert not report.passed                       # the regression reproduces the failure
    assert "incident-42" in report.scores
```

- [ ] **Step 2 — run, expect FAIL** (`Eval.from_trace` not defined).
- [ ] **Step 3 — add `Eval.from_trace` to `verso/evals/suite.py`:**

```python
    @staticmethod
    def from_trace(span: VersoSpan, assertions: list[Assertion]) -> UnitReport:
        """incident -> regression: score a *captured* span (a real past run, e.g. a production
        failure loaded from JSONL) against assertions. The accreting corpus of these IS the moat."""
        report = UnitReport()
        report.scores[span.trace_id] = {a.name: a.score(span) for a in assertions}
        return report
```

- [ ] **Step 4 — write `verso/evals/__init__.py`:**

```python
# verso/evals/__init__.py
from verso.evals.span import VersoSpan, VersoScore, SpanRecord
from verso.evals.suite import Eval, Assertion, UnitReport
from verso.evals.judge import Judge, LLMJudge
from verso.evals.outcome import define_outcome, OutcomeResult

__all__ = ["VersoSpan", "VersoScore", "SpanRecord", "Eval", "Assertion",
           "UnitReport", "Judge", "LLMJudge", "define_outcome", "OutcomeResult"]
```

- [ ] **Step 5 — export from `verso/__init__.py`** (add to the imports and `__all__`): `from verso.evals import Eval, Assertion, VersoSpan, VersoScore, define_outcome, LLMJudge` and add those names to `__all__`.

- [ ] **Step 6 — `pyproject.toml`: add the composed-engine extras (interface only; build nothing).** Append to `[project.optional-dependencies]`:

```toml
evals = ["langfuse>=2", "autoevals>=0.0.100", "braintrust>=0.0.150"]
```

Add a one-line note in `verso/evals/__init__.py` docstring: *"The heavy engine is composed, not built: install `verso[evals]` to export `VersoSpan` to Langfuse / score with autoevals / run offline CI with `braintrust.Eval()`. These are optional and lazily imported; the in-process surface above needs none of them."* (Do **not** import them at module top level.)

- [ ] **Step 7 — run the full suite + lint:** `uv run pytest -q` → all green (live test still skipped); `uv run ruff check verso tests` → clean.

- [ ] **Step 8 — README: append before `## Status`:**

````markdown
**Evals in the box** — the wedge no framework ships. Assertions are deterministic (preferred);
the LLM judge is the fallback. Evals run the *real* agent (prod == eval):

```python
from verso import Eval, Assertion, define_outcome

called_tool = Assertion("used_search", lambda s: "search" in s.tool_names())
report = await Eval.unit(agent_factory=lambda: agent, cases={"q1": "..."}, assertions=[called_tool])
rate = await Eval.pass_k(lambda: agent, "...", called_tool, k=5)     # reliability is a distribution

# a captured production failure IS a regression test:
Eval.from_trace(VersoSpan.from_jsonl(open("incident-42.jsonl").read()), [called_tool])
```
````

- [ ] **Step 9 — commit:** `git commit -am "feat(evals): from_trace incident→regression + exports + composed-engine extras + README"`

---

## Task 6: judge panel (`Eval.judge`), per-step pass rate, and OTel `gen_ai.*` emit

These are the three §13/§5.5/§14.8 pieces that complete the wedge (not deferrals).

**Files:** Modify `verso/evals/judge.py` (+ `JudgePanel`), `verso/evals/suite.py` (+ `Eval.judge`), `verso/evals/span.py` (+ `step_pass_rate`); Create `verso/evals/otel.py`; Modify `verso/evals/__init__.py`, `verso/__init__.py`. Test: extend `tests/test_evals_judge.py`, new `tests/test_evals_otel.py`.

- [ ] **Step 1 — failing tests:**

```python
# --- appended to tests/test_evals_judge.py ---
from verso.evals.judge import LLMJudge, JudgePanel
from verso.evals.span import VersoSpan, SpanRecord
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse
from verso.types import Usage


def _judge(verdict):  # one judge whose model returns a fixed verdict
    return LLMJudge(model=FakeModel([ModelResponse(text=verdict, tool_calls=[], usage=Usage())]), rubric="...")


async def test_panel_aggregates_by_majority_no_single_vendor():
    # 3 judges (the Character.AI-style panel is the OVERRIDABLE example default, not hardcoded vendors)
    panel = JudgePanel([_judge('{"passed": true, "value": 0.9}'),
                        _judge('{"passed": true, "value": 0.8}'),
                        _judge('{"passed": false, "value": 0.2}')])
    score = await panel.score(VersoSpan(trace_id="x", output="ok"))
    assert score.passed and score.kind == "judge"      # 2/3 majority → pass
    assert 0.6 < score.value < 0.7                      # mean of [0.9,0.8,0.2] ≈ 0.633


def test_step_pass_rate_is_separate_from_end_to_end():
    # per-step (did each tool call succeed) is distinct from the end-to-end answer being right (§5.5)
    span = VersoSpan(trace_id="x", records=[
        SpanRecord(kind="tool", name="a", ok=True), SpanRecord(kind="tool", name="b", ok=False)])
    assert span.step_pass_rate() == 0.5
```

```python
# tests/test_evals_otel.py
from verso.evals.otel import to_otel_attrs
from verso.evals.span import VersoSpan, VersoScore


def test_otel_uses_dotform_gen_ai_attrs_and_no_reranker():
    span = VersoSpan(trace_id="t1", output="hi", stop_reason="end_turn", steps=2, usage_total=24)
    span.usage_in, span.usage_out = 16, 8
    attrs = to_otel_attrs(span, [VersoScore("answered", passed=True, value=1.0)])
    assert attrs["gen_ai.usage.input_tokens"] == 16          # dot-form (the §10 locked fix)
    assert attrs["gen_ai.usage.output_tokens"] == 8
    assert attrs["gen_ai.response.finish_reason"] == "end_turn"
    assert attrs["verso.score.answered"] == 1.0
    assert not any("RERANKER" in k or "reranker" in k for k in attrs)   # §10: drop the RERANKER span kind
```

- [ ] **Step 2 — run, expect FAIL.**

- [ ] **Step 3 — add `step_pass_rate` + per-call usage to `verso/evals/span.py`.** In `VersoSpan` add `usage_in: int = 0`, `usage_out: int = 0` fields (set them in `capture` from the DONE result's `r.usage.input_tokens/output_tokens`), and the method:

```python
    def step_pass_rate(self) -> float:
        tools = [r for r in self.records if r.kind == "tool"]
        return sum(1 for r in tools if r.ok is not False) / len(tools) if tools else 1.0
```

- [ ] **Step 4 — add `JudgePanel` to `verso/evals/judge.py`:**

```python
class JudgePanel:
    """A panel of judges, aggregated by majority (pass) + mean (value). Post-hoc, never in the hot
    path. The default panel (e.g. Sonnet/GPT/Gemini) is an OVERRIDABLE example — never a hardcoded
    three-vendor lock-in. Use a different provider here than the agent under test."""
    def __init__(self, judges: list[Judge], name: str = "panel"):
        self.judges, self.name = judges, name

    async def score(self, span: VersoSpan) -> VersoScore:
        scores = [await j.score(span) for j in self.judges]
        passed = sum(s.passed for s in scores) * 2 > len(scores)      # majority
        value = sum(s.value for s in scores) / len(scores)
        return VersoScore(name=self.name, passed=passed, value=value, kind="judge",
                          detail="; ".join(f"{s.name}={s.value:.2f}" for s in scores))
```

- [ ] **Step 5 — add `Eval.judge` to `verso/evals/suite.py`** (the judge tier of unit→judge→experiment):

```python
    @staticmethod
    async def judge(*, agent_factory, cases: dict[str, str], panel) -> UnitReport:
        """Run the agent over the matrix and score each capture with a JudgePanel (the LLM-critique
        tier — use where deterministic Assertions can't express the criterion). Post-hoc only."""
        report = UnitReport()
        for case_name, task in cases.items():
            span = await VersoSpan.capture(agent_factory(), task, trace_id=case_name)
            report.scores[case_name] = {panel.name: await panel.score(span)}
        return report
```

- [ ] **Step 6 — create `verso/evals/otel.py`** (the native-trace export bridge — §13 BUILD, §10 fix):

```python
# verso/evals/otel.py
from __future__ import annotations
from verso.evals.span import VersoSpan, VersoScore


def to_otel_attrs(span: VersoSpan, scores: list[VersoScore] | None = None) -> dict:
    """Project a captured run to OpenTelemetry GenAI semantic-convention attributes (dot-form, the
    §10 locked fix: `gen_ai.usage.cache_read.input_tokens`-style; NO `RERANKER` span kind — Verso
    has no reranker primitive). This is what a composed Langfuse/OTel exporter consumes; it is the
    in-house BUILD, the exporter engine is the COMPOSE."""
    attrs = {
        "gen_ai.system": "verso",
        "gen_ai.operation.name": "agent.run",
        "gen_ai.response.finish_reason": span.stop_reason,
        "gen_ai.usage.input_tokens": span.usage_in,
        "gen_ai.usage.output_tokens": span.usage_out,
        "verso.trace_id": span.trace_id,
        "verso.steps": span.steps,
        "verso.tools": ",".join(span.tool_names()),
        "verso.step_pass_rate": span.step_pass_rate(),
    }
    for s in (scores or []):
        attrs[f"verso.score.{s.name}"] = s.value
    return attrs
```

- [ ] **Step 7 — export `JudgePanel` + `to_otel_attrs`** from `verso/evals/__init__.py` and `verso/__init__.py` (`__all__`). Run the full suite + lint: `uv run pytest -q && uv run ruff check verso tests` → green/clean.
- [ ] **Step 8 — commit:** `git commit -am "feat(evals): JudgePanel tier + per-step pass rate + OTel gen_ai.* emit (dot-form, no RERANKER)"`

---

## Verification plan

**Automated** (a fresh session runs this to confirm the plan is done):
```
uv run pytest -q && uv run ruff check verso tests
```
Expected: all green (the one live test stays skipped without `ANTHROPIC_API_KEY`). The criterion is **tests pass AND no assertion was weakened, no expected output hardcoded** — a green achieved by editing a test is a failure, not a pass.

**Manual** (what a machine can't assert): read `VersoSpan.render()` on a real run and confirm it shows the tool calls + final output legibly (this is the human-facing "what did the agent actually do" surface). Confirm `verso[evals]` is *not* required for the suite to run.

## Done criteria (Plan 6)
- `Eval.unit()` runs the Phase-0 `Agent` over a feature×scenario matrix and reports per-case pass/fail (via the deterministic `Assertion` tier).
- `Eval.pass_k()` reports a pass-rate distribution; `define_outcome()` runs a provably-bounded generate→grade→revise loop.
- `VersoSpan` captures a run from `agent.stream()`, round-trips through JSONL, and `Eval.from_trace()` replays a saved span (incident→regression).
- `LLMJudge` is pluggable, post-hoc, span-isolated, and a judge failure is a score (never an exception); `Eval.judge()` scores via a multi-vendor `JudgePanel` (majority pass + mean value, overridable example default — no hardcoded vendor lock).
- Per-step pass rate is reported separately from end-to-end (§5.5 bottleneck-finding); `to_otel_attrs()` projects a run to `gen_ai.*` **dot-form** attributes with **no `RERANKER`** span (the §10/§13 locked BUILD — the export bridge to the composed Langfuse).
- Zero new runtime dependency; the composed *engines* (Langfuse scheduler / autoevals scorers / Braintrust CI) are optional extras, lazily imported.

## Deferred to later plans (lock-interface, build nothing — §14.8)
Simulation fixtures (mock-API + LLM-simulated user); per-step **PRM** verification hooks; the second-half (HITL/stateful) eval mode; `task_duration_estimate` calibration; the `experiment` (A/B post-ship) tier; the live Langfuse *scheduler/exporter engine* (the `gen_ai.*` projection is BUILT in `otel.py` — only the engine that ships those attrs to a running Langfuse is the composed `verso[evals]` extra). Note each seam; ship none.
