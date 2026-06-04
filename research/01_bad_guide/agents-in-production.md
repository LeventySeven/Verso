# Agents + Workflows in Production (Infra)

## Ship AI: Agents, Workflows, and Python — Vercel CTO Malte Ubl — https://www.youtube.com/watch?v=RXx5ZN69Z3E — transcribed

### Workflow-first framing
- Workflows (durable, resumable execution) exist in every transaction-processing system ever built, dating to 1975 batch processing — the only question is whether it was abstracted explicitly or cobbled together ad-hoc with queues + databases + cron jobs.
- Key mental model for serverless workflows: the function pauses and resumes across multiple steps; an infinite loop inside a serverless function is valid and costs nothing while idle — execution only charges during active compute.
- HITL via ephemeral webhooks: when the workflow hits an approval step, it generates a single-use URL, writes it to a database, and then `await`s that URL being called. The user approves from a queue interface two hours later; the workflow resumes as though no time passed. No polling, no state machines in application code.
- Vercel Workflow Development Kit (WDK): ships as a TypeScript SDK (open source, truly open — not open core). Uses `use workflow` directive syntax inside workflow definitions; decorators via TC39 partnership are a planned equivalent. TypeScript plugin provides IDE awareness of the workflow context automatically.
- Between steps, nothing is running — literally zero compute, which is why pause-and-resume is free. Contrasted with Fluid Compute (active CPU pricing for long-running serverless), which keeps the VM live for millisecond-latency work, not multi-step orchestration.
- Open-source strategy: "grow the pie, keep a proportional slice." The WDK ships with adapters for every runtime so it becomes the default choice regardless of hosting. Vercel monetizes the hosting without owning the standard — designed so enterprises tick the audit/portability checkbox (few will actually self-host, but they want the option).

### Agent-as-a-product vs. internal agents — a sharp distinction
- These are two categorically different things and Malte is emphatic about separating them:
  - **Agent-as-a-service product** (Vercel Agent, Codex Cloud, Cursor agent): you credit-card the service, get an agent you consume. Vercel Agent = helps build/debug applications within the Vercel ecosystem specifically because Vercel already owns runtime data, error logs, preview deployments, environment secrets. That integration context is the moat vs. generic coding agents.
  - **Internal custom agents** built by the company for its own operations: not SaaS, not installable, built for the specific workflow.

### DevOps agent: anomaly detection + triage
- Vercel's anomaly detection runs as a separate pipeline on a time-series database (not LLM-based anomaly detection — deterministic pipeline). When it fires, it kicks off an agent that:
  - Queries the observability system with a query-builder tool
  - Reads logs (structured text — comfortable LLM territory)
  - Analyzes time series data by querying specific sub-ranges
  - Examines IP addresses and error message patterns
  - Makes a binary call: escalate to on-call or defer to next-day review
- The recall/precision insight: with an agent in the loop you can tune anomaly detection to be maximally aggressive (never miss an event) because the agent absorbs the false positive cost — it takes 2 minutes to triage instead of waking a human at 3am. Agent as precision filter sitting downstream of a high-recall detector.
- Planned extension: give the agent access to source code so it can interpret error messages in context and sometimes auto-generate a PR fix. Today limited by not yet having source-code grounding.
- "We are not here to build the AI SRE that replaces that job function" — agents are superb at the right scoped problems but wandering outside that scope breaks them.

### Three internal agents (two open-sourced)
1. **Lead qualification agent**: given tools for LinkedIn, generic Google search, and a classifier for support-vs-sales requests; routes inbound contact-form submissions to correct team. Straightforward — plug in objective + disqualification criteria + hand-off rules.
2. **Abuse analysis agent**: handles inbound abuse reports. Agent does all the pre-work (visit reported site, check account age, payment history, visual similarity check to known phishing pages). Human reviews pre-work and makes final decision. Pre-work that would have been manual 20 minutes becomes a quick confirm. The agent surfaces a "this looks like a Facebook login clone" judgment before the human even opens the ticket.
3. **Data analyst agent** (open-sourced): natural language to SQL against a data warehouse. Key insight: off-the-shelf NL-to-SQL fails because the LLM doesn't know the semantic meaning of your data model — it knows column names but not business semantics. Vercel built a structured documentation format that captures data semantics alongside the schema. Agent success rate went up substantially once it had access to semantic layer, not just raw schema.

