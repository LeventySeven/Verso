# Optimizing AI Inference at Character.AI

**Source:** https://blog.character.ai/optimizing-ai-inference-at-character-ai-2/  
**Authors:** Character.AI Engineering Team  
**Published:** June 20, 2024  
**Status:** read_full  
**Themes:** context, model, loop_harness

---

## Faithful Digest

### The Scale Claim

Character.AI serves more than **20,000 inference queries per second** — roughly 20% of Google Search request volume (~105,000 QPS per Statista 2024). The explicit comparison to Google Search is deliberate: this is the proof that consumer AI at social-media scale is real, and that inference optimization is not academic.

**"We have reduced serving costs by a factor of 33 compared to when we began in late 2022."**

**"Today, if we were to serve our traffic using leading commercial APIs, it would cost at least 13.5X more than with our systems."**

These two numbers — 33x reduction since 2022, 13.5x cheaper than commercial API — define the stakes. This is the literal economic proof that the moat is the serving system, not the weights. A framework that forces API passthrough faces this cost ceiling.

### Memory-Efficient Architecture: KV Cache Reduction >20X

The core bottleneck for LLM inference throughput is KV cache size — it determines max batch size and dominates I/O cost on attention layers. Character.AI achieved >20X KV cache reduction without quality regression through three stacked techniques:

**1. Multi-Query Attention (MQA)**  
Adopted from Shazeer (2019). Reduces KV cache by **8X** compared to Grouped-Query Attention used in most open-source models. This is the single biggest lever.  
> "We adopt Multi-Query Attention (Shazeer, 2019) in all attention layers. This reduces KV cache size by 8X compared to the Grouped-Query Attention adopted in most open source models."

**2. Hybrid Attention Horizons (Local + Global)**  
Interleaves local attention (Beltagy et al., 2020 sliding windows, O(length) complexity) with global attention. Key finding: reducing attention horizon to **1024 tokens** on most layers has no significant impact on evaluation metrics including long-context needle-in-haystack benchmarks.  
> "In our production model, only 1 out of every 6 layers uses global attention."

This means 5 out of 6 layers are local-attention, dramatically reducing the KV cache footprint for long conversations.

**3. Cross-Layer KV-Sharing**  
Ties KV cache across neighboring attention layers, reducing size by a further **2-3X**. For global attention layers, ties KV cache of multiple global layers across blocks (since global layers dominate KV cache under long context). Cites Brandon et al. (2024) as parallel confirmation.  
> "We tie the KV cache across neighboring attention layers, which further reduces KV cache size by a factor of 2-3x."

**Combined effect:** >20X KV cache reduction. GPU memory no longer the bottleneck for large batch sizes.

### Stateful Caching: The 95% Cache Rate

This is the most operationally significant innovation for an agent framework builder to internalize.

Character.AI's users have long conversations: **"the average message has a dialogue history of 180 messages."** Continuously re-prefilling KV caches on each turn is prohibitively expensive at this history length.

The solution: an **inter-turn caching system** that stores KV values on host (CPU) memory between chat turns.

Architecture:
- Cached KV tensors organized in an **LRU cache with a tree structure** (similar to RadixAttention, Zheng et al. 2023)
- Indexed by **rolling hash of prefix tokens**
- On each new query: rolling hash calculated for each prefix, cache retrieved for **longest match**
- Enables reuse even for **partially matched messages** (not just exact prefix matches)

Deployment:
- **Sticky sessions** route queries from the same dialogue to the same server
- Small KV cache size (post-20X reduction) means each server can cache **thousands of dialogues concurrently**

**Result: 95% cache rate at fleet level, reducing inference cost further** — stacked on top of the 20X architecture gains.

> "Our system achieves a 95% cache rate, further reducing inference cost."

The total stack: 20X architecture reduction × 95% cache rate = the path to 33X cost reduction since 2022.

### Native Int8 Quantization (Training + Serving)

**"We use int8 quantization on model weights, activations, and attention KV cache."**

The critical distinction from standard practice:
> "Different from commonly adopted 'post-training quantization' techniques, we natively train our models in int8 precision, eliminating the risk of training/serving mismatch while also significantly improving training efficiency."

Most frameworks quantize after training (PTQ), which introduces a gap between the training distribution and the inference distribution. Training natively in int8 eliminates this mismatch entirely.

Character.AI built custom int8 kernels for matrix multiplications and attention.

---

## VERSO RELEVANCE

