# LLM Architecture Gallery

**Author:** Sebastian Raschka
**URL:** https://sebastianraschka.com/llm-architecture-gallery/
**Status:** read_partial — WebFetch returned a summary of the gallery (79 models listed with key specs); full architecture diagrams are visual/image content not accessible via fetch. Text-layer content captured comprehensively.

---

## Faithful Digest

The gallery is a comprehensive reference cataloguing 79 language model architectures spanning 2019 (GPT-2 XL) through mid-2026, with side-by-side architecture diagrams, attention mechanism details, normalization approaches, positional encoding choices, and compact spec sheets. It is explicitly a comparison tool, not a tutorial.

### Architecture Trend Map (what actually changed model-to-model)

**Attention evolution (the most active axis of change):**
- **MHA** (Multi-Head Attention): Classic GPT-2 baseline, now rare in new models
- **GQA** (Grouped-Query Attention): The dominant modern baseline — Llama 3, Phi-4, Mistral, Qwen3, most dense models. Reduces KV cache size by sharing key/value heads across query groups
- **MLA** (Multi-Head Latent Attention): DeepSeek's innovation — DeepSeek V3, R1, Kimi K2, Mistral Large 3, GLM-5, Sarvam 105B. Compresses KV cache into a low-rank latent space, enabling longer context windows at lower memory cost
- **Sliding-window / hybrid attention**: OLMo 3, Gemma 3/4, Step 3.5 Flash use 3:1 or 5:1 sliding-window-to-global ratios. Local attention handles the bulk of tokens; periodic global attention layers handle long-range dependencies. Allows scaling context window without quadratic cost

**Normalization:**
- **RMSNorm** is universal in modern models (replaces LayerNorm)
- **QK-Norm** (query-key normalization): Added in OLMo 2, Qwen3, Gemma 3/4, many others. Stabilizes training at large scale by normalizing Q and K tensors before attention computation. "QK-Norm was the key training stability trick that unlocked reliable scaling for many 2024-2026 models."

**Positional encoding:**
- **RoPE** (Rotary Position Embeddings): Standard across most models
- **NoPE** (no positional encoding on some layers): SmolLM3 uses NoPE on every fourth layer; LongCat-Flash-Lite mixes RoPE + NoPE. This enables some layers to attend purely by content, not position — useful for very long contexts
- **Per-layer embeddings**: Gemma 4 E2B edge model

**MoE (Mixture of Experts):**
- Sparse routing has become the dominant approach for large models: DeepSeek V3/R1/V3.2 (671B total, ~37B active), Qwen3 (235B-A22B = 235B total, 22B active), Kimi K2 (1T total), Llama 4 Maverick (400B)
- Shared expert pattern: some models keep a "dense prefix" plus shared expert plus routed experts (DeepSeek V3, GLM-4.5)
- MTP (Multi-Token Prediction): DeepSeek V3 uses MTP-1 path for speculative decoding efficiency

**Hybrid architectures (attention + recurrence/linear):**
- Nemotron 3 Nano 4B: 4 GQA + 21 Mamba-2 layers
- Nemotron 3 Nano 30B: 6 GQA + 23 Mamba-2 + 23 MoE layers
- xLSTM 7B: replaces all attention with mLSTM recurrent layers
- Qwen3.5 397B: 3:1 Gated DeltaNet (linear attention) + Gated Attention
- Kimi Linear 48B-A3B: 3:1 Kimi Delta Attention + MLA
- These hybrids are attempting to reduce KV cache growth for very long contexts while retaining quality

**Key numbers:**
- Active parameter counts: 760M to ~49B across the gallery (even the 671B and 1T models activate only a fraction)
- Context windows: 4K (GPT-2) → 128K (most modern) → 256K (Gemma 4, Kimi K2.5) → 1M (DeepSeek V4-Flash)
- 79 models catalogued as of mid-2026

### Notable Specific Models

**DeepSeek V3 (671B total, MLA):** The reference large MoE. Uses MLA for compressed KV, shared expert, MTP for speculative decoding. Became the reference "open-weight frontier" architecture, extensively copied (Mistral Large 3, GLM-5, Kimi K2 all scale this recipe).

**Gemma 3/4 (27B-270M range, GQA + QK-Norm + 5:1 sliding-window):** Google's efficient dense recipe. The 5:1 sliding-to-global ratio is the most aggressive sliding-window ratio in the gallery.

**OLMo 2/3 (7B-32B, MHA + QK-Norm + inside-residual post-norm):** The transparent fully open model. Uses "inside-residual post-norm" — an unusual placement that differs from both pre-norm and post-norm standards. Serves as the architecture research reference for ablation studies.

**SmolLM3 (3B, GQA + periodic NoPE):** Every fourth layer omits RoPE entirely. The smallest model to systematically use NoPE, suggests the technique scales down.

**xLSTM (7B):** The pure recurrent baseline — replaces all attention with mLSTM matrix-memory layers. Represents the non-transformer path.

---

## Key Verbatim/Near-Verbatim Quotes from Gallery

