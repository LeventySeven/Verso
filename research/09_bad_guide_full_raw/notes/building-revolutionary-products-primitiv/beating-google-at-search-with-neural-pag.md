# Beating Google at Search with Neural PageRank

**Source:** Latent Space: The AI Engineer Podcast
**URL:** https://www.youtube.com/watch?v=XqYmRSbOsJg | https://www.latent.space/p/exa
**Published:** January 10, 2025
**Duration:** ~56 minutes
**Speaker:** Will Bryk, CEO of Exa.ai
**Topic:** Building a search engine from scratch with a neural PageRank training objective and custom vector DB infrastructure

---

## Transcript Status

**Read partial (reconstructed from transcript-rich secondary sources)** — Latent Space episode page (latent.space/p/exa) returned structured show notes with substantial technical content including direct quotes. Additional content from:
1. Jason Liu writeup: https://jxnl.co/writing/2025/09/11/why-google-search-sucks-for-ai-will-bryk-exa/ (technical summary with additional detail)
2. Podwise episode summary: https://podwise.ai/dashboard/episodes/2694729

Combined coverage is substantive. Key technical mechanisms, quotes, and numbers verified across multiple sources.

---

## Speaker Background

Will Bryk is CEO and co-founder of Exa.ai (formerly Metaphor). Exa is building a search engine rebuilt from the ground up on neural embeddings rather than keyword matching. The company owns its full stack: crawling, embedding, indexing, and serving. Bryk's argument is that Google is architecturally locked into keyword matching and cannot easily pivot to embedding-first retrieval.

---

## Core Technical Mechanism: Neural PageRank via Link Prediction

### The Training Objective

Exa's fundamental innovation is using **link prediction as the training objective** for their embedding model:

> "The link prediction objective can be seen as like a neural PageRank because what you're doing is you're predicting the links people share."

The training process:
1. Extract all hyperlinks across the web along with the surrounding text context
2. Hide the target link/document
3. Train a transformer to predict which document was linked given the surrounding context
4. Scale this across billions of examples

Example: if someone writes about an aerospace startup and links to spacex.com, the model hides that link and learns to predict "this context → spacex.com." Done billions of times, the model learns a quality signal: high-quality pages are referenced "in like a thousand different ways," capturing semantic variation that traditional PageRank misses.

### Why This Is Strictly Better Than Classic PageRank

Traditional PageRank counts incoming links uniformly — a link is a link regardless of context. Neural PageRank learns the semantic relationship between the referring context and the target document. Bryk: this makes it "strictly more powerful" than PageRank because it captures *why* a page is linked, not just *that* it is.

The result: documents become embeddings in a shared semantic space, not keyword-indexed tokens. Queries retrieve by semantic similarity, not term matching.

---

## Infrastructure: Custom Vector DB for Web Scale

### Why Off-the-Shelf Won't Work

Exa built their own vector database because existing solutions cannot filter at web scale. The problem: embedding similarity search across billions of documents is fast enough; but **filtered** similarity search at web scale requires architectural decisions that off-the-shelf DBs (Pinecone, Weaviate, etc.) were not designed for.

Exa's CTO Shreyas presented the vector DB design at the AI Engineer Summit. The system uses:
- **Matryoshka embeddings**: nested vector representations at multiple dimensions — smaller subsets of the vector still represent full meaning, enabling variable-cost retrieval
- **Binary compression**: converting embeddings to boolean values for storage efficiency
- **Clustering**: segmenting the search space to avoid full-corpus scans
- **SIMD assembly-level operations**: CPU-level optimization for dot-product computation on compressed embeddings

Bryk on the scale challenge: "When you're doing over billions of documents, billions of binary compressed embeddings using clustering, it's still too slow." — hence the custom DB.

### Compute Stack

- **$5M H200 cluster** (144 units) — the investment in the episode title
- Hybrid: owned infra for training + AWS for inference
- Re-indexing: **quarterly** (crawl → embed → index cycle)
- Real-time inference on the serving side

---

## Filtering vs. Ranking: Two Different Problems

Exa makes a sharp architectural distinction that Google blurs:

- **Filtering (objective)**: Does this document match the query's intent? Binary. Exa optimizes this first.
- **Ranking (subjective)**: Which of the filtered results is "best"? Context-dependent. Exa makes this customizable.

Google returns millions of approximate results and ranks them with a black-box algorithm. Exa filters precisely first (using embedding similarity + explicit metadata filters: employee count, Alexa traffic rank, publication date, domain), then lets the API caller control ranking.

This inversion is critical for agent use cases: agents need precision, not approximation + ranking.

---

## Search for Agents vs. Search for Humans

This is the core product thesis:

> "It would kind of be insane if the same search engine optimal for humans would also be optimal for this very different creature."

