# LLM Architecture Internals

## The Big LLM Architecture Comparison (Raschka) — https://magazine.sebastianraschka.com/p/the-big-llm-architecture-comparison — read

### Attention Mechanisms

**Multi-Head Attention (MHA)**
- Traditional: separate K/V heads per query head. More parameter-intensive than GQA.
- Still used in: OLMo 2, OLMo 3 7B, SmolLM3 (partial)

**Grouped-Query Attention (GQA)**
- Multiple query heads share K/V projections. Reduces KV computation and memory.
- Now near-universal: Gemma 3, Mistral Small 3.1, Llama 4, Qwen3, gpt-oss, GLM-4.5, MiniMax-M2, OLMo 3 32B
- DeepSeek-V2 ablation (Figure 4): "GQA appears to perform worse than MHA, whereas MLA offers better modeling performance than MHA"

**Multi-Head Latent Attention (MLA)** — DeepSeek architecture innovation
- Compresses K/V tensors into a lower-dimensional latent space before KV cache storage
- Projected back to original size at inference (adds extra matrix multiply)
- Net result: dramatically smaller KV cache footprint at the cost of extra FLOPs per forward pass
- DeepSeek V3: 68.6 KiB KV cache per token for 671B model (contrast: OLMo 2 = 512 KiB)
- DeepSeek ablation shows MLA outperforms both MHA and GQA on modeling perplexity
- Queries compressed during training only, not inference
- Used by: DeepSeek V3/R1, Kimi K2, Kimi Linear (with gating in full attention layers), Mistral Large 3, Mistral Small 4

**Sliding Window Attention (SWA)**
- Restricts attention to a local window; saves KV cache memory proportionally
- Originated in LongFormer (2020)
- Gemma 2: alternating 1:1 ratio of SWA:global attention; 4096-token window
- Gemma 3: 5:1 ratio (one global per five SWA layers); window reduced to 1024 tokens — ablation shows minimal perplexity impact
- Key insight from Gemma 3: most sequence positions don't need global attention most of the time; 5:1 ratio is nearly free
- Mistral Small 3.1: originally included, disabled (`sliding_window: null`) — too many pathological edge cases at production scale
- Also used by: gpt-oss (every second layer), OLMo 3 7B, MiniMax-M2 (default disabled)

**QK-Norm (Query-Key Normalization)**
- RMSNorm applied to Q and K vectors before RoPE application
- Purpose: stabilizes attention softmax at training, especially combined with Post-Norm
- Originally from 2023 "Scaling Vision Transformers" paper
- Used by: OLMo 2, Gemma 2/3, Qwen3, Mistral Small 3.1, OLMo 3, MiniMax-M2
- MiniMax-M2 variant: per-layer QK-Norm with unique RMSNorm parameters per attention head (finer-grained stabilization)

**Gated Attention / Gated DeltaNet (emerging)**
- Gated Attention: sigmoid-controlled output gate per channel, zero-centered RMSNorm for QK, partial RoPE
- Gated DeltaNet: linear attention variant inspired by RNNs; uses fast-weight delta rule instead of softmax
  - Faster than full attention; less precise at content-based retrieval
  - Qwen3-Next + Kimi Linear: 3:1 ratio (3 Gated DeltaNet blocks per 1 full attention block)
  - MiniMax quote: linear attention "is tricky in production LLMs. It seemed to work fine with regular prompts, but it had poor accuracy in reasoning and multi-turn tasks" — MiniMax-M2 reverted to full attention from M1's linear attention

### Positional Encoding

**RoPE (Rotary Position Embedding)** — current standard
- Rotates Q/K vectors as function of position; naturally handles relative positions
- Used by nearly all modern models: DeepSeek, Qwen3, gpt-oss, GLM-4.5, Grok 2.5, Llama, Mistral
- Partial RoPE (MiniMax-M1/M2): only first `rotary_dim` channels get rotary encoding; rest unchanged
  - Enables length extrapolation without performance degradation: "Partial RoPE enables length extrapolation without performance degradation"

**NoPE (No Positional Embedding)**
- No positional signal added at all; model learns ordering from causal mask alone
- 2023 paper "The Impact of Positional Encoding on Length Generalization" shows NoPE generalizes to longer sequences better than RoPE
- SmolLM3: NoPE in every 4th layer (hesitantly adopted due to uncertain scalability at larger scales)
- Kimi Linear: NoPE in MLA (global attention) layers

