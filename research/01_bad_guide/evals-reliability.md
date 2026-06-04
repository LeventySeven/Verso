# Evals + Task-Horizon Reliability

## Your AI Product Needs Evals (Hamel Husain) — https://hamel.dev/blog/posts/evals/ — [read]

### Core Thesis

- "Unsuccessful products almost always share a common root cause: a failure to create robust evaluation systems."
- "Like software engineering, success with AI hinges on how fast you can iterate." Evals ARE the iteration loop — without them you're doing vibe-checks.
- "Iterating Quickly == Success" — evals compress the feedback loop from days (manual inspection) to minutes (CI), which compounds over the product lifecycle.
- "If you streamline your evaluation process, all other activities become easy" — prompt engineering, fine-tuning, and debugging all draw on the same infra.
- "Many people focus exclusively on behavior change [prompt tweaks], which prevents them from improving their LLM products beyond a demo." The demo-to-product gap is fundamentally an eval gap.

### The Plateau Anti-Pattern (Lucy Case Study)

Lucy's plateau: a real estate AI assistant that got stuck after initial gains. Symptoms form a diagnostic cluster:

1. Fixing one failure created others — classic whack-a-mole; no regression coverage.
2. Limited visibility beyond vibe-checks — no quantified signal, only subjective impression.
3. Prompts ballooned into "long and unwieldy forms" as the team kept patching edge cases without measuring.

The fix was not a better model or bigger prompt — it was building the evaluation system that should have existed from day one.

### Three-Level Hierarchy

**Level 1 — Unit Tests (cheapest, run on every commit)**

- Break LLM scope into features × scenarios matrix.
- Write deterministic assertions — these go beyond traditional pytest; they're also reusable for data cleaning and automatic retries during inference.
- Fast execution is non-negotiable: Level 1 must give sub-minute CI feedback.
- Example (Lucy — Listing Finder feature):
  - Scenario 1: Single match → assert `len(listing_array) == 1`
  - Scenario 2: Multiple matches → assert `len(listing_array) > 1`
  - Scenario 3: No matches → assert `len(listing_array) == 0`
- Example (UUID detection): strip `{{double_brace}}` content, apply regex `/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/ig`, assert `matches.length == 0`.
- Test case generation: use an LLM to synthetically generate diverse inputs — Rechat generated 50 contact-creation instructions each paired with a retrieval instruction, as JSON array of paired strings `[["instr1", "instr2"], ...]`.
- Rechat operates "hundreds of these unit tests"; pass rate is a product decision, not a fixed 100% target.
- Continuously update tests from failures observed during human eval and debugging. Tests must grow with product knowledge.
- Orchestration: GitHub Actions / GitLab Pipelines for CI execution; separate metrics tracking (Rechat uses Metabase dashboard to track pass rates over time).

**Level 2 — Human & Model Evaluation (moderate cadence, with debugging)**

_Trace logging:_
- A trace is a logical grouping of logs across a session or request chain.
- Required capabilities: search, filter, human-readable rendering, interactive playground for prompt iteration.
- Author's preferred tool: LangSmith (does not require LangChain).
- Alternatives: Arize, Human Loop, OpenLLMetry, HoneyHive.
- LangChain auto-logs to LangSmith.

_Custom data viewing tools:_
- "Remove ALL friction from the process of looking at data" — stated twice for emphasis, i.e., it's the core design goal.
- Build domain-specific viewers that expose: feature/scenario classification per trace, synthetic-vs-real flag, cross-linked CRM/application data, embedded interaction views.
- Author built Rechat's viewer in Shiny for Python in less than one day.
- Lilac: semantic AI search/filter to find similar data across a large trace corpus.
- "You are doing it wrong if you aren't looking at lots of data."

_Labeling:_
- Start with binary good/bad — granular scores are "more onerous to manage" and rarely improve decisions.
- Advanced options: active learning, consensus voting.
- Minimum scope: ALL test case traces + representative user-generated traces; sampling strategy evolves over time.
- "You can never stop looking at data — no free lunch exists."

