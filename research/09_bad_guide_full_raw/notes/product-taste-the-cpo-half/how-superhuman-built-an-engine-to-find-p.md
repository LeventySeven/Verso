# How Superhuman Built an Engine to Find Product/Market Fit
**Source:** https://review.firstround.com/how-superhuman-built-an-engine-to-find-product-market-fit/
**Author:** Rahul Vohra (CEO, Superhuman)
**Published:** First Round Review (date unspecified in content)
**Status:** read_full

---

## Faithful Digest

The single most operationally useful PMF essay in circulation. Vohra's core innovation: convert PMF from a vibes-based post-launch feeling into a measurable, improvable metric with a concrete survey instrument and a four-step loop. This is not theory — it is the playbook Superhuman actually ran, with before/after numbers.

### The Survey Instrument

One primary question, plus three follow-up questions:

**Q1 (the metric):** "How would you feel if you could no longer use Superhuman?"
- (A) Very disappointed
- (B) Somewhat disappointed
- (C) Not disappointed

**Q2 (persona):** "What type of people do you think would most benefit from Superhuman?"
**Q3 (core value):** "What is the main benefit you receive from Superhuman?"
**Q4 (blocker):** "How can we improve Superhuman for you?"

**The benchmark:** 40% "very disappointed" = PMF achieved. Below that = not there yet.

**Target population:** Users who have engaged with the product at least twice in two weeks (activated users, not signups).

**Superhuman's starting point:** 22% "very disappointed."

---

### The Four-Step Engine

#### Step 1: Segment to Find Supporters and Define the High-Expectation Customer

- Group all responses by Q1 answer
- Assign personas to respondents
- Focus ONLY on the "very disappointed" segment
- Ignore all other segments temporarily

**Key insight from segmentation:** Happy users describe THEMSELVES when answering "who would benefit most." This is how you get the HXC profile in the users' own language.

**Result:** Segmentation alone lifted Superhuman's PMF score from 22% to 32%.

**The HXC profile Vohra constructed:**

"Nicole is a hard-working professional who deals with many people. For example, she may be an executive, founder, manager, or in business development. Nicole works long hours, and often into the weekend. She considers herself very busy, and wishes she had more time... She spends much of her work day in her inbox, reading 100–200 emails and sending 15–40 on a typical day (and as many as 80 on a very busy one)."

This profile is specific enough to use as a filter. Not a demographic description — a behavioral pattern with named activities and volume.

#### Step 2: Analyze Feedback to Convert On-the-Fence Users Into Advocates

Two questions drive this step:
1. Why do the "very disappointed" users love the product? (from Q3)
2. What holds "somewhat disappointed" users back? (from Q4, filtered to the segment whose Q3 matches the "very disappointed" core value)

**Superhuman's finding on what lovers valued:**
- "Speed! The app is crazy fast, and the UX + keyboard shortcuts make me an actual superhuman"
- "Using Superhuman is so much faster than using Gmail. Not even close."
- Core themes: speed, focus, keyboard shortcuts

**Superhuman's finding on what held fence-sitters back:**
- Mobile app absence (primary blocker)
- Integrations
- Attachment handling
- Calendaring
- Unified inbox
- Search improvements
- Read receipts

**The critical discipline:** "Politely pass over the feedback from users who would not be disappointed if they could no longer use the product. They'll request distracting features, present ill-fitting use cases and probably be very vocal, all before they churn out and leave you with a mangled, muddled roadmap."

This is the most quoted passage in the piece. The word "politely" is doing heavy lifting — you are not dismissing users, you are protecting product integrity.

#### Step 3: Build Your Roadmap by Balancing Delight with Necessity

**The 50/50 split:**
- 50% doubling down on what users love (delight)
- 50% addressing what holds users back (necessity)

"If you only double down on what users love, your product-market fit score won't increase. If you only address what holds users back, your competition will likely overtake you."

**Delight half (Superhuman):**
- More speed: sub-50ms response times, instantaneous search
- More shortcuts: keyboard-first, pipeline keystrokes
- More automation: Snippets with attachments, CC automation, CRM/ATS integration
- More design flourishes: micro-interactions ("-->" → →)

**Necessity half (Superhuman):**
- Mobile app
- Integrations
- Attachment handling
- Calendaring
- Unified inbox
- Search
- Read receipts

**Prioritization method:** Cost-impact grid (low/medium/high × low/medium/high). For necessity items, impact = request frequency. For delight items, impact = product intuition from deep user empathy. Note: these require DIFFERENT cognitive modes.

#### Step 4: Repeat and Make PMF Score the North Star Metric

- Survey new users continuously (never re-survey same user)
- Track "very disappointed" % weekly, monthly, quarterly
- Build custom tooling for continuous measurement
- Make PMF score the ONLY key result in product OKRs