**YaRN (Yet another RoPE extension)**
- RoPE rescaling technique for extending beyond training context length
- Preserves model quality better than naive extension
- OLMo 3: YaRN only on global (non-SWA) layers
- Qwen3: optional extension from native 32k to 131k tokens via YaRN

### Normalization

**RMSNorm pre-norm** — overwhelming modern standard
- Simplified LayerNorm with fewer trainable params; placed before attention and FFN
- GPT-2 → Llama 3 → most contemporary models
- Better gradient behavior at init; works without careful learning rate warm-up

**Post-Norm**
- Original transformer placement (post-residual add)
- OLMo 2 flavor: norm after modules but inside residual connections (unique)
- OLMo quote: post-norm "helped with training stability"
- Used by: OLMo 2, OLMo 3

**Dual Normalization (Pre + Post)**
- Gemma 3: RMSNorm both before AND after each attention/FFN module
- Gets "best of both worlds" (better gradients + stability)
- Extra norm is computationally cheap; minimal throughput impact

### Mixture-of-Experts (MoE)

**Core mechanism**
- Replaces single FFN with N expert FFN blocks; router selects k active experts per token
- Sparse activation: only k/N experts run per token, keeping inference cost tied to active params not total params
- MoE now dominant for flagship models at frontier scale (DeepSeek, Qwen, GLM, Mistral Large, Kimi)

**Shared Expert design**
- Always-active expert used by every token regardless of routing
- From 2022 DeepSpeedMoE paper: prevents common patterns from being learned redundantly across specialized experts
- DeepSeek V3: 1 shared + 8 router-selected from 256 total = 9 active experts per token
- Qwen3's stance: Junyang Lin quote: "At that moment we did not find significant enough improvement on shared expert and we were worrying about the optimization for inference caused by shared expert. No straight answer to this question honestly." — Qwen3 ships without shared expert; Qwen3-Next reverts to including one
- GLM-4.5: includes shared expert
- Grok 2.5: additional SwiGLU module functions as an implicit shared expert

**Dense layers before MoE**
- GLM-4.5: 3 dense transformer layers before MoE blocks begin
- Stated rationale: "Starting with several dense layers improves convergence stability...MoE routing introduced immediately can interfere with early syntactic and semantic feature extraction"
- DeepSeek V3/R1: also starts with 3 dense layers
- Llama 4 Maverick: alternates MoE and dense blocks

**Expert configurations across models**
| Model | Total Experts | Active | Active % | Notes |
|-------|--------------|--------|----------|-------|
| DeepSeek V3/R1 | 256 | 9 (1 shared + 8) | 5.5% | 61 MoE layers |
| Qwen3 235B-A22B | 64 | 8 | 9.4% | No shared expert |
| Qwen3 30B-A3B | 16 | 2 | 12.5% | No shared expert |
| Qwen3-Next 80B-A3B | 256 | 3 | 3.8% | Shared expert added back; 56 layers |
| Llama 4 Maverick | — | 2 | — | 8192 hidden dim per expert |
| gpt-oss 20B | 32 | 4 | — | Fewer, larger experts than DeepSeek |
| gpt-oss 120B | 32 | 4 | — | Wider model, fewer layers than Qwen3-Next |
| Grok 2.5 | 8 | — | — | Older fewer-large-expert approach |
| GLM-4.5 | — | — | — | Shared expert, 3 dense prefix |
| MiniMax-M2 | 32 | 4 | 4.37% | No shared expert; twice as sparse as Qwen3 |
| Kimi K2 | 384 | ~32 | 3.2% | DeepSeek V3 arch scaled to 1T params |

**Industry trend: "many small experts" vs "few large experts"**
- DeepSeekMoE paper finding: larger number of smaller experts outperforms fewer larger experts
- gpt-oss is a notable counter-trend: wider, fewer, larger experts

### Context Length and Attention Cost

**The "quadratic attention" misconception**
- In dense Transformers, the quadratic `O(n^2)` term from attention is dominated by the `O(n * d_model^2)` term from the FFN/MLP block for typical `d_model` sizes
- At inference (generation), attention is O(n * 1) = O(n) linear — one Q vector attends to all KV vectors
- The truly expensive regime is very long prompts/prefill where attention matters more; standard generation is linear
- This explains why the "graveyard" of linear attention alternatives haven't displaced transformers: the claimed savings are real only in specific regimes