_LLM-based automated evaluation:_
- Pattern: (1) model generates response, (2) a more powerful LLM writes a critique, (3) critique model assigns binary label, (4) human evaluator independently labels the same examples, (5) iterate critique prompt to align human and model.
- Low-tech iteration spreadsheet: columns `model_response`, `model_critique`, `model_outcome`, `human_critique`, `human_outcome`, `human_desired_response`. 25–50 examples per iteration cycle. Track alignment score across attempts.
- Model selection: "Use the most powerful model you can afford." Reasoning capabilities required; can afford slower/more expensive than production inference.
- "Model-based evaluation is a meta-problem — must maintain a mini-evaluation system to track its quality."
- Critiques serve dual purpose: they also curate synthetic data for fine-tuning (same data, two uses).
- Metrics warning: do NOT use raw agreement when classes are imbalanced (~50/50); measure precision and recall separately.
- Post-launch: continue periodic alignment exercises — eval quality degrades as distributions shift.

**Level 3 — A/B Testing (post-significant product change only)**

- Cost: Level 3 > Level 2 > Level 1.
- Only appropriate for more mature products with confidence in the baseline.
- "Not too different from standard A/B testing practices."
- Reference: Eppo blog.

### Fine-Tuning as a Downstream Eval Consumer

- "99% of labor involved with fine-tuning is assembling high-quality data."
- Fine-tuning excels at: syntax, style, rules. RAG excels at: context, up-to-date facts.
- Data curation pipeline: (1) generate synthetic data with LLM prompts (same generation method as test case gen), (2) filter via Level 1 assertions, (3) filter via Level 2 critique model, (4) curate via human eval tools on traces, (5) output fine-tuning dataset.
- Eval infrastructure IS fine-tuning data pipeline — they're the same system.

### Key Design Principles

- "Don't buy fancy LLM tools. Use what you have first."
- "Don't rely on generic evaluation frameworks. Create an evaluation system specific to your problem."
- LLMs are useful for eval infrastructure itself: test case generation, assertion brainstorming, synthetic data generation, critique/labeling. The model helps build its own eval harness.
- Reuse eval infra for debugging: searchable trace DB + error-flagging + log navigation → root-cause analysis (RAG failure vs. code bug vs. model quality).
- "You don't need to wait for production data to test your system" — synthetic generation from day one.
- The eval-and-curation loop is the CENTER of the system, not a bolt-on. Prompt engineering, fine-tuning, debugging, and code changes all orbit it.

---

## Measuring AI Ability to Complete Long Tasks (arXiv 2503.14499) — https://arxiv.org/abs/2503.14499 — [read]

### Core Metric: 50%-Task-Completion Time Horizon

- **Definition**: The time that humans with relevant expertise typically need to complete a task that AI models solve at exactly 50% success rate.
- **Operationalization**: Logistic regression fitting agent success probability against log-transformed human baseline times:
  `p_success(agent, task) = σ((log h_agent − log t_task) · β_agent)`
  where `t_task` = geometric mean of successful human baseline times; `h_agent` = the 50% horizon parameter (what we measure); `β_agent` = learned slope.
- 50% threshold mirrors Item Response Theory conventions from human psychometrics.
- 80% horizon variant provided for robustness (doubling time: 204 days, similar; but 80% horizons are 4–6x shorter than 50% horizons — models that sometimes complete hard tasks still fail reliably at moderate length).

### Task Suite (170 tasks total)

| Benchmark | Count | Duration Range | Domain |
|-----------|-------|---------------|--------|
| HCAST | 97 | 1 min – 30 hours | Software tasks |
| RE-Bench | 7 | Fixed 8 hours | ML research engineering |
| SWAA (Software Atomic Actions) | 66 | 1–30 seconds | Single-step developer actions |
| GAIA + adversarial robustness | 6 | — | Mixed |

Example task spectrum by human completion time:
- 3 seconds: shell script identification (multiple choice)
- 1 minute: Wikipedia research and factual lookup
- 9 minutes: molecular dynamics bug detection
- 56 minutes: JSON data transformation script
- 8 hours: CUDA kernel optimization for backtesting

### Human Baselines

- 800+ baselines, 2,529 total hours logged.
- 558 from HCAST/RE-Bench (286 successful); 249 from SWAA (236 successful).
- 148/169 tasks have real human baselines; 21 rely on researcher estimates.
- Participants: skilled professionals (software engineering, ML, cybersecurity), majority from top-100 universities, ~5 years average relevant experience.
- Task-specific success threshold = human target score or average of 7–9 hour runs (RE-Bench).
- Internal validity check: contractor times were 5–18x longer than repo maintainer times; AI performance was consistent with contractor baselines, not maintainer estimates — correctly capturing task difficulty from a capable-but-unfamiliar baseline.

### Primary Finding: ~207-Day Doubling Rate

