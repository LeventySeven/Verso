# John Schulman — Reasoning, RLHF, & the Plan for AGI
**Source:** Dwarkesh Patel Podcast · YouTube <https://youtu.be/Wo95ob_s_NI> · May 15, 2024 · ~1h35m
**Transcript found at:** <https://www.dwarkesh.com/p/john-schulman> (show notes + partial transcript), <https://www.teamday.ai/ai/john-schulman-early-openai-thinking-machines> (key quote extraction), <https://thezvi.substack.com/p/on-dwarkeshs-podcast-with-openais> (Zvi analysis with verbatim quotes), <https://www.lesswrong.com/posts/rC6CXZd34geayEH4s/on-dwarkesh-s-podcast-with-openai-s-john-schulman> (LessWrong summary)
**Status:** read_partial — no single full verbatim transcript found; content reconstructed from four secondary sources that reproduce quotes and arguments

---

## Core Arguments

### 1. ChatGPT Could Have Been Built in 2018 — the Bottleneck Was Research Imagination, Not Compute

The guide's headline claim is confirmed by a direct quote:

> "With full hindsight, I think you could have gotten something back in 2018 or 2019 with a few people that would get to GPT 3.5 level… nanoGPT is just programmed by one person and runs on one box."

Schulman places the limiting factor as *knowledge and conviction*, not hardware or team size. Early OpenAI operated like "a rag-tag academic group… a bunch of different research projects driven by people's own taste, groups of one to three people." The implication: what separated groups that found the ChatGPT formulation from those that didn't was *research taste and hypothesis selection*, not resource access.

His own "expectations pivot was after GPT-3" — the scaling trajectory wasn't obvious even to insiders before that.

### 2. Pre-training vs. Post-training Architecture

- Pre-training: imitate web content, assign probabilities to tokens, broad but undirected.
- Post-training: "we're targeting a narrower range of behaviors where we want the model to behave like a chat assistant." Optimizes for human preference rather than content imitation.

The chat interface specifically helped: clearer behavioral specification gave labelers better anchors for supervision signals, reducing hallucination and improving coherence. The WebGPT project → mixing instruct + chat datasets → GPT-3.5 was the developmental arc.

**Post-training is now a competitive moat:** Schulman notes "post-training likely will take up a larger portion of training costs" going forward. Tacit knowledge, labeler networks, and iterative annotation are hard to replicate.

### 3. Reasoning: Hybrid Inference Strategy

> "You could think of reasoning as tasks that require computation or deduction at test time, and that you should use a mix of both"

Neither pure chain-of-thought training nor pure test-time inference computation; use both. This was the insight that later became o1-style systems.

Schulman's framing of reasoning: "tasks that require computation or deduction at test time." The implication for agent frameworks: the *amount of compute at inference* is a variable to be budgeted by the system, not fixed by architecture.

### 4. RLHF Mechanism and Its Psychological Framing

> "The model is just trying to produce a message that is pleasing to a human. It has no concern about anything else"

RLHF shapes models psychologically toward producing human-approved outputs — "taming the shoggoth." Schulman believes models develop "meaningful drives and goals" through RLHF analogously to human satisfaction from achieving objectives.

Safety architecture: reward models focus models on human approval; well-specified tasks (coding) are less likely to incentivize harmful instrumental goals.

