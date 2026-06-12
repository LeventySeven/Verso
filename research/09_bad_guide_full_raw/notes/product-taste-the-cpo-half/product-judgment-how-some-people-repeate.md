# Product Judgment: How Some People Repeatedly Create Product Success

**Source:** https://www.intercom.com/blog/product-judgment/
**Author:** Paul Adams, CPO at Intercom (ex-Google, ex-Facebook, former UX research)
**Type:** Long-form essay (~20 min read)
**Date fetched:** 2026-06-12

---

## Faithful Digest

### The Central Claim: Product Judgment is Real, Learned, Domain-Specific

Adams opens with the uncomfortable framing: Product Judgment (also called Product Intuition, Instinct, or Taste) is the ability to "use your own judgment to (1) accurately predict what your customers need, want and value, and (2) design and ship the right solution for them." His first thesis: it is not innate. It is learned. It exists on a spectrum from very weak to very strong, and deliberate work is required to build it.

Operational definition — Product Judgment in practice:
- **Roadmapping:** "The person with great product judgment can accurately predict which [feature ideas] will be better for customers. They simply don't ship changes that people don't value."
- **Scoping:** Finding "the right balance between shipping value sooner by building less, while still solving the customer problem. They don't waste any effort."
- **Designing:** Being able to "predict which workflows customers will take and how design changes impact those paths."

The core mechanism: Product Judgment is obtained **only through direct experience with customers**. "The more direct experiences you have with real customers doing real things, the faster your product judgment grows." This is the load-bearing claim the rest of the essay builds on.

### The Non-Transferability Problem (The Most Counter-Intuitive Argument)

The most important and uncomfortable claim in the essay: **Product Judgment is domain-specific and does not transfer across domains.**

Adams tells a personal story: before Intercom (B2B), he had worked on Gmail and YouTube (consumer). He assumed communication software is communication software. "I incorrectly assumed that if I had designed products for people communicating with their family and friends, I could design products for people communicating with businesses. I was wrong, and I made mistakes."

The hard lesson, stated without softening: "There is no other way" to build judgment in a new domain besides talking directly to customers in that domain.

Domains include:
1. The industry (consumer vs B2B, etc.)
2. The type of problem being solved
3. The sub-domains WITHIN building a product: how it is designed vs. how it is priced and positioned vs. how it is roadmapped

Critical distinction: "You can talk to customers about how they perceive value in your product, how they think about your competitors, and that conversation will improve your Product Judgment on making roadmap decisions. It won't help you at all in designing workflows and UI." The judgment you build in one domain does not automatically port.

### The Three Rates of Change Model

Adams introduces a tripartite model for understanding which product knowledge ages well:

**Category 1: Things that never change** — rooted in human psychology. Cognitive biases, how we interpret shapes and forms. These are highly transferable. "You can learn these in many good books, but to truly internalize them you need to see them in action."

**Category 2: Things that change slowly** — e.g., internet software design patterns. Wild divergence early, then extreme convergence happened "about 10 years ago." The fundamentals of how internet software is designed haven't changed much since. This judgment is highly transferable: "If you have observed hundreds and hundreds of people using internet software, you see the same design patterns work and fail time and again, and so can predict with great accuracy the fundamentals of where a new proposed design will be confusing."

**Category 3: Things that change fast** — brand new product types, new competitor innovations, macro socio-economic changes that "alter our perceived reality in the blink of an eye." This is where dogma is most dangerous.

Key warning from this model: "With experienced leaders and practitioners, there is a danger of giving yesterday's advice today. To avoid dogma, you must continually ask: what has changed?"

### What Counts as Direct Experience (and What Doesn't)

Adams is explicit about what DOES NOT build Product Judgment:
- Reading summarized lists of feature requests
- Reading survey data
- Reading research reports from your research team
- Watching video recordings of customer interviews (your research team does the watching and shows you clips) — "This is not enough. Observing a recording is certainly better than reading reports or lists, and so it helps a little bit, but that is a very slow path."
- Talking to internal Sales and Support teams who talk to customers

"The indirect sources of customer insight above are all really important because they can help round out your Product Judgment, but they can't create it."

What DOES work: direct, personal, wide-ranging observation and conversation with real customers using the real product.

### The Researcher Paradox

The essay contains a sharp observation about researchers: Despite being the people who talk to customers most, they often don't have strong Product Judgment. "It is one thing to talk to customers and build judgment, it is another to apply it." Researchers "often stop short of applying it. They hand over the insight, they don't own the impact of the insight."

Adams's prescription: "blur roles and responsibilities, so they can learn how to apply what they are learning. For the same reasons I want PMs and Designers talking directly to customers...I want Researchers sketching solutions, talking to Engineers about how to build them, and building fully rounded Product Judgment by applying what they have observed."

### Quantifying the Journey

Adams gives concrete benchmarks:
- "To build strong Product Judgment in a specific domain, the answer is at least over 100 customers."
- "For true proficiency, built over years, you're looking at talking directly to many hundreds if not over 1,000 customers."

Personal data points:
- At Flow (UX consultancy): interviewed and observed 500+ people using internet software (~3/week, clustered into 5-6/day sessions) — built judgment for software usability and cognitive bias patterns
- At Google (4 years): interviewed ~800 people using Google products, competitor products, or design proposals/prototypes
- At Intercom: domain was new (B2B), had to rebuild judgment from scratch in early years

