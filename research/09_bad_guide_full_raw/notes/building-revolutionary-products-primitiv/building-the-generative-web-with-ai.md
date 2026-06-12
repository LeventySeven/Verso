# Building the Generative Web with AI (Guillermo Rauch, Sequoia)

**Source:** https://www.youtube.com/watch?v=YoxeOS60qBc
**Transcript origin:** Sequoia Capital podcast page (sequoiacap.com/podcast/training-data-guillermo-rauch/) + Inference by Sequoia substack write-up + startuphub.ai summary; original talk also on YouTube. All three sources read; no paywall barrier. Status: read_full (composite of multiple transcript sources).
**Meta:** Guillermo Rauch (Vercel CEO) · Sequoia Training Data · 1h · August 5, 2025. Hosts: Sonya Huang and Pat Grady.

---

## Core Thesis

The web is undergoing its third paradigm shift: static → dynamic → generative. Every assumption about who builds software, how software is distributed, and what software looks like is currently up for disruption. Reliability — not raw capability — is the product differentiator that separates demos from real products.

---

## Key Arguments

### 1. ChatGPT as Unexpected Discovery Layer

ChatGPT's training data includes Vercel docs and Next.js documentation. When users ask ChatGPT how to deploy React apps, it recommends Vercel. Rauch: "People would come to our booth and tell them that they'd learned of Vercel because ChatGPT told them to use Vercel." Signups to Vercel from ChatGPT have been "growing exponentially." This is an entirely new customer acquisition channel that emerged from model training — not from paid marketing. The implication: being the recommended infrastructure in LLM training data is a new form of distribution moat.

### 2. v0 Metrics and "Dev-Adjacent" Profiles

- 3M+ builders on v0 as of August 2025
- User base doubled year-over-year "with zero cost for our entire user base"
- ~1,000 security vulnerabilities prevented per day (tens of thousands total)
- Fortune 10 companies on enterprise tier
- Rauch: "Maybe single digit millions, two digit millions of developers. Now we can actually give this guidance and direction to a much broader set of people." Designers, marketers, PMs — "anybody with a keyboard." — "Instead of yapping into your team chat, yap into v0 and you're creating more value."

### 3. Taste as Infrastructure / Embedding Best Practices

- The classic problem: frameworks put you in a "pit of success" by nudging conventions. LLMs go further by *encoding* best practices into generation.
- Example: iOS Safari theme bar color must match page background. "In the past, we'd have to build frameworks and hope people upgrade. Now we can embed all of those learnings into the model."
- "LLMs are the thing after frameworks. Frameworks put you in a pit of success. LLMs put best practices into the generation itself."
- v0 fine-tunes specialist models to ensure generated code actually functions correctly, not just looks correct.

### 4. Reliability as the Non-Negotiable

- "If something doesn't work immediately, they abandon it." — users of AI coding tools have zero patience for errors.
- "Getting it to the point where it can be reliable...took a lot of work, fine-tuning."
- v0's composite architecture: base model (Claude Sonnet) + RAG injection + stream-fixing + AST corrections + fine-tuned AutoFixer. The harness around the model, not the model itself, is the quality differentiator.
- Vercel infrastructure is built to "detect and repair any kind of mistake" autonomously — "perfectly diagnose" problems and route to solutions.

### 5. Ephemeral / Just-in-Time Software

- "It seems like the world is heading toward just-in-time software created for the individual. Applications generated on demand rather than downloaded."
- "Everything will be ephemeral, for that matter...Everything will be generative just in time for everybody."
- The cost of prototyping has collapsed: "V0 prototypes are replacing pitch decks. By the time you get to your pitch today, it'd be rare not to have a working frontend."

### 6. Agent-First Design Imperative

