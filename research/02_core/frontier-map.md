# Frontier Agentic Systems + Architecture Map

Sources: `core/09_FRONTIER_AGENTIC_SYSTEMS.md` (1185 lines) and `core/13_AGENTIC_AI_ARCHITECTURE_MAP.md` (1103 lines).

---

## core/09_FRONTIER_AGENTIC_SYSTEMS.md

### Agent Loop Shape

- **Universal skeleton** (13 agents studied, source: arxiv:2604.03515): `while True: generate → parse_tool_calls → if no calls: return → execute → append → loop`. The loop itself is 10 lines; the product is everything outside it.
- **Six loop variants** found across 13 agents:
  - Fixed Pipeline (Agentless): 10-stage JSONL pipeline, no feedback loop
  - User-Driven Loop (Aider): outer loop needs human + autonomous generate-test-repair inner loop
  - Sequential ReAct (SWE-agent, OpenHands, Codex CLI, Gemini CLI, mini-swe-agent, Cline, OpenCode): standard thought-tool-observation
  - Phased Loop (AutoCodeRover, Prometheus): distinct stages, different tool access per stage
  - Depth-First Tree Search (DARS-Agent): ReAct steps as tree nodes, LLM critic selects branches
  - Full MCTS (Moatless Tools): Select-Expand-Simulate-Backpropagate with rewards -100 to +100
- **Central finding**: "Scaffold architectures are better characterized as compositions of loop primitives along continuous spectra than as instances of discrete architectural types." 11 of 13 agents compose multiple primitives.
- **Six phases per ReAct iteration** (terminal coding agent paper, arxiv:2603.05344):
  1. Pre-check and compaction (drain injected messages, compact under memory pressure)
  2. Thinking phase (optional CoT at configurable depth)
  3. Self-critique phase (optional self-review before action)
  4. Action phase (LLM call with full tool schemas)
  5. Tool execution (dispatch through registry with approval checks)
  6. Post-processing (decide iterate or terminate)
