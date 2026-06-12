# Note: Build Better Products with Continuous Product Discovery

**Source:** https://www.youtube.com/watch?v=9RFaz9ZBXpk
**Mirror/Transcript:** Lenny's Podcast episode + It Shipped That Way Podcast Ep. 27 transcript (https://www.itshipped.fm/episodes/27) + Pendo Product Love Podcast full transcript (https://www.pendo.io/pendo-blog/full-transcript-teresa-torres-on-the-product-love-podcast/)
**Author:** Teresa Torres
**Format:** Podcast / talk · 48m
**Status:** read_partial — no direct transcript found for the YouTube video ID 9RFaz9ZBXpk specifically; sourced from multiple Teresa Torres podcast transcripts covering the same material (all post-2021 continuous discovery content is convergent; the Lenny's episode summary page was unreachable via HTTP 522 but content was retrieved from other episode transcripts and the Pendo full transcript)

---

## Faithful Digest

### Core Thesis: Discovery Is a Weekly Operating Rhythm, Not a Phase

Torres' central argument is that product discovery should be **continuous and embedded** in daily work — not a waterfall phase that precedes building. The trigger is a team commitment to talk to customers at least once per week while pursuing a defined outcome. This shifts discovery from "a thing we do at the start of a project" to "a habit that shapes every decision."

Direct quote: "I think a product team should be engaging with customers at least once a week." She pre-empts the "no time" objection: conversations don't need to be formal hour-long sessions with three-page guides — brief 15-minute touchpoints create "a continuous drip of the customer perspective in daily work."

### The Opportunity Solution Tree (OST) Framework

Four-layer visual structure from outcome to evidence:
1. **Desired Outcome** (root) — the product/business metric to move
2. **Opportunity Space** — customer needs, pain points, and desires
3. **Solution Space** — proposed solutions for each opportunity
4. **Assumption Tests** — validation activities for each solution's riskiest assumptions

Key distinction: **Opportunity vs. Solution**. An opportunity is an unmet need where multiple solutions are possible. A solution is a specific implementation. Teams routinely mistake feature requests ("I want a CSV export button") for opportunities, when the underlying opportunity is something like "I need to use my data in other tools." Conflating them closes off solution exploration prematurely.

Torres distinguishes outcome types:
- **Product outcomes** (preferred): customer behavior or sentiment changes
- **Business outcomes**: financial metrics — too lagging, often outside team control
- **Traction metrics**: single-feature adoption — too narrow; can incentivize teams to change happy customers' behavior unnecessarily

Quote: "We really want to make sure we're not setting outcomes that incentivize our teams to encourage our customers to do things they don't want to do."

### The Confidence Bias Challenge

Drawing on Daniel Kahneman's research: people express confidence based on coherent narratives they construct, not on accuracy. A customer might claim "fit" matters most when buying jeans, but subsequent questioning reveals convenience and price drove the actual decision. Story-based interviewing (asking "Tell me about the last time you bought jeans?" rather than "What criteria matter?") bypasses aspirational self-reporting by tapping visual/episodic memory.

Quote: "Even knowing about these biases, doesn't protect you from them because your brain will still construct a coherent story and it's going to feel like truth."

### Assumption-Based Testing vs. Feature Prototyping

Most teams prototype entire features/ideas. Torres advocates breaking ideas into **underlying assumptions** and testing each independently through low-fidelity experiments. Benefits:
- Faster iteration
- Richer learning (ideas share assumptions across opportunity spaces)
- Specific insight into what fails
- Opportunity to design around faulty assumptions before building

She critiques overreliance on A/B testing: "18th-century bloodletting — useful in rare cases but overused broadly." Core problem: A/B testing requires building features first, delaying learning until after significant investment. Recommended experimental toolkit: prototyping, smoke screen tests, concierge tests, Wizard of Oz tests.

### The Escalation-of-Commitment Trap

Once teams invest in an idea, they psychologically identify with it, creating confirmation bias that blinds them to contradicting evidence. Torres' prescription: "Be passionate about problems, not products." Staying committed to the customer need (not the solution) lets teams iterate freely on implementations.

### Durable Teams and Metric Stability

Torres argues that many organizations switch metrics quarterly (engagement, then retention, then acquisition), preventing teams from "getting the depth of learning that it takes to really move the needle on a metric." Durable teams with consistent outcome metrics over extended periods build irreplaceable depth of product and customer knowledge.

### Opportunities > Problems (Framing)

Torres argues for "opportunities" over "problems" as the framing concept because: products like sports betting and luxury travel don't solve problems — they satisfy desires. Problem-focused framing limits thinking to friction removal. Opportunity framing encompasses both customer value and business value.

Quote: "when we talk about opportunities and not problems to solve, there are opportunities for the business...those opportunities actually represent customer value."

### Adoption Happens One Habit at a Time

Complete organizational transformation fails; small changes embedded in existing practices succeed. Implementation philosophy: teams needn't apply every discovery habit equally — judgment determines where to invest based on business impact.

---

## VERSO RELEVANCE

### [SHARPENS] §2 Non-goals: The "assumption-first" vs "feature-first" split
Torres' core critique of A/B testing — that it forces you to build before you learn — maps directly to the Verso non-goal: "not an experiment platform." But her framing sharpens the WHY: assumption-based testing with concierge/WoZ/prototype runs before code exists is structurally different from in-production metric tests. Verso's eval-corpus flywheel is post-build validation; Torres describes the pre-build discovery layer. These are complementary, not competing, but the distinction matters when defending the eval design: Verso evals are not assumption tests, they are reliability meters on known-good behavior.
**Verdict:** Sharpen the eval non-goal language: "evals are reliability/regression instruments, not discovery instruments."

### [SHARPENS] §12 Positioning: The "desired outcome as root" OST layer maps to Verso's §1 bet
Torres' OST starts with a single desired outcome at root — everything else is subordinate to moving that metric. This is structurally identical to Verso's framing that the agent harness serves a specific production outcome (reliability at scale) rather than being a general tool. The positioning implication: Verso should articulate its own "desired outcome at root" the way Torres articulates OST roots — one sentence, a product behavior metric, causally linked to a business metric. If the root is "measured lift on pass@k eval" then everything in the harness is subordinate to that.
**Verdict:** Useful positioning discipline: state the root outcome explicitly, not as a feature list.

### [NEW-IDEA] Founder-OS: Continuous discovery rhythm as the VERSO operating model for the AI-engineer persona
Torres argues that the discovery habit fails when treated as "research phase" rather than as a weekly operational rhythm. For Verso's primary persona (structurally-aware senior / AI engineer), the analog is: evals are not a shipping gate (phase) but a weekly feedback loop embedded in the dev cycle. Torres' language for advocating this to PMs ("continuous drip of customer perspective") gives Verso a parallel pitch for the AI engineer: "continuous drip of ground-truth signal on your agents." This reframes evals from "thing you do before launch" to "harness discipline."
**Verdict:** Borrow the framing: eval-as-operating-rhythm, not eval-as-gate.

### [CONFIRMS] §7/§12 Product taste: Escalation of commitment = the "we've always used LangChain" trap
Torres' escalation-of-commitment argument (teams identify with their chosen solution) explains the exact switching friction Verso must overcome. Teams on LangChain/DSPy aren't irrational — they're exhibiting Kahneman-confirmed cognitive bias toward sunk investment. This confirms that the Verso demo wedge needs to be an "assumption test" (Torres' framing), not a feature comparison: show the behavior you can't get elsewhere in 3 lines, make the alternative salient with zero switching cost in the first session.
**Verdict:** Confirms the 3-line side-by-side as the correct wedge form — it's a low-fidelity assumption test, not a sales pitch.
