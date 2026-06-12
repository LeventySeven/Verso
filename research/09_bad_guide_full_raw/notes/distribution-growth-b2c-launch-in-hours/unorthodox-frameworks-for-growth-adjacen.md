# Unorthodox Frameworks for Growth: Adjacent Users — Bangaly Kaba

**Source:** https://www.youtube.com/watch?v=Ub9UkWByFIQ  
**Also at:** https://www.lennysnewsletter.com/p/frameworks-for-growing-your-career-bangaly-kaba  
**Format:** Lenny's Podcast, ~1h42m  
**Speaker:** Bangaly Kaba — early growth PM at Facebook, Head of Growth at Instagram (40M→200M+), VP Product at Instacart, Director of Product at YouTube  
**Transcript status:** YouTube video cannot be watched; Lenny's Newsletter URL is paywalled. Content synthesized from: (1) Andrew Chen's blog post "The Adjacent User Theory" (andrewchen.com) — the canonical long-form write-up of the same framework Kaba presents, (2) Recall.it summary, (3) PodPulse notes, (4) Bash content summary. **Status: read_partial.** The Andrew Chen post is the primary content source; it reproduces the Instagram/Instacart examples Kaba discusses in the podcast.

---

## Core Framework: The Adjacent User Theory

**Definition:** Adjacent Users are people who are **aware** of a product and may have tried it, but who struggle to become engaged users due to adoption barriers in the product's current positioning, UX, or value proposition. They sit in orbit around the product's successful user states — equally likely to drift away or cross into activation.

> "Solving for the adjacent user is not short-term thinking; it is disciplined sequential execution that enables longer-term roadmaps and faster growth."

The central claim: most hypergrowth companies stall not because they've run out of market, but because they've run out of **adjacent user clarity**. The gap between their current retention curve and the theoretical maximum represents untapped value within existing product-market fit — not a new market.

---

## Why Teams Miss Adjacent Users

**1. Power User Gravity**
Product teams become power users themselves, unconsciously building for people who already love the product. This requires "crossing a cognitive threshold" — actively seeing the product through the eyes of someone who almost converted but didn't.

**2. Persona Limitations**
Traditional personas describe *current* users, not *future* ones. They are static, lack actionable specificity for edge segments, and don't surface the barriers adjacent users actually face.

**3. Home Run Mentality**
Teams overvalue large swings targeting entirely new markets instead of "hitting 100 singles" — sequential wins among immediately adjacent segments. The singles compound faster than swing-and-miss.

---

## Detection Signal: Cohort Decay

The primary signal that adjacent users exist: **conversion metrics decline cohort-over-cohort** as new user types enter the funnel state. "New channels (especially paid) typically signal to product that adjacent users are coming." When you turn on paid acquisition, you get a mix of core + adjacent users — and adjacent users don't convert, revealing the gap.

---

## The Instagram Case

- Key activation threshold: "If a user had more than 10 followers in the first 7 days after signing up there was over a 65% chance that the user would become activated."
- Adjacent user problem: a specific segment consistently failed to reach 10 followers — not because they didn't want to, but because Instagram's interface didn't match their discovery behavior, device type, or language expectations.
- Solution: Instagram built "Air Traffic Control" — an internal testing environment that simulates different network speeds, languages, and device permutations — to experience the product as these users would.
- International expansion: web presence + SEO improvements contributed "a 10% growth bump upon launch" for international markets where the app-first assumption broke down.
- Research method: discovered that some users logged out due to data plan concerns or shared devices — a **cultural insight** entirely unrelated to product failures but blocking activation.

> TikTok's counter-strategy: specifically targeted "users who were not successful on Instagram by offering them the opportunity to succeed on TikTok" — a direct adjacent user strategy against a competitor.

---

## The Instacart Case

Successful Instacart users were: female, urban, specific cities, heads of household with children, more affluent, less price-sensitive, willing to invest time building orders (large, planned carts).

Adjacent user hypothesis: lower-intent users who wouldn't invest an hour building a cart. When Instacart expanded acquisition channels, new users arrived who faced tens of thousands of products without intent to build a large order. The friction point: discovery architecture optimized for high-intent users was a barrier for lower-intent adjacent users.

---

## Discovery Process (Four Steps)

**Step 1: Map Success Attributes**
Identify what makes current users successful — each attribute creates an expansion vector. (Instacart: female → male heads of household; urban → suburban; high-intent → lower-intent.)

**Step 2: Build Adjacent Hypotheses**
Bottoms-up data: where do users drop during critical flows? The drop point identifies the barrier.

