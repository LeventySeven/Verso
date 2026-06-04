# Transcripts — DeepLearning.AI (technical agent talks)

Source file: `/Users/seventyleven/Desktop/researchfms/core/TRANSCRIPTS_DEEPLEARNINGAI.md`
Coverage: AI Dev 25 x NYC + AI Dev 25 — 49 talks, October 2024–April 2025

---

## TRANSCRIPTS_DEEPLEARNINGAI.md

### Agent loop shape

- **Anthropic / Tanveer Mittal (AI Dev 25 x NYC):** Canonical agentic loop: (1) receive task, (2) reason and plan, (3) take action via tool calls, (4) receive tool results, (5) reflect on feedback, (6) determine next step, repeat. Simplest implementation: `while True:` with tool calls chained. The loop itself is NOT the differentiator — the feedback pillar is. Most developers over-optimize action tools, under-invest in observability tools that let the agent self-correct.
- **AWS Strands / Nicholas Clegg (AI Dev 25 x NYC):** Formal definition — model-driven agent = LLM + tools in a loop; on each iteration, LLM either calls a tool (add result to context, loop) or emits a final answer (exit). No hardcoded transitions. Path is entirely model-determined. Contrast with workflow agents: those require developer-maintained state machines.
- **Genspark / Kay Zhu (AI Dev 25 x NYC):** Killed 5M-user fixed-workflow RAG product to replace with an LLM-in-while-loop agent engine. Fixed workflows fail on edge cases and accumulate errors; agent engine recovers from previous errors and replans. Key design principle: "less control, more tools."
- **AI21 Maestro / Ori Goshen (AI Dev 25 x NYC):** Research paper finding: as number of constraints passed to an agent exceeds 20–40, success rate drops dramatically even with SOTA models. Maestro's solution: structured plan generation → per-step multi-strategy execution → validator/reducer at each step. Not pure ReAct — a plan-then-validate architecture with parallel strategy execution per step.
- **CrewAI / João Moura (AI Dev 25 x NYC):** Production pattern is NOT pure agency or pure flow. "Agentic systems = deterministic backbone + variable agency per step." Example: user message → LLM intent classifier → if simple: generate; if complex: kick off full multi-agent crew → synthesize. KISS: don't use an agent if a single LLM call handles the task.
- **Haystack / Bilge Yücel (AI Dev 25):** Agent component implements ReAct-style loop. Exit conditions are a first-class primitive: `exit_conditions=["tool_name"]` — agent terminates when a designated "finalization" tool is called. This is more reliable than model-determined exit (which can loop or stop prematurely).
- **Google ADK / Bill Jia (AI Dev 25):** ADK agent loop — assemble prompt (system + history + tool schemas) → Gemini API call → if text: return; if function call: execute (tool or sub-agent), add result to history, loop. Sub-agents run fully isolated loops; orchestrator sees only the final response, not intermediate reasoning.
- **Kimi K2 / Alex Ker (Baseten, AI Dev 25):** Interleaved thinking: standard chain-of-thought does all reasoning upfront, then sequential tool calls with no re-reasoning. Kimi K2 interleaves reasoning after EACH tool call: `reason → call_1 → reason_about_result → call_2 → reason_about_result → ...`. Enables mid-flight strategy revision. Demonstrated: 23 interleaved cycles to solve a PhD-level geometry problem. 200–300 continuous tool calls while maintaining coherence.
- **Panel / Mikhail Parakhin (Replit, AI Dev 25):** Autonomy level L2.5–L3. Bottleneck is NOT codegen quality (LLMs sometimes better than average human at codegen). Real work is everything around codegen: debugging infrastructure, rollback, error detection, environment config, migration, deployment. Replit one-click rollback is more valuable than the LLM.

### Models (name, provider, role)

- **Anthropic three-tier:** Haiku = high-volume/low-complexity (classification, extraction); Sonnet = production workhorse (balanced intelligence/cost); Opus = top-quality (hardest tasks, stuck-agent recovery). Routing implication: production systems should route trivial steps to Haiku, main reasoning to Sonnet, difficult decomposition to Opus.
- **Sonnet 4.5 benchmarks:** SWEBench 80%+. Supports 30-hour continuous coding sessions (up from ~7 hours on earlier models). ~4x improvement in sustained agentic trajectory length. SWEBench is logarithmically scaled — 1% at high end > 5% at low end.
- **Haystack demo:** `claude-3-7-sonnet-20250219` as the agent brain in a GitHub issue resolver. Exit on specific tool call (write_github_comment).
- **Vercel AI SDK / Aayush Kapoor (AI Dev 25 x NYC):** Provider-agnostic. `generateText({ model: openai('gpt-4o') })` and `generateText({ model: anthropic('claude-sonnet-4-5') })` identical except model param. 30+ providers supported via same function signatures.
- **Genspark MoA:** Layer 1: query sent simultaneously to all frontier models (GPT-4o, Claude 3.5/4, Gemini 1.5/2, inferred from context). Layer 2: aggregator LLM reads all outputs including reasoning traces, synthesizes final answer. Hallucination reduction via ensemble reasoning — if models A and B independently reach the same fact via different reasoning paths, strong evidence it's correct.
- **Kimi K2 architecture:** 1-trillion-parameter MoE. Larger vocabulary = more experts. Fewer attention heads per expert. Trained on 3,000 real GitHub tools + 20,000+ synthetic variants per category. Training data = full trajectories with interleaved reasoning-before-and-after each tool call. MCP servers explicitly included in training data.
- **GLM 4.6:** 30% more token-efficient than GLM 4.5 — outputs same reasoning quality in 70% of the tokens. Baseten measured 167% throughput increase + 5–7x cost reduction vs Claude Sonnet when routing Claude Code to GLM 4.6 via LiteLLM.
- **Meta Llama 3 family:** 1B/3B = on-device and single-function agent roles; 8B = fine-tuning experiments; 70B = production workhorse; 405B = max intelligence + distillation source + synthetic data generation. Observed developer path: start with 1B/3B/8B to find recipe, then 70B for production.
- **Gemini 2.0 Flash:** 1M token context window (10M in research). $0.075/M tokens for Flash-Lite. Multimodal inputs: video, images, audio, text, code, full repos simultaneously. Multimodal outputs: text, code, images, audio. Flash-Lite on-device in Chrome Canary (Gemini Nano).
- **Groq LPU:** 10–40x faster inference than GPU-based providers. SRAM-based (not HBM). Kernelless compiler. 10 data centers globally. Model IDs: `groq-compound` (parallel tool calls), `groq-compound-mini` (sequential). Built-in server-side tools: web search, code execution, browser automation. No client-server round trips for tool calls — tool execution is co-located with model.

