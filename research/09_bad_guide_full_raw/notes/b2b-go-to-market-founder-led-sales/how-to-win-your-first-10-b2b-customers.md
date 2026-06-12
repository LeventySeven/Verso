# How to Win Your First 10 B2B Customers

**Source:** Lenny Rachitsky, Lenny's Newsletter  
**URL:** https://www.lennysnewsletter.com/p/how-to-win-your-first-10-b2b-customers  
**Format:** Essay, ~20 min read  
**Section:** B2B Go-To-Market (founder-led sales)

---

## Faithful Digest

### Core Premise

The essay is drawn from interviews with 20+ founders across companies including Vanta, Figma, Retool, Notion, Brex, and others. Its central claim: the path to your first 10 B2B customers is not random — it follows a predictable trust-distance gradient. The further you are from your personal network, the harder acquisition becomes because trust is the scarce resource, not product quality.

The underlying model: **"concentric circles with increasing distance from the founder."** Each ring outward requires more effort to establish credibility because the prospect has less pre-existing reason to believe you won't jeopardize their operations.

### The Seven-Step Sequence (ordered high to low trust / high to low efficiency)

**1. Leverage your personal network**
Start with people who match your ICP and already know you. Not exclusively friends — friends who are bad fits are noise — but former colleagues, ex-managers, ex-reports, people who have seen you operate. Vanta's earliest customers came entirely through the founders' professional networks before any outbound existed. The key insight: these people tolerate more rough edges and give more honest feedback *because* the relationship pre-exists.

**2. Strategic cold outbound**
When personal network is exhausted, targeted cold outreach. The Retool example is load-bearing here: David Hsu used Crunchbase to filter for companies that recently raised Series A/B (had budget, needed tooling fast, less bureaucracy) and sent personalized cold emails. The personalization wasn't flattery — it was specific to the prospect's situation. Twitter/X was also cited as a surface: finding users publicly complaining about the problem Retool solved.

Key tactic: smaller companies are better early targets. They move faster, have less procurement overhead, and are more willing to work with pre-product-market-fit companies. Security-sensitive products (Vanta again) found that smaller targets were far more willing than enterprise to run pilots without full security reviews.

**3. Tap investor networks**
YC and First Round Capital were cited most often. YC's internal network (other portfolio companies) is a captive ICP for many B2B tools. First Round's "First Round Review" and community events create warm introduction surfaces. The dynamic: an investor intro carries institutional trust transfer — the prospect assumes the company has been vetted.

**4. Community participation**
Attend meetups, conferences, online forums where your ICP congregates. The goal is not to pitch — it's to establish presence and credibility before you need the relationship. Slack communities, Discords, Reddit threads. Showing up consistently as someone who adds value *before* asking for anything. This is a slow channel but compounds over time into "reputation as belonging."

**5. Build online content presence**
Create content (blog posts, Twitter threads, YouTube) that demonstrates domain expertise. Multiple founders who had pre-existing audiences (technical blogs, open-source projects) found that early customers came inbound to them before they had to do any outreach. The pattern: content creates pull that reduces cold-outreach friction later.

**6. Pursue press coverage**
Acknowledged as unreliable and often overrated by founders who succeeded. TechCrunch coverage can spike signups but rarely converts to paying customers. Lower priority than channels 1-5. Mentioned as occasionally useful for social proof in later conversations, not as a direct acquisition channel.

**7. Simply launch (Product Hunt / Hacker News)**
Show HN and Product Hunt launches create organic traffic spikes. Multiple founders found their first handful of customers came from launch posts. Hacker News is especially useful for developer tools because the audience is the ICP. The value isn't just the signups — it's the feedback density: you get many opinions fast from people who understand the problem space.

### Critical Qualifiers

- **No silver bullet:** Every founder described using a combination of channels. No single tactic produced all 10. The sequence above is a search order, not a funnel.
- **Don't sell exclusively to friends:** If a friend isn't your ICP, they are noise. Their tolerance for your product's failings will produce false-positive feedback. Honest strangers who are your ICP are more valuable than loyal friends who aren't.
- **The founder must do the selling:** The essay is specifically about *founder-led* sales. Hiring a VP of Sales before you personally have closed customers is a red flag (Sacks makes the same point separately). You must understand *why* customers buy before you can teach someone else to replicate it.
- **Solve the trust problem first:** For security-sensitive products (Vanta, compliance tooling), the first sales cycle is not about features — it's about proof that you'll handle their data responsibly. The product *was* the trust artifact.

