# Interpretability Dreams

**Source**: https://transformer-circuits.pub/2023/interpretability-dreams/index.html  
**Author**: Chris Olah (Anthropic)  
**Published**: 2023  
**Read time**: ~4,000 words  
**Status**: read_full

---

## Faithful Digest

This essay is a research agenda framed as a set of "dreams" — aspirational but tractable goals for mechanistic interpretability. The central intellectual move is Olah's argument for **starting with the tractable sub-problem that opens an entire agenda** rather than charging the big question directly. The essay is organized around six interlocking themes that build from microscopic circuits to large-scale model structure.

### Core Argument: Epistemic Foundation via Bottom-Up Approach

Olah frames mechanistic interpretability as a "bottom-up approach, studying small pieces without an a priori theory." The key epistemological insight: **researchers who start top-down with hypotheses misinterpret neural networks**.

His example: vision models. Researchers naturally assume "dog-head detectors" exist — and find supporting evidence. But earlier layers contain snout, fur, and eye detectors that *also* predict dog presence. Top-down investigation creates an illusion of confirmation.

The solution: examine sufficiently small circuits where "statements about their behavior become questions of mathematical reasoning." This provides an epistemic foundation analogous to axioms in mathematics or assembly language in programming — a ground level from which rigorous upward inference is possible.

### Six Themes / Dreams

**1. Epistemic Foundation**  
Build rigorous ground-level circuit understanding. Small enough circuits are provably understood; work upward from there. No a priori theory needed at the start.

**2. Possibilities / What Becomes Tractable**  
Once foundational understanding is solid, larger analyses become possible: Can we detect deception? Can we understand capability emergence? These become tractable only after the foundation is built.

**3. Feature Families and Equivariance**  
Key tractability insight:

> "Neural network features often appear to form families of analogous features, parameterized by some variable."

Rather than cataloging millions of individual features, researchers can study *families* organized by orientation, scale, hue, or other parameters. The database analogy: structured data remains understandable despite volume because it has schema. Feature families are the schema of the neural network's internal representations.

This is the core "tractable sub-problem" move: instead of "understand all features," ask "what are the structural regularities across feature families?" — a much smaller problem that opens the whole feature-understanding agenda.

**4. Circuit Motifs**  
Reusable computational patterns across different circuits:

> "We expect investigations of motifs to be well served by us first building up a solid foundation of well understood circuits first."

The strategy is explicitly sequential: small circuits → motifs → larger structures. Don't attempt motif discovery before having a solid foundation; the foundation is not wasted work, it's prerequisite work.

**5. Branch Specialization / Macro-Scale Structure**  
Moving from "tiny little veins" (individual neurons) to discovering emergent structures larger than single circuits but smaller than entire networks:

> "Is there a 'respiratory system' or 'heart' or 'brain region' of an artificial neural network?"

This is a research dream, not a current capability — but it's directional: circuit analysis is not the endpoint, it's the beginning of a hierarchy of understanding.

**6. Universality**  
The observation that similar features appear across different networks trained on different data. This becomes a strong constraint: if feature X appears universally, it's likely not a training artifact but a fundamental structure. Universality findings allow cross-network inference.

### The Superposition Problem as a Blocking Sub-Problem

Olah identifies superposition as the key thing that makes the vision-model-style circuit analysis hard to transfer to language models:

> "The extensive superposition of language models has made it much harder to discover analogous structure."

This reframing makes the problem tractable: **solve superposition first** as the blocking sub-problem, then apply the vision-model circuit analysis toolkit to transformers. This is precisely the move that led to sparse autoencoders as a research direction — not "understand transformers," but "first break superposition."

### Bridging Microscopic to Macroscopic

Olah notes a crucial result: "some microscopic, mechanistic discoveries (such as induction heads) have significant macroscopic implications." Induction heads, discovered through circuit analysis, explain in-context learning across a wide range of models — a macroscopic behavior explained mechanistically.

This creates a feedback loop:
1. Find microscopic circuit structure
2. Test whether it predicts macroscopic behavior
3. Use confirmed predictions to validate the microscopic understanding
4. Use the validated framework to investigate new macroscopic phenomena

The bridging strategy is not about completeness but about **predictive leverage** — small mechanistic facts that make large behavioral predictions.

### Research Philosophy: The Tractable Sub-Problem Move

The implicit methodology throughout is:

1. Identify the big question (understand neural networks)
2. Find the blocking sub-problem (superposition prevents feature identification)
3. Define a tractable formulation of the blocking sub-problem (can we decompose activations into monosemantic features?)
4. Solve at minimal scale (toy models, single layers)
5. Generalize upward through discovered structures (families → motifs → branches → macro)

The crucial move is step 2-3: **converting the blocking problem into a tractable version** without losing contact with the original big question.

### The Database Analogy (Feature Families)

The database framing is load-bearing for understanding why the problem is tractable at all:

If neural networks stored one feature per neuron (monosemantic), the interpretability problem would be like reading a database row-by-row — tedious but tractable. Superposition makes neurons polysemantic, breaking the obvious mapping. Feature families restore structure: even with superposition, features are not random — they organize into families with structure. This structure is the "schema" that makes the database readable again at scale.

