# Context Engineering: Lessons from Scaling CoCounsel — Jake Heller

**Source**: https://www.youtube.com/watch?v=sLFv3RSj_d8
**Speaker**: Jake Heller, co-founder Casetext / Head of Product CoCounsel (Thomson Reuters)
**Format**: YC Root Access talk (~20m, "floor 300" importance rating)
**Status**: read_partial — no standalone transcript found for this exact video. Content reconstructed from two sources: (1) the YC Root Access transcript file at /Users/seventyleven/Desktop/Verso/research/02_core/transcripts-yc-rootaccess.md, which contains dense extraction from Jake Heller's Root Access appearance (August 25, 2025) — same speaker, same event series; and (2) supplementary material from startuphub.ai covering Heller's overlapping YC talks on CoCounsel lessons. The guide-note framing ("define the experience before the prompts") was not found verbatim in available sources — that specific phrasing is from the task brief, not a confirmed Heller quote.

---

## What Heller Actually Argues

### The Core Design Principle: Model Expert Workflow First

Heller's foundational question before writing any prompt or picking any architecture: "How would the world's best human attack this problem?" That answer becomes version 0 of the architecture — not a chatbot, not an agent loop, but a faithful model of expert human workflow.

CoCounsel's legal research pipeline, reverse-engineered from expert lawyer workflow:
1. **Clarify the question** — jurisdiction, angle, scope (discrete separate step, not folded into search)
2. **Formulate 20-50 search queries** across different terms and angles
3. **Execute queries**
4. **Read each result page** for relevance and notes
5. **Compile final answer**

Each of these steps is implemented as a discrete micro-task with its own prompt, its own eval suite, and — at Thomson Reuters scale — its own RF-tuned model.

### The Linear vs. Agentic Decision Rule

Heller's rule: "Decide per-task whether the best human would do it linearly (implement as sequential functions) or agentically (needs loop-back if results aren't working). Never default to agentic."

The cost of defaulting to agentic: unpredictable failure modes, debugging complexity, and difficulty establishing the reliability needed for professional users. If the best human does it linearly, a sequential pipeline is more debuggable, testable, and reliable.

This is not anti-agentic — it's anti-agentic-by-default. The ReAct loop is reserved for steps where the best human would genuinely iterate (e.g., "results aren't working, reformulate queries").

### Context Engineering as the Demo-to-Product Gap

The gap between a demo that works and a product professionals trust is entirely a context architecture problem. Heller's grounding instruction (verbatim): "Don't answer based on any of your previously existing knowledge, just based on what I'm giving you right here. If this thing says the sky is purple, the sky is damn purple."

This instruction does two things:
1. Prevents hallucination by anchoring the model to retrieved text
2. Makes retrieval failures visible — if the answer is wrong while the model is grounded, it's a retrieval problem, not a prompt problem. Separates two failure modes that are otherwise confounded.

The implication: context architecture discipline (what goes in, in what order, with what grounding instruction) is the engineering work. Prompt engineering is secondary.

### Eval Discipline: The 999/1000 Rule

Heller's eval progression: 10 → 50 → 100 → 1,000 test cases per micro-step.
Release condition: 999/1,000 passing, and the one remaining case is "kind of debatable."

Observation: "At 6/10 passing most teams stop and conclude 'AI is stupid' — keep going."

Test case sourcing requirement: the 1,000-case suite must come from actual users, not developer imagination. Method: run a small beta, tell customers it will be bad, ask for every failure → each reported failure becomes a test case.

Scale: at Thomson Reuters (CoCounsel at scale), hundreds to thousands of prompts per product; each micro-step has its own eval suite, its own prompt, and its own RF-tuned model.

### Single-Token Output Trick for Classification

For classification steps in high-volume pipelines: format the prompt so the answer token comes first. Use stop words or `max_tokens=1` to cut output after the first token. Result: "the model 'thinks' it's about to give a full explanation → deliberates more → single token carries that deliberation." Cited latency reduction: 200× for classification steps.

This is a concrete test-time compute efficiency technique: more deliberation with less output, not more.

### Reinforcement Fine-Tuning (RF-tuning) vs. Supervised Fine-Tuning

Heller's finding: RF-tuning requires only 50-100 examples + an objective quality judge function. Gains "go a really long way" compared to supervised fine-tuning, which needs thousands of examples.

Qualification: "the hardest part is creating the objective quality judge." The judge function is the real engineering work — a function that can evaluate output quality for a specific micro-task without human review per case.

### Tool Reliability: Eval Tools Cited

Heller explicitly names tools used for evals: Prompt Fu (free, open source, CLI) and Vellum (commercial).

### Building Trust in Sensitive Domains

Customers accept human imperfections but distrust unpredictable AI. Winning strategies:
- Head-to-head performance comparisons
- Pilot programs demonstrating reliability
- Transparent studies and data