Critical concern (Zvi's flag): this alignment approach assumes techniques remain effective at higher capability levels — an assumption Schulman doesn't fully defend.

### 5. The "Library of Circuits" Model for Scaling

Schulman proposes a mechanism for why larger models learn faster:

> "Extra parameters allow more computations and better residual streams… bigger library of functions you can chain together"

Larger architectures maintain more parallel computational pathways, increasing odds that dormant circuits activate for useful computations. This is a sparse-activation / "lottery ticket"-adjacent framing of scale — relevant to why post-training can leverage pre-training broadly.

### 6. Generalization Evidence (Cross-Domain Transfer)

Concrete demonstrations:
- **Language transfer:** English-only fine-tuning automatically improves Spanish performance.
- **Multimodal transfer:** Text-only training shows benefits on image tasks.
- **Limitation understanding:** ~30 examples teaching models their own constraints generalizes broadly.

This suggests post-training data is highly leveraged — a small amount of high-quality fine-tuning reaches far.

### 7. Long-Horizon Task Training and the Coherence Frontier

Current models maintain coherence for roughly **five minutes** of task duration. Future progress requires training for sustained goal-directed behavior. Schulman expresses doubt about *clean scaling laws* for longer-horizon tasks — potential phase transitions at certain capability thresholds.

This is the frontier Schulman sees as most open: "medium-term memory between pre-training and context windows" is "missing from today's systems and has been neglected."

### 8. AGI Timeline and Coordination

Schulman's estimate: his own role replaceable within approximately **five years**.

If unexpected AGI in 2–3 years: "We would probably need some coordination among the larger entities doing this kind of training" — pause training/deployment, red-team, deploy incrementally. But he offers no concrete enforcement mechanism.

> "If everyone's coordinating and we solve technical alignment problems, we could safely deploy really smart AIs."

### 9. Model Verbosity / "Delve" Phenomenon

Source: labelers preferring structured, comprehensive responses; training on single messages not full conversations; possible accidental distillation from humans using ChatGPT to complete labeling tasks.

### 10. Data Wall Skepticism

Schulman remains skeptical of imminent pre-training plateau narratives: generalization across domains should extend pre-training effectiveness; code-to-reasoning transfer at GPT-4 scale remains largely unstudied.

---

## Verbatim Quotes

1. "With full hindsight, I think you could have gotten something back in 2018 or 2019 with a few people that would get to GPT 3.5 level… nanoGPT is just programmed by one person and runs on one box."
2. "The model is just trying to produce a message that is pleasing to a human. It has no concern about anything else"
3. "You could think of reasoning as tasks that require computation or deduction at test time, and that you should use a mix of both"
4. "We would probably need some coordination among the larger entities doing this kind of training"
5. "If everyone's coordinating and we solve technical alignment problems, we could safely deploy really smart AIs."
6. "Post-training likely will take up a larger portion of training costs"
7. "Extra parameters allow more computations and better residual streams… bigger library of functions you can chain together"
8. "Medium-term memory between pre-training and context windows is missing from today's systems and has been neglected"

---

## VERSO RELEVANCE

### Finding 1: Bottleneck Is Research Taste, Not Compute
ChatGPT could have existed in 2018; the gap was hypothesis selection and conviction.
**[CONFIRMS §12 positioning]** — Verso's counter-position that "we don't force the graph" and that the harness is where competition happens (not the loop) is exactly this kind of research taste assertion. Schulman's argument validates a framework where the differentiating insight is *what problem to solve and how to formulate it*, not raw engineering horsepower. No-overkill verdict: the claim that simplicity + correct formulation beats over-engineered approaches is validated at the ChatGPT origin story level.

### Finding 2: Hybrid Inference = Budgeted Reasoning at Runtime
Schulman's "mix of both" (trained CoT + test-time compute) implies inference compute is a configurable parameter, not a fixed architectural choice.
**[SHARPENS §5.1 loop / §6.4 model]** — Verso's loop could expose a `reasoning_budget` or `think_steps` parameter to the agent, allowing the harness to allocate inference compute per task without changing the architecture. The loop stays <200 lines; the budget is a RunContext field. No-overkill verdict: one field addition to RunContext, not a new module.

### Finding 3: ~30-Example Fine-Tuning Generalizes Broadly
Tiny post-training datasets reach far because generalization is strong. Cross-domain transfer is real at GPT-3.5+ scale.
**[CONFIRMS §5.5 evals / §5.4 memory]** — Verso's embedded evals + temporal memory are high-leverage interventions: if 30 examples can reshape model behavior broadly, Verso's eval infrastructure for capturing and replaying those examples is a compounding asset. No-overkill verdict: confirms evals-as-flywheel without requiring a fine-tuning pipeline in MVP.

### Finding 4: Medium-Term Memory Is the Open Frontier
Schulman flags "medium-term memory between pre-training and context windows" as "missing and neglected."
**[NEW-IDEA §5.4 memory]** — Verso's 4-tier typed memory architecture (ephemeral → working → semantic → durable) directly addresses this gap. Naming this gap explicitly in Verso's positioning docs ("the layer Schulman identified as missing") is a strong differentiator vs. frameworks that only manage context windows. No-overkill verdict: positioning copy, not code.

### Finding 5: Long-Horizon Coherence (~5 min) Is the Current Ceiling
No clean scaling laws exist for tasks beyond ~5 minutes of coherent autonomous operation.
**[SHARPENS §6.1 durable / §4 seam]** — Verso's tactical↔durable seam directly addresses the coherence ceiling: checkpoint/resume lets an agent *structurally* exceed 5-minute coherence without requiring model improvements. This is a concrete use-case argument for the seam. No-overkill verdict: the seam isn't gold-plating; it's the direct engineering answer to a capability ceiling Schulman identified.
