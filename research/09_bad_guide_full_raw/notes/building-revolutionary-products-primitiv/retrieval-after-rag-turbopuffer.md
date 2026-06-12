# Retrieval After RAG — Turbopuffer

**Source:** https://www.youtube.com/watch?v=Iu4gEnZFQz8
**Speaker:** Simon Hørup Eskildsen (founder, Turbopuffer)
**Host:** Latent Space (AI Engineer Podcast)
**Date:** ~March 2026 (episode aired 2025/2026)
**Format:** Podcast (~1h)
**Themes:** context, memory, multiagent, loop_harness, strategy
**Transcript source:** WebFetch of latent.space/p/turbopuffer (full show notes / detailed episode summary)

---

## Full Digest

### Origin Story: The Readwise Cost Gap

Turbopuffer started from a concrete pain point Simon encountered while "angel engineering" (three-month consulting stints at startups like Replicate and Causal post-Shopify). Readwise wanted to build a recommendation engine using embeddings — it worked well, but vector search would cost ~$30k/month against Readwise's $5k total infrastructure budget. This gap "haunted" Simon and became the founding question:

> "Why hasn't anyone built a truly cloud-native search database?"

### Three Convergent Platform Shifts (The Architecture Is Only Now Possible)

Turbopuffer's entire architecture depends on three infrastructure primitives that only recently became available simultaneously:

1. **NVMe SSDs in cloud** (2017): Earlier unavailable; now essential for the tiered storage model.
2. **S3 Strong Consistency** (December 2020): Eliminated the need for consensus layers (Zookeeper, etcd). Before this, any metadata system on S3 required distributed consensus.
3. **S3 Compare-and-Swap** (Late 2024): Enables metadata management without distributed consensus at all, finally vindicating Turbopuffer's architectural bet across all clouds.

The architecture in Simon's words: "You just put everything on object storage and you puff it into NVME when you use the data and you puff it into dram if you're querying it live."

**Napkin math foundation (before a line of code):** Simon documented:
- 25 GB/second to DRAM
- 5 GB/second writes to SSD
- S3 bandwidth per connection

Two-round-trip vector search: fetch cluster metadata (S3), fetch closest clusters (SSD/DRAM). Simple JSON files on S3 replaced traditional consensus infrastructure.

### Key Customer Stories

**Cursor (Early 2024):** Day after Turbopuffer launch, Cursor co-founder Arvid emailed with specific metrics. After a 4am call, Simon flew to SF to discover Postgres was down. Proposed tuning auto_vacuum and deeper integration.

> "We reduced their cost by 95%, which I think like kind of fixed their per-user economics."

Cursor's workload: embedding entire codebases with a proprietary embedding model, using semantic search plus grep patterns (hybrid retrieval). Published research shows "25% improvement" on specific agent accuracy benchmarks. The finding: semantic search improves agent accuracy "across all frontier models, especially in large codebases where grep alone falls short."

**Notion (2024–2025):** Required AWS-specific deployment; Turbopuffer was GCP-optimized. Simon's solution: buy dark fiber between AWS (Portland) and GCP (east of Portland, ~14ms via Seattle exchange) — cost $5,000. Absorbed cross-cloud egress costs internally rather than compromising on the S3-without-consensus architecture.

> "We don't wanna do this... we have so high conviction in not doing like a metadata layer on S3."

The conviction was vindicated when S3 Compare-and-Swap arrived in late 2024.

**Scale (2025):** 10x revenue growth, 5x headcount. Managing trillions of vectors and tens of petabytes. Customers include Cursor, Notion, Anthropic, Readwise. ANN-V3 achieves "100 billion vectors with P50 around 40 milliseconds and P99 of 200 milliseconds."

### The Agentic Retrieval Shift

This is the episode's sharpest forward-looking claim:

> "The new pattern is one agent firing many parallel queries at once, turning search into a highly concurrent tool call."

Traditional RAG: one retrieval call before LLM generation, optimized for sparse queries with low latency.

