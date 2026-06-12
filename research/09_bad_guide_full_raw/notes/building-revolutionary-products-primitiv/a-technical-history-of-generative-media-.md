# A Technical History of Generative Media (Fal.ai)

**Source:** https://www.latent.space/p/fal  
**Transcript/notes found at:** https://www.latent.space/p/fal (Latent Space episode page) + https://review.firstround.com/podcast/the-pivot-that-paid-off-how-fal-found-explosive-growth-in-generative-media-gorkem-yurtseven-co-founder-and-ceo/ (First Round deep-dive) + https://sequoiacap.com/podcast/the-rise-of-generative-media-fals-bet-on-video-infrastructure-and-speed/ (Sequoia transcript)  
**Speakers:** Gorkem Yurtseven (CEO) & Batuhan Taskaya (Head of Engineering), Fal.ai  
**Format:** Latent Space podcast, ~1h15m, published September 5, 2025  
**Status:** read_full — verbatim quotes from Latent Space episode transcript and corroborating deep-dive sources retrieved.

---

## What the Speakers Actually Argue

### Why they chose diffusion over LLM serving

Gorkem explains the counterpositiong decision directly:

> "Language models is not a good business. At the time we thought, okay, we are going to be competing again...we are going to be competing against OpenAI and Anthropic."

> "The killer application of language models is search and you are competing against Google at the end."

> "With image and video models, it was a net new market. We weren't going against any incumbent."

The logic is pure counterpositioning: LLM inference is a category where Google can give the layer away free (it is core to their search defense). Diffusion inference at the time of Stable Diffusion 1.5 had no such incumbent. Fal planted their primitive in the net-new market.

The First Round interview adds the framework they used to decide: "which idea reaches $1M ARR first vs. $10M?" Generative inference won on the $10M metric. This is a disciplined "wedge vs. ceiling" test, not a vibes call.

### The technical problem: diffusion inference is categorically different from LLM serving

Gorkem on the compute binding difference (from Sequoia transcript):

> "In autoregressive LLMs, your bottleneck is how fast you can move all those giant weights...In diffusion models, you're saturating all the compute bandwidth of these GPUs."

One image at standard definition is approximately 100x the compute of a text inference call. A five-second video is "at 10,000x for a low-standard definition video." This means batch scheduling, memory management, and kernel optimization are completely different problems. LLM inference optimization (KV cache, speculative decoding, flash attention) does not transfer.

### The CUDA kernel investment and its limits

Batuhan on the kernel count:

> "We have, we have a decent amount of kernels, like over a hundred of custom kernels. This doesn't include the auto-generated ones."

> "If you consider those, you know, like we have tens of thousands of kernels, obviously. At runtime that we are running and dispatching."

Initial performance improvement:

> "You go from like 10 seconds with PyTorch at the time, there was no, not even like a torch compiled torch inductor or whatever. So you were going from 10 seconds to maybe like two seconds on the same GPU."

That is a 5x speedup over naive PyTorch on Stable Diffusion 1.5. Performance improvements range from 1.5x to 10x depending on GPU and workload.

**But Batuhan also flags the erosion dynamic:** "PyTorch is already very, very good for H100s." When newer chips (Blackwell) arrive, "you're not getting the best performance" from stock PyTorch. Fal's moat is not a permanent kernel advantage — it is being first to optimize each new architecture before the ecosystem catches up.

> "Whenever something new comes up, we are the first one to optimize it."

### The real infrastructure moat: multi-model orchestration at scale

Gorkem on the harder problem:

> "We have to be better than them at running those models, and we have to be doing all 600 at the same time."

> "We are at...35 different data centers...we built our own orchestrator...our own CDN service."

Customer usage pattern:

> "Our top 100 customers are using 14 different models at the same time...chained to each other."

The model half-life problem:

> "The half life of a top five model was 30 days."

