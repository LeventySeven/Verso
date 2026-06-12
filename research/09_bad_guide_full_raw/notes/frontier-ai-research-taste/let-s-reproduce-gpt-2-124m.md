# Let's Reproduce GPT-2 (124M)

**Speaker**: Andrej Karpathy  
**URL**: https://www.youtube.com/watch?v=l8pRSuU81PU  
**Duration**: 4h01m  
**Published**: June 2024  
**Status**: read_partial — no official transcript; content reconstructed from detailed walkthrough articles (Towards Data Science line-by-line series, Medium summary, llm.c GitHub discussion #481, nootube.in notes, Internet Archive). The video itself is unwatchable; subtitles/captions not found on Archive.org (248 files listed, none are .srt or transcript text).

---

## What Karpathy Actually Argues

The video is structured as a live build session: Karpathy starts with an empty file and ends with a 124M-parameter GPT-2 model that beats OpenAI's original on HellaSwag (29.9 vs. 29.4). The core thesis is pedagogical: **the decisions that separate a toy from a real training run are specific, enumerable, and learnable by watching the loss**.

### Architecture (Section 1)

- Strict decoder transformer, 12 layers, 12 heads, 768-dim, 1024 context, 50,257-vocab BPE.
- Pre-norm architecture (layer norm *before* attention and MLP, not after — this comes from the GPT-2 paper, not the original "Attention is All You Need").
- Weight tying: `wte` (token embeddings) shared with the final output projection. During backprop, gradients from both branches accumulate into the shared tensor — this reduces parameters and changes optimization dynamics.
- Positional embeddings are learnable (not fixed sinusoids); they naturally recover sinusoidal patterns during training.

### Weight Initialization (Section 1, ~1:06–1:17)

- Base std = 0.02 for all linear layers and embeddings (approximates Xavier for GPT-2's hidden dimensions).
- **Special scaled init for residual projections**: `std *= (2 * n_layer) ** -0.5`. The factor of 2 accounts for two residual additions per block (attention path + MLP path). This prevents the residual stream variance from growing unboundedly with depth.
- Layer norm weights initialized to 1, biases to 0 (PyTorch default, left unchanged).
- Biases initialized to 0 throughout.

### Making It Fast (Sections 2–3, ~1:28–2:14)

The progression from ~1000ms/step to ~93ms/step on a single A100:

| Step | Change | Speedup |
|---|---|---|
| Baseline | Pure FP32 | — |
| TF32 | Crop mantissa (19-bit), preserve FP32 range | ~3x |
| BF16 | Preserve FP32 exponent range, crop mantissa | ~2x further |
| torch.compile | Fuse kernel graph, remove Python overhead | additional |
| Flash Attention | Algorithmic rewrite of attention (tile-based SRAM) | "up to 7.6x on attention alone" |
| Vocab padding | 50,257 → 50,304 (power-of-2 tile alignment) | minor but measurable |

Key insight: **torch.compile cannot discover Flash Attention** — it requires explicit algorithmic rewriting. The two speedups are orthogonal.

BF16 vs FP16: BF16 keeps FP32's exponent range (avoiding gradient scaler complexity), trading mantissa precision. FP16 has more mantissa bits but narrower range (requires loss scaling to avoid underflow). Karpathy chooses BF16 and uses `torch.autocast`.

### GPT-3 Hyperparameters (not in the GPT-2 paper)

This is the key insight for reproducing the *training recipe*, not just the model:

- **Adam β₂ = 0.95** (not PyTorch's 0.999) — looks less far into history, more responsive updates.
- **Adam ε = 1e-8** (same as default).
- **Weight decay = 0.1** (10× PyTorch default 0.01), applied only to tensors with dim ≥ 2 (matrix weights and embeddings, NOT biases or layer norms).
- **Max LR = 6e-4**, min LR = 6e-5, cosine decay with 715-step linear warmup over 19,073 total steps.
- **Batch size ≈ 0.5M tokens** per update (GPT-3 setting). On 8×A100 with 16-sequence micro-batches, this requires gradient accumulation.
- **Gradient clipping at norm 1.0** — prevents catastrophic weight overwrite from bad batches; Karpathy notes this is "a band-aid fix" and data quality is the real solution.

### Gradient Accumulation

```python
GRAD_accum = total_batch_size // (B * T)  # e.g. 524288 // (16 * 1024) = 32 steps

loss_accum = 0.0
for micro_step in range(grad_accum_steps):
    x, y = train_loader.next_batch()
    with torch.autocast(device_type='cuda', dtype=torch.bfloat16):
        logits, loss = model(x, y)
    loss = loss / grad_accum_steps   # <-- scale BEFORE backward, not after
    loss_accum += loss.detach()
    loss.backward()
```

Critical caveat: take the mean across accumulation steps by dividing loss *before* `.backward()`, not by averaging post-accumulation. Averaging means at each step then averaging again is mathematically wrong.

For DDP multi-GPU: suppress gradient sync on all but the last micro-step (`model.require_backward_grad_sync = (micro_step == grad_accum_steps - 1)`), then `dist.all_reduce(loss_accum, op=dist.ReduceOp.AVG)`.

### Data Quality

FineWeb-Edu (10B tokens, subset of Common Crawl filtered for educational quality) replaces Shakespeare. Karpathy's explicit statement: **data quality is of paramount importance**. GPT-3 blended Common Crawl, WebText2, books, and Wikipedia in specific ratios.

Shard-based loading: tokens stored as NumPy int32 arrays to enable `torch.compile` optimization (avoids int64 overhead).

### Evaluation Philosophy

- **Initial loss sanity check**: `−ln(1/50257) ≈ 10.88`. If loss at step 0 deviates significantly, initialization is wrong.
- **Overfit single batch first**: if the model can't drive loss to near-zero on one batch, there's a bug.
- **HellaSwag every 250 steps**: reliable signal even for small models, shows progression from 25% (random) baseline through training.
- **Validation every 100 steps** over 20 unseen batches.

The philosophy: watch the loss curve, match the theoretical expectations at each stage, and compare to known baselines.

### Final Results

- 8×A100 GPUs, ~2.5 hours training time.
- HellaSwag: 29.9 vs. GPT-2 baseline 29.4. Improvement attributed to "better data" (FineWeb-Edu) rather than hardware differences.
- The llm.c C/CUDA rewrite achieves same results in ~90 minutes for ~$20 on Lambda Labs.

---

## VERSO RELEVANCE

### [SHARPENS §5.5 evals] Sanity-check-first debugging discipline

Karpathy's debugging sequence — initial loss = -ln(1/vocab) check → overfit single batch → watch HellaSwag every 250 steps — is a concrete template for **embedded in-process evals**. Verso's `define_outcome(bounded)` and judge-panel currently focus on outcome quality; this adds a **harness-level invariant-checking layer** (did my loop initialize correctly? is loss moving as theory predicts?). The principle: evals are not just final-grade assessments, they're continuous runtime signals.

### [NEW-IDEA §5.2 context / §5.5 evals] Data quality as the primary lever, tooling as secondary

"Data quality is of paramount importance" — the FineWeb-Edu swap was more impactful than hardware changes. For Verso's context-engineering layer, this translates: **the quality of what goes into the context window matters more than the sophistication of the retrieval mechanism**. This challenges the instinct to engineer complex retrieval pipelines (RRF, asymmetric embeddings) before validating that the underlying data sources are high-quality.

### [CONFIRMS §5.1 loop / §12 positioning] Simplicity + correctness beats complexity

Karpathy's loop is 100-200 lines of PyTorch that beats a lab's production model via discipline on hyperparameters and data. This is the anti-over-engineering argument in code form: the GPT-3 recipe was available; using it correctly was the differentiator, not architectural novelty. Directly confirms Verso's <200-line loop thesis — **the loop is not where you compete**.

### [SHARPENS §5.2 context] Gradient accumulation = batching discipline

The gradient accumulation pattern (divide loss before backward, suppress sync on non-terminal steps) is structurally analogous to Verso's observation-masking compaction: **accumulate signal across steps, synchronize only at boundaries**. Both are about managing what you commit vs. what you defer.

### [NEW-IDEA §5.5 evals] "Beats the original on its own benchmark" as the eval design standard

GPT-2 124M beats the original GPT-2 124M on HellaSwag. This is a compelling eval design pattern: use the incumbent as the baseline, not an abstract score. For Verso's `define_outcome(bounded)` — bounded by what? The previous agent run, the human baseline, or a domain-specific gold standard. **Evals need a concrete incumbent to beat, not just a score threshold.**

---

## Verdict

Readable via secondary sources; no raw transcript. The core teaching is run-level judgment: which hyperparameters actually matter, how to debug by watching loss, and why data quality dominates architecture tricks. The most VERSO-relevant finding is the eval philosophy (continuous runtime sanity checks) and the anti-complexity lesson (matching a paper's recipe correctly beats novel architectures).
