# Anthropic Agent Design + LangChain Retrospective

## Building Effective Agents — https://www.anthropic.com/research/building-effective-agents — [read]

### Core Taxonomy: Workflows vs Agents

- **Workflows**: "systems where LLMs and tools are orchestrated through predefined code paths" — the code controls the flow
- **Agents**: "systems where LLMs dynamically direct their own processes and tool usage" — the LLM controls the flow
- Umbrella term for both: **agentic systems**
- The distinction is not about capability — it's about who drives the execution graph. Workflows are deterministic orchestration; agents are stochastic self-direction.
- "Agents can handle sophisticated tasks, but their implementation is often straightforward."
- "Agents are typically just LLMs using tools based on environmental feedback in a loop." — this is the canonical Anthropic definition of an agent

### Default Stance: Don't Build Agents

- "For many applications, optimizing single LLM calls with retrieval and in-context examples is usually enough."
- "The most successful implementations weren't using complex frameworks or specialized libraries."
- "Agentic systems often trade latency and cost for better task performance." — that tradeoff must be justified
- "Start simple, only increase complexity when needed."
- "Add complexity only when demonstrably improves outcomes." — measurement-gated escalation, not capability-first design
- "Success in the LLM space isn't about building the most sophisticated system. It's about building right system for needs."

### The Augmented LLM — Foundation Building Block

Three capabilities bolted onto a base LLM:
1. **Retrieval** — external knowledge lookup
2. **Tools** — callable functions/APIs
3. **Memory** — persistence across interactions

The model itself drives usage: "Model can actively use these—generating own search queries, selecting appropriate tools, determining what information to retain." These are not static additions — the model decides when and how to invoke each.

### Five Workflow Patterns (in order of complexity)

**1. Prompt Chaining**
- Each LLM call processes the previous call's output — sequential pipeline
- May include programmatic **gates** (checkpoints that validate intermediate output before proceeding)
- When to use: "Task can be easily decomposed into fixed subtasks"
- Tradeoff: "Trade off latency for higher accuracy" — slower but more controllable

**2. Routing**
- Classifier LLM call → routes to specialized downstream prompt/pipeline
- Enables separation of concerns, specialized prompts per input class
- When to use: "Complex tasks with distinct categories better handled separately"

**3. Parallelization** (two variants)
- **Sectioning**: Independent subtasks run in parallel, results merged
- **Voting**: Same task run multiple times to get diverse/consensus output
- When to use: "Divided subtasks parallelizable for speed, or multiple perspectives needed"

**4. Orchestrator-Workers**
- Central orchestrator LLM dynamically breaks down incoming task, delegates to worker LLMs, synthesizes results
- Critical distinction from parallelization: "Subtasks aren't pre-defined but determined by orchestrator based on specific input" — dynamic task decomposition, not static fan-out
- When to use: "Complex tasks where you can't predict subtasks needed"

**5. Evaluator-Optimizer**
- Generator LLM produces output; evaluator LLM provides structured feedback; loop until criteria met
- Two fit indicators that must BOTH be true: (a) "LLM responses demonstrably improve when human articulates feedback" AND (b) "LLM can provide such feedback"
- When to use: "Clear evaluation criteria, iterative refinement provides measurable value"

### The Agent Pattern — Full Spec

**Loop definition**: LLM using tools based on environmental feedback in a loop. That's it. The simplicity is intentional.

**Initiation**: begins from "command from or interactive discussion with human user"

**Execution requirements**:
- "Agents plan and operate independently"
- "Crucial to gain 'ground truth' from environment at each step (tool results, code execution)" — grounding, not planning in the abstract
- "Assess progress, pause for human feedback at checkpoints or when encountering blockers"
- "Include stopping conditions (maximum iterations) to maintain control" — hard caps required

**When agents are appropriate**:
- "Open-ended problems where difficult/impossible to predict required steps"
- "Can't hardcode fixed path"
- "LLM operates many turns, must have trust in decision-making"
- "Scaling in trusted environments required"
- Tasks where "flexibility and model-driven decision-making needed at scale"