- "Your customer is no longer the developer. Your customer is the agent that the developer or non-developer is wielding." — this fundamentally changes API design, runtime requirements, and framework architecture.
- Rauch uses the Waymo metaphor: "mostly autonomous with human intervention capability for edge cases."
- v0 integrates directly with Git workflows: branching within v0, live preview, dependency installation, PR generation with descriptions, preview deployments on production infra.
- Workflow durability: "It's using a workflow so the game could run forever. The game could literally run forever or until I run out of tokens." (on agentic chess match) — Vercel Workflows handles provider outages and timeouts.

### 7. Two-Class Developer Model

1. **App Creators** (v0 users): conversational interface, natural language, minimal friction
2. **Platform Builders** (Vercel customers): traditional developer tools, infrastructure-level control

### 8. The 3-5 Year Prediction

"In the next three years we're going to see kingdoms collapse...companies that were born on the internet that have not been able to make those adjustments fast enough" will struggle, while "AI native companies rise to unprecedented heights very, very quickly."

### 9. The "Clean Slate" Practice

Rauch's personal discipline: every weekend, start something from scratch on Vercel. "I get to dogfood the platform and also get to be a beginner — see what the actual first-time experience is." The founder as the canonical new user.

### 10. On Uncertainty / Strong Beliefs

"I encourage people not to have too many strongly held beliefs. Any time people say AI can't do X, I try to be on the side of AI. Six months later, the situation changes."

---

## Verbatim Quotes

1. "LLMs are the thing after frameworks. Frameworks put you in a pit of success. LLMs put best practices into the generation itself."
2. "It seems like the world is heading toward just-in-time software created for the individual. Applications generated on demand rather than downloaded."
3. "Your customer is no longer the developer. Your customer is the agent that the developer or non-developer is wielding."
4. "If something doesn't work immediately, they abandon it." (on AI coding tools and reliability)
5. "Getting it to the point where it can be reliable...took a lot of work, fine-tuning."
6. "In the next three years we're going to see kingdoms collapse...AI native companies rise to unprecedented heights very, very quickly."
7. "Instead of yapping into your team chat, yap into v0 and you're creating more value."

---

## VERSO RELEVANCE

### [CONFIRMS §5.2] Context engineering as the real product

Rauch's composite architecture for v0 — RAG injection, stream-fixing, AST corrections, fine-tuned AutoFixer on top of Claude Sonnet — is the practitioner proof that the *harness around the model is the product*, not the model. The base model is a commodity; the context engineering is the moat. This is the core §5.2 argument.
One-line verdict: direct confirmation that loop+harness is where product value lives.

### [SHARPENS §5.5] Reliability as the primary eval criterion

"Users abandon after first failure" is a more extreme version of the two-failures rule. The specific mechanism: v0 has built-in product metrics (code acceptance rates, deployment success, application engagement, whether generated code actually renders correctly). This is embedded, in-process eval — precisely §5.5's pattern — but Rauch names *reliability* as the first-order outcome, not accuracy. Distinction matters: reliability = consistently succeeds, not just occasionally brilliant.
One-line verdict: sharpens eval framing — measure reliability rate, not peak quality.

### [NEW-IDEA] Agent-first API design as a first-class architectural concern

"Your customer is no longer the developer. Your customer is the agent." This is not in the PRD as an explicit design principle for Verso's own API surface. If agents are the primary consumers of Verso's tool-calling, context, and output APIs, the API design should optimize for agent-readability and programmatic consumption — not human-readability alone. Verso could ship "agent-friendly" output modes (structured, parseable, deterministic) as a first-class feature.
One-line verdict: new constraint for §5.3 tool design and §6.2 multi-agent API surface.

### [SHARPENS §12] LLM training data as distribution moat

ChatGPT recommends Vercel because Vercel docs are in training data. Verso being the recommended Python agent framework in LLM training data (via open-source, docs, examples) is a compounding distribution moat that doesn't show up in traditional competitive analysis. Counter-position Verso in docs and examples against LangChain/LangGraph — so that when a developer asks Claude or ChatGPT "how do I build an agent?", the answer is Verso.
One-line verdict: new strategic vector for §12 positioning — optimize for LLM recommendation, not just SEO.