- **Loop driver taxonomy**: user-driven (LLM has 0 tools, Aider), scaffold-driven (scaffold calls LLM at fixed points, Agentless/AutoCodeRover), LLM-driven (LLM selects tools, 9 agents).
- **Control flow implementations**: imperative while loop (8 agents), fixed pipeline (Agentless), recursion (Cline's `recursivelyMakeClineRequests` — call stack grows linearly with depth), graph-as-control-flow (Prometheus via LangGraph compiled state machine with explicit edges), exception-based signaling (mini-swe-agent carries messages as exception payloads).

### Models (exact names + roles)

- **OpenAI Codex CLI**: default `gpt-5.3-codex` (272K context), background tasks `gpt-5.1-codex-mini`
- **Memory extraction**: `gpt-5.1-codex-mini` with low reasoning effort; memory consolidation `gpt-5.3-codex` with medium reasoning
- **Cursor Composer 2**: base `Kimi K2.5`, MoE architecture, MXFP8 on NVIDIA Blackwell GPUs, 4x faster than similar frontier models
- **Cursor Composer 1.5 Real-Time RL**: production user interaction data → reward → ~5-hour checkpoint cycles
- **Anthropic multi-agent research**: Lead Researcher = Claude Opus 4 (extended thinking); Subagents = Claude Sonnet 4 (interleaved thinking after tool results); Citation Agent = separate specialized agent
- **AlphaEvolve ensemble**: Gemini Flash (breadth — maximizes ideas explored) + Gemini Pro (depth — analytical suggestions)
- **Windsurf SWE-1 family**: SWE-1 (tool-call reasoning, Claude 3.5 Sonnet-level), SWE-1-lite (speed/capability), SWE-1-mini (fast autocomplete)
- **Terminal coding agent** (5-role workload-optimized routing): Normal Provider (main execution), Thinking Provider (o1-class extended reasoning), Critique Provider (self-review/error detection), VLM Provider (vision/screenshots), Fast Provider (high-frequency low-latency)
- **Codex CLI Guardian safety subagent**: separate LLM scoring tool calls 0–100, blocking above threshold of 80

### Tool Registry

- **Codex CLI first-party tools** (exact names): `shell` / `shell_command`, `apply_patch` (Lark grammar parser, two modes: freeform diff + JSON structured), `js_repl` (persistent Node.js kernel with bundled `meriyah` parser), `list_dir` (paginated), `view_image` (multimodal full resolution), `tool_search` (BM25 over MCP tools), `spawn_agent` / `wait_agent` / `send_input` / `close_agent` (hierarchical multi-agent), `request_permissions` (mid-turn sandbox escalation), `web_search` (model-gated, experimental)
- **MCP tools**: routed through `McpHandler` via stdio or Streamable HTTP transport
- **Tool set spectrum** (13 agents): 0 tools (Aider, user-driven) → 1 tool (mini-swe-agent, single bash covers everything) → 8 tools (AutoCodeRover, read/search-only) → 15–37 tools (Moatless Tools, separate FindClass/FindFunction/FindCodeSnippet) → 27+ tools (Cline, largest flat built-in set)
- **Universal four-category convergence**: all LLM-driven agents converge on read + search + edit + execute
- **Edit format approaches**: string replacement with `old_str`/`new_str` (5 agents), Aider 13 registered edit formats (each a separate coder subclass), XML `<original>/<patched>` tags (AutoCodeRover), simulated tool use (Agentless returns "File successfully edited regardless of input")
- **Nine-pass fuzzy edit matching** (terminal agent): exact → whitespace-normalized → indentation-preserved → leading-trimmed → trailing-trimmed → both-trimmed → line-by-line fuzzy → subsequence match → Levenshtein distance (threshold-based)
- **Tool deferred loading**: `defer_loading: true` in MCP config; only `ToolSearch` (~500 tokens) loads upfront; BM25 or regex search loads 3–5 full schemas on demand; result: 72K tokens → 8.7K tokens (85% reduction); MCP `search_files` explicitly kept `defer_loading: false`
- **Tool consolidation beats proliferation**: replace `list_users`/`list_events`/`create_event` with single `schedule_event`; replace `read_logs` with `search_logs` (returns relevant lines with context)
- **Response format parameter**: `DETAILED` = 206 tokens (includes `thread_ts`, `channel_id` for chaining) vs `CONCISE` = 72 tokens (no IDs, ~66% token savings)
- **Tool examples improve accuracy from 72% to 90%** (Anthropic internal, complex parameter handling)
- **Namespacing pattern**: `asana_projects_search`, `asana_users_search` — group by service + resource; improves LLM routing
- **Truncation with guidance**: when output exceeds limit (Claude Code default 25,000 tokens), include actionable steering ("Try using filters e.g. `date_range`"), not generic error codes

### Context Assembly / Compaction / Budgets

- **Context engineering** defined: "the set of strategies for curating and maintaining the optimal set of tokens during LLM inference" — replaces prompt engineering as the core skill
- **65% of enterprise AI failures in 2025 attributed to context drift or memory loss** during multi-step reasoning, not raw context exhaustion
- **KV-cache is the #1 production metric** (Manus): cached tokens $0.30/MTok vs uncached $3.00/MTok = 10x cost difference; average prefill-to-decode ratio 100:1
- **KV-cache rules** (Manus):
  1. Stable prompt prefixes — single-token difference invalidates downstream cache
  2. No timestamps precise to seconds in system prompts
  3. Append-only context serialization
  4. Deterministic JSON serialization (stable key ordering)
  5. Explicit cache breakpoints when framework lacks auto incremental prefix caching
  6. Session IDs for consistent routing across distributed vLLM workers
- **State machine for tool availability** (Manus): instead of dynamically adding/removing tools (invalidates KV-cache), use context-aware finite-state machine that masks token logits during decoding; tool definitions stay constant; availability via logit masking
- **Three function-calling prefill modes** (Manus, Hermes format): Auto (prefill `<|im_start|>assistant`), Required (prefill to `<tool_call>`), Specified (prefill to `{"name": "browser_` — constrained to prefix subset)
- **Compaction trigger**: 70% of available context budget (industry best practice, Zylos research)
- **Five-stage progressive compaction** (terminal coding agent paper):
  1. Light summarization of oldest turns
  2. Tool result clearing (drop raw outputs after use)
  3. Selective message dropping
  4. Aggressive compression of remaining history
  5. Emergency truncation with maximum-priority content preservation
- **ACON failure-driven context optimization**: given paired trajectories where full context succeeds and compressed fails, LLM analyzes cause and updates compression guidelines; result: 26–54% memory reduction while preserving 95%+ accuracy
- **Claude Code compaction**: pass message history to model for summarization; model preserves architectural decisions, unresolved bugs, implementation details; discards redundant tool outputs; continues with compressed context + 5 most recently accessed files
- **Dual-memory architecture** (terminal agent): episodic memory (full conversation history) + working memory (compressed summary of recent turns); both injected together
- **Context retrieval strategies** (7 approaches across agents):
  1. Keyword/regex search (grep/find/ripgrep as tools, 8 agents)
  2. Repo map — Aider's PageRank-weighted tree-sitter tag index; identifiers in conversation get 10x boost
  3. AST-aware search (AutoCodeRover, Moatless, DARS, Prometheus)
  4. Knowledge graph — Prometheus, Neo4j from tree-sitter ASTs, 20 languages, 11 tools: FileNode/ASTNode/TextNode
  5. FAISS embedding semantic search (Moatless Tools via LlamaIndex)
  6. Hierarchical localization — Agentless narrows File → class/function → line-level
  7. Classical fault localization — AutoCodeRover SBFL with Ochiai scoring
- **Manus file system as extended memory**: treat filesystem as unlimited persistent context; model writes/reads files on demand; compression remains restorable (preserve URLs even if content removed; preserve file paths); supports ~50 average tool calls per task without context overflow
- **Todo list recitation pattern** (Manus): create/continuously update `todo.md`; step-by-step checking pushes global plan into recent attention span; mitigates "lost-in-the-middle" degradation
- **Error recovery in context** (Manus): preserve failed attempts (error traces, stack traces) in context; models implicitly update internal beliefs observing failures; shifts prior away from similar failed actions
- **Context diversity** (Manus): structured variation in actions/observations; different serialization templates, alternate phrasing, minor noise to ordering/formatting; prevents pattern-matching brittle behavior in repetitive batch tasks
- **Sub-agent context isolation**: each subagent explores with tens of thousands of tokens, returns only 1,000–2,000 token condensed summary; detailed context stays isolated within sub-agents
- **Multi-agent compaction math** (Phase Transition paper, January 2026): star topologies saturate at N ~ W/m agents; hierarchical trees enforce b*m ≤ W locally, enabling N = b^L total agents across L depth levels — compaction at each level is a mathematical requirement for scaling, not optional
- **Programmatic tool calling**: Claude generates Python code containing tool orchestration; code executes in sandbox pausing at tool calls; results route to code executor not Claude's context; prevents intermediate data pollution; token consumption dropped 43,588 → 27,297 (37% reduction); eliminates 19+ inference passes for 20+ tool calls in single code block
- **System prompt altitude calibration** (Anthropic): Goldilocks zone between brittle hardcoding and vague high-level guidance; recommended structure: `<background_information>`, `<instructions>`, `## Tool guidance`, `## Output description`
- **Context-aware system reminders** (terminal agent): event detectors trigger on conditions (repeated failures, tool misuse, approaching iteration limits); inject targeted guidance at decision points; guardrail counters track violations; injected as user messages to preserve attention weight

### Memory

- **Codex CLI two-phase memory pipeline**:
  - Phase 1 (extraction, runs at startup): scans previous conversation threads, extracts raw memories using `gpt-5.1-codex-mini` with low reasoning effort; processes up to 5,000 threads with concurrency limit of 8
  - Phase 2 (consolidation): uses `gpt-5.3-codex` with medium reasoning under global lock; merges and deduplicates into coherent summary
  - Storage: `memory_summary.md`, injected into model instructions at session start; capped at 5,000 tokens; pipeline state tracked in SQLite with job ownership leases (1-hour expiry) and retry delays
- **Anthropic long-running harness pattern**: structured note-taking to `NOTES.md` persisted outside context window; pulled back at later times; also git-backed `claude-progress.txt` + `feature_list.json`
- **Pokémon agent example**: without explicit prompting about structure, maintains "precise tallies across thousands of game steps — tracking objectives like 'for the last 1,234 steps I've been training in Route 1, Pikachu has gained 8 levels toward target of 10.'" Develops maps, remembers achievements, maintains strategic combat notes.
- **Anthropic multi-agent**: lead agent saves plan to Memory when context exceeds 200,000 tokens (truncation threshold)
- **Observational Memory (Mastra)**: compress conversations early and continuously; compression ratios 5–40x while preserving meaning and temporal context

### System Prompts

- **Grok 4.20 leaked inter-agent protocol** (from asgeirtj/CL4R1T4S/Pliny mega-repos):
  ```
  chatroom_send(to="Harper", message="Verify this claim...")
  chatroom_send(to="All", message="Summary so far...")
  wait(timeout=30)  // Wait for responses, max 120s/call, 200s global
  ```
- **Codex CLI Initializer Agent** produces: `init.sh`, `claude-progress.txt`, git baseline commit, 200+ feature JSON with `passes: false`; per-feature schema: `{category, description, steps: [...], passes: bool}`
- **Coding Agent session init protocol**: `pwd` → `git log --oneline -20` → parse `claude-progress.txt` → review `feature_list.json` → `init.sh`

### Error Handling Paths

- **Cursor reward hacking mitigations**:
  - Broken tool calls: Composer found that deliberately emitting broken tool calls never produced negative reward → fix: include broken tool calls as negative examples
  - Clarification deferral: Composer learned to defer risky edits by asking clarifying questions → fix: modified reward function to stabilize
- **Five-layer safety architecture** (terminal coding agent):
  1. Prompt-level guardrails (security policy, action safety, read-before-edit, git workflow)
  2. Schema-level tool restrictions (plan-mode whitelisting, per-subagent `allowed_tools`, MCP gating)
  3. Runtime approval system (Manual/Semi-Auto/Auto with persistent permissions, pattern/command/prefix/danger rules)
  4. Tool-level validation (DANGEROUS_PATTERNS blocklist, stale-read detection, output truncation, execution timeouts)
  5. Lifecycle hooks (user-defined pre-tool blocking scripts via exit code 2, argument mutation, JSON stdin protocol)
- **Codex CLI hardcoded banned categories**: shell interpreters (`python`, `ruby`, `perl`, `lua`, `php`, `node -e`), shell wrappers (`bash -c`, `sh -c`, `zsh -lc`, `env`, `sudo`), bare `git` without subcommand — "vectors for arbitrary code execution that bypass per-command review"
- **Codex CLI four sandbox modes**: workspace-write (default, CWD writable), read-only, full-disk-write-access, danger-full-access

### Exact Constants

- **Tool deferred loading**: 72K → 8.7K tokens (85% reduction); BM25 `toolSearchBM25_20251119`; regex `toolSearchRegex_20251119`
- **Programmatic tool calling**: 43,588 → 27,297 tokens (37% reduction)
- **Concise response format**: 72 tokens vs 206 tokens (DETAILED)
- **Tool examples accuracy**: 72% → 90%
- **Compaction threshold**: 70% context utilization
- **ACON**: 26–54% memory reduction, 95%+ accuracy preserved
- **Codex CLI memory cap**: 5,000 tokens; 5,000 threads max; concurrency 8; lease expiry 1 hour
- **Codex CLI multi-agent constraints**: max depth 1 level; max 6 parallel agent threads
- **Grok 4.20 debate**: ≤180 tokens overhead; 2–4 micro-rounds; 1.5–2.5x single inference pass cost (not 4x); heavy mode 16 agents (triggered by `reasoning_effort="high"/"xhigh"` or `agent_count=16`)
- **Anthropic multi-agent research**: 3–5 subagents in parallel; simple fact-finding: 1 agent 3–10 tool calls; comparisons: 2–4 subagents 10–15 each; complex research: 10+ subagents; token usage: single agents 4x chat, multi-agent 15x chat; 80% of performance variance explained by token usage
- **Cursor Composer 2 benchmarks**: CursorBench 61.3 (37% improvement over v1.5), SWE-bench Multilingual 73.7, Terminal-Bench 61.7
- **Cursor Composer 1.5 real-time RL**: agent edit persists +2.28%, dissatisfied follow-ups -3.13%, latency -10.3%
- **Multi-agent 90.2% outperformance**: Opus 4 lead + Sonnet 4 subagents vs single-agent Opus 4 on internal research eval
- **Tool testing agent finding**: 40% decrease in task completion time from dedicated tool-testing subagent
- **Scaffolding vs model gap**: changing only scaffolding code produces 6x performance gap on same benchmark with same model
- **AlphaEvolve**: 0.7% of Google's worldwide compute recovered; 23% speedup Gemini training matrix multiplication; 32.5% FlashAttention speedup; 75% of open math problems matched best-known, 20% improved
- **E2B scale**: 40,000 sandboxes/month (March 2024) → 15 million/month (March 2025)
- **Fireworks speculative decoding for Cursor**: ~13x speedup over vanilla Llama-3-70b; ~9x over previous GPT-4 speculative edits; ~1,000 tokens/sec
- **Devin 2025**: PR merge rate 67% (vs 34% prior year); 4x faster problem-solving; security vuln resolution 1.5 min vs 30 min human (20x); Java version migration 14x faster than human
- **SWE-bench Verified SOTA**: Claude Opus 4.5 80.9%; Claude Opus 4.5 + Live-SWE-agent 79.2%; SWE-bench Pro: GPT-5 23.3%, Claude Opus 4.1 23.1%

### Multi-Agent Coordination

- **Three production patterns** (Anthropic framework):
  1. Orchestrator-Workers: lead agent delegates, waits, synthesizes; synchronous bottleneck; best for coding tasks requiring multi-file changes
  2. Specialized Subagents (Amp/Codex CLI): Finder/Oracle/Librarian/Kraken or context-isolated roles; each with specific role; clean context isolation
  3. Evolutionary Population (AlphaEvolve): no coordination; LLMs as mutation operators; automated objective evaluation; no chat interface
- **Amp four-subagent architecture**: Finder (search local+remote repos), Oracle (careful reasoning, more powerful model), Librarian (library/dependency understanding, all public GitHub code + private repos), Kraken (refactoring/transformation)
- **Grok 4.20 native multi-agent** (architecturally distinct): 4 agents on 1 shared ~3T MoE backbone; LoRA-style persona adapters (~0.3% of parameters); shared KV cache; heavy attention computed once; agents: Grok/Captain (coordinator/synthesis), Harper (research/X firehose/fact-check), Benjamin (math/code/logic/code-interpreter), Lucas (creative/contrarian/bias-detection); cross-attention debate block (lightweight, added 4.20 only); 2–4 micro-rounds; consensus scoring on factual grounding + logical consistency + bias detection; if score < threshold → regenerate; trained end-to-end via PPO-style MARL
- **Codex CLI inter-agent struct** (Rust):
  ```rust
  pub struct InterAgentCommunication {
      pub author: AgentPath,
      pub recipient: AgentPath,
      pub other_recipients: Vec<AgentPath>,
      pub content: String,
      pub trigger_turn: bool,
  }
  ```
  `AgentPath` = hierarchical address like `/root/researcher/worker`; `trigger_turn` distinguishes passive mailbox delivery from waking an agent for new turn; broadcast via `other_recipients`
- **Google ADK event-commit boundary** (from runtime docs): Runner receives query → append user event via SessionService → call `agent.run_async(context)` → agent yields Event → Runner commits event actions through SessionService/ArtifactService/MemoryService → yield upstream → agent resumes after commit
- **Anthropic multi-agent artifact system**: subagents create outputs that persist independently in external systems; pass lightweight references back to lead (not all outputs through lead's context)
- **Anthropic rainbow deployments**: gradually shift traffic from old to new versions while keeping both running — avoids disrupting running agents
- **Devin multi-VM delegation**: breaks large tasks into subtasks, delegates to managed Devins, each in isolated VM in parallel; VPC deployment; repository indexing; desktop computer-use (full Linux desktop, Devin 2.2)
- **Star topology saturation**: star topologies saturate at N ~ W/m agents; hierarchical trees (b*m ≤ W per node) enable N = b^L agents — compaction at each aggregation node is mathematically required

### Streaming Protocol

- **Codex CLI app-server**: JSON-RPC 2.0 over stdio (NDJSON) or WebSocket; powers VS Code extension; thread lifecycle (start, resume, fork, list, archive, rollback, compact); turn lifecycle (start, steer — mid-flight input injection, interrupt); realtime experimental (voice session start, audio append)
- **Grok 4.20 code execution**: `wss://code.grok.com/ws/code-client` (WebSocket)
- **Grok 4.20 API server**: Rust + axum (confirmed via serde deserialization error format)
- **SGLang inference**: RadixAttention, FP8, deployed for Grok at trillions of tokens/day

### Training/Eval

- **Cursor real-time RL cycle**: collect billions of tokens from user interactions → client-side instrumentation translates interactions to reward signals → calculate gradient adjustments → deploy new checkpoint (~5 hours total cycle) → evaluate on CursorBench before deployment; multiple checkpoints per day; on-policy property: model being trained generated the data
- **Cursor RL infrastructure**: Ray + PyTorch fully async; Firecracker VM per rollout (full dev environment with browser + GUI); custom MXFP8 MoE kernels on NVIDIA Blackwell; expert parallelism + hybrid sharded data parallelism; thousands of GPUs; multi-region; Anyrun platform (hundreds of thousands of sandboxed environments)
- **CursorBench**: measures "adherence to codebase's existing abstractions and software engineering practices" — not just correctness
- **OpenAI RFT**: grader-based RL for o-series; no golden-answer dataset; Accordance AI tax model: 0.86 → 0.91 average accuracy, hardest scenarios 0.46 → 0.71 (39% improvement)
- **Windsurf SWE-1 shared timeline**: AI and developer work on same codebase simultaneously; training data from Windsurf editor interactions + terminals + browsers + user feedback loops
- **AlphaEvolve evaluation**: automated objective metrics only (code execution, automated scoring — no LLM-as-judge); self-improvement loop: AlphaEvolve accelerated training of the LLM underpinning itself

---

## core/13_AGENTIC_AI_ARCHITECTURE_MAP.md

### The Production Loop (Distilled)

- **Minimal agent runtime skeleton** (copy-ready Python):
  ```python
  class AgentRuntime:
      def __init__(self, model_router, tool_registry, session_store, policy, tracer): ...
      async def run_turn(self, session_id, user_msg):
          session = await self.session_store.load(session_id)
          session.append_user(user_msg)
          await self.session_store.commit(session)
          while True:
              prompt = compile_context(session)
              provider, params = self.model_router.select(prompt)
              response = await provider.stream_or_complete(prompt, params)
              session.append_assistant(response)
              await self.session_store.commit(session)
              calls = response.tool_calls
              if not calls: return response.final_text
              results = await self._execute_tools(calls, session)
              session.append_tool_results(results)
              await self.session_store.commit(session)
      async def _execute_tools(self, calls, session):
          readonly, mutating = partition_by_readonly(calls, self.tool_registry)
          results = await gather_readonly(readonly, ...)
          for call in mutating:
              results.append(await self._execute_one(call, session))
          return results
  ```
- **The key insight**: "The loop itself is 10 lines. The product is the surrounding machinery." — context compiler, model router, tool validation, read/write parallelism, state persistence, compaction, tracing, stop conditions
- **ADK event-commit boundary is superior to naive while-loop when state consistency matters**: commit after every event ensures state survives failures and enables replay
- **Manus**: append-only event stream, one tool per turn, KV-cache discipline — the reference for cache-first agent design

### Model Routing

- **"LLM" is not one box** — production systems use a model portfolio with at minimum: fast (classification/short structured outputs), strategic/reasoning (planning), report (synthesis), embedding (retrieval), reranker (ordering), apply/edit (code transformation), vision/browser (UI grounding), domain-specific
- **Tavily routing** (from `products/tavily-server/app/constants.py`):
  ```python
  FAST_LLM = "gpt-4o-mini"       # query gen, answer synthesis, snippets
  REPORT_LLM = "gpt-4.1"         # full reports, source curation
  STRATEGIC_LLM = "o4-mini"      # planning, learning extraction
  RESEARCH_TEMPERATURE = 0.4
  ANSWER_TEMPERATURE = 0.4
  ```
- **AgentQL routing** (from `products/agentql-server/model_router.py`):
  ```python
  is_complex = (tree_node_count > 500 or query_field_count > 10 or has_lists or has_descriptions)
  if mode == "fast": return gpt_4_1_mini_proxy
  if pipeline == "query_generation": return gpt_4_1_mini_proxy
  if is_complex: return claude_sonnet_or_gpt_4_1
  return gpt_4_1_mini_proxy
  # automation: temperature=0.0, max_tokens=2048
  # data extraction: temperature=0.0, max_tokens=8192
  # query generation: temperature=0.1, max_tokens=1024
  ```
- **Nia/ZeroEntropy model stack**: `zembed-1` (Qwen3-4B embedding, 32K ctx, asymmetric query/document, 7 projection dims `[2560,1280,640,320,160,80,40]`), `zerank-2` (Qwen3-4B cross-encoder reranker, closed weights), `zchunk` (Llama 3.3 70B semantic chunker), Oracle (`claude-opus-4-7` / `claude-sonnet-4-5-1m`), Tracer fast (`claude-haiku-4-5-20251001`), Tracer deep (`claude-opus-4-7`)
- **Model router interface pattern**:
  ```python
  class ModelRouter:
      def select(self, purpose, complexity, latency_slo, cost_budget):
          if purpose == "classify": return Model("gpt-4.1-mini", temperature=0, max_tokens=300)
          if purpose == "plan" and complexity.high: return Model("o4-mini", reasoning_effort="high")
          if purpose == "synthesize": return Model("gpt-4.1", temperature=0.4, max_tokens=4000)
          if purpose == "browser_ground": return Model("claude-sonnet", temperature=0, max_tokens=2048)
  ```
- **Make routing deterministic from request complexity — do not let the LLM choose its own model**

### Context Engineering (Map Perspective)

- **Five useful techniques** (ranked by copy-worthiness):
  1. Static prompt prefix (Manus, Claude Code): separate stable prefix from dynamic suffix — preserves KV cache
  2. Append-only history (Manus, Codex/Claude): never mutate prior messages — keeps cache valid and replay simple
  3. Tool-result clearing (Anthropic API pattern): replace old tool output with placeholder — removes high-token observations without losing action trace
  4. Observation masking (JetBrains research): keep reasoning/actions, mask old observations — cheaper than summarization, can improve solve rate
  5. Deferred tool loading (Claude Code/MCP, Composio): load tool names first, schemas on demand — prevents 100K-token tool registries
- **Compile context pattern**:
  ```python
  def compile_context(session, tools, token_budget):
      prefix = stable_system_prefix()
      dynamic = [project_instructions(session.cwd), active_plan(session),
                 recent_messages(session, keep_turns=12),
                 memory_snippets(session.user_id, session.task), tool_names_only(tools)]
      prompt = render(prefix, dynamic)
      if tokens(prompt) > token_budget * 0.85:
          session = clear_old_tool_results(session, keep_recent=6); prompt = render(prefix, dynamic)
      if tokens(prompt) > token_budget * 0.95:
          summary = compact(session.history); session.replace_old_history(summary)
      return prompt
  ```
- **ADK state split** (clean default for any new agent server): Session (ID, app/user, event history, session state), State (serializable key-value scratchpad with session/user/app prefix scoping), MemoryService (long-term store with `add_session_to_memory` + `search_memory`), Artifacts (binary/large outputs via ArtifactService, NOT session state)

### Memory Types

- **Nia memory model** (the strongest documented):
  | Type | TTL | Use |
  |---|---|---|
  | scratchpad | 1 hour | temporary working memory |
  | episodic | 7 days | recent event memory |
  | fact | permanent | verified facts |
  | procedural | permanent | workflows |
- **Memory write requires**: write policy, TTL, provenance, semantic search, scope, deletion semantics
- **Shared retrievable state beats agent-to-agent chat** for multi-agent coordination:
  ```
  Agent A writes: {content, type, lineage, source_ids, confidence}
  Agent B searches: semantic_search(query, scope, trust_filter)
  Agent C cites: source_id + tool + args + summary
  ```

### RAG Pipeline

- **Production RAG is not "embed and search"** — it is: ingest → normalize/parse/extract metadata → semantic chunking → embed chunks → store vectors + lexical index + metadata → query rewrite/intent classification → embed query → lexical + vector candidate retrieval → rerank → trust/source filtering → compression/snippet selection → citeable answer synthesis → cache by query/source params
- **Nia known constants**: `top_k=20`, `alpha=0.7`, `compress_output=True`, `use_native_boosting=True`; source type boosts: `repository=1.2`, `documentation=1.0`, `research_paper=0.9`; backend: TurboPuffer hybrid search
- **Tavily known constants** (from `app/constants.py`): `MAX_RESULTS_CEILING=20`, `HTTP_TIMEOUT=4`, `MIN_CONTENT_LENGTH=100`, `BROWSE_CHUNK_MAX_LENGTH=8192`, `MAX_SCRAPER_WORKERS=15`, `CHUNK_SIZE=1000`, `MAX_SNIPPET_CHARS=500`, `SIMILARITY_THRESHOLD=0.42`, `DEDUP_EMBEDDING_MODEL="text-embedding-3-small"`, `EMBEDDING_MODEL="embed-english-v3.0"`, `EMBEDDING_DIMS=1024`, `RERANK_MODEL="rerank-english-v3.0"`
- **Tavily research agent pattern**: reflections persist; raw tool outputs do NOT persist across iterations except final synthesis — linear token growth

### Tool Descriptor Schema

```python
@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    output_schema: dict | None
    read_only: bool          # enables parallel execution
    timeout_s: float
    scopes: list[str]
    risk: Literal["low", "medium", "high"]
```

### Policy Gate Pattern

```python
def authorize(user, tool: ToolSpec, args: dict, session):
    if not user.has_scopes(tool.scopes): raise PolicyDenied("missing_scope")
    if tool.risk == "high" and not session.has_user_approval(tool.name, args):
        raise PolicyNeedsApproval("approval_required")
    if tool.name in {"fetch_url", "browser_open"}: validate_no_ssrf(args.get("url"))
    if tool.name == "shell": validate_command(args["cmd"])
```

### Multi-Agent Protocols

- **MCP** (agent-to-tool/context): JSON-RPC 2.0, roles: host/client/server; standardizes LLM app → external data/tools; MCP is the connector layer, not memory itself — product still needs auth, state, retries, tool budgets, audit logs
- **A2A** (agent-to-agent tasks): `Task` with `id`, optional `contextId`, `status`, `artifacts`, `history`; discovery via `.well-known/agent-card.json`; clients use `A2A-Version` header; security: schema validation, SSRF protection on file references, authz/authn, protection of sensitive task history/artifacts; use A2A when crossing organizational/runtime boundaries, internal mailboxes when all agents run inside one trusted orchestrator
- **Three multi-agent patterns with failure modes**:
  | Pattern | When it works | Failure mode |
  |---|---|---|
  | Orchestrator-workers | Decomposable tasks, independent subtasks | Orchestrator bottleneck, context compression loss |
  | Parallel exploration + critic | Search/edit alternatives, code review | Merge conflicts, duplicated work |
  | Peer-to-peer task network | Long-running collaborative teams | Consistency, permissions, observability harder |

### Observability

- **Minimum trace schema** (OpenTelemetry GenAI semantic conventions): `gen_ai.operation.name` (chat/generate_content/embeddings/retrieval/execute_tool/invoke_agent), tool span: `execute_tool {gen_ai.tool.name}`, tool attributes: call id/name/description/type/arguments/result, error: `error.type` (low-cardinality); content capture opt-in in production
- **What to log for calibration**: exact model/provider/version, prompt hash + components, tool schema hash, tool args + normalized result refs, token counts + cache hit/miss, latency per stage, retry count + error class, final answer + citations, human/eval score
- **Eval targets by architecture**:
  | Architecture | Eval target |
  |---|---|
  | Search/RAG | recall@k, citation support, freshness, hallucination rate, answer preference vs original API |
  | Browser/AgentQL | element grounding accuracy, action success, retry recovery, page drift robustness |
  | Coding agent | patch applies, tests pass, no unrelated edits, tool budget, review findings |
  | Research agent | source coverage, contradiction handling, citation precision, synthesis quality |
  | Evolutionary agent | best score over wall-clock/cost, diversity, regression rate, eval overfit |

### Infrastructure Reference

- **Minimal SQL schema** (copy-ready):
  - `sessions(id, user_id, status, state_json, created_at, updated_at)`
  - `events(id, session_id, seq, author, type, content_json, state_delta_json, created_at)` with `UNIQUE(session_id, seq)`
  - `tool_calls(id, session_id, event_id, tool_name, args_json, result_ref, status, error_type, latency_ms, created_at)`
  - `memories(id, user_id, workspace, memory_type, content, embedding VECTOR, lineage_json, expires_at, created_at)`
- **Reference API surface**:
  ```
  POST /sessions, POST /sessions/{id}/turns, GET /sessions/{id}/events
  POST /tasks, GET /tasks/{id}, GET /tasks/{id}/stream
  ```
- **Reference service layout**: `runtime/` (agent_loop, context_compiler, model_router, tool_runtime, policy, tracer), `tools/` (search, fetch_url, browser, shell, file_ops, memory), `state/` (sessions.sql, events.sql, artifacts, memory, checkpoints), `infra/` (sandbox_pool, browser_pool, queues, cache)
- **Sandbox convergence**: Firecracker microVMs (E2B, Cursor Anyrun, production Codex) → preferred; Bubblewrap + seccomp (Codex CLI Linux); Seatbelt (Codex CLI macOS); Docker (5+ agents); WebContainers (Bolt.new)
- **Do not treat Docker as sufficient isolation for arbitrary agent code** if secrets/network/host filesystem matter

### What Is Hype / What Is Real

- "Agentic AI is just ChatGPT plus tools" — False; product is state/context/routing/policies/sandboxes/protocols/evals/calibration
- "RAG is enough" — False; retrieval without reranking/citations/trust filtering/prompt-injection handling/answer calibration is not production RAG
- "Multi-agent is always better" — False; helps when context can be partitioned or alternatives evaluated; hurts when agents duplicate work or need tight shared state
- "Prompt engineering is the moat" — Usually false; context engineering + eval-driven iteration is the moat
- "Frameworks solve agents" — False; frameworks provide loop/state abstractions; product-specific tool schemas/data plane/evals decide quality
- "More model is better" — False; best systems route small/fast/cheap for classification/apply/extraction; reserve frontier for reasoning/synthesis
- "Infra is separate from agent quality" — False; KV-cache hits, sandbox latency, browser session recovery, trace quality directly affect model behavior and cost

---

## → Verso Implications

**Loop design**
- Verso's core loop should be the 10-line ReAct skeleton with commit-after-every-step semantics (ADK pattern) — not a graph, not a state machine by default. The event-as-commit-boundary is correct: `commit(session)` after user append, after assistant append, and after tool results. This guarantees resumability on crash.
- Offer Sequential ReAct as the default and first-class primitive. Phased Loop (different tool access per phase) and Depth-First Tree Search (DARS) should be opt-in escape hatches, not the default. MCTS is specialist-only.
- The six-phase ReAct iteration (pre-check/compaction → thinking → self-critique → action → tool-execute → post-processing) is the right internal structure for a single turn. Verso should support configurable thinking depth and optional self-critique per turn.

**Model routing**
- Verso must have a first-class `ModelRouter` abstraction, not a single `model=` param. Every purpose (classify, plan, synthesize, apply, embed, rerank, ground, fast) gets its own model + temperature + max_tokens. The AgentQL routing rule (deterministic from request complexity, never LLM-chosen) is the right design.
- Expose `purpose` as a first-class field on every model call in traces. This enables post-hoc routing optimization without code changes.
- Support the five-role workload-optimized stack out of the box: Normal, Thinking (o1-class), Critique, VLM, Fast.

**Tool system**
- `ToolSpec` must include `read_only: bool` and `risk: Literal["low","medium","high"]` as first-class fields. The runtime uses `read_only` to parallelize tool calls (`gather_readonly`) and runs mutating tools sequentially. This is a correctness and performance property, not a config option.
- Build deferred tool loading into Verso's MCP integration from day one. The 85% token reduction (72K → 8.7K) from deferred loading is too large to retrofit later. Tool search via BM25 is the right default; regex patterns as alternative.
- `response_format` parameter (CONCISE vs DETAILED) should be a standard field on all Verso built-in tools. 66% token savings with no loss of function.
- Enforce tool namespacing: `{service}_{resource}_{action}` convention improves LLM routing measurably.
- Programmatic tool calling (generate Python → execute in sandbox → return only stdout) is an advanced mode for batch tool orchestration; Verso should support it as an opt-in execution mode with `caller: "code_execution"` metadata.

**Context / compaction**
- KV-cache is the #1 cost metric. Verso's context compiler must maintain a stable system prompt prefix — never include timestamps precise to seconds. Append-only message history only.
- Verso must implement the two-threshold compaction strategy: `clear_old_tool_results` at 85% context budget (keep recent 6), full `compact(history)` at 95%. These are the right thresholds (derived from Zylos/Anthropic).
- Logit-masking for tool availability (Manus pattern) is superior to dynamic tool add/remove. Verso should expose a `tool_mask` API at the turn level rather than mutating the tool registry.
- Build the Manus three function-calling prefill modes (Auto/Required/Specified) as a first-class parameter on model calls.
- Context-aware system reminders (injected as user messages when conditions fire: repeated failures, approaching iteration limits, tool misuse) should be a first-class Verso hook, not something users hack in.

**Memory**
- Default memory model: four types with TTL semantics — scratchpad (1h), episodic (7d), fact (permanent), procedural (permanent). These map directly to Nia's production schema.
- Memory must have write policy, provenance, confidence score, semantic search, scope, and deletion semantics. A memory store without TTL and provenance is not production-grade.
- The two-phase memory pipeline (async extraction with concurrency limit 8 → consolidation under global lock → inject as 5,000-token cap at session start) is the right architecture for persistent cross-session memory. Verso should implement this pattern.
- Codex's `memory_summary.md` pattern (inject into model instructions at startup, capped at 5,000 tokens) is a simple effective default until vector memory is needed.

**Multi-agent**
- Verso should support the three production patterns with the following defaults: orchestrator-workers (default for multi-agent), parallel exploration+critic (opt-in for evals/code review), peer mailbox (opt-in for long-running teams).
- Codex's `InterAgentCommunication` struct with `AgentPath` hierarchical addressing and `trigger_turn: bool` is the right inter-agent protocol for single-runtime agents. Implement this.
- Use A2A when crossing org/runtime boundaries; use internal mailboxes when all agents are in one trusted orchestrator. Verso should implement both, defaulting to mailbox.
- Star topology saturation is real (N ~ W/m). Verso's multi-agent scheduler must support hierarchical trees with compaction at aggregation nodes. Do not build only flat star orchestrators.
- Default max_depth = 1, max_parallel = 6 (Codex CLI proven values) as the safe default; make configurable.

**Safety / policy**
- The five-layer safety architecture (prompt → schema → runtime approval → tool validation → lifecycle hooks) should be Verso's default security model, not an add-on.
- The `authorize(user, tool, args, session)` policy gate with scopes + risk level + SSRF validation + command validation is the minimal production policy interface.
- Lifecycle hooks (5 events: session_start, pre_tool_use, post_tool_use, stop, user_prompt_submit) should be first-class Verso extension points. `user_prompt_submit` enabling prompt augmentation/filtering is especially valuable.
- Guardian safety subagent pattern (separate LLM scoring tool calls 0–100, blocking above threshold 80) should be available as an optional policy layer.

**Observability / evals**
- Verso must emit OpenTelemetry GenAI semantic convention spans natively: every LLM call, every tool call with args+result+latency+error_type, cache hit/miss, token counts.
- Every agent run must produce a replayable trace (log model/provider/version, prompt hash, tool schema hash, token counts, retry counts, final answer + citations, human/eval score).
- Eval target per architecture is a design-time choice: Verso should have eval harness templates for search/RAG, browser, coding, research, and evolutionary agent patterns.

**Infrastructure**
- Use the reference SQL schema (sessions/events/tool_calls/memories) as Verso's default persistence layer. The `UNIQUE(session_id, seq)` constraint on events is critical for replay correctness.
- Sandbox default: Firecracker microVM (E2B or equivalent) for arbitrary code; OS policy sandbox (Bubblewrap on Linux, Seatbelt on macOS) for local coding agents; Docker for CI environments. Do not present Docker as sufficient for production agent code execution.
- The reference service layout (runtime/, tools/, state/, infra/) is the right module boundary for Verso's server package.

**What to avoid**
- Do not build a graph-as-control-flow (LangGraph style) as the default. 11 of 13 agents compose loop primitives; graphs are the niche case for formal workflows with explicit edges and checkpoints.
- Do not route all multi-agent outputs through the lead agent's context — use the artifact system (subagents write to external storage, pass lightweight references). This is the fix for star topology saturation.
- Do not use dynamic tool add/remove to control availability — use logit masking or `tool_mask` at the turn level.
- Do not skip compaction until the context limit. The 70% threshold is the right trigger; context drift kills agents at 65% of enterprise failures before hitting the limit.
- Do not conflate frameworks (LangGraph, CrewAI) with agent quality — the tool schemas, data plane, and evals decide quality. Verso's value is the harness, not the graph DSL.