- **Doubling time**: 207 days (95% CI: 166–240 days, ±19%). Trend holds since 2019.
- **Model trajectory** (representative points):
  - GPT-2 (2019): ~2-second time horizon
  - Claude 3.7 Sonnet / o3 (2025): ~110-minute time horizon
- o3 lies statistically above the long-run trend line (p=0.006), suggesting potential acceleration.
- 2023–2025 growth rate approximately 20% faster than the 2019–2025 average.
- Success rate vs. task length: `y = −0.07x + 0.66, R² ≈ 0.83` (linear on minutes); exponential fit R² ≈ 0.80 on log-transformed duration — strong systematic relationship between task length and failure probability.

### What Drives Capability Growth

Qualitative analysis based on 31 failed GPT-4 1106 runs and 32 failed o1 runs:

**Progress factors** (what improved between GPT-4 → o1/Claude 3.7):
- Tool use capabilities (described as "markedly greater")
- Mistake adaptation — correcting course rather than repeating failed actions
- Logical reasoning and code generation

**Persistent failure modes**:
- *o1*: premature abandonment (16/32), incorrect reasoning (7/32), poor planning/tool choice (6/32), repeating failed actions (2/32)
- *GPT-4 1106*: repeating failed actions (12/31), premature abandonment (8/31), reasoning errors (6/31), poor planning (4/31)

**Characterization of hard cases**: "AI agents still seem to struggle in intuitively 'messier' environments — specifically, environments without clear feedback loops, or where the agent needs to proactively seek out relevant information."

### Reliability Gap: 80% vs. 50% Horizons

- "Even models that sometimes succeed on difficult and diverse tasks cannot reliably perform tasks of moderate length."
- 80% horizons are 4–6x shorter than 50% horizons — meaning the top of the capability range (succeeds sometimes) is far ahead of the reliability range (succeeds consistently).
- This reliability gap is the defining quality problem for agentic systems: occasional success is not production-ready.

### Extrapolation

- **One-month (167 work hours) task horizon**: projected for mid-2028 to mid-2031 at current doubling rate.
- **5-year claim**: "Within 5 years, AI systems will be capable of automating many software tasks that currently take humans a month."
- Author caveat: "extrapolation is affected by both external validity concerns and future changes in the trend."
- SWE-bench Verified replication confirms exponential trend holds on independent benchmark (slightly shorter doubling time there, attributed to difficulty annotation methodology).

### Methodological Robustness Checks

- Alternative curve fits, task weighting variations, WLS vs. OLS, continuous vs. binary scoring — all produce consistent doubling times (Appendix H).
- Inverse-square-root task weighting to reduce influence of large task families (HCAST).
- "Messiness" factor analysis (16 factors: resource constraints, novelty, dynamic environments, etc.): models perform worse on higher-messiness tasks controlling for length, but performance trends are similar across subsets — no evidence of a plateau specific to messy tasks.
- Error structure note: individual model errors are correlated (task difficulty affects all models similarly); greater confidence in the slope than in individual horizon values.

### Key Limitation

Task distribution may not "perfectly represent the average segment of intellectual labor by researchers and software engineers." "Individual benchmarks saturate increasingly quickly" and there's no general intuitive/quantitative way to compare benchmarks. The 170-task suite is the best available but is acknowledged as an approximation.

---

## → Verso Implications

**1. Evals must be a first-class primitive in the Verso API, not a documentation section.**

Hamel's central claim is that eval infrastructure IS the product development loop — prompt engineering, fine-tuning, debugging, and iteration all depend on it. If Verso ships without native eval support, every Verso user will either bolt on LangSmith/custom tooling (friction) or skip evals entirely (plateau). Verso should expose an `Eval` construct as part of the core API alongside `Agent`, `Tool`, and `Memory` — not in a separate library.

**2. Three-tier eval hierarchy maps directly to Verso's execution contexts.**

Level 1 (deterministic assertions, every commit) → Verso's `eval.unit()` that runs in CI with no external calls, asserting on output structure, field presence, enum membership.
Level 2 (LLM judge + human review, periodic) → Verso's `eval.judge()` that wraps a critique model, stores results in a trace store, surfaces a review UI.
Level 3 (A/B, post-ship) → Verso's `eval.experiment()` that A/B routes traffic and reports statistical significance.
This hierarchy should be explicit in Verso's mental model — users need to know WHICH level to reach for, not just that "evals exist."

**3. Trace logging must be native, not a plugin.**