---

## VERSO RELEVANCE

### [NEW-IDEA §4 the seam / §5.1 loop] — The Blocking Sub-Problem Method as Framework Design Discipline

Olah's methodology — identify the big question, find the *blocking* sub-problem, solve it tractably at minimal scale, generalize upward — is directly applicable to Verso's architecture design process.

Applied to Verso: the "big question" is "how do we make agents reliable and production-worthy?" The blocking sub-problem is **context window management** — agents fail not because of bad planning but because they lose track of what matters as the context grows. Solving context engineering tractably (the `ContextBundle` abstraction, the compaction primitive, the static/dynamic prefix discipline) before trying to solve everything else is precisely the Olah move.

This reframes the Verso architecture sequence: don't try to solve the full durable/reliable agent problem first. Solve the **blocking sub-problem** (context management → evaluation → durable checkpointing) in sequence, letting each solved level open the next.

**Verdict: adopt-now** — use this framing explicitly in §4 architecture docs. The sequence context engineering → evals → durable runtime is not arbitrary feature ordering; it's a blocking-sub-problem hierarchy.

### [NEW-IDEA §5.2 context-engineering] — Feature Families → ContextBundle Schema

The feature families insight (structure restores tractability even with superposition) maps to Verso's `ContextBundle` design. The context window has "polysemantic noise" at scale — without schema, it's a mix of system prompt, task instructions, tool outputs, memory retrievals, and current observations. The `ContextBundle` is the *schema* that imposes structure:
- Static prefix (system + persona + tools) = one "family"
- Dynamic prefix (retrieved memory) = another "family"
- Active window (current observations + working memory) = another "family"

The families don't need to be monosemantic individually, but their *boundaries* need to be explicit. Olah's insight: structure is recoverable even when content is mixed, if the organizational principle (the "family parameter") is made explicit.

For Verso: `ContextBundle.inspect()` should expose the family structure, not just the raw token count. Each named slot has a type that tells you what kind of content lives there.

**Verdict: sharpen** — make `ContextBundle.inspect()` return typed slot metadata, not just content. The "family" framing justifies the typed-slot design over a flat context string.

### [SHARPENS §5.5 evals] — Microscopic Finding → Macroscopic Prediction as Eval Design

The induction heads result (microscopic circuit → explains in-context learning across all models) is a template for Verso's eval design. The most powerful evals are those where a **specific behavioral assertion at the micro level** makes a **predicted behavioral consequence at the macro level**. Not just "does the agent complete the task" but "when we ablate component X, do we get the predicted degradation?"

This is the ablation eval pattern from Nanda's guide, but here Olah adds the directionality: micro-to-macro predictions are what give evals interpretive power. An eval that says "agent completed 7/10 tasks" tells you nothing about *why*. An eval that says "when we remove tool X from the context, success rate drops from 70% to 30%, confirming that tool X is load-bearing for this task class" makes a mechanistic claim.

For Verso: eval runs should be designed to make **causal claims**, not just performance measurements. The `define_outcome(bounded)` primitive should support ablation variants as first-class citizens.

**Verdict: sharpen** — ablation-as-causal-claim should be a named eval mode in §5.5, not just a general recommendation.

### [SHARPENS §4 the seam] — Bottom-Up vs. Top-Down and Verso's Anti-Graph Stance

The fundamental reason mech interp uses bottom-up is that top-down hypotheses produce confirming evidence regardless of ground truth (the dog-head detector problem). This is precisely the failure mode of **graph-first frameworks**: the graph is a top-down hypothesis about structure that the developer imposes before knowing what the agent actually does. Evidence "confirms" the graph because the graph shapes what you look for.

Verso's "no graph required" stance is epistemically equivalent to Olah's bottom-up principle: let structure emerge from what the agent actually does (loop + tools + context), don't impose it a priori. The graph should be a *discovered artifact* (if it's useful, you can visualize the agent's traces as a graph post-hoc) not a *design constraint*.

**Verdict: confirm** — reinforces §4 anti-graph stance with epistemological grounding. Surfaceable in §4 docs as "why we don't force the graph."

### [NEW-IDEA §6.1 durable runtime] — The Sequential Tractability Stack

Olah's explicit claim: "We expect investigations of motifs to be well served by us first building up a solid foundation of well understood circuits first." This is not impatience — it's the claim that *skipping levels of the stack is a mistake even if the higher levels look more exciting*.

For Verso: skipping evals to get to durable runtime is the analogous mistake. The durable runtime (event-sourced checkpointing, replay, human-in-the-loop) is only valuable if you can *verify* that the replayed agent produces correct outputs. Without the eval layer, durable runtime is checkpointing garbage. The blocking-sub-problem sequence is: context engineering → evals → durable runtime, in that order.

**Verdict: confirm/sharpen** — use this to justify the roadmap sequencing in §4/§6.1. Don't build the durable runtime without first having eval coverage.

---

**Overall verdict**: Mid-value source for direct content; high-value for epistemological framing. The blocking-sub-problem methodology and the bottom-up anti-graph argument are the most transferable findings for Verso. The feature families → ContextBundle schema mapping is novel and worth capturing explicitly in §5.2 design docs.
