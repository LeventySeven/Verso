# Open-Endedness and General Intelligence

**Speaker:** Tim Rocktäschel (Google DeepMind / UCL, Open-Endedness Team Lead)  
**Venue:** Talk (given at multiple venues: Imperial College I-X Seminar, Cambridge NLIP Seminar, UCL Inaugural Lecture — same content, ~39 minutes)  
**URL:** https://www.youtube.com/watch?v=Ums_VKKf_s4  
**Status:** read_partial  
**Source found:** No direct transcript available for the specific video. Content reconstructed from: (a) the companion ICML 2024 position paper "Open-Endedness is Essential for Artificial Superhuman Intelligence" (Hughes, Dennis, Parker-Holder, Behbahani, Mavalankar, Shi, Schaul, Rocktäschel — PMLR 235, https://arxiv.org/abs/2406.04268) digested via gonzoml.substack.com and proceedings.mlr.press; (b) Cambridge NLIP Seminar abstract (May 2024); (c) Imperial College I-X Seminar abstract; (d) UCL inaugural lecture page; (e) Rainbow Teaming paper abstract (arxiv 2402.16822, Rocktäschel et al.); (f) AdA / Human-Timescale Adaptation paper (Bauer et al., 2023, ICML). The ICML paper is the canonical written version of the talk's arguments. What is not available: verbatim quotes from the specific video, speaker's exact framing or emphasis in the 41-minute version.

---

## Core Thesis

Open-endedness — the property of a system that generates sequences of artifacts that are both *novel* and *learnable* — is not a luxury property of advanced AI. It is a prerequisite for artificial superhuman intelligence (ASI). The trend of improving foundation models through passive scaling will plateau; the fastest path to ASI will be inspired by the scientific method, combining foundation models with open-ended algorithms that drive active self-improvement.

The research program has three interconnected parts: (1) training autonomous agents that can set their own goals and problems; (2) training large-scale world models that provide endless learning environments; (3) connecting open-endedness methods to LLMs to develop AI that can improve itself.

---

## Key Frameworks / Mental Models

### The Formal Definition of Open-Endedness (Novelty + Learnability)

A system is open-ended from the perspective of an observer if and only if its sequence of artifacts exhibits both:

1. **Novelty:** Artifacts become increasingly unpredictable to the observer over time. Expected predictive loss increases for later artifacts — genuine surprise.
2. **Learnability:** The observer's predictive loss decreases as they observe longer historical context. Artifacts make sense in retrospect, enabling the observer to learn patterns.

The encapsulation: *"we'll be surprised, but we'll be surprised in a way that makes sense in retrospect."*

This observer-dependence matters: human cognitive limitations mean a finitely open-ended system may appear infinitely open-ended to a human observer (bounded by human working memory). Non-human observers could evaluate systems humans perceive as saturated.

Two classes:
- **Infinitely open-ended:** maintains novelty + learnability across all time horizons
- **Finitely open-ended:** bounded time horizon τ before novelty plateaus

### Why Passive Scaling Fails the Open-Endedness Test

Foundation models trained on fixed internet datasets are, by this definition, *not* open-ended. They eventually exhaust epistemic uncertainty — no new genuine surprises remain relative to a fixed observer. Context-conditioning changes this: by recombining concepts through contextual prompting, foundation models could theoretically maintain open-endedness indefinitely. This is the bridge from current LLMs to open-ended ASI.

### Illustrative Case Studies

**AlphaGo / AlphaZero:** Achieves open-endedness through self-play. Generates novel moves humans can learn from. Finitely open-ended — plateaus once the game is solved.

**Adaptive Agent (AdA):** Meta-RL trained in XLand 2.0 (procedurally generated 3D worlds + multi-player games). Emergent in-context adaptation to novel tasks at human timescale. Three ingredients: (1) meta-RL across vast, smooth, diverse task distribution; (2) large-scale attention-based memory architecture; (3) automated curriculum prioritizing tasks at the frontier of capability. Finitely open-ended — plateaus after approximately one month due to architectural and environmental limits.

**POET:** Co-evolving agent-environment pairs within a quality-diversity algorithm framework. Maintains open-endedness longer than single-objective systems. Ultimately hits computational saturation.

### Path to ASI Through Open-Endedness: Four Directions

1. **Reinforcement Learning integration:** Wrap RL-style self-improvement around foundation models. Voyager (Minecraft agent) is the clearest example — iterative capability expansion through environmental interaction.
2. **Self-improvement mechanisms:** Tool use, inter-agent communication, model-generated feedback loops. Constitutional AI is cited as a proof-of-concept for replacing human feedback with model-based alternatives for continuous self-refinement.
3. **Task generation ("The Problem Problem"):** The hardest part. Two approaches: environment generation with multimodal reward models; world model training enabling action simulation.
4. **Evolutionary algorithms in code space:** LLMs as selection and mutation operators. Evolution happens in code spaces rather than traditional parameter spaces. Open-ended program synthesis.

### Rainbow Teaming as Open-Ended Safety Research

Rainbow Teaming frames adversarial prompt generation as a *quality-diversity problem*: use open-ended search to populate an archive of successful adversarial prompts spanning dimensions like Risk Category and Attack Style, becoming progressively more effective. Achieved >90% attack success rate on Llama 2 and Llama 3. Fine-tuning on this synthetic adversarial data improves safety without degrading general capability. This is the open-endedness framework applied to the safety problem.

---

## Safety Implications of Open-Ended Systems

The paper explicitly addresses safety as an escalating concern:

**Dual-use capabilities:** Open-ended systems inherently generate novel possibilities, including dangerous ones. Aggressive exploration strategies compound this.

**Interpretability failure:** Artifacts may become incomprehensible to humans, violating the learnability requirement — the system is open-ended relative to a smarter observer but opaque to humans. This is a safety failure mode, not just an evaluation failure.

**Goal misgeneralization:** Systems without well-defined objectives risk specification gaming. Agents capable of environmental action face the Goodhart problem at scale.

**Directability tension:** A fundamental tension exists between maintaining human control and preserving open-ended behavior. Solutions require human-in-the-loop frameworks that constrain without over-constraining.

**Systemic risk:** Individual safe components can create unforeseen problems in integrated human-AI systems. The "flash crash" analogy — emergent behaviors from component interactions.

---

## Tactics / Steps

- Design automated curricula that prioritize tasks at the *frontier* of capability, not the center of the distribution (AdA's lesson).
- Use quality-diversity algorithms rather than single-objective optimization to maintain open-endedness (avoid finitely open-ended convergence).
- Treat task generation as the hard unsolved problem; environment generation is tractable; reward specification is not.
- Apply the learnability criterion as a filter: if humans cannot learn from the artifacts the system generates, the system is not producing useful intelligence — it is generating noise.

---

## Numbers

- AdA (Human-Timescale Adaptation): adapts to novel tasks as effectively and efficiently as humans, trained in XLand 2.0. Finitely open-ended — plateaus at ~1 month.
- Rainbow Teaming: >90% attack success rate on Llama 2 and Llama 3; synthetic adversarial data improves safety without degrading capability.
- AdA paper: demonstrated characteristic scaling laws with respect to network size, memory length, and task distribution richness.
- ICML 2024 position paper received Best Paper Award at ICML 2024 (one of two for Rocktäschel's work that year).

---

## Near-Verbatim Quotes (from paper, not video)

- "We'll be surprised, but we'll be surprised in a way that makes sense in retrospect." (The operational definition of open-endedness)
- "Open-endedness is an essential property of any artificial superhuman intelligence." (Core claim)
- "The trend of improving foundation models through scaling alone will soon plateau, and the fastest path to ASI will be inspired by the scientific method and combining foundation models with open-ended algorithms." (Path thesis)
- "The ingredients are now in place to achieve open-endedness in AI systems with respect to a human observer." (Tractability claim)

---

## VERSO RELEVANCE

### [NEW-IDEA §6.1 durable] The "finitely open-ended" ceiling as the case for durable agents
AdA's key failure mode — finite open-endedness, plateauing after ~1 month in training — translates directly to agent deployment. A tactical ephemeral agent will converge on a behavioral plateau; it cannot improve from deployment experience. The durable layer (§6.1 event-sourced checkpoint/resume) is Verso's mechanism for keeping agents on the novelty frontier: logged event streams create the corpus from which improvement loops can close. The seam is not just about resume-on-failure — it is the architectural prerequisite for an agent that can remain genuinely open-ended over deployment time. **Verdict:** new framing for the durable layer's deeper purpose — not just reliability but ongoing learnability.

### [CONTRADICTS §5.1 loop / strategy] "The ideal harness is no harness" vs. open-endedness
Noam Brown's position (MLST) — "harnesses are a crutch; reasoning models will wash them away" — and Rocktäschel's position are in tension. Open-endedness requires an outer loop (quality-diversity, automated curriculum, task generation). These are harness functions, not model-internal capabilities. The "no harness" thesis assumes reasoning models internalize everything; the open-endedness thesis requires external scaffolding for task generation, learnability tracking, and diversity maintenance. Verso's bet (the harness *is* the product) aligns with Rocktäschel, not Brown. **Verdict:** genuine contradiction — Rocktäschel's framework gives Verso a principled counter to the "harnesses will disappear" attack.

### [SHARPENS §5.5 evals] Learnability as the correct eval criterion
The Rocktäschel / Hughes et al. definition of learnability — "observer's predictive loss decreases as they receive longer historical context" — is a more precise formulation of what `define_outcome(bounded)` should be measuring. An eval is not just "did the agent get the right answer?" but "does the pattern of successes and failures teach the human operator something in retrospect?" If eval logs are opaque (no learnable pattern), the system has crossed into non-learnability and is functionally unsafe by Rocktäschel's definition. **Verdict:** sharpens the evals spec — learnability of the trace is a design criterion, not just accuracy of the output.

### [NEW-IDEA §6.2 multiagent] Quality-diversity as multi-agent scheduler
Rainbow Teaming's quality-diversity framework — populate an archive of agents spanning diversity dimensions — maps onto §6.2 multi-agent scheduling. Rather than running identical sub-agents in parallel, a quality-diversity approach would schedule sub-agents across diverse strategy/approach dimensions, maintaining coverage of the solution space. This is an unexplored design point between "parallel identical sub-agents" and "hierarchical task decomposition." **Verdict:** genuine new idea for the §6.2 multi-agent layer — diversity-aware scheduling as an architectural option.

### [SHARPENS §6.3 safety] Directability-openness tension as a design constraint
The fundamental tension Rocktäschel identifies — human control constrains open-endedness; open-endedness undermines human control — is the core design constraint for §6.3. Verso's HITL promotion mechanism (the tactical/durable seam) is a partial resolution: HITL is opt-in, not mandatory, so the default tactical agent retains full openness while the promoted durable agent trades some openness for accountability. This is not fully theorized in the PRD and Rocktäschel's framing gives it formal backing. **Verdict:** sharpens §6.3 — the HITL seam resolves the directability/openness tension, and this should be stated explicitly.

---

## One-Line Verdicts Per Finding

| Finding | Tag | Verdict |
|---|---|---|
| Finite open-endedness (AdA plateaus) → durable layer as learnability prerequisite | NEW-IDEA §6.1 | Reframes durability: not just fault-tolerance but deployment-time learnability |
| Harness as task-generation/QD scaffold vs. "no harness" thesis | CONTRADICTS §5.1 | Rocktäschel gives principled counter to the "harnesses disappear" critique |
| Learnability criterion = eval traces must be teachable in retrospect | SHARPENS §5.5 | Eval design criterion: trace learnability, not just output accuracy |
| Quality-diversity scheduling for multi-agent diversity | NEW-IDEA §6.2 | Diversity-aware sub-agent scheduling as unexplored design point |
| Directability/openness tension resolved by opt-in HITL | SHARPENS §6.3 | Formal backing for the tactical/durable seam as a safety mechanism |
