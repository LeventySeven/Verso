# Growth Loops Are the New Funnels

**Source:** https://www.reforge.com/blog/growth-loops  
**Authors:** Brian Balfour, Casey Winters, Kevin Kwok, Andrew Chen (Reforge)  
**Format:** Essay (series post 3 of 4 on growth strategy)  
**Access:** Reforge blog 403 — reconstructed from multiple high-fidelity secondary sources including Teknicks, Aakash Gupta's Ultimate Guide, CleverTap, and Balfour's own Universal Growth Loop essay. All quoted material cross-verified across sources.

---

## Faithful Digest of the Source Argument

### The Central Claim: Funnels Are the Wrong Mental Model

The essay opens with a direct attack on the AARRR (Pirate Metrics) funnel, which has dominated growth conversations since Dave McClure's framework. The core claim: **funnels are a useful diagnostic tool but a terrible model for how growth actually compounds.** The authors argue funnels create structural failure modes:

1. **Silo Syndrome** — Funnel stages map to department handoffs. Marketing owns acquisition, product owns activation, finance owns revenue. Because each team optimizes its own stage metric, no one owns the systemic health of how growth compounds.
2. **Linear Thinking** — Funnels assume customer journeys are sequential, which misrepresents non-linear behavior.
3. **No Reinvestment Logic** — Funnels have no answer to "How does one cohort of users lead to the next?" Blue Apron spent ~$400 per customer for <$200 annual value — a funnel looks "healthy" at each stage but the loop never closed.
4. **Scalability Ceiling** — As audiences grow, acquisition costs rise exponentially (no compounding; pure burn). The funnel model has no mechanism to compound because there is no loop.

> "Funnels have no concept of how to reinvest what comes out at the bottom to get more at the top to continue to feed growth over time — in other words, no compounding effect."

### The Growth Loop Definition

A growth loop is a **closed system** where:
- **Input** — A new or returning user converted based on reinvestment of a previous output.
- **Action/Step** — The user engages in a series of actions that produce an output.
- **Output** — The result of those actions creates something that can be reinvested as a new input.

The loop is then described by three diagnostic questions for each step:
- **What**: What specific action occurs at this step?
- **Who**: Which user segment (free user, paying user, creator, buyer, seller) executes it?
- **Why**: What fundamental need or incentive drives participation?

This structure forces a question funnels never ask: *"How does one cohort of users lead to another cohort of users?"*

### Four Types of Acquisition Loops

The authors break acquisition loops into four canonical types:

**1. Viral Loops**
A user signs up, interacts with the product, then shares the product or a piece of content with a contact, or invites a contact to join — which creates a new input.
- Structure: New user → engages with product → shares/invites → new user.
- Example: Dropbox's referral program (give 500MB for each referral); WhatsApp's "message this contact" invite.

**2. Content Loops**
Four sub-types based on who creates content and how it is distributed:
- UG-CD-SEO: User-Generated, Company-Distributed (search engine optimization)
- UG-UD-Social: User-Generated, User-Distributed (social channels)
- CG-CD-SEO: Company-Generated, Company-Distributed (SEO blog)
- CG-UD-Social: Company-Generated, User-Distributed (sharing articles)

Pinterest example: Users create pins → Pinterest packages pins for SEO → Search traffic discovers Pinterest → New users join → Create more pins. The loop incentive is "gaining personal or social capital" through sharing.

**3. Paid Loops**
Revenue from ad conversions funds additional advertising, creating circular reinvestment. Only works if LTV > CAC with enough margin to fund the next round. If unit economics break, the loop collapses — funnels don't surface this until the company is out of cash.

**4. Sales Loops** (sometimes "Product Loops" in other framings)
High-value contracts generate revenue reinvested in sales capacity for scaling. HubSpot's B2B loop: inbound marketing content → leads → sales closes → revenue → funds more content. HubSpot ran six integrated loops simultaneously (inbound marketing, SEO, sales, integrations, content sharing, email marketing), generating 14x return since 2014 IPO.

### Why Loops Are Harder to Copy Than Funnels

The essay makes a defensibility claim: **loops are structurally harder for competitors to replicate than funnel stages.** A funnel stage (e.g., "we run Google ads") can be copied in a day. A loop — especially one dependent on user-generated content, network effects, or platform-specific behavior — takes years to build because the loop's output (corpus of content, network density, review depth) is the moat, not the step itself.

WordPress's CG-UD loop: Footer branding "Powered by WordPress" on every site → users discover WordPress → sign up → create new sites → each carries footer → new discovery. This accounts for >30% of all websites.

### The Universal Growth Loop (Balfour Extension)

From Balfour's related essay, growth loops extend beyond product: growth → attracts better capital and talent → enables solving harder problems → fuels more growth. The failure mode is "loop reversal": misallocated resources → flat growth → difficulty attracting talent → inability to solve new problems → stagnation.

