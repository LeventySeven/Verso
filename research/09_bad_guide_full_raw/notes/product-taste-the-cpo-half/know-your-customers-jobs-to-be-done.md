# Note: Know Your Customers' "Jobs to Be Done"

**Source:** https://hbr.org/2016/09/know-your-customers-jobs-to-be-done
**Authors:** Clayton M. Christensen, Taddy Hall, Karen Dillon, and David S. Duncan
**Published:** September 2016, Harvard Business Review
**Format:** Article (medium length)
**Status:** read_partial — HBR paywall blocks full body text. Opening paragraphs and key thesis visible. Core framework reconstructed from: (1) the HBR podcast episode on the same theory, (2) FullStory's canonical summary, (3) a Medium synthesis (Jobs to Be Done, Milkshakes, and Online Learning — Ameet Ranadive), and (4) the Harvard Business School Working Knowledge writeup of the milkshake study. The framework content is well-documented in secondary sources that draw directly from this article and its companion book *Competing Against Luck*.

---

## Faithful Digest

### The Opening Problem
The article opens with a McKinsey statistic: **84% of global executives report innovation is extremely important to their growth strategies, but 94% are dissatisfied with their organizations' innovation performance.** Christensen et al.'s diagnosis: "most people would agree that the vast majority of innovations fall far short of ambitions." The root cause: product developers focus on building features and analyzing demographics rather than understanding *why* customers make purchasing choices — what progress they are trying to make.

### Core Thesis: The Job as the Unit of Analysis
"Customers are hiring products to fulfill a specific job in their lives." A *job* is defined as **"the progress that a person is trying to make in a particular circumstance."**

Two elements are non-negotiable: **progress** (solving a problem, improving a situation, achieving a goal) and **circumstance** (the context — who, when, where, and the emotional dimensions).

The framework insists: "Jobs are never simply about the functional — they have important social and emotional dimensions, which can be even more powerful than functional ones."

### The Three Dimensions of Every Job
1. **Functional:** What concrete problem needs solving?
2. **Social:** How does the solution affect one's standing among peers or in a community?
3. **Emotional:** What psychological needs or feelings are addressed?

The practical implication: companies that optimize only for the functional dimension leave themselves exposed to competitors who address the social or emotional layer.

### The Milkshake Case Study (canonical)
McDonald's wanted to increase milkshake sales and applied traditional demographic research + customer satisfaction improvements. No impact. Christensen's team reframed the question: what job are customers *hiring* this milkshake to do?

Discovery: **nearly 50% of milkshakes sold before 8 AM, by lone commuters who drove away immediately.** The actual job: "Help me stay awake and occupied while I make my morning commute more fun, keep me full until mid-morning." Competitors were not other milkshakes — they were bananas, donuts, bagels. The milkshake won because it took 20 minutes to consume through a straw, solving the boredom problem better than any alternative.

But in the afternoon, a different job emerged: **parents hired milkshakes to reward children**, competing not against beverages but against stopping at a toy store. Same product, completely different job, completely different competitive set, completely different design criteria.

Key quote: "People hired milkshakes for two very different jobs during the day, in two very different circumstances. Each job has a very different set of competitors...and therefore was being evaluated as the best solution according to very different criteria."

### The Southern New Hampshire University Case Study
SNHU identified an underserved job: non-traditional students (average age 30) wanted to "resume an aborted education at a later stage of their lives." These adults needed just four things: **convenience, customer service, credentials, and speedy completion**. SNHU's main competitor was not traditional universities — it was **doing nothing** (inaction, not a named competitor).

SNHU engineered toward the job: inquiry response time dropped from 24 hours to under 10 minutes; financial aid decisions accelerated from weeks to days; personal advisers maintained constant contact.

Result: growth to 75,000 students, $535M forecasted revenue, 34% compound annual growth. The insight: when your competitor is "doing nothing," you can grow a category rather than fight for share.

### Research Methodology: Jobs Insights Are Fragile Stories, Not Statistics
"Jobs insights are fragile — they're more like stories than statistics...Jobs Theory is not primarily focused on 'who' did something, or 'what' they did — but on 'why.'"

The recommended research method is qualitative story-based interviewing: "Tell me about a time when..." — capturing real-world context rather than survey preferences. Five components to uncover in each job story:
1. What progress is the person pursuing (functional, social, emotional)?
2. What circumstances surround the struggle (who, when, where, what activities)?
3. What obstacles block progress?
4. Are consumers using imperfect solutions or workarounds?
5. What defines "quality" and what tradeoffs are they making?