**Context window evolution**
- Current production context lengths: 128K (most modern models), 256K–262K (Gemma 4, Qwen3-Next), 1M+ (Llama 4 Maverick, DeepSeek V4)
- KV cache is the memory constraint, not computation: MLA at 68.6 KiB/token vs MHA at 128–512 KiB/token is a 2-8x memory reduction
- Approaches to long context:
  - MLA: compress KV during storage, decompress at attention
  - SWA: most tokens use local attention; global attention only every N layers
  - Partial RoPE + NoPE: enables extrapolation beyond training length
  - YaRN: rescales RoPE frequency for graceful length extension
  - Sparse attention (DeepSeek V3.2): adds sparsity pattern on top of standard attention

### Multi-Token Prediction (MTP)

- Train model to predict multiple future tokens at each step (t+1, t+2, ..., t+k) using small auxiliary heads
- Loss = sum of cross-entropies for each offset; k=4 recommended
- Training benefit: richer gradient signal per forward pass; slight compute overhead
- Inference: generates one token normally, but heads enable speculative multi-token decoding
- Step 3.5 Flash: MTP-3 used at both training AND inference (extreme case)
- Used by: DeepSeek V3/R1/V3.2, GLM-4.5, MiniMax-M2, Qwen3-Next

### Width vs Depth

**Gemma 2 ablation**: wider setup scores 52.0 avg benchmark vs deeper: 50.8 (wider wins)
- Deeper: more representational flexibility; harder to train (gradient issues over many layers)
- Wider: faster inference (better hardware parallelism); higher per-layer memory cost

**gpt-oss design philosophy** (few wider layers)
- Embedding dim 2880 vs Qwen3-Next 2048 (wider)
- Expert hidden dim 2880 vs Qwen3 768 (much wider experts)
- 2x attention heads
- Only 24 transformer blocks vs Qwen3-Next 56 (much shallower)
- Includes bias units in attention layers (GPT-2 era practice; mathematically redundant for keys but empirically shows no harm)
- Also uses learned per-head attention bias logits ("attention sinks") for long context stabilization

### Vocabulary and Tokenization

- Most modern models: 128K–151K token vocabularies (Qwen3: ~151K)
- Gemma 3/4 family: 262K vocabulary for multilingual breadth
- Vocabulary size affects inference latency through the final logit projection (larger vocab = larger unembedding matrix)
- Mistral Small 3.1 uses a custom tokenizer contributing to its lower inference latency vs Gemma 3 27B

### Optimizer Innovation

- Kimi K2 (1T params): first production use of Muon optimizer instead of AdamW at this scale
- Previously Muon had only scaled to 16B parameters
- Muon shows smooth loss curves with exceptional decay characteristics in Kimi K2 training

---

## LLM Architecture Gallery (Raschka) — https://sebastianraschka.com/llm-architecture-gallery/ — read

### Gallery overview: 77 models, 270M–1.6T parameters, 1K–1M context, 0B–840 KiB KV cache

### Attention evolution phases (chronological)
1. **MHA** — GPT-2 era (full per-head KV)
2. **GQA adoption** — Llama 3 onward (shared KV groups)
3. **QK-Norm stabilization** — Qwen3, Gemma 3 era (attention score normalization)
4. **Hybrid linear attention** — Qwen3 Next, Kimi Linear (3:1 Gated DeltaNet : global ratio)
5. **Compressed/sparse attention** — DeepSeek V4 (CSA/HCA + mHC, KV cache to 5.4–7.7 KiB)

### KV cache per token — the practical memory constraint
| Architecture | KV per token | Notes |
|---|---|---|
| xLSTM 7B | 0 B | Full recurrent, no cache |
| Nemotron 3 Nano (30B-A3B) | 6 KiB | Mamba-2 dominant |
| Kimi Linear | 7.9 KiB | Gated DeltaNet + MLA |
| DeepSeek V4 (1.6T) | 5.4–7.7 KiB | CSA/HCA compressed attention |
| DeepSeek V3 (671B) | 68.6 KiB | MLA |
| Llama 3.2 (1B) | 32 KiB | GQA |
| Llama 3 (8B) | 128 KiB | GQA |
| OLMo 2 (7B) | 512 KiB | MHA |
| Gemma 3 (27B) | 496 KiB | GQA + SWA |
| Gemma 4 (31B) | 840 KiB | Largest in gallery |