### Finding the right agent projects
- Ask people "what do you hate most about your job" — the sweet spot is: tedious + repetitive (boring = already would have been automated if it could be), but requires micro-judgment or text processing (so it wasn't trivially automatable pre-LLM). High business impact because it's a significant chunk of actual working hours.
- "Agent on every desk" program: forward-deployed Vercel engineers help large companies build their first three agents. Contract: Vercel builds agent #1 with you, is available for #2, by #3 the company is self-sufficient. Goal is empowerment, not dependency.

### Framework design philosophy
- AISDK succeeded because Vercel restrained itself from adding high-level abstractions while patterns were still unknown. "The AI app space is the absolute opposite of web frameworks — we know absolutely nothing." Contrast: in 2025 a new web framework builder knows exactly what apps will look like; AI apps are still emergent.
- "Didn't have to rewrite AISDK when everyone went from chatbots to agents" — because they stayed at a level where both use cases "looked the same stuff people would do on top."
- Agent = tool loop with a streaming wrapper. AISDK's `streamText` + tools handles it. Competitors led with an agent abstraction on day one; AISDK waited until patterns solidified. "Half of those other frameworks are built on top of AISDK anyway."
- Model control: fully endorses "let the model take control, give it tools, get emergent behavior" — but notes that model labs don't care about embedding this inside an application. Framework builder's job is the embedding layer.

### Python first-class on Vercel
- Vercel is actively investing in Python: zero-config support for Flask and FastAPI (throw code over the fence, it runs). Python SDK for Vercel's management API shipped. Fluid Compute program supports Python with active-CPU pricing.
- TypeScript is now the #1 language on GitHub (just passed in 2025), but Malte explicitly doesn't have a "bet on JavaScript" opinion — both communities are large and relevant. "When you're a serious AI cloud you have to support Python."
- Practically: Vercel runs VMs — supporting a new language is technically trivial but takes significant DX investment to make it feel native. PHP/Ruby planned eventually but takes time.

### Security for AI-generated code
- Emerging concern: apps where the developer "doesn't know what they're doing" + AI also may not. Auth should be extracted out of the app layer entirely (Vercel handles it at the platform level), data access controls similarly extracted. Minimum-security floor independent of app quality. Working with large enterprises to make this production-ready.

---

## Block CTO Dhanji Prasanna: Building the AI-First Enterprise with Goose — https://www.youtube.com/watch?v=64J2lHxP0ok — transcribed

### Context: Block's AI transformation
- Block has two main pillars: Square (merchant/seller services) and Cash App (consumer financial app), plus Tidal (music) and Bitcoin-focused open-source initiatives (BitKey hardware wallet, Rig mining hardware).
- Dhanji's AI manifesto (email to Jack): "We need to invest in AI centrally and transform our whole company." Jack flew to Sydney for two days to align. Result: centralized functional org structure replacing the previous GM silo structure (Square, Cash App, Tidal each had separate engineering under a GM). Centralization unlocked platform teams that were previously isolated from product teams.
- "AI-first teams" are now producing code that is "pretty much all entirely vibecoded" via Goose. Legacy codebases at scale still require significant manual work due to context-window limitations and LLM struggles with proprietary frameworks.

### Goose: architecture and design philosophy
- Goose = general-purpose AI agent, CLI + UI (both surfaces backed by same MCP server connections). Built by Brad Axen, one engineer, then scaled to a team of 6-7. Started as a back-closet project; Dhanji ring-fenced it when he became CTO.
- Architecture: pluggable LLM provider system — any LLM capable of tool calling. Core mental model: "LLM is a brain in a jar — Goose gives it arms and legs to act in the real world on real digital systems."
- Agent loop: lets the loop run "as far as it can." If Goose hits obstacles, it backs up and tries another approach. Core tool-calling loop finishes on average 2-3 minutes per turn. "A lot of AI agents learned from us over time" on this approach.
- Tool calling via MCP: Goose was one of the earliest adopters of MCP. Explicitly helped shape MCP with Anthropic. Block treats every enterprise capability (creating issues, opening PRs, running Snowflake queries, taking Square payments, moving bitcoin) as an MCP-exposed capability.
- **Tool shim**: open-source LLMs don't have native tool calling — they just generate text. Block built a "tool shim" layer that adapts open-source LLMs (Llama, Qwen, Deepseek) to use MCP despite lacking native tool-calling support. This is how privacy-conscious employees can run entirely local with no tokens leaving their laptop.
- **Recipes**: if a Goose workflow is successful, the user can "bake" it into a script/recipe and share it with teammates. This is the team-propagation mechanism for discovered workflows — no central engineering needed to codify a new capability.
- Non-engineers are using it: sales staff, finance staff building their own dashboards, reports, and interactive tools. "We never expected our sales guy to be writing software dashboards for themselves." This is in part because non-technical users can use the desktop UI which has identical MCP access to the CLI.

### Safety model (laddered autonomy)
- Default "human in the loop for everything" mode: Goose presents every destructive action for approval before executing.
- Advanced "fully autonomous" mode: user opts in, Goose still voluntarily warns before destructive actions even when not required.
- Interrupt-at-any-time: you can break into a running agent and redirect it — "take a different path."
- Blast radius bounded by user identity: Goose acts *as* the user, not as a super-user. It can only do what that user's ACLs permit. Finance data inaccessible to sales user's Goose instance.

### Headless Goose: CI/CD agent
- Goose runs in Block's CI pipeline as "Headless Goose." Every time InfoSec files a vulnerability ticket, Headless Goose automatically attempts to fix the vulnerability and opens a PR. Humans must review and approve before anything enters production. No autonomous production changes.
- Demonstrates the pattern: agent does the expensive cognitive pre-work, human rubber-stamps the result rather than starting from scratch.

### Model strategy
- Gateway of 10-20 supported models. Most coding work: Claude family preferred, GPT-5 increasingly competitive.
- Privacy-sensitive users: Qwen, Deepseek (fully local, no tokens leave laptop).
- Block does NOT train large LLMs. Does train: SLMs for customer service and risk, and is researching a speech-to-speech model (will be open-sourced with all findings published).
- Philosophy: "My preference would be for all models to be open weights." The competitive future may not be "is open model X as good as closed model Y" but "can you run 500 instances of open model X for the cost of one large closed model call?" — swarm intelligence thesis.

### Swarm intelligence thesis
- Current Goose: one agent, 2-3 minute tool loop, coding on a single codebase. This is the current ceiling.
- Future belief: "50 or 100 instances of Goose working together could build applications the scale and complexity of Cash App." The question of whether open models can challenge frontier closed models becomes a question of whether swarms of cheap models can exceed single expensive calls.
- Architecture hypothesis: hierarchical swarm — large capable model handles planning and reintegration, small/cheap models execute atomic units ("nanoservices"). "Can an infinite number of ants build a spaceship?" — framed as an active research question, not a solved problem.

### Measured impact
- Block's primary metric: **manual hours saved by Goose** — tracked weekly, started at 0%, target is 25% of all manual hours saved by end of year. Currently on track.
- Per-engineer: most engaged Goose users report 8-10 hours/week saved even in complex legacy codebases (30-40% of code they produce). AI-first teams (new greenfield work): practically 100% Goose-written code.
- LLM limitations in enterprise: excellent at general things, struggles with domain-specific deep expertise and with proprietary APIs/frameworks not in training data. "Identifying what the strengths of the LLM are and how you apply them to the enterprise is what unlocks value."
- Race conditions, multi-system topology coordination, higher-level architectural design: still require human engineers. "We definitely need people in the loop for that."

### Capabilities + interfaces framework
- Jack Dorsey's framing: everything is a capability, everything is an interface. The AI agent is the middleware between capabilities and interfaces.
- Block treats Square payments, Cash App money movement, Snowflake queries, GitHub PRs, Jira tickets as the same class of thing: MCP-exposed capabilities. The agent layer orchestrates across them.
- Square AI (public beta): Goose-like bot for merchants — natural language queries over their own financial data. Real example: a wine bar asked "if we close an hour early on Thursdays, how much do we lose?" — turns out waiters made most of their tips in that last hour; they decided not to close early.

---

## Interrupt 2025 Keynote (LangChain) — https://www.youtube.com/watch?v=DrygcOI-kG8 — transcribed

### LangChain origin and thesis
- LangChain launched as a nights-and-weekends open-source project ~2 years before this talk; first launched one month before ChatGPT. Core observation from day 1: easy to prototype, hard to get to production. That delta is where LangChain built a company.
- Original pitch deck mission: "Make intelligent agents ubiquitous." Belief that LLMs need significant tooling around them to be practically useful.
- LangChain Python downloads: 70 million in the most recent single month (not aggregate). Surpassed OpenAI SDK in Python downloads — attributed to developers wanting model optionality and using LangChain as the abstraction layer.

### Three present-day beliefs

**Belief 1: Agents will rely on many different models**
- Models have distinct strengths: some are expensive but reason long (o3-class), some are fast + cheap + task-specific, some excel at writing vs. reasoning. Agents increasingly route to different models at different steps.
- LangChain's evolution: stripped away a lot of the original monolith, re-focused the core package on integrations (language model providers especially). This focus on integrations + model optionality is the stated reason for growth.

**Belief 2: Reliable agents start with the right context**
- The prompt passed to an LLM isn't a single string — it's assembled from: system message, user input, tool outputs, retrieval results, conversation history. Controlling exactly what goes into that context determines what comes out.
- LangGraph: "extremely low-level, unopinionated framework for building agents." No hidden prompts, no hidden cognitive architectures. You construct whatever agent flow you want, assemble context however you want, pass it to the LLM. Supreme controllability is the explicit selling point.
- On top of that primitive, LangGraph adds: streaming, HITL support, short-term memory, long-term memory — all as low-level primitives you compose yourself (not as opinionated behaviors).
- Recommendation: all complex agent orchestration should be built on LangGraph.

**Belief 3: Building agents is a team sport**
- The "agent engineer" persona combines: prompting skills, software engineering, product sense, and ML/evals knowledge. No one has all four at the start. So agent building is collaborative.
- LangSmith: the team platform — observability (trace inspection, input/output at every step), evaluations (offline + online datasets, metrics), prompt management (hub + playground). All in one place so prompt engineers, ML practitioners, and product people can collaborate.
- AI observability ≠ traditional observability: unstructured + multimodal payloads, different user persona (agent engineer not SRE), requires ML + product + prompt context all in one view.

### Three future beliefs

**Future belief 1: AI observability is fundamentally different**
- LangSmith launching new metrics: tool run counts, tool latencies, tool error rates; trajectory observability (which decision paths agents take, latency/errors per path). Available now in LangSmith from live traces.

**Future belief 2: Everyone will build agents**
- LangGraph pre-builts: canonical agent architectures (single agent, swarms, supervisor agents) as starting templates. Lowers barrier for engineers without AI background.
- LangGraph Studio V2: facelift, no longer Mac-only desktop app (browser-based). New capabilities: view all LLM calls in a playground inside the studio, build datasets, edit prompts inline, pull production traces from LangSmith into local Studio for hot-reload debugging of production issues.
- Open Agent Platform: open-source no-code agent builder powered by LangGraph Platform. Includes: tool server (MCP), RAG-as-a-service, agent registry, agent templates. For enterprise users who can't get engineering time.

**Future belief 3: Deployment of agents is the next hurdle**
- Agents are structurally different from web apps:
  - **Long-running**: deep research agents run 10 minutes; some run 1 hour or 12 hours. Not request-response.
  - **Bursty**: background job agents kicked off hundreds or thousands at a time.
  - **Flaky in novel ways**: LLM calls fail; more importantly, LLMs do unexpected things so HITL is necessary, which requires persistent statefulness.
- Prediction: agents will become more long-running, more bursty, and more stateful over time.
- LangGraph Platform (GA as of this talk): 30 API endpoints covering streaming, HITL, memory. Horizontal scaling for burstiness. Designed for long-running workloads. Agents deployed here can be exposed as MCP servers. Control plane for discovering and sharing agents across an org. Deployment options: cloud SaaS, hybrid, fully self-hosted.

---

## → Verso Implications

### On the workflow/agent split
- **The split is real and load-bearing.** Malte Ubl is emphatic: agent-as-a-product and internal automation agents are categorically different things. Verso should make this distinction explicit in its API surface and documentation. A clean ReAct agent loop (the "agent" layer) and a durable workflow engine (the "workflow" layer) are separate concerns that compose, not merge. Don't conflate them.
- **The durable execution escape hatch is not optional — it is the production requirement.** All three sources converge: long-running agents (10 min to 12 hrs — LangChain), pause-and-resume for HITL (Malte's ephemeral webhook pattern), headless batch jobs (Goose in CI). Verso's opt-in graph/durable layer needs to handle all three. Frame it as "the escape hatch for when the ReAct loop isn't enough."

### On the agent loop design
- **Block's architecture is the clearest production reference.** Goose's loop: let it run as far as it can; back up and retry on obstacle; interrupt-and-redirect is first-class. Average turn time 2-3 minutes. Verso should design its default loop with explicit interrupt/redirect capability as a first-class API, not an afterthought. This is what separates a production agent from a demo.
- **The tool shim problem is real at scale.** Block's "tool shim" to adapt non-tool-calling models to MCP is a solved internal problem but a genuine gap in the ecosystem. Verso should offer a provider abstraction that normalizes tool-call semantics across models with and without native tool calling — this unlocks OSS models as a first-class choice.
- **Autonomy should be laddered, not binary.** Block's safety model (full HITL → progressive autonomy → fully autonomous, with voluntary warnings even in autonomous mode) is a design Verso should bake into its agent runtime as a first-class `safety_level` or `confirmation_policy` parameter rather than leaving it to each application to build.

### On context and prompting
- **LangChain's "right context" belief directly validates Verso's context-first architecture.** The prompt is not a string — it's assembled from system message + user input + tool outputs + retrieval + history. Verso's context assembly pipeline should be an explicit, inspectable, composable object — not a hidden string concatenation. Give users control over what goes in at each step.
- **No hidden cognitive architectures.** LangGraph's explicit selling point — zero hidden prompts, zero hidden routing — should be Verso's too. The "clean ReAct loop" thesis means Verso's internals must be fully transparent and overridable, not magic.

### On Python-first
- **Python is non-negotiable for AI infra.** Malte: "When you're a serious AI cloud you have to support Python." Block uses Python extensively for agent infrastructure. LangChain's 70M/month downloads are Python. Verso must be Python-first, not Python-also. Any TypeScript/multi-language features are secondary.

### On evals as first-class
- LangChain frames evals as the "machine learning" component of agent engineering — how you capture non-determinism over time and measure improvement. LangSmith is purpose-built for this. Verso should treat evals as a runtime primitive, not an external concern — built-in dataset management, trace capture, eval runner in the core SDK.

### On observability
- **Agent observability ≠ traditional observability.** LangChain is explicit about this. Verso's observability must expose: tool run counts + latencies + errors (not just endpoint latencies), trajectory/path analytics (which branches agents take), unstructured LLM payload inspection. The user persona is the "agent engineer," not the SRE. Design the UI/API accordingly.
- **Production trace pull-down for local debugging is a killer feature.** LangGraph Studio V2's ability to pull a production trace into local hot-reload Studio is exactly the debugging workflow that distinguishes frameworks that ship from frameworks that prototype. Verso should plan for this pattern.

### On the "right problems" discipline
- Malte: "Agents are both extraordinarily effective and still very ineffective — you have to find the right problems." Framework that asks users "what do you hate most about your job" to find agent projects. Verso's onboarding story and docs should teach this — not "here's how to build an agent" but "here's how to find the workflow worth automating."
- Verso should not position itself as "build any agent for any use case" — position as "the right tool for the tedious-but-judgment-requiring workflows that are now automatable."

### On the capabilities + interfaces model
- Block's Jack Dorsey framing — everything is a capability, the agent is middleware, the interface is what users see — is the right mental model for how Verso agents fit into enterprise products. Verso's MCP-first tool architecture directly aligns: MCP exposes capabilities, Verso orchestrates across them, the application (UI/voice/API) is the interface layer. Verso should use this framing explicitly.

### On open-source strategy
- Vercel's model (truly open + grow the pie + monetize hosting proportionally) and Block's model (open-source everything including Goose because "community of 30,000 engineers > 3,000 internal engineers") both point toward Verso being genuinely open-source with a clear path to hosted/cloud monetization. Open core risks user trust for production-critical infrastructure. True open + premium hosting is the right posture.

### On the swarm/multi-agent future
- Block's swarm intelligence thesis (50-100 Goose instances, hierarchical with large planner + small executors) is a concrete future direction. Verso's graph/durable layer should be designed to support multi-agent topologies, not just single-agent workflows. The "opt-in escape hatch" should handle: hierarchical supervisor+worker, parallel fan-out with merge, and sequential pipeline — these are the three patterns Block and LangChain both independently identify as real production needs.
