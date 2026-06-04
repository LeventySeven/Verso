# Retrieval + Memory Primitives

---

## Retrieval After RAG: Hybrid Search, Agents, and Database Design — Simon Eskildsen of Turbopuffer — https://www.latent.space/p/turbopuffer — transcribed

### Context and Founding Motivation

- Simon Eskildsen (CEO, Turbopuffer), former principal infrastructure engineer at Shopify (~decade); post-Shopify did 3-month "angel engineering" rotations at Readwise, Replicate, Causal before founding Turbopuffer
- **Founding data point:** Readwise wanted semantic search for article recommendations (post-ChatGPT, early 2023); Readwise total infra spend ~$5k/month; estimated vector search cost ~$20–30k/month for ONE feature → shelved the feature. Simon: *"That haunted me. I couldn't stop thinking about it."*
- Napkin-math GitHub repo: tracked DRAM bandwidth (25 GB/s), SSD write bandwidth (5 GB/s), S3 patterns. Identified that three technological prerequisites had converged by 2023:
  1. NVMe SSDs in cloud (only available since ~2017)
  2. S3 strong consistency (December 2020, announced during COVID — eliminated need for Zookeeper-like consensus layers)
  3. S3 Compare-and-Swap (late 2024 — enables metadata operations without distributed consensus)
- Core question: *"Why hasn't anyone built a database placing everything on object storage, tiering into NVMe when accessed, and DRAM during queries?"*

### Turbopuffer Architecture

**What it is:** Described as *"a search engine for unstructured data"* — full-text search, vector search, regex, SQL-style filters — not a vector database specifically.

**Simon's framing on models vs. retrieval:** Models can learn to reason but cannot compress the world's knowledge into weights at any scale; systems need external truth-holding infrastructure connecting AI to complete data. This is the persistent architectural case for retrieval, regardless of context window growth.

**Storage architecture (three tiers):**
- Cold: Object storage (S3) — primary store
- Warm: NVMe SSDs (~5–10% of dataset in cache)
- Hot: DRAM — query execution layer
- Cost structure achieved: $200/month for 1TB S3 + minimal NVMe/DRAM overhead (vs. $20–30k/month for that Readwise feature in 2023 alternatives)

**Consensus layer completely eliminated:**
- No Zookeeper, no Raft, no distributed consensus layer
- S3 as the consistency primitive via Compare-and-Swap
- Metadata stored as JSON files; conflicts resolve via retry loops
- Multiple contending nodes converge over time
- Architectural conviction: refused to add metadata layer even when it cost cross-cloud latency (Notion story below)

**Round-trip optimization — the core performance model:**
- Mimics CPU cache hierarchy and NVMe design: maximize outstanding concurrent requests
- S3 pattern: ~1,000 parallel requests in a single round-trip
- Hard limit: ≤3 round-trips maximum per query
- Near-DRAM bandwidth achievable via S3 at scale

**Early index design (instructive simplicity):** First version literally: (1) cluster all vectors → `clusters.json` on S3, (2) per-cluster files `cluster_1.json`, etc., (3) two-round-trip lookup — get clusters → download nearest cluster files. *"Ultra simplistic, but not a far shot from what the first version of Turbopuffer was."*

**ANN V3 (current production):**
- Scale: 100 billion vectors
- P50 latency: ~40ms
- P99 latency: ~200ms
- Simon: *"Unseen in public SaaS offerings"* (though Google/Meta likely have it internally)
- Delivered by Nathan (chief architect) in 6–8 weeks; Simon: *"Bent the software and X86 to your will."*

**Full-text search (Act Two, current focus):**
- Claims to beat Lucene on specific query patterns — particularly **long queries** (LLM-generated text)
- Optimized for web-scale datasets (Common Crawl — 100B+ documents)
- FTSV3 in pipeline with more Lucene-compatibility features

### Customer Evidence (Architecture-Relevant)