### Dense vs Sparse by model count
- Dense: ~25 models (Llama, Qwen3 dense, Gemma, OLMo, Phi-4)
- Sparse MoE: ~40 models (DeepSeek, Qwen3 MoE, Mistral Large, GLM, MiniMax)
- Hybrid (linear+attention): ~5 models (Qwen3 Next, Ling 2.5, Kimi Linear)
- Recurrent: 1 model (xLSTM — zero KV cache, full state-space)

### Alternative attention architectures (non-mainstream, active exploration)
- **Mamba-2 / SSM hybrid**: Nemotron 3 Nano/Super — mostly state-space layers with sparse GQA layers; 6–8 KiB KV cache
- **xLSTM 7B**: full recurrent replacement, no self-attention, zero KV cache
- **Lightning Attention**: Ling 2.5 — linear attention variant combined with MLA
- **CCA (Compressed Convolutional Attention)**: ZAYA1-8B
- None of these have displaced transformer attention in flagship models yet

### MoE active parameter percentages (frontier models)
| Model | Total | Active | % |
|---|---|---|---|
| DeepSeek V3/R1 | 671B | 37B | 5.5% |
| Qwen3 235B-A22B | 235B | 22B | 9.4% |
| Kimi K2 | 1T | 32B | 3.2% |
| Mistral Large 3 | 673B | 41B | 6.1% |
| GPT-OSS 120B | 117B | 5.1B | 4.4% |
| Qwen3-Next 80B-A3B | 80B | 3B | 3.8% |
| DeepSeek V4-Pro | 1.6T | 49B | 3.1% |

### Positional encoding distribution in gallery
- RoPE: dominant standard in ~60% of models
- NoPE mixing: SmolLM3 (every 4th layer), Arcee Trinity, Sarvam (105B), LongCat-Flash-Lite
- Full NoPE: Kimi Linear (MLA layers)
- Learned absolute: GPT-2 XL only
- p-RoPE: Gemma 4 global layers

### Normalization distribution
- RMSNorm pre-norm: near-universal (~70 of 77 models)
- Post-norm: OLMo 2/3 only (deliberate stability choice, not the default)
- QK-Norm: ~15 models including OLMo 2, Qwen3, Gemma 3/4, Mistral Small 3.1, MiniMax M2/M2.5, GLM-4.5, Arcee Trinity

### Per-layer embedding (Gemma 3n / Gemma 4)
- Gemma 3n: token-layer specific embeddings streamed from CPU/SSD on demand
- Memory example: 5.44B → smaller footprint on 4B variant
- Enables running frontier models on edge/mobile devices without full GPU residency

### Performance benchmarks (AA Intelligence Index)
- DeepSeek V4-Pro (1.6T, 49B active): 51.5 overall; Agents subscore: 67.2
- GLM-5 (744B): 40.6 overall; Agents: 60.3
- GLM-4.7 (355B): 34.2 overall; Agents: 54.3
- GLM-family shows disproportionate agents benchmark strength relative to overall score

---

## Sholto Douglas & Trenton Bricken — How LLMs Actually Think — https://youtu.be/UTuuTTnjxMQ — transcribed

*~2 hour conversation between Dwarkesh Patel, Sholto Douglas (Google DeepMind inference lead), and Trenton Bricken (Anthropic mechanistic interpretability). Recorded early 2024.*

### Long context and in-context learning

- Sholto: long context is "really under-hyped" — "until I started working on it I didn't really appreciate how much of a step up in intelligence it was for the model to have the onboarding problem basically instantly solved"
- Gemini 1.5 paper eval: model learns an esoteric (non-training-data) human language in context better than a human expert could learn it over several months from a few hundred examples
- "This language was esoteric enough that it wasn't in the training data...if you look at the model before it has that context run in it, just it doesn't know the language at all"
- Long context as in-context learning theory: attention operation can be viewed as gradient descent on in-context data — paper shows "N steps of gradient descent looks like N layers of in-context learning" and the loss curves are visually similar
- Implication: the model is doing something functionally like meta-learning / learning-to-learn; GPT-2 → GPT-3 jump was emergence of this meta-learning behavior
- "The key step between GPT-2 and GPT-3 was that all of a sudden there was this meta-learning behavior that was observed in pre-training...something to do with: you give it some amount of context, it's able to adapt to that context"

