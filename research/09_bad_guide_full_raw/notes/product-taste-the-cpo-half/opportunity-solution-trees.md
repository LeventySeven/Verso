# Note: Opportunity Solution Trees

**Source:** https://www.producttalk.org/opportunity-solution-trees/
**Author:** Teresa Torres
**Format:** Article / reference framework post
**Status:** read_full (WebFetch returned comprehensive framework content including structure, methodology, nine-step process, and real-world applications)

---

## Faithful Digest

### What an OST Is
An Opportunity Solution Tree is a visual framework that maps the path from a desired business outcome to testable solution assumptions. Four layers, top-down:

1. **Desired Outcome** (root) — the business/product metric to move
2. **Opportunity Space** — customer needs, pain points, and desires that drive the outcome
3. **Solution Space** — proposed solutions addressing each opportunity
4. **Assumption Tests** — validation activities for each solution's riskiest assumptions

The framework's primary purpose: keep discovery work continuously aligned with a single outcome, so teams don't drift into building things that don't move the metric that matters.

### Seven Key Benefits (verbatim from source)
The OST helps teams:
- "Resolve the tension between business needs and customer needs"
- Build shared understanding of how to reach desired outcomes
- Adopt a continuous (not project-based) discovery mindset
- Unlock better decision-making and faster learning cycles
- Build confidence in knowing what to do next
- Enable simpler stakeholder management