### Segmentation by Job, Not Demographics
The strategic implication: **segment markets by the job customers are trying to accomplish, not by who customers are.** Jobs cross traditional demographic and product-category lines. This reframes competitive analysis: your real competitors are everything that customers consider hiring to do the same job — often including inaction.

---

## VERSO RELEVANCE

### [SHARPENS] §12 — Positioning / Category Design: Verso's Job-to-Be-Done
The JTBD frame sharpens Verso's positioning problem. The question is not "what does Verso do?" but "what progress is the structurally-aware AI engineer trying to make, in what circumstance, and what job is Verso hired to do?"

Candidate job: **"Help me move an agent from a working prototype to a production-reliable system without rewriting it or adopting a foreign mental model — in an afternoon, not a sprint."**

This job has:
- Functional: get the reliability + HITL seam without architectural rework
- Social: I want to look like an AI engineer who ships, not one who got lost in framework hell
- Emotional: I want confidence that the agent won't silently degrade or get me paged at 2am

The one-flag durable promotion and agent.inspect() are direct functional job-solvers. But the social/emotional layer ("look like someone who ships", "confidence") is what makes the product feel like it belongs to this person. The Verso brand / demo register should address all three layers, not just the functional.
**Verdict:** sharpen — use the 3-layer job analysis to pressure-test the demo script and the landing page copy.

### [SHARPENS] §2 — Non-Goals: "Your competitor is doing nothing"
The SNHU finding — that the real competitor was inaction, not a named rival — is directly applicable to Verso's cold-start. The structurally-aware senior engineer's current solution for agent reliability is not LangChain or DSPy — it is **a hand-rolled `while True:` loop with ad-hoc retry logic, no checkpointing, and a mental note to "come back and fix this."** That is Verso's actual competitor: doing nothing systematic. This means Verso's wedge copy should not be "better than X framework" but "the upgrade path from your working prototype that you've been putting off."
**Verdict:** adopt-now — reframe GTM copy: the competitor is the engineer's own procrastination, not LangChain.

### [NEW-IDEA] §12 / §7 — Circumstance-specificity as positioning sharpener
Christensen's insistence that circumstances are more critical than buyer characteristics maps to a Verso positioning opportunity: the circumstance is *the moment the prototype starts failing in prod*. That is the triggering event, the "struggling moment" where the job becomes urgent. Verso should be positioned to appear in that exact circumstance — not before (when there is no pain) and not when the engineer is already three weeks into a full redesign (too late). The demo-able wedge is exactly this: show the user the one-flag promotion at the moment of "my ephemeral agent needs to be durable."
**Verdict:** sharpen — timing the positioning narrative to the "struggling moment" (first prod failure / first 2am page) sharpens the demo script.

### [CONFIRMS] §7 — The Milkshake Multi-Job Problem as Anti-Flexibility Warning
The morning vs. afternoon milkshake jobs are *different products with the same name*. The lesson for Verso: different user segments (the solo AI engineer vs. the platform team vs. the ML researcher) are hiring the framework to do different jobs. Serving all of them equally is the "design for everyone" trap. The current Verso primary persona (structurally-aware senior AI engineer) correctly selects the morning-commute job and refuses to optimize for the afternoon job. This is exactly right — the note confirms that opinionated persona lock = stronger product, not market limitation.
**Verdict:** confirm — JTBD validates the persona lock; do not widen it.

### [NEW-IDEA] Founder-OS — Story-Based Customer Research Protocol
The JTBD research method (story-based interviews, "tell me about a time when...") is the right protocol for Verso's early user research as it expands beyond the founder-as-first-user stage. The five questions (what progress? what circumstances? what obstacles? what workarounds? what quality tradeoffs?) should be the literal interview guide for early Verso users. This is how to identify which agent failure mode is the highest-frequency job to solve next.
**Verdict:** adopt-now — use as the Verso user research interview protocol.

---

## One-Line Verdicts per Finding
- 3-layer job (functional/social/emotional) → pressure-test demo + landing copy: **sharpen**
- Competitor = doing nothing → reframe GTM copy away from "better than LangChain": **adopt-now**
- Circumstance-specificity → position at the "struggling moment": **sharpen**
- Multi-job / morning vs. afternoon → confirms persona lock: **confirm**
- Story-based interview protocol → Verso user research guide: **adopt-now**
