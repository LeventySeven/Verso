# Don't Call Yourself A Programmer, And Other Career Advice

**Source:** Patrick McKenzie (patio11)  
**URL:** https://www.kalzumeus.com/2011/10/28/dont-call-yourself-a-programmer/  
**Published:** October 2011  
**Meta:** Essay, ~30 min read  
**Section:** Leverage & Becoming Hunted (X + career capital)

---

## FAITHFUL DIGEST

Patrick McKenzie's "Don't Call Yourself A Programmer" is ostensibly career advice for new software engineers, but the underlying framework is a masterclass in **framing, positioning, and outcome-oriented communication** that applies directly to how a technical founder describes their product and their work. The essay's central thesis — that engineers systematically misframe their value and therefore undermonetize — is directly transferable to how Verso should describe itself.

### Thesis 1: Reject the Job-Description Identity

The essay's opening move is to argue that calling yourself a "programmer" is a category error. "Programmer" describes a narrow technical skill (writing code) when what employers actually want is someone who **solves business problems that generate economic value**. The label "programmer" positions you as a cost center — a skilled but expensive technician who types things into computers.

McKenzie's reframe: "What do you do?" should be answered not with a job title but with a value statement. Not "I'm a backend engineer" but "I've helped companies reduce infrastructure costs by X% through automated provisioning" or "I build systems that have processed $Y in transactions."

The key principle: **engineers are hired to increase revenue or reduce costs. Everything else is secondary.** Technical elegance, language choice, architectural purity — none of these matter to the employer who is writing the check. What matters is: did revenue go up, did costs go down?

### Thesis 2: Profit Centers vs. Cost Centers

McKenzie introduces a framework with lasting utility: organizations divide into **profit centers** (the divisions that directly generate revenue — sales, product, customer-facing engineering) and **cost centers** (the divisions that support operations — HR, compliance, internal engineering, IT).

Key observations:
- Engineers typically live in **cost centers** — highly-paid but still overhead
- **Nobody outsources profit centers** because that would destroy core revenue generation
- Outsourcing threatens cost centers; it never threatens profit centers
- The highest-leverage career move is to **align yourself with profit generation**, either by joining a profit-center team, or by quantifying your contribution to revenue in language that leadership understands

The implication: the engineer who says "I built the payment processing system that handles $50M/month" is in a different career position than the engineer who says "I work on backend infrastructure." Same job. Fundamentally different perceived value.

### Thesis 3: Business Value Communication as the Master Skill

McKenzie identifies the ability to **communicate your technical work in business terms** as the dominant career skill — more valuable than any technical skill. Specifically:

- You must be able to explain your contributions to: (a) a non-technical executive, (b) a bright 8-year-old, (c) colleagues in other specialties
- The ability to translate technical complexity into business impact is rare among engineers and commands a significant premium
- "Enterprise sales" describes every workplace conversation where you persuade colleagues or leadership to act on your recommendations — engineers do this constantly but rarely recognize it as sales

He makes a related point about confidence: "Modesty is not a career-enhancing character trait in American business contexts." Describing your contributions with confident ownership — without arrogance but without false modesty — is a learnable professional skill that compounds over time.

### Thesis 4: How Hiring Actually Works — The Speed of Beer

The essay's most practically useful section for distribution strategy: **most jobs are never posted publicly**. The actual hiring mechanism is informal social networks. Decision-makers mention a staffing need to peers; peers recommend people they know; the position fills before any formal posting.

McKenzie describes this as information traveling "at approximately the speed of beer" — at the pace of informal conversations, professional meals, conferences, and introductions. The formal HR process (job boards, resume submissions, interview cycles) is the fallback mechanism for positions that couldn't be filled informally.

**Implications for engineers:**
- Professional visibility in your field (conferences, user groups, public writing, OSS contributions) is not just personal brand — it is the mechanism by which you get pulled into opportunities before they are formally available
- The relationship quality of your network matters more than its size
- Being known as someone who does excellent work in a specific domain is the fastest path to being recommended

### Thesis 5: Negotiation and the Lifetime Multiplier

McKenzie makes a strong case that negotiation skill has an outsized lifetime compounding effect. Key practical tactics:
- Do not disclose previous salary (it anchors negotiation downward)
- Delay salary discussion until the employer has invested significant time evaluating you
- Always counteroffer — accepting first offer signals that you didn't have competing options
- Negotiate on multiple axes beyond salary: vacation, flexibility, title, equity, start date

The underlying principle: **every negotiation builds on the previous one**. A $10K improvement in starting salary compounds across raises, job changes, and future negotiations.

### Thesis 6: Credentials and What Actually Matters

McKenzie systematically deflates credential inflation:
- GPA matters only for resume screening at the top of the funnel; networking bypasses resume screening entirely
- Major and minor are nearly irrelevant post-graduation
- Language and stack specialization is overvalued — skilled engineers pick up new languages in weeks
- **What matters:** can you solve the problem? Can you communicate the solution? Can you be trusted to deliver?

The implication: the resume and credential-building focus that many early-career engineers invest in is a lower-leverage activity than building a professional network and developing business communication skills.

### Thesis 7: Startup vs. Megacorp

McKenzie's take is usefully contrarian: startups as default career advice for ambitious engineers is oversold. His actual analysis:
- Most startups fail; you work intensely for years, fail, and restart the job search
- Startups create networks of other failed founders, not established hiring managers
- Large corporations provide cutting-edge work (at sufficient scale), better compensation and stability, and networks of people who will later be decision-makers at many companies
- The right time for startups is after you have financial reserves, domain expertise, and an established network — not straight out of school

