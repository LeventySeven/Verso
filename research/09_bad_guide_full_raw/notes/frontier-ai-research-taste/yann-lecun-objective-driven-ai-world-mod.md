# Yann LeCun — Objective-Driven AI: Towards AI Systems That Can Learn, Remember, Reason, and Plan

**Source:** Harvard CMSA 2024 Ding Shum Lecture, March 28, 2024
**URL:** https://www.youtube.com/watch?v=MiqLoAZFRSE
**Talk length:** ~1h17m
**Speaker:** Yann LeCun, Meta FAIR / NYU
**Transcript status:** No verbatim transcript found. Content synthesized from: CMSA event page (cmsa.fas.harvard.edu/news/2024dingshum), the associated OpenReview position paper (openreview.net/forum?id=BZ5a1r-kVsf), adamjones.me blog summary, charleseldering.substack.com analysis, rohitbandaru.github.io JEPA deep-dive, and multiple secondary sources covering LeCun's consistent public arguments across 2024-2026. Verbatim quotes attributed to LeCun from dated public statements.

---

## What LeCun Actually Argues

### The Central Claim: LLMs Are a Dead End

LeCun's thesis is blunt: "Pure Auto-Regressive LLMs are a dead end on the way towards human-level AI." In November 2025 he sharpened this: "The path to superintelligence via LLMs is complete bullshit. It's just never going to work." His complaint is not capability-level (he acknowledges fluency and pattern-matching) but architectural: the autoregressive token-prediction mechanism has three fatal flaws.

**Flaw 1 — Compounding error from sequential sampling.** Each token is sampled step-by-step; if the error rate per step is e, then the probability of a correct n-step sequence is (1-e)^n. For long horizon tasks this collapses to zero. The hallucination problem "stems from the mathematics of sequential sampling, not data quality or model size."

**Flaw 2 — No internal planning.** LLMs "predict one step at a time, lacking effective long-term planning." The model is forced to produce a token at each forward pass, which "prevents purely internal information processing." It "essentially speaks without thinking" — it cannot plan an utterance at a higher level before generating tokens.

**Flaw 3 — Wrong modality / sample inefficiency.** LLMs train on text; a 4-year-old processes ~1.1×10^14 bytes through vision alone vs. LLMs' ~10^14 bytes of text. The information density of sensory experience far exceeds text. LLMs are "doomed to the proverbial technology scrap heap in a matter of years due to their inability to represent the continuous high-dimensional spaces that characterize nearly all aspects of our world."

### The Positive Proposal: Objective-Driven AI with H-JEPA

The talk proposes a modular cognitive architecture with five components:

1. **Configurable World Model (H-JEPA):** Hierarchical Joint Embedding Predictive Architecture. Trained with self-supervised learning. Does NOT predict raw pixel/token futures — instead predicts in latent embedding space. Energy-based: learns a function F(x,y) that returns low energy when (x,y) are compatible, high energy otherwise. The model learns "abstract representations simultaneously maximally informative and maximally predictable."

2. **Action Generator:** Proposes candidate action sequences (X, Y, Z).

3. **Cost Functions:** Dual objectives — one for task goals, one for safety constraints.

4. **Planning Mechanism:** Classical algorithms (A*, MCTS, gradient-based optimization) search over action sequences by minimizing predicted cost through the world model, before any action is executed. This is the System 2 reasoning layer.

5. **Memory / State:** Short-term and episodic memory referenced by the world model.

The hierarchy in H-JEPA addresses the information-predictability tradeoff: "low-level representations for short-term predictions and higher abstraction level for longer-term forecasts." This enables efficient planning because it avoids sampling in the intractably large raw observation space.

Implementations: I-JEPA (2023, vision), V-JEPA (2024, video), V-JEPA 2 (1B params, 22M videos, action-conditioned robotics planning via Cross Entropy Method at inference time).

### Key Philosophical Stance

"Intelligence is forged through visual and physical exploration, and language is primarily a tool for communication rather than the source of thought." The architecture grounds intelligence in predictive world-modeling and planning, not in language.

On career guidance: "If you are interested in human-level intelligence, do not work on LLMs."

---

## Source Quality

This note is synthesized from secondary sources and the OpenReview paper abstract — no verbatim transcript of the Harvard talk was found. The arguments are consistent with LeCun's documented public positions across 2024-2026. Treat specific quotes as from his broader public record, not necessarily from the March 28 lecture specifically.

---

## VERSO RELEVANCE

### [CONTRADICTS §5.1 / §12 — The loop-vs-graph axis, but from a different angle]

LeCun argues the fundamental unit of intelligence is a **planning loop with a world model**, not a reactive token-generator. This is orthogonal to Verso's loop design but relevant to the §12 positioning: LeCun's critique of LLMs is that they are reactive (no look-ahead). Verso's ReAct loop is also reactive at a per-step level. This is not a contradiction of Verso per se — Verso is a harness around model calls, not a new inference architecture — but it's useful ammunition: the claim that "the loop is where nobody competes" holds even in LeCun's framing, where the loop IS the differentiator (his planning loop is the whole thesis). No-overkill verdict: the LeCun paradigm is a research-level alternative inference architecture; irrelevant to Verso's product layer for the next 3-5 years, but useful for §12 to note that even critics of LLMs agree the planning/harness layer matters.

### [NEW-IDEA for §5.2 context / §5.5 evals — Energy-based "compatibility scoring" as observation filter]

JEPA assigns low energy to compatible (state, prediction) pairs. This is structurally similar to Verso's `{data, error, ok}` dispatch — but LeCun's framing suggests a **continuous compatibility score** per observation, not just a binary dispatch. A Verso analogue: score each tool-return for compatibility with the current world-model (agent goal state) before deciding whether to compact or keep it. This is a sharper version of the observation-masking compaction heuristic already in the PRD. No-overkill verdict: worth one sentence in §5.2 — "compaction candidates can be scored against goal-state compatibility, not just recency."

### [SHARPENS §12 positioning — The contrarian position you must be able to argue]

LeCun provides the strongest intellectual argument *against* the current LLM paradigm. Verso's §12 positioning assumes LLMs remain the substrate; this is a valid assumption for the 2025-2027 window but LeCun's work shows what a different architecture would look like. The value: Verso's harness design (context engineering, evals, durable seam) is **architecture-agnostic** — if the inference substrate shifts from autoregressive LLMs to world-model planners, the harness layer is still needed, possibly more so. This strengthens the "we don't bet on the model" positioning in §6.4. No-overkill verdict: one bullet in §12 — "harness investment is durable across inference paradigm shifts."
