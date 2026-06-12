# Scaling and the Road to Human-Level AI — Jared Kaplan, Anthropic

**Source:** Y Combinator AI Startup School, San Francisco  
**URL:** https://www.youtube.com/watch?v=p8Jx4qvDoSo  
**Transcript:** https://www.ycombinator.com/library/Ml-scaling-and-the-road-to-human-level-ai-anthropic-co-founder-jared-kaplan  
**Secondary digest:** https://videotobe.com/play/youtube/p8Jx4qvDoSo  
**Date:** June 16, 2025  
**Duration:** 41m  
**Status:** read_partial (YC library page did not render full transcript; substantive content extracted from videotobe.com professional transcript digest — covers all major sections with many verbatim passages)

---

## Speaker Background

Jared Kaplan: Anthropic co-founder, trained as theoretical physicist. The originator of neural scaling laws — the empirical finding that model performance scales predictably with compute, data, and model size. Considered the primary source on scaling intuition in the field.

---

## The Scaling Laws Discovery

Kaplan's central empirical finding, presented as the talk's foundation:

"Discovered remarkably precise trends — as precise as anything in physics or astronomy."

The scaling relationships span "many, many, many orders of magnitude in compute, in data set size." This consistency across 5+ orders of magnitude was the key signal: it implied the trend would continue predictably, not plateau unexpectedly.

Physics intuition was the methodological key: rather than vague claims like "exponential convergence," ask "Could it just be a power law? Is it quadratic? Exactly how is this thing converging?" Precision enables prediction and navigation.

Framework applied: large neural networks are studied "as very large systems" leveraging "well-established mathematical approximations from physics and mathematics concerning large matrix behavior."

---

## Two Training Phases

### Pre-Training

"Train AI models to imitate human-written text" and "learn correlations underlying the data."

Models learn which words likely follow others — "learning to predict the next word" as the fundamental mechanism. This phase is compute-bounded and scales predictably.

### Reinforcement Learning Phase

Uses human feedback: early Claude interfaces had annotators compare model responses, selecting outputs deemed "helpful, honest, and harmless," reinforcing beneficial behaviors.

Researcher Andy Jones discovered scaling laws apply to RL too — studying the game Hex showed "remarkable straight lines" in ELO ratings, confirming RL improvements follow mathematical laws similar to pre-training.

---

## Capability Axes

Kaplan frames AI progress on two axes:

**Flexibility (Y-axis):** from narrow (AlphaGo, Go only) to multimodal (text, images, diverse modalities)

**Time horizon (X-axis):** the more important axis. Task complexity and duration capability expanding continuously.

The time horizon axis is the primary one for enterprise and agent use cases. Current capability: "hours"-scale software engineering tasks.

---

## Task Horizon Scaling

Per METR research: task length "doubling roughly every seven months" as models scale.

Projection: predictable progression toward tasks requiring days → weeks → months → years. "Potentially enabling organizations of AI systems to accomplish work equivalent to entire human institutions or scientific communities."

---

## Ingredients for Human-Level AI: The Four Remaining Components

Kaplan identifies what's still missing:

1. **Organizational Knowledge** — AI must operate within company contexts, retaining knowledge about institutional norms, "similar to humans with years of experience."

2. **Memory** — "beyond static knowledge, models need to track progress within extended tasks, building and retrieving task-specific memories across multiple context windows." Memory is identified as the key differentiator for longer-horizon tasks.

3. **Oversight / Nuanced Evaluation** — current systems excel at crisp evaluation (code passes tests; math proves correct), but advancing requires "sophisticated reward signals for subjective assessments — tell good jokes, write good poems, and have good taste in research."

4. **Multimodal Expansion** — from text to robotics, applying scaling principles across modalities.

---

## Memory as the Key Differentiator

Kaplan identifies memory as unlocking "longer and longer horizon tasks," positioning Claude as an "expanding collaborator capable of handling increasingly substantial work portions autonomously."

This is the central bottleneck argument: the loop is not the constraint; memory across context windows is.

---

## Oversight as the Human Role

A key structural finding on human-AI collaboration:

"Humans can judge performance in domains exceeding their execution capability, while AI's generative and judgment abilities remain closely matched."

This creates a stable human niche: oversight and sanity-checking, as "managers to sort of sanity check the work." The point is not that humans are better generators; it's that human judgment can exceed human execution in complex domains, and this asymmetry is durable.

This is the basis for the HITL (human-in-the-loop) pattern: HITL is not a temporary scaffold while AI improves; it is structurally stable because judgment and generation scale at different rates.

---

## The Jevons Paradox and Frontier Value

As AI intelligence improves and becomes cheaper, demand increases rather than stabilizing — the Jevons Paradox.

"Much more convenient to be able to use an AI model that can do a very complex task end-to-end, rather than requiring us as humans to sort of orchestrate a much dumber model."

Translation: end-to-end capable frontier models retain value even as cheaper models improve, because the coordination overhead of orchestrating dumber models is itself a cost. This is the economic argument against "dumb model orchestration" patterns.

---

## Compute Efficiency Trajectory

