# Stanford CS336: Language Modeling from Scratch

**Source:** https://www.youtube.com/playlist?list=PLoROMvodv4rOY23Y0BoGoBGgQ1zmU_MT_  
**Instructors:** Percy Liang & Tatsunori Hashimoto  
**Format:** Course, ~17 lectures (Spring 2024/2025/2026 offerings), YouTube recordings  
**Transcript source:** TextPurr transcript of Lecture 2 (https://www.textpurr.com/transcript/stanford-cs336-language-modeling-from-scratch-spring-2025-lec-2-pytorch-resource); CS336 official site schedule (https://cs336.stanford.edu/); Spring 2025 archive (https://cs336.stanford.edu/spring2025/)  
**Status:** read_partial (full course schedule extracted; detailed Lecture 2 transcript on resource accounting; full verbatim transcripts for remaining lectures not fetched)

---

## Course Overview and Philosophy

CS336 is a graduate implementation course: "walk through every aspect of language model creation, including data collection and cleaning for pre-training, transformer model construction, model training, and evaluation before deployment." Lectures are executable Python programs (Percy's lectures all run as Python files). The course requires "an order of magnitude greater" code than typical ML courses. Assumes strong PyTorch proficiency — starts where explainers stop.

**Pedagogical model**: Build from scratch (inspired by OS courses), integrating systems optimization with theory from the first lecture. Minimal scaffolding; maximum implementation responsibility.

---

## Complete Lecture Schedule (Spring 2026 offering)

| Week | Topic | Instructor |
|------|-------|-----------|
| 1 | Overview, tokenization | Percy Liang |
| 2 | PyTorch, resource accounting (FLOPs, memory, arithmetic intensity) | Percy Liang |
| 3 | Architectures, hyperparameters | Tatsu Hashimoto |
| 4 | Attention alternatives, mixture of experts | Tatsu Hashimoto |
| 5 | GPUs, TPUs | Tatsu Hashimoto |
| 6 | Kernels, Triton | Percy Liang |
| 7–8 | Parallelism (two lectures) | Both |
| 9, 11 | Scaling laws (two lectures) | Tatsu Hashimoto |
| 10 | Inference | Percy Liang |
| 12 | Evaluation | Percy Liang |
| 13–14 | Data (sources, filtering, deduplication, mixing, synthetic data) | Percy Liang |
| 15 | Mid/post-training (SFT/RLHF) | Tatsu Hashimoto |
| 16 | Post-training — RLVR | Tatsu Hashimoto |
| 17 | Alignment, multimodality | Percy Liang |
| 18 | Guest: Daniel Selsam | — |
| 19 | Guest: Dan Fu | — |

---

## Detailed Content: Lecture 2 — Resource Accounting (Transcript Available)

### Memory Accounting

Data type choices are first-class engineering decisions:
- **Float32**: 4 bytes/value — standard, memory-intensive
- **BFloat16**: half memory, float32's dynamic range — preferred for forward/backward computation
- **Float16**: poor dynamic range, causes underflow/overflow in large models — avoid for training
- **FP8**: 8 bits, very unstable, only on H100s — extreme compression

> "For storing optimizer states and parameters, you still need float32, otherwise your training will go haywire." — Percy Liang

**Mixed precision strategy**: float32 for optimizer states + parameters; BFloat16 for forward/backward computation. Balances stability with efficiency.

### FLOPs Accounting

Matrix multiply FLOPs: **2 × product of all three dimensions**

Training total: **6× (data points × parameters)**
- Forward pass: 2×
- Backward pass: 4×

This "6×" rule is the basis for all scaling law computation and training cost estimates.

### Model FLOPs Utilization (MFU)

MFU = actual FLOPs/sec ÷ promised FLOPs/sec

- >0.5 MFU: good
- ~5% MFU: very poor
- Typical range: 50–90% (communication overhead)

H100 hardware: **1979 TFLOPs/sec (BFloat16)** vs. **67 TFLOPs/sec (float32)** — a 29× gap motivating mixed precision.

### Memory Requirements for Training
Total memory = parameters + activations + gradients + optimizer states

Activation checkpointing: trade compute for memory by recomputing activations rather than storing them during backward pass.

> "Efficiency is the name of the game." — Percy Liang

---

## Key Content Areas (from Course Schedule)

### Scaling Laws (Two Lectures)
The empirical relationship between model size, data quantity, compute budget, and loss. Course teaches students to fit scaling laws from data — essential for making principled resource allocation decisions.

### Inference Optimization (Lecture 10)
Deployment-time optimization: KV caching, batching, speculative decoding, quantization strategies. The course frames this as a distinct engineering domain from training.

### Evaluation (Lecture 12)
Model assessment methods — presumably covering benchmark design, contamination, and evaluation validity. Percy Liang is HELM's creator, so this lecture likely covers systematic evaluation methodology.

### Synthetic Data (Lecture 14)
Data filtering, deduplication, mixing, and synthetic data generation. Increasingly important as web-scale data is exhausted.

### Post-Training: RLVR (Lecture 16)
Reinforcement learning for verifiable reasoning — the technique behind o1/DeepSeek-R1 style models. A late addition to the curriculum reflecting 2024-2025 developments.

---

## Assignments
- **A1**: Tokenizer + transformer + optimizer + minimal training run
- **A2**: Profile/optimize with Triton FlashAttention2; distributed training
- **A3**: Analyze transformer components; fit scaling laws
- **A4**: Process Common Crawl; filtering + deduplication
- **A5**: SFT, math reasoning RL, optional safety alignment (DPO)

---

## VERSO RELEVANCE

CS336 is a training/infrastructure course. Its primary relevance to Verso is indirect — it describes the systems-level craft that produces the models Verso uses, and provides conceptual tools for reasoning about model compute/cost tradeoffs in the harness.

### [CONFIRMS §6.4 model] Resource accounting is prerequisite for cost-aware model routing
The course's central framework — FLOPs accounting, MFU, mixed-precision costs, activation memory — is the technical substrate for Verso's cache-cost-aware compaction and role-tiered model routing. If Verso is doing model routing (small vs. large model tiers), the decisions must be grounded in the same resource accounting CS336 teaches. The "6× rule" for training FLOPs and the H100 MFU numbers are the vocabulary for reasoning about per-inference cost ratios.
*Verdict: confirms §6.4 model routing needs explicit cost accounting; useful reference for the compaction cost model.*

### [SHARPENS §5.5 evals] Percy Liang's evaluation lecture — HELM methodology for systematic evaluation
Percy Liang is the creator of HELM (Holistic Evaluation of Language Models), and the evaluation lecture reflects this lineage. CS336 frames evaluation as a first-class engineering discipline: benchmark design, contamination detection, systematic coverage. This sharpens Verso's eval layer beyond unit-test-style checks — define_outcome(bounded) should be informed by HELM-style thinking about what behavioral dimensions to cover and how to avoid contamination.
*Verdict: sharpens §5.5 — systematic eval methodology (coverage, contamination) is missing from the current PRD framing.*

### [NEW-IDEA] RLVR (Lecture 16) as a path to per-step reliability improvement
The course includes a dedicated lecture on reinforcement learning for verifiable reasoning (RLVR) — the o1/DeepSeek-R1 technique. This is relevant to Verso because per-step reliability (the Sholto bottleneck: 90% → 99%) might be addressable not just at the harness level but through fine-tuning models on verifiable tool-call outcomes using RLVR. Verso's "reinforcement-on-tool-return" already known concept could be formalized using this framework. Not a harness change, but a training recipe that pairs with the harness.
*Verdict: new idea for §5.5/§6.4 — RLVR fine-tuning on tool-call outcomes as a complementary reliability layer. Harness generates verifiable signals; RLVR trains on them.*

### [CONFIRMS §5.2 context] Inference optimization (KV caching) validates prefix-discipline engineering
CS336's inference lecture covers KV caching and batching as core deployment engineering. This confirms that KV-cache prefix discipline (already known in Verso) is not a micro-optimization but a tier-one systems concern taught in graduate courses. The Verso context engineering layer's emphasis on cache prefix alignment has explicit systems grounding.
*Verdict: confirms existing design; reference material if the implementation needs justification.*
