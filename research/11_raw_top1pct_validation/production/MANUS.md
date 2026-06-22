# MANUS — Raw Extraction (Context Engineering AS the Product)

**Source read:** `/Users/seventyleven/Desktop/researchfms/teardowns/MANUS.md` (1600 lines / 122KB, read in full).
**Target:** Manus AI (`manus.im`, Butterfly Effect Inc, Singapore/China). Cloud autonomous general-purpose agent: user goal → Linux sandbox VM → plan/execute (shell+browser+code+files) → deliverables.
**Provenance (Tier-1A per teardown):** leaked system-prompt corpus `x1xhlol/.../Manus Agent Tools & Prompt/{Prompt.txt, Agent loop.txt, Modules.txt, tools.json}` (29 tools, 206-line Modules.txt); cross-confirmed by `jujumilk3/leaked-system-prompts/manus_{20250309,20250310}.md` (99% byte-identical one day apart → stable, not hallucinated); plus OpenManus faithful clone. Round-2 adds live OpenAPI v2 spec + bundle probing.

This note focuses on the EXTRACTION TASK: the explicit context-engineering patterns, each mapped to a Verso primitive.

---

## The six context-engineering patterns (the task's spine)

### Pattern 1 — KV-cache discipline / stable prefix
**KNOWN (structural, from the loop design) + INFERRED (teardown does not name "KV-cache" explicitly).** The teardown's mechanism for cache stability is the **append-only chronological event stream** plus the **one-tool-per-turn serial loop**. Agent loop.txt lines 27-34 verbatim:
```
1. Analyze Events ... 2. Select Tools ... 3. Wait for Execution
4. Iterate: Choose only one tool call per iteration ...
5. Submit Results ... 6. Enter Standby
```
§2.1: "#4: 'Choose only one tool call per iteration.' This is the single biggest architecture decision. Every Manus turn is exactly one (LLM → one tool call → sandbox execution → one observation → LLM) cycle ... This makes the trace linear, deterministic, and replayable in the UI."
- Note: the famous Manus blog ("Context Engineering for AI Agents: Lessons from Building Manus") names KV-cache hit-rate as the #1 metric and stable-prefix as the lever. THIS TEARDOWN does NOT quote that blog; it derives cache-friendliness structurally from the append-only event stream. Mark the explicit KV-cache framing as INFERRED-from-known-source-family, the append-only stream as KNOWN.
- **Verso relation:** verso-already-has — "KV-cache-stable system prefix" is an explicit shipped primitive (ContextBundle, stable instructions/history ordering).

### Pattern 2 — todo.md recitation
**KNOWN, VERBATIM (Modules.txt lines 94-101, the Knowledge-module todo.md rules):**
```
- Create todo.md file as checklist based on task planning from the Planner module
- Task planning takes precedence over todo.md, while todo.md contains more details
- Update markers in todo.md via text replacement tool immediately after completing each item
- Rebuild todo.md when task planning changes significantly
- Must use todo.md to record and update progress for information gathering tasks
- When all planned steps are complete, verify todo.md completion and remove skipped items
```
§2.3: "todo.md is a SEPARATE memory layer from the planner ... agent ticks items off via `file_str_replace` (text replacement) ... This gives Manus TWO levels of plan: a coarse external plan (planner-owned) and a fine internal checklist (agent-owned, persisted on disk)." §1.4: "durable, inspectable progress state that the user can see in the file viewer, and that survives context compaction."
- The recitation mechanism: rewrite/tick the checklist via exact-string replacement IMMEDIATELY after each item; rebuild when the plan shifts. This keeps the global objective at the END of the context (recency) so the model re-attends to it each turn.
- **Verso relation:** verso-already-has — scaffolds ("# SCAFFOLD()" ratchet, verify-before-done gate), todo/plan recitation pattern, prune() that masks not drops. The "todo.md as durable external checklist that survives compaction" maps onto Verso's scaffold + durable seam (todo could persist via checkpoint store / sandbox FS).

