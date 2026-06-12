# Mikey Shulman (Suno): The Future of Music

**Source:** https://www.youtube.com/watch?v=E0YL83U5VWk  
**Also published as:** 20VC E1244 (Harry Stebbings), Jan 10 2025, ~58 min  
**Speaker:** Mikey Shulman, co-founder/CEO Suno  
**Transcript status:** No official transcript found. Content synthesized from:
- Latent Space "Making Transformers Sing" interview (latent.space/p/suno) — highest-quality source, closest to verbatim
- Sequoia Capital "Training Data" podcast summary (sequoiacap.com/podcast/sunos-mikey-shulman-everyone-can-make-music-now/)
- Amplify Partners interview (amplifypartners.com/barrchives/how-suno-builds-ai-models-for-musicians)
- horsy.ai summary of the 20VC episode
The Latent Space and Sequoia sources are substantively detailed; quotes below are drawn from those.

---

## Core Arguments

### 1. Autoregression Over Diffusion — Product-First Decision

The most important architectural choice Suno made was to use autoregressive transformer models (predicting the next token, sequentially) rather than diffusion models. This was explicitly a **product decision, not a raw capability decision**:

> "Diffusion produces crisp, brief audio clips (~10-12 seconds). Autoregression enables full 3-3.5 minute songs that 'tell a story.'"

Shulman's framing (Sequoia source):
> "A song is a story, and captivates you in a way that vocal-less background music just won't."

Diffusion competitors had better audio quality per second in early head-to-head comparisons. Suno accepted that tradeoff because song-length narrative coherence was the product. The bet: users want to *feel something*, not optimize for acoustic fidelity on a 10-second clip.

The Amplify source adds the mechanism:
> Autoregressive models "figure it out bit by bit, which tends to make for more interesting music," whereas diffusion generates "elevator music that's a little boring."

### 2. Raw Audio Modeling — Refusing to Pre-Constrain the Problem

Suno models raw audio waveforms, not music-theoretic abstractions:

> "It's just a sound wave. It's just sampled at 48,000 times a second, and it is a continuous float 32 number."

Why this matters — if you encode the problem as "12 tones" you get:

> "If you tell the model there are 12 tones, it will only ever produce those 12 tones. You will be forever limited."

This enables microtonal music, unexpected genre fusions (trap with sitar, country with 808s), and outputs the training data never explicitly showed. The tokenization work — converting continuous audio to discrete tokens — is described as the core R&D focus:

> "We focus very hard basically on how do I tokenize audio in the right way."

Multi-domain training (not just music — non-music human speech helps vocal realism) follows the Code Llama analogy: English alongside code. Shulman acknowledges: "we've barely scratched the surface of what are the right ways to do this."

### 3. Why Music Isn't a Scale Problem Like LLMs

Shulman's contrarian take against the "just scale" orthodoxy:

> "Music isn't a pure scaling problem like LLMs." Model sizes remain relatively small.

Two reasons:
1. **Human preference data** provides a sustainable moat that pure compute cannot close. When the model rates two songs equally but humans prefer one, that discrepancy produces training signal that money alone cannot replicate.
2. Streaming latency is the binding constraint, not parameter count: "we need to stream you music as fast as you can listen to it." This forced architectural efficiency rather than brute scaling.

Corollary: Suno chose smaller models early on intentionally, forcing architectural innovation.

### 4. The Blank Canvas Insight — 90% Create, Not Consume

The most surprising product finding:

> "90% of daily users create something" — inverting the traditional music industry's passive consumption model.

From the Latent Space source: "more than half of the usage is expert mode" where users actively tweak lyrics, rhythm, and style.

Two emergent use cases:
1. **Rapid creation:** "nice shit posting" — songs about immediate moments, created in seconds
2. **Deep iteration:** repeated refinement until the internal song the user heard in their head materializes

Shulman's insight on why creation IS the product:

> "The creation, is actually the entertaining bit."

The gaming analogy: gaming is "50 times bigger than the music industry" because it is active participation. Suno targets converting passive listening to active creation — expanding the total addressable market rather than optimizing professional workflows.

### 5. Industry Positioning — Two Worlds Would Be a Mistake

Shulman explicitly avoids the "AI covers" path (Artist A performing Artist B's songs):

> "This stuff is very viral, but I actually really don't think that this is how people want to interact with music in the future."

The vision: original generative compositions, not remix/imitation. On the industry's future:

> "It would be a real shame if there were two worlds of music, if there were an AI world of music and a non-AI world of music."

Revenue milestone: $300M ARR (confirmed by external reporting as of 2026).

---

## Key Quotes

> "If you tell the model there are 12 tones, it will only ever produce those 12 tones. You will be forever limited."

> "A song is a story, and captivates you in a way that vocal-less background music just won't."

> "People are creating music for the fun and enjoyment and fulfillment that comes with being creative."

> "The creation, is actually the entertaining bit."

> "We need to stream you music as fast as you can listen to it."

---

## VERSO RELEVANCE

### [NEW-IDEA §4 seam / §5.1 loop_harness]
**Finding:** Shulman's autoregression-over-diffusion decision is a **product-constraint-drives-architecture** choice, not a research choice. They accepted worse per-second audio quality to get full-song coherence because the product is a song, not a clip. Applied to Verso: the tactical-vs-durable seam decision should be made the same way — accept the constraint that serves the product (simple loop for tactical, checkpoint resume for durable) rather than chasing a single unified architecture that tries to optimize everything. The "elevator music" failure mode (diffusion = technically correct but missing the point) is a warning against architectures that optimize the wrong metric.
- **Verdict:** Sharpens the seam argument — product outcome (full-song / long-running durable agent) must drive the architecture choice, not capability benchmarks.

### [NEW-IDEA §5.5 evals / §12 positioning]
**Finding:** Suno's training signal comes from the *gap* between model-rated parity and human preference — a natural eval loop embedded in production. When the model cannot distinguish two outputs but users systematically prefer one, that discrepancy trains taste. This is embedded-in-production evals by another name. Verso's `define_outcome(bounded)` + judge-panel is the agent-framework equivalent: you can only train (or trust) the loop on outcomes that humans can judge and the model cannot trivially rank.
- **Verdict:** NEW-IDEA — production-preference gaps as primary eval signal; reinforces Verso's judge-panel approach but adds the specific mechanism of *model-rated ties that humans break*.

### [SHARPENS §12 positioning / strategy]
**Finding:** "90% create, not consume" inverts the expected user behavior. For Verso, this is a reminder that the agent framework user (a developer) is also primarily a *builder*, not a runner. Verso's primary user runs the loop to build something, not to passively consume agent outputs. The DX (developer experience) of the framework is the creative surface — analogous to Suno's expert mode where users tweak. Verso's embedded evals and RunContext.inspect() are the "expert mode" of agent frameworks.
- **Verdict:** Sharpens developer-centric UX design — the builder is the primary user, not the end-consumer.

---

## Honesty Note
The 20VC episode itself (YouTube link / libsyn) had no accessible transcript. The Latent Space and Sequoia sources are from different interviews with Shulman but cover consistent technical ground. Some quotes may be from the Latent Space interview rather than the specific 20VC episode. The technical architecture claims (autoregression, tokenization, raw audio modeling, 90% creation stat) appear consistently across multiple independent sources. Status: **read_partial** (substantive multi-source synthesis, not the exact 20VC episode transcript).
