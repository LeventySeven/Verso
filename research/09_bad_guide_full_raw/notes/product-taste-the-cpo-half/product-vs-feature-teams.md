# Product vs. Feature Teams

**Source:** Marty Cagan (SVPG) · Silicon Valley Product Group  
**URL:** https://www.svpg.com/product-vs-feature-teams/  
**Published:** SVPG (canonical article, referenced across field)  
**Status:** read_partial (SVPG returned HTTP 403; content reconstructed from multiple mirrors, secondary analyses, and Cagan's own extended writing on empowered teams at creatoreconomy.so and wind4change.com — core distinctions fully captured)  

---

## Faithful Digest

Cagan's article establishes the canonical distinction between two kinds of product teams. The framing is deceptively simple and has become the dominant vocabulary for product org design.

### The Core Distinction

**Feature Teams:**
- Receive prioritized feature lists / roadmaps, not strategy
- Focus on *output* (features shipped)
- Value and business viability delegated to the stakeholder or executive who requested the feature
- Engineers and designers operate in "delivery" mode — not involved in discovery
- "Mercenary mindset" — not empowered or responsible for customer impact

**Product Teams (Empowered):**
- Cross-functional: product manager + designer + engineering, all three legs of the stool
- Focused on *outcomes* (measurable customer/business results)
- Given problems to solve, not solutions to build
- All three accountable for their dimension: PM owns value/viability, designer owns usability, tech lead owns feasibility
- "Missionary mindset" — believers committed to solving customer problems

> "It's all about solving problems, not implementing features." (Cagan)

> "Mercenaries build whatever they're told. Missionaries are believers committed to solving customer problems." (Cagan)

### The Four Product Risks

Every product decision involves four risks:
1. **Value risk**: Will customers buy or use it?
2. **Usability risk**: Can users operate it?
3. **Feasibility risk**: Can we build it with available resources?
4. **Business viability risk**: Will it work for the business?

In feature teams, value and viability risk are pushed upstream (to the stakeholder/roadmap owner). In product teams, all four risks are owned by the team.

### How Work Is Allocated

The single most important variable: "Whether leaders are giving teams solutions to build or problems to solve." 

In feature teams, the PM becomes a project manager "herding cats" to deliver features specified by others. In product teams, the PM is responsible for deep customer, data, industry, and business knowledge — functioning as a problem-solver who could theoretically become "the CEO of the product."

The structural implication: "Strong product managers should be viewed as potential future leaders." Feature team PMs are order-takers; product team PMs are emergent executives.

### Startup vs. Big Company Context

Cagan notes that empowered product teams are rare in practice — particularly at large companies where command-and-control management and roadmap-driven planning are entrenched. The feature team model is the *default* that organizations slide into without intentional design.

---

## VERSO RELEVANCE

### [NEW-IDEA] §1 Bet/Moat — Verso must not be a "feature framework"

The product-vs-feature-team distinction maps onto a framework design distinction: a "feature framework" gives builders features to plug in (pre-built chains, tools, integrations). A "product framework" gives builders a problem framing and judgment surface they own. LangChain is predominantly a feature framework — it gives you `LLMChain`, `AgentExecutor`, tools, retrievers. Verso is a product framework: it surfaces the four risks (analogized: value=context quality, usability=DX, feasibility=execution reliability, viability=cost/reliability at scale) and empowers the team to own them, with harness infrastructure that exposes them.

The positioning implication: LangChain is the feature-team framework. Verso is the empowered-team framework. You don't need to say "better than LangChain" — you say "built for builders who own outcomes, not builders who implement roadmaps."

**Verdict: adopt-now** — §1 moat: Verso's counter-position against LangChain can be expressed cleanly via this vocabulary. LangChain = feature-team framework (gives you solutions). Verso = product-team framework (gives you ownership surface).

### [SHARPENS] §12 Positioning — "problems to solve, not features to build" as the positioning axis

The Cagan frame provides the cleanest single-sentence positioning axis for Verso that has appeared in any source so far:

> "It's all about solving problems, not implementing features."

Applied: Verso does not give you agent features. Verso gives you the ownership surface to solve the agent reliability problem your way. This is the counter-position that does not require mentioning LangChain, does not claim global superiority, and resonates immediately with the structurally-aware engineer who has been frustrated by the feature-assembly model.

**Verdict: sharpen** — §12: test "problems to solve, not features to build" as a positioning line. It is shorter and more resonant than most current candidate lines.

### [SHARPENS] §7 Demo-able Wedge — the "four risks" frame sharpens what inspect() is measuring

Cagan's four risks (value, usability, feasibility, viability) give Verso's eval/inspect surface a crisper purpose description. `agent.inspect()` is not a debugger. It is the *risk surface* — the interface through which the team sees and owns all four risk dimensions in real time. Eval-corpus invariants are value/viability risk checks. The inspect surface makes feasibility visible. The one-flag durable diff changes the viability risk profile permanently.

**Verdict: sharpen** — §7: frame inspect() and the eval surface explicitly as "the four-risk ownership surface." This makes the taste argument functional, not aesthetic: "we give you the surface to own your risks."

### [CONFIRMS] §2 Non-Goals — principled refusal to be a delivery vehicle

Cagan's description of feature teams as "delivery" mode maps directly to Verso's non-goal of being a delivery wrapper. Verso explicitly does not give you pre-built agents that deliver answers. It gives you a harness that gives you ownership. This is already a Verso non-goal; the Cagan vocabulary makes it crisper: "We are not a delivery framework. We are an ownership framework."

**Verdict: confirm** — §2 language already implies this. Worth stating in the Cagan vocabulary explicitly.

### [NEW-IDEA] §12 GTM — target engineers in "product team" positions, not "feature team" positions

The Cagan lens suggests a GTM targeting refinement: the structurally-aware senior engineer persona is, specifically, an engineer on a *product team* — one that owns outcomes, has latitude to solve problems their way, and is held accountable for reliability. Engineers on feature teams are given solutions; they don't need a harness that exposes risk. The cold-start GTM target is engineers who feel the ownership weight — who are being asked to ship a reliable agent experience and have no pre-specified solution to implement.

This is a behavioral targeting insight, not just demographic. It suggests Verso's distribution content should speak to "you've been given the outcome, not the roadmap" — not "you've been given a task to code."

**Verdict: adopt-now** — §12 GTM: content should open with the ownership weight ("you own the reliability of this agent, and nobody told you how"), not the task weight ("you need to build an agent"). This filters for the product-team engineer immediately.

### [SHARPENS] founder_os — the Verso maintainer as "product team PM"

The founder-OS layer: the Verso maintainer (as OSS project lead) must operate as a product-team PM, not a feature-team PM. Receiving GitHub issues asking for features (MCP support, LangChain bridge, memory module) is the feature-team request signal. Owning the problem ("agent reliability in production for structurally-aware engineers") and having the latitude to decide which features solve it is the product-team signal. Cagan's "mercenary vs missionary" distinction maps onto the question of whether the maintainer ships what issues request or what the product vision requires.

**Verdict: lock-defer** — founder-OS index; not §1–§12 PRD content.

---

## One-Line Verdict Per Finding

| Finding | Verdict |
|---|---|
| Verso = product-team framework (ownership surface) vs LangChain = feature-team framework (delivery) | adopt-now |
| "Problems to solve, not features to build" as positioning test line | sharpen |
| Four-risk frame sharpens what inspect() / eval surface is doing | sharpen |
| GTM content should open with ownership weight, not task weight | adopt-now |
| "Delivery framework vs ownership framework" — sharper §2 non-goal language | confirm |
| Maintainer = product-team PM: mission over feature requests | lock-defer (founder-OS) |