### The Outcome Layer: What Counts
Torres distinguishes three outcome types:
- **Product outcomes:** customer behavior or sentiment changes (preferred)
- **Business outcomes:** financial metrics (too lagging, often outside the team's control)
- **Traction metrics:** single-feature adoption (too narrow)

The resolution: "when we create business value, we earn the right to serve our customer over time" — so the right outcome layer is a product outcome that is both customer-centered and causally connected to the business metric.

### Opportunity vs. Solution: The Diagnostic Test
**Opportunity:** an unmet customer need, pain point, or desire. Multiple possible solutions exist.
**Solution:** a specific product, feature, service, or workflow addressing an opportunity.

Test: "Is there more than one way to address this?" If yes → opportunity. If no → it's likely a disguised solution (a specific implementation framed as a need).

This distinction matters because teams routinely mistake specific feature requests ("I want a CSV export button") for opportunities, when the underlying opportunity is something like "I need to use my data in other tools." Conflating them closes off solution exploration prematurely.

### Finding Opportunities: Story-Based Interviewing
The recommended method: story-based customer interviews using "Tell me about a time when..." prompts. This captures real-world context and naturally surfaces unmet needs without leading the witness.

Quote: "When we learn about opportunities in the context of a story, we develop a rich understanding of the underlying need."

The alternative — asking "what do you want?" or survey-style feature-preference questions — produces preference data, not opportunity data. Preference data tells you what people think they want; story data tells you where they are actually stuck.

### The Nine-Step Creation Process
1. Verify prerequisites (target customer theory, defined outcome, 3-4 completed interviews)
2. Place outcome at tree top
3. Map the opportunity space (synthesis from all customer stories)
4. Choose a target opportunity
5. Brainstorm solutions for that opportunity
6. Select three solutions to explore (always at least three, never just one)
7. Break each solution into its underlying assumptions
8. Test riskiest assumptions across all three options
9. Evaluate and decide

The key discipline: step 6 explicitly requires evaluating multiple solutions before committing. "When we compare and contrast our options, we make better decisions." The framework builds in assumption diversity before investment.

### Structuring the Opportunity Space: Four-Step Synthesis
1. Create an experience map from all customer stories (the chronological journey)
2. Map experience moments to top-level opportunity nodes
3. Group individual customer needs under relevant experience moments
4. Build parent-child relationships (a parent opportunity has multiple child opportunities)

Update cadence: every 3-4 customer interviews (~monthly for teams interviewing weekly). The opportunity space is living, not a one-time artifact.

### Prioritizing Opportunities: Four-Factor Assessment
Assessment considers:
- **Opportunity sizing:** how many customers experience this? How frequently?
- **Market factors:** how does addressing this affect competitive position?
- **Company factors:** alignment with mission, strategy, and capabilities?
- **Customer factors:** how important is this to the customer? How satisfied are they with current alternatives?

Notably: **effort is explicitly excluded from opportunity prioritization.** "Solutions take effort. But we aren't exploring solutions yet." Effort enters the framework at the solution layer, not the opportunity layer. Including effort in opportunity assessment causes teams to avoid big, important problems because they feel hard.

### Team Scope and Scale
OSTs work best with a **product trio**: product manager, designer, engineer — focused on a single outcome. Warning: "When you expand the scope beyond this, it tends to get too unwieldy." Company-wide OSTs fail because the outcome node becomes too abstract to drive meaningful discovery decisions.

### Connection to Roadmaps and Vision
- **Vision:** where you're headed long-term
- **OST:** how you get there (the structured discovery path)
- **Roadmap:** populated by solutions validated through the OST process

The OST is the operational middle layer — it connects aspiration (vision) to execution (roadmap) through continuous discovery.

---

## VERSO RELEVANCE

### [SHARPENS] §7 / §12 — OST as Verso's Internal Product Discovery Operating System
The OST framework is directly adoptable as Verso's internal product discovery method. The outcome node for Verso's primary product trio would be something like: "AI engineers successfully promote an ephemeral agent to durable checkpoint in <2 hours without re-architecting their code." This is a product outcome (measurable behavior change) that is causally connected to the business outcome (activation + retention of the structurally-aware senior AI engineer persona).

The three-solution discipline (step 6) is particularly valuable for Verso's seam design: rather than committing to a single API shape for the durable promotion, explore three candidate interfaces and test riskiest assumptions across all three before locking the API surface.
**Verdict:** adopt-now — use OST format for Verso product trio's next feature cycle; apply three-solution discipline to API surface decisions.

### [NEW-IDEA] §7 — Opportunity Space vs. Solution Space Distinction as a PRD Structure Tool
The OST's opportunity-vs-solution distinction gives a disciplined vocabulary for the Verso PRD. Currently §7 (demo-able wedge) and §8 (primitives) likely conflate opportunities and solutions. The fix: restate each PRD item as either "opportunity: [customer struggle]" or "solution: [specific mechanism]." This prevents the PRD from locking solutions before the opportunity is well-understood, and keeps the door open to alternative implementations.

Specifically: "agent.inspect()" is a *solution*; the underlying *opportunity* is "I can't see what my agent is doing mid-run and I can't intervene without restarting it." Keeping that separation means inspect() could be replaced by a better interface if testing reveals a higher-quality alternative.
**Verdict:** sharpen — restructure PRD §7-§8 using opportunity/solution distinction to prevent premature API lock-in.

### [CONFIRMS] §12 — Story-Based Interviews as Verso's User Research Protocol
The OST's insistence on story-based interviewing ("tell me about a time when...") directly confirms the JTBD research recommendation from the Christensen note. Both frameworks independently converge on: qualitative stories over surveys, circumstances over preferences, "why" over "what." This cross-source convergence strengthens the recommendation. The five JTBD questions map cleanly to the OST interview approach.
**Verdict:** confirm — story-based interview protocol is now double-confirmed; this is the canonical early-user research method for Verso.

### [NEW-IDEA] §1 / §12 — "Effort Excluded from Opportunity Prioritization" as a Moat-Reasoning Principle
Torres's rule — effort doesn't enter until the solution layer — has a Verso-specific implication for moat reasoning. The tendency to discount "make the harness more powerful" opportunities because they feel hard is exactly the bias the OST framework guards against. Verso's moat opportunities (eval corpus flywheel, seam switching costs, mental model capture) should be prioritized based on customer importance and satisfaction-with-alternatives, not on implementation effort. This keeps the roadmap pointed at defensible positions rather than easy features.
**Verdict:** adopt-now — use as a guardrail in roadmap prioritization: exclude effort from opportunity-layer decisions.

### [SHARPENS] §12 — OST Outcome Layer → Verso's Activation Metric Definition
The framework's insistence on product outcomes (customer behavior changes) over business outcomes (revenue) gives Verso a way to sharpen its activation metric. The question is not "how many people starred the repo" (traction metric) but "how many engineers successfully ran a durable checkpoint + resume cycle within their first week" (product outcome causally connected to retention). This is the OST outcome node for Verso's GTM discovery, and it should drive the design of the demo-able wedge: the wedge is only doing its job if it gets engineers to that activation behavior.
**Verdict:** sharpen — define Verso's OST outcome node as "durable checkpoint cycle completed within first week" and use it to evaluate whether the demo wedge is working.

### [CONFIRMS] Founder-OS — Product Trio as the Right Team Structure
The OST's prescription (product trio: PM + designer + engineer, single outcome) maps to Verso's current stage. For a founder-led project, the trio is collapsed into one person — which means the cognitive discipline of the OST (keeping opportunity and solution separate, updating the tree monthly, testing three solutions before committing) is even more important, not less. The OST is anti-drift infrastructure for a solo founder who is simultaneously customer, researcher, designer, and engineer.
**Verdict:** confirm — the OST discipline is especially valuable at Verso's current stage as anti-drift tooling.

---

## One-Line Verdicts per Finding
- OST as Verso's product discovery OS + three-solution discipline: **adopt-now**
- Opportunity/solution distinction → restructure PRD §7-§8: **sharpen**
- Story-based interviews → confirmed by two independent frameworks: **confirm**
- Effort excluded from opportunity prioritization → roadmap guardrail: **adopt-now**
- Product outcome node → sharpen Verso activation metric: **sharpen**
- Product trio discipline → solo-founder anti-drift tooling: **confirm**