### Full tool registry (names, params, returns, schemas)

**Vercel AI SDK tool definition pattern:**
```typescript
tools: {
  toolName: {
    description: "...",    // most important: LLM reads this to decide whether to call
    parameters: z.object({ // Zod schema → TypeScript types on execute args
      param1: z.string().describe("..."),
      param2: z.number()
    }),
    execute: async ({ param1, param2 }) => { ... }  // any async function
  }
}
```
- **`stopWhen: stepCountIs(N)`** — budget parameter; allows N steps for self-correction. Without this, agent makes one tool call and reports whatever it found.
- Parallel tool calls: when model determines two calls are independent, it generates both in the same LLM step; SDK executes concurrently. Verified in `steps[0].toolCalls`.

**Strands SDK (AWS) tool definition:**
- Decorate any Python function with `@tool`. Strands reads signature + docstring → tool schema. Docstring quality directly determines LLM tool selection quality.
- `agent.messages` = JSON list of message objects, directly mutable. Escape hatch: inject messages from external sources, truncate history, add memory summaries.
- **Agent as a tool:** wrap sub-agent as callable. Demo measured: parent context = 2,700 chars; sub-agent (web search) context = 15,000 chars. 82% reduction in parent context. Generalization: any verbose tool (web search, bash exec, large file read) should be wrapped in a sub-agent that summarizes before returning.

**Haystack ComponentTool auto-generation:**
```python
@component
class SearchDocuments:
    """Search documents in the knowledge base.
    :param query: The search query.
    :param top_k: Max results. Default 5.
    """
    @component.output_types(documents=list[Document])
    def run(self, query: str, top_k: int = 5) -> dict: ...

search_tool = ComponentTool(component=SearchDocuments())
# name, description, parameter schema auto-generated from class name + docstring + type annotations
```
- No boilerplate tool schema. Tool quality = docstring quality.

**Strands Swarm (peer delegation):**
- Swarm class injects `handoff_to_agent` tool into each agent's tool set.
- Each agent's context includes descriptions of all peers — enables autonomous peer discovery.
- Baton-passing: each handoff carries accumulated context + task status.
- No external orchestrator; each agent decides when to hand off.

**Strands meta-agent:**
- Parent has `use_agent` tool with params: `model_name`, `tools_list`, `prompt`.
- Parent dynamically constructs sub-agents at runtime. Best for open-ended tasks (deep research) where solution path is unknown at design time.

**Box MCP tool design principle:**
- Task-oriented, not API-endpoint-oriented. `get_markdown_from_file` wraps 5 underlying API calls. Anti-pattern: 1:1 mapping of API spec to tools.
- Narrower tool set per agent → more reliable tool selection. Too many MCP servers available → selection confusion.

**SAP knowledge graph + 3 broad tools for 110,000 endpoints:**
```
Tool 1 — Discover APIs: embed user query → nearest-neighbor search → return top-K candidate APIs + process context from KG
Tool 2 — Retrieve API Specification: query KG for full spec (ORD metadata + OpenAPI + business process context)
Tool 3 — Execute API: make actual HTTP request to SAP system
```
- Agent always has exactly 3 tools regardless of whether system has 100 or 110,000 APIs.
- The complexity is absorbed by the knowledge graph.
- MCP current limitation: static tool registration cannot scope dynamically by user intent — enterprise-scale requires broad-tool pattern with KG mediation.

**Datadog MCP self-optimization loop:**
1. Run evals → low score on capability X
2. Claude Code + LLM Observability MCP → analyze failing traces
3. Claude Code proposes diff to tool description
4. Apply diff, restart server, rerun evals
5. Score improves
- MCP tools re-discovered on every agent session init (`list_tools`). Can change tool descriptions, preprocessing, consolidate tools without versioning — agents adapt automatically next session.

**Deep research agent (Vercel AI SDK, complete implementation):**
- `generateSearchQueries(query, breadth)` → `generateObject` with schema `{queries: string[]}` → breadth sub-queries per level
- `searchWeb(query)` → Exa `searchAndContents` with `numResults:5, useAutoprompt:true, type:'neural'`
- `searchAndProcess(originalQuery, searchQuery)` → `generateText` agent loop with `stopWhen: stepCountIs(10)` + two tools: `searchWeb` and `evaluate` (enum classifier: `relevant|irrelevant`)
- `generateLearnings(query, results)` → `generateObject` with schema `{learnings: string, followUpQuestions: string[]}`
- `deepResearch(query, depth, breadth, accumulated)` → recursive: each level generates sub-queries, processes them, extracts learnings, enriches query for next level
- `generateReport(accumulated)` → `generateText` with structured system prompt

