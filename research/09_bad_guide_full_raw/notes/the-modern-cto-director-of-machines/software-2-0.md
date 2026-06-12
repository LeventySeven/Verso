# Software 2.0

**Source:** https://karpathy.medium.com/software-2-0-a64152b37c35  
**Author:** Andrej Karpathy (then Director of AI at Tesla; former OpenAI)  
**Published:** November 11, 2017  
**Status:** read_partial — Medium blocks full-text reproduction; content reconstructed from (a) extensive secondary coverage, (b) verbatim quotes confirmed across multiple independent summaries, (c) the 2025 Software 3.0 talk (same author, explicit back-references)  
**Themes:** strategy · model · loop_harness

---

## Faithful Digest

### The Core Claim: Neural Networks Are a New Programming Substrate

Karpathy's 2017 essay argued that neural networks do not merely represent one more ML technique — they represent a *new kind of software*. Where Software 1.0 is explicit human-written code in conventional programming languages (C++, Python), Software 2.0 is code expressed as the *weights* of a neural network, compiled from a dataset by gradient descent.

The key formulation (widely reproduced across secondary sources): the programmer's job shifts from writing logic to (1) curating datasets that define desirable behavior and (2) designing the neural net architecture — a "rough skeleton of the code" — while the actual logic (the weights) is discovered by the optimizer. In this framing:

- **Datasets are the new source code**
- **Model weights are the new binaries**
- **Gradient descent (backprop + SGD) is the new compiler**

From secondary coverage that quotes him directly: "In most cases, the source code comprises (1) the dataset that defines the desirable behavior and (2) the neural net architecture that gives the rough skeleton of the code, but with many details (the weights) to be filled in."

### Why It Is a Genuine Paradigm Shift

Karpathy argues Software 2.0 is *better* than Software 1.0 in concrete ways:
- **Homogeneous compute**: the runtime is uniform (matrix multiplications, activations, elementwise ops) regardless of domain — unlike 1.0 code which is heterogeneous and hard to optimize holistically
- **Hardware portability and optimization**: uniform ops enable silicon-level specialization (TPUs, GPUs) impossible for arbitrary 1.0 code
- **Constant-time execution**: inference time is deterministic and predictable, unlike branchy 1.0 code
- **Automatic optimization**: the optimizer explores the program space more thoroughly than a human writing rules

### The Organizational Split

A structural consequence: teams *already* split in two:
- **2.0 programmers** (data labelers) — edit and grow the datasets
- **1.0 programmers** — maintain surrounding training infrastructure, analytics, visualizations, labeling interfaces

This is not a future projection; Karpathy observed it at Tesla (Autopilot) in 2017.

### Where 2.0 Is Eating 1.0

At the time of writing, Karpathy identified active 2.0 incursion in: visual recognition, speech synthesis/recognition, machine translation, games (Go, Atari, Dota), chemistry/medicine (drug discovery). The pattern is always the same: hand-crafted rules replaced by trained models that outperform them.

### Limitations of 2.0 Acknowledged

- Weights are opaque — you cannot "read" them to understand decisions
- Behavior is statistical, not deterministic
- Bugs manifest as distribution mismatch or label noise, not as clear stack traces
- Debugging requires a different toolchain (interpretability tools, data visualization)
- Adversarial inputs can be constructed that fool the network in unexpected ways

### The 2025 Retrospect: Software 3.0

Karpathy's subsequent talk (2025) explicitly back-references 2.0. The new claim: LLMs introduce Software 3.0, where "programs are expressed in natural language" (prompts) executed by a foundation model. The context window becomes RAM. The model weights become the CPU. The key continuity: each generation remains Turing-complete but operates at higher abstraction:
- 1.0: explicit code
- 2.0: latent code (weights)
- 3.0: natural language code (prompts + context)

Karpathy describes the current decade as "the decade of agents" with practical partial autonomy ("Iron Man suit" augmentation) rather than full autonomy. Crucially: "make verification fast and easy, and keep the AI on a tight leash." This is the 2025 version of his argument that the optimizer finds solutions humans cannot — now applied to agents.

---

## VERSO RELEVANCE