Speed hack: "5-6 people each day for 3-4 days in a row" — clustering dramatically fast-tracks domain judgment.

### The Self-Awareness Signal

A telling heuristic: "People with strong Product Judgment are very good at saying when they don't have that judgment, because they deeply understand how it is accumulated." Strong Product Judgment = knowing your own limits.

Contrast: "Many people think they have strong Product Judgment but don't...they see other leaders do it well, and imitate them, creating a cargo cult."

The proxy for distinguishing strong vs. fake Product Judgment: interest in talking to customers. "You can often identify strong/weak Product Judgment by using interest in talking to customers as a proxy."

### On Experienced Leaders Who "Just Know"

"An experienced leader with deep Product Judgment can often look at something and know what to do, but find it hard to explain. They just know this is the right option, and they are often correct. This is because their brain is using lessons learned from years of direct customer interaction, synthesizing it all subconsciously, and shortcutting to the recommendation." (Reference to Kahneman's Thinking, Fast and Slow System 1.)

Problem: senior leaders with poor Product Judgment exhibit identical behavior from "a place of false confidence and ego." The only way to tell the difference is their history of customer engagement.

---

## VERSO RELEVANCE

### [SHARPENS] §7 / Product Taste: Domain-Specificity of Judgment — the "No Cheap Transfer" Warning

**Finding:** Product Judgment does not transfer across domains. Adams's account of moving from consumer (Gmail/YouTube) to B2B (Intercom) and making mistakes is a precise warning for VERSO's founder operating in a new domain (agent framework builders / structurally-aware senior engineers). The 100-customer threshold for competence and 1,000+ for proficiency is a concrete operating target.

**Verdict:** adopt-now — the founder needs 100+ direct conversations with the primary persona (senior AI engineers) before their own judgment is reliable in this specific domain. Do not rely on transferable framework intuitions. Keep a customer conversation count.

### [SHARPENS] §12 / GTM + Positioning: Why DX-Led Organic Channel Works (and What It Requires)

**Finding:** Adams's model explains why dogfooding + DX-led organic GTM (the VERSO hypothesis) is the right channel but also clarifies its constraint: the founder must be doing direct, wide-ranging conversations with users — not just watching GitHub issues or reading Discord, not outsourcing to user interviews run by others. The "you must use the product yourself" section maps directly to VERSO's dogfood-first positioning.

**Verdict:** sharpen — the GTM plan should include a structured direct-convo cadence (not just passive channel observation), and the founder should track conversation count explicitly.

### [NEW-IDEA] §2 / Non-Goals: The Three-Rates-of-Change Model as a Feature Refusal Heuristic

**Finding:** Adams's tripartite model (never-changes / changes-slowly / changes-fast) gives VERSO a precise tool for deciding what to build vs. what to refuse. Things in Category 1 (human psychology, reliability intuitions) can be treated as stable invariants. Things in Category 3 (model behavior, emergent agentic patterns) are fast-changing and require fresh direct observation rather than relying on transferred intuitions from, e.g., traditional distributed systems.

**Verdict:** lock-defer — useful internally as a reasoning frame for the founder when justifying non-goals to users or investors. Not something to surface in the product or docs yet.

### [CONFIRMS] §1 / Bet/Moat: Judgment-as-Accumulation Supports the Harness Corpus Flywheel

**Finding:** Adams's framing of judgment as domain-specific accumulated observation is structurally isomorphic to VERSO's eval corpus flywheel (Aggregation Theory angle). The more an agent framework sees diverse real-world runs, the better it can predict what breaks — this is domain-specific judgment encoded in corpus form. The essay doesn't use flywheel language but confirms the underlying mechanics.

**Verdict:** confirm — already in the moat framing; no change needed.

### [SHARPENS] Founder-OS Layer: The Cargo Cult Warning

**Finding:** "Many people think they have strong Product Judgment but don't...they see other leaders do it well, and imitate them, creating a cargo cult. This is a very common problem in tech, and the cause of many failed startups." This is a direct warning for VERSO's positioning language. The anti-framework counter-position must not itself become cargo-cult contrarianism (being anti-LangChain because it's cool to be anti-LangChain). The proxy test: can the founder point to 100+ direct customer conversations that validate the counter-position?

**Verdict:** adopt-now — use the customer-conversation count as a discipline device in the founder-OS layer. The cargo cult failure mode is real.

### [NEW-IDEA] §7 / Product Taste: The Researcher Paradox as a Product-Role Warning

**Finding:** Researchers who gather insight but don't apply it build weak judgment. This maps to a VERSO internal risk: if the founder observes lots of user behavior but doesn't personally sketch, implement, and ship against that signal, the judgment built is incomplete. The "blur roles and responsibilities" prescription means the founder should be doing user interviews AND writing code AND making UX calls — not separating these.

**Verdict:** adopt-now — no research-vs-implementation separation. The founder should close every observation loop with a code or design decision.

---

## One-Line Verdicts per Finding

| Finding | Verdict |
|---|---|
| Domain-specificity of judgment: 100 → 1,000+ customer conversations | adopt-now |
| Three-rates-of-change model as refusal heuristic | lock-defer |
| Cargo cult contrarianism warning | adopt-now |
| Researcher paradox: observation without application | adopt-now |
| Judgment-accumulation confirms eval corpus flywheel | confirm |
| DX-led GTM requires structured direct-convo cadence | sharpen |