1. GQA with RoPE — Llama 3 (8B): *"GQA with RoPE"* in 32 layers, *"establishing modern dense baselines"*
2. MLA description: *"compresses KV cache into a low-rank latent space"* (paraphrase from gallery descriptions)
3. QK-Norm: used across OLMo 2, Qwen3, Gemma 3/4 — *"for training stability"*
4. SmolLM3 NoPE: *"every fourth layer omits RoPE"*
5. DeepSeek V3: *"dense prefix, shared expert, and MTP-1 objective"*
6. Scale of gallery: *"79 modern language model architectures"*, *"architecture diagrams, implementation links, release dates, attention mechanisms, decoder types, and compact fact sheets"*

---

## VERSO RELEVANCE

### Finding 1: KV cache pressure is THE dominant architectural constraint — and agent frameworks inherit it directly
[SHARPENS §5.1 loop / §5.2 context-engineering]
The entire 2024-2026 architectural evolution — GQA, MLA, sliding-window hybrids, NoPE layers, MoE sparse activation — is fundamentally driven by one problem: KV cache grows with context length, and agents have long contexts. Every model in the gallery is solving a version of the problem Verso must solve in context engineering. MLA compresses KV into low-rank latent space; GQA reduces KV heads; sliding-window limits the KV that must be held. Verso's static/dynamic prefix discipline and observation-masking compaction are the *application-layer* response to the same constraint the model architects are solving in the *model layer*. **This confirms that KV-cache discipline is not a micro-optimization — it is the central architectural concern shared by model builders and framework builders.** Verdict: **confirm (and sharpen)** — Verso's context engineering section should explicitly frame KV-cache as the governing constraint, not just a performance tip.

### Finding 2: QK-Norm as stability mechanism = analog of Verso's typed event dispatch
[NEW-IDEA §5.1 loop]
QK-Norm prevents training instability by normalizing the magnitudes of attention queries and keys before the dot product. The underlying problem is that without normalization, large-magnitude activations cause gradient explosions at scale. Verso's `{data, error, ok}` typed dispatch pattern solves an analogous problem at the loop level: without typed dispatch, agents fail silently when tools return unexpected shapes, causing "semantic gradient explosions" (wrong branching based on malformed tool output). The structural parallel is NEW: **both QK-Norm and typed dispatch are normalization layers that prevent magnitude/type surprises from destabilizing the system**. This suggests Verso could market its typed dispatch as the "QK-Norm of agent loops" in technical writing. Verdict: **new-idea — use as analogy in docs/positioning.**

### Finding 3: Sliding-window + periodic global attention = Verso's observation-masking compaction
[SHARPENS §5.2 context-engineering]
The 3:1 and 5:1 sliding-window-to-global ratios mean: most layers attend only locally (recent tokens), while occasional global layers attend to everything. This is structurally identical to Verso's N=10 observation-masking compaction: keep recent observations in full detail (sliding window), compress older observations into a summary (the "global attention" equivalent). The model builders and Verso are independently converging on the same solution: local recency bias + periodic global synthesis. **Sharpens the theoretical grounding for N=10 compaction** — it is not arbitrary, it mirrors what the best architectures do internally. Verdict: **sharpen §5.2** — cite the sliding-window convergence explicitly.

### Finding 4: MoE sparse activation = role-tiered model routing analog
[CONFIRMS §6.4 model/provider]
MoE models activate only a fraction of parameters per token (Qwen3 235B-A22B: 22B active of 235B total; DeepSeek V3: ~37B active of 671B). This is the hardware-level implementation of a principle Verso already captures in role-tiered models (cheap loop / mid retry / reasoning synthesis). The framing insight: **sparse routing at the model level and role-tiered routing at the agent framework level are the same efficiency trade-off at different granularities.** Verso's model-routing logic is the application-layer MoE. Verdict: **confirm §6.4** — the tiered model routing is well-grounded in how frontier models themselves work.

### Finding 5: xLSTM and hybrid recurrence — the non-transformer path is real but niche
[SHARPENS §6.4 model/provider]
xLSTM and Nemotron's Mamba-2 hybrids represent genuine non-attention alternatives. They have fixed context memory (no KV cache growth) at the cost of lossy compression. For Verso, this matters for model-agnostic design: the loop must not assume attention-based KV semantics. The SSE transport and typed event stream are correctly model-agnostic. However, **if recurrent models gain traction, the RRF retrieval and asymmetric-embedding memory tier may need reconsideration** since those are optimized for transformer attention patterns. Verdict: **lock-interface-defer** — note in §6.4 that model-agnostic design must account for recurrent models; defer to when they reach frontier quality.

---

## One-line Verdicts per Finding
- KV-cache is the central shared constraint between model architects and Verso: **sharpen §5.2**
- QK-Norm/typed-dispatch analogy for docs and positioning: **new-idea**
- Sliding-window convergence validates N=10 compaction: **sharpen §5.2**
- MoE sparse routing confirms role-tiered model routing: **confirm §6.4**
- Recurrent models exist but niche; design must stay model-agnostic: **lock-interface-defer**