**Cursor (launched summer 2023):**
- Original setup: single 8-core t3.large instance, Rust binary, manual deploys via `^C` to upgrade
- Migration completed in 1–2 weeks
- **Cost reduction: 95%** of Cursor's prior vector search spend
- Fixed per-user economics — was existential for their unit economics
- Cursor trained a custom embedding model (proprietary); ~25% eval improvement on their codebase workloads vs. commodity embeddings
- Cursor embeds entire codebases; 20TB Postgres moved to Turbopuffer for specific query patterns
- Security: file path obfuscation, customer encryption keys in Turbopuffer's S3 bucket

**Notion:**
- Turbopuffer was on GCP (had Compare-and-Swap first); Notion on AWS; cross-cloud latency ~14ms vs. ~1ms co-located
- Turbopuffer response: bought dark fiber between AWS Oregon and GCP exchanges (~$5k), tuned TCP windows aggressively, VPC peering with AWS to absorb egress costs
- Refused to implement a consensus metadata layer just to solve the latency differently; maintained architectural conviction
- Notion engineers independently drew the same "why hasn't anyone done this?" diagram — validated the approach

**Readwise:** Now using Turbopuffer for article recommendations — the feature that was too expensive in 2023 is now viable.

**Anthropic:** BYOC pattern — customer's own VPC deployment.

### The Agentic Workload Shift (Central to Memory/Retrieval Design)

**Old RAG pattern:**
- One retrieval call upfront
- Build 8k token context window
- Execute LLM once per turn
- ~1 search per context-build

**New agentic pattern (observed in production):**
- Agent fires many parallel queries simultaneously in a single turn
- One user-facing agent drives **dozens of concurrent searches**
- Notion: *"a ridiculous amount of queries every round trip"*
- Key design constraint: **diversity of queries matters** — not repeating same query 8 times, but mixing semantic + text + regex + SQL in parallel
- Emphasis on high **write:read ratio** but this ratio is starting to shift as agentic patterns become dominant

**Pricing response to agentic shift:**
- 2025: **5x reduction in query pricing** (first public mention in this episode)
- Further reductions expected
- Rationale: Agentic systems generate query bursts, not individual carefully-chosen calls; pricing must adapt to this pattern

**Hybrid search as diversity engine:**
- Semantic search + text search + regex in parallel reduces query repetition problem
- Each modality retrieves different documents → richer, more diverse context per agent turn
- Simon: *"Now we just see an enormous amount of queries... The right ratio is still very high, like an enormous amount of writes per read, but we're starting probably to see that change if people really lean into this pattern."*

### Database Design Philosophy

- Worst on-call experience: Elasticsearch — difficult to operate, hard to bend to specific query requirements
- Core architectural rule: **no state spread across multiple systems** — stateless design wherever possible
- *"The worst outages are the ones where you have state in multiple places that's not syncing up."*
- Zookeeper-style distributed state = 3 AM wake-up risk; eliminated entirely
- Write latency: ~100ms acceptable (vs. milliseconds for transactional DBs) — different workload contract

### On Long-Context vs. Retrieval

Simon's position (matter-of-fact, not defensive):
- Models cannot compress world knowledge into weights regardless of size
- External truth-holding infrastructure is architecturally necessary
- Coding companies "still rely heavily on search" even with long-context models
- Code search particularly valuable in large codebases where grep is insufficient
- Hybrid retrieval (semantic + text + regex + SQL) is not one-size-fits-all; each pattern matches different query types

### Turbopuffer Positioning

- Not replacing OLTP/transactional workloads
- Not retrofitting onto existing databases (vs. Neon retrofitting Postgres, vs. pgvector bolted on)
- Built purely for this model from ground up: NVMe + object storage, no consensus layer
- "Act One" = vector search; "Act Two" = full-text search; "Act Three" TBD (potential: OLAP, traces/logs, time series, graph — but *"your only moat is really just focus"*)
- Three ingredients for big database company (every ~15 years): new workload + new storage architecture + query plan that can grow

