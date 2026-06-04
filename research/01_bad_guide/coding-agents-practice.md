# Coding agents — real engineering practice

## Inside Devin: The AI Engineer — https://www.youtube.com/watch?v=gI0ZNhA0rvE — transcribed

**Speaker:** Scott Wu, co-founder and CEO of Cognition (makers of Devin). Lenny's Podcast interview, ~60 minutes.

### What Devin is and is not

- Devin is a fully **autonomous, asynchronous** software engineer. The UX model is not a chat assistant — it is a remote colleague you tag in Slack, Linear, or GitHub. You hand off a task and come back later; Devin runs end-to-end and opens a PR.
- It operates with: Slack integration, GitHub integration, Linear integration, an interactive planning phase, the ability to run its own CI/lint/tests in a VM, and a PR review/feedback loop.
- The key insight from a year of use: the product is 50% capability improvements, 50% product interface — learning how humans hand off tasks and get back results is as hard as the underlying AI.
- Positioning: "give Devon tasks, not problems" — well-defined, verifiable tasks with a fast feedback loop (e.g., front-end feature request, bug fix, adding tests, migration) are the sweet spot. Vague architecture rethinks are not.

### How Cognition uses Devin to build Devin

- Engineering team is 15 people.
- Every engineer runs **up to 5 Devins concurrently** in an async workflow. Plan your 5 things for the day, kick off 5 Devin sessions, check back and steer as needed.
- As of interview: **~25% of all PRs merged in the Devin codebase are opened by Devin**. Expectation: >50% by end of year.
- Mental model: not manager–report, more like "brick layer to architect" — engineers spend time on problem definition, architecture, design decisions, and high-level steering, not boilerplate implementation.
- The day-to-day loop: review issues/bugs/features, hand off clear tasks to Devin instances, review PRs, merge or give feedback. Devin can autonomously do 80–90% of a task; the 10–20% requiring precision human judgment is where you step in.
- Devin can self-recurse: through the API, Devin can spin up sub-Devins for parallel work streams. Not default-enabled as of recording but used internally.

### Codebase memory and the "Devin wiki"

- When Devin indexes a codebase it builds an **internal representation (the "wiki")** — structured diagrams, component breakdowns, relationships. This persists and grows across sessions.
- The wiki is human-readable too: engineers use it to onboard new hires, understand unfamiliar repos, and scope tasks before starting a session.
- Context management operates like a good senior engineer: high-level abstraction first, then zoom into specific components as needed. Not every line of every file is loaded at once.
- Key moat claim: every session teaches Devin more about the codebase and the team's conventions. The first session is generic; after months it encodes your patterns and idioms at near-staff-engineer level.

### Architecture and technical decisions

- The founding bet (late 2023): RL with automated feedback loops would be the next capability leap. Code was the natural domain because "you can run the code and that IS the automated feedback that feeds RL."
- Hot take from Scott: "In terms of base intelligence we're basically already there. The hard problem is teaching the model all the idiosyncrasies of real-world engineering — how to use Datadog, how to diagnose this class of error, how to make a GitHub PR properly."
- No single base model update was a "night and day" unlock for Devin — improvement has been a continuous curve across all model releases. Cognition works directly with research teams at foundation labs.
- The VM setup matters critically: Devin needs its own isolated VM with linter, CI, test runner, and browser already configured to test its own code. Without this, quality degrades sharply.
- Async > sync: the 200–500–1000% productivity gains come from running tasks asynchronously in parallel, not from running one task faster.

### Jagged intelligence and task scoping

- Term used: "jagged intelligence" — Devin is far better than a human at some things (retrieval across a million-line codebase, never forgetting a convention, tireless implementation of boilerplate), far worse at others (novel architecture decisions, detecting subtle behavioral regressions without tests, open-ended creative problem-solving).
- A year ago: "high school CS student." Then college intern. Now junior engineer — but these are rough analogies; the jagged profile doesn't map cleanly onto seniority.
- Key UX learning: never give Devin a "problem" (e.g., "rearchitect the auth system"). Give it "tasks" (e.g., "add an idempotency key to the payments endpoint"). Tasks have clear success criteria and are easy to verify.

### Agent adoption pattern

- Grassroots works: one or two early adopters set Devin up, teach it the repos, CI, lint scripts, give it initial easy tasks. Others see PRs flowing in and onboard naturally. By the time they join, Devin already knows the codebase.
- Setup investment required: teach Devin how to run tests, how to lint, what the CI system looks like. This upfront work pays off across all subsequent tasks.

