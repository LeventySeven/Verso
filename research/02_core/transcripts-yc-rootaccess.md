# Transcripts — YC Root Access

Dense extraction from 60 YC Root Access interviews (2025-05-01 → 2026-05-23, ~301K words) covering agent architecture, memory, context engineering, multi-agent coordination, HITL, evals, and tool design as actually practiced in production by funded YC companies.

---

## TRANSCRIPTS_YC_ROOT_ACCESS.md

### Agent Loop Shape

**Answer This / Ayush (2026-05-19) — thin-harness self-extending loop:**
- Foundation: Claude Code CLI wrapped in a thin Python harness; task queue (directory or queue the harness monitors)
- Inbound triggers: email, Slack, external signals → written to task queue
- Loop: agent picks task off queue, reads codebase/DB snapshot (read-only), selects tool from registry, executes, writes result
- Self-extension: when agent encounters a repeated task it cannot handle, invokes a coding sub-agent that authors a new CLI tool and registers it permanently; grew from skeleton + few CLIs to 45+ CLIs autonomously
- Self-correction: agent can edit `instructions.md` (behavioral memory file) in response to natural language feedback from non-technical co-founder via Slack; change persists to next session without deploy
- Factual memory updated by cron job on each new release (agent reads current source directly, not stale docs)
- Result: 100+ emails/day processed, 400+ customer support tickets closed with 2 FTEs at $2M ARR

**Parahelp (2025-12-02) — sampling-over-chains + four-mode assistant:**
- Phase 1 (summer 2024): sampling N Sonnet 3.5 tool-call sequences in parallel per ticket, judge model or heuristic selects best path → lifted resolution from 20% (simple RAG) to 50-60%
- Architecture now: ~40 memory files per customer (policies, integration specs, exception rules, tone, escalation); generalized tools (Stripe, Datadog, Linear, SSO, internal APIs); all complexity in policy files, not in tool set
- Execution time range: 15 seconds (FAQ) to 3 minutes (enterprise debug, 15+ custom tool calls + extended reasoning)
- Orchestration: Hatchet (YC job queue) for concurrency; validated for 700 simultaneous agent instances (mass follow-up feature)
- Every tool has a `validate` function: deterministic code check before the tool call commits its side-effect (policy ceiling, account state, required fields); cited 99% success rate for well-defined billing actions
- Four-mode Parahelp Assistant (support manager-facing): Ask / Configure / Testing / Deep Research — each mode has distinct system prompt + scoped tool set; mode transitions self-initiated by agent; mode switch = structured context compaction boundary (carry digest forward, restart message history cache)
- Testing mode: up to 5 sub-agents × 5 test scenarios each = 25 parallel tests; each sub-agent generates YAML test cases in internal eval framework + simulates mock context (correct account tier, active outage flag, subscription state)
- Deep Research mode: grep-like semantic search across 20,000 tickets; sub-agents open 50-500 full tickets (PII removed); aggregated report with per-ticket citations and policy improvement estimates

**Jared Friedman / YC (2026-05-19) — self-improving loop architecture:**
- 5 layers: (1) Sensor layer — real-world inputs (emails, tickets, telemetry), (2) Policy/decision layer — what agent can do autonomously vs. must log vs. must ask human, (3) Tool layer — deterministic APIs (DB queries, calendar lookups), (4) Quality gate — eval checks, safety filters, human review for high-risk actions, (5) Learning mechanism — observe failures, loop back
- YC internal example: monitoring agent on top of query agent; observes every query by every YC employee; identifies failures; asks why / what fix is needed; writes code; submits PR to YC codebase; agent reviewer merges; deploys; next day same query succeeds — "literally happens overnight now"
- Key condition: every step runs without (or minimal) human intervention → system improves while you sleep

**Skyvern / Sachin (2026-05-19) — PRD pipeline (multi-step agentic):**
- Step 1: semantic search over call recordings for topic; Step 2: Slack search; Step 3: Notion docs; Step 4: customer communications; Step 5: draft PRD grounded with specific evidence; Step 6: adversarial sub-agent review (generates critique); Step 7: RICE prioritization filter (removes junk requirements)
- Content marketing pipeline: retrieve last 20 call recordings → bucket topics (recurring pain, contrarian, social-media-format) → draft 5 LinkedIn/Twitter post pairs → filter through Pangram (AI writing detector) → attach meme → email Sachin for one-click approval

