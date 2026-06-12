# Sparks of AGI: Early Experiments with GPT-4

**Speaker**: Sébastien Bubeck (Senior Principal Research Manager, Machine Learning Foundations, Microsoft Research)  
**URL**: https://www.youtube.com/watch?v=qbIk7-JPB2c  
**Duration**: 49m  
**Venue**: MIT (March 22, 2023), also published as arXiv:2303.12712 (155 pages)  
**Status**: read_partial — no verbatim transcript found. Content reconstructed from: (1) Microsoft Research podcast interview with Bubeck; (2) NextBigFuture detailed talk summary with timestamps; (3) Temple University/TAGIT paper review PDF; (4) arXiv abstract; (5) news coverage with direct Bubeck quotes. The YouTube video exists but no caption/transcript file was located via search.

---

## What Bubeck Actually Argues

### The Evaluation Problem: Why Benchmarks Fail

Bubeck's opening move is to invalidate standard ML benchmarking for GPT-4. Classical benchmarks fail for two reasons:

1. **Training contamination**: GPT-4 likely saw benchmark test sets during pretraining, making held-out accuracy meaningless.
2. **Ceiling effects**: GPT-4 already surpasses bar exams, medical licensing exams, and most academic benchmarks — the instrument is too coarse.

His alternative: **probe for the capability surface qualitatively, breadth-first, hunting for limits**. The methodology is borrowed from psychometrics: use the 1994 consensus definition of intelligence from 52 psychologists ("Mainstream Science on Intelligence") as the evaluation rubric, then test whether GPT-4 matches it domain by domain.

> "We have to test the generative abilities, the interaction abilities." — Bubeck (Microsoft Research podcast)

### The Unicorn in TikZ (Talk Section ~22:13)

The pivotal moment in the talk. Bubeck asked GPT-4 to draw a unicorn using TikZ (a mathematical vector graphics programming language). No unicorn in TikZ format exists on the internet to pattern-match against. GPT-4 produced a program that rendered a recognizable unicorn.

Bubeck's interpretation: "And then, suddenly, with GPT-4, it was kind of clear to me in that moment that it really understood something. It really understands: 'What is a unicorn?'"

This is the empirical crux of his emergence argument: the model demonstrated genuine concept representation, not retrieval. For contrast, Stable Diffusion (a generative image model) was compared at ~27:15 — the contrast being that diffusion models retrieve/blend; GPT-4 *programs* from concept.

### Capability Surface (from paper + talk)

**What GPT-4 can do that surprised Bubeck:**
- Draw unicorns in TikZ (concept → code)
- Solve stacking problems with physical reasoning ("book, 9 eggs, laptop, bottle, nail — stack stably"): instructed to distribute eggs evenly, leave space, prevent cracking, place laptop on eggs
- Write mathematical proofs including proofs about infinite primes (~19:00)
- Pass coding interviews at or above the 100th percentile of human candidates (~32:57)
- Use tools (call Mathematica for exact math when its own arithmetic is unreliable)
- Theory of mind tests at ~10:40 and ~12:29: understanding beliefs, false beliefs, intentions

> "All of the things I thought it wouldn't be able to do? It was certainly able to do many of them — if not most of them." — Bubeck

**What GPT-4 still cannot do (limitations Bubeck identifies as likely fundamental):**
- **Long-term planning** (~42:40): cannot maintain coherent goal-directed behavior over extended horizons
- **Persistent memory**: no memory between sessions; must start from scratch each conversation
- **Real-time learning**: cannot learn new concepts without full retraining
- **Reliable arithmetic**: "it will skip a step...hallucinated that this step is not necessary" — causes errors in multi-step arithmetic despite strong symbolic reasoning
- **Novel theorem proving**: can engage with proofs but cannot independently prove new theorems

Key framing: the limitations are attributed to the **next-word prediction paradigm**, not just scale. Bubeck argues GPT-4 lacks ability to plan ahead as a structural consequence of left-to-right autoregressive generation.

### The Emergence Argument

Bubeck proposes studying emergence through physics methodology:
- Run controlled experiments
- Build toy mathematical models
- Study the "LEGO project" and "Learning Threshold Units" — research on how reasoning capabilities emerge from neural network instability during training

Critical finding on diversity vs. specialization: **adding Wikipedia to equation-solving training data produced better generalization than narrow task-specific datasets** — counterintuitive under Occam's Razor. This supports the "diverse pre-training → broad capability" thesis that undergirds modern LLM development.