### Key Verbatim Fragments (from WebFetch extraction)

- "concentric circles with increasing distance from the founder"
- The framework "essentially represents trust levels" — each ring is harder because you're known less
- On cold outbound: personalization to the prospect's *specific situation* (recent funding, specific pain) not generic flattery
- "No single silver bullet exists. Success typically combines multiple modest channels rather than one dramatic breakthrough."

---

## VERSO RELEVANCE

### Finding 1: Trust-Distance Gradient as the Cold-Start Model
**Tag: [SHARPENS] §12 (GTM/cold-start)**  
The trust-distance model gives Verso a *sequenced* cold-start playbook that matches its DX-led organic GTM intent. The "concentric circles" framing maps cleanly: personal network (AI engineer friends/colleagues) → targeted cold outbound (X/GitHub/HN users publicly frustrated with LangChain overhead) → investor/YC network (if/when Verso has a YC relationship) → community (r/LocalLLaMA, Latent Space Discord, Hugging Face forums). This is not new in principle but sharpens the *ordering* — Verso should exhaust circle 1 before circle 2, not run all channels simultaneously.  
**Verdict: adopt-now** — use this sequencing explicitly in the §12 cold-start section.

### Finding 2: Smaller/Faster-Moving Targets First (even for dev tools)
**Tag: [SHARPENS] §12 (GTM/ICP)**  
The essay's repeated finding that *smaller companies* are better early targets (less procurement, more tolerance for rough edges, faster feedback) is directionally correct for Verso. The primary persona (structurally-aware senior/AI engineer) is more likely to be at a 5-50 person startup or at a growth-stage company with a small AI platform team than at a 10,000-person enterprise. But the sharpening: even within the "senior AI engineer" persona, those at *smaller* companies are the better first customers — they have more autonomy to adopt and champion a new framework, and less bureaucracy to navigate.  
**Verdict: sharpen** — the ICP description should note the company-size dynamic, not just the role.

### Finding 3: Founder Must Close First — No VP of Sales Before Repeatable Close
**Tag: [CONFIRMS] founder_os**  
This confirms the YC canon (do things that don't scale, founder-led everything early). For Verso specifically: the founder should be doing the Show HN post, answering GitHub issues, being in the Discords, closing the first design partners personally. This is already implied in the DX-led organic GTM, but the essay is explicit that hiring sales before you understand *why* people buy is a failure mode.  
**Verdict: confirm** — already embedded in the founder-OS layer.

### Finding 4: Hacker News as Primary Launch Surface for Dev Tools
**Tag: [CONFIRMS] §12 (GTM/launch)**  
Show HN is validated as a primary acquisition channel for developer tools specifically because the audience IS the ICP. This confirms the X build-in-public + Show HN channel pair already in the PRD. Lenny's data point: multiple founders found their first customers from HN launch posts.  
**Verdict: confirm** — already in §12.

### Finding 5: Content Before You Need the Relationship
**Tag: [NEW-IDEA] §12 (GTM/distribution loops)**  
The "pre-build audience before you need it" pattern — founders who had technical blogs, open-source projects, or Twitter followings before launch found that early customers came *to them*. For Verso, this suggests that the build-in-public strategy on X is not just about generating buzz at launch — it's about *pulling* the first customers inbound before a formal launch happens. Concretely: writing threads about the harness-as-moat argument, the one-flag durable diff, the counter-positioning against LangChain, *before* launch creates pre-warmed audience. People who engage with those threads are pre-qualified.  
**Verdict: adopt-now** — the X build-in-public strategy should be framed as "audience before product is public" not just "launch announcement."

### Finding 6: Investor Network as Trust Transfer (YC-specific)
**Tag: [SHARPENS] founder_os (YC-a16z game)**  
If Verso goes through YC, the batch is a captive ICP. AI engineer founders in the same batch who are building agent-heavy products are ideal early design partners — they are structurally-aware, technically sophisticated, motivated to adopt tools that work, and connected to other companies who need the same. The trust-transfer mechanism (YC intro implies vetting) is especially powerful pre-traction.  
**Verdict: lock-defer** — only relevant if/when Verso does YC; note it as a "if YC, do this immediately" tactic.

---

## Summary Verdict

The essay's core value for Verso is the *sequencing discipline* (exhaust high-trust circles before moving to lower-trust ones) and the *content-before-launch* insight. Both are actionable in the §12 cold-start section. The founder-led sales emphasis confirms the founder-OS layer. Nothing here contradicts the established PRD — it sharpens the ordering and adds the pre-launch content-pull angle.