This means cold-start management (model loading speed), intelligent memory management across 600 models, and request routing to GPU clusters with the right cached model are harder competitive moats than kernel performance, because PyTorch will eventually optimize for H100s but nobody will build a 600-model multi-tenant orchestrator for the love of it.

### Revenue trajectory and growth inflection points

The key inflection points were model-driven, not marketing-driven:
- **Stable Diffusion 1.5** → product-market fit
- **SDXL** → first $1M in revenue (fine-tuning ecosystem, LoRAs)
- **Flux** → "we reached from like 2 million to 10 million in revenue...Next month, we were at 2.8 million" — Flux was the first commercially usable, enterprise-ready model; revenue jumped from $2M to $20M in two months
- **Veo3** → text-to-video with sound; "video becoming 50% of revenue"

Overall: $2M ARR (August 2023) → $100M+ ARR (August 2024) → ~50% new revenue from video alone by 2025. Team: 20→40+ people in three months.

### Latency directly maps to engagement

A/B testing result Gorkem cites:

> "When you, when the user asks for an image...if it's slower to create, they're less engaged, they create fewer number of images."

This mirrors Amazon's page-load research. For generative media, latency is a direct revenue lever — not just a quality-of-life metric.

### Counterpositioning summary

Fal refused the LLM serving market not because they couldn't enter it but because Google can price-to-zero on that layer. They chose the net-new market (diffusion inference), wrote the custom kernels to win the early performance game, and then built the multi-model orchestration infrastructure as the durable moat. The kernel performance advantage erodes; the orchestration advantage compounds with customer workflow complexity.

---

## VERSO RELEVANCE

### [CONFIRMS §12 / strategy] Counterpositioning is the founding move, not differentiation

Fal explicitly avoided the market where Google is the terminal competitor. Verso's equivalent: avoid competing on "best agent loop" (Anthropic ships that for free) and plant the primitive in the harness layer — context engineering, evals-first, durable seam — where no frontier lab will build for the love of it.  
**Verdict:** CONFIRMS §12 positioning. "We weren't going against any incumbent" is the founding posture. Verso's version: "We're not competing on the loop; we're building the harness."

### [SHARPENS §5.5 / evals] The "model half-life of 30 days" problem is a Verso evals problem

Fal's customers chain 14 models simultaneously; any model swap in that chain can break downstream behavior. For Verso, the model half-life problem maps directly to evals: if models swap underneath agents, regressions are invisible without embedded evals. The define_outcome(bounded) + judge-panel architecture is the exact solution to the 30-day model half-life problem in agentic contexts.  
**Verdict:** SHARPENS §5.5. "Model half-life" is a concrete customer pain that makes the case for always-on evals visceral. Use this in positioning.

### [NEW-IDEA / loop_harness] The cold-start / model-caching problem has an agent analog

Fal's hardest infrastructure problem is keeping 600 models warm across 35 data centers with intelligent memory management. The agent analog: keeping tool registries, context bundles, and model configurations warm across parallel agent invocations in a multi-agent setting. The scheduling and caching problem at the harness layer is structurally identical. Verso's multi-agent layer (§6.2) should explicitly address warm vs. cold agent invocation cost — the sub-agent scheduler needs a cache-aware routing strategy.  
**Verdict:** NEW-IDEA. The "600 models, 14 simultaneous per customer" operational pattern maps onto multi-agent tool and context caching. Worth specifying in §6.2.

### [CONFIRMS §5.3 / tools] Thin, composable interfaces beat monolithic deep integrations

Fal's customers chain 14 models; Fal's job is to make each model a clean composable primitive. The equivalent Verso insight: native Python @tool is the right primitive precisely because it composes — the tool surface is thin and predictable, so chaining tools across agents (the 14-model-chain pattern) doesn't require a graph. The anti-graph position is structurally identical to Fal's anti-monolith-inference-stack position.  
**Verdict:** CONFIRMS §5.3 tool design. Thin composable primitives > deep integrated frameworks, at both the model inference layer (Fal) and the tool layer (Verso).