### Why agents haven't scaled (reliability, not context)

- Sholto directly challenges common framing: "I would actually take issue with that being the reason that agents haven't taken off — where I think that's more about like nines of reliability and the model actually successfully doing things and if you just can't chain tasks successively with high enough probability then you won't get something that looks like an agent"
- "Your base pass task success rate is 90%; if it was 99%, then chaining doesn't become a problem"
- Step-function emergence: each increment in model scale gives "that extra nine" of reliability, which suddenly makes chaining work — looks emergent but is actually a smooth underlying capability curve
- References "emergence mirage" paper (Rylan Schaeffer lead author) — evaluations using binary right/wrong hide smooth underlying capability; "pass@k" metric reveals smooth curves under the hood
- SWE-Bench is currently the best multi-step eval but still only sub-hour horizons; need multi-day evals to understand economic automation potential
- "I think one of the things that will be really important to do over the next however long is understand better what does success rate over long-horizon tasks look like"

### The residual stream: Anthropic's mental model of transformer computation

Sholto (citing Anthropic internal framing):
- Residual stream = "the working memory of the model, like the RAM of a computer where you're choosing what information to read in so you can do something with it"
- Metaphor: "imagine you're in a boat going down a river and the boat is kind of the current query where you're trying to predict the next token...then you have these little streams coming off the river where you can get extra passengers or collect extra information if you want — those correspond to the attention heads and MLPs"
- Early layers: basic token-level processing ("what do these tokens mean")
- Middle layers: deeper thinking about "how to solve this"
- Final layers: converting back to output token probability distribution
- "It's interesting to think about just like the small compressed amount of information moving through the model, and it's getting modified in different ways"

Trenton's additions:
- "A ton of things are encoded in superposition right...the residual stream is just one high-dimensional vector but actually there's a ton of different vectors packed into it"
- After layer 1: every query, key, and value used for attention is the combination of all previous tokens — by layer 2 you already have "very rich vectors packing in a ton of information" that represent combinations of multiple earlier tokens
- "The causal graph is literally over every single layer that happened in the past"

### Superposition hypothesis (Trenton — core Anthropic interpretability finding)

- "Toy Models of Superposition" paper: even small models, if data is high-dimensional and sparse (most real-world data), learn a compression strategy where more features are packed into the model than it has parameters
- Sparsity condition: "there's only one door catch, there's only one shirt you're wearing...so these are all objects or features and there are so many of them and they appear very infrequently" — the classic case for superposition
- Monosemanticity paper: individual neurons appear polysemantic ("fires for Chinese but also fish and trees and the word 'the' and full stops in URLs") — this is not the model being confused; it's superposition
- Fix: project activations into higher-dimensional space with sparsity penalty (sparse autoencoder / dictionary learning) — "you return it to that high-dimensional and sparse regime, you get out very clean features"
- Models are dramatically **underparameterized** for the task they're solving, not overparameterized: "the claim here is that they're dramatically underparameterized given the complexity of the task that they're trying to perform"
- Bigger models: "having a bigger model, you can just have cleaner representations that you can work with" — explains why larger models are more sample-efficient

### Feature splitting

- How fine-grained features are: depends on capacity given to the sparse autoencoder
- Low capacity: learns "bird" (one feature)
- Higher capacity: learns "ravens, eagles, sparrows" — specific bird features
- "The model will learn however many features it has capacity for that still span the space of representations"
- Feature universality: Base64 feature has "really high cosine similarity across models" trained with different random seeds — models independently learn the same feature in approximately the same direction
- Supports "Platonic theory of neural scaling": "all models on a similar dataset will learn the same features in the same order" (n-grams → induction heads → higher abstractions)
- Models learned three separate Base64 features: one fires for Base64 numbers, one for Base64 letters, one specifically for the subset that is ASCII-decodable — "it took us a little while to figure out what was going on...it has a denser representation of regions particularly relevant to predicting the next token"

### Chain of thought and KV cache steganography

