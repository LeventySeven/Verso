# Theme Synthesis: Memory + Retrieval (§5.4)

**Synthesis of 4 note files** (frontier-ai-research-taste batch):
- Your AI Product Needs Evals (Hamel Husain, 2024)
- Ahead of AI / "Components of a Coding Agent" (Sebastian Raschka, 2026)
- LLM Powered Autonomous Agents (Lilian Weng, 2023) — the heaviest memory source
- The Engineering Challenges of Scaling Interpretability (Anthropic, 2024)

Theme keys touched by this batch: memory, context, evals, loop_harness, strategy.

---

## Cross-Source Picture

These four sources mostly orbit evals/loop/context; only **two** carry real
memory signal, and they pull in the same direction:

1. **Weng (2023)** is the canonical memory taxonomy. It is the literal origin of
   Verso's "4-tier typed memory" framing (sensory→embeddings, short-term→context
   window, long-term-explicit→vector store, long-term-implicit→model weights).
   The harvest already has the tiers; Weng adds two *mechanisms* the harvest
   lacks: (a) the **Generative-Agents retrieval weighting** — recency × importance
   × relevance, where *importance* is an LLM-scored content signal set at WRITE
   time, orthogonal to the relevance signals RRF combines at READ time; and
   (b) the **reflection-synthesis consolidation primitive** (N recent observations
   → 3 questions → answers → higher-order memory), which is the episodic→semantic
   tier transition Verso has named but not specified.

2. **Raschka (2026)** contributes the **dual-store** memory shape that the durable
   layer needs: keep the *full transcript* AND a *distilled working memory* as two
   distinct artifacts, not one merged blob. This is exactly the event-log vs.
   projected-state split Verso's durable runtime should already have — so it lands
   as a §5.4↔§6.1 SHARPEN, not new machinery.

3. **Husain (2024)** contributes one clean decomposition that disciplines what
   memory is *for*: fine-tuning = syntax/style/rules (the weights tier); RAG /
   just-in-time retrieval = facts/context (the external tiers). This is a
   rationale sentence for §5.4, not a feature.

4. **Anthropic (2024)** is metaphor-only for memory: the "pass-inversion / sharding-axis"
   insight says *organize memory for retrieval locality, not just for content
   category.* Useful as design taste, dangerous if over-built — flagged to RESIST
   as literal infra.

**Net:** the memory model is already correct. The high-value deltas are TWO
small, cheap mechanisms (write-time importance score; a deferred reflection
primitive) and ONE sharpening of how the durable store is shaped (dual-store as
two objects). Everything else is confirm or resist. No source challenges a hard
invariant — memory stays a tactical-optional, durable-promotable concern; no
graph, no Rust, loop untouched.

---

## Deltas (deduped across sources, highest-value first)

### D1 — Write-time IMPORTANCE score for episodic memory (recency × importance × relevance)
**Tag:** SHARPENS · **§5.4** · **adopt-now (cheap)**
Source: Weng — Generative Agents retrieval model.
> "Retrieval Model: Surfaces relevant context weighted by three factors: Recency
> ... Importance: LLM query distinguishes mundane from core memories ...
> Relevance: Relational similarity to current situation."

