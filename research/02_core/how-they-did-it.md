# How they did it / under the hood / revolutionary startups

Sources: `core/01_HOW_THEY_DID_IT.md`, `core/04_UNDER_THE_HOOD.md`, `core/11_REVOLUTIONARY_AI_STARTUPS.md`

---

## core/01_HOW_THEY_DID_IT.md

### Agent Loop Shape

- **Perplexity** — not a ReAct loop in the agent sense; a 6-gate deterministic pipeline: Intent Classification → Hybrid Retrieval (BM25 + dense, parallel) → Prefilter → ML Reranking (L1/L2/L3) → Engagement Selection → Structured Prompt Assembly. The "loop" is a strict linear gauntlet; no iteration except multi-turn conversational refinement.
- **Cursor Tab model** — implicit RL training loop: accept/reject signal (+0.75/-0.25/0) → full model retrain every 1.5–2 hours → multiple checkpoint deployments per day. 400M+ daily requests feed the loop. Context window: 13,000 tokens. Latency target: 260ms.
- **Artificial Societies** — simulation loop not a language-agent loop: 2.5M+ real-world persona profiles in a social graph; homophily, opinion formation, virality modeled; each simulation run ~30 seconds for 20–300 personas; 95% accuracy against human self-replication benchmarks.
- **TensorPool Agent (beta)** — monitoring loop: detects GPU Xid errors, NCCL failures, kernel panics, CUDA OOM; auto-recovers from checkpoints. Autonomous, not interactive.

### Models (Exact Names + Roles)

- **Perplexity Sonar family:** Sonar (LLaMA 3.3 70B, lightweight grounded search), Sonar Pro (LLaMA 3.3 70B, complex multi-turn), Sonar Reasoning (DeepSeek-R1, chain-of-thought analytical), Sonar Deep Research (undisclosed, exhaustive literature reviews). All fine-tuned on proprietary data for search-based QA.
- **Perplexity licensed models:** GPT-5/5.2, Claude Opus 4.6, Gemini 2.5/3.0, Grok (via Amazon Bedrock). Estimated $15–20M/year to OpenAI.
- **Perplexity inference acceleration:** Cerebras (~1,200 tok/s for Sonar, 10x faster than GPU baseline), NVIDIA TensorRT-LLM.
- **Cursor:** Proprietary Composer model uses MoE + RL. Multi-model: GPT-5.2, Claude Opus 4.6, Gemini 3 Pro, plus in-house. Custom MXFP8 quantization kernels — 3.5x speedup on Blackwell GPUs.
- **Cursor speculative edits:** Fine-tuned Llama-3-70B achieves ~1,000 tok/s (13x speedup over vanilla). Running on Fireworks AI.
- **Cursor context reranker:** Fine-tuned 7B CodeLlama, processes up to 500,000 tokens per query.

### Tool Registry / Pipeline Components

- **Perplexity Agent API presets:** `fast-search` (Grok, 1 step), `pro-search` (GPT-5.1, 3 steps), `deep-research` (GPT-5.2, 10 steps), `advanced-deep-research` (Claude Opus 4.6, 10 steps). Tools: `web_search` ($0.005/call), `fetch_url` ($0.0005/call).
- **Perplexity ROSE engine:** Speculative decoding and MTP decoders as first-class primitives. Prefill-Decode Disaggregation (separate infra, independently scalable). Python/PyTorch frontend, migrating hot path to Rust.
- **Perplexity three-tier ML reranking:** Tier 1 (lexical + embedding scorers), Tier 2 (cross-encoder reranker; lexical + vector + authority + freshness + engagement), Tier 3 (XGBoost final scoring, ~0.7 quality threshold — top ~30% survive). **Critical failsafe:** if insufficient results pass threshold, entire result set is discarded and retrieval restarts.
- **Turbopuffer engine:** Core binary in Rust. ANN v3: SPFresh centroid clustering (wide shallow tree), RaBitQ binary quantization (16–32x compression), AVX-512 VPOPCNTDQ popcount. FTS v2: MAXSCORE dynamic pruning, 256-posting fixed blocks, 741M postings/sec decode. Native filtering: attribute indexes aware of vector clustering hierarchy. p50 warm query: 8ms, p90: 10ms, p99: 35ms. Cold query: ~400ms (3–4 roundtrips to S3).
- **Cursor context engine:** Tree-sitter parsing at function/class boundaries → Merkle tree file hashing (sync every ~5 min) → embeddings stored in Turbopuffer (serverless, S3-backed) → fine-tuned 7B CodeLlama reranker. 20x cost reduction from blob-storage KV caching (8–10ms warm latency).