**Jake Heller / CoCounsel (2025-08-25) — pipeline design from human expert workflow:**
- Design principle: ask "how would the world's best human attack this problem?" — that's version 0 of the architecture
- Legal research pipeline: (1) clarify question (jurisdiction, angle) — discrete separate step, (2) formulate 20-50 search queries across different terms/angles, (3) execute queries, (4) read each result page for relevance and notes, (5) compile final answer
- Decision rule: is this step linear (implement as sequential functions) or agentic (needs loop-back if results aren't working)? Never default to agentic — if best human would do it linearly, implement linearly
- Scale: hundreds to thousands of prompts at Thomson Reuters scale; each micro-step has its own prompt, its own eval suite, its own RF-tuned model

---

### Models (exact names and roles)

- **Parahelp**: Anthropic model family throughout; Claude Opus 4 crossed the threshold for automated eval generation (generating YAML test cases + mock context + policy improvement proposals without human authorship); Sonnet 3.5 was the earlier sampling-over-chains enabler
- **Answer This**: "Claude Code works exceptionally well because it already knows how to inspect files, run commands, and use CLIs" (verbatim endorsement from Ayush)
- **Trigger.dev**: "Claude Opus 4.5 is substantially better at using tools like Trigger correctly" — closed the bifurcation between traditional devs and vibe coders; TypeScript is "the de facto language of AI applications" (Matt)
- **Salient voice AI**: GPT-3.5/successors for demo quality; Llama 2 (open weights) + vLLM for serving at 400K dials/day — vLLM "allowed anyone like us to grab one of these Llama models, serve it up to millions of requests per minute"
- **Phone AI**: custom fine-tuned LLMs (not OpenAI under the hood); started with Groq for latency; architecture forces decomposition into smaller specialized models (variable storage ≠ conversational response model)
- **CoCounsel**: "a different model for every single prompt"; comparison runs per micro-step; explicit call-out: "Gemini 2.5 Flash — beautiful model, cheap as [hell]. If it works to your level of satisfaction, use that. Don't use 2.5 Pro."
- **Jared YC loop**: no model name given; tool layer is "deterministic APIs the AI can call"

---

### Tool Registry (names, schemas, patterns)

**Answer This — bootstrapped tool registry:**
- Starter CLIs: Intercom (customer support), Fathom (meeting notes), Stripe (payments), others
- Meta-tool: coding agent as a CLI — gives main agent the ability to author and register new tools
- `instructions.md` as a writable personality/behavioral memory file: loaded into context every turn; agent permitted to edit it in response to feedback
- Slack as interface: inbound messages trigger task queue via SSH; zero custom dashboard

**Parahelp — tool design principles:**
- Every tool (including MCP tools) has a `validate` function for deterministic pre-execution checks
- Tools: Stripe, Datadog, Linear, SSO systems, Notion, Retool, Slack approval flow
- Slack approval flow: for sensitive actions above confidence threshold, agent generates short summary → billing manager clicks approve → agent resumes thread and executes
- Anti-churn tool (roadmap): offer configurable discount based on churn signals (policy: "offer 20% off if about to churn")
- Upsell tool (roadmap): send higher-tier plan link based on usage signals
- Mass follow-up: research agent identifies ticket category → support manager approves policy → 700 simultaneous agent instances spawned

**Dex Horthy / HumanLayer (2025-08-25) — MCP tool design warning:**
- "If you have MCP tools that return big blobs of JSON, that's going to flood your context window with a bunch of nonsense"
- Tools should return only what the agent needs for the next step: structured, minimal, pre-filtered
- Sub-agent ideal return: file path, line numbers, brief explanation, explicit pointers to where parent should read next

**Phone AI — decomposed pipeline:**
- Variable storage (capturing caller name/email): smaller, faster model
- Conversational response generation: different model
- Each component independently testable and updateable
- Validate function exists between LLM decision and actual side-effect

---

### Context Assembly and Compaction

**Jared Friedman (2026-05-19) — making organization legible to AI:**
- "If it is recorded, it happened to the AI. If it did not get recorded, it did not happen to your intelligence."
- Process: raw recordings → diarization → categorization by topic → synthesis into structured representation → AI gets breadcrumbs, not 100K hours of audio
- YC user manual: 2,000 hours of recorded office hours → diarized → categorized (fundraising, hiring, co-founder disputes) → 150-page user manual "dramatically better than existing one" → now updated monthly
- Organization's domain knowledge: emails, Slack, Notion, recordings — must be made "legible" before any self-improving loop can run

**Dex Horthy / HumanLayer (2025-08-25) — Research → Plan → Implement framework:**
- LLMs are pure functions: output quality = input quality, no other lever exists
- Keep context utilization under 40% at all times; at 40%, write structured progress file to disk → new context window reads that file as onboarding
- Never use `/compact` (slash-compact): "trash" — produces summary with no authorial control, loses architecturally critical info
- Intentional compaction format: goal / what was accomplished / files touched + specific changes / what was tried and failed (why) / next steps / constraints established
- Research phase output: not prose summary but navigational map with file names + line numbers (e.g., "authentication flow starts in `src/auth/middleware.go:47`, calls `ValidateToken()` at line 83, which delegates to `TokenStore.Lookup()` in `src/db/tokens.go:122`")
- Plan phase: every change specified including files, specific code snippets, verification/testing steps; if you're shouting at agent during implement, the plan was bad — fix the plan not the agent
- Sub-agents for context control (not task decomposition): parent dispatches sub-agent to find relevant files and return structured summary; parent never consumes the search cost directly
- Context hierarchy of harm: bad info (worst) > missing info > noise
- 170,000 usable tokens: fewer tokens consumed per task = higher quality result (Jeff Huntley / SourceAMP finding)
- The spec is the source; the code is the compiled artifact (Sean Grove "The New Code"); most teams are committing the binary and deleting the source

**Chroma / Jeff Huber (2025-08-25) — gather-and-glean framework:**
- Gather (maximize recall): pull all possibly relevant tokens from SQL, vector DB, tools, MCP, web search, conversation history — don't miss anything
- Glean (maximize precision): remove irrelevant material; techniques in order: top-K → RRF → LTR → dedicated rerankers → LLM-as-gleaner
- "Cheating at search": using LLM to select relevant candidates outperforms algorithmic ranking for complex queries; small fast cheap models in parallel for gleaning pass
- Multi-probe gather: LLM generates query plan with 10-30 distinct probes simultaneously across structured + unstructured sources
- Long context does NOT solve the problem: Chroma technical report — performance drops precipitously at 10K tokens on non-trivial tasks; needle-in-haystack benchmarks are zero-reasoning tasks (bottom-left quadrant); real agent tasks are upper-right quadrant (attend to much context + high reasoning)
- Focus context (oracle-curated relevant material) dramatically outperforms full context
- Agent success cases in context: sometimes makes performance worse — agent "pattern-matches and gets lazy" and replays prior answer instead of reasoning; failure cases reliably help (agent escapes local minima)
- Compaction finding: OpenCode's compaction performs negligibly better than no compaction; "smarter compaction with a better prompt" significantly better — active open research problem

**Parahelp — mode-based context compaction:**
- Mode switch = structured compaction boundary: carry digest of prior mode's output, restart message history cache
- Sessions run 30-40 minutes without overflowing context because mode transitions enforce compaction at semantically meaningful points
- Each mode's toolset is scoped: Configure mode cannot run deep research; Testing mode cannot apply file diffs; tool scoping enforces mode integrity

**Skyvern (2026-05-19) — context as the variable:**
- "Agents produce slop primarily because they lack context, not because the underlying models are inadequate"
- New-hire analogy: agent without context = new hire who doesn't know the business, customers, history, priorities
- Good context operationally: company email + Slack + Notion + call recordings (correlate "this customer had this issue with this part of the product") + direct DB access ("this customer ran these jobs and these failures occurred")
- Remote-first structural advantage: all context is written/recorded by default; in-person companies generate context verbally and it evaporates
- Structural changes to make agents effective: ban DMs (all questions in public channel threads), record all calls (including co-founder one-on-ones), give agents access to all recorded content, give every employee an agent

---

### Memory Architecture

**Mem0 (2026-01-23) — production memory layer:**
- Three storage types on write: (1) key-value pairs for simple retrievable facts ("user prefers Airbnbs in New York"), (2) semantic chunks for richer unstructured content (vector similarity), (3) graph memory (knowledge graph capturing how facts connect)
- At query time: pull from all three stores simultaneously; low latency; inject only relevant subset into context (not full history)
- Memory decay modes: hard decay (discard all after N months), exponential decay (recent weighted higher), domain-aware decay (travel preferences always relevant; other categories decay normally)
- Customization: developer specifies in plain language what to capture and what to ignore; Mem0 interprets via LLM → extraction rules → reruns pipeline over existing memories to update
- Competitive moat: model-agnostic and framework-agnostic; memory is write (gives custody of user data to model provider if you use their memory layer); Mem0 developer owns the store
- Framework integrations: exclusive memory provider in AWS Strands SDK; also CrewAI, Flowise; one tool to add memory, one tool to search memory; memory travels with user, not with framework
- Three-phase vision: (1) make it work (current), (2) make it neutral (no lock-in to model/framework), (3) make it portable (memory travels across all user's AI apps — email/phone become identity; memory becomes next layer)
- Phase 3 analogy: "as AI interfaces shift from swipe/scroll/click to conversational/agentic, users will accumulate rich personal data across dozens of AI apps... expect any new app to already know them"

**Answer This — three explicit memory types:**
- Factual memory: codebase + DB snapshot (updated via cron on each release); agent reads ground truth at query time, not stale docs
- Behavioral memory: `instructions.md` — preferences, communication style, handling patterns, escalation rules; evolved through feedback loops; persists across sessions
- Procedural memory: recurring tasks encoded in auto-generated CLI tools

**Parahelp — memory files as policy substrate:**
- ~40 memory files per customer; organized by domain (billing, SSO, escalation, tone, product FAQ)
- Updates: Configure mode agent searches all files for relevant entries, identifies conflicts/gaps, applies diffs in staged mode for human review before commit; explicitly modeled on coding agent applying diffs to source files
- Knowledge ingestion pipeline detects changes from Linear, help center, Slack tags → assistant agent runs file-edit pass across affected files → proposes updates in draft mode
- Differentiation from workflow-based tools: policies encoded in natural language files, not directed graphs; when new edge case emerges, add policy to file (not new node in graph); pricing change affecting 3 files caught + updated in one session

**Mastra / Sam Bhagwat (2025-08-25) — LongMemEval-driven memory engineering:**
- LongMemEval: 500 questions across 5 categories testing distinct memory mechanisms:
  1. Single-session information extraction (simplest, not retrieval-dependent)
  2. Multi-session reasoning (retrieval across distributed history is bottleneck)
  3. Temporal reasoning (correct date presentation is bottleneck)
  4. Knowledge updates (targeted overwrite semantics in working memory is bottleneck)
  5. Absence awareness (returning nothing when nothing relevant; agent must say "I don't know")
- Mastra memory architecture: (A) semantic recall = embed all messages → PGVector/Chroma → top-K + message range context (like `grep -C N`), (B) working memory = template-driven attribute store, domain-specific schema
- Baseline: 67% vs. SOTA ~72%
- Change 1: LLM-generated tailored working memory templates per domain (personal trainer vs. legal research vs. customer support track different attributes)
- Change 2: targeted field-level updates instead of full document rewrite — LLM rewrites introduced errors in untouched fields; surgical overwrite of specific field only eliminates this
- Change 3: correct date presentation — benchmark conversations at historical dates, system was presenting wrong dates; fix improved temporal reasoning by "a couple of percentage points"
- Change 4: messages grouped by day with hour-level timestamps within each day group (not flat chronological list) — gives LLM affordances to identify session boundaries and temporal order
- Configuration is architecture, not tuning: top-K of 2 vs. 5 vs. 20 produces dramatically different results; single-session questions unaffected by top-K (don't need multi-session retrieval)
- ChatGPT identity failure: conflated Bhagwat's daughter's usage (5-year-old girl who loves Squishallows) with his own identity — failure of document-level rewrite semantics; field-level targeted updates prevent this
- Next roadmap: episodic memory (session-scoped summaries, middle layer between per-message and attribute-level) + reranking support, both measured against LongMemEval before shipping
- Framework value: every memory improvement propagates to all Mastra-based apps across all domains automatically

---

### HITL (Human-in-the-Loop) Patterns

**Trigger.dev (2026-05-09) — checkpoint-restore as HITL substrate:**
- Technical primitive: freeze complete state (CPU, memory, file system) → resume on different machine when external condition satisfied (human response, another agent output, API return)
- HITL as cost optimization: when task pauses waiting for human, Trigger frees the compute — no idle billing during review windows (can span hours)
- HITL as correctness: agent doesn't reconstruct prior context when human responds; full in-memory state preserved
- Developer interface: TypeScript async/await code; Trigger handles underlying pause/resume mechanics transparently
- Icon.com pattern: Phase 1 (context assembly runs while user uploads assets), Phase 2 (generation triggers when user specifies ad type), human-in-the-loop occupies the gap between phases — feedback provided, workflow resumes from checkpoint

**Parahelp — tiered HITL:**
- Default: autonomous execution for actions within policy bounds and confidence threshold
- HITL trigger: actions exceeding confidence threshold or policy boundary → Slack approval flow → billing manager sees short summary → clicks approve → agent resumes thread
- Progressive trust model: enterprise accounts graduated from 20-seat → 50-seat → 100-seat → 1,000-seat following same trajectory as new human hire
- The `validate` function layer prevents execution before HITL escalation decision

**Dex Horthy — code review as HITL:**
- Code review's primary purpose: maintaining shared mental alignment, not bug detection
- Team does not read every line of code; reads research files and implementation plans instead
- Tests = ground truth for correctness; plans = ground truth for intent
- Wrong line of code → 1 bug; wrong section of plan → hundreds of wrong lines; wrong assumption in research phase → thousands of wrong lines

**Jared Friedman — human at the edge:**
- Human role: interface with places AI cannot reach yet (in-person conferences, novel situations, ethical considerations, high-stakes emotional moments, sales)
- "It's where the founder comes to us and is thinking about breaking up with their co-founder. It's those real high-stakes, high-emotion moments where you really want a human being."
- Sales: "I think that's a human being in the room for the next 20 years."
- Two-role company: ICs (builders/operators) + DRIs (directly responsible individuals — one named human accountable for each thing, not a committee)
- Middle management eliminated: coordination absorbed by AI; AI should be doing it

---

### System Prompts and Behavioral Configuration

**Answer This — skills file concept (from Jared Friedman on YC monitoring agent):**
- Skills file = structured representation of what the AI agent knows how to do: what capabilities, what tools, what context, how to match query to right tool
- When monitoring agent identifies query failed because "we need to update the skills file" → adds new skill definition (not new code, but new knowledge about what agent can do and when)
- Skills file is agent's self-model; updating it is how agent learns new query types without retraining
- Capabilities represented declaratively (file agent can read and modify), not in model weights → self-improving without retraining

**Parahelp — memory files as system prompt substrate:**
- ~40 files replace static system prompt; loaded at query time based on relevance
- No system prompt with 5K tokens of generic policy; instead domain-specific natural language files that compose
- Ops manager can edit policy by chatting with Configure agent; no code required; change staged for review before commit

**Jared Friedman — Codex ephemeral software principle:**
- "Store all the data preciously. Treat the software as ephemeral."
- The valuable asset = data + "comprehension inside people's heads of how the function works" (encoded as skills, context, instructions)
- Software on top = implementation, regeneratable; data = irreplaceable
- Applications: generate internal tools from original instructions → throw away → regenerate when models improve in two months with same instructions

**Dex Horthy — CLAUDE.md as reviewed artifact:**
- "We basically test those for weeks before anyone's allowed to change them"
- System prompt = source; wrong line in CLAUDE.md causes wrong behavior across every agent session until fixed; gets more review attention than any individual code change

---

### Error Handling Paths

**Parahelp — validate-then-execute pattern:**
- validate() runs deterministic checks before tool side-effect commits
- Failure paths: (a) correct parameters → re-try, (b) escalate to Slack approval, (c) inform customer additional verification needed
- All three paths happen without the side effect executing

**Jake Heller / CoCounsel — "don't answer from prior knowledge" instruction:**
- Grounding instruction: "Don't answer based on any of your previously existing knowledge, just based on what I'm giving you right here. If this thing says the sky is purple, the sky is damn purple."
- Effect 1: prevents hallucination by anchoring to retrieved text
- Effect 2: makes retrieval failures visible — wrong answer while grounded = retrieval problem (not prompt problem)
- Separates two failure modes that are otherwise confounded

**Chroma / Huber — absence awareness:**
- Retrieval system must return nothing when nothing is relevant; agent correctly interprets null retrieval as "I don't know"
- 10-gallon / 20-gallon / 30-gallon tank example: retrieve the 10 and 20 (they exist), recognize 30 is absent, say "I don't have that information" rather than interpolate
- Requires both high recall (don't miss what is present) and high precision (don't over-retrieve loosely related content that causes hallucination of presence)

**WhyHungry / Siti (2026-05-19) — context as error prevention:**
- Autonomous bug-fixer: 60-70% one-shot fix rate (debated metric); fix rate stagnates or regresses without rich context (code history, system architecture, related files); improves with context
- Bottleneck: context-feeding pipeline is at least as important as code-editing capability

---

### Constants, Thresholds, Configurations

- Parahelp context window: sessions run 30-40 minutes; mode switch = compaction at semantically meaningful boundary
- Parahelp: ~40 memory files per average customer
- Parahelp: testing mode up to 25 parallel test executions (5 sub-agents × 5 tests each)
- Parahelp: variable execution 15 seconds (FAQ) to 3 minutes (complex enterprise debug with 15+ tool calls)
- Parahelp: mass follow-up: 700 simultaneous agent instances; requires Hatchet for queue management
- Answer This: 100+ emails/day, 400+ tickets closed, 45+ auto-generated CLIs
- Dex Horthy: 40% context utilization ceiling before intentional compaction
- Dex Horthy: 170K usable tokens in context window; fewer tokens per task = better quality
- Dex Horthy: progress file written to disk at 40% ceiling; new agent reads file as onboarding → skips full re-discovery phase
- Chroma: performance degrades dramatically at 10K tokens on non-trivial recall tasks (technical report finding)
- CoCounsel: 10 → 50 → 100 → 1,000 eval test cases; release condition = 999/1,000 passing (99.9%); at 6/10 passing most teams stop — keep going
- CoCounsel: RF-tuning requires maximum 50-100 examples + objective quality judge function; gains "go a really long way" vs. supervised fine-tuning needing thousands of examples
- Mastra: top-K of 2 vs. 5 vs. 20 produces dramatically different retrieval quality; configuration is architecture
- Mastra: baseline 67%, SOTA ~72%, reached SOTA through 4 targeted changes
- Skyvern: PRD pipeline calibration cycle — team called it "slop" until pipeline tuned to "actually I'll use this to draft my feature"
- Trigger.dev: 90%+ of current usage is agentic workflows (vs. back-office batch jobs in 2023)
- Phone AI: 80% of callers don't know they're talking to AI (April 2026); latency is now "oxygen" — hygiene not differentiator; active frontiers: endpointing, phone audio transcription (8kHz, compressed, noisy), edge cases
- Jared Friedman: 5x revenue-per-employee at YC Demo Day vs. 18 months prior; token usage as leading indicator of frontier exploration (not a performance metric)

---

### Multi-Agent Coordination

**Parahelp — coordination primitives:**
- Four-mode assistant: Ask / Configure / Testing / Deep Research as distinct agents sharing session context; mode transitions self-initiated by assistant
- Mass follow-up: research agent identifies category → support manager approves → 700 agent instances spawned simultaneously each with own conversation thread
- Testing mode: up to 5 sub-agents with 5 tests each = 25 parallel test executions; sub-agents generate YAML + mock context + run proposals
- Deep research: research agent issues semantic search → spawns sub-agents to open 50-500 full ticket texts → sub-agents produce structured findings → research agent aggregates
- Context budget decision made at multi-agent coordination level (50-500 tickets per sub-agent based on relevance density)

**Conductor (2026-05-08) — multi-agent orchestration layer:**
- Architecture: git worktrees (not clones) as isolation primitive — shares git object store, cheap to create, low disk overhead; each worktree = separate branch = separate agent
- Interface bottleneck: human working memory caps at 3-5 concurrent agents; next abstraction = CEO-layer that aggregates status, surfaces exceptions, handles routine coordination
- "CEO of a megacorp" interface: engineer sees high-level summaries, drills into PR-review level detail only when needed
- "Slop-free zones": certain codebase areas where human is architect (every AI contribution carefully reviewed); other areas AI runs freely
- Best engineer patterns from field research: (1) invest heavily in CLAUDE.md/skills files — highest-leverage config investment; (2) simple and vanilla setups outperform elaborate configurations; (3) proactive not reactive — think through design questions agent will face before dispatch, pre-load context and constraints
- Code review bottleneck: "stuck in the 2010 GitHub PR review era" — even with parallel agents, every output requires careful line review; PR review redesign is major open product problem
- Conductor Cloud: agents persist when laptop closed; cloud env = organizational unit of work; enables access from phone/laptop/existing cloud infra
- Series A: $22M from Spark Capital and Matrix; 10x growth Jan-May 2026

**Jared Friedman — organizational multi-agent:**
- Product analytics loop: agent finds highest-friction funnel point → researches best practices → designs A/B test → runs for a week → picks winner → deploys → repeats
- Customer feature loop: customer suggestions arrive → triage agent (CPO/CTO judgment) → discard or write code → deploy → ship to customer — no human
- Multiple agents coordinating via recorded artifacts (shared data store), not real-time messaging

**Skyvern / Sachin — adversarial sub-agent pattern:**
- After drafting PRD: dedicated adversarial review sub-agent reads it and generates critique
- Then RICE prioritization (Reach, Impact, Confidence, Effort) to eliminate junk requirements
- Adversarial reviewer as standard pipeline stage, not occasional checkpoint

**Trigger.dev — agent-as-queue-subscriber pattern:**
- Trigger is not an orchestrator; it is the execution substrate and queue layer below the orchestrator
- LangChain/CrewAI/custom loops run on top of Trigger; Trigger handles reliable execution, retry, checkpoint-restore that orchestrators don't provide
- Scrapybara full coding agent pipeline: clone repo → evaluation loops → LLM modifies code → commit → push — entire pipeline as single long-running Trigger task

---

### Streaming Protocol

**Trigger.dev:**
- TypeScript SDK; pause/resume mechanics transparent to developer via async/await
- Checkpoint-restore: freeze complete state (CPU, memory, file system) → resume on different machine
- Human review window: compute freed during pause (no idle billing); restored from checkpoint when human responds
- Scrapybara pattern: long-running Trigger task (no streaming to user; background execution)

**Phone AI:**
- Custom LLMs on Groq (fast inference hardware); latency is "oxygen" — must be below perceptible delay in voice
- Pipeline of smaller models per component running on fast inference hardware; each independently updated
- Phone audio challenge: 8kHz sample rate, codec compression, packet loss, environmental noise — systematic degradation from studio-quality ASR assumptions

**Salient:**
- 400,000 dials/day via vLLM on Llama 2 (open weights); "vLLM allowed anyone like us to grab one of these Llama models, serve it up to millions of requests per minute"

---

### Eval Infrastructure

**CoCounsel / Jake Heller — per-prompt eval discipline:**
- Per-prompt eval suite: write best-guess prompt → write 10 test cases (context, expected correct output) → run all 10 → most teams stop at 6/10 and conclude "AI is stupid" — keep going until 10/10
- Expand: 10 → 50 → 100 → 1,000; 1,000-test suite must come from actual users, not developer imagination
- Real-world test input source: run small beta, tell customers it will be bad, ask for every failure → each reported failure = test case
- Release condition: 999/1,000 passing and the one remaining case is "kind of debatable"
- Eval tools: Prompt Fu (free, open source, CLI) and Vellum (commercial)
- Single-token output trick for classification steps: format so answer token comes first; use stop words or max_tokens=1 to cut after first token; model "thinks" it's about to give full explanation → deliberates more → single token carries that deliberation; 200x latency reduction for classification steps in high-volume pipelines
- Reinforce fine-tuning > supervised fine-tuning: 50-100 examples + objective quality judge; "hardest part is creating the objective quality judge"

**Parahelp — eval as core engineering investment:**
- "Probably engineering-wise the most time building internally" on evaluations
- Every ticket processed = implicit eval data point; monitoring layer flags anomalies in resolution rate, escalation rate, tool-call accuracy continuously
- Opus 4 unlock: first model intelligent enough to generate eval sets on the fly (look at past tickets, identify patterns, construct test cases covering edge cases) — since launch, no custom eval set has been written manually
- YAML test case format in internal eval framework; mock context system (enterprise tier, active outage, subscription state) requires tight coupling between eval runner and integrations layer
- Testing mode generates + runs + iterates until all proposed policy cases pass before surfacing "publish" suggestion

**Mastra — benchmark-driven memory engineering:**
- LongMemEval as feedback loop: treat benchmark as tight engineering loop not one-time measurement
- Category decomposition: group questions by mechanism because a change that improves one mechanism may have no effect on another (top-K change moves multi-session but not single-session scores)
- "Write an eval scaffold and then just iterate a lot" — eval generates data that reveals "odd weird things you can do to present information in a clearer and easier to understand format for the LLM"

**Skyvern:**
- PRD pipeline calibration: send drafts to team → they call it "slop" → tune pipeline → repeat until "actually I'll use this to draft my feature"
- Calibration loop (not initial prompt) is what made the pipeline useful

---

### Framework Design Lessons (directly Verso-relevant)

**The thin harness finding (Answer This, Parahelp, Conductor, Trigger.dev):**
- Multiple independent practitioners converged on: thin harness over coding-capable agent + first-class tool registry + writable memory file + task queue
- "Pete, Tom, and Gary had already explained why a thin harness over a coding-capable agent is architecturally correct" — established as consensus at same YC event
- Elaborate configurations don't translate to more output; best engineers use simple vanilla setups

**ReAct vs. plan-execute (Dex Horthy, Jake Heller):**
- Dex Horthy: Research → Plan → Implement is better than ReAct for brownfield codebases; Plan phase = explicit spec that human reviews before implementation
- Jake Heller: decide per-task whether best human does it linearly (implement as sequential functions) or agentically (needs loop-back); never default to agentic
- Parahelp sampling-over-chains: multiple parallel ReAct traces + judge model to select best path; test-time compute scaling for tool-use reliability

**Context budget over model size (Chroma, Dex Horthy, Skyvern):**
- Context quality is THE variable; model capability is not the bottleneck in most production failures
- "LLMs are pure functions. The only thing that improves the quality of your outputs is the quality of what you put in." (Dex Horthy)
- Chroma: focus context (curated relevant material) dramatically outperforms full context even with million-token windows available

**Documentation as context window engineering (DevTool panel, 2026-05-14):**
- "Documentation is a context window engineering problem" — documentation company panelist
- Old docs: extensive exposition, multi-page tutorials, deeply linked cross-references
- New docs: restructured to fit inside a coding agent's context window in a single load; measurably improved agent accuracy and reduced mistakes
- Agents attending to single coherent document maintain accurate context; multi-page navigation loses coherence at each navigation step
- "If you are being recommended by Claude and Gemini and ChatGPT, you're in a great place" — model-recommendation has replaced or is replacing traditional marketing channels

**Memory neutrality principle (Mem0):**
- Memory is write: writing to model-provider memory = giving custody of user relationship data to provider
- Verso implication: memory layer must be provider-agnostic; memory travels with user not with model or framework
- Three types needed: key-value (facts), semantic (rich content), graph (relationships between facts)
- Decay must be configurable: hard / exponential / domain-aware

**Tool trust, not just tool calling (Parahelp, Phone AI):**
- "Tools sound pretty trivial to set up... but then as you dive in you find out that tools are way more than just calling the API endpoint. It's having the proper guardrails"
- Validate-before-execute is a first-class primitive, not an afterthought
- Tool reliability = validate function + eval suite per tool + mock context for testing

**The skills file / CLAUDE.md as first-class infrastructure (Conductor, Jared Friedman, Dex Horthy):**
- Highest-leverage configuration investment for any agent system
- Skills file = agent's self-model; capabilities represented declaratively (modifiable without retraining)
- CLAUDE.md: tested for weeks before anyone allowed to change it; wrong line causes wrong behavior across all sessions
- Self-extending architecture: monitoring agent watches for failures → identifies which skill needs update → updates skills file → agent can handle new query type overnight

**Compaction as engineered boundary, not background process (Parahelp, Dex Horthy):**
- Parahelp: mode transition = structured compaction trigger; developer-controlled, not automated
- Dex Horthy: `/compact` = "trash"; intentional compaction via authored progress file
- Chroma: OpenCode compaction negligibly better than no compaction; "smarter compaction with better prompt" significantly better
- What to preserve: goal / accomplishments / files touched + specific changes / what failed and why / next steps / constraints established / key design decisions

**Evals before launch, not after (Jake Heller, Mastra, Parahelp, Skyvern):**
- Eval suite per micro-step (not per product) is the unit
- Most teams stop at 6/10 — keep going
- Real-world inputs required (imagined test cases miss how actual users send queries)
- Benchmark grouped by mechanism: a change that improves one mechanism may have zero effect on another

---

## → Verso Implications

- **Build a first-class thin-harness template.** Multiple independent practitioners at production scale converged on: thin Python/TypeScript harness + Claude Code/coding-capable agent + task queue + writable instructions file + tool registry. Verso should make this the canonical "simple agent" pattern, not an advanced use case.

- **`validate()` on every tool, always.** Parahelp's finding that tool trust requires deterministic pre-execution checks (not just LLM judgment) applies to any production agent. Verso should expose a validate hook as a first-class tool API slot — not optional middleware.

- **Memory must be triadic with configurable decay.** Mem0's production architecture (key-value / semantic / graph + hard/exponential/domain-aware decay) is the right model. Verso's memory layer should support all three storage types and all three decay modes, provider-agnostic.

- **Compaction is a developer-controlled boundary, not background magic.** Dex Horthy's authored progress-file pattern and Parahelp's mode-transition-as-compaction-trigger both show that compaction must be engineered with author control over what is preserved. Verso should expose a `compact(spec: CompactionSpec)` primitive rather than auto-summarizing.

- **Keep context utilization under 40%** (Dex Horthy) — Verso's runtime should expose a context utilization metric and emit a warning or trigger a configurable handler when threshold is approached. Default threshold: 40%.

- **Skills file / agent self-model as first-class artifact.** The monitoring-agent → updates-skills-file → agent-gains-new-capability-overnight pattern (Jared Friedman YC internal) is extremely high value. Verso should support a declarative capabilities manifest file that agents can read and write, enabling self-extension without retraining.

- **Evals as infrastructure, not afterthought.** Jake Heller's "10 → 50 → 100 → 1,000 test cases per micro-step; release at 999/1,000" and Mastra's "write an eval scaffold and iterate" both show evals are the feedback loop that drives quality. Verso should ship with a built-in eval harness (per-tool, per-pipeline-step) rather than assuming users will wire their own.

- **Plan phase as HITL boundary.** Dex Horthy's Research → Plan → Implement pattern inserts a human review gate at the Plan level — a lightweight, human-readable artifact reviewed before any code runs. Verso's HITL interface should support this "review the plan, not the code" pattern. The plan is the primary reviewable artifact; the implementation is the compiled output.

- **Sub-agents for context control, not task decomposition.** Parahelp and Dex Horthy both use sub-agents primarily to avoid consuming the parent's context budget on search/discovery. Verso's sub-agent API should make this pattern explicit: `dispatch_sub_agent(task, return_format: StructuredSummary)` rather than a generic fork.

- **Multi-probe gather as standard retrieval pattern.** Chroma's finding that 10-30 parallel probes across structured + unstructured sources dramatically increases recall maps directly to Verso's tool system. Verso should provide a `gather(probes: Probe[])` primitive that issues all probes in parallel and returns a ranked candidate pool for downstream gleaning.

- **Do not auto-recommend "agentic" for every task.** Jake Heller's rule: if the best human would do it linearly, implement it linearly. Verso's framework should distinguish `pipeline` (linear, predictable, debuggable) from `agent` (loop-back on failure, dynamic branching) as first-class abstractions — and default to pipeline for deterministic tasks.

- **Mode-based agent as production pattern.** Parahelp's four-mode assistant (Ask / Configure / Testing / Deep Research with distinct prompts + scoped tool sets + self-initiated transitions) shows that structured mode switching with tool scoping is superior to a single universal agent. Verso should support multi-mode agent definitions with per-mode tool scopes and context compaction on mode transition.

- **Long context is not a substitute for context selection** (Chroma). Performance degrades dramatically at 10K tokens on non-trivial tasks even with 1M-token windows available. Verso should encourage (and provide tooling for) selective context assembly rather than "dump everything in."

- **Agent success cases in memory can hurt performance** (Chroma). Past failure cases reliably help; past success cases sometimes cause pattern-matching laziness. Verso's memory design should allow users to configure whether successful episodes are stored at all, and to distinguish failure-case memory from success-case memory.

- **Documentation for agents = single-context-window fit.** Verso's own docs and any generated integration docs should be structured to fit in a coding agent's context window in a single load. Multi-page cross-linked docs actively degrade agent accuracy on integration tasks.

- **The spec is the source; the code is the compiled artifact.** (Dex Horthy / Sean Grove) Verso should treat prompt specifications and pipeline plans as first-class versioned artifacts, not ephemeral session content. Committing the code without storing the spec that produced it is equivalent to committing a compiled binary without the source.

- **HITL checkpoint-restore is a cost optimization, not just a safety feature.** Trigger.dev's model (free compute during human review window; restore from checkpoint on response) enables HITL without idle billing. Verso's durable execution escape hatch should implement checkpoint-restore semantics with compute release during pauses.

- **Token usage per person as a proxy for frontier exploration, not productivity.** (Jared Friedman) Verso's analytics / observability layer should expose token usage per agent/session/user as a leading indicator of exploration breadth — not as a performance metric, but as a directional signal about which agents are operating at the frontier.