The harvest has RRF (k=60) + asymmetric embeddings — but RRF only fuses
*relevance* signals at READ time. The genuinely new piece is **importance**: a
single lightweight LLM call at WRITE time ("how important is this event for
future decisions, 1-10?") stored as a scalar on the episodic record. It is
content-aware, complementary to RRF (not redundant), and cheap because it runs
once on store, never on query. Final episodic ranking = RRF(relevance) blended
with stored importance and recency decay. This is the one memory mechanism worth
adding to v1.

### D2 — Dual-store memory: full transcript + distilled working memory as TWO objects
**Tag:** SHARPENS · **§5.4 / §6.1** · **sharpen**
Source: Raschka — "Structured Session Memory."
> "Dual storage: (a) complete transcript (full history), (b) working memory
> (distilled state for task continuity)."

Maps 1:1 onto Verso's durable seam: full transcript = the append-only
event-sourced log; working memory = the derived/projected state. The sharpen is
to expose these as **distinct API artifacts**, never merged — the raw log is the
source of truth for replay/checkpoint, the working memory is the cheap thing the
loop actually reads each turn. Validates the existing durable design; the action
is "keep them separate in the API surface," not "build a new store."

### D3 — Reflection-synthesis consolidation (episodic → semantic), but DEFERRED
**Tag:** NEW-IDEA · **§5.4** · **lock-defer**
Source: Weng — Generative Agents reflection mechanism.
> "Reflection Mechanism: Synthesizes 100 recent observations → generates 3
> salient questions → answers those questions (creates higher-order memories)."

This is the concrete algorithm for the episodic→semantic tier promotion that
Verso names but leaves unspecified. It is distinct from observation-masking
compaction (N=10): compaction manages the *context window*; reflection produces
*durable long-term knowledge*. Worth a reserved interface slot —
`reflect(trigger_n≈100)` on the semantic tier — but the implementation is
deferred: it only earns its place once the episodic tier exists and an agent runs
long enough to have something to consolidate. Lock the seam, ship nothing yet.

### D4 — Fine-tuning vs. RAG decomposition disciplines the tier rationale
**Tag:** SHARPENS · **§5.4** · **sharpen (doc only)**
Source: Husain.
> "Fine-tuning is best for learning syntax, style, and rules, whereas techniques
> like RAG supply the model with context or up-to-date facts."

A one-sentence rationale that maps cleanly onto the tiers: weights tier =
style/rules (fine-tune territory); external/retrieval tiers = facts (RAG/JIT
territory). Add as design-rationale prose in §5.4 so users don't reach for RAG to
fix a style problem (or vice versa). No code.

### D5 — Memory organized for retrieval LOCALITY, not just content category (taste, not infra)
**Tag:** NEW-IDEA · **§5.4 / §5.2** · **sharpen (principle), resist as literal infra**
Source: Anthropic — pass-inversion / sharding-axis insight.
> "The problem required a pass that inverts the sharding axis ... specifically to
> create data locality."

The transferable taste: when you tier memory, index it along the axes you expect
to query (recency, session, topic) so retrieval hits a locality group rather than
scanning everything. This is genuinely useful as a *design principle* for how the
4 tiers are keyed. It is dangerous if taken literally — Anthropic's multi-pass
distributed shuffle is 100TB-scale infra that has NO place in a personal-infra v1.
Keep the principle (key tiers by query axis); resist the machinery.

### D6 — Sensory/embedding tier and MIPS index zoo are background, not build targets
**Tag:** CONFIRMS · **§5.4** · **confirm**
Source: Weng — four-type memory table + MIPS algorithms (LSH/ANNOY/HNSW/FAISS/ScaNN).
The four-type table confirms the harvest's tier design at its source. The MIPS
survey (five ANN algorithms) is reference material: Verso depends on an existing
vector store (whichever ships HNSW/FAISS), it does not implement ANN search. No
action beyond citing Weng as the tier-taxonomy origin.

---

## RESIST (overkill / bullshit for a personal-infra v1)

- **Anthropic's multi-pass hierarchical distributed shuffle** (100GB→100PB axis
  inversions). Brilliant at interpretability scale; absurd as memory infra for a
  single-operator framework. Keep only the *locality* taste (D5); build none of it.
- **Implementing MIPS / ANN search in-framework** (LSH, ANNOY, HNSW, FAISS, ScaNN).
  Verso wraps an existing vector store. Re-implementing approximate-NN is a research
  project, not a primitive. Hard resist.
- **Full Generative-Agents memory-stream architecture** (every observation logged
  to an unbounded external DB + continuous reflection sweeps). Adopt only the two
  cheap pieces — write-time importance (D1) and a deferred reflect() slot (D3).
  Resist the always-on stream + scheduled reflection daemon as v1 default; it's
  cost and complexity with no tactical-tier payoff.
- **Reflexion's 3-slot reflection-in-working-memory and CoH/Algorithm-Distillation
  training loops.** These are RL-flavored self-improvement schemes; they belong to
  model training, not to a durable agent harness. Out of scope.
- **Importance scoring at READ time / per-query.** If importance is added (D1), it
  must be a write-time scalar. Re-scoring importance on every retrieval would put an
  extra LLM call on the hot path — violates "no overkill." Resist.
- **A bespoke memory consolidation daemon shipped enabled-by-default.** Even D3's
  reflect() must be opt-in and deferred; a background consolidation process running
  on every agent breaks "ephemeral-and-simple by default."
