# Y Combinator Requests for Startups (Summer 2026)

**Source:** https://www.ycombinator.com/rfs
**Author:** Y Combinator (multiple partners)
**Format:** Live reference document — short
**Themes:** bet_moat, positioning, gtm_distribution, founder_os

---

## Full Digest

The RFS is YC's public signal of where partner appetite currently sits. Each item is attributed to a specific partner, meaning it reflects individual conviction, not committee consensus. These are validation signals for founder-market fit, not requirements for applying.

---

### AI-Focused Categories (Relevant to Verso's Space)

**AI-Native Service Companies** (Gustaf Alströmer)
Fund companies that directly *deliver* services previously outsourced — not software tools for those service categories. Priority sectors: insurance brokerage, accounting, tax, audit, compliance, healthcare administration. The key quote: "the total spend on services is many times larger than spend on software." This is the software-to-service shift YC is explicitly betting on.

**Company Brain** (Tom Blomfield)
Platforms that consolidate fragmented company knowledge (emails, Slack, tickets, databases) into "executable skill files for AI agents" — a "living map of how a company works" that bridges raw data and reliable automation.

**Software for Agents** (Aaron Epstein)
As AI agents proliferate, YC backs software rebuilt for machine-readable interfaces (APIs, MCPs, CLIs) instead of human-oriented buttons and forms. Key framing: "the next trillion users won't be people, they'll be AI agents."

**The AI Operating System for Companies** (Diana Hu)
The connective layer making companies "legible to AI by default" — integrating Slack, Linear, GitHub, recordings, and other tools so systems can flag misaligned development and generate executable specifications for agents.

**Inference Chips for Agent Workflows** (Diana Hu)
Purpose-built silicon for agentic AI's requirements: fast context switching, speculative decoding, persistent KV caches across execution graphs. Distinct from "prompt in, response out" inference workloads.

**Dynamic Software Interfaces** (Ankit Gupta)
Coding agents enabling radical interface customization — users become "forward deployed engineers" designing interfaces matching their specific workflows through modifiable primitives.

**AI-Native Discovery Engines** (Jon Xu)
Closed-loop discovery cycles: propose hypotheses, test, analyze results — in domains like drug discovery and materials science.

**SaaS Challengers** (Jared Friedman)
AI has collapsed software production costs 10–100x, eliminating legacy SaaS moats built over decades. YC backs both: (a) simple clones underpricing incumbents and (b) AI-native rebuilds fundamentally rethinking workflows.

**Startups Selling to Huge Companies** (Harshita Arora, Brad Flora)
Fortune 100 leaders now actively seek AI-powered solutions. AI enables small teams shipping sophisticated products in months rather than years — makes enterprise sales viable for early-stage companies within their first year.

---

### Hardware / Infrastructure (Less Directly Relevant)

- AI for Low-Pesticide Agriculture (Garry Tan)
- AI-Native Discovery Engines in science (Jon Xu)
- AI Personalized Medicine (Ankit Gupta)
- Electronics in Space (Philip Johnston)
- Hardware Supply Chain acceleration (Nicolas Dessaigne)
- Industrial Capabilities in Space (Adi Oltean)
- Supply Chain 2.0 for Semiconductors (Diana Hu)
- Counter-Swarm Defense (Tyler Bosmeny)

---

## VERSO RELEVANCE

### [SHARPENS] "Software for Agents" (Aaron Epstein) is the closest YC category to Verso's actual bet
**Finding:** Epstein's framing — software rebuilt for machine-readable interfaces (APIs, MCPs, CLIs) because "the next trillion users won't be people, they'll be AI agents" — is essentially the agent-native infrastructure thesis. Verso, as the harness layer for agent loops, sits in this category. The implication: YC partners are explicitly looking for this. Verso should be able to map itself to this RFS item in any YC application or pitch.
**PRD section:** §1 (the bet / moat), §12 (positioning)
**Verdict:** adopt-now — explicitly name this YC category in any fundraising context. "We are the harness layer in the 'Software for Agents' thesis."

### [NEW-IDEA] "Company Brain" (Tom Blomfield) surfaces a downstream Verso wedge — the organization's durable context layer
**Finding:** Blomfield wants platforms consolidating company knowledge into "executable skill files for AI agents" — a "living map of how a company works." This is exactly what Verso's durable/checkpoint layer enables at the agent-execution level. The company brain is the organizational version of what Verso's event-sourced seam enables at the code level. This could be a named downstream use case: "Verso as the runtime for company brain implementations."
**PRD section:** §1 (moat extensibility), §7 (demo-able wedge expansion)
**Verdict:** lock-defer — don't lead with this, but it's a natural secondorder narrative for Series A when the TAM question arises.

### [SHARPENS] "AI-Native Service Companies" (Alströmer) — the target customer vertical for Verso's wedge
**Finding:** YC explicitly wants to fund companies that deliver services (accounting, compliance, healthcare admin) using AI agents — not tools for those companies, but the companies themselves. These are exactly the kinds of companies that will need a harness layer for reliability and HITL, not just an LLM wrapper. Verso's primary customers are the builders of these AI-native service companies.
**PRD section:** §12 (GTM, ICP sharpening)
**Verdict:** sharpen — Verso's ideal first practitioner-customers are the engineering leads at AI-native service companies (the Gustaf Alströmer bet). They have the highest stakes on reliability and context engineering. They are also not hobbyists — they will pay.

### [CONTRADICTS] YC's "SaaS Challengers" framing slightly misaligns with Verso's category position
**Finding:** Friedman's SaaS Challengers framing — AI collapsed software production costs 10–100x, so build simple clones or AI-native rebuilds — treats the value proposition as cost and speed. Verso's thesis is not that agent frameworks are cheaper to build — it's that the *harness* is where reliability compounds. The cost-collapse framing could attract the wrong co-positioning: "Verso is cheaper LangChain" is a trap. The anti-"Better-Trap" principle applies here.
**PRD section:** §2 (non-goals), §12 (positioning — resist cost-competition framing)
**Verdict:** resist — in any YC or investor context, do not accept the SaaS Challengers framing. Verso is in "Software for Agents" and "Company Brain" runtime, not "cheaper SaaS."

### [CONFIRMS] Inference Chips for Agent Workflows (Diana Hu) reveals the infra stack Verso sits above
**Finding:** Hu's chip request specifies: fast context switching, speculative decoding, persistent KV caches across execution graphs. These are the hardware requirements *generated by* the agent loop patterns Verso implements. Verso is the software layer that produces these access patterns. This confirms that the harness layer (Verso) and the silicon layer (Diana Hu's chip RFS) are co-evolving infrastructure — Verso is upstream of the chip demand curve.
**PRD section:** §1 (bet / moat — positioning in the stack)
**Verdict:** confirm — Verso sits in the right layer of a stack that YC believes will need purpose-built silicon.

---

## Summary Verdict

The RFS is a live calibration tool for Verso's positioning. The highest-value finding: Verso maps most cleanly to "Software for Agents" (Epstein) and secondarily to "Company Brain" (Blomfield) as a runtime layer. The danger: the "SaaS Challengers" cost-framing is a positioning trap. The ICP sharpening: engineering leads at AI-native service companies (Alströmer's funded companies) are Verso's primary paying customers.