**Risks**: "Higher costs, potential for compounding errors" — both worsen with loop depth

**Mitigation**: "Extensive testing in sandboxed environments, along with appropriate guardrails"

### Framework Critique — Verbatim

Pros: "Make it easy to get started by simplifying standard low-level tasks"

Cons: "Often create extra layers of abstraction that can obscure underlying prompts and responses, making harder to debug. Can tempt adding complexity when simpler setup suffices."

Recommendation: "Start using LLM APIs directly—many patterns implementable in few lines of code. If using framework, ensure you understand underlying code. **Incorrect assumptions about what's under hood are common source of customer error.**"

This is a direct indictment: frameworks are harmful when they make developers uncertain about what's actually running. Transparency is a correctness property, not just a DX nicety.

### Three Core Design Principles

1. "Maintain simplicity in agent's design"
2. "Prioritize transparency by explicitly showing agent's planning steps"
3. "Carefully craft agent-computer interface (ACI) through thorough tool documentation and testing"

### Tool Design — ACI (Agent-Computer Interface)

Anthropic coined "ACI" as an explicit parallel to HCI. The argument: tool interfaces are interfaces for the model, not the user, and deserve the same design rigor.

**Format selection rules (3)**:
1. Give model enough tokens to "think" before it writes itself into a corner — pre-commit space
2. Keep format close to what model has seen naturally in internet text — minimize distribution shift
3. Eliminate formatting overhead: no line counting, no string-escaping, no context-burning bookkeeping

**ACI design practices (4)**:
1. **Model's perspective first**: "Is usage obvious based on description/parameters?" Include example usage, edge cases, input format requirements, clear boundaries from similar tools. "Think of writing great docstring for junior developer."
2. **Optimize parameter names and descriptions**: especially critical when multiple similar tools exist
3. **Test empirically**: "Run many examples to see mistakes, iterate" — treat tool design as an empirical loop, not a spec exercise
4. **Poka-yoke** (mistake-proof): change argument design to make incorrect usage structurally impossible

**Concrete example**: SWE-bench agent — model made mistakes with relative filepaths after moving out of root directory. Fix: require absolute filepaths as a constraint on the tool interface. "Model used this method flawlessly" after change. Anthropic "spent more time optimizing tools than overall prompt."

### Agents in Practice — Two Validated Domains

**Customer support agents**:
- Natural fit: open-ended conversation flow + external data/action requirements
- Tool set: customer data, order history, knowledge base articles, action APIs (refunds, ticket updates)
- "Success clearly measured through user-defined resolutions"
- Business model enabled: "usage-based pricing models charge only for successful resolutions" — evals unlock billing

**Coding agents**:
- "Code solutions verifiable through automated tests" — this is why they work: ground truth exists
- Agents iterate using test results as environmental feedback (the loop has a real signal)
- "Problem space well-defined and structured"
- Anthropic's SWE-bench Verified: solves real GitHub issues from PR descriptions alone
- Caveat: "Automated testing helps verify functionality, human review remains crucial for ensuring solutions align with broader system requirements" — tests verify local correctness, not systemic fit

---

## Reflections on Three Years of Building LangChain — https://www.langchain.com/blog/three-years-langchain — [read]

### Origin and Early Design

- Launched fall 2022 as an 800-line personal Python package by Harrison Chase (`hwchase17`)
- Founding insight: "I saw a few common patterns in terms of how people were building and put those patterns into `langchain`" — pattern documentation, not framework design
- Early scope: model integrations, vector DB connections, high-level templates for RAG/SQL/extraction ("in 5 lines of code")
- Company formed February 2023 with cofounder Ankush Gola
- Core thesis: "LLMs are even more powerful when connected to external data and APIs"
- Early design principle: **model neutrality** — "Especially in a dynamic industry, helping users pick a model and later change that decision was incredibly important"

### The Abstraction Problem — Honest Admission

Specific failures acknowledged by Harrison:

