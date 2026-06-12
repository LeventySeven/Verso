# Hippocratic AI: Building the First Safety-First LLM for Healthcare

**Source:** The MAD Podcast with Matt Turck (Aug 23, 2023) + Polaris technical paper (arxiv.org/abs/2403.13313v1)
**Speaker:** Munjal Shah (CEO & Co-founder, Hippocratic AI)
**URL:** https://www.youtube.com/watch?v=2STR07YWFCY
**Duration:** 48 min
**Transcript status:** No verbatim transcript found. Notes synthesized from: (1) Polaris paper (arxiv.org/abs/2403.13313v1) — read in full; (2) Hippocratic AI research page (hippocraticai.com/research/); (3) Medium article by Shah on partnering with healthcare providers; (4) Third-party analysis (envzone.com); (5) Digidai.github.io deep analysis. The MAD Podcast and YouTube video have no public transcript mirror.

---

## What Shah Actually Argues (from readable sources)

### 1. The Scope Bet: Non-Diagnostic Deliberately

Shah's core thesis is that ~$3 trillion in U.S. healthcare spending targets **non-diagnostic, non-drug care**: medication adherence, appointment follow-ups, lab result communication, post-surgical check-ins, nutrition guidance. This is the space where AI can scale safely without touching diagnosis. The constraint is not timidity — it is the verifiable-safety envelope. Shah's framing: "Most people who build LLMs just did not have enough experience in the health care world to solve problems LLMs can solve."

The 2023 bet: a 16.7% critical staffing shortage in U.S. hospitals made "super-staffing" via conversational AI tractable. Hippocratic targets the work currently done by nurses, medical assistants, social workers, and nutritionists — not physicians.

### 2. Constellation Architecture: Supervisory Multi-Model System

The Polaris paper (March 2024) formalizes what Shah was pitching in the 2023 MAD episode as "safety-first." Core architecture:

- **One primary conversational agent** (70B–100B params) drives the patient-facing dialogue — empathetic, natural, multi-turn voice calls
- **Multiple specialist support agents** (50B–100B each, 22 total in Polaris 3.0) run **concurrently**, each watching for domain-specific failures: medication management, lab interpretation, nutrition, privacy/compliance, human escalation triggers, checklist completion, EHR summarization
- **Total parameter count: 4.2T+ across Polaris 3.0**
- Specialist agents emit structured JSON-like field-value pairs (not free text) → deterministic orchestration layer merges them into the primary agent's next prompt
- If the primary model fails or misses a task, the specialist ensures the system continues correctly and safely

The key design decision from the paper: "break down the faculty into medium-size specialist models with consistent high performance" rather than relying on one oversized general model. The argument: competing objectives (fluency, medical accuracy, safety, latency) pull in different directions on a single model; separate specialists optimized per objective outperform the general.

### 3. Safety Philosophy: Bottom-Up, Not Regulatory Top-Down

Shah criticizes top-down regulatory approaches: "Why aren't we using the experts who do the job today — who know the job best — as our way of determining safety?" The model: practicing nurses and physicians evaluate AI outputs, iteratively. The Polaris evaluation recruited 1,100+ licensed nurses and 130+ physicians to assess 307,038 unique calls. This mirrors traditional healthcare triage.

Training data is similarly bottom-up: nurses create initial conversations → trained agents replace nurses in subsequent rounds → nurses review/correct AI outputs → instruction models clean for diversity. The company acquired 1.5 trillion healthcare-specific tokens and partnered with 10 health systems for proprietary data. Shah: "Health care data is very different from other data... Most of the data is below the water line."

### 4. Iterative Co-Training

Unusually, Polaris does not train the primary agent in isolation. It uses **iterative co-training**: primary and support agents are trained together with registered nurses supervising the loops. Four phases: foundation training (clinical documents) → instruction tuning (reasoning tasks) → conversation tuning (simulated nurse-patient dialogues) → agent tuning (specialist coordination) → RLHF on nurse preference feedback.

### 5. Safety Metrics