Key differences:
- **Query form**: Humans type short keywords; agents "spit out like a paragraph or more explaining exactly what it wants" — rich, structured, precise
- **Result volume**: Humans want ~5 links; agents process thousands of results programmatically
- **Precision requirement**: Humans tolerate approximate results and click through; agents need high-precision retrieval or downstream hallucination follows
- **Latency tolerance**: Humans expect 500ms; agent workflows can tolerate minutes or hours for a thorough search

On variable compute: "People think of searches as taking 500 milliseconds...But what if searches can take a minute or 10 minutes or a whole day?" — this parallels o1's test-time compute scaling for reasoning. Harder queries get more compute.

---

## LLM-Based Labeling Over Human Annotation

Bryk argues that LLMs outperform human annotators for search relevance:

> "I actually think like you just — we get by, which we are right now doing using like LLMs as the labelers specifically for search."

Humans gravitate toward keyword matching when annotating relevance; GPT-4 captures semantic relevance better. This inverts conventional wisdom about human-labeled training sets being the gold standard.

---

## Business Economics

- Google's search monetization: ~$0.001 CPM via advertising
- Exa's advantage: front-loads compute during indexing; marginal per-query cost stays low as LLM inference prices drop "by 200X in like a couple of years"
- Perplexity and ChatGPT Search use Bing/Google APIs — avoiding infra costs but inheriting ranking quality limitations
- Exa's per-query pricing aligns incentives: "Our incentive is to make people like the search as much as possible... Whereas Google's incentive is making them click on ads."

---

## Product: Websets

Latest product launch: turns filtered search results into structured data grids — converting web pages into databases without manual scraping. Combines precision filtering with structured export. Target: enterprise research workflows (VC, competitive intelligence, lead generation).

---

## Key Quotes

> "The link prediction objective can be seen as like a neural PageRank because what you're doing is you're predicting the links people share."

> "We want to expand people's notion...you could actually get whatever you want."

> "Google is stuck in this links-based experience...tied to keyword-based matching."

> "It would kind of be insane if the same search engine optimal for humans would also be optimal for this very different creature."

> "Perfect search requires test-time compute... your search could sometimes take half a second, but sometimes it could take a minute or 10 minutes, or an hour or a day."

> "Even if you've crafted a great system prompt, you want to be part of the process itself."

---

## VERSO RELEVANCE

### [SHARPENS §5.4 memory / §5.2 context] Asymmetric embedding + Matryoshka already in Verso's corpus — link prediction as the training objective is new

The training mechanism (link prediction as neural PageRank) is the specific mechanism behind why Exa's embeddings are qualitatively different from generic sentence transformers. For Verso's just-in-time retrieval layer (RRF k=60 + asymmetric embeddings already known), this confirms that the *training objective* of the embedding model matters as much as the architecture. For agent memory retrieval, the ideal embedding model would be trained on a link-prediction-style objective over agent runs (predict which prior observation was referenced given a new context).

**Verdict:** SHARPENS §5.4. Not just "use asymmetric embeddings" but "the training objective of your embedding model determines retrieval quality for agent-specific corpora."

### [NEW-IDEA] Filtering-first retrieval architecture for agent tool results

Exa's architecture (filter precisely → rank optionally) is directly applicable to Verso's tool-result memory layer. When an agent retrieves from memory, it should filter first (semantic match + temporal + source-type metadata) before any ranking step. Current known design (RRF k=60) is a ranking-first approach. A filtering-first approach would reduce false positives in tool-result retrieval — especially important for long-running durable agents accumulating large observation histories.

**Verdict:** NEW-IDEA for §5.4 memory. Filter-then-rank vs. rank-from-full-corpus is an architectural choice with real precision implications at scale.

### [SHARPENS §5.3 tools] Variable-compute search as a first-class tool pattern

"Search can take a minute or 10 minutes or a day" is a tool design pattern: expensive tools should expose a compute-budget parameter. Verso's tool interface (§5.3) should support `tool.call(budget=ComputeBudget.HIGH)` or equivalent — tools that are natively variable-cost should expose that interface rather than forcing callers to use a fixed-cost version. This applies to search, code execution, and any tool with meaningful quality-vs-speed tradeoffs.

**Verdict:** SHARPENS §5.3. Adds a concrete interface requirement: variable-compute tools need a budget parameter, not a binary fast/slow switch.

### [CONFIRMS §5.3 tools / §12 positioning] Search rebuilt for agents, not humans, is the right market thesis

Exa's entire product is built on the observation that "the same search engine optimal for humans is not optimal for agents." This is the Verso thesis applied to search infrastructure: don't adapt human tools to agents, build for agents natively. The positioning parallel is direct — Verso's counter-position ("we don't force the graph") is the same move applied to orchestration.

**Verdict:** CONFIRMS §12 positioning. External validation of the "build for agents natively" thesis from a company that built the entire infrastructure stack on this bet.
