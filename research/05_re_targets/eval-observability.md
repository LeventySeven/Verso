# RE Targets: Eval + Observability
**Category:** eval-observability
**Relevance to Verso:** Verso's wedge is reliability — an agent framework that ships with or integrates
cleanly into eval/observability tooling closes the loop between development and production. The
tactical↔durable seam produces structured checkpoints that are natural eval attachment points. Typed
memory is a native eval surface. The open questions: what trace schema should Verso emit natively,
what eval data model should Verso's `@tool`/loop produce, and which backends to target as first-class
integrations.

---

## Already Covered

| File | What it covers | Verso-relevant depth |
|------|---------------|----------------------|
| `teardowns/LAMINAR.md` (931 lines) | Full RE of Laminar (YC S24): Rust app-server, ClickHouse + Quickwit + Postgres storage, the **Signals AI agent pipeline** (filter→summarize→tool-calling agent on compressed traces), span data model, DLX batch pattern, RabbitMQ fanout, gRPC OTLP ingestion | High — the Signals agent is the novel primitive: 3-stage trace compression before LLM, fixed `MAX_ALLOWED_STEPS=5`, 10 observation types including AGENT/TOOL/EVALUATOR, scores attached via optional FK to trace_id or observation_id. Directly informs Verso's native trace schema. |
| `teardowns/WEIGHTS_AND_BIASES.md` (591 lines) | W&B Models (LevelDB protobuf transaction log, Go `wandb-core` crash-safe writer) + **Weave** (`@weave.op` call-tree capture, `CallStartReq`/`CallEndReq` → ClickHouse REST trace server, auto-patch of OpenAI/Anthropic clients) | High — Weave's `@weave.op` decorator is the closest existing art to Verso's `@tool` annotation pattern; the call-tree/span model is directly comparable. Shows what zero-friction Python instrumentation looks like at the framework level. |
| `teardowns/NEPTUNE.md` (2128 lines) | Neptune.ai experiment tracker: run/series/artifact model, metadata namespace design, versioning | Low — primarily ML experiment tracking, not agent tracing or LLM-specific eval. Useful background but doesn't directly shape Verso decisions. |

---

## RE Targets

### Langfuse

**What it is:** Open-source LLM engineering platform — tracing, eval/scoring, prompt management, datasets. Self-hostable (Postgres + ClickHouse). YC W23. Processes billions of observations/month.

**Why for Verso:** Langfuse has the most carefully designed LLM-native trace schema of any open-source platform and it's fully readable. The schema is directly relevant to what Verso should emit: 10 observation types (GENERATION, SPAN, EVENT, AGENT, TOOL, CHAIN, RETRIEVER, EVALUATOR, EMBEDDING, GUARDRAIL), scores table with FK to trace_id or observation_id, three score sources (ANNOTATION, API, EVAL), three data types (NUMERIC, BOOLEAN, CATEGORICAL). The 2026 "Events table" rewrite (flat immutable wide table, 3× less memory, 20× faster queries) is the architecture Verso's checkpoint serializer should target. The LLM-as-judge eval scheduler (job-based, async, ClickHouse-backed, OTel-passthrough for immutable spans) shows how to wire evals to the durable seam without blocking the agent loop. First-class OTel integration (OTLP gRPC + HTTP) is the integration contract Verso should implement natively.

**What to RE:** (1) The ClickHouse trace+observation schema — exact column names, ReplacingMergeTree dedup logic, `sumMap` aggregation for cost/token rollups, partition pruning windows. (2) The scores attachment model — how `config_id` → `ScoreConfig` → evaluator job fires, the `JobExecution` enrichment path, the async eval scheduler. (3) The new flat "Events" table design (post-2026-01) — why collapsing trace+span into one wide row is better than normalized tables for agent workloads. (4) The OTel ingestion path — what the `OpenTelemetryIngestion` module does to translate generic OTLP spans into Langfuse's typed observation taxonomy.

**Source pointer:** `github.com/langfuse/langfuse` (TypeScript, Apache-2.0). DeepWiki cross-reference at `deepwiki.com/langfuse/langfuse`. ClickHouse blog post: "Langfuse and ClickHouse: A new data stack for modern LLM applications."

**Priority:** P0

---