---

## The Bitter Lesson — Richard Sutton (2019) — http://www.incompleteideas.net/IncIdeas/BitterLesson.html — partial

*Note: incompleteideas.net returns a self-signed cert error in this environment. Content reconstructed from Wikipedia, LessWrong post, and search corpus — marked INFERRED where not verbatim from original.*

### Core Thesis (verbatim from original, per LessWrong reproduction)

*"The biggest lesson that can be read from 70 years of AI research is that general methods that leverage computation are ultimately the most effective, and by a large margin. The ultimate reason for this is Moore's law, or rather its generalization of continued exponentially falling cost per unit of computation."*

*"The bitter lesson is based on the historical observations that 1) AI researchers have often tried to build knowledge into their agents, 2) this always helps in the short term, and is personally satisfying to the researcher, but 3) in the long run it plateaus and even inhibits further progress, and 4) breakthrough progress eventually arrives by an opposing approach based on scaling computation by search and learning."*

### Historical Examples (INFERRED from multiple secondary sources, consistent with each other)

**Chess:**
- Deep Blue defeated world champions via alpha-beta search scaled on specialized hardware — NOT via encoded grandmaster knowledge
- Prior approaches encoded specific chess structures, opening books, endgame tables
- The search-based approach scaled with hardware; the knowledge-based approach hit a ceiling

**Go:**
- AlphaGo surpassed human performance; relied less on expert game knowledge than predecessors
- AlphaGo Zero eliminated human expertise entirely — learned only through self-play
- Human Go expertise actively harmed earlier systems; removing it improved performance

**Speech Recognition:**
- 1970s: hand-crafted phonetic rules
- Statistical methods (Hidden Markov Models) trained on large datasets consistently beat them
- Deep learning continued the trend; no explicit phonetic knowledge required

**Computer Vision:**
- Algorithms designed to mirror human visual perception (explicit edge detection, SIFT features) beaten by convolutional neural networks
- General learned representations > hand-engineered features

### The Two General-Purpose Scalable Techniques

Sutton identifies exactly two methods that reliably scale with computation:
1. **Search** — generalized optimization/planning over large spaces
2. **Learning** — gradient-based methods that improve with data and compute

Both are general-purpose, domain-agnostic, and leverage falling compute costs. All domain-specific knowledge-based approaches are the "wrong" investment.

### The Structural Tension

INFERRED but consistent across multiple reproductions:

Researchers are individually incentivized to encode domain knowledge:
- Provides short-term performance gains (publishable)
- Is personally satisfying (researchers feel their expertise matters)
- Produces clearly understandable systems
- But: creates brittle ceilings, inhibits further scaling, and is eventually obsoleted

The "bitterness" is that this is less anthropocentric than researchers want: human expertise matters less than compute. The lesson is repeated in each new domain — researchers resist it each time.

### The Meta-Lesson

INFERRED from multiple sources including the verbatim final quote:

*"We should stop trying to find simple ways to think about the contents of minds, such as simple ways to think about space, objects, multiple agents, or symmetries. All these are part of the arbitrary, intrinsically-complex, outside world. They are not what should be built in, as their complexity is endless; instead we should build in only the meta-methods that can find and capture this arbitrary complexity."*

*"We want AI agents that can discover like we can, not which contain what we have discovered."*

Key implication: baking in discovered structures is always a mistake. Build discovery methods, not structures.

---

## The Scaling Hypothesis (Gwern) — https://gwern.net/scaling-hypothesis — read

### Core Thesis

Intelligence emerges from simple neural units + simple learning algorithms applied at (currently) unreachable scale. Computational resources increasing → progressive capability gains, without requiring new architectures or algorithmic breakthroughs. The hard claim: scale IS the algorithm.

### GPT-3 as Evidence

