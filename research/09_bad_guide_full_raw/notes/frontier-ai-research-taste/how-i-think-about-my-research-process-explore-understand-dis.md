# How I Think About My Research Process: Explore, Understand, Distill — Neel Nanda

**URL**: https://forum.effectivealtruism.org/posts/hmBPqApDXvhLzbiFt/how-i-think-about-my-research-process-explore-understand  
**Author**: Neel Nanda (Google DeepMind, Mechanistic Interpretability team lead)  
**Published**: EA Forum (date approximate)  
**Type**: Essay / first post in a sequence on research process  
**Status**: read_full — complete text retrieved and verified

---

## Source Description

This is Neel Nanda's first-principles framework for how he conducts open-ended empirical research, developed through supervising 20+ papers in mechanistic interpretability. He breaks research into four stages — Ideation, Exploration, Understanding, Distillation — and gives specific tactical and strategic advice for each. The key claim: the dominant junior-researcher mistake is imposing hypothesis-testing structure *before* they understand the territory, i.e., jumping from Exploration to Understanding without doing the Exploration work. The secondary claim: distillation is deeply undervalued, and early distillation accelerates understanding.

While the context is mech-interp, Nanda explicitly states the framework applies to "empirical sciences with short feedback loops."

---

## Full Digest

### Introduction

> "Research is hard. Expect frustration, dead ends, and failed hypotheses."

Nanda's framework is both strategic (high-level direction, pivoting decisions) and tactical (next steps, prioritization). He distinguishes these from specific skills like coding or paper reading, which are separable competencies.

The guide is intentionally personal: "This framework reflects subjective experience and may not universalize." But it has been validated over 20+ supervised papers.

### Stage 1: Ideation — Choose a Problem / Domain

Research taste has multiple components:
- **Exploration**: noticing when anomalies merit investigation
- **Understanding**: designing experiments that distinguish hypotheses precisely
- **Distillation**: identifying the most interesting narrative
- **Broadly**: an intuitive understanding of what constitutes good research, informed by deep domain knowledge

> "Research taste encompasses multiple facets beyond problem selection."

Practical guidance: for initial projects, lean on mentors and read key papers. "Tools like Google/OpenAI Deep Research help with literature reviews in unfamiliar domains." Replicating and extending existing papers works well for those without mentors.

### Stage 2: Exploration — Gain Surface Area

"At the project's start, understanding is vague. You often don't know the right questions yet."

**North star**: Gain information efficiently.

**The core junior mistake**: researchers think they should have clear goals and specific hypotheses immediately. Nanda says this is wrong — being in exploration without clear direction is totally normal and expected.

> "Prioritise for information gain."

Practical tactics:
- Do many experiments quickly rather than seeking perfect experiments
- Visualize data in multiple ways
- Ask regularly: "Am I getting enough information per unit time?"
- Keep a **highlights document** of interesting results to spot connections

> "Long-term exploration should feel like play — following genuine curiosity while checking you're not in rabbit holes."

Key realization: **"Much exploration work involves discovering which questions matter, then crystallizing those into precise hypotheses becomes straightforward."**

The question-discovery step is the substance of exploration — not the hypothesis-testing.

### Stage 3: Understanding — Test Hypotheses

This stage begins when you understand the domain well enough to form *specific, testable hypotheses* — ones you can write down and envision evidence for or against.

Example hypothesis: "Do chat models store summarized information about user prompts in specific tokens?"

**North star**: Gather evidence for and against hypotheses.

The process is not linear: you frequently dip back into exploration when:
- Hypotheses prove ill-posed
- Experiments don't work as designed
- Anomalous results emerge

**Critical skill**: deep commitment to skepticism. Researchers encounter wrong hypotheses, inconclusive experiments, methods that lose to simple baselines. 

> "This is normal but emotionally challenging."

Practical approaches: always seek alternative explanations, implement strong baselines, check for bugs.

**Experiment design as underrated skill**:

> "Great experiments elegantly distinguish between plausible hypotheses, validate non-trivial predictions, and remain tractable to implement."

Internal process: "simulating worlds where hypotheses are true, thinking through implications, and converting implications into testable experiments."

### Stage 4: Distillation — Compress, Refine, Communicate

Begins when you're "fairly convinced" (not proven) your hypotheses are true or false.

**North star**: Distill findings into concise, rigorous truth communicated clearly.

Three components:

**Compress**: Reduce work into concrete, well-scoped claims — "something fitting into bullet points." Explain it to a peer in a lightning talk. "Readers rarely retain more than a few key claims."

**Refine**: Build rigorous evidence for each claim, persuasive to skeptics through *strong evidence*, not clever writing. Higher standards than self-conviction: sanity checks, statistical robustness, strong baselines.

> "Spend substantial time red-teaming: What could you be missing? What alternative explanations exist? What experiments would distinguish them?"

**Communicate**: "Clarity matters more than polish. Present evidence clearly and acknowledge limitations."

**The undervaluation mistake**: "Researchers undervalue this stage, treating write-ups as time-wasting afterthoughts left until conference deadlines. Actually, early distillation work is valuable — writing clarifies understanding, reveals holes, prompts missing experiments."

**The overvaluation mistake (opposite)**: "Over-prioritizing distillation, defaulting to 'get accepted to conferences' as the main goal. This warps thinking toward impressive-looking rather than important questions, and evidence reviewers prefer rather than evidence establishing truth."

> "Your ultimate goal is to find truth, not to produce an exciting paper."

### On Pivoting and Recursion

"Sometimes distillation reveals messier-than-expected situations. Acknowledge this rather than denying inconvenient truths. You may need to return to understanding or exploration — this is normal and doesn't indicate failure."

The four stages are not strictly sequential — they are recursive. The loop between Understanding and Exploration is especially common.