### The engineer-as-architect shift

- Jevons paradox applied to software: cost of coding drops → total amount of code the world wants increases → more engineers needed, not fewer.
- The 90% of engineering time that is currently "Kubernetes error, bug report, migration, dependency upgrade" gets delegated to Devin. The 10% that is genuinely architecture and design becomes 100% of the human's job.
- Human engineers need to get better at: problem definition, precise specification, architecture reasoning, system-level tradeoffs, and understanding abstractions deeply enough to know when the AI is wrong.

---

## Engineering practices that make coding agents work — https://www.youtube.com/watch?v=owmJyKVu5f8 — transcribed

**Speaker:** Simon Willison (creator of Django, creator of Datasette, prolific AI blogger). Panel discussion with Eric at Static, ~35 minutes.

### Simon's personal coding agent workflow

- Writes more code on his phone than on his laptop now. Uses Claude Code for the Web (container running in Anthropic's infra) for essentially all coding.
- Live demo during the pre-interview chat: prompted Claude Opus 4.6 with "run a benchmark then find the best options for making it faster" on a WebAssembly engine written in Python. Got a 49% speedup on Fibonacci. Prompt was two sentences.
- Stages of AI adoption as a programmer:
  1. ChatGPT for questions / occasional help
  2. Coding agents that write bits of code for you
  3. The agent writes more code than you do (inflection point for Simon ~4-6 months before recording)
  4. You don't write any code at all — you direct, review, and merge
  5. (Cutting-edge, 3 weeks old at time of recording) You don't even read the code — agents prove to you via tests and conformance suites that what they wrote works
- StrongDM example: "nobody writes code, nobody reads code" — works only if you invest in robust mechanisms for agents to prove their output is correct (tests, behavioral verification, conformance suites).

### TDD as the #1 practice for coding agents

- Red-green TDD is the single most important practice for getting reliable output from coding agents.
- Simon hated TDD throughout his career — found it tedious, slowing. With agents it is effectively free: the agent spins for a few minutes running failing tests, you don't care.
- **The rule:** Start every coding session with "here's how to run the tests (normally `uv run pytest`). Use red-green TDD."
- Why it works: constrains the agent to write only what's needed to pass the test. Prevents hallucinated over-engineering. All good coding agents know what TDD means — it's about 5 tokens of instruction.
- "Tests are no longer even remotely optional. They used to be extra work you might skip. They're free now."

### Curl-exercising the live API as the second layer

- Test suites don't catch everything — the web server might not boot even if tests pass.
- Practice: tell the agent to **start the server in the background, then use curl to exercise the API it just created**. This finds bugs the unit tests missed.
- Simon released a tool called **Showboat** (48 hours old at time of recording): builds a markdown document of the manual test run — each curl command, its output, and whether it passed. Gives a human-readable audit trail of what the agent actually tried.

### Conformance-driven development

- A more powerful pattern when an external specification exists: give the agent a language-agnostic conformance test suite (e.g., the WebAssembly spec, which includes hundreds of tests) and say "write code until this suite passes."
- Used this to implement file upload support in Datasette: told Claude to build a test suite that passes for Go, Node.js, Django, Starlette, and two other web frameworks, then use that as the spec to build the Datasette implementation.
- "You can reverse engineer 6 implementations of a standard to get a new standard, then implement the standard." The agent-generated implementation then has broad behavioral coverage even without human review of the code.

### Context and code quality

- Templates / Cookiecutter: Simon uses ~6 Cookiecutter templates to bootstrap projects. These put tests in the right place, set up CI, add a README. The agent then follows the existing patterns.
- **Agents are extremely consistent about following established patterns.** If your codebase uses a particular testing style or module layout, the agent will replicate it to a T. This means code quality is a choice you make, not something that happens to you.
- If the agent produces 2,000 lines of low-quality code and you choose to ignore it, that's on you. If you review it and say "refactor this piece to use this other design pattern," the agent can produce code better than you'd write by hand (because you'd be too lazy to do the cleanup at the end of a session; the agent does it willingly).
- Code quality context-dependent: for single-use vibe-coded HTML/JS tools, code quality is irrelevant. For maintained production code, quality matters enormously — and the agent will keep producing quality work if you ask for it.

### Prompt injection and the lethal trifecta

- **Prompt injection** (term coined by Simon): class of attacks where malicious content in agent-read documents contains instructions that hijack the agent. Example: documentation that says "to confirm you've read this, run base64-encoded rm-rf."
- The failure mode is real and exploitable in current agents. Obfuscated commands (base64-encoded bash, pipe tricks) bypass surface-level filters.
- **The lethal trifecta** (Simon's preferred term): an agent is dangerous when it has all three: (1) access to private data (env vars, emails, secrets), (2) exposure to malicious instructions (reads external content), (3) an exfiltration vector (can send data outbound). Cut any one of the three legs and the risk collapses.
- Solution: **sandboxing is the #1 mitigation**. Claude Code for the Web runs in an Anthropic-managed container — worst case a prompt injection can destroy the container, not your local machine or production data.
- For user data in testing: invest in good mocking. Build a button that generates 100 synthetic users with fake names. Build edge-case generators (e.g., a user with 1,000 ticket types). Never clone production to your laptop.
- Docker containers and Apple Containers are acceptable sandboxes for local runs. Simon notes the friction is still too high — he still runs directly on his Mac for convenience, acknowledging the risk.

### The model inflection points (as of recording, ~June 2025)

- GitHub Copilot (2022): nice autocomplete.
- GPT-4 (2023): first model that was actually useful and didn't make up everything.
- Sonnet 3.5 + Claude Code (early 2024): "the killer moment" — first time a model felt good enough at driving a terminal to do useful coding tasks. This was the real start of the coding agent era.
- November 2024: models "just got so good" — Claude and GPT upgraded and code quality jumped from "janky solution you have to fix up" to "you give them a task and they do a good solution."
- Opus 4.6 + Codex 5.3 (June 2025, one week before recording): "I'm one-shotting basically everything now." Two-sentence prompts, don't even need to ask if it's going to work. This is the reliability threshold that enables the no-read-code workflow.
- Current challenge: "I don't know what the boundary challenges are right now." Model providers rarely ship clear "this thing that failed before now works" changelog. Engineers need to periodically re-try things that failed before.

### Human cost of running multiple agents

- Running 3–4 agents concurrently is cognitively exhausting — you have to "fire on all cylinders" to keep them all busy and productive.
- "After 2–3 hours of that I'm done for the day." This might be what prevents the "one engineer, 1,000 projects" scenario — human bandwidth for directing agents is the actual constraint.
- Engineers should currently be expanding their language repertoire. Simon shipped 3 Go projects in 2 weeks despite not being a fluent Go programmer. You read the output well enough to sanity-check it + TDD loop confirms it works.

---

## The Agent Development Lifecycle: Build, Test, Deploy, Monitor — https://www.youtube.com/watch?v=jWy39wavbjY — transcribed

**Speakers:** Harrison Chase (CEO, LangChain) and Ankush Gola (CTO, LangChain). Interrupt conference keynote, ~30–35 minutes.

### Why building agents is different from building software

- The core difference: both input space and output space are enormous and poorly bounded.
  - Inputs are natural language (infinite dimensions, can include images, audio, video).
  - LLMs are nondeterministic and extremely sensitive to small prompt changes.
  - Result: agent systems are very hard to predict before you actually launch and put them in front of users.
- Teams that ship agents reliably have converged on a common pattern: **ship early, iterate quickly**. This produces a new lifecycle — the Agent Development Lifecycle (ADLC) — that runs parallel to but is distinct from the traditional SDLC.

### The core agent loop (LangChain's view)

- The fundamental unit, unchanged from original AgentExecutor to today: **LLM in a loop calling tools** until it decides it's done.
- All the complexity — planning, memory, sub-agents, HITL, checkpointing — wraps around this core loop. But the loop itself is simple.
- LangGraph was built when application graphs became too complex for chains. Now "deep agents" is the current evolution.

### Deep agents: the agent harness architecture

Deep agents is LangChain's agent harness. A harness supercharges the core LLM-in-loop by adding:

1. **Execution environment** — the harness needs a place to run:
   - Full sandbox: file system, code execution, shell, docker. Expensive to spin up per agent.
   - Virtual file system: a database exposed to the agent as if it's a file system. LLMs are good at reading/writing files so you can simulate a real FS. Lightweight.
   - Code interpreter (new in 0.6): uses QuickJS (JavaScript runtime) as a middle ground. Agent can write and execute JS, manipulate data files, call tools programmatically — but cannot run Docker or arbitrary OS commands. Key benefit: multi-tenant-friendly, no per-agent sandbox spinup.
2. **Built-in context management** (skills and memory):
   - Summarization: when conversation gets too long, automatically summarize (short-term memory compression).
   - Context offloading: logic for handling very long tool call outputs.
   - Prompt caching: automatically cache the stable part of the prompt prefix for speed and cost.
3. **Steering / HITL controls** — long-horizon agents are not fully autonomous. Harness provides robust human-in-the-loop checkpoints.
4. **Delegation** — harness can kick off sub-agents (planning agents, task-specific sub-agents) and coordinate their results.

### Build phase: what's needed

- Agent needs: instruction (agent.md / CLAUDE.md style files, skills files), tools (via MCP), an execution environment, and memory.
- Context has evolved from simple prompts → AGENT.md files → skills files → LLM wikis (Karpathy-style condensed markdown knowledge bases). LangChain's "context hub" stores, versions, and tags all of this.
- Memory should be open (not locked to a model or framework). Memory = accumulated context = early form of agent skill.
- Open source model support (deep agents 0.6): native GLM-5, DeepSeek, Neotron models; inference partners Fireworks, Base10, Nvidia. Cost of frontier models keeps rising, open models are getting competitive.
- "Deep agents code" released as open-source example of building a coding agent on top of the harness with open source models.

### Test phase: evaluations

- Agents require more iteration than traditional software before they're production-ready.
- Eval setup:
  1. Build a dataset of inputs (seed from real user data or synthetic).
  2. Define evaluation criteria / scoring functions (correctness, hallucination detection, task success rate).
  3. Run agent over dataset, score results, create experiments.
  4. Use experiments to hill-climb (improve) or gate (don't regress).
- Online evals (LLM-as-judge or code-based scoring running over production traces in real-time) complement offline eval datasets.
- LangSmith Engine (launched at conference): an ambient, proactive agent that sits on top of your traces, runs on a schedule, detects issues, assigns priority, backs claims with evidence traces, and suggests concrete resolution actions (code changes, prompt edits, new eval data points, new online evals). Acts at all ADLC stages.

### Deploy phase: what changes going from local to production

The problems that emerge only in production:
- **Multi-user:** environment variables and memory must become user-scoped, not global.
- **Auth:** access control.
- **Durability:** the agent must survive server restarts; tasks can run for hours. This is why durable execution (checkpoint-resume) is critical for long-horizon agents.
- LangSmith deployments: 30+ API endpoints for streaming, HITL, auth, etc. Served 100M+ agent runs. Customers include Workday, Cisco, Etsy, Podium, ByteDance.
- **Sandbox-as-infrastructure**: LangSmith Sandboxes (now GA):
  - Spin up in <1 second.
  - Persistent across interactions (survive between agent turns).
  - Supports snapshots and forks (for branching / parallel exploration).
  - **Auth proxy pattern**: to give an agent access to a third-party API that requires an API key without exposing the key inside the sandbox (which could be leaked via prompt injection): an auth proxy sits *outside* the sandbox, intercepts traffic, and inserts the credential. The agent never sees the key.
  - Framework-agnostic: usable with or without deep agents, for dev testing, RL training, or production.

### Monitor phase: observability architecture

- Every agent trace is a nested tree of spans (input → LLM call → tool call → sub-agent call → output), deeply nested, potentially thousands of intermediate steps.
- LangSmith trace payload sizes: P50 grew from 6 KB to 37 KB over 2 years. P99 grew from 364 KB to 12 MB. One customer sent 50 TB of trace data in a single day.
- Weekly trace volume for a maturing customer: from small during dev → 150M traces/week in production.
- One internal deep-agents trace captured 8.1 million tokens.
- Traditional databases are not built for this: slow queries, ingestion bottlenecks, rising costs at scale.
- **SmithDB**: purpose-built database for agent observability, announced at conference.
  - Written in Rust.
  - Backed by object storage (cheap, infinite scale, compute-storage separation, self-host-friendly for data residency).
  - Cluster manager provides load balancing with sticky routing (important for cache utilization and batching for ingestion).
  - Ingestion: raw data batched → durably written to object storage → registered in Postgres-backed metastore.
  - Query: figure out which files to scan, download from object storage, scan; use SSD cache + memory buffer for recent/leading-edge data.
  - Compaction service reshapes files for more optimal query plans.
  - Key optimizations:
    - **Random access** for drilling into individual traces/steps (not just aggregate queries).
    - **Full text search** across trace payloads: custom inverted index layout on object storage.
    - **Thread queries**: multi-turn conversations are first-class; threads backed by SmithDB with snappy drill-down.
    - **Distributed span merging**: spans arrive out of order over hours (start event hours before end event) — SmithDB merges them efficiently at query and compaction time.
    - **Top-K optimization**: naive fan-out scans all files; SmithDB uses time-window-based execution plans to avoid expensive object storage fan-outs for ORDER BY / LIMIT queries.
  - Built on Apache DataFusion (Rust query engine) + Vortex (extensible file format with custom encodings/chunking per column).
  - Performance: 6x–15x faster than previous infrastructure on key observability workloads (Clay, Vanta as early adopters confirm).
  - "Langsmith performance is not only important for human UX but also agent UX. Increasingly, agents are the users of LangSmith too. Slow tools become an Amdahl's law bottleneck for multi-agent systems."

### Governance layer

- At scale (10+ or 100+ agents), governance becomes critical:
  - **Cost**: who is spending what? Per-user, per-agent cost attribution. Surprise bills prevention.
  - **Data exposure**: agents should not have access to every data source. PII and secrets detection and guardrails.
- LangSmith LLM Gateway (beta): sits between agents and their LLM calls. Set spend limits, full spend visibility, PII/secrets guardrails. Integrates with major coding agents and all LLM providers. All calls automatically traced to LangSmith.

### The full ADLC as a closed loop

Build → Test → Deploy → Monitor → (LangSmith Engine detects issues) → back to Build. Traces sit at the center of the loop — they are the connective tissue that makes the iteration flywheel spin. SmithDB is the database that makes traces fast enough for the loop to be tight.

---

## → Verso implications

### Agent loop design

- **Keep the core loop simple (confirmed):** LangChain's CTO explicitly says the agent primitive — LLM in loop calling tools until done — has not fundamentally changed. All the complexity is the *harness* around it. Verso should keep the loop itself simple and composable; complexity belongs in optional harness features.
- **Async execution is a first-class requirement:** Devin's entire UX is built on async handoff (kick off, come back later). Verso's API must support fire-and-forget with later polling/streaming of results, not just synchronous blocking calls. The sync path is a convenience wrapper over async.
- **HITL is not optional for production coding agents:** Both Devin (interactive planning phase, mid-task steering, PR review) and LangChain (HITL controls as a harness feature) treat human-in-the-loop as essential, not an afterthought. Verso should have first-class HITL checkpoints: "pause here and wait for human input before proceeding."
- **Sub-agent / delegation is the scaling primitive:** Devin's architecture allows Devin to spawn sub-Devins (parallelized work streams sharing context). LangChain's harness explicitly supports delegation. Verso should have a clean delegation API — an agent spawning a child agent with a shared or forked context window.

### Execution environment / sandbox

- **Sandboxes are the #1 security control:** Simon Willison, Scott Wu, and Harrison Chase all independently conclude that sandbox isolation is the critical security layer for coding agents. Verso should have sandbox-first design — the execution environment is a first-class primitive, not an afterthought.
- **Auth proxy pattern is load-bearing:** the LangSmith auth proxy (outside the sandbox, intercepts traffic, inserts credentials) solves the prompt-injection-vs-API-keys problem cleanly. Verso should implement this pattern — API keys never visible to the agent's execution context.
- **The execution environment spectrum is: virtual FS → code interpreter → full sandbox.** Verso should support all three, with the lightweight code interpreter (QuickJS-style) as the default for multi-tenant deployments and the full sandbox as an opt-in for trusted/isolated workloads.
- **VM/sandbox setup is a precondition for quality:** Devin's onboarding lesson: give the agent a properly configured VM with lint/CI/tests before assigning any real task. Verso should make it trivially easy to configure the execution environment (Dockerfile, test runner command, lint command) once and have it available to all agent sessions.

### Testing and evals

- **Red-green TDD is the standard operating practice for coding agents:** Verso should bake TDD into the coding agent template/scaffold. The starter prompt should instruct agents to run the test suite first, use red-green TDD, and confirm the server boots and APIs curl correctly after tests pass.
- **Tests are now free — they should be mandatory, not optional:** Verso's evaluation framework should assume test generation is part of every coding task. The agent should be expected to write tests before implementation.
- **Conformance suites are the highest-value testing pattern when available:** Verso should support "give the agent a test suite and say run until it passes" as a first-class operation — not just unit tests, but multi-implementation conformance suites.
- **Offline + online evals form the eval loop:** Verso's testing subsystem needs both: (a) offline dataset evaluation for hill-climbing during development, and (b) online LLM-as-judge or code-based scoring over production traces. These feed the "Langsmith Engine"-style issue detection loop.

### Memory / context

- **Codebase memory is a moat and a usability requirement:** Devin's wiki (internal codebase representation that persists across sessions) is both a technical requirement and the primary stickiness mechanism. Verso should have built-in persistent context storage per project/repo — agents accumulate knowledge about the codebase rather than starting from zero each session.
- **Context has graduated from prompts → AGENT.md files → skills → wikis:** Verso should natively support AGENT.md / CLAUDE.md style instruction files, skills files, and LLM-wiki-style condensed knowledge bases. These should be versioned and taggable (not just flat files).
- **Memory should be open-standard and portable:** LangChain's explicit position is that memory should not be locked to a framework. Verso should store agent context in open formats (plain markdown, JSON) that survive if the framework is replaced.
- **Summarization as automatic short-term memory management:** when conversations exceed context limits, automatic summarization is the right default. Verso should build this in rather than leaving it to application code.

### Observability / monitoring

- **Traces are the center of the ADLC, not a nice-to-have:** LangChain's Ankush Gola: "Each agent trace captures the unique behavioral record of what your agent actually did at a specific point in time." Verso must emit structured traces by default, covering every LLM call, tool call, sub-agent dispatch, and their inputs/outputs/latencies.
- **Trace payloads are large and growing fast:** P50 = 37 KB, P99 = 12 MB, with multi-million token traces in complex coding agents. Verso's trace infrastructure should be designed for this scale from day one — not a bolt-on.
- **Agent UX latency matters as much as human UX latency:** agents consuming LangSmith (for tool calls, context retrieval, etc.) are blocked by slow infrastructure. Verso's internal tooling should target sub-100ms for read paths that are in the agent's critical path.
- **The observability loop should be agentic:** LangSmith Engine (an agent that scans traces, detects issues, suggests fixes) is the right long-term architecture. Verso should eventually ship a "Verso Engine" — an agent that monitors your other agents and surfaces actionable recommendations.

### Security

- **The lethal trifecta is the frame for agent security design:** any Verso agent that touches (1) private data + (2) external/untrusted content + (3) can send data outward is a prompt injection risk. Verso should surface this as a security checklist during agent configuration, not a footnote in documentation.
- **Sandbox by default, escalate with explicit opt-in:** Claude Code for the Web's model (all agents run in containers, skip-permissions is the default, worst case is container destruction) is the right design. Verso's default execution mode should be sandboxed; direct local execution should require explicit `--trust-local` style flag with a warning.

### API and product design

- **Task vs problem distinction is a critical UX teaching moment:** Devin's biggest onboarding lesson: users who give Devon "problems" fail; users who give it "tasks" succeed. Verso's documentation and scaffolding should make this distinction explicit and provide examples of well-formed vs. ill-formed tasks.
- **Confidence signals and scope-out before execution are valued:** Devin gives confidence levels before starting tasks ("here's how confident I am I understand each piece"). This HITL pattern — show a plan and confidence level, get approval, then execute — is worth supporting in Verso's default coding agent template.
- **The engineer-as-architect shift validates Verso's thesis:** the "brick layer to architect" transformation Scott Wu describes is exactly what happens when you have a clean agentic layer below the engineer. Verso's positioning should speak directly to this: Verso is the framework that lets you build the agentic layer underneath your engineering team.
- **Multiplayer / team-aware context is a differentiator:** Devin accumulates knowledge from every team member's interactions (PR reviews, Slack corrections, task context from other engineers). Verso should have a multi-user context model — agent sessions are not siloed per user but contribute to a shared team-level knowledge base.
- **Cost governance at fleet scale:** LangSmith LLM Gateway's spend limits + data exposure guardrails are essential when running 100+ agents. Verso should ship cost attribution and guardrails as part of the monitoring layer, not as an afterthought for enterprise.

### Positioning against LangGraph / Pydantic-AI

- LangChain's own admission: most apps started as chains, became graphs. But the core agent primitive never needed to be a graph — it's always been "LLM in loop." The graph was complexity that grew around the harness, not intrinsic to the agent.
- Verso's thesis (keep agents simple, opt-in graph for durable-execution edge cases) is validated by the trajectory: even LangChain's current flagship is "deep agents" (a harness around a simple loop), not "LangGraph everywhere."
- The ADLC (Build → Test → Deploy → Monitor) is a framework-level abstraction, not a product. Verso should provide the primitives for each phase; let teams compose their own lifecycle tooling rather than owning the entire platform like LangSmith does.
