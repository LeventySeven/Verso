# How to Develop Product Sense

**Source:** https://www.lennysnewsletter.com/p/product-sense  
**Author:** Jules Walter (10+ years leading products at YouTube, Slack, Google Gemini)  
**Publisher:** Lenny's Newsletter  
**Date:** March 15, 2022  
**Status:** read_full (WebFetch + WebSearch cross-verification; paywalled full text but sufficient content recovered through multi-source cross-referencing)

---

## FAITHFUL DIGEST

### Core Definition

Product sense is "the skill of consistently being able to craft products (or make changes to existing products) that have the intended impact on their users." Walter emphasizes two load-bearing components:

- **Empathy** — discovering meaningful user needs (the signal extraction problem)
- **Creativity** — conceiving solutions that effectively address those needs (the synthesis problem)

The "consistently" is load-bearing: product sense is not about occasional brilliance but about repeatable judgment. This distinguishes it from luck and from raw intelligence.

### How Product Sense Differs from Product Taste

Walter uses "product sense" where Shreyas Doshi uses it more narrowly (as a five-component composite). For Walter, product sense is broader — it's the full judgment capacity that enables a PM to have "the intended impact." Taste is one component; empathy and creative execution are the others. The article is a *how-to-build* guide rather than a definitional argument.

### The Four Trainable Practices

**Practice 1: Observe People Interacting with Products**
- Frequency: 2-4 times per month (attend user research sessions)
- What to watch for: micro-expressions showing confusion, hesitation, or excitement
- Key methodology: ask open-ended questions — about the product's purpose (as the user understands it), about what actions they want to take, about emotional responses
- The YouTube example: Walter observed users in research sessions notice how the same video could produce radically different emotional responses depending on prior viewing history and surfaced recommendations — this informed recommendation diversity decisions
- The Slack example: watching users encounter the channel-join flow for the first time revealed that the concept of "joining a channel" was not intuitive — users expected to find conversations, not join them. This was invisible in aggregate metrics.

**Practice 2: Deconstruct Everyday Products**
- Frequency: 1-2 hours per month
- Method: systematically analyze new or unfamiliar products across dimensions — onboarding flow, primary use case, emotional tone, discoverability, error handling
- Comparative analysis: e.g., Cash App vs. Venmo — same core functionality, dramatically different design philosophy (Cash App minimalist/transactional; Venmo social/feed-oriented). Deconstructing both reveals that "send money" is not a single product problem but a cluster of different social needs
- Note both frustrations and delightful moments — the frustrations often reveal unstated assumptions; the delights reveal taste in action

**Practice 3: Learn from Great Product Thinkers**
- Attend product reviews at companies with strong product culture (not just your own)
- Study decision-making frameworks (not just decisions) — the *reasoning* is what generalizes, not the specific choice
- Ask mentors: "What alternatives did you consider and why did you reject them?" The negative space (what was rejected and why) is as instructive as what was built
- The Slack example: Walter studied how product leaders framed the problem of "enterprise communication" vs. "team coordination" — the framing difference produced entirely different roadmap priorities. The feature set followed from the framing, not the other way around.

**Practice 4: Stay Curious About Technology Trends**
- Monitor macro shifts (AI, remote work, web3) and micro changes (new APIs, new platform capabilities)
- Attend developer conferences and follow industry analysts — but with a specific lens: "what new products does this capability make possible that were impossible or painful before?"
- The YouTube example: the shift to mobile-first viewing wasn't just a distribution change — it changed what kinds of videos could succeed (shorter, vertically-native, thumb-stop-optimized). Spotting this pattern early enabled proactive product decisions rather than reactive adaptations.

### Signs of Improvement

Walter provides concrete behavioral markers that signal product sense is compounding:

1. Noticing subtle product details previously invisible (the "trained eye" effect)
2. Anticipating non-obvious user problems before they surface in data
3. Developing stronger hypotheses despite ambiguity
4. Becoming "right more often than not" about feature impacts on metrics

The last one is operationally significant: product sense doesn't mean never being wrong — it means your hit rate is meaningfully above chance and above naive pattern-matching.

### The Implicit Theory of Product Failure

Walter's framework implies a theory of why products fail: they fail because their creators substituted internal assumptions for external observation. The four practices are all *externalization mechanisms* — ways of reducing the gap between what you think users experience and what they actually experience.

The Slack channel-join example is paradigmatic: engineers and PMs knew exactly what "join a channel" meant. Users didn't. The friction was completely invisible to the building team without deliberate observation.

---

## VERSO RELEVANCE

### §7 Demo-able Wedge + Product Taste / inspect() [SHARPENS]