### Context assembly / compaction / budgets

- **Genspark append-only context:** Never reorganize conversation history by relevancy. Append-only means prefix (system prompt + prior turns) is identical every turn → maximizes prefix cache hits. Cost math: 80%+ cache hit rate → effective price = 80%×10% + 20%×100% = 28% of full price (3.6x savings; Genspark claims 5–10x by including system prompt computation). Framework abstraction danger: LangChain/LlamaIndex can silently add whitespace, metadata, or reorder messages → invalidates entire cache prefix. Custom scaffolding gives byte-level control.
- **Genspark compaction threshold:** 70–80% context window utilization triggers compaction. This is not at 100% — the 20–30% buffer provides headroom. Compaction = second LLM call summarizes prior important points → replaces detailed history with compact summary → continues with: [system prompt] + [compacted summary] + [recent turns]. Rarely triggered, not per-turn.
- **Genspark context isolation:** Sub-agent runs in own isolated context window. Its working memory (tool call chains, intermediate outputs) does not pollute super-agent context. Linear context preferred over distributed parallel states — synchronization overhead ("thinking sync") outweighs parallelism gains.
- **Anthropic Files API:** Upload files once, reference across multiple conversations. Combined with Code Execution tool: CSV → analysis code → execute → charts → presentation. Stateful scratchpad + compute-in-the-loop.
- **MongoDB memory creation trigger:** At 75% context window utilization. After creation, compact conversation history. Why 75%: leaves 25% for next generation step + tool results. Too early wastes capacity; >90% risks overflow before memory creation LLM call completes.
- **CodeRabbit token optimization:** Baseline (diff only) = 17,000 tokens, bug not found. Brute force (all connected code, JSON) = 110,000 tokens, bug found. Optimized (outside-diff impact slicing, XML tags) = 18,300 tokens, bug found — same accuracy as 110,000 tokens. 6x token reduction by including only callers/callees with direct contracts, not all files connected by any reference. XML-style tags over JSON: better training data coverage, fewer structural tokens, more robust in long-context (human-legible anchors like `<outside_diff_impact>`).
- **Context engineering definition (CodeRabbit / Loker):** The discipline of designing and dynamically assembling the information an LLM needs to perform a specific task at domain-expert quality. Distinct from prompt engineering (instructions). Context engineering = the information environment the model reasons within. Senior engineer analogy: before reviewing a PR, they clone the repo, read docs, check history, understand what the PR was supposed to accomplish, look at how changed code is used elsewhere. Context engineering automates all of that.
- **Context engineering (Neo4j / Macklin):** 5 techniques: (1) RAG + hybrid search + reranking + contextual chunking; (2) memory management (sliding window, summarization, episodic, global state); (3) structure/ordering — Anthropic guideline: most relevant info at top, consistent delimiters, fixed templates for memory vs query sections; (4) tools + function calling — offload heavy compute to tools, give LLM a query tool instead of dumping raw data table; (5) knowledge graph augmented context — explicit relationships traversable, no probabilistic retrieval for structured domain knowledge.
- **Anthropic context assembly guidance (from multiple talks):** Place most relevant information at the top of long prompts. Models pay disproportionate attention to beginning of context. Use consistent delimiters (`[TOOL RESULT: tool_name]`). Fixed templates for memory vs new query sections.

### Memory (what persists, TTLs, backends)

**Complete memory taxonomy (MongoDB / Apoorva Joshi, AI Dev 25):**
- **Short-term / working memory:** LLM context window. Already in most apps. Breaks as session length and task complexity grow.
- **Long-term semantic memory:** LLM weights (frozen, built-in) + external databases for domain-specific knowledge (RAG knowledge bases). External DB is required — weights are not updatable at inference time.
- **Long-term episodic memory:** Sequences of actions taken to complete tasks. Schema: `{task_name, task_description: "natural language description of action sequence", outcome, error_encountered}`.
- **Long-term procedural memory:** LLM weights (built-in) + agent code (execution flow constraints) + **agents can modify their own system prompts** — if user provides instructions, agent can update system prompt to incorporate them, persisting for future calls.
- **Sensory memory:** Not applicable to current AI agents.

**Creation:**
- When to create: context at 75%, end of session, after X turns, scheduled (nightly), explicit user save.
- Raw ingredients are NOT memories: extract specific insights — character traits, action sequences, error resolutions, user instructions — not every detail.
- Persist to external DB: without persistence, memories die at session end.
- Always include `created_at`, `updated_at` timestamps — enables recency decay, eviction, priority ordering.
- Procedural memories (system prompts): single source of truth, updated in place, versioned.

**Retrieval:**
- When to retrieve: application-specific. Simulations = before every action. Code agents = only on error. Computer-use = during initial planning.
- Techniques: exact match, vector search, hybrid (BM25 + vector), reranking with composite score.
- **Composite scoring formula:**
  ```python
  composite = (
      0.5 * vector_similarity +
      0.3 * math.exp(-age_days / 30) +  # recency decay, 30-day half-life
      0.2 * importance_score             # LLM-generated at creation time
  )
  ```
- Importance score generated once at creation (not at retrieval — avoids latency + LLM call per retrieval). Pre-compute and store.
- Initial retrieval: top-50 candidates by vector similarity → composite re-score → threshold filter → top-K selected.

