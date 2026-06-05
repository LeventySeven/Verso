# Evals + Trace Schema (the wedge) — Verso Design Resolution

**Subsystem:** `evals/` + trace schema emitted by the checkpoint serializer
**PRD sections:** §5.5, §10 items 9 (code-execution escape hatch — not this file) and 13 (judge panel)
**Teardown source:** `research/03_teardowns/eval-observability.md` (Langfuse · Braintrust/autoevals · DeepEval · Arize Phoenix + OpenInference · RAGAS · Comet Opik · promptfoo · MLflow 3 · OpenLLMetry/Traceloop · Galileo Luna-2 · LangSmith — all RE'd from source at depth-1 clone, 2026-06-05)
**Resolution date:** 2026-06-05

---

## Decisions Resolved

### Decision 1 — The Universal Score Object (what the checkpoint serializer emits)

**Choice:** Emit this exact shape from every score-producing path (judge, annotation, code-assertion):

```python
@dataclass
class VersoScore:
    name: str                          # metric name / rubric label
    value: float                       # always float in [0.0, 1.0] (normalized)
    source: Literal["HUMAN", "LLM_JUDGE", "CODE"]
    label: str | None = None           # categorical string value (e.g. "relevant")
    reason: str | None = None          # judge chain-of-thought / explanation
    target_span_id: str | None = None  # FK → the span being scored
    target_trace_id: str                # FK → the trace being scored
    source_span_id: str | None = None  # FK → the judge's own trace (recursive observability)
    correction: dict | None = None     # HITL corrected value → dataset flywheel
    config_id: str | None = None       # links to a ScoreConfig for shape validation
    dataset_run_id: str | None = None  # FK → offline eval run (when set, this is an offline score)
```

**Rationale:** Every system in the teardown lands on the same five-element primitive: `(name, value:float, source-enum, label?, reason?)` + FK to `(trace_id, span_id?)`. The 3-source enum is independently rediscovered by 6 platforms under different names: `{API/EVAL/ANNOTATION}` (Langfuse), `{sdk/ui}` (Opik), `{HUMAN/LLM_JUDGE/CODE}` (MLflow `AssessmentSourceType`) — MLflow's naming is the clearest. The `correction` field (LangSmith `EvaluationResult`) is not cosmetic: it is the HITL-to-dataset flywheel. The `source_span_id` / `execution_trace_id` (Langfuse migration 0030) enables clicking from a score to the judge's own trace — recursive observability that costs nothing to include and is impossible to retrofit once scores are in the wild without it.

**Evidence:** `eval-observability.md` §Cross-System Patterns §Convergence 1; Langfuse `domain/scores.ts:4` `ScoreSourceArray = ["API","EVAL","ANNOTATION"]`; MLflow `assessment.py` `AssessmentSourceType {HUMAN,LLM_JUDGE,CODE}`; LangSmith `evaluation/evaluator.py:70` `EvaluationResult{correction, source_run_id, target_run_id}`; Langfuse migration 0030 `execution_trace_id`.

**Alternatives rejected:** Per-backend adapters (one shape per backend) — rejected because the universal shape is accepted by all 6 major backends with field renames only, adding adapters would add churn with no user benefit. Embedding scores inside span rows — rejected; Phoenix's `SpanEvaluations` separation (scores as a separate table joined by `span_id`) is proven correct: a judge re-run is an append, not a span mutation, and immutability of spans is the foundation of reproducibility.

---

### Decision 2 — The Trace/Span Schema (observation taxonomy + storage model)

**Choice:** Adopt the **10-kind observation taxonomy** from Langfuse / OpenInference (minus PROMPT, which is redundant with SPAN in a native-Python framework), plus the `dotted_order` ordering key from LangSmith:

**Span kinds (10):**
`SPAN` (generic) · `GENERATION` (any LLM call) · `AGENT` (agent loop boundary) · `TOOL` (tool invocation) · `CHAIN` (logical sub-pipeline) · `RETRIEVER` (vector/lexical search) · `EMBEDDING` (embedding call) · `GUARDRAIL` (safety check) · `EVALUATOR` (judge span) · `RERANKER` (rerank step)

**Span fields (the minimal schema — storage-backend-agnostic):**

```python
@dataclass
class VersoSpan:
    # Identity + tree structure
    id: str                           # UUIDv7 — chronological by construction
    dotted_order: str                 # "{ts_Z}{uuid7}" or "parent.{ts_Z}{uuid7}" — single sortable tree column
    trace_id: str                     # root run's id
    parent_span_id: str | None        # direct parent (redundant with dotted_order but kept for FK joins)

    # Classification
    kind: SpanKind                    # the 10-kind enum above
    name: str                         # human-readable label

    # Timing
    start_time: datetime              # UTC, microsecond precision
    end_time: datetime | None         # None while the span is open

    # Payload
    input: str | None                 # ZSTD-compressed in ClickHouse (CODEC(ZSTD(3)))
    output: str | None                # ZSTD-compressed
    input_mime_type: str = "text/plain"   # or "application/json"
    output_mime_type: str = "text/plain"

    # LLM-specific (set on GENERATION spans)
    model_name: str | None = None
    provider: str | None = None
    usage: dict[str, int] = field(default_factory=dict)    # Map-based: {input, output, cache_read, reasoning, ...}
    cost: dict[str, Decimal] = field(default_factory=dict) # Map-based: {input, output, cache_read, ...}

    # Tool-specific (TOOL spans)
    tool_name: str | None = None
    tool_parameters: str | None = None   # JSON
    tool_call_id: str | None = None

    # Retriever-specific (RETRIEVER spans)
    embedder: str | None = None
    top_k: int | None = None
    chunk_size: int | None = None

    # Cross-cutting
    status: Literal["OK", "ERROR", "PENDING"] = "OK"
    status_message: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    session_id: str | None = None
    user_id: str | None = None
    entity_path: str | None = None      # "agent.tool.llm" — Traceloop traceloop.entity.path
    tags: list[str] = field(default_factory=list)

    # Version link (MLflow LoggedModel pattern)
    agent_version_id: str | None = None  # tag → "all traces for version X" regression axis
    run_id: str | None = None            # links span to a Verso run/experiment
```

**`dotted_order` construction (LangSmith `run_trees.py:1245`):**
```python
def make_dotted_order(start_time: datetime, span_id: str, parent_dotted_order: str | None) -> str:
    segment = start_time.strftime("%Y%m%dT%H%M%S%fZ") + span_id
    return f"{parent_dotted_order}.{segment}" if parent_dotted_order else segment
```
One indexed string column gives: tree reconstruction, chronological sort, sibling order — no recursive parent-id walk.

**Usage/cost as `dict[str, int|Decimal]` (Map-columns in ClickHouse):**
Token counts are `dict[str, int]` — `{"input": 512, "output": 128, "cache_read": 256, "reasoning": 64}`. Rollups use `sumMap` key-wise (Langfuse `repositories/events.ts:3287`). Adding a new token category (e.g. a future provider's `video_tokens`) requires zero schema migration — it appears in the map. Discrete-attribute backends (like OpenInference `llm.token_count.prompt`) can be derived from the map on export.

**Rationale:** The 10-kind taxonomy is proven: Langfuse adopted it (migration `0001/0002/0003`) and every downstream eval metric consumes typed span kinds (MLflow's `RetrievalRelevance` scorer reads `RETRIEVER` spans; DeepEval's `ToolSpan` feeds `ToolCorrectness`; `EVALUATOR` kind marks the judge's own span). Coarser taxonomies (LangSmith's 7, with `chain` as catch-all) break downstream eval. The `dotted_order` string is strictly better than bare `parent_id` for ordered tree reconstruction. Map-based usage/cost survives provider churn; fixed columns do not.

**Evidence:** Langfuse `domain/observations.ts:5` — 10-kind taxonomy, `isGenerationLike()` predicate at `:148`; Langfuse ClickHouse `usage_details Map(LowCardinality(String),UInt64)` + `sumMap` rollup at `repositories/events.ts:3287`; LangSmith `run_trees.py:1245` `_create_current_dotted_order`; DeepEval `tracing/types.py` 5-span-type model (`AgentSpan{available_tools}`, `LlmSpan{model,input/output_token_count}`, `RetrieverSpan{embedder,top_k,chunk_size}`, `ToolSpan{description}`); MLflow `tracing/constant.py:9` `mlflow.modelId` tag; Opik `000001_init_script.sql` `spans ORDER BY (workspace_id, project_id, trace_id, parent_span_id, id)` showing trace-contiguous sort.

**Alternatives rejected:** Fixed scalar token columns — rejected; every provider has different token categories and the `Map` approach survives additions without migrations. Fewer than 10 span kinds — rejected; GUARDRAIL and EVALUATOR kinds are required for Verso's safety hooks and judge spans to be queryable as first-class objects.

---

### Decision 3 — The OTel Semconv Fork: `gen_ai.*` primary, OpenInference `openinference.*` enrichment

**Choice:** Emit **`gen_ai.*` as primary LLM-call attributes** on every GENERATION span. Optionally enrich with `openinference.span.kind` for Arize-ecosystem backends. Never emit only one namespace and drop the other.

**Always emit on a GENERATION span:**
```
gen_ai.request.model          # e.g. "claude-sonnet-4-6"
gen_ai.system                 # "anthropic" / "openai" / "google"
gen_ai.usage.input_tokens     # from usage["input"]
gen_ai.usage.output_tokens    # from usage["output"]
gen_ai.usage.cache_read_input_tokens    # from usage["cache_read"] if present
gen_ai.usage.cache_creation_input_tokens  # from usage["cache_write"] if present
gen_ai.operation.name         # "chat" / "embeddings" / "invoke_agent" / "execute_tool"
```

**`openinference.span.kind` enrichment layer** (set on every span when `verso.otel.enrichment=true`):
Map Verso span kinds → OpenInference values: `SPAN→UNKNOWN`, `GENERATION→LLM`, `AGENT→AGENT`, `TOOL→TOOL`, `CHAIN→CHAIN`, `RETRIEVER→RETRIEVER`, `EMBEDDING→EMBEDDING`, `GUARDRAIL→GUARDRAIL`, `EVALUATOR→EVALUATOR`, `RERANKER→RERANKER`.

**Bidirectional conversion** (from `openinference/_genai_conversion.py`):
```python
OPENINFERENCE_TO_GENAI = {
    "openinference.span.kind": "gen_ai.operation.name",
    "llm.token_count.prompt": "gen_ai.usage.input_tokens",
    "llm.token_count.completion": "gen_ai.usage.output_tokens",
    "llm.model_name": "gen_ai.request.model",
}
```
Ship this map in `verso/evals/otel_compat.py` so any consumer can project either direction.

**Rationale:** `gen_ai.*` is the IETF/OTel-SIG path and has broadest backend support — Langfuse's `ObservationTypeMapper.ts` (`server/otel/`) reads it at P3 (after native and OpenInference), Phoenix reads it, every OTLP collector reads it, OpenLLMetry-instrumented libraries emit it. Emitting `gen_ai.*` means any OpenLLMetry-patched provider called inside a Verso tool (OpenAI, Anthropic, Groq, etc.) integrates without adapters — Verso becomes a transparent OTLP forwarder for its own tools. The `openinference.span.kind` enrichment is one extra attribute per span — the cost is trivial; the benefit is Arize Phoenix compatibility without any change in Verso's internal model.

**Evidence:** Langfuse `server/otel/ObservationTypeMapper.ts` priority chain (P1=native, P2=openinference, P3=gen_ai — both namespaces consumed); OpenInference `_genai_conversion.py` verbatim bidirectional map; OpenLLMetry `semconv_ai/__init__.py:158` `gen_ai.*` vs `llm.*` split; `eval-observability.md` §OpenLLMetry §Namespace Fork §→ Verso Implications point 9.

**Alternatives rejected:** OpenInference-only (`llm.*` primary) — rejected; it requires a conversion step for every standard OTLP backend and Verso's users are more likely to ship to Langfuse/generic than to Arize. Dual full-namespace emit on every span — rejected; doubles the attribute payload on hot-path spans; keep OpenInference as opt-in enrichment.

---

### Decision 4 — The Judge Design: Constrained-Verdict, Never Free-Text

**Choice:** Verso's judge abstraction forces structured output. Three verdict modes, selectable per judge:

**Mode A — Structured JSON output (default):**
```python
class JudgeVerdict(BaseModel):
    reasoning: str          # chain-of-thought; persisted as score.reason
    score: float            # [0.0, 1.0] for numeric; or...
    # OR:
    label: str              # one of the configured categories
    pass_: bool | None = None  # True/False for CI gate; derived from score >= threshold
```
Force via `response_format={"type": "json_schema", "json_schema": {...}}`. On `safeParse` failure → `UnrecoverableError` (no retry — model can't fix a schema mismatch; log and skip). Reasoning is always present; persisted as `score.reason`. This matches Langfuse `features/evals/outputDefinition.ts` verdict schema and promptfoo `{reason, pass, score}`.

**Mode B — Logprob-weighted continuous score (G-Eval, numeric judges):**
```python
async def g_eval_score(
    criteria: str,
    output: str,
    input: str | None = None,
    expected: str | None = None,
    score_range: tuple[int,int] = (0, 10),
    model: str = "openai:gpt-5-mini",
) -> tuple[float, str]:
    """Returns (normalized_score [0,1], reasoning_text)."""
    # Step 1: generate evaluation steps (cached on metric instance)
    steps = await _generate_eval_steps(criteria, model)
    # Step 2: score request with top_logprobs=20
    raw, reasoning = await _score_with_logprobs(steps, output, input, expected, score_range, model)
    # Step 3: weighted expectation over top logprobs
    # filter: logprob >= log(0.01), token.isdecimal()
    # weighted_score = sum(int(tok)*exp(lp) for tok,lp in top_logprobs filtered) / sum(exp(lp) ...)
    normalized = (raw - score_range[0]) / (score_range[1] - score_range[0])
    return normalized, reasoning
```
Requires `top_logprobs` support from the model provider. Denoises variance in one call vs N-call aggregation (DeepEval `utils.py:336` `calculate_weighted_summed_score`).

**Mode C — Enum-constrained tool-call (categorical judges):**
```python
# Force the model to call select_choice(choice: Literal[...])
# Map letter→float via choice_scores dict (autoevals pattern)
# COT_SUFFIX elicits reasoning before the forced call
```
Used for classification (pass/fail, A/B/C/D/E, hallucination/clean).

**Built-in scorers shipped:**

| Scorer | Mode | Score map | Evidence |
|--------|------|-----------|----------|
| `Factuality` | C (enum A–E) | A=0.4, B=0.6, C=1.0, D=0.0, E=1.0 | autoevals `templates/factuality.yaml` |
| `ClosedQA` | C (enum Y/N) | Y=1.0, N=0.0 | autoevals `templates/closedqa.yaml` |
| `GEval(criteria)` | B (logprob) | logprob-weighted [0,1] | DeepEval `metrics/g_eval/` |
| `Faithfulness` | A (structured) | fraction of faithful statements | RAGAS `_faithfulness.py` 2-call |
| `ToolCorrectness` | deterministic | LCS-weighted / set-overlap / exact | DeepEval `metrics/tool_correctness/` |
| `AgentGoalAccuracy` | A (structured) | 0 or 1 (infer-goal→compare) | RAGAS `_goal_accuracy.py` |
| `EmbeddingSimilarity` | deterministic | `max((cos-0.7)/0.3, 0)` | autoevals `string.py:197` rescaled |
| `LLMRubric` | A (structured) | `{reason, pass, score}` | promptfoo `prompts/grading.ts:11` |
| `DAGMetric(dag)` | tree of A/B/C | terminal scores or G-Eval leaves | DeepEval `metrics/dag/` |

**Factuality asymmetric score map rationale:** subset-answer (0.4) < superset-answer (0.6) < exact (1.0) < D=0.0 (disagrees). This is intentional: missing facts hurt more than extra facts, but neither is fully correct. It's the single most load-bearing constant in autoevals and must ship verbatim, not as a uniform binary.

**EmbeddingSimilarity floor-rescale rationale:** raw cosine between any two English sentences floors around 0.7; without `(cos-0.7)/0.3` every score reads 0.7–1.0 and is uninformative. Never expose raw cosine as a 0–1 score.

**Evidence:** autoevals `py/autoevals/llm.py:91` `DEFAULT_MODEL = "gpt-5-mini"`, `:115` `build_classification_tools`, `:232` forced `tool_choice`, `:386` prompt assembly; `templates/factuality.yaml` score map; DeepEval `metrics/g_eval/utils.py:336` `calculate_weighted_summed_score`; DeepEval `metrics/g_eval/template.py:39` `score_range=(0,10)`, `top_logprobs=20`; RAGAS `metrics/_faithfulness.py:37` statement-generation prompt, `:74` NLI verification prompt; RAGAS `metrics/_goal_accuracy.py:55` `InferGoalOutcomePrompt`, `:86` `CompareOutcomePrompt`; autoevals `string.py:197` `scale_score`; promptfoo `prompts/grading.ts:11` `DEFAULT_GRADING_PROMPT`.

**Alternatives rejected:** Parsing a float from free-text — rejected by unanimous convergence across 6 platforms; all serious systems constrain the verdict. N-call aggregation for continuous scores — G-Eval's logprob-weighting achieves denoising in one call, N calls are wasteful and slower.

---

### Decision 5 — Online vs Offline Eval Architecture

**Choice:** Both modes run through a **single `EvalJob` execution engine**; the source is the only thing that changes.

**Online eval (production traces):**
```
Trace written to store
  → async queue event: XADD stream "eval_jobs" {trace_id, rule_id}
  → consumer group worker picks up (long-poll ≤20s, batch_size configurable)
  → dedup: skip if JobExecution(config_id, trace_id) already COMPLETED
  → sampling gate: if random() > rule.sampling → ack and skip
  → delay: sleep(rule.delay_ms) — lets the full trace flush before the judge reads it
  → fetch trace spans, render judge prompt, structured output verdict
  → write VersoScore with source=LLM_JUDGE
  → ACK message; on timeout (unclaimed >1min) → claim by another worker (at-least-once)
```

**Offline eval (dataset runs):**
```
EvalRun(name, dataset_id, agent_version_id) created
  → for each DatasetItem: run the agent → get trace_id
  → insert DatasetRunItem{run_id, item_id, trace_id,
      snapshot_input, snapshot_expected_output}   ← denormalized snapshot
  → same EvalJob engine runs judges against the trace
  → scores tagged with dataset_run_id
```
The `snapshot_input`/`snapshot_expected_output` denormalization is load-bearing: datasets are mutable but an experiment must be reproducible even after items are edited. This is Langfuse's `dataset_run_items` design (migration 0024).

**Queue implementation:** Redis Streams consumer group (Opik's design, `OnlineScoringEngine.java`) — simpler than Langfuse's Postgres `JobExecution` + BullMQ: `XADD` on write, consumer group, `XAUTOCLAIM` for fault tolerance. `streamMaxLen` caps the stream. For Verso v1 (dogfood, no Redis): use an async `asyncio.Queue` with a background worker coroutine; the interface is identical (`submit(trace_id, rule_id)`), Redis is a pluggable backend swap.

**Large-trace judge routing (>50k tokens):** Instead of inlining the whole trace, give the judge tools to query it. Opik `OnlineScoringEngine.prepareLlmRequest` uses `agenticToolsThresholdTokens=50_000` with `charsPerToken=4`. Ship this constant and this routing in Verso's judge runner:
```python
AGENTIC_JUDGE_THRESHOLD_TOKENS = 50_000
CHARS_PER_TOKEN_HEURISTIC = 4

if len(trace_text) / CHARS_PER_TOKEN_HEURISTIC > AGENTIC_JUDGE_THRESHOLD_TOKENS:
    verdict = await run_tool_equipped_judge(judge, trace_store, trace_id)
else:
    verdict = await run_inline_judge(judge, trace_text)
```

**Per-rule sampling:** `rule.sampling ∈ [0.0, 1.0]`; `random() > sampling → skip`. Langfuse `evalService.ts:621`.

**Evidence:** Opik `OnlineScoringEngine.java` + `OnlineScoringConfig.java` (Redis Streams design, `SCORE_FIELD_NAME="score"`, `REASON_FIELD_NAME="reason"`, `agenticToolsThresholdTokens`); Langfuse `worker/.../evalService.ts:180` `createEvalJobs`, `:612` dedup, `:621` sampling, `:635` `JobExecution{status:"PENDING"}`, `:676` BullMQ delayed queue, `:689` CANCELLED on filter-deselect; Langfuse ClickHouse migration `0024_dataset_run_items.up.sql` `(snapshot_input, snapshot_expected_output)` denormalization.

**Alternatives rejected:** Inline judge in the request hot-path — universally rejected by all 6 platforms; latency impact kills the user experience. Separate eval engine for offline vs online — adds complexity for zero benefit; the same judge, same queue, same scoring output is the correct abstraction.

---

### Decision 6 — eval==run Wiring (how an eval run is connected to the executor)

**Choice:** An `EvalRun` IS a Verso agent run. The agent's `trace_id` is the linkage key:

```python
@dataclass
class EvalRun:
    id: str                     # UUIDv7
    name: str                   # e.g. "factuality-v2-test"
    dataset_id: str
    agent_version_id: str       # links to AgentVersion (the MLflow LoggedModel equivalent)
    created_at: datetime
    status: Literal["RUNNING", "COMPLETED", "FAILED"]
    # summary (written on completion):
    score_summaries: dict[str, ScoreSummary]  # {metric_name: {mean, p50, p25, p75, n}}

@dataclass
class DatasetRunItem:
    id: str
    run_id: str                 # FK → EvalRun
    dataset_item_id: str
    trace_id: str               # FK → the agent's execution trace
    error: str | None
    # denormalized snapshot (immutable at run time):
    snapshot_input: str         # ZSTD-compressed JSON
    snapshot_expected_output: str | None

@dataclass
class DatasetItem:
    id: str
    dataset_id: str
    input: dict                 # the test input
    expected_output: str | None
    metadata: dict
```

**`AgentVersion` tagging:** every `agent.run()` and `agent.submit()` auto-tags the root span with `agent_version_id` (derived from `Agent.__version__` if set, or from a hash of the agent's config+instructions). This is the MLflow `mlflow.modelId` tag pattern. One indexed query: `SELECT * FROM scores WHERE spans.agent_version_id = X` = all scores for version X = the regression comparison axis.

**CI gate wiring:**
```python
result = await evals.run(
    agent=agent,
    dataset=dataset,
    scorers=[Factuality(), GEval(criteria="..."), ToolCorrectness()],
)
# result.compare(baseline_run_id) → regression report
# result.passes(thresholds={"factuality": 0.8, "g_eval": 0.7}) → bool for CI exit code
```
`compare()` diffs `score_summaries` across two `EvalRun`s. `passes()` exits non-zero on regression. The exact threshold-per-metric design is from Braintrust's documented CI integration.

**Evidence:** MLflow `entities/logged_model.py` `LoggedModel{model_id, name, source_run_id}` + `tracing/constant.py:9` `mlflow.modelId` tag; Langfuse `clickhouse/0024_dataset_run_items.up.sql` denormalized snapshot; Braintrust SDK `Eval(name, data, task, scores)` CI regression pattern (`eval-observability.md` §Braintrust §Eval Runner).

---

### Decision 7 — `eval.unit` / `eval.judge` API + `define_outcome` bounded loop

**Choice:** Three-tier eval API, all in `verso/evals/`:

```python
# --- Tier 1: eval.unit — deterministic CI assertions ---
from verso.evals import EvalSuite, Assertion

suite = EvalSuite.from_cases([
    {
        "input": "...",
        "expected": "...",
        "assertions": [
            Assertion.contains("Paris"),
            Assertion.regex(r"\d{4}"),
            Assertion.cost(max_usd=0.01),
            Assertion.latency(max_ms=5000),
            # trajectory assertions for ReAct loops:
            Assertion.trajectory_tool_sequence(["search", "summarize"]),
            Assertion.trajectory_tool_args_match("search", {"query": "Paris weather"}),
            Assertion.trajectory_step_count(max=5),
            Assertion.trajectory_goal_success(),
        ],
    }
])
result = await suite.run(agent)
assert result.passes(strict=True)  # CI gate

# --- Tier 2: eval.judge — LLM critic panel ---
from verso.evals import JudgePanel, JudgeConfig

panel = JudgePanel(
    judges=[
        JudgeConfig(model="anthropic:claude-sonnet-4-6", weight=0.4),
        JudgeConfig(model="openai:gpt-5", weight=0.4),
        JudgeConfig(model="google:gemini-3-pro", weight=0.2),
    ],
    scorers=[Factuality(), GEval(criteria="Is the answer helpful and accurate?")],
    threshold=0.7,
)
scores = await panel.score(trace_id="...")
# runs AFTER the agent returns; never in the hot path

# --- Tier 3: define_outcome — bounded generate→grade→revise ---
agent.define_outcome(
    rubric="The answer must cite at least 3 sources and be factually accurate.",
    max_iterations=3,   # REQUIRED — never unbounded (PRD anti-pattern #16)
    scorer=Factuality(),
    stop_when=lambda s: s.value >= 0.9,
)
# On agent.run(): loop is generate → grade → revise up to max_iterations
# If threshold reached early → stop. If max_iterations exhausted → return best result.
```

**`define_outcome` constants (from research):**
- Default `max_iterations=3`, absolute max `max_iterations=20` (hard cap). Source: Anthropic Research agent `define_outcome` (teardown `research-deepresearch`).
- `stop_when` defaults to `lambda s: s.value >= 0.9` when a numeric scorer is used.
- On each iteration: the previous output + score + `reason` are fed back as context to the agent (`rubric` stays in the system prompt; prior attempt's `reason` goes in user turn).

**Trajectory assertion types (from promptfoo `types/index.ts:589`):**
```python
class TrajectoryAssertion:
    GOAL_SUCCESS = "trajectory:goal-success"
    TOOL_SEQUENCE = "trajectory:tool-sequence"       # exact sequence match
    TOOL_ARGS_MATCH = "trajectory:tool-args-match"   # args on a specific tool call
    TOOL_USED = "trajectory:tool-used"               # set membership
    STEP_COUNT = "trajectory:step-count"             # max steps
    TOOL_CALL_F1 = "tool-call-f1"                    # F1 on (tool, args) pairs
```
These map 1:1 onto Verso's `AgentResult.step_trace` (the list of `(tool_name, tool_args, tool_result)` tuples Verso already records per step).

**Evidence:** promptfoo `types/index.ts:589` `BaseAssertionTypesSchema` full taxonomy including `trajectory:*`; promptfoo `prompts/grading.ts:11` `DEFAULT_GRADING_PROMPT`; Anthropic Research `define_outcome` bounded loop (`research-deepresearch` teardown); PRD §5.5 `define_outcome(rubric, max_iterations=3)`; `_SYNTHESIS.md` anti-pattern #16 "unbounded grader/eval loops."

---

### Decision 8 — Score Storage Schema (ClickHouse vs SQLite, dev/prod split)

**Choice:** Abstract the score/span storage behind a `TraceStore` interface; ship two implementations:

**Dev (default, zero-infra):** SQLite via `aiosqlite`:
```sql
CREATE TABLE spans (
    id TEXT PRIMARY KEY,              -- UUIDv7
    dotted_order TEXT NOT NULL,       -- sortable tree key (indexed)
    trace_id TEXT NOT NULL,
    parent_span_id TEXT,
    kind TEXT NOT NULL,               -- SpanKind enum
    name TEXT NOT NULL,
    start_time TEXT NOT NULL,         -- ISO8601 UTC
    end_time TEXT,
    input TEXT,                       -- JSON string
    output TEXT,                      -- JSON string
    usage TEXT DEFAULT '{}',          -- JSON dict
    cost TEXT DEFAULT '{}',           -- JSON dict
    model_name TEXT,
    provider TEXT,
    status TEXT DEFAULT 'OK',
    metadata TEXT DEFAULT '{}',
    session_id TEXT,
    user_id TEXT,
    entity_path TEXT,
    agent_version_id TEXT,
    tags TEXT DEFAULT '[]'
);
CREATE INDEX idx_spans_trace ON spans(trace_id);
CREATE INDEX idx_spans_order ON spans(dotted_order);
CREATE INDEX idx_spans_version ON spans(agent_version_id);

CREATE TABLE scores (
    id TEXT PRIMARY KEY,
    target_trace_id TEXT NOT NULL,
    target_span_id TEXT,
    source_span_id TEXT,              -- judge's own trace
    dataset_run_id TEXT,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    source TEXT NOT NULL,             -- HUMAN | LLM_JUDGE | CODE
    label TEXT,
    reason TEXT,
    correction TEXT,                  -- JSON (HITL flywheel)
    config_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_scores_trace ON scores(target_trace_id);
CREATE INDEX idx_scores_span ON scores(target_span_id);
CREATE INDEX idx_scores_version ON scores(target_trace_id);  -- joined with spans
```

**Prod (operator-deployed):** ClickHouse `ReplacingMergeTree(last_updated_at)` for spans+scores, Postgres for eval configs/job state. The ClickHouse schema follows Langfuse's proven design: `ORDER BY (project_id, kind, toDate(start_time), id)` puts `kind` second (dominant filter dimension for eval queries); usage/cost as `Map(LowCardinality(String),UInt64)` / `Map(LowCardinality(String),Decimal64(12))`; CODEC(ZSTD(3)) on input/output blobs; bloom filter on `id` + `metadata` keys. Scores: `ORDER BY (project_id, toDate(timestamp), name)` with bloom filter on `(project_id, target_trace_id, target_span_id)` — the join path.

**Evidence:** Langfuse ClickHouse migrations `0001/0002/0003` (observations `ORDER BY (project_id, type, toDate(start_time), id)`, `Map` usage columns, ZSTD codecs, bloom filters); Opik `000001_init_script.sql` `ORDER BY (...trace_id, parent_span_id, id)` + `value Decimal32(4)`; `eval-observability.md` §Langfuse ClickHouse schema.

---

### Decision 9 — PRD §10.13: Judge Panel Default

**Choice:** Ship a **default panel config** (overridable) with the Character.AI–validated weights, but make it a named constant, not hardcoded model strings. Users can override at agent construction or globally.

```python
# verso/evals/defaults.py

DEFAULT_JUDGE_PANEL = JudgePanel(
    judges=[
        JudgeConfig(model="anthropic:claude-sonnet-4-6", weight=0.4),
        JudgeConfig(model="openai:gpt-5-mini", weight=0.4),
        JudgeConfig(model="google:gemini-3-pro", weight=0.2),
    ],
    threshold=0.7,     # pass/fail gate
)

# Usage:
panel = JudgePanel.default()          # uses the above
panel = JudgePanel.single("openai:gpt-5")  # single-judge shorthand (no vendor lock)
panel = JudgePanel(judges=[...])      # fully custom
```

**Rationale:** The Character.AI production-validated panel (Sonnet 0.4 / GPT-4o 0.4 / Gemini 0.2, `threshold=0.7`) is the strongest empirical starting point in the harvest. However, hardcoding three specific vendor model strings as an internal constant violates PRD §10.13's anti-vendor-lock intent. The resolution: ship it as an **overridable named default** — users who want single-judge (for cost) get `.single()`, users who want production-grade multi-judge get `.default()`, users who have opinions get full config. The weights (0.4/0.4/0.2) and threshold (0.7) are durable; the specific model version strings are not (they should be updated when new model versions land). Store model strings as module-level constants updatable without touching the panel logic.

**Evidence:** `agents-character-deep` teardown — JudgeJudy panel `(Sonnet 0.4 / GPT-4o 0.4 / Gemini 0.2, threshold=0.7)` described as production-validated; PRD §10 item 13 "ship an overridable example panel config; never hardcode a single vendor"; `_SYNTHESIS.md` line 533–534.

---

## Component Spec

### `verso/evals/schema.py` — All Data Classes

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

# ---- Span kinds ----
SpanKind = Literal[
    "SPAN", "GENERATION", "AGENT", "TOOL", "CHAIN",
    "RETRIEVER", "EMBEDDING", "GUARDRAIL", "EVALUATOR", "RERANKER"
]

# ---- Score source ----
ScoreSource = Literal["HUMAN", "LLM_JUDGE", "CODE"]  # MLflow AssessmentSourceType naming

# ---- Score shape ----
@dataclass
class VersoScore:
    name: str
    value: float                           # [0.0, 1.0] normalized
    source: ScoreSource
    target_trace_id: str
    target_span_id: str | None = None
    source_span_id: str | None = None      # judge's own trace
    label: str | None = None
    reason: str | None = None
    correction: dict | None = None         # HITL→dataset flywheel
    config_id: str | None = None
    dataset_run_id: str | None = None
    id: str = field(default_factory=lambda: make_uuid7())
    created_at: datetime = field(default_factory=datetime.utcnow)

# ---- Span shape ----
@dataclass
class VersoSpan:
    id: str                                # UUIDv7
    dotted_order: str                      # "{ts}{uuid7}" or "parent.{ts}{uuid7}"
    trace_id: str
    kind: SpanKind
    name: str
    start_time: datetime
    parent_span_id: str | None = None
    end_time: datetime | None = None
    input: str | None = None
    output: str | None = None
    input_mime_type: str = "text/plain"
    output_mime_type: str = "text/plain"
    model_name: str | None = None
    provider: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    cost: dict[str, Decimal] = field(default_factory=dict)
    tool_name: str | None = None
    tool_parameters: str | None = None
    tool_call_id: str | None = None
    embedder: str | None = None
    top_k: int | None = None
    chunk_size: int | None = None
    status: Literal["OK", "ERROR", "PENDING"] = "OK"
    status_message: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    session_id: str | None = None
    user_id: str | None = None
    entity_path: str | None = None         # "agent.tool.llm" Traceloop pattern
    agent_version_id: str | None = None
    run_id: str | None = None
    tags: list[str] = field(default_factory=list)

# ---- Eval data model ----
@dataclass
class DatasetItem:
    id: str
    dataset_id: str
    input: dict
    expected_output: str | None = None
    metadata: dict = field(default_factory=dict)

@dataclass
class DatasetRunItem:
    id: str
    run_id: str
    dataset_item_id: str
    trace_id: str
    snapshot_input: str          # JSON, snapshotted at run time (immutable)
    snapshot_expected_output: str | None
    error: str | None = None

@dataclass
class ScoreSummary:
    name: str
    mean: float
    p25: float
    p50: float
    p75: float
    n: int

@dataclass
class EvalRun:
    id: str
    name: str
    dataset_id: str
    agent_version_id: str
    created_at: datetime
    status: Literal["RUNNING", "COMPLETED", "FAILED"] = "RUNNING"
    score_summaries: dict[str, ScoreSummary] = field(default_factory=dict)
```

### `verso/evals/trace.py` — Span tree builder

```python
DOTTED_ORDER_TS_FMT = "%Y%m%dT%H%M%S%fZ"

def make_dotted_order(start_time: datetime, span_id: str, parent: str | None) -> str:
    seg = start_time.strftime(DOTTED_ORDER_TS_FMT) + span_id
    return f"{parent}.{seg}" if parent else seg

class SpanContext:
    """contextvars-based span tree — used by @tool and @agent decorators."""
    _current: ContextVar[VersoSpan | None] = ContextVar("verso_current_span", default=None)

    @classmethod
    def current(cls) -> VersoSpan | None:
        return cls._current.get()

    @classmethod
    def push(cls, span: VersoSpan) -> Token:
        return cls._current.set(span)

    @classmethod
    def pop(cls, token: Token) -> None:
        cls._current.reset(token)
```

### `verso/evals/judge.py` — Judge abstraction

```python
# Constants
JUDGE_DEFAULT_MODEL = "openai:gpt-5-mini"     # autoevals DEFAULT_MODEL
G_EVAL_SCORE_RANGE = (0, 10)
G_EVAL_LOGPROB_MIN = math.log(0.01)           # filter tokens < 1% probability mass
G_EVAL_TOP_LOGPROBS = 20
FACTUALITY_CHOICE_SCORES = {"A": 0.4, "B": 0.6, "C": 1.0, "D": 0.0, "E": 1.0}
COT_SUFFIX = (
    "Answer the question by calling `select_choice` with your reasoning in a step-by-step "
    "manner to be sure that your conclusion is correct. Avoid simply stating the correct "
    "answer at the outset. Select a single choice by setting the `choice` parameter to a "
    "single choice from {{__choices}}."
)
NO_COT_SUFFIX = "Answer the question by calling `select_choice` with a single choice from {{__choices}}."
EMBEDDING_SIM_FLOOR = 0.7      # autoevals string.py:197 — raw cosine floor for English sentences
TEXT_SCORE_MAX_LENGTH = 500    # Langfuse domain/scores.ts:59
AGENTIC_JUDGE_THRESHOLD_TOKENS = 50_000   # Opik OnlineScoringEngine
CHARS_PER_TOKEN_HEURISTIC = 4             # Opik OnlineScoringEngine

class JudgeVerdict(BaseModel):
    reasoning: str
    score: float | None = None
    label: str | None = None
    pass_: bool | None = Field(None, alias="pass")

class JudgeConfig:
    model: str
    weight: float = 1.0
    use_cot: bool = True

class JudgePanel:
    judges: list[JudgeConfig]
    scorers: list[Scorer]
    threshold: float = 0.7

    @staticmethod
    def default() -> "JudgePanel": ...
    @staticmethod
    def single(model: str) -> "JudgePanel": ...
```

### `verso/evals/online.py` — Async eval queue

```python
# Rule shape (persisted in config store)
@dataclass
class EvalRule:
    id: str
    name: str
    scorer: Scorer
    sampling: float = 1.0        # Langfuse evalService.ts:621 — probability gate
    delay_ms: int = 2_000        # Langfuse `:676` — let trace flush before judge reads
    enabled: bool = True

# Queue interface (asyncio.Queue in dev, Redis Streams in prod)
class EvalQueue(Protocol):
    async def submit(self, trace_id: str, rule_id: str) -> None: ...
    async def consume(self) -> AsyncIterator[tuple[str, str]]: ...  # (trace_id, rule_id)

# Worker loop
async def eval_worker(queue: EvalQueue, store: TraceStore, rules: dict[str, EvalRule]):
    async for trace_id, rule_id in queue.consume():
        rule = rules[rule_id]
        if random.random() > rule.sampling:
            continue   # sampled out
        await asyncio.sleep(rule.delay_ms / 1000)
        trace = await store.get_trace(trace_id)
        score = await run_judge(rule.scorer, trace)
        await store.write_score(score)
```

### Key Constants (all attributed)

| Constant | Value | Source |
|----------|-------|--------|
| `DEFAULT_JUDGE_MODEL` | `"openai:gpt-5-mini"` | autoevals `llm.py:91` |
| `G_EVAL_SCORE_RANGE` | `(0, 10)` | DeepEval `template.py:39` |
| `G_EVAL_TOP_LOGPROBS` | `20` | DeepEval `utils.py:336` |
| `G_EVAL_LOGPROB_MIN` | `math.log(0.01)` | DeepEval `utils.py:336` |
| `FACTUALITY_SCORES` | `{A:0.4, B:0.6, C:1.0, D:0.0, E:1.0}` | autoevals `factuality.yaml` |
| `EMBEDDING_SIM_FLOOR` | `0.7` | autoevals `string.py:197` |
| `TEXT_SCORE_MAX_LENGTH` | `500` | Langfuse `domain/scores.ts` |
| `AGENTIC_JUDGE_THRESHOLD_TOKENS` | `50_000` | Opik `OnlineScoringEngine.java` |
| `CHARS_PER_TOKEN_HEURISTIC` | `4` | Opik `OnlineScoringEngine.java` |
| `DEFAULT_EVAL_DELAY_MS` | `2_000` | Langfuse `evalService.ts:676` |
| `DEFAULT_JUDGE_SAMPLING` | `1.0` | (production: tune down; dev default: all) |
| `DEFINE_OUTCOME_DEFAULT_ITER` | `3` | Anthropic Research `define_outcome` |
| `DEFINE_OUTCOME_MAX_ITER` | `20` | Anthropic Research `define_outcome` |
| `JUDGE_PANEL_THRESHOLD` | `0.7` | Character.AI JudgeJudy panel |
| `JUDGE_PANEL_WEIGHTS` | `[0.4, 0.4, 0.2]` | Character.AI JudgeJudy panel |
| `STUCK_THRESHOLD_IDENTICAL` | `4` | OpenHands (via `_SYNTHESIS.md`) |
| `MAX_CATEGORICAL_CATEGORIES_MIN` | `2` | Langfuse `domain/scores.ts` `MinimumCategoricalCategoryCount` |

---

## Open Unknowns

1. **G-Eval `top_logprobs` provider support.** Not all providers expose `top_logprobs` (Anthropic does not as of 2026-06; OpenAI does). Verso must either feature-detect and fall back to Mode A (structured output) when `top_logprobs` is unavailable, or restrict G-Eval to OpenAI-family providers. Needs dogfooding to find the right fallback ergonomics.

2. **Dev-time eval store persistence format.** SQLite is correct for dev, but schema migrations on a local SQLite file are annoying during rapid iteration. Whether to version the schema with Alembic or use a "drop and recreate on version mismatch" strategy needs a real dogfood iteration before deciding.

3. **`entity_path` chaining implementation detail.** Traceloop's `get_chained_entity_path` is trivial in single-process synchronous code but requires careful contextvar scoping in `asyncio` tasks spawned by `fan_out`. The exact scoping rule (does a sub-task inherit parent's `entity_path` or start fresh?) needs to be decided by using it on a real multi-agent run.

4. **ScoreConfig FK validation in the score write path.** Langfuse enforces that all scores with the same name validate against the same `ScoreConfig` shape — so you can't accidentally write a float where a categorical was expected. Implementing this in Verso's score writer adds a round-trip to the config store per score. Whether to enforce this at write time or at query/aggregate time is unclear; defer to dogfood.

5. **Distilled-SLM fast path (Luna-2 pattern).** The architecture is clear (per-metric LoRA adapter on a shared Llama 3B backbone, single-token calibrated-probability decode) but requires a training pipeline Verso doesn't have in v1. The open question is whether to expose the interface (`mode="slm"` on a scorer) as a future hook without the implementation, or defer the abstraction until there's an actual SLM to plug in.

6. **Red-team plugin × strategy decomposition.** The promptfoo factoring (what-vulnerability × how-delivered, ~379 plugins × ~33 strategies) is proven, but integrating it in Verso raises a question: should red-team be in `verso/evals/` or a separate `verso.redteam` package? The eval data model naturally accommodates it (same scores, same trace store) but the adversarial input generation is a qualitatively different workflow. Defer to Phase 3.

7. **`correction` field in the HITL→dataset flywheel.** The concept is clear: a human-corrected score on a trace can be promoted to a dataset example in one call. The UX/API for that promotion is not yet designed — `score.promote_to_dataset(dataset_id)` is a sketch, not a spec. Needs a real HITL workflow to validate.
