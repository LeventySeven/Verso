# How To Build The Future: Aravind Srinivas

**Source:** Y Combinator "How To Build The Future" series  
**Speaker:** Aravind Srinivas, Co-founder & CEO, Perplexity AI  
**Interviewer:** David Lieb (YC General Partner)  
**Date:** February 21, 2025 · ~34 min  
**URL:** https://www.youtube.com/watch?v=SP7Ua8FKZN4  
**Transcript source:** No verbatim public transcript found for this specific YC HTBTF episode. Content below draws on: Singju Post transcript of a related Perplexity talk (https://singjupost.com/aravind-srinivas-perplexitys-race-to-build-agentic-search-transcript/), Stanford GSB writeup (https://www.gsb.stanford.edu/insights/perplexitys-aravind-srinivas-infinite-value-knowledge), and secondary coverage of the YC HTBTF episode from multiple aggregator summaries. Status: **read_partial** — core arguments are confirmed across multiple sources; specific verbatim quotes from the HTBTF YC episode are not available.

---

## What Srinivas Actually Argues

### Kill the ChatGPT-clone impulse — redefine the category

Perplexity launched two months before ChatGPT (August 2022 founding, public product pre-ChatGPT). The founding insight was that the answer to user search intent is not ten blue links and it's not a chatbot — it's *"What if we just give answers and cite the relevant sources."*

The explicit anti-position: building a ChatGPT clone was the wrong move. ChatGPT is a general-purpose conversational model. Perplexity's product is an answer engine with a specific contract: every claim is grounded in a cited source. The category definition matters — "answer engine" sets user expectations differently than "chatbot" or "search engine."

Verbatim: *"We're not building a search engine… We're building an answer engine."*

The PMF signal came on New Year's Eve (Dec 31, 2022 / Jan 1, 2023) when Perplexity handled *"close to 700,000 queries"* despite poor branding, slowness, and limited infrastructure. Users were actively sharing screenshots. That organic sharing behavior — not the query count — was the signal: product-market fit beyond novelty.

The doubling mechanism: adding follow-up question capability doubled average session engagement time and increased daily query volume. This showed the interaction model was right — users wanted to explore a topic, not extract a single fact.

### Citations as identity and trust infrastructure

Perplexity's citations were not an afterthought — they became a core identity marker differentiating them from all other AI products at a time when hallucination was the dominant criticism of LLMs:

*"We are the most focused on getting as many answers right as possible."*

The Stanford GSB framing: citation is adapted from academic standards — *"every sentence needs… citation."* This imposes a design constraint on the system: the LLM is prompted to attribute every factual claim to a specific document or source section, not to synthesize freely.

Practical consequence: Perplexity separated answer integrity from monetization. Google's structural problem is that their business model (ads in search results) creates an incentive to surface commercial links over direct answers. Perplexity monetizes through subscriptions and suggested follow-up questions — the answer itself is not manipulated by revenue considerations.

### Technical approach: bet on model commoditization, win on the application layer

Perplexity's architecture:
1. User query → query classifier (determines freshness vs. accuracy tradeoff)
2. Targeted multi-source web search (purpose-built, not Bing API — Bing's relevance model is "what would a user click?" not "what document has the needed information?", different objectives)
3. Candidate documents → LLM synthesis (GPT-4, Claude, or proprietary models depending on tier)
4. Inline citations: every sentence linked to a source section

Srinivas's explicit bet: *"Models are going to get increasingly commoditized"* while application-layer differentiation (summarization, referencing, formatting, custom UIs across verticals) remains valuable. This means Perplexity's moat is not the model — it's the retrieval pipeline, the citation UX, and the trust brand built around accuracy.

The "dumb approach" insight: Srinivas chose a *"simpler, less resource-intensive method"* for retrieval rather than building complex indexed systems per domain. As LLMs improved at inference time, the simpler retrieval approach became more valuable — the model could do more synthesis work, reducing the need for sophisticated pre-processing. Betting on model improvement to compensate for simpler retrieval turned out to be right.

### Competing against Google as an AI-native product

Google's structural disadvantage identified by Srinivas: their business model prevents them from offering direct booking links (flights, hotels, restaurants) without cannibalizing affiliate revenue from their advertising clients. An AI answer engine can say "book this flight for $350" without the constraint. There was also a historical moment: *"Maybe it was so good that you needed AI to kill it basically"* — referring to Google's own search quality, which created such high user expectations that only an AI-native product could meet them.

The incumbent's curse: Google must maintain ad revenue while improving search — these are in tension. Perplexity has no such tension; it can optimize answer quality without considering which answer generates ad revenue.

*"Speed is really the weapon that the startup has against an incumbent."*

### Future: from answers to actions

Srinivas articulates a clear evolution path: answer engine → action engine. Users want not just information but task completion — booking flights, buying products, making reservations. This requires:
- Browser-level integration (Comet Browser, launched October 2025 — free AI-powered browser with 800+ app integrations)
- Multi-step agent reasoning that goes beyond single-query-single-answer
- Partnerships or APIs into transaction systems

This is the "boring work" analogy: similar to how Google had to build Finance, Shopping, and Flights integrations. Perplexity now has to build the transaction rails that make actions possible.

### Team and culture

- Primary metric: daily query volume (raw signal of utility)
- Culture: *"brutal honesty"* about bugs and product deficiencies
- Meeting style: *"Start meetings with questions, not with presentations"*
- Bias for action over deliberation: *"extreme bias for action"*
- User philosophy (inherited from Google's early days): *"The user is never wrong"*

---

## VERSO RELEVANCE

### [CONFIRMS §12 — positioning] Build AI-native against incumbents, not AI-adjacent
Srinivas's story is the canonical AI-native vs. incumbent case study. The key move: refuse to clone the incumbent's product (ChatGPT for conversation, Google for links), instead redefine the category with a product that incumbents structurally cannot build without cannibalizing their existing revenue streams. Verso's positioning against graph-heavy frameworks (LangGraph, Crew) follows the same logic: don't build "a simpler LangGraph," build "the thing LangGraph makes impossible to build simply." The category is "no-overkill agentic harness," not "another orchestration framework."
**Verdict:** Confirms §12 positioning playbook — category redefinition beats feature competition.

### [SHARPENS §5.2 — context / retrieval] Query classification before retrieval is load-bearing
Perplexity's query classifier (freshness vs. accuracy tradeoff — factual/historical → prefer older reliable sources; news/recent → prioritize freshness) is a retrieval router that runs before any document retrieval. This is already known to Verso (RRF + retrieval strategy selection), but Srinivas makes concrete what the classifier dimensions are: time-sensitivity of the answer domain, not just semantic similarity of the query. For Verso, a RetrievalRouter should expose these dimensions explicitly: cache-first vs. fresh-index-first vs. no-retrieval.
**Verdict:** Sharpens §5.2 — time-sensitivity as a first-class retrieval routing dimension, not just query semantics.

### [SHARPENS §6.4 — model] Commodity model + application-layer moat is the right bet
Srinivas explicitly chose to use APIs (GPT-4, Claude, etc.) rather than train proprietary models, betting on commoditization. Verso's §6.4 cross-model failover architecture is the correct response to the same bet: if models commoditize, the agent harness must be model-agnostic with clean abstraction over providers. The moat is the harness quality (context engineering, evals, reliability), not model ownership. This independently validates Verso's model-abstraction layer.
**Verdict:** Sharpens §6.4 — model-agnostic harness is the right architecture when betting on model commoditization.

### [NEW-IDEA — §5.5 / evals] PMF signal = organic sharing behavior, not aggregate metrics
The New Year's Eve moment: Srinivas's PMF signal was not "700K queries" — it was users sharing screenshots unprompted despite the product being slow and poorly branded. For Verso's embedded evals (§5.5), this suggests a behavioral signal tier above task-completion rate: unprompted re-use and sharing of agent outputs. A Verso eval primitive could track "agent output was voluntarily shown to another person / saved / acted upon" as a higher-quality PMF signal than automated scoring.
**Verdict:** New evals signal idea for §5.5 — organic re-use as a tier above task-completion rate. Out-of-scope for v1 but worth noting.

### [CONFIRMS §5.2 — context] Separation of retrieval objective from clickthrough objective
Srinivas's specific critique of Bing API: its relevance model optimizes for "what would a user click?" rather than "what document has the needed information?" These are different objectives. For Verso's context assembly (§5.2), the same distinction applies: a retrieval step optimized for LLM consumption should rank by information density and relevance to the query intent, not by user engagement with the document. Verso's RRF + asymmetric embeddings already points this direction; this confirms the objective function must be explicitly decoupled from engagement signals.
**Verdict:** Confirms §5.2 — retrieval objective (information relevance) must be explicitly decoupled from engagement-based ranking.
