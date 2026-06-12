# Enterprise Sales

**Source:** Y Combinator Startup School  
**URL:** https://www.youtube.com/watch?v=0fKYVl12VTA  
**Speaker:** Pete Koomen, General Partner at YC; co-founder of Optimizely (YC W10), grew to $100M ARR  
**Format:** YouTube video / Startup School lecture, 23 minutes  
**Published:** July 2024  
**Transcript status:** read_partial — no verbatim transcript found. Content reconstructed from: YC Library summary page, OpenTools YouTube summary, LinkedIn post with notes, Y Combinator podcast episode description, and search result excerpts. Content reflects the documented frameworks from the talk, not a word-for-word transcript.

---

## What Koomen Actually Argues

### Core Thesis: Technical Founders Are the Best Salespeople (Pre-PMF)
Koomen opens with the counterintuitive claim: before product-market fit, a technical founder is the most effective salesperson for their own product—*more* effective than a hired sales professional. The reasons:
1. Deep product knowledge enables real-time adaptation during demos
2. Genuine conviction is perceptible and can't be faked by a sales hire
3. Customer feedback from sales conversations directly informs product decisions
4. Only the founder can distinguish a real problem signal from a polite non-commitment

**Implication:** Hiring a salesperson to close your first enterprise customers before the founder has done it personally is a mistake. The first sales conversations are learning events, not revenue events.

### The Sales Hypothesis
Before any outreach, construct an explicit sales hypothesis:

> "Customer X has problem Y, and our product solves it."

This hypothesis drives all prospecting decisions. Without it, founders end up talking to "easy-to-reach" prospects who don't actually match the profile—wasting months on conversations that will never close.

A sales hypothesis should name:
- The specific company type (not "large enterprises" but "mid-market SaaS companies with >50 engineers and no dedicated ML team")
- The specific problem (not "inefficiency" but "they manually review every agent output before deploying")
- The mechanism of resolution (how your product specifically addresses that problem)

### The 7-Step Enterprise Sales Funnel

**Step 1: Prospecting**
- Identify companies that match your hypothesis
- Find specific decision-makers at those companies (Apollo.io, LinkedIn Sales Navigator)
- Prioritize: (a) companies you can verify are experiencing the exact problem, (b) companies where you have a warm path

**Step 2: Outreach**
- Priority order: inbound demand (content, blog, technical resources) > warm intro > cold email
- Cold email rule: "Write personalized cold emails you'd be excited to receive." This means mentioning a specific recent event, signal, or article about that company—not a templated blast.
- Conferences: attend the events where your specific buyers gather

**Step 3: Qualification**
- Ask discovery questions; do not pitch
- Three qualification criteria: (1) Do they have the problem? (2) Do they have budget? (3) Do they have decision-making authority?
- "Great salespeople spend most of their time listening."
- Anti-pattern: pitching to everyone who takes a meeting, regardless of fit. A qualified "no" is more valuable than an unqualified conversation.

**Step 4: Demo**
- Structure as storytelling: clear arc from problem → struggle → resolution
- Personalize every demo: use the company's actual name, their logo, their specific use case
- Show "magic moments": the single interaction that demonstrates ease, speed, or delight disproportionate to expectation
- Connect every feature shown directly to a specific pain the prospect named in the discovery call

**Step 5: Pricing**
- Before quoting, ask: "What does this problem cost you today?" and "What do you currently pay for [competing solution]?"
- Price higher than feels comfortable—as a test of genuine need, not as overconfidence
- "Higher prices indicate genuine customer need." If they won't pay for it, they don't need it badly enough.
- Use each pricing conversation as a data point; the goal at this stage is price discovery, not revenue optimization

**Step 6: Closing**
- Understand the procurement process *before* you present pricing: "How does your company typically evaluate and purchase new software?"
- Prepare in advance for: security reviews, legal redlines, compliance signoffs, IT approvals
- Recommendation: Common Paper legal templates to minimize back-and-forth
- Identify your "champion" within the organization—the internal person who wants you to win and will navigate internal obstacles for you
- "Maintain close communication with your champion." They know where deals go to die inside the org.

**Step 7: Implementation**
- Implementation is your responsibility, not the customer's. A signed contract is not a win—a habitual product user is a win.
- Before signing, create a detailed implementation plan: who owns what, when, success metrics
- Project-manage adoption like an internal engineering sprint
- A customer who doesn't adopt is not a customer—they're a churn in waiting

### Critical Anti-Patterns