**Update / Delete:**
- Update = retrieve relevant existing memories + compare with new info + reconcile conflicts (prefer newer) + write back.
- Deletion strategies: move unused memories (no access in 90 days) to archival storage; hard delete after retention period. MongoDB TTL index: `expireAfterSeconds=90*24*3600` on `last_accessed` field handles automatically.
- Logs ≠ memories: logs = store everything for debugging. Memories = extract specific insights for real-time retrieval.

**Anthropic emergent memory behavior:** Claude 4 models, with minimal prompting, spontaneously adopted structured hierarchical memory in Claude Plays Pokemon: one file per town, per gym, per puzzle, per route. Claude 3 created monolithic flat markdown file. This emergent organizational behavior used as research signal confirming genuine model improvement.

**Skills (Anthropic):** Open-source framework. A collection of files (prompts + example scripts). Procedural memory: agent completes task → writes Skill encoding the steps → future instances replay procedure without re-deriving. Program synthesis analogy. Claude Agent SDK is identical harness used internally for Claude Code.

**CrewAI memory:** Short-term (in-context), long-term (cross-session), entity memory (specific entities over time). Backends: RAG or Graph RAG. Early implementations "naive" — flat vector DB, no expiration, no entity disambiguation. Current direction: Graph RAG where entities become nodes, relationships become edges, retrieval follows graph paths.

### Verbatim / near-verbatim system prompts

**Haystack GitHub agent system prompt (structure, not verbatim — "very long"):**
- Instructions for how to navigate GitHub repos using `GitHubRepositoryViewer` and `GitHubIssueCommentor` tools.
- When to use viewer (explore codebase) vs commenter (submit final answer).
- Format requirements: output in Markdown suitable for GitHub comments.
- Structure fix proposals as numbered approaches with code snippets.
- Stop after calling `write_github_comment` once.
- Available in public Haystack GitHub repo.

**Vercel AI SDK deep research agent prompts (verbatim from demo):**
```
# generateSearchQueries:
"Generate {breadth} specific, distinct search queries to research this topic comprehensively:
Topic: {query}
Requirements:
- Each query should target a different aspect or angle of the topic
- Queries should be specific enough to return focused results
- Avoid overlap between queries"

# searchAndProcess:
"Research query: {searchQuery}
Use the searchWeb tool to find relevant information about this query.
Then use the evaluate tool to assess whether the results are relevant to: {originalQuery}
If results are irrelevant, search again with a refined query."

# generateReport system prompt:
"You are a research analyst writing a comprehensive report.
Structure the report clearly with:
- Executive summary
- Key findings by topic
- Evidence and sources for each finding
- Gaps and areas for further research"
```

**Arize eval prompt (original + meta-prompt improved version):**
```
# Original:
"You are an evaluation assistant evaluating questions and tool calls
to determine whether the tool would answer the question.
Question: {input.value}
Tool called: {tool.name}
Tool result: {tool.result}
Does this tool call correctly answer the user's question?
Answer with ONLY 'correct' or 'incorrect'."

# Meta-prompt improved version (structure):
"A tool call is CORRECT if:
- The tool called is the right tool for the task
- The tool was called with appropriate parameters
- The tool's output contains information that answers or progresses toward answering the question
A tool call is INCORRECT if:
- A different tool would have been more appropriate
- The tool produced an error or empty output
- The tool's output does not address the user's question
Respond with ONLY 'correct' or 'incorrect'."
```

**MongoDB memory extraction prompt (reconstructed):**
```
"Review the following conversation excerpt and extract memories worth persisting.
Only extract information that would be useful to know in future conversations.
Do NOT extract every fact mentioned — only important, reusable insights.
For each memory, determine:
1. Memory type: semantic, episodic, or procedural
2. Content: concise statement of the memory
3. Importance: 0.0-1.0 score (0=trivial, 1=critical)
Return a JSON array of memory objects."
```

**MongoDB importance scoring prompt (reconstructed):**
```
"Rate the importance of this memory on a scale of 0.0 to 1.0 for future retrieval.
0.0 = completely trivial (agent confirmed understanding of routine task)
0.5 = moderately important (user mentioned preference affecting recurring task)
1.0 = critically important (user provided constraint that must never be violated)
Respond with ONLY a number between 0.0 and 1.0."
```
Note: this is an exception to the "no numeric scores" rule because it's anchored with examples, used for sorting not binary classification, and computed once at creation time.

### Error handling paths