1. **Breaking changes** — version instability punished production users
2. **Hidden abstractions** — "making hidden prompts explicit" was listed as a corrective action — LangChain's early chains had prompts baked in and invisible to the developer
3. **Package bloat** — unnecessary dependencies
4. **Dependency conflicts** — poor module isolation
5. **Outdated documentation** — knowledge rot in a fast-moving space
6. **Control vs. ease tradeoff**: "The same high level interfaces in `langchain` that made it easy to get started were now getting in the way when people tried to customize them to go to production."

This last point is the core structural tension: early LangChain optimized for Day 1 onboarding and paid for it at Day 30 (production customization). The abstraction that made the 5-line demo possible became the wall that blocked real deployments.

### LangSmith — Why It Was Kept Separate

- Problem identified: "LLM systems had quality problems. LLM calls kept on messing up, largely because they had the wrong context." — quality failures traced to context assembly, not model capability
- LangSmith built as observability + evals for LLM systems
- **Deliberately separated from `langchain`**: "We recognized that the space was very early and that a tool like LangSmith was much needed, so we committed to building LangSmith to be best-in-class, regardless of the framework (or lack of framework) that a developer used."
- Design principle: "LangSmith is neutral to the LLM and neutral to the underlying framework"
- This separation is the key lesson: **evals/observability must be framework-agnostic** or they don't get adopted

### LangGraph — The Controllability Response

Built because persistent user feedback demanded production control that `langchain`'s abstraction layer prevented.

**Two explicit pillars**:
1. **Controllability**: "no hidden prompts, no hidden context engineering. You had full control over your system"
2. **Runtime**: streaming, statefulness, human-in-the-loop, durable execution as first-party features — not bolted-on, not third-party

Validated in production: LinkedIn, Uber, J.P. Morgan, BlackRock.

LangGraph is the admission that graph-based orchestration has a legitimate use case — but specifically for the **durable execution + HITL + checkpoint-resume** axis, not as the default mode for all agents.

### LangChain 1.0 — The Rebuild

Decision to do massive breaking changes: "We decided it would be best to do this in 1.0 release."

Three design goals:
1. Easiest possible agent onboarding
2. More customization than previous versions (production control)
3. Production-ready runtime included

Implementation:
- Centered on "the core tool-calling loop that is now synonymous with 'agents'" — the loop is the primitive
- Introduced **middleware** for context engineering: "uniquely designed to give developers control over the 'context engineering' lifecycle exactly where they need it"
- Built on LangGraph runtime

Honest assessment: "The best patterns for an agent architecture are far better understood today than when we started the project, and 1.0 is far more curated than anything you've seen from our team before." — acknowledgment that the early versions shipped prematurely.

### Context Engineering — The Root Cause Frame

LangChain's quality post-mortem consistently pointed at context as the root cause:
- LLM failures traced to "wrong context" in LLM calls
- LangSmith's job: debug "every agent decision" — which means debugging what context the model saw
- LangGraph's middleware: control over "the 'context engineering' lifecycle exactly where they need it"
- Hidden prompts (original `langchain` chains) were a context engineering opacity problem — developer couldn't see or control what the model received

### Product Architecture Lesson — Platform Independence

- LangSmith built "completely separate from `langchain`" as a deliberate commitment to neutrality
- Goal: "a single place where you can get most of your tooling" while "making each new product independent of the existing ones but well integrated into the platform"
- This is the tension every framework builder hits: integration vs. independence. LangChain's answer: independence by default, integration as a surface layer.

### Key Numbers

- 80 million monthly downloads at time of publication
- 1+ million developers in community
- $125M Series B at $1.25B valuation (October 2025, 3-year anniversary)

---

## → Verso Implications

- **The taxonomy is the frame**: Anthropic's workflows-vs-agents distinction maps directly to Verso's design space. Verso should expose this taxonomy explicitly in its API — not as an implementation detail but as the primary conceptual layer users think in. Workflows (predefined code paths) go in one bucket; the agent loop (LLM-directed) goes in another. The framework should never blur this line.

