# The Ultra-Scale Playbook: Training LLMs on GPU Clusters
**Source**: https://huggingface.co/spaces/nanotron/ultrascale-playbook
**Also at**: https://nanotron-ultrascale-playbook.static.hf.space/
**Author**: Hugging Face / nanotron team
**Status**: read_full (fetched static site with full technical content)
**Scope**: 4,100+ distributed training experiments, up to 512 GPUs, full LLM training stack

---

## Summary of the Source's Actual Argument

This is an empirical reference guide for distributed LLM training — not a research paper but a practitioner playbook backed by 4,100+ real experiments. It synthesizes the full stack: single-GPU memory math, 5 orthogonal parallelism dimensions (DP, TP, PP, SP, CP), ZeRO stages, activation checkpointing, and hardware topology effects. The guide is organized from first principles (single GPU) through progressive composition of parallelism strategies.

---

## Technical Digest

### Single-GPU Memory Math

Transformer parameter count formula:
```
N = h·v + L·(12·h² + 13·h) + 2·h
```
where h = hidden dimension, v = vocabulary size, L = layers. The h² term dominates.

**Memory per model size (mixed precision BF16 + FP32 master):**
| Model | Without FP32 grad acc | With FP32 grad acc |
|-------|-----|-----|
| 1B | 16 GB | 20 GB |
| 7B | 112 GB | 140 GB |
| 70B | 1,120 GB | 1,400 GB |
| 405B | 6,480 GB | 8,100 GB |

Models ≥7B exceed single H100 (80GB) for weights + gradients + optimizer states.

**Activation memory formula:**
```
m_act = L·seq·bs·h·(34 + 5·n_heads·seq/h)
```
Scales linearly with batch size, **quadratically with sequence length**. Activations become the dominant memory consumer at large batch sizes or long sequences.

**Activation recomputation trade-offs:**
- Full recomputation: ~30-40% extra compute, maximum memory savings
- Selective recomputation (attention focus): ~70% activation memory reduction at **only 2.7% compute cost** — this is the sweet spot used by DeepSeek-V3

### Data Parallelism

Basic: replicate model, split data, all-reduce gradients. Three key optimizations:
1. Overlap gradient sync with backward pass via hooks
2. Bucket gradients (reduce communication ops)
3. `model.no_sync()` during gradient accumulation except final step

Global batch size equation: `bs = gbs = mbs × grad_acc × dp`

**Strategy rule**: maximize dp (parallel, free) over grad_acc (sequential, slow).

**Scaling limit**: Ring latency becomes limiting at ~64–256 GPUs depending on model/configuration. Above this, DP throughput drops despite constant per-GPU memory — must switch to other parallelism dimensions.

### ZeRO Optimizer

Three stages partition along the DP dimension:

**ZeRO-1** (optimizer states): Memory = `2Ψ + 2Ψ + k·Ψ/N_d`
- Eliminates duplicated optimizer computation
- Operations: forward → backward → reduce-scatter gradients → local optimizer step → all-gather parameters

**ZeRO-2** (+ gradient partitioning): Memory = `2Ψ + (2Ψ + k·Ψ)/N_d`
- Up to 8× memory reduction vs. baseline
- ZeRO-2 generally preferred over ZeRO-1: similar communication cost, less memory

**ZeRO-3 / FSDP** (+ parameter partitioning): Memory = `(2Ψ + 2Ψ + k·Ψ)/N_d`
- Communication cost: 3Ψ total (vs. 2Ψ for ZeRO-2)
- Enables training models that don't fit a single GPU
- Prefetch next layer parameters during current layer compute (effective up to DP≈512)
- **Hard limit**: Cannot shard activation memory. Must combine with activation checkpointing for full memory relief.

### Tensor Parallelism

Mathematical foundation: two matrix-multiply splitting patterns (column-wise, row-wise). For Transformer blocks:
- MLP: column-linear → row-linear with broadcast + all-reduce
- Attention: column-linear on Q,K,V (each GPU handles subset of heads) → row-linear on output