- **AWS Strands core principle:** Informative error messages are NOT developer UX — they are the primary self-correction mechanism. Without descriptive errors, model cannot reason about what went wrong and cannot decide next step. This is the key engineering investment that makes model-driven agents work.
- **Genspark code accuracy:** Agent runs output, observes compilation/execution errors, auto-corrects. For spreadsheet/data: double-check by computing result a different way and comparing.
- **Replit agent error recovery:** Console access → reads error output from running processes → identifies issue → modifies code → retries. Demo included autonomous resolution of circular dependency in Drizzle ORM schema, re-running migrations, verifying via SQL.
- **Anthropic feedback gap:** Developers give agents powerful action tools but poor observability. React app built for 20 min, layout wrong, but Claude cannot observe without browser screenshot mechanism. Fix: add observability tools (browser screenshot MCP, test runner, linter, visual diff tool, semantic validator). Feedback tool quality directly limits self-correction ability and therefore autonomous task length.
- **Kimi K2 interleaved thinking for error recovery:** After tool call fails or returns unexpected result, model can reason about failure before next tool call. Changes approach based on intermediate results rather than continuing with broken assumption.
- **Haystack exit conditions as error prevention:** `exit_conditions=["tool_name"]` terminates agent when designated finalization tool is called. Without this: over-iteration or never-terminate. Fallback: `max_iterations` hard limit. Designing good exit conditions is as important as designing tools.
- **AI21 Maestro validator pattern:** At each step, a validator picks best result from parallel executions. Output validated before passing to next step. Per-requirement validators can be LLM-as-judge (single-constraint — dramatically better than multi-constraint) or deterministic code validators. Reduces compounding error: at 90% per-step accuracy, 10 steps compounds to ~35% success. Maestro's validation at each step breaks the compounding.
- **Moderation pipeline (BlackRock):** Group 1 (hard block, concurrent): toxic + sensitive + off-topic + jailbreak — if any fires, immediate block. Group 2 (soft block, concurrent): alternative routing. Group 3 (independent): PII detection — never blocking, runs in parallel, operates on output. Pre-generation vs post-generation filtering: Box enforces access control BEFORE AI gets involved. AI never sees unauthorized content. Post-retrieval filtering is weaker.

### Exact constants (temperatures, thresholds, timeouts, token limits, retries, cache TTLs)

- **Genspark compaction:** 70–80% context window utilization threshold
- **MongoDB memory creation:** 75% context window utilization threshold
- **MongoDB recency decay:** 30-day half-life (configurable per application)
- **MongoDB memory TTL:** 90 days no-access → archival; additional period → hard delete
- **MongoDB composite score weights:** 0.5 × vector_similarity + 0.3 × recency_weight + 0.2 × importance_score
- **Genspark prompt cache hit rate:** >80%
- **Genspark cache cost savings:** 5–10x token cost reduction
- **Strands agent-as-tool ratio:** parent context = 2,700 chars vs sub-agent (web search) context = 15,000 chars — 82% reduction
- **Vercel AI SDK deep research:** `stopWhen: stepCountIs(10)` per search-evaluate cycle; breadth=3, depth=2 example → 12 total queries
- **CodeRabbit token comparison:** diff-only = 17,000 tokens; optimized outside-diff slicing = 18,300 tokens (+1,300 = 7.6%); brute force = 110,000 tokens. Scale savings: 1,000 PRs/week × (110,000–18,300) = 91.7M tokens/week saved
- **Arize eval accuracy benchmarks:** baseline = 68%; + few-shot (3–4 examples) = 84% (+16pp); + meta-prompting = 88% (+4pp); DSPy/MIPRO = faster but no accuracy gain with small datasets
- **LLM-as-judge:** categorical labels ONLY (correct/incorrect/ambiguous). Do NOT use numeric scores. LLMs hallucinate numbers. `rails=["correct", "incorrect"]` parameter enforces constrained output. Temperature = 0 for eval calls.
- **Semantic cache distance threshold:** lower threshold = higher precision/lower recall; higher threshold = higher recall/lower precision. Must be tuned per use case. Walmart study: hit rate + dual-tier (L1 vector + L2 in-memory) + decision engine (code detector bypass + temporal context bypass) → highest overall accuracy.
- **Redis semantic cache demo:** cached query = ~300 tokens + 2 LLM calls; uncached = ~750 tokens + 5 LLM calls. 36% cache hit rate → $27,400/year vs $39,200/year at 10,000 daily queries.
- **Snowflake cascade proxy for AI Filter:** small proxy model + thresholds to avoid large LLM calls. Dynamically learns confidence thresholds from actual query distribution. Speed improvement: 20–500%. Accuracy impact: <2% misclassification. Query rewrite (pairwise → all-at-once for mutual exclusion classification): up to 70x speed improvement. F1 improvement example: 6% → 80% on NASDAQ article-to-ticker matching.
- **Groq LPU inference speed:** 10–40x faster than GPU-based providers. Multi-step agent calculus: 10 tool calls × 100 tokens/call at 20 tok/s = 50s; at 2,000 tok/s = 0.5s.
- **Anthropic SWEBench:** Sonnet 4.5 = 80%+. Scale note: doubling time for AI coding capability ~70 days (vs ~7 months for general task capability from METR data).
- **LandingAI ADE accuracy:** 99%+ on DOCVQA benchmark; state-of-the-art general VLMs cluster in low-to-mid 90s. KYC case study: 70%+ reduction in manual document review time.
- **Baseten KV-aware routing:** users with warm cache on a replica get routed to that replica. Cache hit → skip most prefill computation → TTFT dramatically lower. Autocomplete UX threshold: >200–300ms = perceived lag. N-gram speculative decoding: 2x higher speed at peak traffic (Sourcegraph AMP Tab).

### Multi-agent coordination