### The AGI Definition Problem

Bubeck distinguishes "lowercase agi" (current GPT-4 level) from uppercase AGI. He explicitly rejects universality and optimality as requirements:

> "Intelligence has nothing to do with universality or optimality. We as human beings are notoriously not universal." — Bubeck

His lowercase-agi definition: understands diverse topics, reasons across domains, uses tools and interacts with humans, retrieves information. By this definition, GPT-4 qualifies (with caveats).

For uppercase AGI, additional requirements: persistent memory, real-time learning, goal-oriented agentic behavior. GPT-4 lacks all three.

Crucially, Bubeck notes the public GPT-4 was **deliberately "slightly dumbed down"** from the internal testing version for safety reasons — what he evaluated was more capable than what shipped.

> "We should not dissociate our futuristic goal with technical innovation." — Bubeck

---

## VERSO RELEVANCE

### [SHARPENS §5.5 evals] Probe capability surface breadth-first, hunt for limits — don't chase scores

Bubeck's evaluation methodology is directly applicable to Verso's `define_outcome(bounded)` and judge-panel design. The key insight: **capability surface probing must be qualitative and adversarial**, not benchmark-score-maximizing. For Verso's evals harness, this means the judge panel should include "break it" probes — tasks designed to find the failure mode, not confirm the success mode. The "hunt for limits" stance is the opposite of the standard eval pipeline that measures known tasks.

**No-overkill verdict**: Add one adversarial probe task per agent evaluation suite; do not build a full capability mapping system.

### [NEW-IDEA §5.5 evals / §6.3 safety] The "capability gap between testing and production" pattern

Bubeck's note that the public GPT-4 was "slightly dumbed down" from internal version for safety introduces a crucial eval discipline: **the model you eval and the model you deploy may systematically differ**. For Verso's model abstraction layer (§6.4), this means eval suites must be run against the *exact deployment artifact* — not a test model, not a smaller proxy. The capability gap between eval model and prod model can be intentional (safety), accidental (quantization, routing), or version-drift.

**No-overkill verdict**: The ModelInterface must tag the exact model version evaluated; warn if production model differs from eval model.

### [CONFIRMS §6.4 model / §12 positioning] Tool use as the remedy for next-word-prediction's planning limit

Bubeck's identification of planning as the structural failure mode of autoregressive generation is the strongest argument for **tool use + external memory** as architectural compensators. GPT-4 calling Mathematica for exact arithmetic is the canonical example: the model routes around its own unreliability by delegating to a trustworthy tool. This directly confirms Verso's `@tool` design and the "native Python @tool is THE tool path" position — tools are not convenience wrappers, they are structural compensators for model limitations.

**No-overkill verdict**: This is already confirmed in the PRD; the Bubeck evidence makes the argument stronger but requires no new PRD changes.

### [SHARPENS §5.1 loop / §6.1 durable] Lack of persistent memory is the most concrete AGI gap

Bubeck explicitly lists "no memory between sessions" as a primary limitation. For Verso, this means the tactical ↔ durable seam (§4) is not just a convenience feature — it is **the architectural fix for the gap Bubeck identified in 2023**. An agent that retains cross-session memory (via the durable layer) closes the most concrete capability gap between GPT-4-era agents and more general systems.

**No-overkill verdict**: The durable layer's value proposition should explicitly include "closes the stateless session boundary that limits current LLMs."

### [NEW-IDEA §5.2 context] Diversity in training data → better generalization; applies to context curation

Bubeck's finding that adding Wikipedia to math training improved generalization (diversity > specialization) has a direct analogue for context engineering: **injecting diverse context types into the window may improve reasoning even when they seem off-topic**. This challenges the pure relevance-maximizing retrieval approach. Some noise from adjacent domains may be beneficial.

**No-overkill verdict**: Speculative; needs empirical validation. Flag as hypothesis for Verso evals team, not a PRD change.

---

## Verdict

No full transcript found; reconstructed from 5 secondary sources including a detailed timestamp-keyed summary. Content is substantive: Bubeck's eval methodology (probe for limits, not benchmarks), the TikZ unicorn as capability evidence, planning-as-structural-failure, and the persistent memory gap all have direct Verso relevance. The most actionable finding is the "eval the exact deployment model" discipline (capability gap between testing and production).