### [CONFIRMS §6.4 model/provider] The serving system IS the moat, not the weights
The 13.5X cost differential vs. commercial APIs and 33X cost reduction over 2 years are concrete proof that model weights become commodity while the serving/harness layer is where economic differentiation lives. For Verso, this confirms the strategic bet: the framework's value is in the harness, not in which model it calls. The model is interchangeable; the context management, caching, and inference orchestration are where moats form.  
**Verdict: confirm**

### [NEW-IDEA §5.2 context-engineering — HIGH VALUE] Stateful prefix caching is a first-class context primitive
The 95% cache-hit rate via inter-turn KV caching is the production proof of what KV-cache static/dynamic prefix discipline means in practice. The rolling-hash longest-match approach (RadixAttention-style) enables cache reuse even for *partially* matched messages, not just exact prefixes. This is more sophisticated than simple prefix caching and directly maps to Verso's context-engineering layer.

Concrete design implication: Verso's ContextBundle or context management layer should be designed with awareness that the order and stability of prefix content dramatically affects inference cost downstream. The "static system prompt + dynamic user content" discipline already in Verso's known harvest is correct — this article gives the production numbers proving why. But the 180-message average conversation length is new: Verso's context-engineering primitives need to handle *long* conversation histories efficiently, not just single-turn grounding.  
**Verdict: sharpen** — the 180-message average history means append-only history + compaction (observation masking) are not optional niceties; they are economic necessities at scale

### [SHARPENS §5.1 loop] 180-message average history validates append-only + compaction design
The average 180-message dialogue history at Character.AI is a concrete production benchmark for what "long conversation" means. Verso's append-only loop design + observation-masking compaction (N=10 already in harvest) is vindicated by this scale. If a framework flushes context on every turn or reconstructs from scratch, it cannot compete economically.  
**Verdict: confirm + sharpen**

### [NEW-IDEA §5.2 context-engineering] Local attention (1024-token horizon) shows most context is local
The finding that reducing attention horizon to 1024 tokens on 5/6 layers causes no quality regression (including on long-context benchmarks) is a deep architectural insight. For Verso's context-engineering design, this suggests: the most important context is recent context, and there is a strong case for tiered context management that keeps the *recent* window sharp while efficiently compressing older history. This is a design rationale for the "just-in-time retrieval" approach already in Verso's harvest — it mirrors what the architecture is actually doing.  
**Verdict: sharpen** — use as architectural justification for tiered context management

### [NEW-IDEA §6.4 model/provider] Native int8 training eliminates train/serve mismatch
Post-training quantization creates a distribution mismatch; native quantized training does not. For Verso as a framework (not a training framework), the implication is: prefer model providers who train natively in their serving precision. This is a model-selection criterion for Verso's provider abstraction layer.  
**Verdict: lock-interface-defer** — note for provider evaluation criteria

### [CONFIRMS §1 the bet] 20,000 QPS is the production scale target
The Character.AI QPS benchmark calibrates what "at scale" means: ~20K queries/second, 180 messages average per conversation. Verso's durable runtime (§6.1) must be designed with this scale in mind — not as a target, but as evidence that the design space is real.  
**Verdict: confirm**

---

## Key Verbatim Quotes

- "Today we serve more than 20,000 inference queries per second."
- "We have reduced serving costs by a factor of 33 compared to when we began in late 2022."
- "if we were to serve our traffic using leading commercial APIs, it would cost at least 13.5X more than with our systems"
- "the average message has a dialogue history of 180 messages"
- "In our production model, only 1 out of every 6 layers uses global attention."
- "Our system achieves a 95% cache rate, further reducing inference cost."
- "we natively train our models in int8 precision, eliminating the risk of training/serving mismatch"
- "With these techniques, GPU memory is no longer a bottleneck for serving large batch sizes."

---

## Technical Reference Summary

| Technique | Reduction | Citation |
|---|---|---|
| Multi-Query Attention | 8X KV cache vs GQA | Shazeer 2019 |
| Hybrid Local/Global (5:1 ratio, 1024 window) | Significant | Beltagy 2020 |
| Cross-Layer KV-Sharing | 2-3X | Brandon 2024 |
| **Combined** | **>20X** | — |
| Stateful inter-turn caching (RadixAttention-style) | **95% cache rate** | Zheng 2023 |
| Native int8 training | Eliminates train/serve mismatch | — |
| **Total cost reduction** | **33X since 2022** | — |
| **vs. commercial API** | **13.5X cheaper** | — |