Recovery requires contraction before expansion — "cut initiatives and/or people in order to focus the fire power in a concentrated area." This is counter-intuitive but necessary for loop reset.

---

## VERSO RELEVANCE

### [SHARPENS] §12 GTM: Verso's DX organic channel should be designed as a loop, not a funnel — adopt-now

The prior pass established Verso's GTM as "DX-led organic" — X build-in-public + Show HN. This source sharpens the architecture: the right mental model is a **content/viral loop**, not a conversion funnel. Concretely:

- **Input**: Developer discovers Verso via X thread or Show HN post.
- **Action**: Developer uses Verso in a side project or work agent → encounters the harness → publishes their own take ("I used Verso's one-flag durable promotion, here's what happened").
- **Output**: New developer content referencing Verso (GitHub stars, blog posts, X threads, HN comments).
- **Reinvestment**: That output becomes discoverable content driving the next cohort of inputs.

This is a UG-UD-Social loop with a secondary CG-CD-SEO loop from Verso's own build-in-public content. The funnel framing ("conversion rate from Show HN") misses whether the loop is closing.

Tag: [SHARPENS] §12 — verdict: **adopt-now**. Reframe Verso's GTM section from funnel language to loop architecture. The key design question becomes: what does a user produce after using Verso that naturally recruits the next user?

### [SHARPENS] §1 Moat: The loop OUTPUT is the moat, not the primitive

The essay's defensibility claim maps precisely onto Verso's eval-corpus flywheel (already established). The loop framing adds precision: **the output of Verso's product loop is the eval corpus + the harness lift data**. Each team that uses Verso and generates eval results is creating output that:
1. Proves harness value (economic effect)
2. Gets shared as case studies/blog posts (viral/content effect)
3. Attracts the next "structurally-aware engineer" who wants the same results.

This makes the eval corpus not just an "Aggregation-Theory flywheel" (prior pass framing) but specifically the reinvested output in a product-led content loop. Sharpens rather than contradicts.

Tag: [SHARPENS] §1 — verdict: **adopt-now**. Name the loop explicitly in the positioning: "Each team that instruments a harness generates data that proves the case for the next team."

### [NEW-IDEA] The "why does the loop activate" diagnostic reveals the missing design constraint

The Reforge framework insists you must specify **WHY** a user takes each step. Applied to Verso's developer loop: why does a user who benefited from Verso then produce shareable content? The answer must be engineered, not assumed. Current prior-pass GTM assumes organic build-in-public but doesn't identify the incentive mechanism. The loop collapses if the user has no personal/professional reason to share.

Options to engineer the "why":
- **Social capital**: Sharing a concrete before/after (the 3-line side-by-side diff) is inherently shareable because it makes the sharer look structurally sophisticated.
- **Reciprocity**: Verso's OSS + build-in-public posture invites reciprocal transparency from users.
- **Status signal**: Being an early adopter of an "anti-framework" in the AI infra space is a status marker among senior engineers.

Tag: [NEW-IDEA] §12 / §7 — verdict: **adopt-now**. The 3-line side-by-side demo is already identified as the wedge; this makes explicit that it's the shareable artifact that closes the loop. Design the demo around shareability: it should be Twitter/X-native (tweetable code diff, not a PDF).

### [SHARPENS] §2 Non-goals: Paid loop is explicitly not Verso's loop

The paid loop requires LTV > CAC with margin. Verso's persona (senior/AI engineers) is not a consumer purchase — paid acquisition doesn't fit. The framework confirms that Verso's correct loop type is viral/content (UG-UD-Social), not paid. Reinforces non-goal: no ad spend, no sales motion.

Tag: [CONFIRMS] §2 — verdict: **confirm, no action needed**.

### [SHARPENS] §12 The loop reversal risk is the founder-OS warning

Balfour's extension: when growth stalls, the temptation is to add more features/initiatives rather than concentrate. For Verso: if the DX loop stalls (Show HN lands but loop doesn't close — no user-generated content appears), the failure mode is feature scatter, not the right response. The right response is to identify which loop step broke and fix exactly that.

Tag: [SHARPENS] founder_os — verdict: **lock-defer** (useful if/when Verso faces plateau; not pre-launch priority).

---

## Verdict Summary

| Finding | Tag | Section | Verdict |
|---------|-----|---------|---------|
| Design Verso's GTM as a loop, not a funnel | SHARPENS | §12 | adopt-now |
| Eval corpus is the reinvested output of the product loop | SHARPENS | §1 | adopt-now |
| Must engineer WHY the user shares; 3-line diff is the shareable artifact | NEW-IDEA | §12/§7 | adopt-now |
| Paid loop confirmed non-goal | CONFIRMS | §2 | confirm |
| Loop reversal risk = concentration signal at plateau | SHARPENS | founder_os | lock-defer |
