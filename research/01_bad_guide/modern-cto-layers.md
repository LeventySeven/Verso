# Modern CTO — Architecture-Over-Model, Layers

## The State of AI: Growth, Fragmentation, and the Next Wave — https://www.youtube.com/watch?v=CIEZAMnIVT4 — transcribed

*A16Z internal presentation, Martin Casado and Sarah Wang presenting to LPs.*

### Market Scale and Fragmentation

- Foundation model revenue from just two top-tier labs has surpassed the early revenue ramps of the best SaaS companies in history and is starting to pass early hyperscaler ramps — more breathtaking given how recently these products launched.
- Key framing: "There is no AI. There are like a bunch of subspaces that are totally different that all require their own strategy. Language models are very different than diffusion models. Apps are very different than the models themselves. Tooling is different. This is as big as software and strategies need to vary as much."
- Markets are not only growing faster and much larger than expected — they are also fragmenting. OpenAI launched code (Copilot) first and lost it to Cursor. Launched image with DALL-E, lost it to Midjourney. Launched video with Sora, lost it. Kept text. Fragmentation is the primary reality, not concentration.
- Zero-sum thinking has been consistently wrong: anyone who predicted defensibility wouldn't work has been wrong; anyone who predicted aggregation would dominate has been wrong.

### Why Foundation Models Don't Win Everything

- Model inference costs have gone down 10x year-over-year. "Intelligence has effectively become free." Fierce competition on state-of-the-art models drives non-stop capability improvement paired with continuous price decreases.
- "GPT wrapper" was a derogatory term — the conclusion now is that's not even a thing. "When someone writes software on whatever cloud, you don't call it a cloud wrapper. There's a tremendous amount of complexity in the software on top of these models and tremendous opportunity to add value."
- Where specialized apps beat foundation models: complex workflows + ton of customer data + deep integrations necessary to get last-mile value for the customer. This is where specialized AI apps are "crushing any foundation model layer company in the market."

### AI-Native vs SaaS Companies

- AI-native companies are far outpacing SaaS counterparts. New companies are blowing past 100M ARR in record time. On average (aggregated Stripe data) AI-native companies are growing faster than SaaS 2.0 generation.
- Two reasons: (1) Compelling ROI out of the box — 10x+ improvement in customer experience vs. incremental 25-50% improvement from SaaS 2.0. (2) Replacement of services budgets (not just software budgets).
- Why incumbents struggle despite distribution advantage: classic Innovators Dilemma. "AI companies aren't building an AI product. They're just building a product." Newer, mostly in-office (founders in office 6-7 days a week), and skilled at "ringing out every last drop of value from the LLM in a way that actually translates to customer value."

### Concrete ROI Data Points

- CTO dinner survey: last year — 10-15% productivity gains, all using GitHub Copilot. This year — 30-50% productivity gains on low end, one CTO reported 10x lift; 24/24 portfolio companies using Cursor; 90% of code AI-generated. "In a short 12 months, maybe not even 12 months."
- Decagon (customer support): customers slashing support costs up to 80%. Deflection rates from 30% up to 60-80%. CSAT scores doubling. "Tangible ROI, not hype."

### Defensibility

- No inherent endemic moat in the technology stack to AI other than overcoming the bootstrap problem. AI solves bootstrap (getting first 100-200 customers) because models are "magical" — but it doesn't solve retention.
- Pattern that works: startup comes in with a model, gets users, but then has to revert to traditional software to build traditional moats — two-sided marketplace, longtail integration moat, workflow moat, whatever they've figured out how to build in the past.
- Brand effects returning: "How much better is OpenAI than Anthropic? I don't know. But everyone uses it because of the brand." Brand moats from early internet are re-emerging. Companies entering massive vacuums and becoming known.

### Where Value Accrues in the Stack