### Context Assembly / Compaction / Budgets

- **Cursor Priompt (called "Preempt" in transcript — earlier name was Priompt):** JSX-based prompt compiler. Each context fragment (current file, nearby files, recent edits, type info, user instruction) gets a priority score. Binary search over token budget to find optimal cutoff — drops lowest-priority elements. Not simple truncation. Priority: cursor line = highest, decreasing by distance. Decouples raw data from rendering. Enables A/B testing against historical prompt data.
- **Cursor cache warming:** While user types, proactively warms inference cache with current file contents. When user hits Enter, very few tokens need computation before generation begins.
- **Perplexity context model:** Sub-document segmentation. Documents decompose into "self-contained spans" for individual retrieval. Full pages are NEVER passed to LLM — only most relevant chunks. Chunks, URLs, publication dates, and ranked excerpts embedded directly into prompt BEFORE LLM generates anything. LLM does not decide what to cite — pre-assembled evidence with inline citation markers already mapped.
- **Manus (11_REVOLUTIONARY):** KV-cache as #1 metric. 100:1 input:output ratio. 10x cost from cache hits. Append-only event stream + logit masking state machine (tools masked but not removed to preserve cache). Strictly ONE tool call per iteration.

### Memory (What Persists, TTLs, Backend)

- **Cursor codebase indexing:** Embedding vectors stored in Turbopuffer (S3-backed). No actual code stored on Cursor's servers — only vectors. Merkle tree root hash comparison avoids per-file hashing. Hash-based caching: Nth person at company who indexes same codebase gets near-instant results (cache hit on embedding vectors).
- **Cursor Shadow Workspace:** Hidden Electron window where agents modify code without affecting user's view. On Linux, mirrors filesystem using a kernel extension so AI operates on files that exist only in memory. Agents get feedback from LSP (type errors, linting, go-to-definition), iterate in hidden env.
- **Perplexity multi-turn:** Conversational context maintained for iterative web searches on follow-up questions. Engagement-based signals (user clicks, up/downvotes) update source rankings; sources consistently skipped or downvoted dropped within ~1 week.

### System Prompts / Architectural Constraints

- **Perplexity foundational constraint:** "You are not supposed to say anything that you didn't retrieve." Derived from academic citation rule: every claim backed by a citation. This is an architectural constraint, not a feature — prevents hallucinations through pipeline design.
- **Perplexity BrowseSafe (Dec 2025):** Three-layer defense against prompt injection in retrieved content: trust boundary enforcement (all web content treated as untrusted), hybrid detection pipeline (fine-tuned Qwen-30B-A3B classifier F1=0.91 for fast scanning, frontier LLM fallback for uncertain cases), data flywheel (flagged cases become training data). Detection runs async in parallel with retrieval. Finding: adding 3 benign distractors drops detection accuracy from >90% to ~81%.

### Error Handling Paths

- **Perplexity reranking failsafe:** If insufficient results meet the ~0.7 quality threshold at L3, entire result set discarded and retrieval restarts. This is why Perplexity rarely gives garbage answers.
- **Cursor apply model:** Merging a model's suggested change into the actual file requires its own trained model. Naive deterministic matching fails ~40% of the time. Solution: trained apply model.
- **Cursor speculative editing:** diff-based editing fails ~40% (models bad at counting lines); full file rewrite accurate but slow. Solution: speculative decoding using existing file as draft.

### Exact Constants / Thresholds / Latencies

- Perplexity search API: p50=358ms, p75=443ms, p90=604ms, p95=763ms
- Perplexity reranking threshold: ~0.7 (top ~30% of candidates survive)
- Perplexity Deep Research: processes hundreds of sources (vs standard 60+ candidates)
- Turbopuffer warm: p50=8ms, p90=10ms, p99=35ms; cold p50=343ms
- Turbopuffer write: p50=285ms for 500kB; global 10M+ writes/sec
- Turbopuffer ANN v3: 200ms p99 at 1,000+ QPS over 100 billion vectors
- Turbopuffer cost: ~$70/TB/month vs $1,600/TB/month competitors (50–100x advantage)
- Cursor Tab: 260ms latency, 13,000-token context window, retrain every 1.5–2 hours
- Cursor speculative edits: ~1,000 tok/s (13x speedup over vanilla Llama-3-70B)
- Cursor RL reward: +0.75 accept, -0.25 reject, 0 silence
- Cursor codebase reranker: up to 500,000 tokens per query
- ElevenLabs voice: ~75ms model inference, ~135ms end-to-end TTFB
- Turbopuffer FTS: 741M postings/sec decode; 10x on-disk reduction from v1
- Notion sharding: 480 logical shards across 32 physical databases; migration: 3 days, 96 CPUs on m5.24xlarge