- **Simple by default, escape hatch on demand**: Anthropic's canonical agent definition — "LLM using tools based on environmental feedback in a loop" — is almost embarrassingly simple. Verso's default `Agent` should be exactly this: a loop with tool calls and environmental feedback. No graph, no node types, no edge conditions. The graph escape hatch (LangGraph-style durable execution / HITL / checkpoint-resume) should be an opt-in `DurableAgent` or `WorkflowGraph` subtype — present but never the default.

- **Anti-abstraction as a first principle**: Both sources converge on the same failure mode: abstractions that hide prompts and context from the developer are correctness risks, not just DX inconveniences. Anthropic: "Incorrect assumptions about what's under hood are common source of customer error." LangChain: hidden prompts in chains were explicitly listed as a bug that had to be fixed. Verso must expose every prompt, every context assembly step, every tool invocation — no magic strings, no invisible system prompts, no hidden context injection.

- **Frameworks are dangerous when they lie**: The Anthropic warning — "ensure you understand underlying code" — is a design requirement for Verso. Every abstraction Verso provides should have a trivial "show me what this expands to" escape. The abstraction should be syntactic sugar over transparent mechanics, not a black box.

- **The five workflow patterns are composable primitives**: Prompt chaining, routing, parallelization (sectioning + voting), orchestrator-workers, and evaluator-optimizer map cleanly to composable Verso operators. These should be named, first-class, and composable — not emergent from graph topology. Give developers the vocabulary: `Chain`, `Router`, `Parallel`, `Orchestrator`, `EvalLoop`.

- **ACI is a first-class concern**: Anthropic's Agent-Computer Interface framing means Verso should treat tool definitions as artifacts that deserve their own design tooling — not just JSON schemas, but testable, empirically improvable interfaces. The framework should make it easy to run tool-usage tests, catch mis-invocation patterns, and iterate on parameter design. "Spent more time optimizing tools than overall prompt" is the practitioner signal — Verso's tooling should reflect this.

- **Poka-yoke tool design**: Verso's tool registration API should encourage and make it easy to constrain inputs structurally — require absolute paths, reject ambiguous enum values, make invalid states unrepresentable. This is a framework design choice, not user responsibility.

- **Gates are a primitive**: Programmatic gates on intermediate steps (prompt chaining) are not just a workflow pattern — they're the mechanism that keeps workflows from accumulating errors silently. Verso should expose gates as a first-class primitive: checkpoints where developer code can inspect/validate intermediate state before the next LLM call proceeds.

- **Stopping conditions are required, not optional**: "Include stopping conditions (maximum iterations) to maintain control" — Verso should make `max_iterations` a required parameter (with a sane default) on every agent loop, not optional. Every agent that can loop must have a declared exit condition. This is a correctness guarantee, not a configuration option.

- **Evals must be framework-agnostic**: LangChain's most durable product (LangSmith) is the one they deliberately decoupled from the framework. Verso's eval/observability story should follow the same principle — the eval layer should work regardless of whether users adopt Verso's agent loop or plug in their own. Lock-in through evals is a false strategy; adoption through evals is the right one.

- **Context engineering is the real product**: LangChain's post-mortem traced quality failures to "wrong context" in LLM calls. This is the correct frame. Verso's highest-value abstraction is not the agent loop itself (that's 50 lines of code) — it's the context assembly pipeline: what goes in, in what order, with what compression/priority logic. Verso should make context assembly inspectable, testable, and composable.

- **The tool-calling loop is now synonymous with agents** (LangChain 1.0's own framing): this validates Verso's thesis that the loop + tools is the durable primitive. Everything else — memory, context, evals, HITL — is infrastructure around that loop. Design Verso so the loop is the core, and everything else is pluggable.

- **Beware Day-1 vs Day-30 tradeoff**: LangChain's structural failure was optimizing for the 5-line demo at the cost of production customizability. Verso must be as easy on Day 1 as LangChain was, but the abstractions must be thin enough that Day 30 customization is a natural extension, not a rewrite. This means: no magic, explicit defaults, every parameter overridable.

- **Model neutrality is a founding constraint**: LangChain identified this early and it proved correct — "helping users pick a model and later change that decision was incredibly important." Verso must be model-provider-agnostic from day zero. The agent loop API must not bake in any provider's tool-calling format.