**Superhuman's results over three quarters:**
- Summer 2017: 22%
- After segmentation: 33%
- After three quarters of the full engine: **58%**

**Organizational effects:**
- Team grew 14 → 22
- NPS increased in parallel
- Users became "noticeably more vocal about how much they loved the product"
- Existing investors requested allocation in future rounds
- Outside investors sought investment opportunities

**Scaling caveat:** As you move beyond early adopters, new user segments are more demanding. PMF scores may drop. Solutions: network effects (Uber, Airbnb model) OR continuous quarterly roadmap rebuilding using this same process (SaaS model).

---

### The Paul Graham Underpinning

Vohra cites PG directly: "When a startup launches, there have to be at least some users who really need what they're making—not just people who could see themselves using it one day, but who want it urgently... you can either build something a large number of people want a small amount, or something a small number of people want a large amount. Choose the latter."

This is the HXC logic restated: intensity of need from a small segment > mild interest from a large one.

---

## VERSO RELEVANCE

### [NEW-IDEA] §12 GTM / cold-start — The PMF survey as Verso's Day 1 instrument

Verso has no survey infrastructure yet. The Superhuman engine should be adopted directly and immediately. The instrument maps cleanly:

**Verso PMF survey (adapted):**
- Q1: "How would you feel if you could no longer use Verso?" (very/somewhat/not disappointed)
- Q2: "What type of engineer do you think would most benefit from Verso?"
- Q3: "What is the main benefit you get from Verso?"
- Q4: "How can we improve Verso for you?"

Target population: engineers who have shipped at least one agent to production using Verso (the activated user equivalent).

40% threshold remains the benchmark.

**Verdict:** adopt-now — implement this survey in the GitHub repo (as a discussion template or Typeform link in the README) from Day 1 of public launch.

### [SHARPENS] §12 Positioning / persona — The HXC profile makes the structurally-aware senior concrete

Verso has named its primary persona as "the structurally-aware senior / AI engineer." The Superhuman method shows how to make that concrete: use the exact language that "very disappointed" users use to describe themselves and their workflow patterns. The HXC profile should name: how many agents they run in production, what failure modes they've been burned by, what their relationship to HITL/checkpointing is, and what they're currently using instead.

Draft HXC for Verso (to be validated against survey data):
"Alex is a senior engineer or tech lead at a product company who has already shipped one or more agents to production. They've been burned by silent failures, context window blowouts, or the inability to resume from mid-loop failures. They read the Anthropic engineering posts. They know the loop is ~10 lines. They resent frameworks that take power away from them. They want a harness that encodes the decisions they've already made, not one that makes decisions for them."

**Verdict:** adopt-now — build this HXC profile out; use it as the §12 persona anchor.

### [SHARPENS] §2 Non-goals — "politely pass over" the non-disappointed as a product discipline

The Vohra principle directly encodes Verso's non-goal discipline: the users who would not be disappointed without Verso are the vibe-coders and ML researchers. Their feedback will produce distracting features and a muddled roadmap. Deliberately ignoring them is not dismissal — it is product integrity. This gives Verso a named framework for saying no.

**Verdict:** adopt-now — reference this in the §2 non-goals section as the decision rule for roadmap filtering.

### [CONFIRMS] §1 Bet / moat — "intensity of need from a small segment > mild interest from a large one"

The PG citation Vohra deploys confirms Verso's bet: do not optimize for the mass market of vibe-coders and framework hoppers. Optimize for the small segment of structurally-aware engineers who need a harness with such intensity that losing it would be very disappointing. The moat is built on that intensity, not on breadth.

**Verdict:** confirm.

### [NEW-IDEA] §12 GTM — 50/50 roadmap split as Verso's ongoing loop

The 50/50 delight/necessity split gives Verso a concrete roadmap heuristic once PMF survey data starts arriving:
- Delight half: invest in what the structurally-aware engineers already love (the seam promotion, inspect(), the invariant encoding, the eval ergonomics)
- Necessity half: address the specific blockers preventing the "somewhat disappointed" segment from crossing to "very disappointed" (likely: ecosystem integrations, specific cloud deployment patterns, documentation depth for complex use cases)

The key discipline: treat these as requiring different cognitive modes — delight requires product intuition from deep empathy, necessity requires frequency-weighted prioritization from data.

**Verdict:** lock-defer — operationalize once first cohort of survey data exists.

### [SHARPENS] Founder-OS — PMF score as the ONLY OKR key result

Vohra made PMF score the only KR in product OKRs. This is a founder-OS operating principle: collapse the metric landscape to one number during the critical PMF window. Verso's equivalent is to track the "very disappointed" % as the only product health metric until it crosses 40%, and resist the temptation to add vanity metrics (GitHub stars, downloads, Twitter mentions) as substitutes.

**Verdict:** adopt-now — file in founder-OS / metrics operating principle.