**Meta-learning as key emergent capability:**
- GPT-3 (175B params) demonstrated meta-learning absent in GPT-2 (1.5B)
- Not just learning facts — learning *how to follow directions and learn new tasks from few examples*
- Mechanism: attention mechanisms function as "fast weights" that "learned to learn" through training on sufficiently varied data
- Emerged without being designed for meta-learning in any way — *"something that just happens. In a sense, you can't avoid this happening"* (DeepMind researcher Matthew Botvinick)
- Internet-scale training presents diverse problems → drives meta-learning spontaneously

**Scaling laws (Kaplan et al. 2020):**
- Power-law relationship: `L(C) ∝ C^−0.048` where C = compute in petaflop/s-days
- GPT-3 training: ~3,640 petaflop/s-days (~2× AlphaGo Zero)
- Cross-entropy loss: ~3.3 (GPT-2) → ~1.73 (GPT-3); ~50% reduction
- This curve shows no inflection point — "roughly logarithmic/power-law, as it was for much smaller models"
- GPT-3 continued trend for additional two orders of magnitude beyond initial projections
- Human-level performance estimated at ~0.7–0.86 bits/character; GPT-3 at ~1.73 — significant gap remains
- Extrapolation: another 3 orders of magnitude (100–1000× compute) → loss ~1.24

**Emergent capabilities unpredictable in advance:**
- Arithmetic, translation, anagram-solving, SAT analogies, few-shot adaptation — none were predicted
- *"What would another ~30% improvement over GPT-3 gain? I don't know. Does anyone? Not that I know of."*
- Threshold effects appear at specific loss levels; the ability they correspond to is not predictable

### The "Blessings of Scale" Taxonomy

**Stability and generalization improve:** Larger models → more powerful, more generalizable, more human-like from simple data increase and compute increase alone.

**Emergence without design — examples:**
- StyleGAN: disentanglement emerges at sufficient embedding size
- Transformers: relational reasoning emerges with adequate samples
- Dactyl (robot hand): millions of domain randomizations induced implicit meta-learning
- DD-PPO: two orders of magnitude compute scaling outperformed classical planners
- AlphaZero → MuZero: MuZero obsoleted AlphaZero by learning tree search implicitly

**Why scale forces genuine learning:**
- Large models contain countless sub-networks; optimization discovers those that solve the problem
- Small models learn *"superficial or memorized parts of the data"*
- Large models cannot memorize Internet-scale data → forced to discover abstract algorithms
- The ensemble hypothesis: large models ≈ ensembles averaging to Occam's razor
- Lottery ticket hypothesis: sparse effective sub-networks exist within dense large networks
- Bayesian interpretation: large models approximate amortized Bayesian inference, build *"informative priors when trained over many tasks"*

### The Pretraining Compression Argument

Predicting text requires implicitly encoding: logic, causality, object permanence, history. Loss reduction phases:
1. Character frequencies: 5 bits → ~3 bits/character
2. Vocabulary and formatting: → <3 bits
3. Word associations and semantics: → 2 bits
4. Long-range coherence and reasoning: → <1 bit
5. The final bits (deepest): causality, theory of mind, logical reasoning

*"The final few bits are the most valuable bits, which require the most of what we think of as intelligence."*

A difference of 0.02 bits/character separates models understanding gender pronouns from those guessing randomly — imperceptibly small in aggregate loss, but cognitively decisive.

Human superiority over animals is concentrated in rare, consequential decisions — *"the long tail of novel choices"* — not common tasks. This concentration in the final bits explains why *"those last bits are the hardest/deepest."*

### Scaling vs. Hand-Engineering (The Bitter Lesson Applied)

**GPT-3 uses architecture from early 2018** — "magnificently obsolete" — yet outperforms sophisticated specialized systems. This is Sutton's Bitter Lesson at scale.

What GPT-3 doesn't need:
- Brain imitation learning
- Neural architecture search
- Sophisticated attention mechanisms (fully-connected works at scale)
- Exotic components of any kind

