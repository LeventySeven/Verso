# RAW EXTRACTION — core06-agentic-architectures (methodology)

**Source file:** `/Users/seventyleven/Desktop/researchfms/core/06_AGENTIC_ARCHITECTURES.md` (2874 lines, 165KB)
**Read ranges:** L155-184 (Universal Agent Loop), L402-447 (Claude Code core instructions verbatim), L776-910 (Anthropic Official Agentic Patterns — full detail §6), L1286-1349 (Ring-by-Ring loop), L1440-1453 (SWE-bench leaderboard), L1454-1531 (Seven Patterns + comparison tables).
**Provenance note (from source header, L149):** "Reverse-engineered from leaked system prompts, open-source code, and production analysis. Every architecture here is sourced from actual code or captured prompts — not marketing. Sources: x1xhlol/system-prompts-and-models-of-ai-tools (16+ products), jujumilk3/leaked-system-prompts (124+ prompts), OpenAI Codex CLI source (Apache 2.0), OpenCode source (MIT), Anthropic engineering blog, Cursor technical reports, Cognition blog."

---

## 1. The minimal "agent = LLM in a loop with tools + environment feedback" definition — KNOWN-from-source (L155-177)

Section header: **"## 1. The Universal Agent Loop"** — "Every agentic product uses the same core primitive. The differences are in what surrounds it."

Verbatim code block (L159-170):
```python
# This is the entire agent loop. Everything else is engineering around it.
messages = [system_prompt] + [user_message]
while True:
    response = llm.generate(messages, tools=tool_definitions)
    if response.has_tool_calls:
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call)
            messages.append(tool_result(result))
    else:
        return response.text  # done
```

Key attributions (verbatim, L172-176):
- **Claude Code** "implements this as a single-threaded while-loop (`nO`). Entire state is a message array. **No state machine, no workflow graph.** The Rust rewrite (`claw-code`) does it in ~88 lines in `conversation.rs`. `AgentRuntime` holds: session (message array), api_client, tool_executor, permission_policy, system_prompt, max_iterations, usage_tracker."
- **Codex CLI** "implements `AgentLoop.run()` ... parses streaming events from OpenAI Responses API, detects tool calls, dispatches to handlers, feeds results back."
- **Manus** "is the exception: strictly ONE tool call per iteration. Must await results before proceeding. ~50 tool calls per typical task."

> VERSO TAG: verso-already-has. The "while True: generate → if tool_calls execute & append results → else return" loop IS Verso's core/loop.py async ReAct loop. "No state machine, no workflow graph" + "everything else is engineering around it" is verbatim Verso thesis ("we don't force the graph"). ~88-line claw-code / <200-line Verso are the same brutal-core claim.

---

## 2. Anthropic's Official "When to Use What" decision table — KNOWN-from-source (L776-789)

Section: **"## 6. Anthropic's Official Agentic Patterns — Full Detail" → "### 6.1 When to Use What"**

Verbatim table:

| Scenario | Pattern | Why |
|----------|---------|-----|
| Well-defined sequential tasks | Prompt chaining | Each step validates before next |
| Multiple input categories | Routing | Specialized handling per type |
| Speed + redundancy needed | Parallelization | Independent subtasks or voting |
| Unpredictable subtasks | Orchestrator-Workers | Dynamic decomposition |
| Iterative refinement | Evaluator-Optimizer | Clear eval criteria drive loops |
| Open-ended autonomous | ReAct agent loop | Unknown step count |

**Override principle (verbatim, L789):** "Consider adding complexity only when it demonstrably improves outcomes."

This is the canonical workflow-vs-agent decision spine: the five Anthropic workflows (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer) sit BELOW the ReAct agent loop, which is reserved for "Open-ended autonomous / Unknown step count."

> VERSO TAG: neutral-context (the table itself) / avoid-overkill (the 5 workflow patterns as built-in primitives). Verso's stance is the SAME as the override principle ("add complexity only when it demonstrably improves outcomes" ≈ "cut anything that buys ~1%"). Verso deliberately does NOT ship prompt-chaining/routing/parallelization/orchestrator-workers/evaluator-optimizer AS primitives — they're user code composed from the one loop. This table is the external authority that VALIDATES "don't force the graph": even Anthropic frames agents as the top rung you climb to only when step count is unknown.

---

## 3. Orchestrator-Workers — Anthropic's recommended complex pattern — KNOWN-from-source (L791-832)

"From their own multi-agent research system." Topology: **LeadResearcher (Opus 4)** spawns **3-5 parallel Subagents (Sonnet)**, each doing 3+ parallel tool calls; Lead merges; a **CitationAgent** post-processes.

Hard numbers (verbatim):
- **"Performance: 90.2% improvement over single-agent Opus 4 on research eval."** (L825)
- Subagents "store work in EXTERNAL systems and pass lightweight references → prevents information loss when context is truncated" (L828)
- "Lead uses extended thinking for planning; subagents use interleaved thinking post-tool execution" (L829)
- "A tool-testing agent rewrites tool descriptions → **40% decrease in task completion time**" (L830)
- "Token usage: multi-agent uses ~15x more tokens than chat, ~4x more than single agent" (L831)
- **"Three factors explain 95% of performance variance: token usage (80%), tool call count, model choice"** (L832)