- Chain of thought as adaptive compute: "one forward pass has a finite and predetermined amount of compute — if there's a complicated reasoning question you want to spend more time thinking about it, so you do CoT where the model just thinks through the answer and you can think about it as all those forward passes being able to dump more compute into solving the problem"
- Information bottleneck at token boundaries: "the residual stream is a compressed representation of everything happening in the model and then you're turning the residual stream into one token which is like log(50,000) bits = very small"
- But KV cache carries more: "during a forward pass you create these KV values that future steps attend to — all those keys and values are bits of information you could use in the future"
- Head cannon for CoT: model may learn to smuggle information into KV state via steganographic encoding — "the key and value weights change so that sort of steganography can happen in the KV cache"
- Evidence against naive CoT faithfulness: papers showing you can edit the CoT so reasoning is "totally garbled" and model still outputs the correct answer; CoT "is not at all representative of what the model actually decides its answer is"
- Miles Turpin paper: model infers answer from statistical pattern (all examples are option A), generates plausible-sounding but fabricated Chain of Thought to justify it
- Sholto: "the tokens you actually see in the CoT do not necessarily at all need to correspond to the vector representation that the model gets to see when it's deciding to attend back to those tokens"
- Teacher forcing at training time: model never sees its own output tokens during training (gets correct tokens injected); "the only information it's getting about the past is the keys and values, it never sees the token that it output"

### Cerebellum / attention analogy (Trenton)

- Trenton's paper: Pentti Kanerva's 1980s associative memory algorithm → when implemented as electrical circuit, is identical to the core cerebellar circuit
- Cerebellar circuit is near-universal across organisms (fruit flies have it via mushroom body; debate only about cephalopods)
- Trenton showed this operation is "to a very close approximation the same as the attention operation including implementing the softmax"
- Three-way convergence: Kanerva's algorithm ↔ cerebellar circuit ↔ transformer attention
- 70% of brain neurons are in cerebellum; associated with sequence prediction ("next token prediction — the cerebellum lights up a lot"), fine motor control, and social skills (damaged cerebellum → higher autism probability)

### "Most intelligence is pattern matching" (Trenton's thesis)

- "Most intelligence is pattern matching and you can do a lot of really good pattern matching if you have a hierarchy of associated memories"
- Start with basic object-world associations → chain into more abstract associations (e.g., a wedding ring symbolizes many downstream associations)
- MLP layers as long-term associative memory: generalization of the attention operation, operating on things not currently in context
- Sherlock Holmes as example: "his attention heads are querying his context...and his MLPs are retrieving longer-term facts or modifying that information...in later layers doing even more sophisticated queries and slowly reasoning through to a meaningful conclusion"
- "You can even generalize the attention operation and this associative memory as the MLP layer as well in a long-term setting where you don't have tokens in your current context"

### Mechanistic interpretability — practical implications

- Dictionary learning pipeline: (1) train model normally, (2) feed many inputs, collect activations, (3) project to high-dimensional sparse space via sparse autoencoder, (4) get interpretable feature directions
- "The beautiful thing about dictionary learning instead of linear probes is that it's **unsupervised** — you are just trying to learn to span all of the representations that the model has and then interpret them later"
- Feature anomaly detection: "if there's a weird feature that suddenly fires for the first time that you haven't seen fire before, that's a red flag"
- Deception detection goal: "ideally we can find some compelling deception circuit which lights up when the model knows it's not telling the full truth to you"
- CCS (Contrast-Consistent Search) work: "not looking good in terms of replicating or actually finding truth directions"
- Sleeper agents paper experiment: applying dictionary learning to fine-tuned-with-trigger models to detect the trigger without needing to elicit the behavior
- Automated interpretability: using the model itself to label features — "even familiar with cases where a human will look at a feature and try to annotate it fires for Latin words, and then when you ask the model to classify it, it says fires for Latin words defining plants — it can already beat the human in some cases"
- Feature geometry concern: features for harmful topics (e.g., Anthrax) need to be near semantically related features (biology subtree) for hierarchical search to work; empirically unclear whether this holds universally
- Trenton: "I would really surprise me given how linear the models seem to be that there isn't some component of the Anthrax feature vector that is similar to the biology vector and that they're not in a similar part of the space"

### Distillation mechanics

