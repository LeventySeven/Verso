# Growth+Sales: The New Era of Enterprise Go-to-Market

**Source:** Peter Lauten & Martin Casado (a16z), July 29, 2020  
**URL:** https://a16z.com/growthsales-the-new-era-of-enterprise-go-to-market/  
**Status:** read_full

---

## Core Argument

Growth+sales is the combination of bottom-up product-led adoption (consumer-style growth) layered with top-down enterprise sales. The authors argue this is now the *dominant* GTM model for enterprise software and that incumbents cannot adapt to it without destroying their existing business. The model creates a structural window for new company formation analogous to what SaaS did in the 2000s.

The key structural claim: "When the initial route to market is focused on how much a product sells itself, the winners are the product visionaries, not veteran sales leaders pushing outdated software." And: "Adapting to the growth+sales era is near impossible for the top-down sales incumbents."

---

## Historical Context and Examples

Companies that successfully executed growth+sales: GitHub, Zoom, Qualtrics, Slack, Atlassian, PagerDuty, Yubico, Stripe, Plaid.

The pattern is consistent: organic user-driven adoption matures first, then enterprise sales layers on top. GitHub crossed 10M repositories (December 2013) before seriously pursuing enterprise sales.

---

## Old World vs. New Buyer Behavior

**Traditional enterprise sales:**
- Long relationship-driven cycles requiring AEs, SEs, RFPs
- Maximally complex products designed to check procurement boxes
- Vendor discovery through analyst reports, centralized IT
- Users not the buyers; buyers not the users

**Growth+sales:**
- "All the complexity of the traditional sales cycle collapses into a single decision maker: the end user"
- Discovery through word-of-mouth and peer recommendation
- Best products win on design, UX, speed, actual functionality
- Consumer growth tactics become essential: viral loops, community building, trusted brand

---

## Six Failure Modes (Full)

**Failure Mode 1: Forcing Growth When It Doesn't Fit**
Not all products allow bottom-up adoption. Products requiring secure IT authorization, or systems of record requiring full department migration, face "insurmountable technical constraints." The test: can an individual user get meaningful value independently, without IT approval? Zoom: "it just works" — freemium model that "starts simple but earns the right to be complex." Products that fail this test should not force the growth motion.

**Failure Mode 2: Acquiring Users Without Generating Organic Love**
"Paid acquisition channels that yield low-retaining users is the addictive drug that will ultimately kill a distribution model." Paid acquisition that doesn't convert into genuine product love ruins both unit economics and subsequent enterprise sales (customers who don't love it won't expand). Twilio's counter-example: "acquire developers like consumers, enable them to spend like enterprises" — won mindshare through superior technology, not paid acquisition.

**Failure Mode 3: Using Traditional Metrics to Measure New Motions**
Traditional metrics (ARR, ASP, seats, unique logos) are backward-looking and obscure growth motion performance. Correct metrics: MAUs, WAUs, DAUs, engagement (session length, days active/week), active user retention, funnel conversion throughout the user journey. "DAUs often tell us way more about which products are victorious than any backward-looking revenue metrics." Slack's intracompany network effect (how deeply used within a company) predicts full deployment and revenue better than seat counts alone.

**Failure Mode 4: Layering Sales Too Early**
Premature sales creates two disconnected pitches — product experience to users, ROI argument to executives — without synergy. You capture the complexity of both motions without the benefits of either. Early signals the market is ready for top-down sales: users start asking "How can I get this in the hands of my entire department?" and "Why isn't everybody using this?!" GitHub organic maturity (10M repositories) before enterprise push is the canonical example.

**Failure Mode 5: Growth That Doesn't Enable Enterprise Sales**
Some organic presence doesn't create a path to enterprise revenue. Open source with no connection to enterprise buyers. Freemium where users are permanently satisfied with the free tier and never need premium. The test: does organic adoption create a natural pull toward someone with a budget?

**Failure Mode 6: Neglecting Growth After Sales Takes Off**
"Growth+sales is not about doing growth first, and then growing up to sales without ever looking back. It's about delivering on your promises to the user, then making new promises to the enterprise buyer without forgetting about the user." Risks: slowing feature velocity, UX falling behind, brand erosion — becoming the next incumbent for a younger competitor to disrupt. Atlassian's counter-example: following growth+sales wins on Jira/Confluence, expanded through acquisitions (Trello, HipChat, OpsGenie, AgileCraft) and organic product expansion, maintaining the growth+sales motion.

---

## Strategic Advantage for Startups