### Multi-Agent Coordination

- **Perplexity Agent API:** Universal gateway — presets route queries to different (model, step-count) configurations. All three API products (Search, Sonar, Agent) reveal a platform strategy: Search = infrastructure, Sonar = first-party product, Agent = universal gateway that makes Perplexity the default way to add search to any model.
- **Cursor cascade:** Expensive model (GPT-4/Sonnet) generates rough sketch; cheap fine-tuned Llama implements it. "Smarter models plan, less intelligent models implement." — the cascade architecture pattern.
- **Sierra (11_REV):** "Constellation" of 15+ specialized LLMs. Routes different tasks to different models based on requirements. Parallel execution across models within a single conversation.
- **Cognition/Devin (11_REV):** Compound system — Planner (strategy), Coder (trillions of code tokens trained), Critic (adversarial review). Custom SWE-1.5, SWE-1.6, SWE-grep models. SWE-1.6 = 100x more RL compute than SWE-1.5 on same base. Multi-VM delegation achieves 67% PR merge rate, 4x faster.
- **Manus (11_REV):** 3-layer (planning, execution, validation). "Wide Research" — each subagent is a fully capable general-purpose Manus instance, not predefined roles. GAIA benchmark 86.5% vs OpenAI Deep Research 74.3%.
- **Emergent (11_REV):** PM/Architect/Coder/QA agents with role specialization. Self-healing test-fix loop. $100M+ ARR in 8 months, 6M+ apps built.

### Streaming Protocol

- Perplexity API: SSE (Server-Sent Events) with OpenAI-compatible streaming format (`response.output_text.delta` events). Web frontend: Socket.IO (polling → WebSocket upgrade). They translate between SSE (API) and Socket.IO (web client).

### Training / RL / Eval Details

- **Cursor Tab RL:** ~100 different suggestions generated, reward function trained on which ones humans accept. Exploits pass@k — probability at least one of k samples is correct is much higher than any single sample. Only needs ~50–100 human examples to align (hybrid RLHF/RLAIF). Full retrain every 1.5–2 hours.
- **Cursor "apply" model:** Separate trained model; enables cascade where expensive model plans, cheap apply model implements.
- **Cursor bug detection insight:** Models bad at finding bugs (barely in pre-training distribution). Asymmetric data strategy: train model to INTRODUCE realistic bugs (easier), use synthetic data to train reverse model that DETECTS bugs.
- **Perplexity pplx-embed training (4 stages):** (1) Diffusion continued pretraining — disable causal masking, random token masking for bidirectional reconstruction, ~250B tokens 30 languages, +1pp retrieval vs causal baselines; (2) Contrastive learning (3 sub-stages: pair → cross-lingual → multilingual → contextual dual-loss → triplet hard-negative mining); (3) SLERP merging — spherical linear interpolation between contextual and triplet checkpoints in weight space; (4) Quantization-aware training — tanh mean pooling → rounding → straight-through gradients. INT8: 4x storage reduction, no quality loss. Binary: 32x reduction, <1.6% quality loss at 4B scale.
- **Synthetic data taxonomy (Cursor team / Lex Fridman):** (1) Distillation — cannot exceed teacher; (2) Asymmetric difficulty — train easy direction (introduce bugs), use for hard direction (detect bugs); (3) Generation + verification — produce many outputs, keep only verified-correct (most likely to yield massive gains).
- **Scaling law nuance (Cursor team):** Labs now overtrain smaller models on far more tokens than compute-optimal because inference cost matters more than training cost. Scaling laws should be multi-dimensional: compute + params + data + inference compute + context length.

---

## core/04_UNDER_THE_HOOD.md

### The Primitive-Rebuilding Framework (Critical for Verso Design)

Revolutionary products rebuilt the **atomic unit of computation in their domain**:

| Product | Primitive Rebuilt | Old primitive | New primitive |
|---------|-------------------|---------------|---------------|
| Perplexity | Search result | 10 blue links | cited answer |
| Cursor | Code edit | type characters | speculative generation from file |
| Figma | Design object | local file | multiplayer-synced node |
| Linear | Issue | server-rendered row | locally-synced observable |
| Stripe | Payment | bank integration | API call |
| Notion | Document unit | page | composable block |

**The wrapper test:** If you can swap out the underlying model and the product is basically the same, you built a wrapper. If removing the model requires rethinking the entire architecture, you built a primitive.

### Figma Multiplayer Architecture

- **Data model:** `Map<ObjectID, Map<Property, Value>>`. Server keeps latest value for any (ObjectID, Property). Atomic boundary: the property value. Two people editing same property → last-writer-wins. Different properties on same object → perfect merge.
- **CRDT strategy:** Not pure CRDT (no decentralized overhead). Not OT (combinatorial explosion). Simplified centralized CRDT — took CRDT concepts, removed decentralization. Server authority.
- **Conflict resolution:** Clients apply changes immediately (optimistic). When server sends conflicting changes, client discards them if they conflict with unacknowledged local changes. Result: changes feel instant, no flicker.
- **Fractional indexing:** Object positions in parent arrays use fractions between 0 and 1. Insert between two objects = average of positions. No reindexing siblings on insert. Deterministic concurrent insertions.
- **Rust rewrite:** Node.js for network I/O (WebSockets, HTTP); separate Rust child process PER DOCUMENT for performance-critical operations; communication via stdin/stdout message protocol. Result: 10x+ faster serialization, GC latency spikes eliminated, dramatically reduced memory per process.

### Linear Sync Engine Architecture

- **Bootstrap:** On first load, client downloads ALL data for workspace (40+ model types) via `/sync/bootstrap?type=full` into IndexedDB. All reads are LOCAL — querying IndexedDB, not server. Every interaction sub-50ms.
- **Delta sync:** WebSocket pushes `SyncAction` objects (Insert/Update/Delete/Archive) with monotonically increasing sync IDs. `/sync/delta` returns changes between two sync IDs.
- **Consistency model:** All mutations execute on server first. Server assigns monotonically increasing sync IDs. All clients receive same ordered change stream. CRDTs ONLY for rich-text descriptions. Everything else: server-ordered last-write-wins.
- **MobX reactivity:** Observable properties on model objects. Any property change → automatic re-render of dependent React components. Combined with local IndexedDB reads = "instant UI."

### Stripe API Versioning

- Date-based versions (e.g., `2017-05-24`). User's account pins to version at first request.
- Current code always reflects newest version. **Version Change Modules** encapsulate each breaking change with: doc of what changed, transformation function, eligible resource types.
- Response flow: format at current version → determine target version → walk BACKWARD through time applying each transformation. Inverted approach: transform downward. Cost of old versions is fixed and encapsulated, not scattered.

### Notion Sharding

- 20B rows (2021) → 200B rows (2024). Partition key: workspace ID. 480 logical shards / 32 physical databases = 15 per DB. 480 chosen for its many factors (enables incremental scaling: 32→40→48, not doubling).
- Zero-downtime migration: double-write → backfill (3 days, 96 CPUs m5.24xlarge) → verification (random UUID sampling + dark reads) → switchover (incremental read migration → full cutover). Migration and verification logic written by DIFFERENT people.

### Cursor Deep Architecture (from Lex Fridman #447 transcript)

- **Why MoE for Tab:** Task is "incredibly pre-fill token hungry" — extremely long prompts (code context) but short generation output. MoE ideal for input-heavy/output-light profile.
- **Zero-entropy-bits abstraction:** Once user expresses intent, all remaining keystrokes carrying no new information should be automated. Code has lower bits-per-byte than natural language — disproportionate number of tokens are highly predictable. Design metric: "how many consecutive tabs can we make the user press."
- **Speculative pre-computation:** Pre-compute NEXT Tab suggestion assuming you'll accept current one. If you press Tab, next suggestion already waiting. With smaller KV caches (MQA/GQA/MLA), could speculatively cache 10 possible next states.
- **Codebase Merkle tree:** Compare single root hash instead of every file hash. Only drill down recursively on mismatch. Most of the time, root matches. Hash-based embedding cache: Nth indexer of same codebase gets near-instant results.
- **Why full agents aren't ready (Cursor's view):** Most programming involves iterating on something you don't fully understand upfront. Need instant feedback and ability to refine. "Talk to your computer like an engineering department" vision flawed — forces abdication of micro-decisions (speed/cost/complexity tradeoffs that are hard to articulate in NL).
- **80% of Cursor users on Windows machines**, many not powerful. Major reason local model inference is impractical.