Current AI remains "really inefficient" because unlocking frontier capabilities takes priority over cost reduction.

"Annual gains of 3x to 10x occur through algorithmic improvements and scaling, yet efficiency gains typically redirect toward increased capability rather than cost reduction."

Future equilibrium: "extremely inexpensive" AI through lower precision formats — but continued rapid capability improvements may sustain frontier focus indefinitely.

---

## Claude 4 Improvements (Revealed Here)

Claude 4 reduced over-eagerness in agent behavior (noted as a problem in 3.7), with key improvements:

- Better oversight and directional following
- Memory systems enabling task persistence across context windows
- Improved code quality through refined supervision

"Scaling laws paint a picture of incremental progress toward human-level AI through smooth curve progression."

---

## Depth vs. Breadth Intelligence

A sharp distinction relevant to AI positioning:

**Depth** (single-problem focus over decades, e.g., Riemann hypothesis) — requires sustained human expertise that AI currently lacks for novel frontier problems.

**Breadth** (synthesizing vast information across disciplines, e.g., biology + psychology + history) — AI excels because "comprehensive pre-training knowledge enables extracting insights no single human expert could assemble independently."

AI's competitive advantage is strongly in breadth synthesis. Agent frameworks should route accordingly.

---

## On Scaling Law Failure

When scaling appears broken, Kaplan's default hypothesis: implementation error, not law breakdown.

"Five years of experience showed apparent failures invariably resulted from implementation mistakes" — incorrect architecture, bottlenecks, or precision problems.

The practical implication: if a model doesn't improve with more compute, fix the training setup before concluding scaling has stalled.

---

## Building Strategy for Founders

"Build things that don't quite work yet" — exploit rapidly advancing capabilities. Products failing with current Claude versions might succeed with forthcoming releases.

"Leveraging AI for AI integration" — accelerating adoption across sectors. Focus on identifying rapid-adoption domains beyond software engineering.

---

## VERSO RELEVANCE

### [SHARPENS §5.4 / memory] — Memory is the human-level AI bottleneck, not the loop

Kaplan explicitly identifies memory as the key differentiator for longer-horizon tasks — not compute, not model size, not loop architecture. This sharply confirms Verso's 4-tier typed memory + temporal versioning (§5.4) as a first-class architectural concern, not a convenience feature. **SHARPENS §5.4**: the memory design should be foregrounded in Verso's positioning — "Verso solves the memory bottleneck Kaplan identifies as the primary constraint on longer-horizon agents."

### [SHARPENS §4 / seam] — HITL is structurally stable, not temporary scaffolding

Kaplan's "judgment exceeds execution" asymmetry provides a theoretical grounding for Verso's one-flag tactical-to-durable promotion with HITL. HITL is not scaffolding to remove as models improve; it is structurally stable because human judgment and AI generation scale differently. **SHARPENS §4**: the seam design doc should note that HITL is not a temporary feature — it has a permanent role as judgment asymmetry persists.

### [CONFIRMS §5.5 / evals] — Nuanced oversight as eval: the reward signal problem

Kaplan's "oversight/nuanced evaluation" ingredient directly validates Verso's judge-panel + define_outcome(bounded) approach. The problem he names — "sophisticated reward signals for subjective assessments" — is exactly what Verso's panel-of-judges eval infrastructure addresses. **CONFIRMS §5.5**: use Kaplan's framing ("tell good jokes, write good poems, have good taste in research") as the canonical statement of the problem Verso's evals solve.

### [SHARPENS §12 / strategy] — Jevons Paradox against dumb-model orchestration

Kaplan's Jevons argument ("more convenient to use a model that does complex tasks end-to-end") is an economic argument *against* multi-layer orchestration of weaker models. This creates a tension with Verso's multi-agent dispatch (§6.2): orchestrating many dumb sub-agents may be more expensive than one capable frontier model. **SHARPENS §12**: Verso's multi-agent rationale should address this trade-off explicitly — sub-agents are justified when parallelism > coordination overhead, not as a default pattern.

### [NEW-IDEA — §5.4 / memory] — Task-horizon doubling (7 months) as Verso benchmark target

METR's finding that task horizons double every 7 months is a concrete benchmark target for Verso's memory and durable layer. If the framework is designed today for hours-scale tasks, it should be *architecturally ready* for weeks-scale tasks within 14 months. **NEW-IDEA**: add a "horizon readiness" property to the durable layer design — what needs to change (if anything) when task horizons move from hours to days to weeks? This is a concrete forward-compatibility test for §6.1.

---

## One-Line Verdict per Finding

- **Memory is the bottleneck**: §5.4 should be foregrounded in all Verso positioning as the core differentiator.
- **HITL is structurally stable**: §4 seam doc should state that HITL is permanent, not scaffolding — grounded in Kaplan's judgment/execution asymmetry.
- **Evals confirm**: use Kaplan's "good taste in research" framing as canonical motivation for judge-panel evals.
- **Jevons vs. orchestration**: §12 needs explicit trade-off analysis — sub-agents when parallelism beats overhead, not by default.
- **7-month horizon doubling**: add horizon-readiness test to §6.1 durable layer design.