- Empirical observation: "The models are being commoditized and are always under pressure. So model companies are expanding up" — building software around models (AI infrastructure, like code). Vertical AI solutions are "earning their way down the stack" — realizing they need AI infrastructure to scale.
- Palantir CTO's view: "Our theory is the value is going to accrue in two places: at the chips layer and at the AI infrastructure layer, what we would call ontology. Those two layers are going to be pretty defensible."
- Historical pattern: technology revolutions are "almost always tool revolutions, not concept revolutions. It was not Galileo who invented the telescope — he used it to discover planetary motion. The future of these technologies is determined not by the inventor of the technology, but by the people who wield the technology."

### Wipeout Patterns

- "Researcheritis" (Martin Casado coinage) — companies get so focused on research that they can't ship. Particularly dangerous when incumbents and Chinese companies are pouring money in.
- Conflicts (portfolio conflicts) matter more in AI than even in crypto — too aggressive early, conflicted yourself out of the eventual winner.
- This is not a market where a rising tide lifts all boats. "Picking actually matters more than ever."
- "Heat cannot be confused with momentum."

---

## Palantir CTO on the SaaS Apocalypse — https://www.youtube.com/watch?v=1LcH4lP9XbA — transcribed

*Shyam Sankar, CTO of Palantir, interviewed by A16Z (Katherine Boyle and Eric). Wide-ranging on defense tech, SaaS disruption, AI value accrual, and the architecture of winning.*

### The SaaS Apocalypse: Alpha vs Beta Software

- Core rubric: "What software is about beta and what software is about alpha. Software that's about beta is going to really struggle." Beta software = software that made you more similar to everyone else. Alpha software = software that expresses your competitive advantage, your strategy.
- AI (and specifically vibe coding) "allows you to make software that's specific to you. It's inherently alpha-focused. If you do it right."
- Platforms already focused on alpha are going to continue to have an advantage — AI fills their sails.
- "The stuff that's all beta is really going to struggle. And you can almost argue the beta wasn't that valuable to begin with."
- COVID example: CEOs in earnings calls didn't talk about the $5 ERP implementation that saved the supply chain "because all of them fell over like paper tigers in two weeks." What they talked about was Zoom and Teams. "That should have been a Sputnik moment for the software industry — wow, we haven't built that's valuable."
- Palantir was a COVID tailwind because they could "help customers adapt to this reality at the speed of the disruption." COVID separated wheat from chaff.
- The coming split: software that allows you to express how you're more different than other companies — "software that allows you to express your competitive advantage" — will be a premium. Beta software faces existential pressure.

### Stack Value Accrual — Palantir's Theory

- Empirical stack observation: chips → models → AI infrastructure → AI applications.
- Models are being commoditized, always under pressure → model companies expanding up, calling it a "harness" but actually building software (AI infrastructure) around the model.
- Vertical AI solutions earning their way down: "I need this actual AI infrastructure to be able to scale to my customer base and handle more use cases."
- "Our theory is always been the value is going to accrue in two places: at the chips layer and at the AI infrastructure layer — what we would call ontology. Those two layers are going to be pretty defensible."
- Ontology here = the knowledge graph / data layer that ties enterprise operations to the AI pipeline; the thing that makes intelligence actionable.

### Engineering Leadership vs Financial Engineering

- "The software that's about beta made you more similar to everyone else." The engineering divergence from the 70s: wage growth disconnected from GDP.
- Intel story: at the fork in the road, they could promote CFO or Pat Gelsinger (CTO) as CEO. They picked the CFO — "the person Wall Street would understand." Looked like it was working for 10 years until it fell off a cliff. "That was all financial engineering, not real engineering."
- "When was the last Boeing CEO to be an engineer? I think it was 2004." The pathway to CEO went through finance, not engineering.
- Andy Grove at Intel started every annual sales kickoff by telling salespeople: "Just remember, it's the engineers who create all the value. You guys just move it around."
- Elon's statement: "The pathway to the CEO is through the CTO." Sounds heretical for a generation where that's not what we were taught — but Sankar argues it's directionally correct.
- "We became very good at financial engineering and forgot about engineering."