- **Strands Swarm (peer, AI Dev 25 x NYC):** Peer agents, `handoff_to_agent` tool injected into each, no hierarchy, each agent knows all peers, baton-passing with accumulated context + task status.
- **Strands hierarchical:** Agent-as-tool. Sub-agent receives prompt, runs own loop, summarizes, returns summary. Parent never sees intermediate tool calls. Modular and independently testable.
- **Strands meta-agent:** Parent constructs sub-agents dynamically at runtime: `use_agent(model_name, tools_list, prompt)`. Parent does meta-reasoning: "what kind of sub-agent do I need?" Best for open-ended tasks.
- **Google ADK multi-agent:** Parent-child. Each agent has own context window, own tool set, own system instruction. Orchestrator delegates, receives final response only. Provides encapsulation.
- **Genspark Mixture of Agents (MoA):** Layer 1: all frontier models simultaneously, independent reasoning. Layer 2: aggregator reads ALL outputs including reasoning traces, synthesizes. Cost offset: MoA is expensive; prompt caching at >80% hit rate offsets MoA costs.
- **Box A2A (Agent-to-Agent):** A2A = orchestrator-to-sub-agent delegation. MCP = agent-to-tools/data. NOT alternatives — complements at different abstraction levels. A2A orchestration calls agents → agents use MCP tools to access data. Architecture: orchestrator exposes agent cards (Google A2A protocol). Each specialized agent exposed via localhost on specific port.
- **A2A + Autonomy parallelism (Box, AI Dev 25 x NYC):** 1,000 documents → sequential = 30 min; 1,000 parallel agents (one per document via Autonomy YAML config) = 4 min. Purpose-built single-task agents parallelize trivially because no shared state.
- **CrewAI shared context / agent repositories:** Different teams build duplicate tools. Solution: agent repository — all agents stored centrally, reusable across org. Persistent cross-user memory via RAG/Graph RAG backends.
- **SAP process edge traversal for multi-agent tool discovery:** Vector retrieval finds semantically matched APIs but misses mandatory prerequisites (e.g., "create purchase order" → doesn't retrieve "create purchase requisition" which must precede it). Fix: after vector retrieval, traverse KG process edges (`must_precede`, `must_follow`) to expand candidate set with prerequisites. Agent receives APIs + process ordering. Successfully executes correct sequence.
- **BlackRock domain-driven bots:** Each domain bot independently developed and deployed. Orchestrator routes via context-aware intent analysis (full conversation history + query + sensitivity classification). Real-time data → API bot (deterministic). Static knowledge + sensitivity → RAG bot with heavy guardrails. Non-sensitive operational → LLM lighter guardrails.
- **Genspark Reinforcement Learning for tool use (published with Fireworks AI):** RL teaches tool sequencing, not world knowledge. Environment: Genspark's production tool set. Reward: multi-dimensional grader score. Result: open-source model outperformed GPT-4 and Claude on Genspark's specific task distribution. Process: build LLM-as-judge grader FIRST → use grader as reward signal → RL fine-tuning via PPO/GRPO. Principle: everything follows from having a good evaluator.

### Streaming protocol

- **AG-UI (CopilotKit / Tyler Slaton, AI Dev 25 x NYC):** 16 standard events. Transport-agnostic: HTTP SSE, WebSocket, WebRTC — same 16 events. Event categories: lifecycle (`run_started`, `run_finished`), content (`text_message_start`, `text_delta`, `text_message_end`), tool (`tool_call_start`, `tool_call_delta`, `tool_call_end`, `tool_call_result`), state (`state_snapshot`, `state_delta`), action (`agent_action_request`, `agent_action_response`), meta (`raw` for custom extensions). Thread ID + run ID: thread = entire conversation, run = one interaction.
- **AG-UI bidirectional state sync:** Agent backend defines state schema `{name, todos, counter}`. Frontend reads current state via `agent.state.name`. Frontend writes updates to agent state (user clicks counter → agent immediately aware). Enables collaborative canvas (v0, Lovable, Cursor style).
- **AG-UI front-end tools:** Agent emits `tool_call` event, execution happens client-side in browser (React state update, DOM manipulation, browser API access), no server round-trip. Agent "calls" tool but execution is client-side JavaScript.
- **Groq server-side tools:** Contrast with client-side tool calling (requires round trips per tool call). Server-side built-in tools (web search, code execution, browser automation) execute with no network round-trip — only final response crosses the wire. `groq-compound`: parallel tool execution. `groq-compound-mini`: sequential.
- **Gemini Multimodal Live:** Persistent connection, streams audio/video frames continuously, model responds as input arrives (starts before all input received). Interruption-aware. Server maintains KV cache between turns. Round-trip latency target: <500ms end-of-speech to start-of-model-speech. Foundation for ambient agents.
- **Vercel AI SDK streaming:** `streamText` / `streamObject` streaming variants. Parallel tool calls executed concurrently via `Promise.all`. `steps[]` array provides full auditability of every LLM call, tool invocation, and result.

### Training / eval setups

**Evaluation infrastructure (cross-cutting, the universal ordering):**
- Build evaluation infrastructure BEFORE optimization. Genspark: grader before RL. Arize: trace → evaluate → optimize. BlackRock: automated compliance review IS the product quality guarantee. Anti-pattern: prompt engineering without baseline measurements.

**LLM-as-judge patterns:**
- Use categorical labels (correct/incorrect), NOT numeric scores. `rails=["correct", "incorrect"]` in Phoenix. LLMs hallucinate numbers, produce inconsistent scores.
- Specialize judges: one judge per constraint (faithfulness/groundedness judge, response quality judge, tool-call correctness judge). Single-constraint judges dramatically outperform multi-constraint judges.
- Judge alignment with human feedback: MLflow workflow — define judges → add labeled examples → label (agree/disagree + rationale) → align. Demo: 50% → 100% agreement with domain expert after alignment.
- Meta-prompting: give LLM labeled examples → ask it to write improved evaluation prompt → 68%→84%→88% accuracy chain.
- LLM-as-judge for complex agentic behaviors: express criteria in plain English ("ensure the third tool call in the trace is the expected tool call"). Judge agent has tools to introspect trace. Can be aligned with human feedback. More maintainable than code-based trace evaluation.

**Datadog eval generation pipeline (no LLM for generation):**
1. Concrete query (CQ) → ground truth answer (execute against live API)
2. CQ → AST (abstract syntax tree)
3. Traverse AST, map nodes to NL templates
4. Result: natural language question with preserved semantics
5. Time-travel parameter: pass timestamp, server pretends it's that time → reproducible time-relative queries
6. LLM-assisted seed generation: coding agent + docs → seed CQ queries with placeholder service names → developer replaces with real names → 1 docs page = ~200 labeled eval scenarios
- Eval run time = 2 minutes. Run locally. Results on dashboard with shareable trace IDs.
- Tag evals by documentation section headers → group by capability → see exactly which capabilities have low scores.

**Kimi K2 training pipeline for interleaved thinking:**
1. Scrape 3,000 real tools from GitHub
2. Cluster into categories → generate 20,000+ synthetic variants per category (MCP servers explicitly included)
3. Create synthetic agents with diverse task specs
4. Simulate diverse usage trajectories (full sequences: user prompt → reason → tool call → result → reason → ...)
5. Quality filter → inject high-quality trajectories into pre-training data
6. Interleaved thinking emerges from training data that contains reasoning before AND after each tool call

**Genspark RL fine-tuning (published with Fireworks AI):**
- RL teaches the model which tools to call in which situations, how to sequence tools, how to recover from errors — not new world knowledge.
- Environment: production tool set. Reward: multi-model grader (Gemini for visual, LLM for content). Training algorithm: PPO or GRPO (unspecified in talk).
- Curriculum: start with simple single-tool tasks → multi-tool → error recovery.
- Key finding: after RL, model develops genuine understanding of tool selection and sequencing, not pattern-matching on training examples — generalizes to novel tasks.

**Automatic RLHF from UI signals (CopilotKit):**
- User edits agent-generated content → delta = preference signal. Large edit = strong negative. No edit = positive.
- HITL approvals/denials → approval = positive reinforcement, denial = negative.
- Follow-up correction queries immediately after output = strong negative signal.
- "Automatic" = no explicit rating interface. Signals collected passively from normal user interactions → dramatically higher signal volume than thumbs up/down.
- 2026 product bet: capture these signals → agent training loop, no explicit feedback required.

**MLflow evaluation stack (Samraj Moorjani, Databricks, AI Dev 25 x NYC):**
- Tracing: one-line decorator, 25+ framework integrations, OpenTelemetry ingest. Every LLM call, tool call, latency, error, cost captured.
- Agentic Insights: agent that reads production trace experiment → identifies issues, root-causes, generates Markdown report. Invoked via Claude Code using MLflow MCP server: `genai_analyze_experiment(experiment_id)`.
- Automatic prompt optimization: JEPA technique. Takes source model + source prompt + quality signal → optimizes prompt to transfer quality to target model. System-level optimization.
- Judge alignment: labeled examples + agree/disagree + rationale → align. Demo: 50% → 100% agreement.
- Agent-as-a-judge: express criteria in plain English, judge fetches only relevant trace context (not full trace in prompt). More maintainable than brittle code-based trace evaluation.

**Sonar/SonarQube study (Manish Kapur, AI Dev 25 x NYC):**
- 6 models × 4,400 Java tasks. All models produce large numbers of coding issues.
- Higher reasoning modes → MORE verbose/complex code, not less. GPT-4: ~200K lines for a task; GPT-5 high reasoning: ~75–80K lines for same task.
- Security vulnerabilities: decreasing across generations. Bugs (logic errors, runtime errors): INCREASING with higher-reasoning models.
- Cognitive complexity: GPT-5 minimal reasoning = 75%; Claude Sonnet 4 = 77%. High = hard to maintain.
- AI-generated code inherits historical bugs from training data. LLMs are agreeable: challenge correct code → LLM says "you're right" and produces a different (now broken) version.
- Sonar Sweep: training data quality product. Based on Anthropic paper showing small amount of bad code in training data can pollute LLM quality. Result: 50–65% reduction in security vulnerabilities in trained models when using cleaned vs uncleaned training data.

---

## → Verso implications

- **The loop must be trivially simple.** Every practitioner who shipped to production arrived at `while True: {reason, tool_call, add_result_to_context}`. The loop is NOT the differentiator. Verso must provide a clean, minimal default loop that is immediately understandable and extensible — not a graph DSL. Genspark explicitly killed frameworks to control every byte of the prompt.

- **The feedback pillar is the primary quality lever, not the action pillar.** Anthropic's most actionable insight: over-optimization on action tools, under-investment in observability tools. Verso's tool registry must make it trivially easy to add observability tools (browser screenshot, test runner, linter, semantic validator, visual diff). The framework should nudge users toward closing the feedback loop with a first-class concept of "sense-check tools" alongside "action tools."

- **Prompt caching is a first-class architecture constraint, not an optimization.** Genspark's append-only design is driven entirely by cache hit rate. Any framework that silently reorganizes message history, adds metadata headers, or timestamps messages will kill prompt caching. Verso must guarantee prefix stability — the context assembled for turn N must be a strict append of turn N-1's context. This should be the default and documented as such. Custom scaffolding beats framework magic when caching is the cost model.

- **Compaction should trigger at 70–80% context, not at 100%.** The 20–30% headroom is not an accident. Verso needs a configurable compaction threshold (default: 75%) with a pluggable compaction strategy (summarize-and-replace by default). This is the durable layer; the tactical loop runs on top. Mirror Claude Code's own behavior.

- **Tool descriptions are the product, not the implementation.** Datadog's entire self-optimization loop improves tool descriptions, not model weights. Haystack's ComponentTool pattern shows that docstring quality IS the tool quality. Verso's tool interface should make description a required field, support rich structured descriptions (purpose, params, when-to-use vs when-not-to-use), and provide scaffolding for tool self-documentation.

- **Agent-as-a-tool is the right abstraction for context budget management.** Strands demonstrated: wrapping verbose tools (web search, bash exec) in sub-agents that summarize = 82% reduction in parent context. This pattern should be a first-class Verso primitive: `SubAgent(tools=[...], summarize=True)`. Any tool whose raw output exceeds a token threshold should suggest wrapping.

- **Exit conditions are safety-critical, not optional.** Haystack's `exit_conditions=["tool_name"]` pattern is the right approach. Verso's agent loop must support: specific tool-call-based exit, max-iteration fallback, confidence-threshold exit (pluggable). Model-determined exit is unreliable. Make exit conditions required, not optional.

- **Informative error messages ARE the self-correction mechanism.** AWS Strands' core lesson: descriptive tool errors enable model-driven recovery. The model can't reason about failures it can't observe. Verso's tool execution wrapper must format exceptions into structured, model-legible error messages (not raw Python tracebacks). Template: `{tool_name} failed: {error_type}: {description}. Input was: {args}. Common causes: {suggestions}`. This is a framework responsibility, not user responsibility.

- **Categorical labels for LLM-as-judge, not numeric scores.** The Arize finding (68%→84%→88% with categorical labels + few-shot + meta-prompting) should be baked into Verso's eval primitives. Verso eval interface must default to `rails=["correct", "incorrect", "ambiguous"]`. Never expose a numeric score interface without explicit opt-in.

- **Broad-tool pattern + knowledge graph = the enterprise scalability primitive.** SAP's 3 tools for 110,000 endpoints is the clearest demonstration: never scale tool count to match API surface. Verso should document this pattern and provide a `BroadToolAdapter` that maps a graph/index of capability descriptions to a fixed small set of discovery + retrieval + execution tools. This also solves the MCP limitation (static registration can't scope dynamically by user intent at enterprise scale).