He frames startup involvement as a **lifestyle choice**, not a universal career accelerator. The lifestyle trade-offs (uncertainty, intensity, resource constraints) should be made with clear eyes.

---

## VERSO RELEVANCE

### [SHARPENS] §12 Positioning — "Don't call your product a framework"

McKenzie's core insight ("programmer" is the wrong identity because it describes inputs, not outputs) maps directly to Verso's positioning challenge. The failure mode is: "Verso is a Python agent framework" — which describes the artifact (a framework, an input) rather than the outcome (what gets solved). 

The McKenzie reframe applied: **Verso should be described through the business/engineering problems it eliminates**, not through its technical category. Not "an agent framework" but "the reason your agents don't fail silently in production" or "the infrastructure that turns a 9-nines agent into a reliable system." The category label ("framework") belongs in the technical details; the positioning lead should be the outcome.

This connects directly to the already-established principle against "-er-than-LangChain" Better-Trap language: that language also describes inputs ("better framework") rather than outputs ("your production agents recover from context loss automatically").

**Verdict: adopt-now** — audit every Verso positioning statement for input-language vs. output-language. Rewrite all input-descriptions as outcome-descriptions.

### [SHARPENS] §12 GTM — Visibility as the mechanism for becoming hunted

McKenzie's "speed of beer" insight sharpens the "becoming hunted" distribution thesis. The mechanism by which Verso gets adopted by structurally-aware senior engineers is not through their Google search ("best agent framework") — it is through **informal professional networks**. An engineering director mentions Verso to a VP in a meeting. A senior engineer writes "we're using Verso in production" in an internal Slack and gets three DMs. A Show HN post leads to a direct message from a team that had exactly the same production problem.

This means: Verso's GTM must create **visible artifacts that people can reference in informal conversations**. The X build-in-public posts, the Show HN, the README that explains the *judgment* behind the design — these are all "speed of beer" assets. They are the things that get mentioned in passing and create pull before any formal sales motion.

**Verdict: sharpen** — design every public artifact (post, README section, blog post) to be shareable in a 1:1 professional conversation, not just discoverable through search. The test: "Would a senior engineer send this link to a colleague with the message 'this is exactly the thing we've been missing'?"

### [CONFIRMS] §12 GTM — DX-led organic GTM (no sales motion)

McKenzie's entire hiring/networking model confirms that Verso's zero-sales-motion approach is correct for the target persona. Structurally-aware senior engineers do not respond to cold outreach or sales calls. They respond to technical content that demonstrates genuine understanding of their problems, shared by trusted peers through informal channels. The "speed of beer" is the GTM mechanism; Verso's job is to create the artifacts that get forwarded at beer speed.

**Verdict: confirm** — no delta.

### [NEW-IDEA] §12 Positioning — Profit center / cost center framing for Verso value proposition

McKenzie's profit center/cost center framework offers a specific positioning move for Verso with engineering leaders. The framing: "Your agent infrastructure is currently a cost center — it produces failure logs, not revenue. Verso is how you turn it into a profit center by making agent reliability measurable and improvable." This is outcome language that lands at the VP Engineering / CTO level, not just the individual contributor level.

The more specific version: every agent that fails silently, recovers wrong, or loses context in production is a cost event. Verso's harness (checkpoint/resume, evals-as-the-gradient, context density) converts those cost events into recoverable reliability events. That is a cost-reduction and revenue-preservation story, not a DX story.

**Verdict: lock-defer** — this framing is useful for enterprise/top-down adoption but may overcomplicate the early OSS positioning. Defer to when Verso has a commercial tier that enterprise buyers evaluate.

### [SHARPENS] founder_os — Outcome language in all public communication

McKenzie's principle that **professional communication should always lead with business outcomes** is an operating norm for how the Verso founder writes X posts and essays. The temptation in build-in-public is to show the technical work ("here's how we implemented checkpoint/resume") without leading with the outcome ("here's why agents fail silently and what it costs you"). Both are necessary; the outcome comes first.

The specific McKenzie framing: always be able to answer "so what does this mean for revenue or cost?" even about technical decisions. For Verso: "context density matters because lost context is a failed agent transaction, which is a cost event." That sentence is more persuasive than any amount of technical elegance.

**Verdict: adopt-now** — every X post that describes a technical decision should include an explicit outcome statement. Not just "we built X" but "X means you never lose Y again."

### [SHARPENS] founder_os — Conference/community visibility over SEO optimization

McKenzie's "speed of beer" model sharpens where to invest early-stage GTM energy. SEO and content marketing optimize for the formal channel (job boards / search). The "speed of beer" informal channel is optimized by: speaking at conferences (AI Eng, LLM tool meetups), appearing in Slack communities where structurally-aware engineers gather, contributing meaningfully to adjacent OSS projects, being the person whose technical takes get shared by people your target audience already trusts.

This is a different activity profile than "write SEO-optimized content." It is: invest in the relationships and community presence that make your name recognizable when it comes up at beer speed.

**Verdict: adopt-now** — schedule 1-2 conference talks or community appearances per quarter. Not just to present Verso but to be present in the communities where the 1,000 True Fans already gather.

---

## Source Rating

**Relevance to Verso:** High for positioning and GTM, moderate for founder-OS. The profit center/cost center framing and the outcome-language principle are the highest-value specific contributions from this source. McKenzie's "speed of beer" mechanism sharpens the "becoming hunted" thesis with a concrete model of how informal distribution actually works.
