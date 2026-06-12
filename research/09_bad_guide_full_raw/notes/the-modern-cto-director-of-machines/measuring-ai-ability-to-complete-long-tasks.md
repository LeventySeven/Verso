# Measuring AI Ability to Complete Long Software Tasks — METR (Kwa, West, Becker et al.)
**Source:** https://arxiv.org/abs/2503.14499 (NeurIPS 2025, arXiv:2503.14499v3)
**Authors:** Thomas Kwa, Ben West, Joel Becker, et al. (25 researchers, METR)
**Status:** read_partial (HTML abstract page + HTML full paper fetched; PDF binary not decodable; all key numbers and methodology captured)
**Themes:** evals, strategy, loop_harness, model

---

## Faithful Digest

### Core Metric: 50% Task-Completion Time Horizon
The paper introduces a single, human-calibrated metric: **the 50%-task-completion time horizon** — the amount of time a human expert typically takes to complete tasks that a given AI model can complete with 50% success rate.

The logistic regression model underlying this:
`p_success = σ((log h_agent - log t_task) · β_agent)`
where `h_agent` is the model's 50% time horizon and `t_task` is the geometric mean of human completion time for that task.

This makes the metric intuitive: if a model has a 50-minute time horizon, it can do in 50% of attempts what a skilled human does in 50 minutes.

### Key Numbers (the ones Verso bets on)
- **GPT-2 (2019):** ~2 seconds time horizon
- **Claude 3.7 Sonnet:** ~50 minutes time horizon
- **o3:** ~110 minutes time horizon
- **Doubling time (2019–2025):** approximately every **207 days** (95% CI: 166–240 days)
- **Acceleration signal:** o3 is significantly above the long-run trend line (p=0.006) — possible acceleration since 2024
- **80% success horizon:** doubling time of ~204 days, but horizons are 4–6x *shorter* than 50% horizon — reliability lags capability by substantial margin

### Task Suite: 170 Total Tasks
1. **HCAST:** 97 tasks ranging from 1 minute to 30 hours human completion time
2. **RE-Bench:** 7 ML research tasks (8 hours each)
3. **SWAA:** 66 atomic tasks (1–30 seconds)

Human baselines: over 800 baselines totaling 2,529 hours, from skilled professionals averaging ~5 years experience. Success rate shows strong negative correlation with task length (R²≈0.83).

### Drivers of Improvement (Qualitative)
- Improved tool use capabilities
- Better error recovery and adaptation
- Stronger logical reasoning and code generation
- Increased robustness to mistakes

**Persistent limitation:** Models struggle with unstructured "messy" environments — tasks lacking clear feedback or requiring proactive information-seeking. Messiness degrades performance systematically but doesn't change the overall trend.

### External Validity
- **SWE-bench Verified replication:** Exponential trend confirmed, possibly shorter doubling time
- **Internal PR tasks:** Found 5–18x variation in human completion time based on expertise level — the "reference human" definition substantially affects difficulty
- **Messiness analysis:** 16 "messiness" factors tested; performance degrades but trend shape is preserved across high/low messiness subsets

### Extrapolation (with explicit uncertainty)
Naive extrapolation: AI achieving >1-month (167 work hours) time horizon somewhere between **mid-2028 and mid-2031**.

The authors explicitly flag: "substantial uncertainty due to external validity concerns and potential trend changes." This is not a confident prediction — it's an extrapolation from an exponential that may not hold.

### Limitations the Authors Acknowledge
- Task distribution may not represent average software engineering work
- Reference human population significantly affects difficulty perception  
- Cannot reliably measure 95%+ success rates with current dataset
- Messier real-world tasks may show different trends
- "The doubling time confidence interval is wide" — 166 to 240 days

---

## VERSO RELEVANCE

### [CONFIRMS §1 — The Bet] The primary citation for the task-horizon curve is solid
The METR paper is the quantitative backbone of Verso's "build for 18 months out" bet. The 207-day doubling time (95% CI 166–240 days) means:
- Conservative end: horizon doubles every 240 days (~8 months)
- Central estimate: doubles every ~7 months
- Accelerated scenario: o3 is already significantly above trend (p=0.006)