### AI as Tool Revolution, Human Agency Paramount

- "What always irks me about how we talk about AI is as if somehow we have no human agency. AI is going to do X. No, that's not right. Humans are going to use AI to do X. There's a choice here."
- Pascal: "Every human has a god-shaped hole in their heart." The potential pathology of the labs: they've "filled that hole with AGI. There are things they assert as empirical that are actually articles of faith."
- "If you view this through a very pragmatic clear-eyed view: I'm not sure why the goal is replacing people to begin with. Isn't the goal to win? Isn't the goal to be dominant in your industry? How do I build the Iron Man suit for the sales people I do have?"
- Chinese advantage (Sankar's framing): "They have a pragmatic approach. The whole point of AI is to win. It's not AGI. It's how do I improve my productive forces." America's advantage: CEOs come to Palantir and say "I want to dominate my industry. I want to destroy my competition." Ambition sets the frame.
- Technology revolutions (repeated from video 1): "Almost to a T, every major technology revolution is a tool revolution, not a concept revolution. It was not Galileo who invented the telescope. He used it to discover planetary motion. The microscope, the power loom, the telescope, the personal computer — determined not by the inventor but by the people who wield the technology."
- "The AI doomerism — we're listening to the inventors who are incredibly smart. But just like their creations, they have their own jagged intelligence. Just because they were smart at building the model doesn't mean they're going to be right about the implications of it."
- "Those range of outcomes are exactly what's possible. And it's up to us to pick which one we want to be on."

### Heretical Builders — The Architecture of Innovation

- "Almost to a T, every single major defense innovation was a heretical idea. The institution was against it. The bureaucracy was against the process tried to kill it."
- Consolidation bred conformity: "It was the beginning of the true financialization of defense. These companies really could no longer think about growth. They thought about financial metrics, dividends, buybacks, cash flow."
- Founders need protection to thrive: "People like that do not survive in these bureaucracies on their own. Someone realized there's something special here and despite that, we tolerate him." (Referring to John Boyd, father of the F-16, protected by an unnamed three-star general.)
- Co-location of R&D and production: "SpaceX — there's a reason the R&D engineers are co-located on the production floor. What is the feedback loop and cycle time they expect to come out of that? Innovation is a consequence of productivity. If you don't make the thing, you can't innovate on how you make the thing and what the thing is."
- "The great lie of globalization is that we can do the innovation over here and have the production go over there."
- Wuxi example: "We used to think Wuxi was just some cheap contract pharmaceutical research. Now 50% of all clinical trials are being done in China."

### AI in the Military Context — Domain Knowledge Amplification

- Palantir has been building AI infrastructure for the military. Key observation: "The most compelling AI applications I'm seeing across commercial or private or public sector are being built by these green suiters."
- "AI is massively empowering to people with specific skills." The intel warrant officer who really knows their domain — 10 years ago they would have made a PowerPoint. "Now they spend two weeks, they build it themselves. Now they're having an empirical conversation about how what they built actually drives the army forward."
- Big institutions "struggle with zero to one. Everyone wants to rush to get to N as quickly as possible." Startups understand the pathing from zero to one to N; large organizations cargo cult their way there.

### Software as Malleable Weapon — Operational Data Teams

- Army concept: "How do we want to employ software as a almost like a malleable weapon system? As something that our commanders can wield to drive advancement."
- "Operational data teams" — embedded software capability inside military units, wielded by commanders.
- AI empowers people with domain expertise who previously had no way to act on their knowledge: "They were always there. 10 years ago, what would they have done though with their idea? Make a PowerPoint slide? Brief some program bureaucrat who would tell them how bad their idea is? No, they wouldn't have wasted their time. Now they spend two weeks, they build it themselves."

---

## How to Build a Self-Improving Company with AI — https://www.youtube.com/watch?v=t-G67yKAHBQ — transcribed

*Talk by a YC partner (context: YC batch, references to Gary, Diana, Pete). Conceptual and high-level. Draws on Jack Dorsey tweet thread and Diana's earlier talk.*

### The Roman Legion Problem

- Most companies today are organized like a Roman legion: nested hierarchies with consistent spans of control, named individuals passing orders down and information back up. "Human beings are the conduit for information flowing up and down."
- Jack Dorsey's tweet: the underlying assumption that hierarchically organized companies are the way to organize economic units of value — "AI basically breaks that."
- Old framing (wrong): AI = co-pilots making engineers 20% more productive, adding to workflows, shipping more software. "That is a broken way of thinking about AI. It's like taking the old way of working and adding a more powerful engine onto it."
- Correct reframe: "You can reimagine what a company is and how it acts." A solo engineer "can produce more code than an entire engineering team."

### The Self-Improving AI Loop — Architecture

Five-layer loop structure articulated explicitly:

1. **Sensor layer** — emails from customers, support tickets, code changes, subscription cancellations, product telemetry. "Sensor data to get information from the outside world."
2. **Policy layer** — decision layer: rules about what the AI can do, what it has to ask a human for permission to do, what it must log.
3. **Tool layer** — "Gary's code" — basically deterministic APIs: query my database, look at my calendar. A set of tools the AI can call.
4. **Quality gate** — evals, deterministic checks, safety filters, human review for high-risk stuff.
5. **Learning mechanism** — system interacts with real world, picks up where it doesn't work, loops back into top.

- "If you can run every single step of that without human intervention — with minimal human intervention — your system gets better and better and better while you're sleeping."

### YC Live Example: From Sidekick to Self-Improving

- Generation 1: agent with deterministic tools to query the database. "When did I last have office hours with this company?" Pretty simple.
- Generation 2: "For this company I'm doing office hours with right now, they need introductions for anyone in petrochemicals." Could query DB in different ways, use RAG, come up with five relevant founders. "This is a sidekick. This is last year's version. Making me 20 or 30% more effective."
- Generation 3 (the aha moment): put a monitoring agent on top that looked at every query every YC employee was doing — tracked when it worked and when it did not work. When it failed: "Why not? Do we need different deterministic tools? Do we need to update the skills file? Do we need a different database? A new index?" Then: write the code, put in a merge request to the YC codebase, have an agent review it, merge it, deploy it. "When a human comes the next day to ask the same query, it will now succeed."
- "That's not just AI making you 20-30% more valuable. It is the AI going through this loop to figure out how to self-improve."

### Other Self-Improving Loop Examples

- Product analytics loop: agent goes through product analytics, identifies highest friction in sales funnel, researches best practices, puts in place an A/B test, runs it for a week, picks the best version, deploys it. "Then doing that again and again and again. You just have a self-optimizing product loop."
- Customer service loop: suggestions coming in continuously. Triage agent (acting as CPO + CTO) makes judgment calls: discard, or "this is in line with our roadmap, we can do it overnight — write the code, deploy it, ship it to the customer without a human being involved."

### Making the Organization Legible to AI

- Prerequisite for self-improvement: "Make the entire organization legible to AI. You've got to record everything."
- YC implementation: partner emails now in YC database; every Slack message, every DM, every office hour recorded for last 3-4 months. "If it is recorded, it happened to the AI. If it did not get recorded, it did not happen to your intelligence."
- Diarization problem: "You cannot pump in 100,000 hours worth of recordings into a context window. You have to diarize it — basically aggregate it down, synthesize it into the important parts, give the AI breadcrumbs."
- YC user manual example: 2,000 hours of recorded office hours from last 3 months → regenerated 150-page user manual that is "dramatically better than the existing user manual." Now can update every single month. "Our user manual becomes self-improving. Every new piece of advice we give, it's compared with the existing user manual and either incorporated or thrown away."
- Then: pump user manual as context into an AI agent → "ask a superintelligent AI and get the combined wisdom of 16 YC partners in one. But only if it's legible."

### Software as Ephemeral, Context as Durable

- "Codex is now good enough to one-shot most simple internal software dashboards." All internal ops teams should sit on a layer of intelligence understanding, then create their own dashboards and workflows — but treat the software as entirely disposable.
- "I would very preciously store all the data. Treat the software as ephemeral. You can generate it, you can regenerate it. The valuable part is the comprehension inside people's heads of how the function works. The software to actually run the event you can generate for the event. You can throw it away. The models get smarter in a month or two. Throw the software away. Give it your original set of instructions and regenerate it."
- "The business context and skills are the valuable part. The software on top of it is ephemeral."

### Org Structure Implications

- "Burn tokens, not headcount." Companies getting to demo day with ~5x more revenue per employee than 18 months ago. "You're going to be constrained on token usage, not headcount, really really soon."
- Blunt metric: measuring everyone's token usage. "Obviously dumb and gameable at the extreme, but directionally correct." Who is token-maxing, who is not — good proxy for which employees you should spend time with.
- "Middle management is done. I just don't think you need middle management for this coordination problem. AI should be doing it."
- Two roles that matter: (1) ICs — builders, operators. (2) Directly responsible individuals — named humans, not committees. "You need a single person. Not a committee, not a group of people."
- "Jack Dorsey has three roles. I actually don't like the third one, so I deleted it."
- Humans at the edge of the company brain, interfacing with reality — "it's where this intelligence makes contact with reality. Human beings reach into places the models can't go yet." Novel situations, ethical considerations, high-stakes emotional moments (co-founder dispute), sales conversations.

### The Company Brain Model

- Central structure: "All of your data, all of your emails, your DMs, the skills, the know-how — that is the company brain." Humans sit around the edge interfacing with the real world.
- Key question left for the audience: "If you were building your company today, would you start it in this shape?"

---

## → Verso Implications

### Architecture Beats the Model (all three sources)

- The A16Z data is definitive: the app layer beats the model layer when it has complex workflows + customer data + deep integrations. This validates Verso's positioning — the framework that makes integrating domain context and tools first-class is more defensible than the framework that only wraps the model.
- Palantir CTO's "ontology" layer = what Verso should call its durable infrastructure layer: the knowledge graph, the memory system, the tool registry that ties enterprise operations to AI decision-making. Verso must make this a first-class concept, not an afterthought.
- "GPT wrapper" is not a real category. Verso should position itself explicitly against this framing — building real software on top of models is legitimate and high-value. Verso's job is to make that real software easy to build.

### The Three-Layer Structure for Verso

- The YC self-improving loop maps cleanly onto Verso's architecture decisions:
  1. **Sensor layer** → Verso's event ingestion / trigger system. First-class support for external events (webhooks, queues, scheduled triggers) feeding into agents. Not an afterthought.
  2. **Policy layer** → Verso's HITL + permissions model. What can the agent do autonomously; what requires approval; what must be logged. This is the durable layer that changes slowly.
  3. **Tool layer** → MCP first-class integration. Deterministic APIs. The YC speaker explicitly calls these "deterministic APIs." Verso should lean hard on this framing: tools are deterministic; the agent's intelligence is in knowing when and how to call them.
  4. **Quality gate** → Verso's evals integration, safety filters, human review triggers. Should be a first-class, configurable stage, not bolted on.
  5. **Learning mechanism** → Verso's feedback loop / trace-based improvement. The monitoring agent pattern (watch what fails, generate fixes, deploy) is the canonical self-improving pattern Verso should natively support.

### Decouple Decider from Executor

- Palantir CTO's framing: "Software as a malleable weapon system — something commanders can wield." The decider (the commander with domain knowledge) is separate from the executor (the software/AI system). Verso should make this decoupling explicit in its API — agents that decide vs. tools that execute.
- The "Iron Man suit" metaphor: AI amplifies the expert, not replaces them. Verso's design should assume a human expert in the loop at the edges, not try to eliminate them. HITL is not a concession — it's the architecture.
- The intel warrant officer example: people with domain expertise but no software background can now build. Verso's DX (developer experience) must be accessible to domain experts, not just ML engineers.

### Build for Capability 18 Months Out

- Model inference costs down 10x year-over-year. Intelligence is effectively free and getting freer. Verso should architect for a world where the bottleneck is not model capability but context assembly and tool orchestration — because that's the world 18 months from now.
- "The value is going to accrue at the chips layer and the AI infrastructure layer (ontology)." Verso is playing for the ontology/infrastructure position. Not the model. Not the UI. The connective tissue between domain knowledge and AI action.
- Stack compression: model companies expanding up into software; vertical AI companies earning down into infrastructure. Verso sits at the contested middle layer — needs both depth (infrastructure-grade) and breadth (framework-grade). The escape hatch for graphs is about depth; the simple ReAct loop is about breadth.

### Context/Memory as the Durable Asset

- YC talk makes this structural: "The business context and skills are the valuable part. The software on top of it is ephemeral." Verso's memory and context systems are the durable asset; the agent loop itself is somewhat ephemeral and should be replaceable.
- Implication for Verso API: memory backends, knowledge stores, and skill definitions should be stable, versionable, exportable — first-class citizens. The agent runner can be swapped. The memory cannot be.
- "If it is recorded, it happened to the AI. If it did not get recorded, it did not happen to your intelligence." Verso must make comprehensive trace recording + observability a core feature, not optional middleware. Every tool call, every decision, every failure must be loggable by default.

### The Monitoring Agent Pattern — Killer Verso Use Case

- The YC monitoring agent (watches queries, detects failures, generates fixes, opens PRs, deploys overnight) is the most powerful concrete pattern in all three sources. Verso should make this pattern a first-class example in documentation and potentially a built-in template.
- This pattern requires: (a) structured trace/event collection from the primary agent, (b) a secondary agent with read access to those traces, (c) tool access to code generation + version control + deployment, (d) a quality gate before deployment. All four are Verso primitives that need to compose cleanly.

### Alpha vs Beta Software — Verso's Positioning

- Palantir CTO's alpha/beta rubric is a gift for Verso's positioning: Verso is alpha-layer infrastructure — it helps teams express what is unique about their domain and workflow, not make them more similar to everyone else.
- LangGraph, CrewAI, and other frameworks can be characterized as "beta infrastructure" — they implement generic patterns that make every agent look the same. Verso's thesis is the opposite: start simple (ReAct + MCP + memory + evals), but give escape hatches for the specific complexity that makes your domain unique.
- "Platforms already focused on alpha are going to have their sails filled by AI." Frame Verso as the platform that lets teams build alpha software, not beta software.

### Middle Management Is the DAG

- "Middle management is done. AI should be doing the coordination." In agent framework terms: explicit orchestration graphs (LangGraph DAGs) are middle management — they encode who-coordinates-whom statically. Verso's simpler ReAct approach is the IC model — the agent itself coordinates dynamically.
- The escape hatch for real graph cases (durable execution, checkpoint-resume, HITL approval flows) is exactly the cases where you *do* need explicit coordination — not general coordination, but high-stakes, low-frequency decisions. This maps to Verso's thesis exactly: simple loop by default, opt-in graph for legitimate durable cases only.

### Fragmentation = Framework Opportunity

- No single model wins everything. Cursor won code, Midjourney won image, etc. The same fragmentation will happen in agent frameworks: different domains will need different tool sets, different memory patterns, different quality gates.
- Verso should be designed to fragment well — easy to assemble a domain-specific agent stack without being locked into a particular model, particular tool registry, or particular memory backend. Pluggability at every layer is a strategic requirement, not just good design.