Hamel lists LangSmith, Arize, HoneyHive etc. as interchangeable — the standard is "searchable, filterable, interactive playground." Verso should ship a built-in trace store that meets this bar with zero configuration. Optional forwarding to LangSmith/Arize via adapter. The default should be "traces just exist" — not "add 10 lines of SDK setup."

**4. The eval data model must expose feature × scenario tagging.**

The Lucy pattern — break the LLM scope into features × scenarios, write one assertion per cell — is the practical unit of eval coverage. Verso's eval construct should accept `feature` and `scenario` metadata on test cases, enabling filtering ("show me all failures in the listing-finder / no-match scenario") in the built-in trace UI. This is what turns a generic test runner into a debugging tool.

**5. Synthetic test-case generation should be a first-class workflow, not a footnote.**

"You don't need to wait for production data to test your system." Rechat generated 50+ synthetic test cases per feature using an LLM with a single generation prompt. Verso should include a `eval.generate(prompt, n)` helper that invokes the user's configured LLM to produce synthetic test case inputs, making the eval corpus self-bootstrapping from day one.

**6. LLM-judge alignment workflow must be native because it IS the ongoing quality signal.**

Hamel's spreadsheet method (25–50 examples, `model_outcome` vs `human_outcome`, iterate critique prompt) is the core of Level 2. Verso should provide a structured alignment workflow: given a judge prompt, sample N traces, expose a side-by-side review UI, compute precision/recall split (not raw agreement), and emit a calibration score. This is the feedback loop that keeps automated evals trustworthy over time.

**7. The task-horizon paper defines Verso's reliability SLA target.**

The 80%/50% horizon gap is the most important finding for Verso's design: models that sometimes succeed on long tasks still fail reliably at moderate lengths. "Even models that sometimes succeed on difficult tasks cannot reliably perform tasks of moderate length." Verso's eval layer must measure RELIABILITY — not just peak success — at the user's target task horizon. Verso should surface both a `p50_horizon` (capability ceiling) and a `p80_horizon` (production-reliability floor) for any agent under eval, so teams can see whether they're in the "sometimes works" zone or the "ships to prod" zone.

**8. Persistent failure modes (premature abandonment, repeated failed actions) are Verso loop design problems, not just eval problems.**

The paper's breakdown: o1's #1 failure mode is premature abandonment (16/32 failures). GPT-4's #1 failure mode is repeating failed actions (12/31). These are ReAct loop pathologies. Verso's agent loop should have built-in circuit-breakers: max-repeated-action detection (detect if the same tool call with similar args has failed N times → surface to HITL or terminate), and abandonment detection (if the model emits a "cannot proceed" without hitting a tool error → flag for eval). These behaviors should be observable through Verso's eval layer, not require custom monitoring.

**9. "Messy environments without clear feedback loops" is the key reliability bottleneck — Verso must make feedback explicit.**

The paper's characterization of hard tasks: "environments without clear feedback loops, or where the agent needs to proactively seek out relevant information." Verso's tool design guidance should push users toward tools that return explicit success/failure signals (not ambiguous outputs), and Verso's eval harness should measure agent behavior in low-feedback conditions specifically — flagging agents that fail to probe for missing information versus those that correctly handle ambiguity.

**10. Evals-as-infrastructure unlocks fine-tuning without extra work.**

Hamel: "99% of fine-tuning labor is assembling high-quality data" — and the eval pipeline produces it. Verso's eval construct should export labelled trace pairs (input, expected_output, actual_output, judge_label) in a fine-tuning-ready format (JSONL with system/user/assistant turns) so that an eval run doubles as a data collection run. No separate data pipeline needed.

**11. "Don't use generic eval frameworks" is a market positioning signal for Verso.**

Hamel explicitly warns against generic frameworks. Verso's answer: domain-specific eval primitives that are ALSO generic enough to cover any task. The `feature` × `scenario` tagging system, plus the LLM judge alignment workflow, plus the reliability-horizon metric — these are specific enough to be useful, generic enough to apply across domains. This is Verso's differentiation from LangSmith (observation-only) and from raw pytest (no LLM-native primitives).

**12. The 207-day doubling rate sets the pace for Verso's capability roadmap.**

Task horizons double every 7 months. Features that are eval-hard today (long multi-step tasks, messy environments) will be tractable by 2027. Verso should be designed to benefit from this: as model capability grows, Verso's eval layer should surface the tasks that just crossed the reliability threshold (p80 horizon improved) without requiring users to re-architect. Evals-as-first-class-primitive means the reliability floor measurement is always running; Verso surfaces when the bar has moved.