### Pattern 3 — file-system as memory (externalize state to disk)
**KNOWN, VERBATIM (file_rules, Modules.txt lines 115-119):**
```
- Use file tools for reading, writing, appending, and editing to avoid string escape issues in shell commands
- Actively save intermediate results and store different types of reference information in separate files
- When merging text files, must use append mode of file writing tool to concatenate content to target file
- Strictly follow requirements in <writing_rules>, and avoid using list formats in any files except todo.md
```
§5.2 / §15.4: "save intermediate results in separate files" is "the context-window survival mechanism. By persisting intermediate state to disk, the agent can survive context truncation — it can re-read its own intermediate work from disk." §5.2: prompt explicitly warns the event stream "may be truncated or partially omitted" (Modules.txt line 33). The writing_rules draft-then-append workflow (§7) is the same idea: write each section to a separate draft file, then `file_write(append=true)` them — "the agent never tries to write all 10,000 words in one model call."
- **Verso relation:** verso-already-has (conceptually) — Verso has typed 4-tier memory, ADD-only supersede, durable checkpoint store, ctx.deps. Manus's "user's own filesystem as inspectable memory" (§5.2: "uses the user's own filesystem (todo.md) rather than a separate 'memory' abstraction — making the memory inspectable by the user in real time") is a UX framing Verso achieves through inspect()/durable history, not a missing primitive.

### Pattern 4 — keep errors in context
**KNOWN, VERBATIM (error_handling block, Modules.txt lines 178-183):**
```
- Tool execution failures are provided as events in the event stream
- When errors occur, first verify tool names and arguments
- Attempt to fix issues based on error messages; if unsuccessful, try alternative methods
- When multiple approaches fail, report failure reasons to user and request assistance
```
§15.5 escalation ladder: (1) verify tool name + args, (2) fix from error message, (3) try alternative methods, (4) after multiple failures escalate to user with full failure context. Failures are FED BACK as Observation/error events in the stream (not hidden) — the model sees its own failure trace and self-corrects. Teardown compares to Devin's "ask after 3 CI failures."
- **Verso relation:** verso-already-has — in-loop reask (append ValidationError + re-drive), Retry(feedback) self-healing, output validators, RetryPolicy typed errors, stuck/doom-loop detection (StopReason.STUCK), grace-call at max_steps. Manus's "report failure + request assistance" = Verso Hooks ask / should_continue + HITL request.

### Pattern 5 — avoid few-shot ruts (diversify, don't pattern-lock)
**WEAK in this teardown — only INFERRED-adjacent.** The teardown does NOT contain an explicit "avoid few-shot ruts / break uniform action patterns" rule. The closest signals:
- info_rules (Modules.txt 122-128): "Conduct searches step by step: search multiple attributes of single entity separately, process multiple entities one by one" — anti-conflated-search, forces varied per-step queries rather than one mega-query.
- writing_rules (Modules.txt 169-176): "varied sentence lengths" / "avoid list formatting" — explicit anti-uniformity in OUTPUT prose.
- Honest call: the Manus blog's actual "avoid few-shot ruts" lesson (vary serialization/phrasing so the model doesn't mimic a repetitive context pattern) is NOT quoted here. Mark as NOT-DIRECTLY-IN-THIS-SOURCE; the prose-diversity rule is the only on-page analog.
- **Verso relation:** neutral-context (under-attested in this source). If anything, verso-already-has the spirit via prune() masking and not re-feeding stale uniform tool outputs.

