# How Glean CEO Arvind Jain Solved the Enterprise Search Problem

**Source:** Sequoia Capital Training Data Podcast, Episode 19  
**Speaker:** Arvind Jain, Co-founder & CEO, Glean  
**Hosts:** Sonya Huang & Pat Grady (Sequoia Capital)  
**Date:** October 29, 2024 · ~45 min  
**URL:** https://www.youtube.com/watch?v=dvJOQvBkg_U  
**Transcript source:** Sequoia Capital show-notes page (https://sequoiacap.com/podcast/training-data-arvind-jain/), supplemented by Unusual VC blog (https://www.unusual.vc/how-glean-found-product-market-fit-arvind-jain-on-enterprise-search-and-ai/) and Sequoia spotlight article (https://sequoiacap.com/article/arvind-jain-glean-spotlight/). No line-by-line transcript publicly available; content is from authoritative secondaries.

---

## What Jain Actually Argues

### The founding insight — enterprise search is not a crawling problem

Jain's core reframe: *"The biggest mistake everyone made was thinking enterprise search was a crawling and indexing problem. It's actually a knowledge graph and personalization problem."*

The problem was identified at Rubrik, Jain's previous company: *"I cannot find anything in this company. I don't know where to go and look for information."* The corpus was 300+ cloud SaaS applications, each with different APIs, different data formats, and — critically — different per-user permission structures.

Consumer search (Google) has three simplifying properties that enterprise search lacks:
1. The corpus is public — no permissions to enforce
2. Relevance can be inferred from aggregate click signals across all users
3. Documents are mostly static HTML — one crawler handles everything

In enterprise:
- *"Each individual has their own level of access to those systems. The CEO has access to different data than someone in R&D who has access to different data than someone in HR."* Every query must be personalized and permission-filtered in real time.
- Every app has unique APIs requiring custom integrations.
- Data lives in Slack threads, Jira tickets, Confluence pages, Salesforce records — no unified format.
- Relevance signals must be reconstructed from implicit behaviors (dwell time, recency, team-scoped engagement) because there's no cross-user click signal.

### The Glean architecture — four foundational layers before AI

Glean's differentiator is not the LLM layer — it's what lives beneath:

1. **Deep integrations** — custom connectors to every major enterprise SaaS (Salesforce, Confluence, Jira, Google Drive, SharePoint, ServiceNow, Slack, etc.)
2. **Permission/governance engine** — ensures every result shown to a user is only content that user is authorized to see, enforced at query time
3. **Enterprise knowledge graph** — transforms the entirety of a company's data into nodes representing people, documents, and the relationships between them; can be built in under two hours for a new customer
4. **Ranking system** — uses implicit signals: document engagement frequency, content recency, team-specific popularity, user-to-document associations from Slack/email, dwell time

The knowledge graph is what makes results both relevant and personalized. The same query ("what is our Q3 pricing strategy?") returns different results for the CFO and an engineer, not because the documents differ but because access and relevance both differ per person.

### Why naive enterprise RAG fails

Verbatim: *"You're chaining two imperfect technologies. Failure often happens at retrieval, not the LLM stage, when you can't find relevant knowledge."*

The standard enterprise RAG pattern (vector embed everything → nearest-neighbor retrieve → LLM synthesize) fails because:
- Vector search lacks permission awareness — it retrieves semantically similar documents regardless of access rights
- Vector search has no concept of recency, team-scoped relevance, or engagement signals
- Error compounds: if retrieval is imprecise, the LLM hallucinates or answers based on the wrong documents

Glean's RAG advantage: the retrieval layer is full enterprise search with the four foundational layers above. The LLM gets a pre-filtered, permission-correct, relevance-ranked context window. The retrieval quality is the differentiator.

### The agentic error-compounding problem

Jain articulates the fundamental constraint on agentic automation with precision: *"If each step is 90% accurate, a 10-step workflow drops to ~35% accuracy. Human input remains critical."*

Glean's current approach: expose a workflow engine allowing users to manually build complex automations (creating training data for future automated behavior). Human-in-the-loop is not a limitation to be engineered around — it's a source of grounding data.

Vision: proactive AI assistants that anticipate needs rather than wait to be queried. The shift from reactive to proactive is the key behavioral change — agents that surface relevant information before the user forms a query.

### Act 1 → Act 2: search infrastructure as platform moat

Glean's Act 1 (enterprise search product) creates the infrastructure for Act 2 (AI application platform):
- Customer trust established through a working search product
- Pre-integrated data pipelines with governance already built
- APIs so developers build on Glean's platform rather than building their own permission-aware data connectors

Verbatim: *"Glean is the Google or ChatGPT, but inside your enterprise. It's where employees ask questions and get answers using company knowledge."*

Verbatim: *"The majority of work we do today won't be done by us in five years. AI assistants will have access to all company data and context."*

### Technical scope decisions

Glean trains smaller, customer-specific language models understanding company-specific terminology, acronyms, and domain knowledge. They explicitly do not plan to build GPT-scale foundation models. Core competency is enterprise data integration, governance, and ranking. The LLM is a commodity they route to.

Success metric: 80% of user sessions result in successful question resolution, measured implicitly via click, dwell time, and follow-up query behavior.

---

## VERSO RELEVANCE

### [CONFIRMS §5.2 — context / retrieval] Retrieval quality is the real RAG bottleneck
Jain's central empirical finding: failure in enterprise RAG chains happens at retrieval, not at the LLM. This is a CONFIRMS for Verso's context-engineering emphasis (§5.2). The sophistication belongs in context assembly — the LLM is already good enough. The RRF k=60 + asymmetric embeddings pattern already known to Verso addresses exactly this; Jain provides the independent enterprise-scale evidence that retrieval quality is where the work belongs.
**Verdict:** Confirms §5.2; retrieval > LLM as the bottleneck is empirically validated at enterprise scale.

### [SHARPENS §5.2 — context] Permission-awareness as a first-class context constraint
Verso already handles permission filtering conceptually, but Jain's architecture makes explicit that permissions must be enforced at query time, not at index time — because what a user can see changes dynamically as roles shift. For Verso's context assembly, this implies: permission-check is a gate that runs before the retrieval step, not a property of stored documents. The ContextBundle.inspect() primitive should surface whether a retrieved chunk is permission-valid for the current RunContext.
**Verdict:** Sharpens §5.2 — permissions as a dynamic query-time gate, not a static document property.

### [SHARPENS §6.1 — durable / HITL] Error-compounding arithmetic → mandatory HITL at step N
Jain's 0.9^10 ≈ 0.35 formula is the cleanest quantitative argument for why Verso's tactical-to-durable seam (§4/§6.1) is not optional — it's mathematically necessary for multi-step workflows above a reliability threshold. At 90% per-step accuracy over 10 steps, human approval at step 5 (splitting the chain) restores ~0.9^5 ≈ 0.59 accuracy at each half. HITL is not ergonomic sugar — it's error-compounding mitigation. This gives Verso a precise quantitative framing for when to promote an agent to durable.
**Verdict:** Sharpens §4/§6.1 — HITL placement is an error-compounding optimization, not a UX preference. Provide the formula in docs.

### [NEW-IDEA — §5.4 / memory] Enterprise knowledge graph as memory topology
Jain's enterprise knowledge graph (people × documents × relationships × permissions) is a specific memory architecture: typed nodes, typed edges, access-controlled traversal. For Verso's 4-tier memory (§5.4), the "organizational" or "knowledge" tier could be modeled not as a flat vector store but as a typed graph with permission-scoped traversal. Query becomes: "find documents relevant to this query, accessible by this agent identity, prioritized by engagement signals in this team context." This is more structured than RRF alone.
**Verdict:** New memory topology idea for §5.4; probably out-of-scope for v1 but precise enough to be useful.

### [CONFIRMS §5.5 — evals] Implicit behavioral signals over explicit ratings
Glean measures success via implicit user behavior (dwell time, click, follow-up query patterns) rather than asking users to rate results. This is the same "embedded evals" philosophy Verso encodes in §5.5 — ground truth comes from behavioral trace, not survey. The 80% successful-session target is a concrete operational metric derived from behavioral signals.
**Verdict:** Confirms §5.5 — behavioral trace as ground truth is independently validated at enterprise scale.

### [CONFIRMS §12 — positioning] The infrastructure-first moat
Jain's Act 1 → Act 2 play is Verso's harness positioning articulated for enterprise search: the boring infrastructure work (integrations, permissions, ranking) is the moat; the LLM is the commodity. Verso's harness is the "boring infrastructure" that makes agents reliable — context engineering, evals, HITL, checkpointing. The generative layer is exchangeable (§6.4 cross-model failover). Jain's framing validates that the infrastructure player wins when LLMs are commoditized.
**Verdict:** Confirms §12 strategy — infrastructure moat outlasts model advantage.