**Step 3: Build Empathy (Four Methods)**
- **Be the Adjacent User** — simulate their environment (device, network speed, language)
- **Watch the Adjacent User** — usability testing; observe workarounds before helping
- **Talk to the Adjacent User** — uncover cultural/behavioral insights that data misses
- **Visit the Adjacent User** — observe authentic workflows in actual environments

**Step 4: Sequence Carefully**
- Adjacent users should differ on only **one or two attributes**. Multi-attribute segments require a new value proposition (a home run swing, not a single).
- Not all adjacent segments are strategically worth pursuing — Instagram deprioritized second-account features despite data showing the behavior, because it conflicted with strategic focus.
- Solve for existing users driving additional monetization first; then users driving indirect value; then new adjacent prospects.

---

## Sequencing Rule on Growth Trajectory

When Slack evaluated international expansion, India's faster growth trajectory and clearer monetization hypothesis made it higher ROI than France's larger but static user base. **A smaller segment growing rapidly can outpace a larger, stagnant one** over meaningful time horizons.

---

## Continuous Adaptation

Adjacent user definitions shift constantly through three mechanisms:
1. **New information** (experiment results, new instrumentation, research)
2. **New user influx** (solving for one segment brings adjacent types via word of mouth)
3. **New value props** (feature launches alter activation requirements — Instagram Stories made activation harder initially because new users needed more accounts to follow for content)

> "Repeatedly cross the cognitive threshold of seeing through your adjacent user's eyes."

---

## VERSO RELEVANCE

### [NEW-IDEA §12 GTM — adjacent user as the Verso cold-start diagnostic]
**Finding:** Kaba's framework is directly applicable to Verso's cold-start problem. Verso's core user is the structurally-aware senior/AI engineer (lead choosing a harness for 2nd/3rd production agent). The adjacent user is: (a) the ML researcher who understands agent loops but hasn't owned production ops, or (b) the senior engineer who is writing their first agent and hasn't yet hit the reliability wall. The drop point is different for each. Without this diagnostic, Verso risks building onboarding for the core user while the adjacent user churns silently.
- **Verdict:** NEW-IDEA: run the adjacent user diagnostic before any GTM expansion. Map the activation threshold for Verso's core user (first successful harness-vs-raw-loop comparison?), then identify who is failing to cross it and why. That failure is a product problem masquerading as a distribution problem.

### [SHARPENS §12 GTM — cohort decay as the GTM health signal]
**Finding:** Kaba's cohort decay signal is the leading indicator of "you've saturated your current segment and are now pulling in adjacent users who don't convert." For Verso: when conversion from "downloaded/installed" to "ran first eval" starts declining across weekly cohorts, it signals adjacent users are arriving — likely from referrals by early adopters who have different use cases or experience levels. The response is not more marketing; it is a product investigation.
- **Verdict:** Sharpens Verso's GTM metrics: track conversion-to-first-successful-eval by cohort from day one. Cohort decay is the canary.

### [CONFIRMS §12 GTM — sequential singles over home run swings]
**Finding:** Kaba's "100 singles" principle directly confirms Verso's cold-start Stage-1 atomic network (~5 vocal production leads) over a broad launch. The instinct to go wide (HN front page, Product Hunt day-1) before the adjacent user thesis is validated is the home run mentality Kaba warns against. Verso should go deep with one specific sub-segment (e.g., AI engineers at YC startups building production agents) before expanding to adjacent segments (ML researchers, platform teams, solo developers).
- **Verdict:** Confirms: Verso's Stage-1 is finding 5 structurally-aware AI engineers who hit the reliability wall and want a harness. Do not expand until that segment's activation is cracked.

### [SHARPENS §12 positioning — TikTok adjacent-user counter-positioning]
**Finding:** TikTok's counter-strategy — explicitly targeting Instagram's non-successful users — is an available positioning move for Verso. The engineers who tried LangChain and hit the graph constraint, or tried CrewAI and couldn't debug it, are LangChain's "non-successful users." They have intent, they tried, they churned. They are Verso's most natural adjacent entry point.
- **Verdict:** Sharpens §12 positioning: the struggling-moment persona (engineers who hit the LangChain wall) is not just a market insight — it is the adjacent user. Verso's positioning should explicitly name the failure mode they escaped, the way TikTok named what Instagram denied them.

---

## Honesty Note
The YouTube video (~1h42m) cannot be watched. The Lenny's Newsletter transcript is paywalled. The Andrew Chen blog post ("The Adjacent User Theory") is the canonical long-form write-up of the same framework Kaba presents in the podcast — Andrew Chen was Kaba's colleague at Instagram and documents the same Instagram examples with consistent detail. This note treats the Andrew Chen post as a reliable proxy for the podcast content. Four secondary sources (Recall, PodPulse, Bash summary, iVoox) are consistent with the Andrew Chen framework. No fabrication.