The incumbents' dilemma is structural: adapting to growth+sales requires dismantling the very sales machine that generates their current revenue. A traditional enterprise software vendor cannot credibly go developer-first without cannibalizing its enterprise AE org and devaluing its complex product positioning. This is the counter-positioning power (in Helmer's vocabulary) of the growth+sales motion.

---

## VERSO RELEVANCE

### §1 — Bet / Moat / Counter-Positioning

**[CONFIRMS]** The incumbents-cannot-copy argument is the exact mechanism Verso's counter-positioning relies on. LangChain cannot go "harness-first, no abstraction" without destroying its framework product and the LangSmith monetization layer built on top of it. The a16z formulation — "adapting to the growth+sales era is near impossible for the top-down sales incumbents" — applies to framework vendors who monetize complexity: they cannot credibly simplify without self-destruction. **Verdict: CONFIRMS the counter-positioning power. Use the a16z framing explicitly in investor materials.**

**[SHARPENS]** Failure Mode 1 is a precision test for Verso's product thesis: does the product allow individual adoption without IT approval? Answer: yes — a Python package installed via `pip`, runnable in any existing project. The harness IS individually adoptable by a senior engineer without procurement. This is a genuine growth-motion fit. **Verdict: sharpen §1 — explicitly state Verso passes the individual-adoptability test, which is not a given for all agent frameworks.**

### §12 — GTM / Positioning

**[SHARPENS]** Failure Mode 4 (layering sales too early) is directly actionable: Verso should have explicit criteria for when top-down sales is triggered. The a16z signal is: users start asking "why isn't my whole team using this?" That is the moment to layer on enterprise motion, not before. Pre-signal, the entire GTM should be bottom-up: DX-led, Show HN, X build-in-public, free tier, self-serve. **Verdict: sharpen §12 — add explicit trigger criteria for transitioning from pure PLG to growth+sales.**

**[NEW-IDEA]** Failure Mode 3's metric prescription is directly applicable: Verso should track DAU/WAU/MAU and engagement (sessions, days active) as primary health metrics, NOT ARR or logo count in the early phase. If the growth motion is working, these consumer-style metrics will show it before revenue does. This is a measurement architecture decision. **Verdict: adopt-now — define the metric stack for the PLG phase before any revenue is tracked.**

**[CONFIRMS]** The "acquire developers like consumers, enable them to spend like enterprises" (Twilio) formulation is almost verbatim Verso's strategic aspiration. The structurally-aware senior engineer is both the individual adopter (consumer behavior) and the internal champion who pulls budget (enterprise behavior). The a16z framing validates this dual persona. **Verdict: CONFIRMS the primary persona and distribution thesis.**

**[NEW-IDEA]** Failure Mode 6 (neglecting growth after sales takes off) is a future-state warning for Verso: once enterprise deals begin, the temptation is to stop investing in DX/docs/community and focus on AE support. This kills the moat. The eval-corpus flywheel and the harness's invariant quality only compound if the community keeps growing. Atlassian's multi-product expansion is the right model: keep the growth motion alive in parallel with the sales motion. **Verdict: lock-defer — relevant at Series A, not pre-revenue, but should be in the strategic roadmap.**

### §7 / §12 — Demo-able Wedge / Product Taste

**[SHARPENS]** Failure Mode 2 (low-retaining paid users from paid acquisition) reinforces why Verso's launch strategy must be superconsumer-first / community-first, not paid. The first 50 users must genuinely love the framework. If the Show HN doesn't generate organic enthusiasm, that is a product signal, not a distribution problem. **Verdict: sharpen — do not supplement early organic with paid until organic love is confirmed.**

### Founder-OS Layer

**[NEW-IDEA]** The explicit framing "product visionaries win, not veteran sales leaders pushing outdated software" is a positioning statement for Verso's founder persona as well. The founder should be the visible product visionary, not a sales-first operator. Build-in-public as the authentic expression of product vision, not marketing. **Verdict: confirm and encode in founder-OS content.**

---

## Verdict Summary

| Finding | Tag | PRD Section | Verdict |
|---|---|---|---|
| Incumbents cannot copy growth+sales without self-destruction (LangChain specific) | CONFIRMS | §1 Moat | Use a16z framing in investor materials |
| Verso passes individual-adoptability test (pip install, no IT) | SHARPENS | §1 Moat | Explicitly state in positioning |
| Explicit trigger criteria needed for PLG→growth+sales transition | SHARPENS | §12 GTM | Add "why isn't my whole team using this?" trigger |
| DAU/WAU/MAU as primary health metrics (not ARR) in PLG phase | NEW-IDEA | §12 GTM | Define metric stack before revenue tracking |
| Neglecting growth after sales = becoming next incumbent | NEW-IDEA | §12 GTM | Add to strategic roadmap for Series A |