### Braintrust

**What it is:** Commercial AI eval + observability platform. Closed-source backend, open-source SDKs and autoevals library. Purpose-built Brainstore OLAP database for agent trace workloads.

**Why for Verso:** Braintrust's eval data model (Dataset → Experiment → Scorer → Score, with CI/CD gating on score regressions) is the clearest articulation of "eval==run" semantics that Verso should offer. The `eval()` function that runs a task function over a dataset and attaches scores to an experiment is exactly the pattern Verso's durable seam should enable — a checkpoint-resumed agent run is structurally identical to an eval run. The Brainstore architecture reveals what makes agent trace storage different from generic OLAP: WAL on object storage with one-file-per-request, three-source query merging (unprocessed + processed + compacted), per-customer partitioning (no shared table hot spots), semi-structured data as first-class (no JSON shredding). This is the storage design Verso should recommend to operators. The sandboxed Python scorer execution (the only commercial platform with this) is the eval isolation model Verso should match in its built-in eval runner.

**What to RE:** (1) The open-source `autoevals` library (`github.com/brainlid/autoevals` / `github.com/brainlid/autoevals` — check exact org) — the exact scorer implementations (LLMClassifier, Factuality, ClosedQA, etc.) and how they chain LLM calls to produce 0–1 scores. (2) Brainstore architecture blog — WAL file format, three-source query merge, customer partitioning strategy. (3) The `braintrust-sdk` open-source client — how `Experiment`, `Dataset`, `Score` objects serialize and how CI/CD gating works (exit code, score threshold comparison). (4) The `Loop` AI assistant UX — how it maps natural-language failure descriptions to dataset curation + scorer recommendations (probe via their API if direct source isn't available).

**Source pointer:** Open-source: `github.com/brainlid/autoevals` (JS + Python scorers, MIT). SDK: `github.com/brainlid/braintrust-sdk`. Blog: `braintrust.dev/blog/brainstore-architecture`. Closed — probe production API for eval job schema via error mining.

**Priority:** P0

---

### Arize Phoenix + OpenInference

**What it is:** Open-source AI observability and eval platform (Arize-ai/phoenix, Apache-2.0). OpenInference is the companion OTel semantic convention spec for AI spans (also open-source, Arize-ai/openinference).

**Why for Verso:** Phoenix v16 (May 2026) shipped sandboxed Code Evaluators — composite scoring, embedding-based eval, LLM-jury executed server-side. The OpenInference semantic conventions are the most complete OTel-for-LLMs spec available and Verso should either adopt them or explicitly diverge. The span kind taxonomy is more granular than Langfuse's and directly covers the Verso agent loop: AGENT, CHAIN, LLM, TOOL, RETRIEVER, RERANKER, EMBEDDING, EVALUATOR, GUARDRAIL, PROMPT. The attribute namespacing (`openinference.*`, `llm.*`, `tool.*`, `agent.*`, `graph.node.*`) is what Verso should emit on every span. Phoenix's OTel-native architecture (any OTel collector works) is the integration model Verso should use — emit standard OTLP and let users choose their backend (Phoenix, Langfuse, Honeycomb, Grafana, etc.). The `graph.node.id` + `graph.node.parent_id` attributes in OpenInference are specifically designed for graph-based agents — worth reading to confirm Verso's simpler linear/branching model doesn't need them or to consciously adopt them.

**What to RE:** (1) Full OpenInference semantic conventions spec — every attribute in every namespace, required vs optional, how agent span kinds compose (e.g., an AGENT span wrapping TOOL + LLM children). (2) Phoenix's eval attachment model — how `px.Client().log_evaluations()` attaches scores to specific spans, the `Evaluations` protobuf schema, how evals are stored separately from traces and joined at query time. (3) Phoenix's sandboxed Code Evaluator design (v16) — what sandboxing mechanism is used (subprocess? container? Deno?), how composite scorers chain, how embedding similarity evals work. (4) The `openinference-instrumentation-*` auto-instrumentation packages — how they wrap framework calls to emit typed spans without user code changes (the zero-friction instrumentation model Verso should consider for its own runner).

**Source pointer:** `github.com/Arize-ai/phoenix` (Python, Apache-2.0). `github.com/Arize-ai/openinference` (Python + TS + Java). Spec: `arize-ai.github.io/openinference/spec/semantic_conventions.html`. Phoenix v16 release notes for Code Evaluators.

**Priority:** P0

---

### DeepEval (Confident AI)

**What it is:** Open-source Python eval framework (pytest-native, `github.com/confident-ai/deepeval`, Apache-2.0). Confident AI is the companion SaaS platform. 40+ metrics covering RAG, agents, multi-turn, multimodal.

**Why for Verso:** DeepEval is the most complete open-source implementation of LLM-specific eval metrics — the actual metric internals (G-Eval, DAG metric, PlanQualityMetric, PlanAdherenceMetric, TaskCompletion, ToolCorrectness) show exactly what Verso's built-in eval suite should score. The pytest-native design (each metric is a class with `measure(test_case)` → `score: float`, `reason: str`) is the API pattern Verso should adopt for `@eval` decorators. The `@observe()` decorator + `evals_iterator()` for tracing component-level execution during eval runs is the direct bridge between Verso's `@tool` instrumentation and its eval runner — the same instrumentation path powers both production tracing and offline eval. The `AgentSteps` trace model (captures each tool call, its inputs/outputs, and whether the agent followed its plan) is the canonical eval schema for ReAct-loop agents. DeepTeam (`github.com/confident-ai/deepteam`) is the companion red-team framework — relevant for Verso's adversarial eval capability.

**What to RE:** (1) The metric base class and LLM judge chain — how `G-Eval` fires N LLM calls and aggregates scores, how the verdict prompt is structured, what the `reason` field extraction looks like. (2) The `AgentSteps` / multi-step trace model — exact fields, how `ToolCorrectness` verifies tool call sequences, how `PlanAdherenceMetric` compares the generated plan to execution trace. (3) The `@observe()` decorator internals — how it patches async functions to capture inputs/outputs for both tracing and eval replay. (4) The Confident AI online eval integration — how production traces trigger async metric evaluation, what the polling/push model is, how score results flow back to datasets.

**Source pointer:** `github.com/confident-ai/deepeval` (Python, Apache-2.0). `github.com/confident-ai/deepteam` (Python, Apache-2.0). Docs: `deepeval.com/docs`.

**Priority:** P0

---

### promptfoo

**What it is:** Open-source LLM eval + red-team framework (TypeScript, MIT, `github.com/promptfoo/promptfoo`). YAML-declarative config. CI/CD-first. Used internally at OpenAI and Anthropic.

**Why for Verso:** promptfoo's declarative eval config model (YAML: `prompts × providers × tests × assertions`) is the most mature "eval-as-code" design available and directly shapes what Verso's eval config format should look like. The assertion taxonomy (deterministic: exact, contains, regex, JSON schema; model-graded: llm-rubric, factuality, answer-relevance; code: JavaScript/Python functions) is the complete set Verso needs to ship. The red-team plugin/strategy architecture (50+ attack categories, composable plugins + strategies that generate adversarial test cases, LLM-as-judge grading) gives Verso a ready-made adversarial eval layer. The CI/CD gate model (exit code on score regression, result diffing between runs, GitHub Action) is the exact integration Verso should ship for its own eval runner. Local SQLite storage (Drizzle ORM) + web UI for result inspection is the self-contained dev loop Verso should match.

**What to RE:** (1) The YAML config schema — exact fields, how `prompts × providers × tests` expand into a test matrix, how `defaultTest` and `assert` blocks compose. (2) The assertion pipeline — how each assertion type fires (sync code, async LLM call, or hybrid), how scores are normalized, how failures produce human-readable diffs. (3) The red-team architecture — how plugin modules generate adversarial inputs (cloud generation API vs local), how strategies wrap/modify generated attacks, how the grading model determines pass/fail. (4) The result storage and comparison model — SQLite schema, what a "run" record looks like, how the web UI diffs two runs.

**Source pointer:** `github.com/promptfoo/promptfoo` (TypeScript, MIT). Docs: `promptfoo.dev/docs/red-team/architecture/`.

**Priority:** P1

---

### RAGAS

**What it is:** Open-source RAG + agentic eval framework (Python, Apache-2.0, `github.com/explodinggradients/ragas`). Metric-first; TestsetGenerator for synthetic dataset creation from knowledge graphs.

**Why for Verso:** RAGAS is the reference implementation for retrieval-aware eval metrics — Faithfulness, Answer Relevancy, Context Recall, Context Precision — that any agent framework with tool-based retrieval must support. The `DiscreteMetric` / async `score()` architecture shows how to make metrics composable and LLM-provider-agnostic (any LLM can be the judge). The knowledge-graph-based TestsetGenerator (synthesizes multi-hop questions from document graphs) is directly relevant to Verso's eval dataset generation — agents with memory need multi-hop test cases, not single-turn QA pairs. RAGAS v0.2+ introduced `AgentBenchmark` for evaluating multi-step tool-use traces — this is the bridge between RAG metrics and Verso's ReAct loop eval needs. Integration with Langfuse, Langsmith, and Arize Phoenix as score sinks means RAGAS metrics slot naturally into whatever backend Verso recommends.

**What to RE:** (1) The metric base class (`Metric`, `MetricWithLLM`) — how async `_ascore()` is structured, how the judge chain fires (what prompts, how many LLM calls per metric, how the verdict is extracted). (2) Faithfulness specifically — it makes two LLM calls: statement extraction + NLI-style verification — read the exact prompts. (3) The `TestsetGenerator` — how the knowledge graph is built from documents, what the synthesizer types are (simple, multi-context, reasoning), how diversity is enforced. (4) `AgentBenchmark` / agentic eval features — how tool call traces are structured for evaluation, what metrics apply to agent steps vs final answers.

**Source pointer:** `github.com/explodinggradients/ragas` (Python, Apache-2.0). Docs: `docs.ragas.io`. Paper: arxiv.org/abs/2309.15217.

**Priority:** P1

---

### Comet Opik

**What it is:** Open-source LLM observability + eval platform (Python + TypeScript, Apache-2.0, `github.com/comet-ml/opik`). ClickHouse + MySQL + Redis backend. 12.5k GitHub stars in ~9 months.

**Why for Verso:** Opik's architecture is the most directly replicable self-hosted eval backend for Verso to recommend or ship alongside. The dual-storage design (ClickHouse with ReplacingMergeTree + UUID v7 primary keys for traces; MySQL for ACID-requiring data like feedback definitions and project configs) is the right split for an agent framework backend. The online eval rule engine (Redis Streams for real-time scoring, Flask+Gunicorn Python evaluator service, Redis Queue for async jobs) shows how to wire "score every trace in production" without blocking the agent. The LLM-as-judge online eval pipeline is implemented in Python and is readable. Opik's `@track` decorator (analogous to Weave's `@weave.op`) shows a third implementation of the zero-friction Python instrumentation pattern — comparing Opik, Weave, and DeepEval's `@observe` gives Verso the full design space for its own span emission decorator.

**What to RE:** (1) The ClickHouse trace schema — exact table definition, UUID v7 key ordering, how low-cardinality fields are ordered in the sorting key. (2) The online eval architecture — Redis Streams → evaluator worker → ClickHouse score write flow, how rules are defined (project-level, metric-type, sampling rate), how fault tolerance works (message claiming). (3) The `@track` decorator internals — how it captures async function calls, builds the span tree, and flushes to the backend. (4) The Python evaluator service (Flask+Gunicorn) — how custom metric code is executed, whether sandboxing exists, how results are written back.

**Source pointer:** `github.com/comet-ml/opik` (Python + TypeScript, Apache-2.0). Architecture blog: `comet.com/site/blog/llm-observability-architecture-engineering/`. Docs: `comet.com/docs/opik/self-host/architecture`.

**Priority:** P1

---

### MLflow 3 (GenAI)

**What it is:** Open-source ML platform with full GenAI eval suite added in v3 (Python, Apache-2.0, `github.com/mlflow/mlflow`). `LoggedModel` entity, OTel-based tracing, 50+ built-in scorers, lifecycle-consistent eval from dev to prod.

**Why for Verso:** MLflow 3's `LoggedModel` entity (first-class citizen grouping traces + metrics + runs + prompts under one model version) is the most mature implementation of "model version as the unit of eval comparison" — directly relevant to Verso's checkpoint/durable seam, where each checkpoint could be tagged to a model version. The consistent scorer API (same scorers run in dev, CI, and production) solves the "eval drift" problem that Verso's seam should address — the eval you write during development should be the same one that runs on production traces. MLflow's OTel-based tracing (auto-captures source name, git commit hash, execution type as trace tags) is the metadata model Verso should emit for every agent run. Being fully open-source with no enterprise paywall means it's the safe baseline recommendation for Verso operators.

**What to RE:** (1) The `LoggedModel` entity schema — exact fields, how it links to `Run`, `Trace`, `Prompt`, and eval metrics. (2) The scorer API — how built-in scorers (LLM judges + deterministic) are defined, how custom scorers are registered, how `mlflow.evaluate()` runs a task function over a dataset and records scores. (3) The tracing integration — how `mlflow.tracing` emits OTel spans, what automatic metadata tags are attached, how traces attach to a `LoggedModel` vs a `Run`. (4) The production monitoring path — how the same scorer definitions run async on production traces (if at all — or is this only offline?).

**Source pointer:** `github.com/mlflow/mlflow` (Python, Apache-2.0). MLflow 3 release: `mlflow.org/releases/3/`. Databricks docs: `docs.databricks.com/aws/en/mlflow3/genai`.

**Priority:** P1

---

### OpenLLMetry / Traceloop

**What it is:** Open-source OTel-for-LLMs instrumentation library (Python + TS + Go + Ruby, Apache-2.0, `github.com/traceloop/openllmetry`). Now OTel-GenAI-aligned. 25+ backend exporters.

**Why for Verso:** OpenLLMetry's semantic conventions were recently merged into the official OTel GenAI SIG — meaning they are becoming the IETF-style standard for LLM span attributes. Verso must either adopt these conventions natively or explicitly diverge with documented reasons. OpenLLMetry's auto-instrumentation packages (patch OpenAI, Anthropic, LangChain, CrewAI, etc. at import time) show the zero-friction instrumentation model that Verso's SDK should at minimum be compatible with — if Verso emits standard OTLP with OTel GenAI attributes, OpenLLMetry-instrumented code inside Verso tools will just work. The `@workflow` decorator (marks a function as a named logical workflow for trace grouping) is directly analogous to Verso's `@agent` entry point — worth reading to see how workflow context propagates through nested LLM/tool calls. The comparison between OpenLLMetry (OTel GenAI SIG aligned) and OpenInference (Arize-led, broader span kind taxonomy) is the key fork Verso must decide on.

**What to RE:** (1) The semantic convention attribute mapping — exact `gen_ai.*` attributes emitted per provider (OpenAI, Anthropic), how they map to the OTel GenAI spec vs the older `llm.*` namespace. (2) The auto-instrumentation mechanism — how `TraceloopInstrumentor().instrument()` patches LLM client methods without user code changes, what context propagation looks like across async boundaries. (3) The `@workflow` / `@task` decorator system — how they create parent spans, how context is propagated into nested calls. (4) The OTLP exporter configuration — how to point at Langfuse, Phoenix, Honeycomb, etc. without code changes.

**Source pointer:** `github.com/traceloop/openllmetry` (Python + TS, Apache-2.0). OTel GenAI SIG: `opentelemetry.io/docs/specs/semconv/gen-ai/`.

**Priority:** P1

---

### Galileo (pre-Cisco acquisition)

**What it is:** Commercial LLM eval + guardrails platform, acquired by Cisco May 2026. Luna-2: family of small evaluation SLMs (20+ metrics simultaneously, <200ms). Closed source.

**Why for Verso:** Galileo's Luna-2 architecture (distilled small-model evaluators with metric-specific heads, sub-200ms, fine-tunable on production feedback) is the reference design for "eval at inference speed." This is relevant to Verso's online eval story — running a full LLM-as-judge call per agent trace is too slow and expensive for production; Luna-2-style distilled SLM evaluators are the right alternative. The key architectural question: can Verso recommend or ship a lightweight local eval model that scores traces without a full LLM call? The fact that Galileo deploys offline evals and online guardrails from the same metric definitions (no dev/prod split) is the exact seam-consistency argument Verso should make. Now Cisco-owned, architecture details may become harder to access — RE now while the company still publishes independently.

**What to RE:** Closed source — probe via: (1) Galileo's engineering blog and any pre-acquisition architecture posts about Luna-2 training data, metric head design, distillation approach. (2) Cisco/Splunk integration announcements that may reveal API contracts. (3) Job postings for Luna training team roles (reveal model architecture, training data, evaluation benchmarks). (4) The `galileo-python` SDK on PyPI — reverse-engineer the client to find endpoint schemas, metric names, score response shapes.

**Source pointer:** Closed — `galileo.ai` (now part of Cisco Splunk). PyPI: `pip install galileo`. Pre-acquisition engineering blog at `galileo.ai/blog`.

**Priority:** P2

---

### LangSmith

**What it is:** LangChain's commercial LLM observability + eval platform. Closed-source backend, open-source SDK (`github.com/langchain-ai/langsmith-sdk`). Framework-agnostic since 2025.

**Why for Verso:** LangSmith is the most widely deployed eval platform (millions of traces/day) so its UX patterns have become the industry default that Verso users will compare against. The "annotation queue" model (sample production traces → annotate with domain experts → convert to eval dataset → run evaluators → feed back to annotation queue) is the full flywheel Verso should enable. The evaluator SDK is open-source and shows how to define custom evaluators that run both in CI and online against production traces. The "one-click trace → dataset" promotion is the key UX that Verso's durable seam should make easy — a HITL checkpoint should be promotable to an eval case in one command. Most useful as a UX reference rather than a deep architecture RE, since the backend is closed.

**What to RE:** Open-source SDK at `github.com/langchain-ai/langsmith-sdk` — (1) How run/trace objects are structured in the client (the `RunTree` class, parent/child relationships, attachments). (2) The evaluator interface — `run_evaluator`, how feedback is attached to runs, what the `EvaluationResult` schema looks like. (3) The dataset/example model — how `Dataset` and `Example` objects are structured, how they version. (4) The `@traceable` decorator — context propagation across async boundaries, how it compares to Weave's `@weave.op` and OpenLLMetry's `@workflow`.

**Source pointer:** Open-source SDK: `github.com/langchain-ai/langsmith-sdk` (Python + JS, MIT). Closed backend. Docs: `docs.smith.langchain.com`.

**Priority:** P2

---

## Notes

**Key fork Verso must decide:** OpenInference (Arize, 10 span kinds, `openinference.*` namespace, Phoenix backend) vs OTel GenAI SIG / OpenLLMetry (`gen_ai.*` namespace, any OTel backend). These two are converging but not identical. OpenInference has the richer agent model (AGENT, GUARDRAIL, EVALUATOR span kinds, `graph.node.*` attributes); OTel GenAI has broader tooling support and is the IETF path. Recommendation: emit OTel GenAI as the primary format, add `openinference.*` as an optional enrichment layer via Verso's pluggable edge model.

**The "eval==run" insight (Braintrust, MLflow 3):** The cleanest framing for Verso is that a checkpoint-resumed agent run IS an eval run — same task function, same input, deterministic replay. Verso's durable seam should expose this natively: `verso run --eval dataset.jsonl` should execute the same agent loop as `verso run` but over a dataset and attach scores.

**Scores-to-traces attachment is the key primitive:** Every platform (Langfuse, Laminar, W&B Weave, Opik, LangSmith) converges on the same model: scores are first-class objects with FK to (trace_id, span_id) and a source enum (HUMAN, CODE, LLM). Verso should emit this schema natively from its checkpoint serializer so any of these backends can attach scores without an adapter layer.

**Helicone is in maintenance mode** (acquired by Mintlify March 2026, no new features) — skip as an RE target.

**HoneyHive** is closed-source with no architectural revelations accessible via public RE — skip for now unless a source appears.

**Galileo's P2 rating** reflects that: (a) it's now Cisco-owned and going dark, (b) the Luna-2 distilled SLM concept is the key insight and can be RE'd from the SDK alone without deep access to the platform.

**The three P0 targets (Langfuse, Braintrust, DeepEval) cover the three axes Verso needs:** Langfuse → native trace schema to emit; Braintrust → eval data model and storage architecture for the durable seam; DeepEval → metric implementations and pytest-native API for the built-in eval runner.