### v0 by Vercel — Composite Pipeline

- Base model (Sonnet 4) achieves 64.71% error-free. Composite pipeline achieves 93.87%. **+29pp through engineering, not model improvement.**
- Steps: (1) System prompt + RAG (docs, examples, uploaded sources) + hand-curated code sample directories + AI intent detection injecting current API versions; (2) model routing (frontier for new gen, quick-edit for small changes); (3) LLM Suspense (stream processing: fixes imports, URLs, formatting during streaming — icon validation via vector DB of all lucide-react icon names, <100ms; AST-based fixes for structural issues); (4) AutoFixer model (reinforcement fine-tuning + speculative decoding with adaptive speculation, 8,130 chars/sec = 10–40x faster than GPT-4o-mini, 86.14% error-free standalone).
- **Key insight (Malte Ubl):** "Don't train your own foundation models if you want to iterate fast; use a composite model architecture to stay flexible as the field evolves."

### The Cascade Architecture Pattern

From multiple companies: expensive model generates rough sketch, cheap model implements it. "Smarter models plan, less intelligent models implement."

- Perplexity: expensive synthesis, cheap retrieval scoring
- v0: frontier model for generation, AutoFixer (8,130 chars/sec) for error correction
- Cursor: GPT-4/Sonnet for planning, fine-tuned Llama for apply (1,000 tok/s)

### ElevenLabs Voice Pipeline (XTTS architecture)

1. **Conditioning Encoder:** 6 layers 16-head attention + Perceiver Resampler. Processes reference audio → 32 fixed-length embeddings × 1024 dims (voice identity, timbre, pitch, accent, rhythm).
2. **Autoregressive token prediction:** GPT-2-style decoder-only transformer (443M params) predicts audio codes from text tokens + voice conditioning. Audio codes from VQ-VAE (13M params) encoding mel-spectrograms; 8192-code codebook at 21.53 Hz.
3. **HiFi-GAN vocoder (26M params):** Converts latent vectors to waveform. Speaker embeddings injected at each upsampling layer.

- **Instant cloning:** Audio sample as conditioning at inference time. No weight updates. Works with 30 seconds of audio.
- **Professional cloning:** Actually fine-tunes model parameters.
- **Flash model:** Distillation reduces diffusion decoder from 10 steps to 1 forward pass. ~75ms model inference, ~135ms end-to-end TTFB. Genuine quality tradeoff.

### Discord Scale Architecture

- 12M+ concurrent users, 26M WebSocket events/sec, 20+ microservices, 5 engineers.
- **Manifold (fan-out):** Groups PIDs by remote node, consistent hashing, partitions by CPU cores. Reduces inter-node traffic while maintaining linearizability. (Before: 900ms–2.1s to publish to 30K+ user guilds because Erlang send/2 costs 30–70us per call.)
- **FastGlobal:** Exploits Erlang shared heap — functions returning constant data compile to read-only shared heap. 0.3us lookups (vs 7us ETS). 500K lookups: 30 seconds → 750ms.
- **Database evolution:** MongoDB → Cassandra (177 nodes, constant incidents) → ScyllaDB (72 nodes). Migration: Rust at 3.2M records/sec, 9 days. p99 reads: 40–125ms → 15ms.
- **Language per layer:** Python (API monolith), Elixir (distributed real-time), Rust (data layer), C++ (media). Each language where it's strongest.

### Midjourney Architecture

- **TPU migration (Q2 2024):** A100/H100 → Google Cloud TPU v6e pods. Monthly inference costs: $2.1M → $700K (65% reduction). $16.8M annualized savings, 11-day payback. 35% latency improvement, 3x throughput. 4.7x better performance-per-dollar for inference.
- **Discord-first:** No owned platform — leveraged Discord for auth, real-time, community, content moderation, payment hooks. David Holz: "people really like imagining together" — the social layer was the product.
- **Compound advantage:** Subscription revenue → TPU compute → training on user prompts + upvote selections → better model → retains subscribers. Zero VC = zero pressure to grow unsustainably.

