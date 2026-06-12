# The SaaS Org Chart

**Source:** David Sacks (Craft Ventures)  
**URL:** https://sacks.substack.com/p/the-saas-org-chart  
**Format:** Essay, ~15 min read  
**Section:** B2B Go-To-Market (founder-led sales)

---

## Faithful Digest

### Core Premise

Sacks provides template org charts for SaaS startups at Series A, B, and C stages. The surface goal is "what should your org look like after each funding round." The deeper argument is about *sequencing* — hire in the wrong order and you destroy repeatability before you understand what you're even repeating.

The key underlying principle: **you cannot systematize what you have not yet understood personally.** The founder must close the first customers before hiring anyone in a go-to-market function. Premature VP of Sales is one of the most common and most destructive early startup mistakes.

### Stage-by-Stage Structure

**Series A (~50 employees, ~$2-5M ARR)**

CEO direct reports:
- CTO (12 engineers)
- VP Sales (12, including SDRs and AEs)
- Director of Product (5)
- Director of Customer Success / CSM (9)
- Director of Marketing (6)
- Director of Finance (6)

Engineering splits: front-end, back-end, client applications, core services, analytics, DevOps.

Key Sacks ratios at Series A:
- 1 SDR per 2 AEs
- 1 PM per 5-8 developers
- 1 manager per 5-10 reports
- ARR per employee: $20,000-$25,000

The critical Series A signal: VP of Sales should already be in place *and* should already have a repeatable playbook from the founder's early sales. If the founder hasn't closed customers personally, the VP of Sales will be flying blind and will almost certainly fail.

**Series B (~125 employees, ~$5-15M ARR)**

Growth expands to VP-level leaders across functions. Engineering grows to ~40 under the CTO. Sales and Customer Success combine under a CRO (~45 people). Marketing becomes a CMO role (~15 people). Product management becomes a more formal function with a Director or VP of Product.

ARR per employee target: $40,000-$50,000 — which means Series B companies must be growing faster than their headcount.

**Series C (~400 employees, ~$20-50M ARR)**

Mature structure:
- CPO (~23)
- CRO (~185, including US and European regions, enterprise/mid-market/SMB segments)
- CMO (~33)
- CFO (~39)

ARR per employee: $50,000-$66,666.  
IPO benchmark: $100,000 ARR per employee.

The Series C org is characterized by *specialization* — you now have different sales motions for different segments, separate regional teams, and a full product organization with dedicated PMs.

### Expense Ratios

Sacks's target expense allocation:
- **10% G&A** (general and administrative)
- **40% R&D** (engineering, product)
- **50% S&M** (sales and marketing)

This ratio is important because it implies the channel assumption: SaaS companies at scale spend *more* on go-to-market than on building the product. For an OSS-led company like Verso might be, this ratio will look different (R&D heavier, S&M lighter because community and inbound replace outbound sales motion).

### The Repeatable Close Prerequisite

The most practically important section for early-stage companies:

Sacks is explicit that hiring a VP of Sales before you have closed customers yourself is a failure mode. His reasoning:
1. You cannot evaluate whether the VP is doing a good job if you don't know what "good" looks like
2. The VP cannot build a playbook if there is no pattern to replicate
3. Early sales cycles are information-gathering exercises — founders do this better than salespeople because they can respond to feedback by changing the product in real time

The sequence: founder closes first 5-10 customers → identifies the repeatable pattern → then hires a VP of Sales to scale that pattern. Not before.

### Key Verbatim Fragments (from WebFetch extraction)

- 10% G&A : 40% R&D : 50% S&M allocation
- 1 SDR per 2 AEs
- 1 PM per 5-8 developers
- ARR per employee benchmarks by stage ($20k-25k → $40k-50k → $50k-66k → $100k at IPO)

---

## VERSO RELEVANCE