Simple optimizers (Adam) stabilize with simple training on minibatches of millions — scale replaces engineering.

**"Green AI" critique:** Researchers pursuing efficiency without scale are *"throwing good money after bad."* Efficiency gains emerge AFTER scale demonstrates what's possible, not before. One large model at marginal deployment cost beats hundreds of narrow special-purpose models requiring separate researchers, datasets, and training runs.

### Cost and Feasibility Anchors

- GPT-3 training: ~$5M in 2020 (modest by scientific research standards)
- GPT-3 storage: 500–800GB (~$30 in hard drives)
- Inference: 0.4 kWh per 100 pages (fractions of a cent per generation)
- Scaling to 1 trillion parameters: ~$10–100M budget, thousands of GPUs — trivial by government/military research standards
- Hardware overhang: *"sufficient compute exists today for much larger models; the limiting factor is human courage of their convictions"*

### Context Window as an Architectural Bottleneck

Gwern explicitly notes GPT-3's narrow context window as a severe limitation: *"severely limit performance on tasks requiring long-range dependencies."* The BPE tokenization scheme sabotages character-level tasks (arithmetic, anagrams). These are architectural constraints that scale can overcome — but they represent real gaps at any given compute level.

**Implication for memory systems:** Context window limitations are NOT solved by scale alone; they require architectural choices (attention mechanisms, retrieval augmentation). Scale solves loss reduction; architectural choices determine what can fit in context.

### Timeline Predictions (2020 perspective)

Using Moravec's historical forecasts: *"2020s for first sub-human systems"* — GPT-3 emerged 2020, consistent. Reaching human-level language modeling: ~2027 if doubling every 3.4 months continues (requires ~2.2M× GPT-3's compute). Author: "I don't know" whether this holds — forecasting specific capabilities remains speculative even as loss improves predictably.

### Organizational/Research Dynamics

- OpenAI alone had "courage of conviction" in pursuing scaling
- Competitors operated under "weak scaling hypothesis" — believed AGI requires correct algorithms piecemeal
- Academic reward structures: *"cleverness is rewarded and heavy use of compute is considered cheating"*
- Historical validation: most AI researchers made public statements about needing algorithmic breakthroughs that were wrong

---

## → Verso Implications

### 1. Retrieval is a durable architectural primitive, not a workaround for small context windows

The Turbopuffer evidence is direct: production systems at Cursor scale, with long-context models available, still rely heavily on semantic + text + regex hybrid retrieval. Simon's framing: *"Models can learn to reason but cannot compress the world's knowledge into weights."* Gwern makes the complementary point: context windows are architectural constraints that don't disappear at any given capability level. **Verso's memory/retrieval module should be a first-class primitive, not a plugin.** Design it for the long term.

### 2. The agentic query pattern flips the retrieval contract — Verso's tool layer must handle burst-parallel retrieval natively

Old RAG = 1 retrieval call before 1 LLM call. New agentic = dozens of parallel heterogeneous retrieval queries per turn (semantic + full-text + regex + SQL, all concurrent). Notion's "ridiculous amount of queries every round trip" is the new baseline. **Verso's `search` tool interface should be designed for fan-out parallel invocation from inside the ReAct loop, not single-call-per-turn.** The agent loop should treat memory retrieval as a cheap, repeatable, parallelizable tool call, not a one-shot setup step.

### 3. Hybrid search diversity matters more than any single modality

Turbopuffer's lesson: the value of hybrid search (semantic + BM25 + regex) is not "better recall" on a single dimension — it's **diversity of retrieved content**, which is what makes parallel agentic queries non-redundant. Each modality retrieves different documents. **Verso's memory abstraction should expose at least three retrieval modes: semantic (vector), lexical (BM25/full-text), and exact (regex/SQL-filter). The agent should be able to issue all three simultaneously. This is a design decision for the tool schema, not a backend choice.**