### On Sustainable Work

"Research involves frustration, dead ends, and imposter syndrome. Focus on process and learning. Take breaks — sustainable work yields better overall productivity."

---

## VERSO RELEVANCE

This essay is primarily about *how humans do research*, not about agent design. But the framing has precise and non-obvious implications for Verso because Verso's evals and loop design are themselves about directing a cognitive loop (model + harness) that mirrors the research process Nanda describes.

### [SHARPENS §5.5] — Eval design must match the stage: Exploration evals ≠ Understanding evals
Nanda's key insight is that exploration and understanding are fundamentally different cognitive modes with different success criteria. Applied to Verso's eval harness: **evals should be tagged by the stage they test**, not treated as a uniform battery. An "exploration eval" measures information gain (did the agent surface useful surface area? did it avoid rabbit holes?). An "understanding eval" measures hypothesis quality (did the agent form testable, specific predictions?). A "distillation eval" (= Verso's current judge-panel / define_outcome) measures correctness and parsimony of the final output.

Verso's current evals (judge-panel, define_outcome(bounded)) are exclusively distillation-phase evals. There is currently no primitive for exploration-phase evaluation (e.g., "did the agent observe the right things?"). **Verdict: sharpen** — add exploration-phase eval primitives (information gain / coverage metrics) to the evals spec.

### [SHARPENS §5.1] — The "highlights document" pattern = explicit intermediate state tracking in the loop
Nanda's tactical advice: keep a highlights document of interesting results to spot connections across experiments. In agent-loop terms, this is a named pattern: **intermediate observation accumulation**, distinct from the main conversation transcript. An agent running many parallel tool calls (exploration phase) should accumulate a `highlights_buffer` — a curated subset of notable intermediate results — rather than forcing the full observation log into the next reasoning step. This is a missing primitive in Verso's context engineering. **Verdict: lock-interface-defer** — define the `highlights_buffer` interface slot; defer implementation.

### [SHARPENS §5.2] — "Information gain per unit time" as a first-class optimization target
Nanda's north star for exploration: "Prioritize for information gain." Ask regularly: "Am I getting enough information per unit time?" This is a concrete optimization objective that Verso's loop does not currently track. An exploration-mode agent should be asking this question structurally — i.e., the harness should be able to inject a prompt: "Given what you've observed so far, is this tool call likely to provide new information or is it redundant?" This is a **context-injection pattern** distinct from reflection/self-critique: it's a coverage monitor, not an error checker. **Verdict: lock-interface-defer** — design as a named hook: `on_step_before(mode="explore")` injects information-gain prompt.

### [NEW-IDEA for §5.1 / §5.5] — Recursive stage awareness: loop should know what phase it's in
Nanda's framework is explicitly recursive — agents (and researchers) move between Exploration, Understanding, and Distillation dynamically. This implies Verso's agent loop could benefit from an explicit **mode parameter** or **phase tracking**: is the agent currently exploring (information gain), understanding (hypothesis testing), or distilling (evidence compression)? Different phases warrant different tools, different context compaction strategies, and different eval criteria.

This is a significant architectural idea: rather than a single monolithic loop, Verso could expose a `phase` parameter that the harness uses to configure:
- Which tools are prioritized (exploration: broad read-only tools; understanding: targeted probing tools; distillation: write tools)
- Context compaction aggressiveness (exploration: keep everything; distillation: compress heavily)
- Eval criteria (information gain vs. hypothesis test vs. claim precision)

**Verdict: lock-interface-defer** — the loop API should reserve a `mode/phase` field; don't build the full machinery in v1, but don't close the door.

### [SHARPENS §5.5] — Red-teaming as a named eval step: alternative explanations + distinguishing experiments
Nanda's distillation advice: "Spend substantial time red-teaming: What could you be missing? What alternative explanations exist? What experiments would distinguish them?" This is a concrete formulation of adversarial eval that maps to Verso's judge-panel design. The judge panel should include a **devil's advocate role** that explicitly generates alternative explanations for the observed output before scoring. This makes red-teaming a structural requirement, not an afterthought. **Verdict: adopt-now** — add a named `devil_advocate` judge role to the judge-panel spec.

### [CONFIRMS §5.5] — Early distillation is valuable; writing clarifies understanding
"Early distillation work is valuable — writing clarifies understanding, reveals holes, prompts missing experiments." This confirms that Verso's `define_outcome(bounded)` should be defined *at the start* of an eval run, not after results are in. An outcome defined late is susceptible to post-hoc rationalization. This is the "pre-register your eval" principle. **Verdict: confirm** — define_outcome pre-registration is already implied by Verso's design; this reinforces it.

### [CONFIRMS §2 / §1] — "Find truth, not exciting paper" = quality signal for what Verso shouldn't be
"Your ultimate goal is to find truth, not to produce an exciting paper." The opposite mistake — optimizing for reviewer-preferred evidence rather than truth — maps precisely to what LangChain and LangGraph do: optimize for impressive demo benchmarks and conference talks. Verso's "no overkill, no bullshit, simplicity" principle is the engineering equivalent of Nanda's research integrity principle. **Verdict: confirm** — useful rhetorical alignment for §12 positioning.

### [SHARPENS §6.2] — Subagent scope = exploration vs. understanding role assignment
In a multi-agent Verso deployment, subagents could be assigned to different phases: one subagent runs exploration (broad parallel tool calls, information gain mode), another runs understanding (targeted hypothesis probing), a third runs distillation (synthesis and compression). This extends the already-known role-tiered model pattern (cheap loop / mid retry / reasoning synthesis) into a *phase-tiered subagent* pattern. **Verdict: lock-interface-defer** — track as a named multi-agent dispatch pattern.
