# François Chollet: How We Get To AGI

**Source:** Y Combinator AI Startup School, San Francisco, June 16, 2025, ~35m  
**URL:** <https://www.youtube.com/watch?v=5QcCeSsNRks>  
**YC Library:** <https://www.ycombinator.com/library/Md-fran-ois-chollet-the-arc-prize-how-we-get-to-agi>  
**Transcript:** <https://singjupost.com/francois-chollet-how-we-get-to-agi-transcript/>  
**Status:** read_full — full transcript found at singjupost.com and fetched successfully.

**Speaker context:** Chollet created Keras (the dominant high-level deep learning API), authored Deep Learning with Python, and created the ARC-AGI benchmark. He founded the ARC Prize competition. He is the field's most articulate critic of the conflation between scale and intelligence.

---

## Core Claim: The Pretraining Era Is Over

Chollet's central empirical claim: despite a "50,000x scale-up of base LLMs" from 2019 to present, performance on ARC-AGI remained "roughly 10%" — near random guessing. This is the decisive evidence. If scaling pretraining were sufficient for general intelligence, ARC performance should have tracked compute. It didn't.

Conclusion: "fluid intelligence does not emerge from scaling up pre-training. You absolutely need test-time adaptation." The pretraining era was the era of scaling memorized skills. That era is over.

---

## What Intelligence Is

Chollet adopts McCarthy's view: "AI is about getting machines to handle problems they have not been prepared for." His own formulation: intelligence is "the efficiency with which you operationalize past information in order to deal with the future. It's an efficiency ratio."

The key distinction: **skill vs. intelligence.**

"Skill is the output of that process...displaying skill at any number of tasks does not show intelligence." A model can achieve expert-level performance on chess, coding, and mathematics through memorization and pattern-matching — that is crystallized skill. Intelligence is the capacity to generate new skills efficiently when confronted with novel problems. Current LLMs are expert skill exhibitors, not necessarily intelligent in this sense.

---

## Why Benchmarks Matter (and Fail)

Benchmarks "direct the attention of the research community towards what matters." Saturated benchmarks (those that LLMs have already solved) are dangerous because they signal false progress. When GPT-4 achieves 95% on a benchmark, that benchmark tells you nothing about whether the field is moving toward AGI — it tells you the field has found a way to match the training distribution of that benchmark.

ARC-AGI was designed to be unsaturable by pattern-matching: each task requires solving a novel program-synthesis problem using a small number of examples. ARC-AGI cannot be solved by memorization.

---

## ARC-AGI as the Calibration Instrument

"ARC is not the destination...ARC is really just an arrow pointing in the right direction." The benchmark is a tool to reveal the bottleneck, not the final objective.

**ARC-1 results:** GPT-4 class models scored 0–10%. Humans with no prior training score ~85%. o3 at 50,000x compute reached ~87%. This gap — between human fluid intelligence and LLM performance on novel reasoning — is what ARC measures.

**ARC-2 (released March 2025):** Harder, requires "deliberate thinking" (cannot be solved by fast pattern-matching), but remains "completely doable by regular folks with no prior training." GPT-4.5 = 0%, Llama 4 = 0%. ARC-2 exposes that the 2024 pivot to test-time compute has not yet solved compositional novel reasoning.

---

## The 2024 Shift: Test-Time Adaptation

In 2024, the field pivoted from pretraining scaling to test-time compute. Chollet's characterization: "test-time adaptation — creating models that could change their own states at test time to adapt to something new." This represented a paradigm shift from "querying preloaded knowledge" to "the ability to learn and adapt at inference time."

Key techniques: test-time training (fine-tuning on the specific task at inference), program synthesis (writing a program to solve the task), and chain-of-thought reasoning ("the model tries to reprogram itself for the task at hand"). The chain-of-thought framing is interesting — Chollet reads CoT not as retrieval of memorized reasoning but as a form of test-time self-modification.

This pivot is the reason o3 achieved 87% on ARC-1 — it uses extended test-time search, not just next-token sampling. At 50,000x more compute than a standard call.

---

## The Kaleidoscopic Hypothesis

"Our experience of the world seems to feature a never-ending novelty and complexity, but the number of unique atoms of meaning that you need to describe it is actually very small. And everything around you is a recombination of these atoms."

Intelligence involves mining experience to identify "abstractions" — reusable building blocks that can be flexibly recombined to address novel situations. The world is not infinitely complex; it is a small vocabulary of primitives in infinite combination. The intelligence task is to identify the vocabulary (learn the atoms) and then use them combinatorially (program synthesis).

---

## Type 1 vs. Type 2 Abstractions — The Critical Taxonomy

This is Chollet's most technically load-bearing claim:

**Type 1 (Value-centric):** Operates on continuous domains via distance functions. Underlying mechanism: metric/similarity. Examples: perception, pattern recognition, intuition. Modern machine learning (transformers, CNNs) is fundamentally Type 1. Type 1 is what deep learning does well.

**Type 2 (Program-centric):** Operates on discrete programs/graphs via exact structure matching — subgraph isomorphisms. Underlying mechanism: structural identity. Examples: human reasoning, software engineering, formal mathematics. "Transformers are great at type one abstraction...but they're still not a good fit for type two."

Humans excel precisely because they combine both: Type 1 provides fast pattern recognition (intuition), Type 2 provides slow reasoning (deliberation). Current AI is strong at Type 1, weak at Type 2.