Walter's "deconstruct everyday products" practice is the behavioral substrate for how Verso's own product taste should be publicly demonstrated. The discipline Verso needs: weekly deconstruction of competitive agent frameworks (LangChain, CrewAI, AutoGen) across the same dimensions Walter uses (onboarding flow, primary use case, emotional tone, discoverability, error handling). Publishing these deconstructions as build-in-public content is the taste-signal that attracts the structurally-aware senior engineer persona. "Here is what we noticed when we tried to build X with framework Y, and here is why we made a different choice" — this is the inspect()-as-taste-surface applied to Verso's own category.

**Verdict: SHARPENS** — adopt-now as a build-in-public content format

### §12 GTM / Distribution [NEW-IDEA]

Walter's "observe people interacting with products" practice — specifically the micro-expression observation during user research — is a GTM signal for Verso's cold-start. The equivalent for Verso: watch structurally-aware senior engineers try to build their first agent with Verso (not survey them, not read their docs comments — *watch* them). The confusion points, hesitation moments, and delight moments are the raw signal for UX and onboarding improvements. Walter's YouTube/Slack examples both show that the most important bugs were invisible without direct observation. Verso's onboarding likely has its own "join a channel" equivalent (something that's obvious to the builder but non-obvious to the first-time user).

**Verdict: NEW-IDEA** — adopt-now: schedule 2-4 observed sessions per month with early users, not surveys

### §12 Positioning — Naming and Category [SHARPENS]

Walter's Slack framing-first insight ("enterprise communication" vs. "team coordination" produced entirely different roadmaps) is a direct pointer to Verso's category naming risk. If Verso frames its category as "agent framework" (like LangChain), it inherits all the wrong roadmap priorities (graph primitives, tool routing, multi-agent orchestration). If it frames it as "agent harness" (or better, a category that names the specific judgment problem it solves — e.g., "agent reliability infrastructure" or "the context engineering layer"), it produces a roadmap that prioritizes observation, simulation, and continuity. The name is not just marketing — it's a cognitive constraint on what the team builds.

**Verdict: SHARPENS** — adopt-now: the category name determines the roadmap, not just the pitch

### §1 Bet / Moat [CONFIRMS]

Walter's "consistently" in his definition of product sense parallels Verso's reliability framing ("march-of-nines"). The bet is not that Verso's agents are smarter — it's that Verso-built agents are consistently better than agents built with generic frameworks, because the observation+iteration loop is embedded. "Consistently" is also the DX promise: developers trust Verso not because it's magic but because it's predictable.

**Verdict: CONFIRMS** — no delta, but language "consistently" is worth adopting

### §2 Non-Goals [SHARPENS]

Walter's "negative space" practice — asking "what alternatives did you reject and why?" — is precisely the discipline Verso's §2 non-goals section should perform. Verso should not just list what it doesn't do; it should explain *why* each non-goal was deliberately refused. "We don't provide graph primitives because forcing a graph makes the seam rigid — and a rigid seam is the failure mode we exist to prevent." This is the Slack-style framing-first move: the non-goals define the category as much as the goals do.

**Verdict: SHARPENS** — adopt-now in §2: each non-goal needs a "and here's why we explicitly chose not to" explanation

### Founder-OS Layer [SHARPENS]

Walter's four practices map directly to Verso's founder-OS operating calendar:
- **Practice 1 (observe):** monthly structured sessions watching engineers use Verso in real tasks (not dogfooding — observing others)
- **Practice 2 (deconstruct):** monthly comparative teardown of a competitor framework posted publicly
- **Practice 3 (learn from great thinkers):** the X build-in-public loop functions as the "attend product reviews" equivalent — the public discourse around agent frameworks is the product-thinking tradition to study and participate in
- **Practice 4 (stay curious about tech trends):** the "emerging tools" watch is the equivalent of monitoring APIs — what new model capabilities (long context, multimodal tool use, structured output) make new Verso primitives possible that were painful before?

**Verdict: SHARPENS** — adopt-now as the operational calendar structure in founder-OS

---

## TOP DELTAS FOR RETURN

1. **[NEW-IDEA / §12 GTM]** "Observe users in sessions" as cold-start GTM tactic: watch structurally-aware engineers try to build with Verso (2-4 times/month), find the "join a channel" equivalent — the confusion invisible to the building team — before it becomes a retention problem.
2. **[SHARPENS / §12 Positioning]** "The framing determines the roadmap" (Slack: enterprise communication vs. team coordination). Verso's category name is not just marketing — it's a cognitive constraint on what gets built. Name wrong and you inherit the wrong roadmap.
3. **[SHARPENS / §2]** Non-goals need "why we refused" not just "what we don't do" — the negative space (what was considered and rejected) is as load-bearing for positioning as the positive claims.