### The 7 Patterns (Framework Distillation)

1. **Rebuild the primitive, not the workflow.** Can you describe what primitive you're rebuilding in one sentence? If not, you're building a feature.
2. **The moat is the pipeline, not the model.** Each company's moat is a compound system where each component reinforces others. Can't replicate by copying one piece.
3. **Latency is the product.** 200ms = instant. 500ms = normal. 1000ms = slow. Users feel it viscerally. Revolutionary products all in "instant" category through radical architectural decisions.
4. **Own your infrastructure layer.** If core primitive depends on a third-party, that service controls your product's quality ceiling. Perplexity left Bing API; building own index was the unlock.
5. **Compound feedback loops.** Specific data from usage feeds directly into model training or system optimization. Cursor's 90-minute retrain cycle is the most aggressive example.
6. **Constraint-driven architecture.** The constraint is not a limitation — it's a design forcing function. "You are not supposed to say anything you didn't retrieve" → entire citation pipeline.
7. **Taste as technical decision-making.** Srinivas testing on airline wifi. Cursor team forking VS Code. The ability to feel the difference between "this works" and "this is right."

---

## core/11_REVOLUTIONARY_AI_STARTUPS.md

### Novel Agent Architecture Patterns (Tier 2)

- **Sierra — 15+ Model Constellation:** Parallel execution across models within a single conversation. Agent OS 2.0 with memory + context + action. Outcomes-based pricing (pay for results, not API calls). Agent Studio 2.0: natural-language "Journeys" for goal/guardrail definition. Software-style release pipelines for agents.

- **Manus — CodeAct + Context Engineering:** CodeAct paradigm — generates executable Python as universal action format. Strictly ONE tool call per iteration (architectural constraint). KV-cache as #1 metric; 100:1 input:output ratio; 10x cost from cache hits. Append-only event stream + logit masking state machine (tools masked but not removed, preserves cache). "Wide Research": each subagent is a fully capable general-purpose Manus instance (not predefined roles). GAIA benchmark 86.5%.

- **Harvey — Legal Data Factory:** Multi-agent: Sourcing Agent + Legal Review Agent + Data Integration pipeline. Custom `voyage-law-2-harvey` embeddings trained on 20B+ tokens. Multi-model orchestrator routing Claude/Gemini by task type. Parameterized jurisdiction tools. Mid-2025 pivot: all integrations become tool calls in a pure agent framework. Custom embeddings give 25% fewer irrelevant results.

- **Cognition/Devin — Compound AI + Custom Models:** Planner + Coder + Critic. SWE-1.6 = 100x more RL compute than SWE-1.5 on same base. Discovery: correctness-only rewards produce "AI slop" — needs richer reward signal. Multi-VM delegation: 67% PR merge rate, 4x faster.

- **Dust — Agent Operating System:** Synthetic filesystems mapping enterprise data (Slack, Notion, GitHub) into Unix-like structures with 5 commands (list, find, cat, search, locate_in_tree). Temporal-based workflow orchestration. Coordinator agent classifies complexity, decomposes tasks, orchestrates up to 6 concurrent sub-agents. Autonomous triggers from webhooks/schedules.

- **Hermes Agent (Nous Research) — Self-Improving:** AIAgent loop + gateway + cron scheduler + tooling runtime + ACP + SQLite persistence + RL environments. Learning cycle as first-class architectural concern. FTS5 full-text search over all past sessions. Autonomously creates skills, refines during use, compounds across sessions. ~22K stars.

- **Decagon — Agent Operating Procedures:** AOPs mix natural language + code. Business team writes NL; tech team manages code. Both compile into agent behavior. Qualitative guardrails ("user appears angry") handle things structured rules cannot.

- **xAI Grok 4.20 — Inference-Time Multi-Agent Debate:** 4-agent debate system (Grok/Captain, Harper/Research, Benjamin/Logic, Lucas/Contrarian) as LoRA-style persona adapters (~0.3% of params) on shared ~3T MoE backbone. Cross-attention block enables critique exchange. PPO-style MARL training optimizes debate + quality jointly. Cost: 1.5–2.5x (not 4x) because shared KV cache. Hallucination drops ~12% → ~4.2% (65% reduction). NOT prompt-engineering multi-agent — trained end-to-end as inference-time computation.

### Agent Infrastructure (Tier 3)