- **Composite memory scoring (vector + recency + importance) is the right default.** The MongoDB formula is battle-tested: 0.5×vector + 0.3×recency_decay + 0.2×importance. Verso's memory layer should implement this as the default reranker after initial vector retrieval. Importance score should be generated at creation time (one LLM call, amortized across all future retrievals — not at retrieval time).

- **Memory lifecycle policy is mandatory.** MongoDB's TTL index pattern: no-access in 90 days → archival; after retention period → hard delete. Verso memory module must expose lifecycle policy as a first-class config: `ttl_days`, `archive_threshold_days`, `compact_at_n_items`. Unbounded growth is a production failure mode.

- **Evaluation must come before optimization.** The universal practitioner finding: build eval infrastructure first, then optimize. Verso must make tracing zero-friction (one decorator/context manager, automatic capture of every LLM call + tool call + latency + token counts). OpenTelemetry-compatible span format. Export to DataFrame for eval pipelines.

- **The hybrid deterministic+probabilistic architecture is the production pattern.** CrewAI, BlackRock, Haystack, Mistral all independently converged: pure agent fails on reliability; pure workflow fails on flexibility. Verso must make it trivially easy to compose: deterministic routing → LLM step → deterministic validation → conditional agent escalation. The escape hatch for graphs is legitimate here: HITL, checkpoint-resume, durable execution — these are the cases where graph overhead pays for itself.