1. **Talking to the wrong customers** — targeting accessible/friendly prospects who can't buy or won't benefit. Result: months of warmth, zero signal.
2. **Bottom-up approach for top-down products** — hospital software needs CFO/CIO buy-in. Individual doctor enthusiasm doesn't close. Know whether your product is top-down or bottom-up in each org.
3. **Underpricing from fear** — founders systematically underprice because they fear rejection. Low prices attract the wrong buyers and destroy perceived value.
4. **Skipping implementation ownership** — "signing a contract is not the same as a customer." Post-close, the founder who disappears loses the reference.

### Koomen's Optimizely Origin Point
Koomen and co-founder Dan Siroker "used trial and error to figure out how to sell" at Optimizely. The video explicitly draws on this trial-and-error process—meaning the advice is empirically grounded in a company that went from YC batch (2010) to $100M ARR through enterprise sales, not PLG.

---

## VERSO RELEVANCE

### [SHARPENS] §12 / gtm_distribution — The Sales Hypothesis as VERSO's Cold-Start Instrument
**Finding:** Koomen's sales hypothesis ("Customer X has problem Y, and our product solves it") is the precise instrument VERSO needs for Stage-1 atomic network construction. VERSO's hypothesis should be extremely specific: "Senior AI engineers at Series B–D companies that already have 1-2 agents running in production, who are hitting reliability failures they can't instrument or recover from without a rewrite, and whose current harness is a bespoke asyncio loop." This specificity determines which cold outreach messages to write and which inbound signals to prioritize. The hypothesis is testable and updates on evidence.  
**Verdict:** Sharpens the cold-start selection logic. "5 vocal production leads" without this hypothesis is a guess; with it, it's a repeatable prospecting process.

### [NEW-IDEA] §12 / gtm_distribution — "Magic Moment" Demo as the Harness Seam Demo
**Finding:** Koomen's "show the magic moment" principle names what VERSO's demo-able wedge must do in a sales context. The existing wedge (3-line side-by-side, one-flag durable diff, inspect()) is structurally correct. What Koomen adds: the magic moment must be *personalized* — shown with the prospect's actual agent topology, their actual failure mode, their actual production load. A generic demo of the seam mechanism is interesting; a demo that shows their specific prod agent gaining checkpoint/resume with 3 lines is a magic moment.  
**Verdict:** New demo instruction: personalize the seam demo to the prospect's own architecture before the meeting.

### [CONFIRMS] §12 / gtm_distribution — Founder Must Do First Sales
**Finding:** Koomen's core claim (technical founder is the best pre-PMF salesperson) directly confirms VERSO's DX-led organic + founder-led cold-start model. No sales hire in Stage 1. The founder's depth on the harness architecture is the reason for product conviction that closes first deals — exactly the "structurally-aware" language VERSO already targets. This is not a constraint; it's an advantage.  
**Verdict:** Confirms no sales motion in Stage 1; founder's technical depth is the conversion mechanism.

### [SHARPENS] §12 / gtm_distribution — Champion Identification at Stage 1
**Finding:** Koomen's "champion" concept (the internal person who wants you to win) maps onto VERSO's persona. The structurally-aware senior AI engineer IS the champion within their org. They can navigate internal procurement, security review, and architecture-committee approval. VERSO's onboarding experience, documentation quality, and respond-to-issues speed should be calibrated to delight the champion, because the champion is the internal distribution mechanism.  
**Verdict:** Sharpens the superconsumer persona: the structurally-aware senior is both buyer and champion; DX is champion-management.

### [NEW-IDEA] §7 / product_taste — Implementation Plan as Harness Onboarding Contract
**Finding:** Koomen's "create a detailed implementation plan before signing" names a VERSO product gap: there should be a canonical onboarding track (not documentation, but a structured plan) for a team integrating VERSO into an existing agent. The plan should specify: which agent gets the seam first, what the success metric is at day 7/30, who owns what in the integration, and what "habitual use" means. This is harness onboarding as a product artifact, not a customer success activity.  
**Verdict:** New product requirement: a structured implementation track that transforms the signed/installed moment into a habitual-use moment. Reduces churn on early adopters.

---

## One-Line Verdict
Koomen's 7-step funnel is the most directly applicable B2B sales framework for VERSO's Stage-1 cold-start: the sales hypothesis sharpens atomic-network selection, the champion concept names how the structurally-aware senior creates internal distribution, and the implementation-plan principle surfaces a missing harness onboarding artifact.