**Hard constraint**: TP degree ≤ number of attention heads. With GQA, requires careful KV synchronization.

**Communication overhead**: All-reduce in forward pass after MLP **cannot be fully overlapped** with compute — it's on the critical path. This is why TP is intra-node only.

**Throughput cliff at node boundary**:
- TP=1→8 (intra-node, NVLink ~600+ GB/s): Reasonable scaling
- TP=8→16 (crosses node boundary, EFA ~100-200 GB/s): **~43% performance degradation**
- **Practical rule**: TP ≤ 8 within a single node; never scale TP across nodes if avoidable

### Sequence Parallelism (SP)

Extends TP to LayerNorm and dropout by splitting along sequence dimension. LayerNorm needs full hidden dimension h — SP splits along sequence so each GPU handles (b·s·h)/tp activations instead of (b·s·h).

Transition operations use conjugate pairs (all-gather↔reduce-scatter between TP and SP regions). Communication cost equivalent to TP (all-reduce = all-gather + reduce-scatter in bandwidth), but different overlapping potential.

TP+SP=16 enables 16k-token sequences where TP=16 alone cannot.

### Context Parallelism (CP)

For sequences ≥128k tokens where TP+SP cannot reduce activations enough. Splits full sequence across GPUs — each token independent *except* in attention.

**Ring Attention**: GPUs arranged in ring, K/V pairs circulate. Each GPU:
1. Send current K/V to next GPU (async, non-blocking)
2. Compute attention on current K/V pairs
3. Receive K/V from previous GPU
4. Repeat

**Load imbalance problem**: Causal attention mask means early-sequence GPUs do less work than late-sequence GPUs. Fix: **Zig-Zag Ring Attention** — distribute tokens interleaved (not sequential) to balance computation.

**Implementation choice**:
- All-Gather variant: single all-gather, more temporary memory, one step
- Ring (All-to-All) variant: K/V chunks circulate one at a time, more memory-efficient, overlaps better. **Ring wins for memory**.

### Pipeline Parallelism (PP)

Splits model layers across GPUs sequentially. Solves the core problem that TP cannot scale beyond a single node.

**Bubble problem**: Naive AFAB (all-forward-all-backward) schedule with p pipeline stages and m micro-batches:
- Bubble ratio: r_bubble = (p-1)/m
- With m=1: ~75% idle time with 4 GPUs

**1F1B (One Forward, One Backward)**: Interleave F and B passes. Same bubble size, but only stores activations for p micro-batches (not m) — enables more total micro-batches, better memory profile.

**Interleaved stages**: Non-sequential layer distribution creates "looping pipeline," reduces bubble but increases communication (activation tensors ping-pong between GPUs).

**Key PP advantage over TP for inter-node scaling**:
- PP inter-node scaling: only **14% degradation** at 2-node transition
- TP inter-node scaling: **43% degradation** at same transition
- Reason: PP only transfers activations between pipeline stages (small); TP requires all-reduce of full parameter gradients (large)
- **Rule**: For 2+ node scaling, prefer PP over TP.

### 5D Parallelism Composition

Five largely orthogonal dimensions: DP, TP, PP, SP, CP.

**Decision tree for configuration**:
1. Model + batch fits single GPU? → DP only
2. Weights fit single node? → TP(≤8) + DP + ZeRO; else TP(≤8) + PP + DP
3. Activation memory dominant? (long sequences) → Add CP or TP+SP
4. Inter-node comms limiting? → Prefer PP over scaling TP

**Cluster topology heuristics**:
- <8 GPUs: all strategies roughly equivalent, choose simplest
- 8–64 GPUs: TP within node (TP≤8), DP across nodes
- 64–512 GPUs: TP+DP+ZeRO intra-node, PP inter-node
- 500+ GPUs: TP+DP+ZeRO (intra-node), PP (inter-node), add CP for long sequences