> VERSO TAG: avoid-overkill (the orchestrator-workers topology as a primitive) + steal-additive (the tool-description-rewrite finding, see §8). The 15x token cost and "95% of variance = token usage(80%) + tool count + model" is a strong argument AGAINST orchestrator-as-primitive and FOR Verso's context-engineering-first stance. Verso's Agent-tool / subagent spawn is the seam if a user wants this; it should not be a built-in graph node.

---

## 4. Programmatic Tool Calling — KNOWN-from-source (L834-869)

**Problem:** "10 sequential tool calls = 10 inference passes, each adding results to context." **Solution:** "Claude writes Python code that calls tools and processes results. Tool outputs from programmatic calls are NOT added to context — only final stdout."

Setup uses `{"type": "code_execution_20250825"}` + a tool with `"allowed_callers": ["code_execution_20250825"]`.

**Performance (verbatim, L869):** "Token usage dropped 37%. On BrowseComp and DeepSearchQA benchmarks, adding programmatic calling was the key factor unlocking agent performance."

> VERSO TAG: neutral-context / avoid-overkill. This is a code-execution-tool feature (Anthropic API primitive), not a loop pattern. Verso's @tool path + a code-exec tool could express it; building "allowed_callers" routing into the core is not on-thesis. The principle (collapse N inference passes, keep intermediate results out of context) overlaps Verso's prune()/observation-masking philosophy.

---

## 5. Tool Search — Deferred Loading — KNOWN-from-source (L871-877)

**Problem:** "58 MCP tools consume ~55K tokens before any conversation." **Solution:** "Mark tools as `defer_loading: true`. Only tool names loaded. Full schemas loaded on-demand ... via `tool_search_tool_regex`."
**Impact (verbatim):** "Context overhead drops from ~77K to ~8.7K tokens (95% reduction). Accuracy: Opus 4 improved from 49% to 74%. Opus 4.5 from 79.5% to 88.1%."

> VERSO TAG: steal-additive (candidate). Verso ships @tool + tool_from_schema(raw/MCP) but (per current-state summary) does NOT list deferred/lazy tool-schema loading. A `defer_loading=True` flag on a tool — names in the prompt, full JSON schema fetched on demand — is additive, byte-identical when unused (default eager), and on-thesis (context-engineering is first-class). Note: this raw-extraction agent observed this exact mechanism in THIS Claude Code session's harness (deferred tools via ToolSearch), corroborating the source. NOT MCP-first; it works for native @tool too.

---

## 6. Long-Running Agent Harness (Anthropic's production two-phase pattern) — KNOWN-from-source (L879-905)

**Phase 1 — Initializer Agent (first session):** creates `init.sh` (dev server startup), `claude-progress.txt` (chronicles work across sessions), a feature-list JSON (each entry `{category, description, steps[], passes:false}`), makes initial git commit.
**Phase 2 — Coding Agent (each subsequent session):** `pwd` verify → read git logs + progress → select highest-priority `passes:false` feature → start dev server via `init.sh` → run e2e verification → implement + commit → update progress → "Mark `passes:true` only AFTER e2e browser automation verification."
**Key rule (verbatim, L905):** "It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality."

> VERSO TAG: verso-already-has (mostly). This maps to Verso's scaffolds (load_skills, "# SCAFFOLD()" ratchet, verify-before-done gate) and durable seam (checkpoint/resume across fresh processes, progress chronicle ≈ event-sourced history). The "passes:true only after verification" gate is Verso's verify-before-done. The cross-session progress file is what Verso's durable checkpoint store replaces with event-sourcing.

---

## 7. Ring-by-Ring loop implementation (Anthropic SDK shape) — KNOWN-from-source (L1286-1347)

- **Ring 1:** single tool, single turn — `tool_choice={"type":"auto","disable_parallel_tool_use":True}`, run tool, feed `tool_result` back.
- **Ring 2 (verbatim "the core pattern"):** `while response.stop_reason == "tool_use":` loop — process all `tool_use` blocks, append `{"role":"assistant", content}` then `{"role":"user", content: tool_results}`, re-create. "response.content now has the final text answer."
- **Ring 3 (Parallel):** "Same loop — just process ALL `tool_use` blocks (not just the first)."
- **Ring 4 (Streaming):** swap `messages.create` → `messages.stream`, handle `content_block_start`/`content_block_delta`/`message_stop`.

> VERSO TAG: verso-already-has. Ring 2 IS the ReAct loop; Ring 3 is parallel tool calls; Ring 4 is Verso's typed true-delta streaming events. The "rings" framing (escalate from single-call up only as needed) is the same ladder Verso embodies — start with one call, add the loop, add parallelism, add streaming, each additive.