- **Stagehand (Browserbase):** 4 primitives: act, extract, observe, agent. Natural language instead of CSS selectors. Self-healing execution layer (adapts when DOM shifts). Element/action caching eliminates redundant LLM inference. 44% faster than v2. Model-agnostic Agent Mode.
- **Temporal:** Durable execution platform. Workflows survive crashes. 380% YoY growth. Used by Netflix, OpenAI. THE foundation for reliable long-running agents.
- **Neon:** Serverless Postgres, scale-to-zero, copy-on-write branching. 80%+ of databases now auto-created by AI agents.
- **E2B:** Firecracker microVM sandboxes. 150–200ms boot. 15M sessions/month. 200M+ sandboxes started.
- **Fly.io Sprites:** PERSISTENT stateful Firecracker microVMs (vs E2B ephemeral). Agents maintain state across sessions. $0.07/CPU-hour.
- **MCP:** Open standard. 8M+ server downloads, 5,800+ servers, 300+ clients. Created by Anthropic, adopted by OpenAI, Google, Microsoft, AWS.
- **Martian:** Intelligent router predicting which model performs best per prompt using interpretability techniques. 300+ companies.

### Patterns Across the Landscape

1. Custom/fine-tuned models — if you're only calling GPT-4, you're a wrapper.
2. Multi-model routing — different models for different subtasks.
3. RL training loops — model improves from production usage.
4. Self-improving architectures — system gets better without full retraining.
5. New primitives — Browserbase (4-primitive browser SDK), Dust (synthetic filesystem), Wordware (NL-as-code), Extropic (probabilistic compute).
6. Multi-agent with role separation — Cognition (Planner/Coder/Critic), Emergent (PM/Architect/Coder/QA), Manus (planning/execution/validation), Dust (coordinator + 6 sub-agents).
7. Durable execution — Temporal-backed long-running agents that survive crashes.

---

## → Verso Implications

### On the core loop design

- **Simple ReAct is correct.** Every successful agentic company (Manus, Hermes, OpenClaw, Cognition) uses variants of a clean ReAct loop — plan, act (one tool at a time), observe, repeat. None of them use complex static graphs as the primary primitive. The graph is an escape hatch for durable execution (Temporal), not the default.
- **ONE tool call per iteration is the Manus lesson.** Manus enforces strictly one tool call per iteration as an architectural constraint. This forces the model to reason about each step explicitly rather than batching decisions. Verso should consider making this the default and allow multi-tool batching only as an opt-in for performance cases.
- **Append-only event stream as state.** Manus's append-only event stream + logit masking (tools masked but not removed to preserve KV cache) is the pattern Verso should borrow for conversation/execution state. Never mutate — always append. Cache preservation is a first-order concern, not an afterthought.

### On model routing

- **Cascade is a first-class architectural pattern.** Expensive model plans, cheap model implements — Cursor, Perplexity, v0 all use this. Verso's router should support cascade chains natively, not just "pick the best model for this task." A route declaration like `plan: sonnet → implement: llama-fast` should be a first-class primitive.
- **KV-cache preservation must drive routing decisions.** Manus uses KV-cache hit rate as its #1 metric. 100:1 input:output ratio means prompt caching is not an optimization — it IS the cost model. Verso's routing layer must be cache-aware: prefer the model that already has the context cached.
- **Multi-model constellations (Sierra: 15+) vs simple routing:** Sierra runs models in parallel within a single conversation, routing subtasks to specialists. Verso should expose a `constellation` agent type: one top-level coordinator that fans out to specialist sub-agents and merges results. Not a graph — just a coordinator with typed output channels.

### On context management

- **Priompt/Preempt is the right mental model:** context fragments with priority scores, binary search over token budget. Every piece of context has a decay function (cursor line = max, decreasing by distance from edit point). Verso should ship a `ContextManager` that accepts `(content, priority, ttl)` tuples and automatically compacts to a token budget via priority ordering. Not a simple FIFO truncation.
- **Sub-document retrieval, not full-page retrieval.** Perplexity's insight — each token of context is precious, so retrieve chunks not pages — applies directly to agent memory retrieval. Verso's RAG integration should always return semantically segmented chunks, not full documents.
- **Separate retrieval from synthesis models.** Perplexity's retrieval stack operates completely upstream of synthesis model selection — same documents regardless of which synthesis model is chosen. Verso should enforce this separation architecturally: retrieval is a pipeline stage with its own latency SLA, not embedded inside the synthesis prompt.