### What Doesn't Work at Scale
- Pure DP beyond ~256 GPUs: ring latency dominates
- TP across node boundaries: ~43% degradation, never worth it
- TP>16: communication overhead catastrophic
- Naive PP with m<p micro-batches: bubble ratio >1 (negative efficiency)
- ZeRO-3 at extreme DP scales without prefetching: per-layer latency overhead compounds beyond DP≈512

### Computational Efficiency
- Well-optimized single GPU: 40–50% MFU (model FLOPS utilization)
- Optimized DP cluster: 30–45% MFU
- With TP/PP overhead: 20–35% typical
- State-of-art tuned: 45–55% (rare)

### Batch Size Guidance
- Recent LLMs: 4–60M tokens per batch
- Llama 1: ~4M tokens for 1.4T training tokens
- DeepSeek-V3: ~60M tokens for 14T, scaling from 3,072 seqs (4k length) to 15,360 seqs over first 469B tokens
- Final performance relatively insensitive to exact batch size around optimum; empirically validate with own experiments

---

## Key Verbatim Quotes

1. "Activations become by far the largest memory burden" when processing large batches or sequences.

2. "One pass can shuffle 100GB of data, two passes can shuffle 10TB, three passes 1PB, four passes 100PB." (from distributed shuffle section)

3. "Finding the right balance is key to scaling training" — on memory/compute/communication trade-offs.

4. Selective recomputation achieves "70% activation memory reduction at a 2.7% compute cost."

5. "Maximize dp (parallel) over grad_acc (sequential) when possible."

6. TP=8→16 inter-node: "~43% performance degradation" versus PP: "only 14% degradation."

---

## VERSO RELEVANCE

### Finding 1: This Playbook's Relevance Is Indirect — Model Training Infra, Not Agent Infra
**Assessment**: The Ultra-Scale Playbook covers *LLM training* infrastructure, not agent runtime infrastructure. For Verso — an agent harness framework — the technical content (ZeRO stages, pipeline parallelism, activation checkpointing) describes the infra that produces the models Verso runs against, not Verso's own architecture.

**Verso mapping**: [CONFIRMS §6.4 model/provider] — Indirectly useful for understanding what goes into the models Verso uses, and why model generations improve at the rates they do. The playbook's empirical results (4,100+ experiments, hardware scaling laws) are the infrastructure evidence underlying Gwern's "scaling still working" claim. A Verso developer who understands training constraints can make better model selection decisions (e.g., understanding why a 70B model behaves differently at different context lengths relates to activation memory constraints during training).

**Verdict**: confirm — background context, not actionable for Verso architecture.

### Finding 2: Sequence Length Quadratic Scaling — Context Window Costs
**Text**: Activation memory formula: `m_act = L·seq·bs·h·(34 + 5·n_heads·seq/h)` — scales quadratically with sequence length (seq² term in the n_heads·seq/h factor). Long sequences impose quadratic activation memory costs during training.

**Verso mapping**: [SHARPENS §5.2 context-engineering] — This is WHY long-context models are expensive and why Verso's KV-cache prefix discipline matters at inference time. Training a model with 128k context required massive infrastructure investment (ring attention, context parallelism). At inference, the KV-cache costs are the runtime analog. The insight: context length cost is not linear; it's at least quadratic in training and similarly non-linear in inference. This makes Verso's context engineering discipline (static prefix isolation, dynamic compaction) economically mandatory at scale, not just a nice-to-have. Users paying per-token will feel this quadratic pressure.
**Verdict**: sharpen — add to §5.2 context-engineering: the quadratic cost of sequence length is a training-time fact that translates to inference-time economics. Context discipline is not premature optimization.

### Finding 3: Selective Recomputation Pattern — Compute for Memory Trade-Off
**Text**: Selective activation recomputation (attention focus) achieves "70% activation memory reduction at a 2.7% compute cost." Used by DeepSeek-V3.

**Verso mapping**: [NEW-IDEA §5.2 context-engineering, §5.1 loop] — At agent runtime, this training pattern has an inference-time analog: selective context recomputation (re-running prefix computation to free KV-cache) vs. storing the full KV-cache. A 2.7% compute overhead to free 70% of cache memory is a favourable trade in long-running agentic sessions with many compactions. The framing from training directly maps: don't store everything, recompute selectively when it's cheap. This validates observation-masking compaction (already in harvest) from a different angle: memory vs. compute is the same trade at inference.
**Verdict**: sharpen — the selective recomputation 70%/2.7% ratio is useful framing for context compaction cost-justification.