### Pattern 6 — tool masking, not removal
**WEAK/INFERRED in this teardown.** The teardown does NOT explicitly state the Manus-blog "mask tool logits instead of removing tool definitions to preserve KV-cache." The on-page analogs:
- Tool-use rules (Modules.txt 201-206): "Carefully verify available tools; do not fabricate non-existent tools"; "Events may originate from other system modules; only use explicitly provided tools."
- Datasource module (Modules.txt 68-77): "Only use data APIs already existing in the event stream; fabricating non-existent APIs is prohibited" — and crucially, data APIs are "called through Python code and cannot be used as tools" (a hard tool/code split rather than dynamic add/remove). API docs are INJECTED as Datasource events "dynamically based on which APIs are relevant to the current task" (§6) — i.e., availability is gated by context injection, conceptually adjacent to masking.
- Honest call: the explicit logit-masking-to-preserve-cache mechanism is NOT in this teardown. Mark as NOT-DIRECTLY-IN-THIS-SOURCE.
- **Verso relation:** verso-already-has the safe analog — quarantine trust-tier, PermissionDecision 4-valued (allow/deny/ask/defer), trust_tier, per-tool gating. Verso gates tool *use* via permissions rather than mutating the tool list mid-cache; that is the on-thesis equivalent of "mask not remove."

---

## Supporting architecture (KNOWN, verbatim) that validates the context-engineering bet

### Event stream taxonomy (7 event types, Modules.txt 32-41, verbatim)
```
1. Message  2. Action  3. Observation  4. Plan  5. Knowledge  6. Datasource  7. Other
```
§2.2: "The Manus event stream is NOT a conversation. It is a chronological log with seven distinct event kinds." Three (Plan/Knowledge/Datasource) come from SEPARATE upstream modules; the agent LLM only CONSUMES events, never generates plans/knowledge itself. §10.2: "There is NO inter-service messaging. All four services communicate only by appending events to the chronological event stream ... This is the canonical 'blackboard architecture' pattern from 1980s AI."
- **Verso relation:** neutral-context / avoid-overkill. Verso's counter-thesis is "no graph, no orchestrator-as-primitive, ONE clean ReAct loop." Manus's separate Planner/Knowledge/Datasource SERVICES are exactly the multi-service machinery Verso refuses to force. The typed-event STREAM itself maps to Verso's typed streaming events (message/reasoning/tool.start/tool.result/done) — Verso-already-has the stream, avoids the service split.

### One-tool-per-turn serial loop (Agent loop.txt line 31)
"Choose only one tool call per iteration." Opposite of Claude Code's parallel tool calls. Chosen for linear/deterministic/replayable trace.
- **Verso relation:** verso-already-has — Verso's async ReAct loop (<200 lines). (Verso does not mandate serial-only; this is a design knob, not a gap.)

### "Plain text responses are forbidden" (Modules.txt 201-206, verbatim)
"Must respond with a tool use (function calling); plain text responses are forbidden." All user text routes through `message_notify_user` (non-blocking) / `message_ask_user` (blocking). Tool names are confidential ("Do not mention any specific tool names to users").
- **Verso relation:** neutral-context. Verso has done()-tool termination and structured output; forcing tool_choice=required is a config, not a missing primitive.

### Writing rules — the long-form deliverable lever (Modules.txt 169-176, verbatim)
"continuous paragraphs using varied sentence lengths ... avoid list formatting ... minimum length of several thousand words ... actively cite original text with sources ... first save each section as separate draft files, then append them sequentially ... no content should be reduced or summarized; the final length must exceed the sum of all individual draft files."
- The draft-then-append rule is a CONTEXT-WINDOW workaround: never write 10k words in one call; build on disk.
- **Verso relation:** neutral-context (output-style policy, not a framework primitive).

### Information hierarchy / anti-hallucination (info_rules, Modules.txt 122-128, verbatim)
"Information priority: authoritative data from datasource API > web search > model's internal knowledge"; "Snippets in search results are not valid sources; must access original pages via browser."
- **Verso relation:** neutral-context (prompt-engineering discipline, app-level).

### Sandbox runtime / data API (Modules.txt 80-91, verbatim)
```python
sys.path.append('/opt/.manus/.sandbox-runtime')
from data_api import ApiClient
client = ApiClient()
weather = client.call_api('WeatherBank/get_weather', query={'location': 'Singapore'})
```
Data APIs are system-paid, auth-free, Python-only ("cannot be used as tools"), docs injected as Datasource events on demand.
- **Verso relation:** avoid-overkill (managed data-API gateway is Manus's moat/infra, out of Verso's framework scope). The "code-mode tool" idea (call APIs via generated Python, not tool defs) is interesting but NON-GOAL-adjacent (Verso is native @tool path, not code-execution-as-tool-bus).