At the central estimate, from Claude 3.7's ~50-minute horizon: 18 months = ~2.6 doublings → expected horizon of ~300–400 minutes (~5–7 hours). That means frameworks designed for today's 50-minute tasks will be substantially wrong by the time Verso ships a mature v1.

**Verdict:** confirm — Verso's §1 bet is directly supported. The specific doubling-time CI (166–240 days) should be cited precisely.

### [SHARPENS §1 — The Bet] The 80% horizon gap is a strategic opportunity, not a warning
The 80% success horizon is 4–6x shorter than the 50% horizon, with the same ~204-day doubling time. This means reliability *lags* raw capability by a factor of 4–6x in task length. For Verso's durable runtime (checkpoint/resume, error recovery): as raw capability grows, the gap between "what models can do sometimes" and "what you can rely on them to do" remains large. The harness that closes this gap (retry, checkpoint, structured error recovery) becomes *more* valuable as raw capability scales, not less. The 80% horizon catches up to the 50% horizon only as that infrastructure matures.

**Verdict:** sharpen — §6.1 durable runtime section should use this gap explicitly: "the 80% reliability horizon lags 4–6x behind the 50% capability horizon; durable runtime is the mechanism that closes this gap."

### [NEW-IDEA §5.5 — Evals] METR's logistic success-probability model as Verso eval primitive
The formula `p_success = σ((log h_agent - log t_task) · β_agent)` gives a model-calibrated probability for any task of a given human-estimated completion time. Verso's `define_outcome` / judge-panel eval infrastructure could expose this as a calibration primitive: given a task's estimated human completion time and the model in use, compute expected P(success) as a baseline for judging whether a failure represents a real regression or just expected difficulty. This would make Verso evals automatically model-aware without requiring users to manually calibrate expectations per model.

**Verdict:** lock-interface-defer — powerful but requires METR-style calibration data per model; lock the interface (task_duration_estimate as optional eval parameter) and defer the calibration infrastructure.

### [SHARPENS §6.1 — Durable Runtime] "Messy environments" as the core harness problem
The paper's named limitation: "Models struggle with unstructured 'messy' environments lacking clear feedback or requiring proactive information-seeking." This is precisely where checkpointing and structured error recovery earn their cost. "Messy" tasks — the real-world ones — are where the reliability gap is widest. Verso's durable runtime (checkpoint/resume, human-in-the-loop) is specifically designed for messy environments. The paper provides quantitative evidence that messiness degrades performance systematically; the implication is that harnesses controlling the feedback structure (which is what Verso's context-engineering layer does) have disproportionate impact on messy-environment performance.

**Verdict:** sharpen — §6.1 and §5.2 context-engineering sections should explicitly frame messy environment taming as the primary durable runtime motivation.

### [SHARPENS §1 — The Bet] Wide CI means Verso needs architecture that's correct across the range
The 95% CI (166–240 days doubling) is wide enough that planning around only the central estimate is wrong. Verso's architectural invariants should hold whether the doubling slows to 240 days or accelerates further beyond o3's current above-trend position. The "tactical<->durable seam with one flag" architecture is specifically robust across this range: if capability accelerates, agents need durable infrastructure sooner (the seam matters more); if it slows, the tactical default remains correct (the seam costs nothing). The seam is a hedge across the CI range.

**Verdict:** confirm — already captured, but citing the CI explicitly in §1 makes the robustness argument stronger.

### [NEW-IDEA §5.1 — Loop] Task success as logistic function of log(task_length): loop budget implications
The R²≈0.83 correlation between task length and success rate implies that the loop's token/step budget is a first-class determinant of success probability. A loop that can't adaptively extend its budget for longer tasks will systematically underperform the capability curve. Verso's loop should expose a `max_steps` and `max_time_budget` as typed parameters — not hardcoded defaults — and the eval infrastructure should model expected success probability as a function of these budgets per model. Currently Verso's loop is fixed-step; this suggests the loop's step budget should be a runtime-variable parameter tied to the task's estimated complexity.

**Verdict:** lock-interface-defer — expose `step_budget` as typed parameter on RunContext; defer adaptive budget inference to eval layer.