### Finding 4: The 5D Composition Decision Tree — Parallels Agent Decomposition
**Text**: 5D parallelism composition (DP, TP, PP, SP, CP) with a decision tree: "Can it fit one GPU? → Can it fit one node? → Is activation memory dominant? → Are inter-node comms limiting?" These are orthogonal, composable dimensions applied progressively.

**Verso mapping**: [NEW-IDEA §6.2 multi-agent, §4 the seam/architecture] — The decision tree structure (progressive composition of orthogonal dimensions) is a design pattern that applies directly to Verso's multi-agent architecture. Multi-agent decomposition similarly decomposes along orthogonal axes: parallelism (fan-out agents), sequence (pipeline agents), memory scope (shared vs. isolated context). The playbook's lesson — start with the simplest configuration that fits, add dimensions only when hitting a constraint — is exactly Verso's "no overkill" principle applied to agent topology. Verso shouldn't force multi-agent topology any more than this playbook would force 5D parallelism on a model that fits one GPU.
**Verdict**: adopt-now — use the decision tree framing for §6.2 multi-agent: "add agent topology only when the task doesn't fit a single-agent configuration."

### Finding 5: ZeRO vs. TP Trade-Off Pattern — Communication vs. Memory
**Text**: ZeRO-3 shards everything but requires all-gather every forward pass (communication latency sensitive). TP shards activations but requires intra-node all-reduce on critical path. The right choice depends on cluster topology and model size — no universal winner.

**Verso mapping**: [NEW-IDEA §5.4 memory] — The ZeRO vs. TP analogy maps to Verso's memory tier decision: full per-session context (all-in, expensive retrieval) vs. distributed memory layers (tiered retrieval, JIT). The playbook teaches that the communication cost of gathering distributed state is real and must be overlapped with computation where possible. For Verso's 4-tier typed memory: JIT retrieval is the "all-gather" operation; its cost must be overlapped with prompt construction (pre-fetch pattern). The playbook's prefetch optimization (gather next layer's params during current layer compute) directly maps to pre-fetching episodic/semantic memory while the model processes the current prompt segment.
**Verdict**: sharpen — prefetch memory retrieval during prompt construction, not before or after; overlap is the principle.

### Finding 6: PP > TP for Inter-Node Scaling (14% vs 43% degradation)
**Text**: Pipeline parallelism degrades only 14% when crossing node boundaries vs. 43% for tensor parallelism. The reason: PP only transfers activations (small); TP requires synchronization of full parameter tensors (large).

**Verso mapping**: [NEW-IDEA §6.2 multi-agent] — This hardware analogy has a software parallel: pipeline-style multi-agent systems (sequential handoffs with intermediate results) degrade less gracefully than all-at-once fan-out systems when the "inter-node bandwidth" (coordination overhead, message passing latency) is high. For slow or unreliable orchestration channels (e.g., cross-service or async multi-agent), pipeline topology (sequential specialised agents) is more robust than parallel tensor-style fan-out with large shared context. The 14% vs 43% degradation ratio maps to coordination cost sensitivity.
**Verdict**: lock-interface-defer — useful framing for §6.2 multi-agent topology; not immediately actionable.

---

## Summary Verdict
The Ultra-Scale Playbook is primarily relevant to Verso as (1) infrastructure evidence for scaling dynamics (validating the Bitter Lesson empirically at LLM training scale), and (2) a source of design patterns — decision trees, composition of orthogonal concerns, prefetch/overlap techniques — that translate to agent harness design. The direct technical content (ZeRO stages, pipeline schedules) describes training infra, not agent infra. The most actionable extraction is the quadratic sequence length cost (→ context engineering economics) and the progressive composition decision tree (→ multi-agent topology).