- Pre-Polaris: ~80% clinical accuracy
- Polaris 1.0: 96.79%
- Polaris 2.0: 98.75%
- Polaris 3.0: 99.38% (validated across 1.85M+ patient calls)
- Severe harm concerns: 0.06% → 0.00% by Polaris 3.0
- LLM outperformed GPT-4 on 105 of 114 healthcare-specific exam benchmarks

### 6. Operational Philosophy

Shah mandates 100% in-person operations: "We're 100% in-person. Our company is literally five days a week." He attributes faster safety responsiveness and clinical feedback loops to shoulder-tap collaboration. The embedded clinical team (3 doctors, 3 nurses) works inside the engineering organization providing continuous RLHF.

---

## Key Verbatim Quotes (from readable sources)

- "First, we're safety first. That's what we're committed to." (Munjal Shah, envzone.com)
- "Why aren't we using the experts who do the job today — who know the job best — as our way of determining safety?" (Shah, multiple sources)
- "We are literally having them work with us in joint development sessions every minute." (Shah on health system co-development)
- "Health care data is very different from other data... Most of the data is below the water line." (Shah on proprietary training data)
- "Most people who build LLMs just did not have enough experience in the health care world to solve problems LLMs can solve." (Shah on the missed opportunity)

*Note: No transcript from the specific MAD Podcast episode (Aug 2023) was found. These quotes come from related written sources by Shah.*

---

## VERSO RELEVANCE

### [NEW-IDEA] — Supervisory multi-agent as safety pattern, not orchestration pattern (§6.2 multi-agent, §6.3 safety)
Hippocratic's constellation is not about task decomposition or efficiency — the specialists are there to **catch primary model failures in real time**. Each specialist is a redundant safety checker on a specific dimension (medication, escalation, compliance). This is structurally different from Verso's current sub-agent framing (failure-quarantine + scheduler-offload). Verso could offer a "safety harness" pattern: a lightweight supervisor agent that watches the primary agent's outputs and vetoes or flags based on a domain-specific rubric. This is not a graph; it is a concurrent monitor that runs alongside the loop.
- Verdict: worth adding to §6.3 as a named pattern: "parallel safety-watcher" — one-flag promotion to enable it, no loop rewrites.

### [SHARPENS §6.2] — Structured outputs as the interface between specialist and primary
The Polaris paper's strongest engineering insight: specialist agents emit **JSON-like field-value pairs, not free-form text**. The primary agent cannot be contaminated by a specialist's prose style or hallucinated reasoning — only structured signals reach it. This sharpens Verso's existing sub-agent-as-isolate idea: the interface contract between agents should be typed, not free text. Verso's typed `ContextBundle` / named `StopReason` are already moving in this direction, but the Polaris framing makes the anti-prose case crisply.
- Verdict: confirms Verso's typed-boundary direction; adds "verifiable control flows" as explicit justification language.

### [NEW-IDEA] — Scope-as-safety-strategy: limit the task space to make the safety envelope verifiable (§6.3 safety, §12 positioning)
Hippocratic's deepest insight is that **choosing which problems NOT to solve** (diagnosis) is a safety strategy, not a product limitation. The non-diagnostic constraint is what makes 99.38% clinical accuracy achievable and verifiable. Verso equivalent: the harness should let builders declare an explicit scope boundary (what this agent will and will not attempt), and the eval framework should include boundary-adherence as a first-class metric. Currently Verso evals are output-quality focused; scope-compliance is a separate dimension.
- Verdict: new eval category to spec. Low implementation cost; high safety credibility.

### [CONFIRMS §5.5 evals] — Real-world clinical evaluation at scale (1.85M calls, 6,234 clinicians) shows benchmark-only eval is insufficient
The RWE-LLM framework explicitly argues that "traditional LLM benchmarking approaches provide very limited output coverage" for healthcare safety. Verso's embedded in-process evals are right to target real-run data over synthetic benchmarks. Hippocratic's judge-panel equivalent is the 6,234 licensed nurse/physician evaluator pool — domain-specific evaluators, not general LLM judges.
- Verdict: confirms Verso's judge-panel pattern; adds argument that evaluator domain specificity matters as much as evaluator count.