Agentic retrieval (Notion/Cursor agent behavior observed): "sometimes 8+ parallel requests" per single reasoning round. The optimization target shifts from latency minimization to **concurrent throughput over bursts.**

> "Agentic systems are dramatically increasing query volume... we expect retrieval infra to adapt to huge bursts of concurrent search rather than a small number of carefully chosen calls."

In response, Turbopuffer reduced query pricing 5x with further reductions planned.

### Why RAG Isn't Dead

Simon collects empirical case studies rather than speculating. Cursor's published data: semantic search + hybrid retrieval improves agent accuracy across all frontier models. As agent capability increases, retrieval precision requirements increase — sloppy retrieval becomes the bottleneck, not model capability.

Turbopuffer's evolution:
- **Act One:** Vector search exclusively
- **Act Two:** Full-text search (now competitive with Lucene on long, LLM-generated queries at web scale)
- **Future Acts:** Simple OLAP, time series, traces/logging — only after customer demand pattern validation

### Build vs. Buy in AI Era

The equation shifted: "from 'can we build it?' to 'do we have time?'" Notion's engineers sketched Turbopuffer's architecture on a napkin before finding the company. They chose to buy when they concluded: "if this team can feel like an extension of our team, we can go a lot faster."

### Fundraising Honesty

Told seed investor Lachy Groom: "If this doesn't have PMF by year-end, we'll return all the money... we don't wanna work on this unless it's really working." Groom: "I've never heard anyone say that before."

### The P99 Engineer Philosophy

Hiring framework: history of bending computer behavior to will; obsessive about systems (maps, trains, details); thinks in tradeoffs explicitly. Benchmark: Nathan achieved 40ms P50, 200ms P99 on 100B vector search. Default rejection unless a champion "fights" for the candidate.

Simon's philosophy on operating with limited information: "When I don't know how to play a game, I just play with open cards."

---

## VERSO RELEVANCE

**[SHARPENS §5.2 — Context Engineering]** The agentic retrieval pattern — agents firing 8+ parallel retrieval calls per reasoning round — directly sharpens the "just-in-time retrieval" claim in the PRD. JIT retrieval is not one call before generation; it's a concurrent burst pattern. Verso's ContextBundle / RRF k=60 design must account for parallel concurrent fetches, not a linear pre-fetch. The retrieval primitive is more like a parallel map than a sequential lookup.
*No-overkill verdict:* Sharpens design intent for ContextBundle; no new abstraction — just make sure the tool interface is async/concurrent-friendly.

**[CONFIRMS §5.4 — Memory]** Cursor's hybrid retrieval (semantic embedding + grep/regex patterns) and the "25% agent accuracy improvement" with semantic search across all frontier models empirically validates the 4-tier typed memory + asymmetric embedding design. The data shows semantic + keyword hybrid is not premature optimization — it's the empirically superior pattern.
*No-overkill verdict:* Confirms RRF + asymmetric embedding bet; no change needed.

**[NEW-IDEA — §6.2 / §5.3]** The pricing signal is structurally important: Turbopuffer cut query prices 5x specifically because agentic workloads create burst-concurrent patterns, not steady-state linear queries. For Verso's multi-agent architecture, this implies tool calls that hit retrieval infra should be designed for **burst concurrency** — async tool calls that can be parallelized within a reasoning step, not sequential. This is a concrete scheduling implication for the tool dispatcher in multi-agent settings.
*No-overkill verdict:* Flag for tool scheduler design — async parallel tool dispatch is the right default for retrieval tools.

**[CONFIRMS §12 — Positioning / Strategy]** The three-platform-shift story (S3 consistency 2020, NVMe, S3 CAS 2024) is a clean example of "primitive-first with receipts" — only build when underlying infrastructure makes the architecture possible. Verso's loop-is-not-the-product thesis rhymes: don't build the harness until the model primitives (async generators, structured outputs, MCP) are mature enough to build on. Timing matters as much as architecture.
*No-overkill verdict:* Strategic confirmation; no implementation change.