---

## Discrete Program Search

The solution for Type 2 reasoning: "discrete program search — commutative search over graphs of operators from a domain-specific language." Rather than gradient descent on continuous spaces, the system searches through a space of discrete programs, guided by learned intuition.

The fundamental difficulty: "program synthesis is extremely data efficient...the size of that space grows combinatorially with problem complexity." You don't need many examples to induce a program from them — but finding the program requires searching an exponentially large space. Current approaches: genetic algorithms, beam search, MCTS over program spaces. Historical examples Chollet cites: genetic algorithms for antenna design, AlphaGo's Move37, DeepMind's AlphaEvolve — "all discrete search systems."

---

## The Path to AGI: Meta-Learning Systems

Chollet's proposed architecture: "AI is going to move towards systems that are more like programmers that approach a new task by writing software for it."

The architecture:
- Deep learning modules for Type 1 sub-problems (perception, pattern matching)
- Algorithmic modules for Type 2 reasoning (discrete program operations)
- Discrete program search guided by learned intuition (the DL component informs the search)
- A global, evolving **library of reusable abstractions**: "When a new problem appears, the system is going to search through this library for relevant building blocks...uploading new ones back to the library"

This library is the analogue of open-source software: a growing, shared vocabulary of abstractions that each task contributes to and draws from. The system improves continuously as it encounters more tasks — not by retraining the base model, but by growing the abstraction library.

Meta-learning is the key: the system learns how to learn, not just how to perform specific tasks.

---

## Exact Numbers

- 50,000x scale-up of base LLMs (2019–2025): ARC-1 performance = ~10%
- Human ARC-1 performance: ~85%
- GPT-4 class models on ARC-1: 0–10%
- o3 on ARC-1 at 50,000x compute: ~87%
- ARC-2 (March 2025): GPT-4.5 = 0%, Llama 4 = 0%
- o3 cost for 87% ARC-1: extreme compute, not production-viable

---

## VERSO RELEVANCE

### [CONFIRMS §5.1 — Loop]
Chollet's test-time adaptation framing directly validates Verso's tactical-vs-durable seam. The tactical agent loop is a test-time computation: it runs, adapts to what it observes, and produces an output. The durable layer is a learned abstraction library: checkpointed state, accumulated knowledge, learnable behavior across runs. Chollet's architecture separates "what you know before the task" from "what you figure out during the task" — exactly the Verso seam. No graph required; just the ability to checkpoint mid-run and resume.

**One-line verdict:** Chollet's test-time adaptation = the theoretical basis for Verso's tactical loop; his abstraction library = the theoretical basis for the durable layer.

### [SHARPENS §5.5 — Evals]
ARC-AGI as a design principle for Verso evals: the right eval presents genuinely novel tasks that cannot be solved by memorization or pattern-matching against training data. A Verso eval suite should include at least some tasks the model has never seen (synthesized from templates, randomized parameters, novel tool combinations). If every eval can be solved by matching against training distribution, the eval is not measuring generalization — it is measuring recall. Define_outcome(bounded) should include novelty as a property of the task, not just the answer.

**One-line verdict:** eval tasks should be novel-by-construction to test fluid intelligence, not crystallized skill.

### [CONTRADICTS §2 — Non-Goals / positioning]
Chollet's Type 1/Type 2 distinction creates a challenge for Verso's "no graph" positioning. Type 2 reasoning (discrete program search over structured spaces) benefits from explicit graph representations — the search space IS a graph. If Verso's tactical agents need to perform multi-step symbolic reasoning or program synthesis, the "no graph" constraint may force them to approximate Type 2 reasoning with Type 1 tools (transformer-based chain-of-thought), which Chollet explicitly says is suboptimal. Verso should acknowledge that its sweet spot is Type 1-dominated tasks and frame the graph demurral as a product choice, not a fundamental claim about all reasoning.

**One-line verdict:** "no graph" works for retrieval/generation/tool-use agents; may be a constraint for agents doing symbolic reasoning or program synthesis.

### [NEW-IDEA — §5.4 — Memory]
The "evolving library of reusable abstractions" is a concrete memory architecture: not key-value retrieval from past episodes, but a curated vocabulary of reusable program fragments. For Verso, this suggests a memory tier between episodic (past runs) and semantic (background knowledge): **procedural memory** — a library of reusable agent subroutines (mini-programs for common task patterns) that the agent can retrieve and compose. Each successful run deposits new subroutines into the library. This is above the 4-tier typed memory already designed but is a distinct tier with distinct update semantics (structured, versioned, composable rather than narrative or vector-embedded).

**One-line verdict:** procedural memory (reusable subroutines, versioned) is a missing tier between episodic and semantic memory.

### [SHARPENS §12 — Positioning]
Chollet's skill-vs-intelligence distinction is Verso's sharpest positioning argument: the typical agent framework competition is about skill delivery — how efficiently can the agent perform the tasks it was trained for? Verso's competition should be about intelligence delivery — how efficiently can the agent handle tasks it was NOT prepared for? The tactical loop + durable seam + evals-first stack is what enables the jump from skill execution to intelligent adaptation. This is the positioning angle: Verso agents get better at novel tasks, not just faster at familiar ones.

**One-line verdict:** Verso's competitive moat is test-time adaptability (Chollet's intelligence), not task-specific performance (his skill).
