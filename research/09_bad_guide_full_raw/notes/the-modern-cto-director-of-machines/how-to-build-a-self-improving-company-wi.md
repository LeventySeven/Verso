# How to Build a Self-Improving Company with AI

**Source:** https://www.youtube.com/watch?v=t-G67yKAHBQ  
**Transcript:** https://www.odaily.news/en/post/5210879 (detailed summary with verbatim passages); corroborated by https://www.startuphub.ai/ai-news/artificial-intelligence/2026/ai-native-companies-building-self-improving-organizations and https://startup.whatfinger.com/2026/05/21/how-to-build-a-self-improving-company-with-ai/ (chapter structure)  
**Status:** read_partial (no word-for-word transcript found; reconstructed from 3 independent detailed summaries covering all chapter headings; direct quotes marked with confidence)  
**Speaker:** Tom Blomfield, YC General Partner (co-founder Monzo, Broom)  
**Event:** YC Batch Talk, published May 19 2026  
**Duration:** ~13 min

---

## Roman Legions Frame (Opening Reframe)

Traditional organizations still operate hierarchically like Roman legions: information flows up through management chains, commands flow down. This was a rational design for specific communication constraints.

AI dissolves the assumptions that made that structure necessary. The frame shift: move from "hierarchical organization" to "intelligent organization driven by AI-native software."

---

## Copilots Are the Wrong Mental Model

Common misdirected AI adoption goals: "make engineers 20% more productive," "add copilots to existing workflows." Blomfield argues this misses the fundamental opportunity.

*"What's truly worth thinking about isn't how to add an AI tool to an old organization, but reimagining what the company itself is."*

The frame shift from "AI as tool" to "AI as organizational substrate" is the core thesis.

---

## Domain Knowledge Extraction

The real bottleneck is not code-writing capability — it is business knowledge scattered across "people's brains, Slack messages, emails, Notion documents." This must become machine-readable organizational context.

Once systematized, the company can operate as an intelligent system rather than a bureaucratic hierarchy. The YC example: 2,000 hours of office hours recordings → diarized → categorized → synthesized into a 150-page user manual *in one weekend*. Now updated as a continuously living repository.

*"If it is recorded, it happened to the AI. If it did not get recorded, it did not happen to your intelligent system."*

This implies an organizational mandate: record everything (emails, Slack, meetings, office hours) and process through speaker diarization and summarization. The AI can only act on what is legible to it.

---

## The Self-Improving Loop Architecture (Five Layers)

Blomfield describes five integrated layers:

1. **Sensor layer** — Customer emails, support tickets, product telemetry; real-world inputs
2. **Strategy/Decision layer** — Rules defining AI permissions and constraints; what it can do autonomously vs. must log vs. must escalate
3. **Tool layer** — Deterministic APIs and callable functions; the execution surface
4. **Quality gate** — Safety filters and human review for high-risk items; the eval and validation layer
5. **Learning mechanism** — Feedback loops enabling continuous self-correction

YC's internal monitoring agent demonstrates this in practice: observes every internal query → identifies failures → determines root cause → writes code fix → submits PR → agent reviewer merges → deploys. *"Continuously get better without human intervention."* The system improves while you sleep.

---

## Burn Tokens, Not Headcount

Revenue-per-employee ratios increased five-fold within 18 months at YC companies. Future organizational bottleneck shifts from employee count to token consumption.

Blomfield proposes measuring organizational effectiveness through "token usage" as a directional metric (while acknowledging gaming potential).

Extreme scenario: one person with advanced AI tools may replace thousands of traditional workers. Potential ~80% headcount reduction at established organizations. "Closing a call center to replace the team with AI service agents will take a handful of days."

---

## Software Is Ephemeral, Context Is Valuable

Internal software should be treated as temporary artifacts: *"You can generate it and regenerate it."* When models get smarter, throw away the old software and generate a new version.

What must be preserved meticulously: data and context. Blomfield saves all emails as Markdown, never discarding anything.

*"Software is ephemeral, context is valuable."*