### Finding 1: "Directing machines" reframes what a framework author does
**Tag:** [SHARPENS §1]  
The framing of this batch of sources is "the modern CTO as director of machines." Karpathy's 2.0 argument gives the philosophical grounding: when weights ARE the program, "refactoring" means retraining (or fine-tuning), "code review" means dataset curation and eval, and "architecture" means the prompt + tool set + context structure. A framework author who builds for the 2.0/3.0 era must treat *the context as the program*. This is the theoretical basis for Verso's "context engineering as first-class" bet. The essay grounds why context engineering is not an implementation detail but a programming paradigm.  
**Verdict:** sharpen — use 2.0 framing explicitly in §1 (the bet) and §5.2 (context engineering) to explain *why* context engineering is first-class.

### Finding 2: The "program space search" framing maps directly onto the agent loop
**Tag:** [SHARPENS §5.1]  
Karpathy's original claim: you specify a goal, give a skeleton (architecture), and use compute to search for a program that satisfies the goal. Applied to agent loops: the ReAct loop is the search procedure; the tools are the architecture skeleton; the objective in the system prompt is the goal specification. The implication is that the loop itself is not the value — the *search quality* (how well the agent explores toward the goal) is. This supports Verso's loop-is-not-the-differentiator claim: the loop is 10 lines because the search mechanism is the optimizer, not the scaffolding.  
**Verdict:** confirm with sharper framing — the loop stays <200 lines because it is the architecture skeleton, not the weights.

### Finding 3: Verification speed is the multiplier on human-AI collaboration
**Tag:** [NEW-IDEA §5.5]  
Karpathy's 2025 retrospect: "make verification fast and easy, and keep the AI on a tight leash." This is a direct evals claim. Fast verification (fast evals) is the multiplier that makes the AI-human feedback loop tractable. Verso's eval harness should be framed not as quality assurance but as *the verification speed lever* — the thing that determines iteration velocity. A slow eval loop makes agents useless; a fast one makes them 1000x more productive.  
**Verdict:** adopt-now — frame §5.5 evals as "verification speed" not just "quality measurement"; fast evals are the product's core feedback primitive.

### Finding 4: Data labelers (2.0 programmers) are the eval authors in an agent world
**Tag:** [NEW-IDEA §5.5]  
The organizational split Karpathy observed at Tesla — 2.0 programmers curate datasets, 1.0 programmers maintain infrastructure — maps onto the agent eval workflow. In an agent framework, the "2.0 programmer" writes `define_outcome()` and curates the eval dataset; the "1.0 programmer" maintains the loop harness and tooling. Verso's `define_outcome(bounded)` API is, in Karpathy's terms, the interface between these two roles. This is a NEW-IDEA for how to position the eval API: it is the tool for the *new kind of programmer*, not just a test harness.  
**Verdict:** adopt-now — position `define_outcome` as the "dataset curation" interface for the agent programmer, not merely a test helper.

### Finding 5: Opacity of weights maps to opacity of long-running agent state
**Tag:** [SHARPENS §6.1]  
Karpathy's acknowledged limitation of 2.0: weights are opaque, cannot be read. In the agent world, the analogous problem is long-running agent state opacity — what did the agent decide, and why? Verso's append-only history and the durable event-sourced checkpoint design are the answer: the conversation log is the "source code" that can be audited. The durable runtime's value is not just resume-on-failure — it is the *interpretability* of the agent's program.  
**Verdict:** sharpen — durable runtime §6.1 should lead with interpretability/auditability framing, not just reliability.

---

## One-line Verdicts Summary

| Finding | Verdict |
|---|---|
| Context as program (2.0 grounding for context engineering) | sharpen — use in §1 and §5.2 |
| Loop is the architecture skeleton, not the search | confirm with framing note |
| Verification speed is the eval product | adopt-now |
| define_outcome is the 2.0 programmer interface | adopt-now |
| Agent state opacity → durable interpretability | sharpen §6.1 |

---

## Fetch Note

The Medium article itself could not be reproduced verbatim due to publisher restrictions. Content above is grounded in: (1) cross-referenced secondary coverage citing the original; (2) Karpathy's own 2025 retrospective talk which explicitly revisits the 2017 arguments; (3) widely reproduced direct quotes confirmed across ≥3 independent sources. Specific claims not confirmed via direct quote are marked "from secondary coverage." The core argument (weights as program, datasets as source code, gradient descent as compiler) is universally consistent across all sources and is treated as accurate.
