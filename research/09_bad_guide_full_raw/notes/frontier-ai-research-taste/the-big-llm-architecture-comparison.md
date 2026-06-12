# The Big LLM Architecture Comparison
**Source:** Sebastian Raschka (Ahead of AI newsletter), magazine.sebastianraschka.com
**URL:** https://magazine.sebastianraschka.com/p/the-big-llm-architecture-comparison
**Status:** read_partial (primary URL blocked by WebFetch copyright enforcement; content reconstructed from: the Medium summary by Mehul Gupta at data-science-in-your-pocket, the langcopilot.com detailed technical writeup, and the web search synthesis citing Raschka's original article and X thread)
**Themes:** model, context, loop_harness
**Note on partial read:** The direct Substack URL refused full reproduction. All technical claims below are cross-referenced across at least two independent summaries and Raschka's own X thread summary; architectural facts are high-confidence. Quotations are from Raschka's X thread or secondary summaries that quote the article directly.

---

## Full Digest (Reconstructed from Cross-Referenced Sources)

The article surveys 11+ frontier open-weight LLM architectures (DeepSeek V3/R1, OLMo 2, Gemma 3, Mistral Small 3.1, Llama 4 Scout/Maverick, Qwen3, SmolLM3, Kimi K2, GPT-OSS, Grok 2.5, GLM-4.5) seeking to understand what architectural decisions are actually load-bearing vs cosmetic. Raschka's meta-conclusion: "all these models still look like transformers" — changes involve "clever hacks, compression tricks, and scheduling magic" rather than architectural revolution.

### Model-by-Model Architecture Breakdown

**DeepSeek V3 (671B total / 37B active)**

The reference architecture that others are now copying or reacting to.

*Multi-Head Latent Attention (MLA):* Rather than sharing keys/values across fewer heads (GQA), MLA "compresses the key and value tensors into a lower-dimensional 'latent' space before caching them." During inference, compress projections expand back to original dimensions. Ablation plots from the DeepSeek paper: MLA > GQA > MHA in modeling quality. This is not just a memory trick — it's a quality improvement.

*MoE structure:* 256 total experts, 9 active per token (8 routed + 1 shared expert consulted by every token). The shared expert mechanism ensures a universally-consulted knowledge base while the routed experts specialize. Total 671B parameters but only 37B active. "DeepSeek V3 has 671B total parameters but runs only 37B — that's the whole MoE story: pretend to be huge, act small."

*Significance:* "MoE is not a trend; it's the next evolutionary stage."

**OLMo 2 (Transparency/Stability focus)**

*Normalization innovation:* Uses Post-LN style RMSNorm (applied AFTER attention/FFN layers, not before — reversal of the usual Pre-LN pattern). Also adds QK-Norm inside attention *before* RoPE. The combination "helps stabilize training." Raschka's meta-point: "normalization layers' importance is underestimated" — this is a design dimension that deserves more attention than it gets.

**Gemma 3 (Sliding Window Attention focus)**

*Aggressive local attention:* 5 local attention layers per 1 global attention layer. Local window = 1024 tokens. This reduces KV cache memory by ~75% compared to full attention. "Gemma 3's flagship text stack leans on local attention more aggressively than Gemma 2."

*Dual normalization:* RMSNorm applied both before AND after GQA modules — "belt and suspenders" capturing benefits of multiple placements.

*Trade-off acknowledged:* Sliding window attention sacrifices the ability to attend to arbitrary context; the 5:1 ratio is the tuned compromise point.

**Mistral Small 3.1 (Simplicity rebound)**

*Abandons sliding window, returns to pure GQA + FlashAttention.* Rationale: "highly optimized FlashAttention implementations" make pure GQA faster than sliding-window variants despite the memory cost. This is Raschka's key data point for the thesis that "simplicity has long-term advantages" — the model that goes back to basics beats the models that added complexity.

Raschka's lesson: "every architectural choice has a maintenance cost; sliding window complicates the inference stack."

**Llama 4 (Maverick/Scout)**

*MoE adoption, but different MoE than DeepSeek:* 2 active experts with 8,192 hidden size each vs. DeepSeek's 9 active experts with 2,048 hidden size each. Fewer but larger experts. "Llama 4 Maverick is basically 'DeepSeek Lite.'"

*Alternates MoE and dense FFN layers* (not every layer is MoE). Uses GQA (not MLA). 17B active parameters vs DeepSeek's 37B — denser per-token but smaller total.

**Qwen3 (Dense + MoE variants)**

Dense variants prioritize depth over width. Dense range: 0.6B, 1.7B, 4B, 8B, 14B, 32B. MoE variants: 30B-A3B, 235B-A22B (notation: total-active). MoE versions *remove* the shared expert — "developers stated they didn't see clear enough benefit" from it, diverging from DeepSeek and GLM.

**SmolLM3 (NoPE)**

Removes positional embeddings (RoPE) from 3/4 of layers — the **NoPE** (No Positional Embeddings) approach. Only 1 in 4 layers has RoPE. Research rationale: "models without explicit positional information also show better length generalization." The causal attention mask provides implicit directionality even without explicit RoPE. "Challenges assumptions about position encoding necessity." Raschka's gloss: "NoPE isn't as stupid as it looked."

**Kimi K2 (Scale + Muon optimizer)**

1 trillion total parameters — likely "the largest LLM of this generation." Uses MLA (copied from DeepSeek) and MoE. Thinking version supports 256k context window. Notable: "uses the Muon optimizer, producing exceptionally smooth training curves." Open-sourced before competitors.

**GPT-OSS (Width over depth)**

Favors width over depth. MoE with few, large experts. Sliding window attention on every other layer. Includes *attention bias units* (GPT-2 style) and *attention sinks* — retrograde components that most others dropped. This is the unusual presence of old GPT-2 components in a 2025 frontier model.

**Grok 2.5**

Standard MoE with few large experts plus always-on shared expert. Represents 2024 design patterns rather than 2025 innovations.

**GLM-4.5**

Begins with three dense layers before introducing MoE — a "warm-up" pattern before sparsity kicks in. Includes shared expert. DeepSeek-inspired modifications.

**Qwen3-Next / MiniMax-M2 / Kimi Linear (Frontier 2025+)**

*Qwen3-Next:* Doubles expert count, reinstates shared expert, hybrid attention: 3 Gated DeltaNet layers + 1 full attention layer per 4-layer cycle. Natively supports 262k context window. Implements Multi-Token Prediction for faster speculative decoding.

*MiniMax-M2:* Per-layer QK-Norm with individual head scale parameters. Partial RoPE (half-dimension rotation). 10B active parameters. No shared expert.

*Kimi Linear:* Revives linear attention mechanisms from 2020 research. Channel-wise gating in linear layers. MLA applied to global layers, RoPE removed in those sections. Balances accuracy and efficiency for long contexts.

### Cross-Cutting Trends

1. **MoE is default at scale.** The question is no longer whether to use MoE but which MoE flavor (how many experts, how many active, shared vs. not, every layer vs. alternating).

2. **MLA vs GQA is the attention schism.** DeepSeek family uses MLA (better quality, more complex); Llama/Gemma family uses GQA (simpler, faster, less cache pressure). MLA > GQA > MHA in quality but GQA + FlashAttention may win on practical inference speed.

3. **NoPE experiments are running.** Multiple models are reducing or removing RoPE in subsets of layers; evidence is growing that implicit directionality from causal masking may be sufficient for most layers.

4. **Shared expert: no consensus.** DeepSeek uses it, Llama doesn't, Qwen removed it, GLM kept it. No settled verdict.

5. **Normalization placement is underrated.** Post-LN vs Pre-LN, QK-Norm before/after RoPE, single vs double RMSNorm — these choices affect training stability significantly and are not sufficiently studied.

6. **Linear attention is not dead.** Kimi Linear and Qwen3-Next hybrid approaches suggest linear attention has found a viable niche in long-context layers.

### Raschka's Meta-Verdict

"LLM developers are prioritizing inference efficiency and training stability rather than fundamental architectural innovations." The core structure has not changed since GPT-2. The innovations are compression tricks, scheduling, and normalization strategy. The practitioner's skill is in reading a new model paper and separating cosmetic from load-bearing choices.

Cosmetic choices (likely to churn): specific expert counts, exact normalization placement, width-vs-depth trade-off for a given parameter budget.

Load-bearing choices (structurally stable): the transformer attention mechanism itself; the autoregressive training objective; the tokenizer-token prediction loop.

---

## VERSO RELEVANCE

### Finding 1: MLA's quality advantage over GQA has direct implications for KV-cache context engineering [SHARPENS §5.2]

MLA compresses K/V to a low-dimensional latent space *stored in the cache*, then expands at inference time. This means the "effective cache content" is different from the raw K/V: more information per cache token. For Verso's KV-cache prefix discipline (static/dynamic prefix separation), this has a concrete implication: when a model uses MLA (DeepSeek, Kimi), the latent K/V cache is keyed on the *projected* input, not the raw input. This means the prefix that must be held stable for cache reuse is defined at the *projection* level — a different invariant than for GQA models. Verso's `ContextBundle` inspect() interface should track whether the target model uses MLA or GQA, because the prefix-stability rules differ.

**Verdict: sharpen.** §5.2 KV-cache guidance needs a model-attention-type branch: MLA models require latent-space prefix stability, GQA models require head-level prefix stability.

### Finding 2: NoPE layers (no RoPE in 3/4 of layers) → length generalization is a property of the model's attention mechanism, not just context length [SHARPENS §5.2]

SmolLM3 removes RoPE from 3/4 of layers and shows *better* length generalization. This challenges the assumption that "longer context = need more positional encoding." For Verso's just-in-time retrieval and ContextBundle design: if the model handles length via causal masking rather than RoPE, then the *order* of items in the context may matter less than previously assumed (no position encoding to reinforce order in non-RoPE layers). This could mean that ContextBundle's ordering discipline (which prefix is static, which is dynamic) is less critical for NoPE-heavy models.

**Verdict: sharpen.** §5.2 should note that context ordering discipline strength is model-dependent: strict for RoPE-every-layer models, more relaxed for NoPE-heavy models.

### Finding 3: Mistral's "simplicity rebound" — abandoning sliding window for GQA + FlashAttention — is a direct empirical case for Verso's "resist overkill" invariant [CONFIRMS §2, SHARPENS §12]

Mistral Small 3.1 abandoned the complexity of sliding window attention and won on inference latency. Raschka's lesson: "every architectural choice has a maintenance cost." The model that reverted to the simpler baseline beat the models that added complexity — because the optimized simple thing (FlashAttention) outpaced the complex thing (sliding window) once implementation caught up. This is exact confirmation of Verso's counter-positioning thesis: the complexity tax accumulates, and at some point the highly-optimized simple implementation wins. Verso's "no graph required" bet is the same bet Mistral made on attention.

**Verdict: confirm.** This is a clean empirical data point for §12 positioning: cite Mistral's reversion to simplicity as evidence that complexity accumulation in frameworks (like adding graphs to agent frameworks) has the same failure mode as complexity accumulation in model architectures.

### Finding 4: Shared expert debate (no consensus) → Verso should not pre-commit to a "universal tool" primitive [NEW-IDEA §5.3]

DeepSeek uses a shared expert (consulted by every token), Qwen removed it (didn't see sufficient benefit), Llama skipped it, GLM kept it. The pattern: initially the shared expert seems obviously useful (universal background knowledge), but the ablations are mixed. This maps to a Verso primitive question: should there be a "universal tool" or "background context injected into every agent call"? The model-world equivalent says: maybe, maybe not — and forcing it increases complexity without guaranteed benefit. The correct Verso design is to make universal-injection *opt-in* (a decorator or flag on a ContextBundle component), not default.

**Verdict: lock-interface-defer.** Don't make universal-context-injection a default or required primitive. Make it opt-in and study usage patterns before promoting it.

### Finding 5: "Load-bearing vs cosmetic" as the practitioner's reading skill = the right frame for evaluating framework primitives [NEW-IDEA §1]

Raschka's meta-skill: read a new model paper and separate cosmetic choices (expert counts, normalization placement) from load-bearing choices (attention mechanism, training objective). This is directly applicable to Verso framework design: separate cosmetic API choices (naming conventions, decorator syntax) from load-bearing choices (the event-sourcing model for durable runs, the typed RunContext injection, the append-only history invariant). Every design review should apply this question: "is this choice load-bearing or cosmetic?" Load-bearing choices should be decided early and frozen; cosmetic choices can evolve.

**Verdict: adopt-now.** Use "load-bearing vs cosmetic" as the internal language for design reviews. Publish this frame in the §1 bet section — the durable architectural choices are the ones that persist across 3+ model generations.

### Finding 6: Attention mechanism mixing (hybrid architectures: DeltaNet + full attention per cycle) → multi-provider model routing may not assume homogeneous attention [SHARPENS §6.4]

Qwen3-Next uses 3 Gated DeltaNet layers + 1 full attention layer per 4-layer cycle. This means the model's behavior depends on *which layer* a given token is processed in — the same model behaves differently across its layers. For Verso's cross-model failover (never same-model failover): if primary model is a hybrid-attention architecture, the fallback model should not assume the same layer-level behavior. The `StopReason`-based routing should be aware that hybrid-attention models may have qualitatively different failure modes (DeltaNet layers failing differently from full-attention layers).

**Verdict: lock-interface-defer.** Hybrid attention is frontier/emerging; flag it as a future concern for §6.4 routing but do not design for it now.