---

## 8. Claude Code core instructions — overkill / anti-overengineering warnings (verbatim) — KNOWN-from-source (L404-428)

From the leaked Claude Code system prompt, "# Doing tasks":
- "Do not create files unless they're absolutely necessary for achieving your goal."
- "Don't add features, refactor code, or make 'improvements' beyond what was asked."
- **"Don't add error handling, fallbacks, or validation for scenarios that can't happen."**
- "Don't create helpers, utilities, or abstractions for one-time operations."
- "# Output efficiency: Go straight to the point. **Try the simplest approach first without going in circles.** ... Lead with the answer or action, not the reasoning."

> VERSO TAG: neutral-context (validation). This is Anthropic's own product encoding Verso's exact "brutal, no overkill, simplest thing" law — useful as external corroboration of the thesis, not a primitive to copy.

---

## 9. Scaffolding-matters numbers — KNOWN-from-source (L1450-1452, 1464)

- "Agent scaffolding matters as much as the model. Three frameworks running identical models scored **17 issues apart on 731 problems**. Same model, different agent → **6-point gap on SWE-bench Pro** (Augment's context engine vs raw Claude)."
- "On truly novel issues (not in training data): best agents solve only ~18-20%, far below 70%+ on curated benchmarks."
- "Augment's context engine accounts for **6 SWE-bench points over identical model**." (Pattern #2: "Context Engineering > Prompt Engineering")

> VERSO TAG: neutral-context (validation). Directly supports Verso's "context-engineering is first-class / the harness is the product" positioning with hard SWE-bench deltas.

---

## 10. Seven Patterns That Work at Scale (production survey) — KNOWN-from-source (L1454-1496)

1. **Separation of Cognitive Tasks** — Aider Architect/Editor → 85% pass; Claude Code Explore(read)/Plan(research)/General-Purpose(action).
2. **Context Engineering > Prompt Engineering** — see §9; Manus append-only event stream + KV-cache as #1 metric (10x cost reduction); Claude Code L1/L2/L3 memory hierarchy with progressive disclosure.
3. **Sandboxing as Architecture** — Codex "Environment-as-primitive (Seatbelt/Bubblewrap/Landlock, enabled by default)."
4. **Edit Format Matched to Model** — Aider format per model (whole for o1, diff for Sonnet, udiff for GPT-4 Turbo); OpenCode provider-adaptive.
5. **Multi-Path Exploration with Backtracking** — Amazon Q tree search + critic + rollback (85% higher success); Cursor Bugbot 8 parallel passes → majority voting.
6. **Asynchronous Fire-and-Forget** — Jules returns PR in ~10 min; Codex sandboxed VMs.
7. **Continuous RL from Production** — Cursor Tab retrained every 90 min from accept/reject across 400M+ daily requests.

> VERSO TAG: mixed. #2 (context engineering, KV-cache, append-only) = verso-already-has (KV-cache-stable prefix, prune, memory). #1 (cognitive separation) = the Agent/subagent seam, avoid-overkill as a built-in. #5/#6/#7 = avoid-overkill (backtracking trees, async fire-and-forget infra, production RL are out of scope / NON-GOALS-adjacent: no learned routers, not the model). #3 sandboxing is a safety/hook concern Verso partially covers via trust_tier/quarantine.

---

## 11. KV-cache / cost framing — KNOWN-from-source (L731-744, 1467, 1509)

- Manus: "KV-Cache Optimization (their #1 metric)"; "Session routing: session IDs → consistent vLLM workers"; "KV-cache optimization (100:1 ratio)"; "append-only event stream + KV-cache as #1 metric (10x cost reduction)."

> VERSO TAG: verso-already-has. Verso ships KV-cache-stable system prefix as a first-class context primitive; this corroborates prioritizing it. Session→worker routing (vLLM) is infra, out of Verso scope.

---

## SUMMARY OF VERSO-RELEVANT JUDGMENTS

- **verso-already-has:** the universal loop (§1, §7), long-running harness ≈ scaffolds+durable (§6), KV-cache prefix (§11), context-engineering-wins (§2 of seven, §9).
- **steal-additive (high bar, candidate):** deferred tool-schema loading (`defer_loading=True`) — §5. Additive flag, byte-identical default-eager, on-thesis context-engineering, works for native @tool (not MCP-only). Plus the tool-description-rewrite eval insight from §3 (40% faster) as an evals/optimization recipe, not a primitive.
- **avoid-overkill (refuse as primitives):** the five workflow patterns as built-ins (§2), orchestrator-workers topology as a graph node (§3), programmatic-tool-calling routing in core (§4), backtracking trees / async-VM infra / production-RL (§10 #5–7).
- **neutral-context (external validation of thesis):** "add complexity only when it demonstrably improves outcomes" (§2), Claude Code anti-overengineering instructions (§8), scaffolding-matters SWE-bench deltas (§9), "no state machine, no workflow graph" (§1).