### Constants / numbers (Constants Table §9, verbatim sources)
- Tool calls per iteration: 1 (Agent loop.txt:31)
- 29 tools (corrected from R1's 27; +browser_console_exec, +browser_console_view) (tools.json)
- 7 event types; 3 upstream modules (Planner/Knowledge/Datasource)
- Sandbox: Ubuntu 22.04 amd64, user `ubuntu` passwordless sudo, Python 3.10.12, Node 20.18.0
- OpenManus clone: `max_steps: int = 20`, `max_observe: int = 10000` (char cap on tool output before truncation)
- Inferred real max_steps: 50-100
- Round-2: agent_profile 3-tier `manus-1.6-{lite,standard,max}`, free-tier auto-downgrade to lite; APISIX/3.11.0 gateway; 200 req/min per-IP; OpenAPI v2 = 32 endpoints.

### OpenManus clone confirms ReAct (app/agent/manus.py, app/agent/toolcall.py, verbatim)
Inheritance: `Manus → ToolCallAgent → ReActAgent → BaseAgent`. `think()` appends `next_step_prompt` as a user message, calls `ask_tool(messages, system_msgs, tools, tool_choice)`. Confirms canonical loop = ReAct (think → tool call → observation → think).
- **Verso relation:** verso-already-has — Verso IS this loop, done right and <200 lines.

### Round-2 structured-output extraction (§R2.4, verbatim contract)
`structured_output_schema` (JSON Schema) on task.create → post-task separate LLM call extracts JSON; constraints: all props in `required`, `additionalProperties:false`; result `{success, value, error}` with schema-conforming zero-values even on failure.
- **Verso relation:** verso-already-has — output_type=, in-loop reask, output validators, Retry(feedback). Manus's "post-task extraction" is slightly different (separate pass vs in-loop), but Verso's in-loop reask is the on-thesis equivalent and arguably superior.

### Round-2 verbose trajectory flag (§R2.4)
`/v2/task.listMessages?verbose=true` exposes `tool_used / plan_update / new_plan_step / explanation` events; without verbose only user/assistant/error/status. "full trajectory observability ... useful for debugging, RL training, and trust verification."
- **Verso relation:** verso-already-has — VersoSpan + OTel, from_trace, "prod==eval, captured failure IS a regression test."

---

## Multi-service / infra machinery Verso must NOT copy (avoid-overkill)
- Separate Planner / Knowledge / Datasource SERVICES feeding a blackboard event stream (§2.3, §10) — orchestrator/planner machinery; Verso NON-GOAL ("no orchestrator-as-primitive, no router/planner cult").
- Managed multi-cloud sandbox fleet (AWS ephemeral microVM + GCE "Manus PC" persistent VM + macOS iOS-build VM) (§R2.5, §R2.6, §R2.11) — pure infra/product, not framework.
- APISIX gateway, Connect-RPC backend, Enterprise IAM/DSPM/SCIM, webhooks, VNC/VS-Code-Server, iOS build pipeline (§R2) — product surface, far outside Verso scope.
- `make_manus_page` MDX deliverable system, deploy_apply_deployment (static/nextjs) (§3.6, §15.13) — product output, not framework.
- "Several thousand words minimum / no lists" writing policy (§7) — app prompt, not a primitive.

---

## Honest caveats on the task's six named patterns
The task named six patterns from the Manus *blog*. This *teardown* solidly attests FOUR of them (stable-prefix-via-append-only-stream, todo.md recitation, file-system-as-memory, keep-errors-in-context). The other two (avoid-few-shot-ruts, tool-masking-not-removal) are NOT explicitly present in this teardown — only weak structural analogs (step-by-step search; "only use provided/injected tools"; data-API-as-code split). Anyone wanting the verbatim blog framing must read the Manus blog itself, not this RE file. Marked accordingly above.