This is the direct inverse of traditional software asset valuation. The valuable IP becomes organizational context, not the codebase.

---

## Middle Management Is Over

Blomfield states flatly: "I believe middle management is over." Coordination problems previously requiring supervisory layers can be handled by AI. The future organization requires only two role types:

- **Individual Contributors (ICs)** — All team members serve as builders/operators; bring concrete prototypes, not concepts
- **Directly Responsible Individuals (DRIs)** — Single named person accountable for outcomes; prevents diffusion of responsibility into AI systems

No committees. No groups. One named person per initiative.

---

## Where Humans Still Matter

Humans occupy "the edge of this brain, responsible for interacting with the real world." Critical domains remaining human:

- Novel, unfamiliar situations outside training distribution
- Ethical judgments requiring human values
- High-risk emotional moments (co-founder disputes)
- Live sales pitches requiring human presence

*"Humans are where this intelligent system touches reality."*

---

## The "Holy Shit Moment at YC"

Chapter heading from the talk structure — refers to the experiential shift when founders realize AI loops actually work at organization scale. No detailed verbatim content recovered from summaries; appears to be a narrative turning point in the talk about witnessing self-improving loops run overnight.

---

## Verbatim / Near-Verbatim Quotes (confidence: high from multiple independent summaries)

- *"AI is not something you bolt onto the side of a company. The company itself has to be built with self-improving AI loops from the ground up."*
- *"If it is recorded, it happened to the AI. If it did not get recorded, it did not happen to your intelligent system."*
- *"Software is ephemeral, context is valuable."*
- *"Burn tokens, not headcount."*
- *"I believe middle management is over."*
- *"Humans are where this intelligent system touches reality."*
- *"Copilots are the wrong mental model."*

---

## VERSO RELEVANCE

### [SHARPENS §4 — seam (tactical↔durable)]
"Software is ephemeral, context is valuable" is the sharpest external articulation of why Verso's tactical/durable seam exists. Tactical agents produce ephemeral execution; the durable layer preserves event-sourced context. The seam is precisely the mechanism that makes context permanent without making code permanent. One-flag promotion becomes "keep the context, regenerate the code when models improve." Verdict: sharpens §4 significantly; this quote belongs in positioning copy.

### [SHARPENS §5.4 — memory]
The organizational legibility requirement ("record everything, make it machine-readable") maps directly to Verso's append-only history and 4-tier typed memory. Blomfield's argument for why this matters at org scale is the same argument for why it matters at agent scale: the system can only improve on what it can read. The temporal versioning in Verso's memory tier is the micro-scale version of Blomfield's "continuously updated living repository." Verdict: sharpens §5.4; confirms the design choice.

### [NEW-IDEA — §6.1 durable / §6.2 multi-agent]
The five-layer self-improving loop (sensor → decision → tool → quality gate → learning mechanism) is a useful reference architecture for Verso's durable tier design. The "quality gate" layer maps to embedded in-process evals + judge-panel. The "learning mechanism" layer (feedback loops enabling self-correction) is partially addressed by reinforcement-on-tool-return but Verso doesn't yet have an explicit mechanism for "identify failure, write fix, submit PR, merge, deploy" cycles. This could be a durable-tier capability: an improvement-agent that observes loop failures and updates AGENTS.md or tool definitions. Not yet in PRD as a first-class pattern.

### [CONFIRMS §5.5 — evals]
The quality gate as a mandatory layer in every self-improving loop confirms Verso's evals-first positioning. The YC internal monitoring agent example shows evals are not optional instrumentation — they ARE the mechanism that enables improvement. Verdict: confirms; strong external authority.

### [SHARPENS §12 — strategy]
"Copilots are the wrong mental model" as a frame directly supports Verso's counter-position. The framing also implies Verso should not pitch itself as "a copilot for agent development" but as "organizational substrate" — the framework that makes self-improving loops possible. The DRI concept (one named person accountable) maps to Verso's HITL gate in the durable tier: explicit human accountability, not diffused committee approval. Verdict: sharpens §12 positioning and §6.1 HITL design.