### On memory

- **Three-tier memory is the pattern:** in-context (highest cost, lowest latency), cache-warm (intermediate), persistent store (vector DB, lowest cost). Verso should expose all three tiers explicitly, not conflate them. Hermes's FTS5 full-text search over all past sessions is a concrete implementation of the persistent tier.
- **Hash-based cache keys for codebase/document embeddings.** Cursor's Merkle tree approach — compare root hash first, drill down only on mismatch, cache embeddings by content hash — means the Nth agent indexing the same document gets near-instant results. Verso memory backend should support hash-keyed embedding caching.
- **Persistent vs ephemeral sandboxes are a design choice, not an afterthought.** E2B = ephemeral (150–200ms boot, no state carry-over). Fly.io Sprites = persistent stateful (state survives across sessions). Verso should let users declare sandbox persistence mode in their agent definition.

### On error handling and resilience

- **Durable execution (Temporal) is the escape hatch for long-running agents.** Verso's "opt-in graph" escape hatch should be Temporal-backed. Workflows that need checkpoint/resume, HITL pauses, or crash survival should delegate to Temporal as the persistence layer. This is the right separation: simple agents in the Verso ReAct loop; complex workflows in Temporal.
- **Retry and restart as first-class operations.** Perplexity's reranking failsafe — entire result set discarded and retrieval restarts if quality threshold not met — shows that "retry the whole pipeline" is sometimes the right call. Verso's loop controller should support configurable restart policies at the pipeline level, not just per-tool retry.
- **Adversarial critic as a named architecture.** Cognition's Planner/Coder/Critic triad — with Critic running adversarial review — is a concrete error-detection pattern. Verso should expose a `critic_agent` primitive: an agent whose job is to find flaws in another agent's output before it's returned.

### On evaluation / training loops

- **Short retrain cycles create compound moats.** Cursor's 90-minute retrain is not a product feature — it's an architectural choice that makes every accept/reject signal immediately useful. Verso should expose evals as a first-class primitive with hooks to feed accept/reject/score signals back to a fine-tuning or few-shot update pipeline.
- **The AutoFixer pattern (+29pp from engineering):** v0's composite pipeline lifted error-free rate from 64.71% to 93.87% through post-processing, not model improvement. Verso should support pipeline-level post-processing stages (AST fixers, import validators, format correctors) that run after LLM output before delivery. These stages should be composable and independently testable.
- **Asymmetric data strategy for tooling.** Cursor's insight: introduce bugs (easy) to generate training data for finding bugs (hard). Verso's eval harness should support asymmetric synthetic data generation — easy-direction generation feeding hard-direction evaluation.

### On streaming

- **SSE with OpenAI-compatible format is the default.** Perplexity's API uses SSE + `response.output_text.delta`. v0 uses LLM Suspense for stream processing (fixing imports, icon validation via vector DB — all happening DURING streaming). Verso's streaming layer should support mid-stream transformation hooks — pipeline stages that modify tokens as they arrive, not only after generation completes.
- **Socket.IO for real-time web clients, SSE for API consumers.** Perplexity separates the two transports explicitly. Verso's server runtime should expose both: SSE for programmatic API consumers, WebSocket/Socket.IO for dashboard/UI consumers.

### On the "moat is the pipeline" principle

- **Copy the architectural constraint, not the feature.** Perplexity's "you cannot say anything you didn't retrieve" is an architectural constraint that produced the entire citation pipeline. Cursor's "suggestions must appear at keystroke speed" produced speculative decoding + cache warming. Verso's design principle: each constraint in your agent's definition should drive an architectural decision in the framework, not just a prompt instruction.
- **Custom embeddings are a moat when trained on domain-specific data.** Harvey's `voyage-law-2-harvey` (20B+ legal tokens) gives 25% fewer irrelevant results. Perplexity's pplx-embed (250B tokens, 30 languages, SLERP-merged) outperforms every off-the-shelf embedding model on their workload. Verso should make pluggable embedding backends a first-class concern and document how to replace the default with a domain-tuned model.
- **Feedback loop engineering is the moat, not the initial architecture.** Perplexity: queries → engagement signals → ranking model updates → better answers → more queries. Cursor: accept/reject → 90-min RL retrain → better tab model → more accepts. Verso agents should ship with built-in telemetry hooks that produce eval-ready datasets from production traffic with zero extra instrumentation.