### Finding 1: The Expense Ratio as a Signal of GTM Model Type
**Tag: [NEW-IDEA] §12 (GTM/positioning)**  
Sacks's 10/40/50 ratio (G&A/R&D/S&M) is the *sales-led SaaS* canonical allocation. Verso's planned GTM is fundamentally different: DX-led organic, no sales motion, community-first, OSS-driven inbound. This means Verso's ratio should look more like 10/70/20 or even 10/80/10 in early stages — engineering-heavy, marketing-light because the product *is* the distribution. This is not a flaw; it's a deliberate choice. But founders should explicitly recognize they are *not* building a Sacks-style SaaS org. The framing clarifies what Verso is countering: the 50% S&M allocation assumption is what forces SaaS companies into outbound-heavy, AE-driven sales motions. Verso's OSS + DX-led model is a structural rejection of that allocation.  
**Verdict: new-idea** — surface this contrast explicitly in §12 when explaining why no sales motion.

### Finding 2: Founder-Closes-First is a Hard Prerequisite
**Tag: [CONFIRMS] founder_os**  
Sacks's emphasis on founder-led sales before any GTM hire confirms the founder-OS layer. For Verso: the first 10 design partners should be closed by the founder personally, with direct engagement in their repos, pair programming sessions, GitHub issue threads. The founder must understand *why* these people adopt before any attempt to systematize the GTM. This is already in the PRD but Sacks provides the clearest articulation of *why* — you can't evaluate GTM hires if you don't know what you're optimizing for.  
**Verdict: confirm** — already embedded in founder-OS layer.

### Finding 3: ARR-per-Employee as a Velocity Signal
**Tag: [SHARPENS] founder_os**  
The ARR-per-employee benchmarks ($20k-25k at A, $40k-50k at B, $100k at IPO) are useful as guardrails for Verso's growth model. For a lean, founder-operated, OSS-first company, Verso should be able to sustain much higher ARR-per-employee ratios than traditional SaaS — particularly if the GTM is inbound-only and the product is self-serve. A $100k ARR-per-employee target at Series A (vs. Sacks's $20-25k) would be a signal of capital efficiency that appeals to the a16z/YC "build a generation-defining company" game. This is a framing Verso could lean into in fundraising narratives.  
**Verdict: sharpen** — relevant to the founder-OS fundraising narrative.

### Finding 4: 1 PM per 5-8 Developers is a Taste Constraint
**Tag: [NEW-IDEA] product_taste**  
Sacks's ratio of 1 PM per 5-8 developers is instructive as a *taste constraint*. Verso should resist the temptation to hire product managers early. In the harness-as-the-product model, the founder IS the PM — the design choices (what to expose, what to hide, what the one-flag durable diff looks like) should not be delegated to a non-technical PM who lacks the structural awareness to make the right calls. This maps to the "invariants-as-taste" principle: the people making product decisions must understand the constraint space deeply. No PM at seed/A means the founder's taste dominates — which is the right call for Verso.  
**Verdict: new-idea** — add to the founder-OS operating principles as "no PM before product taste is locked."

### Finding 5: CRO at Series B — the Sales/CS Integration Signal
**Tag: [SHARPENS] §12 (GTM)**  
Sacks's recommendation to combine Sales and Customer Success under a CRO at Series B is a useful signal for Verso's eventual org design. For a developer tool with high switching costs at the seam, Customer Success is actually the primary retention driver — it's not a separate function from "sales" but is the mechanism by which expanded usage (more agents, more teams, checkpoint/resume upgrade) gets unlocked. Verso's equivalent of the CRO role at scale would be someone who thinks about the full customer journey from "first agent to checkpoint" rather than just closing the initial deal.  
**Verdict: lock-defer** — relevant at Series B+, not actionable at seed.

---

## Summary Verdict

The Sacks piece is most useful to Verso as a *contrast surface* — it describes the canonical sales-led SaaS org, which Verso is explicitly not building. The 10/40/50 expense ratio contrast, the founder-closes-first prerequisite, and the no-early-PM principle are the three actionable findings. The ARR-per-employee benchmarks are useful for the fundraising narrative. Everything else (Series B/C structures, CRO role) is lock-defer.