- **Security-before-AI: access control must precede model invocation.** Box's pattern (check permissions → reject if unauthorized → then AI sees data) is architecturally correct. Verso's integration layer should provide hooks for pre-tool authorization checks that run before the tool execution, not after. Post-retrieval filtering is weaker (data was momentarily in context, filter can have bugs).

- **Interleaved thinking (reason-after-each-tool-call) is the architecture that maintains coherence at 100+ tool calls.** Kimi K2's training demonstrates this is learnable. Verso's default loop should support an interleaved mode where a brief reflection step fires after each tool result before the next decision. This is implementable as: add system prompt instruction + increase step budget.

- **Provider-agnostic interface is table stakes.** Vercel AI SDK's model demonstrates the right API: `generateText({ model: anthropic('claude-sonnet-4-5') })` and `generateText({ model: openai('gpt-4o') })` are identical. Verso must ensure the agent loop, tool registry, memory layer, and eval hooks are all provider-agnostic. Model selection is a configuration choice, not an architectural commitment.

- **Build eval infra that runs in 2 minutes.** Datadog's 2-minute eval cycle transforms evals from chore into dev cycle feedback loop. Verso must ship with an eval runner that: loads traces, runs LLM-as-judge in parallel, aggregates by tag, reports to dashboard. The eval loop should be as fast as a unit test suite.

- **The memory taxonomy should be explicit in the framework.** Verso should expose four distinct memory types (short-term/context, semantic/RAG, episodic/action-sequences, procedural/system-prompts) as first-class primitives with separate backends and lifecycle policies. One-size-fits-all memory is the "naive" implementation practitioners regret.

- **RL fine-tuning for tool use is the ceiling, not the floor.** Genspark's published result (open-source model outperforms GPT-4 after domain-specific RL on agent trajectories) means Verso's eval infrastructure needs to produce trajectory datasets suitable for RL fine-tuning — not just hold-out labeled pairs. The eval infrastructure is also the training data pipeline.