The product is not just the software: "support, training, thoughtful onboarding, and continuous engagement" are part of the reliability package.

### The "Undercover Agent" Product Design Method

Before writing a single prompt: "founders must become 'undercover agents,' meticulously documenting professional workflows." Every step of an expert's workflow translates either to an LLM prompt (a step requiring judgment) or a discrete software component (a step that is deterministic). The documentation phase is the product design phase.

---

## Verbatim Quotes (from YC Root Access transcript and sourced blog summaries)

- "How would the world's best human attack this problem?" [design principle, verbatim from Root Access transcript]
- "Don't answer based on any of your previously existing knowledge, just based on what I'm giving you right here. If this thing says the sky is purple, the sky is damn purple." [grounding instruction, verbatim from Root Access transcript]
- "Never default to agentic — if best human would do it linearly, implement linearly." [paraphrase, Root Access transcript]
- "At 6/10 passing most teams stop — keep going." [verbatim, Root Access transcript]
- "A different model for every single prompt" [on CoCounsel's per-micro-step model routing, verbatim, Root Access transcript]
- "Gemini 2.5 Flash — beautiful model, cheap as [hell]. If it works to your level of satisfaction, use that. Don't use 2.5 Pro." [verbatim, Root Access transcript]
- "The hardest part is creating the objective quality judge." [on RF-tuning, verbatim, Root Access transcript]
- "The most important thing you could do for marketing and sales is to build a fucking amazing product." [verbatim, startuphub.ai source]

---

## VERSO RELEVANCE

### [CONFIRMS §5.5 evals] 999/1000 at micro-step granularity is the evals gold standard

Heller's eval discipline confirms Verso's evals-first design at the right granularity: per micro-step (per tool, per pipeline stage), not per product. The 10→50→100→1,000 progression with real-user-sourced inputs is the target pattern for Verso's built-in eval harness. The "keep going past 6/10" observation is the behavioral insight that distinguishes serious practitioners from demos.

**Verdict**: Confirms evals design at the right level of specificity. No overkill.

### [SHARPENS §4 seam] Linear-vs-agentic as the first seam decision, not agentic by default

Heller's rule ("if the best human does it linearly, implement it linearly") sharpens Verso's tactical↔durable seam design. The seam is not just tactical (ephemeral) vs. durable (checkpointed) — it's also linear (pipeline, sequential functions) vs. agentic (loop-back on failure). Verso should make this three-way choice explicit at configuration time: `pipeline` (linear, no loop), `agent` (ReAct loop), `durable_agent` (checkpointed + HITL). The framework should not default to the agent path.

**Verdict**: Sharpens the seam design with a concrete decision rule.

### [SHARPENS §5.2 context] Grounding instruction as a diagnostic tool, not just a safety guardrail

Heller's "sky is purple" grounding instruction does double duty: it prevents hallucination AND separates retrieval failures from prompt failures. For Verso's RunContext and ContextBundle design, this suggests grounding instructions should be a first-class parameter surfaced in the framework (not buried in system prompt boilerplate), and the framework should support tracking which failures are retrieval failures vs. model failures. This is diagnostic infrastructure, not just safety.

**Verdict**: New design implication for ContextBundle.inspect() — add failure-mode attribution.

### [CONFIRMS §5.3 tools] Per-micro-step model routing confirms role-tiered model design

"A different model for every single prompt" and Heller's explicit recommendation ("Gemini Flash if it works, don't use Pro") confirm Verso's §6.4 role-tiered model design. The framework should make per-tool/per-step model routing a first-class configuration, not a monolith. The single-token classification trick (200× latency reduction) is an optimization Verso could expose as a built-in prompt decorator: `@verso.classify(model=flash, max_tokens=1)`.

**Verdict**: Confirms model-routing design; suggests concrete API for the classification optimization.

### [CONFIRMS §5.5 evals] RF-tuning requires objective judge function — Verso's judge-panel connects

Heller's finding that the hardest part of RF-tuning is "creating the objective quality judge" directly connects to Verso's judge-panel design (§5.5). Verso's `define_outcome(bounded)` primitive is the mechanism for building the quality judge that Heller identifies as the bottleneck. This is the right abstraction — the framework should make defining bounded outcome criteria as easy as possible, since that's the blocking step for systematic improvement.

**Verdict**: Confirms judge-panel design rationale with a practitioner's exact bottleneck identification.

### [NEW-IDEA] Expert workflow documentation as the missing product design phase

Heller's "undercover agent" method — documenting expert workflow before writing any prompt — is a missing step in most AI product development. Verso could surface this as a design principle in documentation or as a `workflow_map` artifact type: a structured representation of expert steps, each tagged as LLM-judgment-required or deterministic-code-required. This is the spec before the code, applied at the product level.

**Verdict**: New-idea for documentation and workflow primitives. Lightweight to implement.
