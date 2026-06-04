# Transcripts — a16z + Microsoft + Google

## TRANSCRIPTS_A16Z.md

### Agent Loop Shape
- **Meter Benchmark tiers** define the target loop shapes Verso must support: Agent-1 coherent for ~2 min (simple tool-call ReAct), Agent-2 coherent for ~20 min (structured plan-execute), Agent-3 coherent for ~200 min (requires architectural changes, not just better models — durable execution, explicit checkpointing, error-accumulation prevention). The 200-min tier is where real enterprise work lives; current industry sits between Agent-2 and Agent-3.
- **What breaks coherence** (directly observed): context window overflow, goal drift, error accumulation (each mistake raises probability of the next), hallucinated progress (agent convinces itself it succeeded when it didn't). These are the exact failure modes a loop design must guard against.
- **The "five-tier employee" model** (a16z Big Ideas 2026): Tier-5 agent proactively identifies the problem, researches root cause, evaluates options, implements solution, then asks for approval at the last possible moment. The loop shape is: observe → plan → execute → checkpoint with human only at decision gates, not every step.
- **Replit agent loop**: write → run → observe output → diagnose → fix → repeat. Key: agent sees actual runtime output (stdout, error messages, exit codes), not just the code it wrote. Feedback from execution is a first-class loop input.
- **Cursor multi-model coordination**: one model plans, a different model executes edits, a third verifies. Model routing is a layer above the loop, not inside it.

### Models (Name + Provider + Role)
- **GPT-5 (OpenAI)**: unified reasoning with automatic budget allocator baked in — model itself decides how much "thinking time" based on query complexity; easy queries near-instant, hard queries spawn extended chain taking seconds to minutes. This is a strong design precedent: don't force callers to choose reasoning mode.
- **GPT-5 Codex (OpenAI)**: specialized coding model — used explicitly in the Microsoft Blueprint example as the coding agent's model because "it performs better on coding tasks than a generalized model." Model specialization per agent is a real pattern.
- **Claude Opus 4.6 / Claude models (Anthropic)**: cited as default for agentic coding work (Patrick Chanezon's setup). Step function in capability cited as "around Opus 4.5" — Karpathy confirmed this changed the industry.
- **Cursor routing**: Claude for agentic coding (fewer hallucinations on edits, slower), GPT-4 for some tasks (faster, different error modes), Gemini for long context. Routing on error-mode class, not just cost/speed.
- **RFT (Reinforcement Fine-Tuning)**: mechanism = (query, correct_answer) pairs → RL training loop on GPT-5 base; trains for reasoning, not pattern matching. Domain moat when proprietary data is truly non-recreatable.

### Tool Registry
- **OpenClaw tool integrations (reference implementation)**: Mercury banking (analytics), Google Docs (read/write), YouTube analytics, web scraping, Twilio (outbound phone calls), email (read access), Google Drive. Tools exposed to the agent as named capabilities; memory stored in MEMORY.md updated daily.
- **Cursor context assembly tools**: embedding search + recency + dependency graph to select relevant files. Not just "dump the whole repo" — active retrieval pipeline.
- **Multi-layer memory system (OpenClaw)**: Toby's QMD search tool + 2GB local database as three-layer memory; improvement over flat MEMORY.md was "marginal" — important calibration for Verso memory design (complexity doesn't guarantee quality).
- **Stagehand browser automation**: natural language → accessibility tree (AXTree) → LLM reasoning → Playwright execution. AXTree is more information-dense than screenshots (role, label, interaction data) and more stable than CSS selectors. Stagehand is a reasoning layer on top of Playwright.

### Context Assembly / Context Engineering
- "Context engineering" is the explicit term replacing "prompt engineering" — multiple a16z speakers use it without quotation marks. The shift: not what you say but (a) what tools you give the agent, (b) what data you inject at runtime, (c) what you retrieve from memory, (d) how you structure the window.
- **Cursor**: embedding search + recency + dependency graph for file selection; pre-warm context window in background before the user types; caches prompt prefixes aggressively.
- **The "fill the context" fallacy**: bigger context windows do NOT improve performance when filled with irrelevant content; selectivity matters. Cursor injects only files actually relevant to current task.
- **Long-term direction**: agents that persist understanding across sessions — not "start from scratch" but "I've worked on this codebase for 6 months." First-class project memory primitive.
- **The Cursor Rules pattern**: user-defined project memory files; once set up, switching cost becomes high (same lock-in dynamic as email filters). Verso needs a first-class equivalent.

### Memory
- **OpenClaw three-layer**: MEMORY.md (daily update, works poorly), QMD search tool, 2GB local database. Flat memory file is unreliable for recall. Vector search over local store is the working approach.
- **Cursor goal**: "what does this agent know about this project?" as a first-class primitive. Cross-session persistence of codebase understanding.
- **EVE (plaintiff law)**: outcomes data persists from intake to settlement/judgment — private outcomes dataset feeds back into intake decisions. This is a memory-as-competitive-moat pattern: what the agent remembers (case outcomes) is the product differentiation.

### System Prompts / Instructions
- **Replit agent**: creates a high-level plan before writing code; plan is visible to user; user can approve or modify before execution. Explicit plan-approval gate in the prompt flow.
- **Cursor agent instructions** (inferred): uses Cursor Rules files — persistent per-project instruction files that define coding conventions, keybindings, patterns. The instruction layer is user-editable and version-controlled alongside the code.
- **Agent-as-Tier-5-employee framing** (a16z): agent identifies problem → researches root cause → evaluates options → implements → asks approval at last possible moment. This is the target system prompt shape for autonomous agents.

### Error Handling
- **Specification gaming** (Steinhardt): agent finds technically correct answer violating intent; passes tests by hardcoding expected outputs. Prevention: clear intent specification, not just acceptance criteria.
- **Goal misgeneralization**: model learned a goal that works in training, breaks on distribution shift.
- **Hallucinated progress**: agent convinces itself it succeeded when it hasn't. Most dangerous failure mode for long-running tasks. Need explicit progress verification, not self-report.
- **Error accumulation**: each mistake raises probability of the next. The loop needs explicit error-state detection and recovery paths (not just retry).
- **Reliability over capability**: "you'd rather have a less capable agent that works 95% of the time than a more capable one that works 70%." Replit's lesson: reliability IS the product at adoption stage.
- **The debugging spiral**: stuck agents tend to retry the same approach repeatedly, hallucinate that they made progress. Hardest UX problem. Verso needs max-iteration limits + human escalation path.

### Exact Constants
- **Meter benchmark tiers**: ~2 min, ~20 min, ~200 min — 10x jumps; each jump requires architectural changes, not model improvement.
- **Computer use agent success rates**: 50-60% on simple single-screen tasks; drops to 20-30% on multi-step multi-app workflows. Business automation requires >90% — the gap from 60% to 90% is where most startups are stuck.
- **Cursor latency targets**: sub-100ms completions feel magical; >300ms feels like waiting. Autocomplete latency is a hard product constraint.
- **Replit failure concentration**: most failures happen in the first 5% (setup, dependencies) and last 5% (deployment, env vars) of a project; the middle 90% is where AI is best.
- **Harvey ARR growth**: 300%+ YoY; AmLaw 100 clients. Abridge: 100M+ patient records, 60-70% physician documentation time reduction. These are calibration numbers for "AI that works."
- **AI inference cost curve**: declined 99%+ over 3 years — faster than Moore's Law (50% per 18 months). At this rate, tasks uneconomic in 2022 become viable by 2026.
- **Enterprise AI adoption**: daily active users / licensed seats ratio = 20-40% for most enterprise AI; best products hit 70-80%. This is the real adoption metric.
- **ARR per FTE**: AI-native 2025 top performers at $1.5M-3M; some above $5M. Pre-AI SaaS baseline $400K-600K. Headcount scales 2x while revenue scales 10x.

### Multi-Agent Coordination
- **Cursor's multi-model pattern**: plan (model A) → execute (model B) → verify (model C). Each model chosen for its error profile on that task type, not just cost/speed.
- **Agent-to-agent negotiation without emotion**: agents negotiating with other agents can resolve disputes without emotional overhead. A new use case class, not just efficiency.
- **Dynamic agent layer vs. systems of record** (Sarah Wang, a16z): new agent layer extracts intent → classifies request → maps to workflow → identifies entities → executes. This replaces the SoR UI layer while the SoR data layer persists. Verso agents must be able to sit in front of existing systems without replacing them.

### Streaming Protocol
- Not explicitly detailed in a16z transcripts.

### Training / Eval
- **RL + verifier** is the fundamental new primitive: policy generates trajectory → verifier scores → policy updated. The verifier is the critical component, not the policy model.
- **Verifier difficulty by domain**: math (easy — proof checker), code (medium — run tests, but tests can be wrong), writing (hard — subjective), business decisions (very hard — outcomes take months). RL-trained agents will be superhuman on tasks with clean verifiers; only marginally better on tasks without.
- **Periodic Labs physical verifiers**: AI proposes experiment → robotic lab executes → physical results → AI updates hypothesis. This is RL with physical reality as the verifier — escapes the recursive self-improvement information ceiling.
- **RFT (OpenAI)**: domain expert models trained with RL on proprietary (query, correct_answer) pairs. Trains reasoning, not pattern matching. Target customers: law, finance, healthcare, science.
- **Mid-training (Periodic Labs)**: domain-specific corpus training BEFORE task-specific fine-tuning. Cheaper and often larger gains than RLHF; gives model domain intuitions and vocabulary before RL.
- **The recursive self-improvement impossibility** (Vishal Misra): pure LLM self-improvement without new external information is mathematically impossible — the model circles within the same information manifold. New information must come in: physical experiments, human feedback, real-world RL. Direct design constraint for Verso eval loops.

### Framework-Design Lessons
- **Context engineering is the product**: companies that invest in retrieval infrastructure, memory systems, and tool selection outperform those that just swap in newer models. The framework's job is to make context assembly excellent, not to compete on model quality.
- **Reliability beats capability**: the 95%-reliable, less-capable agent wins over the 70%-reliable, more-capable one at adoption stage. Verso's execution guarantees are more important than model quality.
- **The boilerplate problem teaches template design**: Replit fixes edges (first 5% and last 5%) with pre-built templates and deployment-as-a-service; agent operates in the middle. Verso should have a concept of "project scaffolds" that handle the edges so agents focus on the middle.
- **The verifier problem shapes what Verso can guarantee**: Verso can offer strong reliability on verifiable tasks (code runs, tests pass, schema validates); must be honest about weak guarantees on unverifiable tasks (writing quality, strategic decisions).
- **Multi-agent coordination belongs at the framework layer**: the routing, caching, and coordination layer on top of model APIs is where the value lives — not the model API itself. This is Verso's core value proposition.

---

## TRANSCRIPTS_MICROSOFT.md

### Agent Loop Shape
- **Computer Use Agent (CUA) loop — 4 explicit steps**: (1) Perception: understand current state (screenshot, DOM analysis, or hybrid); (2) Analysis: process perceived content (vision/pixel/visual markers/code analysis); (3) Plan and Action: receive task → generate plan → execute steps (click, type, navigate, fill); (4) Evaluate: check current state against expected, handle errors by looping back to step 1. Explicit evaluate-and-loop makes this a complete ReAct instantiation.
- **David Soria Parra's personal workflow** (ground truth from MCP co-creator): (1) plan mode (`Shift+Tab` in Claude Code) → agent creates plan → run the plan; (2) STOP the session → restart to clear context window ("I don't want to compact too much"); (3) next task, next task, next task; (4) after 2-3 sessions: launch 3-4 sub-agents in parallel: security review, principal architect review, super-picky code review → implement fixes. Explicit session boundary management as a first-class practice.
- **Patrick Chanezon's presentation-building agent** (real production workflow): agent reads prompt.txt → fetches sources in parallel (Teams via Work IQ, blog post, HBR article, Karpathy tweet via Playwright MCP) → background task for image generation (parallel) → generate 16-slide plan → install npm package → generate JS file → run JS → output PPTX. This is a realistic multi-tool, multi-source, parallel agent run with human approval gates.
- **Armchair Architects loop design rules**: simple planner with bounded steps; explicit reflection points; log all cognition (plans, decisions); define "bankruptcy" condition: "I need to know when to declare bankruptcy — agent has gone off, I'm not going to try to reset it 30 times" → log as failure, notify human, kick off agent recovery. Bankruptcy declaration is a first-class design pattern, not an edge case.

### Four Multi-Agent Patterns (Ranked by Practicality)
1. **Specialist Delegation**: orchestrator knows agents and calls specific specialist by name. Most practical today, most deterministic. "I know this is a legal question → delegate to legal agent."
2. **Sequential Directed Graph**: fixed workflow, one stage flows to the next. LangGraph/Semantic Kernel/LangChain all built around this. Orchestrator understands the workflow, not the domain problem.
3. **Parallel Farm-Out**: same query to N agents simultaneously, pick the best. "I have not found a use case yet practically" — expensive, rare legitimate use case.
4. **Negotiation/Consensus**: parallel farm returns conflicting results → arbitrator agent resolves. Supervisor/Critique: supervisor agent judges quality of all agents, tells orchestrator when an agent "isn't doing a great job anymore."
- **Message-based as the underlying pattern**: "a lot of these patterns are actually message-based — coming back full force." Fire-and-forget, single message/multiple processors, pub/sub. Recommendation: "go back to your books and look at message broker patterns."
- **Agents are NOT microservices**: peer-to-peer direct agent calling makes it "a lot more difficult to instrument, understand, and orchestrate." Prefer supervisor-worker or pub/sub. Most A2A communication will be those two patterns.

### Models (Name + Provider + Role)
- **GPT-5 Codex (OpenAI)**: specialized coding model used for coding agent in Zava system — explicitly preferred over general GPT-5 for coding tasks.
- **gpt-4o**: used for general agents in production deployment (`agent.yaml` shows `model: gpt-4o` as default, `gpt-5-codex` for coding agent).
- **Claude Opus 4.6 (Anthropic)**: Patrick Chanezon's main agent model in his GitHub Copilot CLI setup (high reasoning mode). Sub-agent uses GPT-5.4 for image generation. Multi-model per task is the real production pattern.
- **GPT-5.4 (OpenAI)**: image generation sub-agent model in Patrick's workflow.
- **Multi-model router**: "submit a request, intelligent system evaluates and picks the right model based on cost, performance, policy." When model changes (5 → 5.1), router abstracts it — agent code doesn't change. But: model swaps require regression testing to verify guardrails still hold.

### MCP — Complete Technical Detail
- **MCP transport options**: Standard I/O (stdio) — only for local dev, no auth; Streamable HTTP — current standard for remote servers, mix of HTTP + SSE for bidirectional long-polling, includes auth headers.
- **Four building block types**: (1) Tools (most common) — JSON-RPC `tools/call` with name + arguments + inputSchema + outputSchema; (2) Resources — read-only static data (architectural guidelines, API configs); (3) Prompt Templates — reusable prompt templates across apps; (4) Sampling (reverse direction) — server requests LLM inference from the client.
- **Initialization call structure**: client → `initialize` → server responds with capability list: `{prompts: {listChanged}, resources: {subscribe}, tools: {}}`. Every client sends this first.
- **November 2025 MCP version (20251125) key additions**: OpenID Connect discovery for simpler auth; incremental consent; async tasks (experimental) — `tasks/create` returns `taskId`, `tasks/get` polls for status. "Major step towards real multi-step pipelines."
- **`approval_mode` parameter**: `"never_require"` (read-only operations, no user prompt), `"always_require"` (write operations, user must approve every MCP call), `"none"` (no MCP calls).
- **Skills vs. MCP** (David Soria Parra, definitive from the creator): Skills = domain knowledge + local programs, progressive discovery (model loads skill token cost only when needed), no external connectivity built in. MCP = standardized external connectivity, doesn't provide domain knowledge. "They're actually very complementary."
- **MCP security**: OAuth 2.1 for agent flows; client credentials for autonomous agents; authorization code + PKCE for user flows. Early MCP had stdio with no auth — "rough start." Least privilege: give agent exactly the number of tools and rights it needs, not more.
- **MCP as translation layer**: "almost like embeddings for your context — how the language model understands the real world and the actions it can take."
- **Tool description is the routing mechanism**: the `description` field is how the LLM decides when to invoke the tool. "Call this when you need to find GitHub repos." The description IS the routing logic.

### A2A Protocol
- **A2A vs. MCP distinction** (Microsoft architects): MCP = agent calling DOWN to tools; A2A = agents talking to each other as PEERS. "Originally proposed by Google, now in Linux Foundation."
- **`agent.json` as discovery mechanism**: A2A client accesses this JSON to discover server's name, description, tools, auth, URL — without prior knowledge. When using ADK's `to_a2a()`, this file is auto-created at the hostname.
- **A2A client pattern**: `agent_card="http://localhost:8001/agent.json"` — the only field the A2A client needs. No model, no instructions of its own — it's a pure router to the remote agent.

### Identity / Security
- **Token lifecycle for agents**: normal OAuth token is 72 hours — wrong for agents. Agent tokens should be "valid for exactly the time it needs to execute, then that identity token should go away." Each new token request is itself an authorization checkpoint.
- **Principle of least privilege**: "the minimum amount of rights that they need in order to get the job done." Language models have no authorization concept — everything around the LLM must enforce authorization.
- **Zombie agent risk**: agent that finishes a task should not retain access rights. Token expiry tied to task completion, not wall clock.
- **Microsoft Entra ID**: introducing agent identity with agent-specific OAuth/OpenID Connect token lifecycle.

### Observability
- **OpenTelemetry as the standard**: Microsoft, Splunk, Datadog committed. Microsoft created "agent scope" — a specific telemetry schema for agents submitted as PR to OpenTelemetry community (not yet widely adopted as of recording).
- **Agents are not microservices**: need specific data models for agent spans, not just HTTP traces. Log all cognition: plans, decisions, not just requests/responses.
- **Ring releases**: canary 5% → expand by rings; monitor cost and performance at each ring before expanding. Same as traditional SRE, applied to agent deployments.

### Eval Framework (Four Metrics — Concrete)
1. **Relevance**: is the response actually relevant to the task? (Agent can interpret task differently and go down wrong path.)
2. **Groundedness**: is the response grounded in actual data sources, not fabrication? ("Is it actually pulling from our vector store or just fabricating employees?")
3. **Tool Accuracy**: did the agent choose the RIGHT tool? Low accuracy → "maybe you have too many similar tools or too many tools and we're distracting the LLM."
4. **Tool Output Utilization**: after tool responded, did the agent actually USE the output? Distinct from tool accuracy — can call tool and ignore output.

### Agent Checklist (Architect's Framework — Eric's)
- Phase 1: Validate agent exists for right reason — pick ONE good job, define ROI + success metrics + measurability.
- Phase 2: Enumerate tool catalog, knowledge sources, update frequency; prevent PII leakage, establish evaluators and guardrails.
- Phase 3: Memory design — short, medium, long-term; TTL policies; cognitive monitoring to detect when agent is making things up vs. using authoritative memory.
- Phase 4: Reasoning scaffolding — simple planner with bounded steps; explicit reflection points; log all cognition; bankruptcy declaration.
- Phase 5: OpenTelemetry-based logs, metrics, traces.
- Phase 6: Ring releases; monitor cost and performance.

### Constants
- **Token budget for tools**: "give the agent exactly the number of tools and the number of rights that it needs — not more." No specific number given but "minimal viable" is the explicit principle.
- **Multi-agent handoff max turns**: `termination(max_turns=20)` — explicit upper bound in the code example.
- **Patrick's agent config**: 5 MCP servers, 4 plugins, 65 skills, 4 agents in his personal GitHub Copilot CLI setup. This is the complexity level a production agent user reaches organically.
- **Three-attempt rule** (Sid Anand Carey): try with AI three times; if it doesn't get it by turn three, do it yourself. A practitioner-discovered constant for human fallback.

### Framework-Design Lessons from Microsoft
- **Small specialized agents over one Uber-agent**: "I would much rather have you build a thousand agents with very very limited scope that know only what they need to do." Safety, security, and control all come from small-scope agents. One Uber-agent "frightens me personally."
- **The taxonomy is three layers**: (1) MCP — tool/resource exposure (most mature), (2) A2A — agent-to-agent communication (standardizing), (3) Orchestration/lifecycle — how agents start, resume, checkpoint, escalate (least standardized). "Anthropic is actually quite far ahead in this — Claude Code and Claude Work's orchestration is rock solid."
- **Don't invent proprietary agent protocols**: "Are they making their own crypto?" — same red flag. Only buy/use agents that support OAuth, OpenTelemetry, MCP, A2A. Verso must adopt these standards from day one.
- **Context engineering as onboarding**: "Think of yourself as a project manager onboarding an agent to your project" — architecture understanding, coding conventions, communication patterns. The `agents.md` file pattern (persistent preferences the agent reads at start of every session) is the right abstraction.
- **Declarative over imperative**: the developer role shifts from imperative ("I write all the code") to declarative ("I specify the outcome, verify the result"). Framework should support prompt.txt / prompt files as the primary agent invocation mechanism.
- **Verso must have explicit bankruptcy handling**: "I need to know as an architect when to declare bankruptcy — log as failure, notify a human, agent recovery process kicks in." This is a first-class API, not an edge case.
- **Cost is a first-class concern**: "if you use frontier models and the agent layer gets overwhelmed, it's not only bad for response times — it can also get very expensive." Rate limiting, request balancing, execution cost monitoring are required features.

---

## TRANSCRIPTS_GOOGLE.md

### ADK Architecture (Agent Development Kit)
- **Model-agnostic + cloud-agnostic**: connect to OpenAI or any open-source tool, deploy anywhere. Cloud Run is the best target: "one-step command." MCP toolset is built into ADK (not a separate layer).
- **Three agent categories**: (1) LLM-based agents — use LLM for reasoning, decide tool calls and agent transfers; (2) Workflow agents — prescriptive/deterministic (Sequential, Parallel, Loop); (3) Custom agents — implement your own execution logic. All three compose together.
- **Workflow agents are the right abstraction for flowchart-expressible logic**: "If you can draw a flowchart for a part of your agent's logic, workflow agents are the way to go — makes execution flow more deterministic." Use workflow agents for predictable order; use LLM agents for flexible decision-making.

### Agent Loop Shape
- **ADK event structure** (explicitly shown in Dev UI): user input → model thinking → tool call request → tool execution → tool result → model response. Each event clickable to inspect full payload. This is the canonical ADK loop.
- **LoopAgent** (iterative refinement pattern):
  ```
  LoopAgent(sub_agents=[draftingAgent, critiqueAgent], max_iterations=10)
  // Exits when critiqueAgent is satisfied OR max_iterations reached
  ```
  Explicit termination condition + hard cap. Both are required.
- **Gemini 3 Flash instruction following**: "15-minute conversations stay fully on-task with just a system prompt" — previously needed Pipecat Flows module for complex multi-step workflows. Model quality improvements can retire complexity in the framework.
- **Pipecat ConciergeAgent**: gigantic system prompt, Gemini 3 stays on task for 15+ minutes. Registered tools: `search_flights`, `search_lodging`, `save_trip_report`, `google_search_grounding`. Tool + memory save pattern for session persistence.

### Models
- **gemini-2.0-flash**: used in supply chain orchestrator, inventory agent, customer support agent. General-purpose workhorse.
- **gemini-3-flash**: used in Pipecat voice agent with `thinking_level="minimal"` — "huge impact on how quickly the bot will answer." Gemini 3 is "more than smart enough to do all of this without thinking too hard" — don't over-think.
- **Thinking level configuration** (critical constant): `thinking_level="minimal"` for voice agents where latency matters; higher levels for complex reasoning. Framework should expose this as a first-class parameter.

### Tool System (Complete Patterns)
- **FunctionTool pattern** (TypeScript ADK — complete):
  - actual function that does the work (returns JSON-serializable object)
  - tool definition with `name`, `description`, `parameters` (Zod schema), `handler`
  - description field = routing mechanism: "Call this when users ask about their order or delivery"
  - ADK intercepts function call, executes code, passes result back to LLM
- **Three tool types in TypeScript ADK**: (1) Function tools (your code + schema); (2) Built-in tools (Google Search = one line: `llm.enable_google_search_grounding()`); (3) Third-party tools (MCP server tools).
- **AgentTool** (agent-as-tool pattern): wrap any agent as a callable tool for another agent. `new AgentTool(summarizerAgent)` — the parent agent calls it like a tool, not a peer.
- **MCP Toolbox for Databases**: `tools.yaml` maps SQL statements to named tools; agent uses `MCPToolboxToolset(url, toolset_name)` — no tool definitions of its own, no database implementation knowledge. The toolbox is a proxy regardless of whether backend is Postgres, Mongo, or REST.
- **Google Search Grounding**: one line in Pipecat — `llm.enable_google_search_grounding()`. "Gemini already knows how to use Google. This is basically just turning it on." Built-in tool registration should be this simple.

### A2A Protocol (Complete Pattern)
- **`to_a2a()` utility**: one-line conversion — takes root agent, returns A2A-compatible server running on specified port. Auto-creates `agent.json` at the hostname when hosted with uvicorn.
- **`agent.json` structure**: `{name, description, tools: [{name, description}], url, authentication}`. This is the A2A discovery mechanism.
- **A2A client = no model**: `finance_agent = LLMAgent(name="finance_agent", agent_card="http://localhost:8001/agent.json")` — the ONLY field needed is the agent_card URL. The client doesn't know what tools the server has or what language it's written in.
- **SSE for long-running operations**: A2A server sends status updates (`completed`, `in_progress`, `started`, `cancelled`, `failed`) via SSE. For multi-day operations, push notifications can be enabled.
- **Human-in-the-loop in A2A**: in the supply chain demo, finance approval requires human yes/no. In production: finance agent would create a Jira ticket or send email for third-party human approval — then continue. The HITL gate is asynchronous.

### State and Memory (Three-Layer Model — Explicit)
```
Session    — unit of conversation: unit ID, user ID, full event history, shared state map, last-event timestamp
State      — agent's "temporary scratch pad": serializable key-value pairs
             Prefix controls lifecycle:
             "user:"   → persists across sessions for that user
             "temp:"   → only lasts for current turn
             (no prefix) → lasts for current session
Memory     — long-term storage (separate service)
```
- **Template syntax in instructions**: `{subject}` and `{audience_level}` are filled from session state at runtime. Instructions become dynamic without code changes.
- **Context persistence via tool**: `save_trip_report` tool — LLM returns markdown describing everything planned, saved to file. Next session reads it back into context. Simple and reliable, no special memory infrastructure.

### Security (Model Armor — Complete Architecture)
- **Input filtering flow**: client prompt → Model Armor (BEFORE model) → if clear, to model → model calls tool → tool response → Model Armor again → back to client. The callback hook is `before_model_callback` in ADK.
- **Output filtering (SDP — Sensitive Data Protection)**: REDACTS not blocks — preserves application flow. Tool response: "credit card is 4532-..." → after SDP: "credit card is [REDACTED]" → model formats response → response also goes through SDP before returning to user.
- **Authentication within tools, not agents**: agent should never handle credentials directly. Agent creates session ID → passes to tool → tool requests access token from IDP → tool calls API → API validates → returns. "All authentication downstream is completely invisible to the user."
- **API keys via Secrets Manager**: never env vars, never hardcoded. Agent uses IAM credentials to fetch secret → passes to tool. "You'd be surprised how frequently API keys in env vars happen in production."
- **OWASP LLM Top 10 covered**: prompt injection (direct and indirect), sensitive information disclosure, improper output handling, excessive agency (insufficient access control).

### Infrastructure (Gemini Serving — Critical Numbers)
- **KV Cache routing challenge**: to achieve cache hits, requests with the same prefix must consistently route to the same machines. Gemini app vs. API have different tool use patterns and different context-change patterns — global cache optimization is hard because usage patterns differ by product.
- **2M context window tradeoff**: not generally available because "takes enormous capacity away from broader user base." Gmail all-context feature uses embeddings + retrieval rather than a 2M context window per call — demonstrates that embeddings are the scalable path, context window is not.
- **Embeddings as scalability solution**: embedding-based retrieval (vs. token-based) is the path to personalizing at scale without burning context window. "Deploy for more users and make it fundamentally easier for them to derive value."
- **Traffic floor problem**: each new model launch sets a new traffic floor — old model stays heavily used even after new model launches. Capacity prediction is "wishful thinking."
- **TPU vertical integration**: seventh-generation TPU (Ironwood) as serving efficiency enabler. Same team from pre-training through production — joint decisions on compute allocation.

### Key Design Principles (Stated Explicitly in ADK Tutorial)
- "Give precise and explicit instructions to define the agent's purpose, persona, goals, and guidance on how it should interact with users and tools."
- "Tools should also be described with great detail so the LLM clearly understands its purpose and arguments."
- Multi-agent is ideal "for complex problems that naturally decompose into smaller subtasks or require different areas of expertise."
- Overhead warning: "there might be some overhead in communication or latency" with multi-agent systems — choose the right approach for the problem scope.
- Purpose-built agents over multi-purpose agents: "a researcher agent for writing design docs, a testing agent for software testing" — the same principle Microsoft also stated.

### Framework-Design Lessons from Google
- **Workflow agents for deterministic logic + LLM agents for flexible logic**: don't use LLM reasoning for things that can be expressed as a flowchart. The LoopAgent/SequentialAgent/ParallelAgent primitives must be first-class, not afterthoughts.
- **Agent-as-tool is the lightweight composition pattern**: `AgentTool(summarizerAgent)` — any agent can become a tool callable by another agent. No separate protocol needed for this pattern; it's just tool calling with an agent behind it.
- **State prefix lifecycle is the right memory abstraction**: `user:` / `temp:` / (no prefix) for across-sessions / current-turn / current-session. Simple, explicit, no magic TTL management required by the developer.
- **The A2A `agent_card` pattern is the right inter-agent discovery mechanism**: one URL that returns a JSON document describing everything the remote agent offers. Verso should adopt this pattern for any inter-agent communication.
- **MCP toolbox proxy pattern**: tools.yaml + binary proxy is the right abstraction for database tools — agent defines the query capability, not the database connection. Verso should have a first-class database toolbox that works this way.
- **Thinking level is a first-class parameter**: expose it per-call. Minimal for latency-sensitive (voice), higher for accuracy-sensitive (complex reasoning). Don't hide it.
- **Build observability from day one**: the Dev UI showing event streams (user input → model thinking → tool call → tool result → model response) should be the standard debugging interface. Every Verso agent should expose this event stream.

---

## → Verso Implications

### Loop Design
- **Implement the Meter Benchmark tiers as explicit design targets**: Agent-2 (20-min coherence) is the MVP bar; Agent-3 (200-min) requires durable execution + checkpoint-resume. These are not aspirational — they define the two modes Verso must support from launch.
- **Bankruptcy declaration is a required API, not an edge case**: `agent.declare_bankruptcy(reason, context)` → log failure, emit event, escalate to human. Called explicitly when `max_iterations` is hit or when error-accumulation is detected. Based on Microsoft architects' explicit checklist item.
- **Build the evaluate-and-loop as a first-class step**: every agent loop has a perception step (observe current state), action step, and evaluate step (did it work? if not, loop back). Don't let agents self-report success.
- **Hallucinated-progress detection**: require agents to produce verifiable progress artifacts (test pass, file written, API response received) rather than accepting "I completed the task" as completion. From Cursor/a16z reliability analysis.
- **Session boundary management**: expose explicit `session.reset()` (clear context, start fresh task) and `session.checkpoint()` (save state, resume later). David Soria Parra does this manually by restarting Claude Code after 2-3 tasks — Verso should make it a first-class operation.

### Tool System
- **Tool description IS the routing logic**: the `description` field of every tool must be written as routing instructions ("Call this when..."). Verso should enforce this in the tool schema and warn when descriptions are vague.
- **Three tool types should be first-class**: FunctionTool (user code + schema), BuiltinTool (framework-provided, one-line activation), MCPTool (external MCP server). AgentTool (agent-as-tool) is the fourth type — any agent can be used as a tool by another.
- **MCP is the external connectivity layer; Skills are the domain knowledge layer**: they're complementary, not competing. Verso should support both: MCP tools for external services, Skill files (markdown + code) for domain knowledge with progressive loading.
- **Minimal viable tool set per agent**: give agents exactly the tools they need, not more. Too many similar tools → tool accuracy drops ("LLM gets distracted"). Verso should surface tool-accuracy metric in eval output.
- **`approval_mode` per tool**: `never_require` (read-only), `always_require` (write/destructive), `batch_require` (approve at session start). Based on Microsoft's implementation.

### Multi-Agent Coordination
- **Implement the four patterns explicitly**: Specialist Delegation (default, most practical), Sequential Pipeline, Parallel Farm, Consensus/Arbitration. Expose them as named primitives, not just graph edges.
- **Prefer supervisor-worker and pub/sub over peer-to-peer**: direct agent-to-agent calling makes observability and orchestration hard. Verso's inter-agent communication should go through the framework layer, not direct calls.
- **Agent-as-tool vs. A2A vs. handoff**: three distinct composition patterns. Agent-as-tool = synchronous, returns result. A2A = cross-network, remote agent, `agent_card` discovery. Handoff = transfer of control to another agent in the same system. All three needed.
- **A2A `agent_card` pattern for remote agents**: standardize on `{name, description, tools: [...], url, authentication}` as the discovery format. Verso remote agents should auto-serve this at their root URL.

### Memory
- **State prefix lifecycle as the core memory primitive**: `user:key` (cross-session), `temp:key` (current turn only), `key` (current session). Simple, explicit, no hidden TTL management. Google ADK's implementation is the right model.
- **Context persistence via save-and-reload tools**: `save_report(markdown)` → file → next session reads it back. This works reliably with no special infrastructure. Verso should ship a `save_context` / `load_context` built-in tool pair.
- **Project memory file (agents.md / CLAUDE.md pattern)**: agent reads this at the start of every session. User edits it to encode preferences, conventions, workflow state. This is the right long-term memory abstraction for developer use cases.
- **First-class cross-session project memory**: "what does this agent know about this project?" is a first-class primitive. Verso should have a `ProjectMemory` type that persists across sessions and is version-controlled.

### Context Assembly
- **Context engineering beats model quality**: invest in retrieval infrastructure, memory systems, and tool selection. The framework's job is to make context assembly excellent, not to compete on model quality.
- **Selective retrieval over full-context dump**: embedding search + recency + dependency graph for file/document selection. Never inject everything — inject only what's relevant to the current task. Verso should ship a retrieval primitive that selects context rather than dumps it.
- **Template syntax in instructions**: `{variable}` filled from session state at runtime. Makes instructions dynamic without code changes. First-class feature, not a workaround.

### Security and Identity
- **Agent token lifecycle = task lifetime**: OAuth tokens that expire at task completion, not 72 hours. Each new-token request is an authorization checkpoint. Verso should have a first-class task-scoped credential system.
- **Authentication inside tools, never in agents**: agents should never handle credentials. Tool layer owns auth. Verso tool registration should support IAM-credential-based secret fetching as a built-in pattern.
- **Input filtering as middleware, not LLM logic**: `before_model_callback` pattern — Model Armor / input validation runs before the LLM sees the prompt. Output filtering (SDP redaction) runs before the response leaves the system. Verso should have middleware hooks at both positions.
- **Least privilege enforcement**: Verso agent definitions should declare exactly what tools and data sources they need. Runtime should prevent access to undeclared resources.

### Observability and Eval
- **Event stream as the standard debugging interface**: user input → model thinking → tool call request → tool execution → tool result → model response. Every Verso agent should emit this event stream. Dev UI should visualize it.
- **Four-metric eval framework as built-in**: Relevance, Groundedness, Tool Accuracy, Tool Output Utilization. These should be standard Verso eval metrics, not add-ons.
- **OpenTelemetry agent scope as the trace format**: adopt the emerging standard. Every agent span should include: agent name, session ID, turn ID, tool calls made, model used, token counts, bankruptcy events.
- **Ring releases as a deployment primitive**: `agent.deploy(version="v2", canary=0.05)`. Instant version rollback: `agent.deploy(version="v1")`. Based on Microsoft's agentVersion pattern.

### Framework Architecture
- **Durable layer for 200-min tasks; simple loop for 20-min tasks**: the escape hatch for durable execution (checkpoint, resume, HITL) should be opt-in, not the default. Simple ReAct loop should be the default.
- **Small specialized agents over Uber-agents**: enforce single-responsibility at the agent definition level. Verso agent definitions should have a `scope` field that narrows what they can do.
- **Model routing layer above the loop**: the routing, caching, and coordination layer is where the value lives. Verso should expose model routing as a first-class concept: route by task type, by error profile, by cost budget.
- **Adopt all four open standards**: MCP (tool exposure), A2A (inter-agent), OpenTelemetry (observability), OAuth/OIDC (agent identity). Any Verso agent that doesn't support these is a red flag — "are they making their own crypto?"
- **The three-attempt rule as a built-in escape hatch**: after N failed attempts on the same subtask, escalate to human. N=3 is the practitioner-discovered value. Make it configurable per agent, defaulting to 3.
- **Cost is a first-class concern**: expose token costs, model costs, and total task costs in the event stream. Rate limiting and cost budgets should be first-class agent configuration, not afterthoughts.