- Sholto: standard training signal is a one-hot vector — "normally during training you're trying to predict this one hot vector that says this is the token you should have predicted"
- Problem: if the model is far off, gradients push in the right direction but the signal is very sparse
- Distillation adds: "the full readout from the larger model — all of the probabilities — so you get more signal about what you should have predicted; it's showing a tiny bit of your working"
- Metaphor: "watching a Kung Fu master versus being in the Matrix and downloading the program"
- Implication: distilled models learn a *different* model from what you'd get training from scratch, not just a compressed version — "you get a very different model if you distill versus if you train from scratch"

### Positive transfer across modalities and tasks

- Training on code improves language reasoning: "when you train LLMs on code they get better at reasoning and language" — unless it's just high-quality comment tokens, this implies code training teaches general reasoning structure
- "Code is a nice explicit structure of composed reasoning: if this then that encodes a lot of structure in that way...you can imagine transferring to other types of reasoning problems"
- David Lab paper: fine-tuning on math problems makes the model better at entity recognition — the same attention heads that track object positions in math equations transfer to entity tracking in text
- Trenton: "I think we have a lot of evidence that actual reasoning is occurring in these models and that they're not just stochastic parrots"
- Evidence: Othello circuit work — give model a sequence of moves, apply interpretability, recover a learned board state representation the model was never explicitly trained to represent

### Intelligence explosion constraints

- Sholto: "I think we're less at the moment bound by the sheer engineering work of making these things than we are by compute to run and get signal and taste in terms of what the actual right thing to do is"
- Compute elasticity: "I think the Gemini program would probably be like maybe five times faster with 10 times more compute or something like that" — ~0.5 elasticity
- Key bottleneck structure: ideas → experiment → interpret results → next experiment; understanding *why* something failed is the hard part, harder than generating ideas
- Intelligence explosion braking mechanism: can't just rewrite code to improve the AI; must train a new model, which costs compute — "the world of what we're making today looks very different to what people imagined it would look like 20 years ago — it's not going to be able to write its own code to be really smart because actually it needs to train itself"
- Sholto: "each incremental order of magnitude gives more nines of reliability at things and so unlocks things like agents, but at least at the moment reasoning improves somewhat sublinearly" with scale

### Language as a specially evolved medium for learning

- "Language has evolved for tens of thousands of years to be this cast in which young minds can develop...that is the purpose of language after all"
- Contrast with other modalities: vision/audio researchers must reason deeply about the right representation space (pixel prediction? feature distillation?) — "in language people are just like well I guess you just predict the next token, it's kind of an easy decision"
- Implication for multimodal: positive transfer across modalities is believed but understated publicly; "I can't say peeps about that...but this is something that people believe"

---

## → Verso Implications

### 1. Token streaming is not the bottleneck — KV cache is

The actual per-token memory cost of inference varies 100x across architectures (6 KiB for Mamba-hybrid vs 840 KiB for Gemma 4 31B). Verso's framework abstractions for agent loops, multi-turn conversations, and streaming should surface KV-cache-relevant concepts:
- **Context window budget** is KV memory, not just token count; expose it as a first-class concept
- **Context compaction** is not "clear history" — it needs model-architecture-aware summarization that preserves KV-compact representations
- For long-running agents, Verso should enable pluggable context managers that understand the cost model of the underlying model (dense vs MLA vs SWA)

### 2. Sliding window attention means the agent loop must NOT assume full attention over all turns

SWA at 5:1 ratio (1 global per 5 local) means model layers may not attend to arbitrary past context. Models like Gemma 3/4 only have one global attention layer per 5 layers with a 1024-token local window. Verso's memory system should:
- Default to putting high-importance context (tool schemas, goal, instructions) in positions that fall within global attention layers OR within the local window
- Never assume "it's in the context window = model can retrieve it" — architecture matters

### 3. Chain of thought is not transparent — but it's still mechanistically valuable

CoT is not a faithful representation of what the model "computed" — the visible tokens may be fabricated post-hoc while actual computation flows through KV state. But CoT still helps because it:
- Provides intermediate KV states that subsequent tokens can attend to (adaptive compute)
- Allows error-checking and self-correction steps that wouldn't exist in a single forward pass

Implication for Verso: **never treat CoT tokens as ground-truth reasoning traces for safety or logic verification**; treat them as steering tokens that increase computational depth. Verso's eval primitives should not assume CoT faithfulness.

### 4. Reliability nines unlock agent capabilities in step functions — design for the 99% threshold