### 4. The Bitter Lesson condemns hard-coded memory schemas and hand-crafted retrieval heuristics

Sutton's evidence: every domain where researchers encoded knowledge (chess endgame tables, phonetic rules, visual feature detectors) eventually lost to general search + learning methods. Applied to agent memory: hard-coded memory schemas, hand-tuned retrieval pipelines, manually-designed chunking strategies, and bespoke summarization rules are all the same mistake. **Verso's memory system should be general-purpose and configurable, not opinionated about what to store or how to chunk. The framework should be the substrate; the agent learns what to retrieve.** The `store` and `retrieve` API surface should be minimal and composable, not prescriptive.

### 5. Scaling validates the long-context-vs-retrieval design choice: both, not either/or

Gwern: context window limitations are real even for the largest models (the BPE/character-level failures are architectural, not scale-sensitive). Turbopuffer: production agentic systems combine long context AND retrieval — not as a workaround but as the intended design. **Verso should not pick sides in the "long-context replaces RAG" debate. The framework should make it trivially easy to use long context for recent/hot state and retrieval for cold/large/precise state. The memory module design: hot state = in-context (managed by Verso's context manager), warm state = local vector store, cold state = external search tool. Three tiers, mirroring Turbopuffer's storage architecture conceptually.**

### 6. Storage architecture choice matters — don't couple the memory module to expensive infrastructure

Turbopuffer's founding data point: $20–30k/month for vector search on a $5k/month total infra company. Cost is a real adoption barrier. **Verso's default memory backend should be zero-infrastructure (SQLite + local embedding, or even flat-file BM25) with a clean interface that swaps to Turbopuffer/Pinecone/Weaviate without code changes. The goal: every developer can run memory locally; every production deployment can plug in a scalable backend. This is the "starts for free, scales to serious" pattern.**

### 7. The Bitter Lesson directly attacks prompt-engineered memory heuristics in agent frameworks

Current agent frameworks (LangChain memory chains, CrewAI memory managers) mostly implement manually-designed heuristics: "summarize every N turns," "extract entities and store," "rank by recency + importance score." Sutton says these are the wrong approach — *"build in only the meta-methods that can find and capture this arbitrary complexity."* **Verso's memory module should lean toward learned/emergent patterns over hard-coded heuristics. In practice: store everything by default (low cost), retrieve via semantic + lexical search, let the agent decide relevance rather than the framework. The framework provides the substrate; the LLM applies the judgment.**

### 8. Write-heavy workloads with read spikes is the expected agentic memory access pattern

Turbopuffer observes: historically high write:read ratio, but the ratio is shifting as agentic patterns produce burst reads per turn. **Verso should design its memory module's access pattern around: (1) cheap continuous writes (append-only log of observations/tool outputs), (2) burst parallel reads at decision points (before each LLM call), (3) explicit memory compaction as a periodic background job (not triggered per-turn).** This mirrors the SST/LSM pattern that makes object-storage databases efficient.

### 9. Simplicity of the search primitive unlocks composeability — don't over-engineer retrieval abstractions

Turbopuffer's first version was two JSON files and two S3 round-trips. It worked. The complexity grew from observed workload needs (ANN V3 came after validating demand at scale). **Verso's memory module should ship with the simplest possible retrieval primitive that works — cosine similarity over dense vectors + BM25 over tokens, with a single `retrieve(query, k, filters)` interface — and evolve from there. Do not pre-build graph retrieval, multi-hop reasoning chains, or knowledge graph integration. Build what ships, expand what customers need.**

### 10. The "no external state" principle from Turbopuffer is a framework design lesson

Simon's deepest architectural conviction: no state in multiple systems not syncing up is the source of 3 AM outages. **Verso's memory module should have a single canonical store (not separate vector store + key-value store + graph store with their own sync). The agent's working memory is one thing with multiple query interfaces (semantic, lexical, exact). This is also the right answer for simplicity: one store, multiple indices, one consistency boundary.**
