# No Priors: State Space Models with Cartesia's Albert Gu & Karan Goel

**Source:** No Priors Podcast, Episode 70 (June 27, 2024)
**Guests:** Albert Gu and Karan Goel, co-founders of Cartesia AI
**URL:** https://www.youtube.com/watch?v=neQbqOhp8w0
**Transcript location:** https://podscripts.co/podcasts/no-priors-artificial-intelligence-technology-startups/state-space-models-and-real-time-intelligence-with-karan-goel-and-albert-gu-from-cartesia
**Duration:** 34 minutes
**Status:** read_partial (podscripts transcript lightly OCR'd; supplemented by Cognitive Revolution full episode with Gu + Mamba-3 blog post + Index Ventures writeup)

---

## Speaker Backgrounds

Albert Gu completed a long PhD at Stanford focused on sequence modeling. He describes drifting away from dominant approaches: "instead of working on them, I got really interested in these alternate kind of recurrent models." He is the inventor of HiPPO (2020), S4, and Mamba.

Karan Goel grew up in India, came from an engineering family, did Stanford grad school starting in reinforcement learning, then pivoted toward the SSM research that Gu was pioneering. They met at the Stanford AI Lab and co-founded Cartesia in 2023.

---

## Core Technical Arguments

### 1. The Quadratic-vs-Constant Asymmetry

The fundamental architectural claim is about inference-time cost:

> "One of the big advantages of these alternatives is the linear scaling... the time it takes to process any new token is basically constant time for a recurrent model. But for a transformer, it scales with the history."
> — Albert Gu, No Priors Ep. 70

Transformers maintain a KV cache that grows with every new token — quadratic cost as context length increases. SSMs maintain a **fixed-size state** and discard raw tokens after compression. This is what Cartesia's Mamba-3 paper later called the "inference-first" property: "intelligence should be natural enough to interact with in real time."

The consequence: SSM inference cost does not grow with conversation length. For applications requiring long-running streaming (voice agents, continuous sensor processing), this gap becomes structural.

### 2. "Fuzzy Compression" vs. Exact Recall

Gu uses the analogy of memory: SSMs do "fuzzy compression" — they strip unnecessary detail while keeping what matters. This is a feature, not a bug, for compressible modalities (audio, video). It is a genuine limitation for tasks requiring exact lookup (e.g., retrieving a specific fact from a long document).

Acknowledged trade-off (from Mamba-3 blog, authored by Gu): "There is no free lunch. That same constraint forces models to compress all past information into one representation, fundamentally limiting retrieval capabilities. Linear models naturally underperform Transformers on retrieval tasks."

The honest framing: SSMs win on compression, lose on recall. This is why hybrids exist.

### 3. The 10:1 Hybrid Architecture

Both the podcast and later Cartesia research converge on a ~10:1 SSM-to-attention ratio as optimal:

- ~10 SSM layers handle sequential compression and long-range memory
- ~1 attention layer handles exact associative lookup (dictionary-style retrieval)

Described as: "fuzzy compression where it helps, exact lookup where it matters."

Evidence from the Cognitive Revolution episode with Gu: "Evidence suggests roughly 1 attention layer per 8-12 state space layers optimizes complementary strengths. Attention excels at associative recall (dictionary-like lookups); SSMs handle sequential compression."

Gu: "I'm not completely sure myself at this point" regarding what expressivity trade-offs in Mamba 2 mean practically — intellectual honesty about active unknowns.

### 4. Domain-Specific Fit: Audio/Video vs. Text

Karan on where SSMs dominate: "for audio and video, which are highly compressible, SSMs are much better and more scalable." High sampling rates create redundancy — SSMs can exploit this. Text is information-dense and tokenized, where transformer attention still has advantages.

The product manifestation: Sonic, Cartesia's text-to-speech engine, achieved **135ms model latency** at launch — significantly faster than existing TTS alternatives. Use cases: voice agents requiring real-time response, interactive gaming NPCs.

Quality bar Karan sets: "The way I think about it is, like, would I want to talk to this thing for more than 30 seconds? And if the answer is no, then it's not solved."

### 5. Edge / On-Device Vision

The longer-term thesis: "constant-time steps that run on a phone or laptop." Because state size is fixed, the memory and compute footprint doesn't balloon with session length. Cartesia's mission framing: "enduring intelligence" — long-lived, stateful models that run anywhere without cloud dependency.

Karan: "Not only do these models lack the depth of understanding that humans possess, they're slow and computationally expensive in a way that restricts their development and use to only the largest companies."

### 6. Research Philosophy

Gu on how he picks problems: "How do I treat my research problems? And I can't explain. My answer is just aesthetic... there's something I find elegant and aesthetically pleasing about things." The SSM lineage — HiPPO → S4 → Mamba → Mamba 2 — emerged from this aesthetic pull toward theoretical grounding with empirical surprise.

---

## Mamba Architecture Mechanics (from Cognitive Revolution deeper interview)

- **Core innovation (Mamba 1):** Input-dependent gating. The decay factor depends on input values, allowing the model to "skip over" irrelevant tokens (filler words) by keeping state unchanged.
- **Mamba 2:** Blocks of state elements decay together rather than independently. Reduces granularity from per-element to per-chunk. Enables matrix multiplications during training by rewriting the forward pass to avoid materializing states. Trade-off: modest expressivity reduction for large training efficiency gain.
- **Mamba-3:** "Inference-first" philosophy. Prioritizes deployment efficiency over training-time tricks, motivated by RL/agent workloads pushing "inference demand through the roof."

---

## VERSO RELEVANCE

### [SHARPENS §6.4 — Model Layer]
**The 10:1 hybrid ratio and the "inference-first" framing are directly relevant to Verso's model-agnosticism layer.** If Verso's `iter_model_stream` and cross-model failover needs to accommodate hybrid SSM architectures, the constant-time-per-token property changes how the harness should think about streaming: no KV-cache growth means longer sessions don't accumulate cost in the same way. Verso's context compaction logic (observation-masking at N=10) was designed for transformer attention economics; SSM backends may need a different compaction heuristic — or compaction may be less urgent for SSM-backed steps.
**Verdict:** Sharpen §6.4 with a note that SSM/hybrid backends change the streaming cost model; don't over-engineer for transformer assumptions.

### [NEW-IDEA — §5.2 Context / §6.4 Model]
**Stateful streaming as substrate for durable agents.** Gu's "constant-time steps" and fixed-size state are exactly the property you want in a long-running durable agent: the model doesn't accumulate unbounded context. Verso's durable layer currently relies on checkpoint/resume to manage state — but an SSM-native backend could maintain rolling state natively without explicit compaction. This is a future-facing architecture point: design the durable model interface so that a "stateful backend" can plug in without forcing compaction-on-every-step.
**Verdict:** Flag as future-facing §6.4 extension; don't build now, but don't foreclose it.

### [CONFIRMS §5.2 — Context Engineering]
The "fuzzy compression" framing confirms that lossless context preservation is not achievable at inference — every model (including transformers with attention) has a bounded effective window. Verso's observation-masking compaction strategy is correct in principle: compress early observations aggressively, preserve recent and task-critical context. SSMs make this explicit architecturally.
**Verdict:** Confirms existing design; no change needed.

### [SHARPENS §5.3 — Tools / Voice]
Sonic at 135ms model latency at 34-minute podcast date (June 2024) validates that SSM-backed voice is now production-grade for real-time agent voice loops. If Verso ever exposes a voice transport layer, SSM-based TTS is the correct backend choice. The Karan quality bar ("would I talk to this for more than 30 seconds?") is a useful UX benchmark for any voice-loop Verso might wrap.
**Verdict:** Informational for §5.3; relevant if Verso adds voice transport.