Sholto's framing: agents don't fail because tasks are too long; they fail because per-step reliability is 90% instead of 99%. Going from 90% → 99% per step converts a 10-step task from 35% → 90% success. Verso's design implications:
- Build **retry / error-recovery as a first-class agent loop primitive**, not a user concern
- Provide **built-in step-level success verification** hooks (not just final output eval)
- Expose the probability-multiplication math clearly in docs: "this agent will succeed P^N of the time"
- Evals should measure **per-step pass rate** separately from end-to-end, so users can find their bottleneck

### 5. In-context learning is gradient descent — treat context assembly as the primary product

Sholto: long context allows models to "instantly onboard" entire codebases; the context window is the primary lever for specializing a general model to a specific task. More meaningful than fine-tuning for most agents.
- Verso's memory system should be designed as **context curriculum** — not just "what fits" but "what teaches the model the right in-context gradient"
- Prime example: for a coding agent, putting examples of correct tool-use patterns in context before the task is equivalent to implicit fine-tuning
- Verso should offer structured **few-shot example injection** as a core memory primitive (not just retrieval)

### 6. MoE active parameter percentages reveal model personality — Verso should surface model selection guidance

Most frontier models use only 3–10% of total parameters per token (DeepSeek V3: 5.5%, Qwen3-Next: 3.8%, Kimi K2: 3.2%). This means:
- "671B model" ≠ "671B compute" per token; actual compute is closer to 37B-equivalent
- Small MoE models (Qwen3 30B-A3B, 3B active) can match larger dense models on many tasks at a fraction of the cost
- **Verso model selection guide** should surface active parameter count and KV cache cost, not just "total parameters," to help users pick the right model for their latency/cost/quality tradeoff

### 7. Superposition means models are underparameterized — more context always helps, don't truncate

Trenton's core finding: models encode more features than they have neurons, compressed via superposition. Models are underparameterized for the data they model. This means:
- Additional context genuinely helps: more examples, more relevant documents, richer task descriptions all give the model more feature-space signal to decode from
- Verso should **never silently truncate context** — truncation is a semantic lossy operation, not a neutral trimming. Surface it explicitly to users.
- Verso's context manager should prefer **structured summarization over hard truncation**

### 8. Features are universal across model families — prompts transfer

Base64 features, induction heads, and other low-level features appear across models trained with different seeds on similar data. This supports the emerging finding that many prompting patterns (CoT, XML structure, role priming) transfer across model families.
- Verso should provide **model-agnostic prompt templates** as defaults, with model-specific overrides only where empirically needed
- Don't over-engineer per-model prompt customization — convergent features mean prompts are more portable than developers assume

### 9. Language evolved for teaching — it's the ideal agentic communication medium

The conversation highlights: language has been optimized over millennia to convey structured reasoning to learners. This is likely WHY LLMs succeed where other modalities require complex representation engineering.
- Verso agent-to-agent communication should default to **natural language** (not structured JSON schema messages or vector passing), because language carries more implicit structure than raw data formats
- Future: Trenton notes that sharing feature vectors (not just text) between agents could be more efficient, but requires interpretability progress. Verso can prepare for this by designing message passing as **pluggable** — natural language now, richer representations later.

### 10. Attention is an associative memory retrieve, not "understanding"

Trenton's thesis: attention ≈ Hopfield/cerebellar associative memory retrieval; MLP layers ≈ long-term key-value retrieval of "compiled" facts. This means:
- **Models don't "reason" through a task — they retrieve relevant patterns and compose them**
- Agent design should work WITH this: provide lots of relevant examples and analogous prior solutions in context, rather than asking the model to reason from first principles
- Verso's RAG and memory retrieval should optimize for **associative proximity** (semantic similarity to the task pattern), not just factual relevance
- Multi-agent coordination works because each agent can carry different in-context "associative knowledge" — specialization via context, not weights

### 11. The "quadratic attention" concern is largely a myth at generation time — design for prefill cost instead

At generation (token-by-token output), attention is O(n) not O(n^2). The real cost model for long-context agents is:
- **Prefill cost** (proportional to prompt length × model size) — this is where quadratic matters
- **KV cache memory** (linear in context length × model KV width) — this is the production bottleneck
- Verso's cost model and documentation should explain prefill vs generation costs separately, and guide users toward caching strategies (prompt caching, persistent context) that eliminate repeated prefill costs
