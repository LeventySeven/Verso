# OSS_AGENTS — Raw Extraction (browser-use + OpenHands)

Track: production. Sources read (exact paths):
- `/Users/seventyleven/Desktop/researchfms/teardowns/BROWSER_USE.md` (1899 lines)
- `/Users/seventyleven/Desktop/researchfms/teardowns/OPENHANDS.md` (1404 lines)

Task focus: OSS agent loops (grep-first). browser-use's DOM action loop + `ActionLoopDetector`; OpenHands' event-stream architecture + state. Judge event-stream-as-state vs Verso's message-history+checkpoint. KNOWN = stated in source w/ file:line; INFERRED = my synthesis.

---

## A. BROWSER-USE — the DOM action step loop

### A1. The minimal loop (KNOWN — `browser_use/agent/service.py:131`, step at `:1023`)
`class Agent(Generic[Context, AgentStructuredOutput])`. Constructor accepts **~70 kwargs** (service.py:133-209). `Agent.step()` has **4 phases** (service.py:1064-1077), verbatim:
```python
# Phase 0: captcha wait (if browser is solving)
captcha_wait = await self.browser_session.wait_if_captcha_solving()
# Phase 1: Prepare context (browser state + history + screenshot)
browser_state_summary = await self._prepare_context(step_info)
# Phase 2: Get LLM output + execute actions
await self._get_next_action(browser_state_summary)
await self._execute_actions()
# Phase 3: Post-processing (downloads, loop detection, failure tracking)
await self._post_process()
```
Each step wrapped by `_finalize()` which emits `CreateAgentStepEvent` and saves history. Loop continues until `done` action called or `max_steps` reached. (KNOWN)

This is a plain async ReAct loop — observe (serialized DOM + screenshot) → LLM plans → execute indexed actions → post-process. **Same shape as Verso's core/loop.py.** (INFERRED, on-thesis match.)

### A2. The novel primitive: indexed-DOM-as-action-target (KNOWN — exec summary, service.py)
> "the framework extracts every interactive element from the live DOM tree, assigns each a stable integer index, renders them as `[i]<tag attribute=value/>` tokens, and the LLM picks actions by index (`click(3)`, `input(5, "hello")`). This eliminates CSS-selector hallucination ... the LLM cannot make up a non-existent index."
Domain-specific grounding trick (constrain the action space to a finite enumerated menu). NOT general-agent-framework material — it's browser-tool-specific. (avoid-overkill for Verso core; it belongs in a browser tool if Verso ever ships one.)

### A3. ActionLoopDetector — in-loop stuck/doom-loop watchdog (KNOWN — `agent/views.py:157-249`)
The detector runs *inside* the agent loop:
- **Window:** 20 most recent action hashes (`loop_detection_window`, default 20, views.py:90).
- **Action hashing (canonicalized by type, views.py:110-148):** `search` → sort+lowercase tokens; `click`/`input` → hash by element index; `navigate` → full URL; `scroll` → direction + index.
- **Page fingerprinting:** per-step `PageFingerprint = (url, element_count, sha256(dom_text)[:16])`.
- **Escalating nudges (views.py:215-244), verbatim:**
  - 5+ repetitions: "If this is intentional and making progress, carry on. If not, it might be worth reconsidering."
  - 8+ repetitions: stronger "Are you still making progress?"
  - 12+ repetitions: strongest nudge.
  - 5+ consecutive stagnant pages: "The page content has not changed across {N} consecutive actions. Your actions might not be having the intended effect."
- **Mechanism (KNOWN):** "Nudges are injected into the user message as context — the agent is *informed* but never *blocked*. The detector is a soft conscience, not a guard."

KEY DESIGN POINT vs Verso: browser-use's loop detector **nudges, it does not halt**. Verso's `StopReason.STUCK` *terminates*. Two different philosophies: soft-nudge-in-context vs hard-stop. (See judgment section.)

### A4. Other in-loop behavioral nudges (KNOWN — §8, service.py)
- **Replan nudge** (`planning_replan_on_stall=3`, views.py:79): after 3 consecutive failures inject "Multiple consecutive failures detected. Consider revising your plan or trying a different approach." Disable with `=0`.
- **Exploration nudge** (`planning_exploration_limit=5`, views.py:80): no plan after 5 steps + complex task → nudge to generate a plan.
- **Budget warning:** at 75% of max_steps inject "You have used 75% of your step budget. Critically evaluate completion strategy."
- **Force-done after last step:** if `step_info.is_last_step()` and `done` not called, inject a forcing message to call done with whatever results exist. (= Verso's grace-call / max_steps_policy. verso-already-has.)

### A5. Failure budget / error taxonomy (KNOWN — views.py:66, service.py:1245+)
- `max_failures=5` default. Single-action errors increment `consecutive_failures`; success resets to 0. Multi-action-step errors handled by loop detection NOT failure count.
- `final_response_after_failure=True` (views.py:87): after max_failures, one final recovery call.
- Typed error categorization in `_handle_step_error`: `InterruptedError` (not logged); CDP/WebSocket connection errors (reconnect logic w/ `RECONNECT_WAIT_TIMEOUT`, terminal if `_cdp_client_root is None`); `RateLimitError` → wait-before-retry; `ValidationError` → "Invalid model output format. Please follow the correct schema."; missing-required-fields → strip stacktrace + reask. (= Verso error taxonomy + FailoverModel/RetryPolicy. verso-already-has.)
- Per-action: every handler wraps in try/except and returns `ActionResult(error=msg)` instead of raising — "a single failed action doesn't kill the loop — the LLM sees the error in next step's history and can adapt." (= Verso tool error-as-observation. verso-already-has.)
- Per-step timeouts: `llm_timeout` auto-detected by model (groq 30s; claude/o3/deepseek/gemini-3-pro 90s; default 75/60s); `step_timeout=180`. `asyncio.wait_for(..., timeout=llm_timeout)`. (= Verso per-tool timeout_seconds + per-call model; auto-by-model-substring is a cute heuristic, not core. neutral.)

### A6. Context / MessageManager — single-message, cache-friendly (KNOWN — `agent/message_manager/service.py:597`)
- `system_message: SystemMessage` set once at init, `cache=True`.
- "Each step the user message is rebuilt fresh (NOT appended — the prompt is single-message, cache-friendly)." Structure includes `<agent_history>` (+ `compacted_memory` if present), `<sensitive_data>`, filtered actions for current URL.
- Compaction: `compact_every_n_steps=25`, `trigger_char_count=40000` (~10k tokens), `keep_last_items=6`, `summary_max_chars=6000`, `chars_per_token=4.0` (views.py:35-56). LLM-summarization compaction of older history.
- Anthropic 4.5 needs ≥4096-token prompts for cache hits; browser-use ships an inflated prompt variant just to clear that threshold (`prompts.py:17-24`). 8 system-prompt variants compiled at init by model + flash_mode + thinking.

NOTE on thesis: browser-use's default IS LLM-summarization compaction (`compacted_memory`). Verso's stated NON-GOAL is "no LLM-summarization-compaction-by-default" — Verso prefers `prune()` masking. So browser-use is a counter-example data point, not a thing to copy. (avoid-overkill.)

### A7. Multi-model slots within ONE agent (KNOWN — service.py:249-252)
4-5 model slots in a single Agent: `llm` (main, every step), `page_extraction_llm` (extract action; 120s timeout), `judge_llm` (post-hoc trace eval), `fallback_llm` (on main failure), `compaction_llm`. Each defaults to main `llm`. "pseudo-multi-agent: one Agent runs the loop, but specialized LLMs handle expensive sub-tasks." (= Verso per-call `model=` swap + `agent.override()` + FailoverModel. verso-already-has.)

### A8. Judge as post-hoc verifier (KNOWN — `views.py:288-303`)
```python
class JudgementResult(BaseModel):
    reasoning: str | None
    verdict: bool
    failure_reason: str | None  # max 5 sentences
    impossible_task: bool
    reached_captcha: bool
```
Runs after agent completes/max_steps; grades full trace vs ground-truth; saved to `ActionResult.judgement`. Doesn't intervene during execution. (= Verso LLMJudge / Eval.judge / from_trace. verso-already-has. Note `impossible_task` as a judge field is a nice idea.)

### A9. AgentOutput schema — structured thought (KNOWN — system_prompt.md, views.py:457-485)
Agent emits JSON each step: `thinking, evaluation_previous_goal, memory, next_goal, current_plan_item, plan_update, action[]`. Flash mode strips all but `memory` + `action` (cheaper). `max_actions_per_step=5`. (Multi-action-per-step batching = like OpenHands `_ActionBatch`. INFERRED.)

---

## B. OPENHANDS — event-stream architecture + state

### B1. Re-architected into a 4-package SDK monorepo (KNOWN — §0)
Old monolith (`AgentController` state machine, `CodeActAgent`, `agenthub/` registration, `AgentDelegateAction`) is GONE. Now: `openhands-sdk` (kernel: `Agent`, `Conversation`, `LLM`, event stream, condenser, builtin tools), `openhands-tools`, `openhands-agent-server` (FastAPI, 80 routes + 2 WS), `openhands-workspace`.

### B2. The TWO load-bearing primitives (KNOWN — §1, verbatim)
1. **Event sourcing.** "Every agent step is a sequence of typed `Event` objects (`SystemPromptEvent`, `MessageEvent`, `ActionEvent`, `ObservationEvent`, `AgentErrorEvent`, `CondensationRequest`, `Condensation`, `PauseEvent`, `TokenEvent`, `ConversationStateUpdateEvent`, `ConversationErrorEvent`, `UserRejectObservation`). They are appended to a file-backed `EventLog` and replayed on resume."
2. **Frozen-pydantic configuration.** `AgentBase` is `model_config = ConfigDict(frozen=True)` (base.py:108) — "configuration-IS-the-agent", stateless kernel. "Mutating a public field on `ConversationState` triggers `__setattr__` → autosave → state-change callback (state.py:399-444). This is the persistence and resume mechanism."

### B3. The step loop: `LocalConversation.run()` (KNOWN — `local_conversation.py:746-890`)
Replaces legacy `AgentController` state machine. Pseudocode (verbatim-ish):
```python
with self._state:
    if status in (IDLE, PAUSED, ERROR, STUCK): status = RUNNING
while True:
    with self._state:
        if status in (PAUSED, STUCK): break
        if status == FINISHED:
            if hook_processor:
                should_stop, feedback = hook_processor.run_stop(reason="agent_finished")
                if not should_stop:
                    on_event(MessageEvent(source="environment", ... "[Stop hook feedback] "+feedback))
                    status = RUNNING; continue
            break
        if stuck_detector and stuck_detector.is_stuck(): status = STUCK; continue
        if status == WAITING_FOR_CONFIRMATION: status = RUNNING   # user approved
        self.agent.step(self, on_event, on_token); iteration += 1
        if status == WAITING_FOR_CONFIRMATION: break
        if iteration >= max_iteration_per_run:
            if status == FINISHED: break
            status = ERROR; on_event(ConversationErrorEvent("MaxIterationsReached")); break
```
Notable (KNOWN):
- `with self._state:` acquires a **FIFOLock** (no thread-starvation under heavy `send_message`), defers all autosave I/O until `__exit__` — multiple mutations = ONE write (state.py:539-560).
- "**FINISHED is intentionally not checked at the bottom of the iteration**" — lets a concurrent `send_message` arrive between `status=FINISHED` and next iter, win the FIFO lock, reset to IDLE, get processed (local_conversation.py:838-851). (Reactivatable FINISHED.)
- `ConversationRunError` carries `conversation_id` + `persistence_dir` so user can resume.

### B4. The FSM: `ConversationExecutionStatus` (KNOWN — state.py:46-78) — 8 states
`IDLE` (initial, **explicitly NOT terminal** to avoid false positives when remote WS sends initial state), `RUNNING`, `PAUSED`, `WAITING_FOR_CONFIRMATION`, `FINISHED` (terminal but reactivatable by user message), `ERROR` (terminal), `STUCK` (terminal), `DELETING`.
(Verso uses StopReason enum on a simpler loop; OpenHands has an explicit 8-state FSM with a status field on persistent state. INFERRED: this is heavier than Verso's loop+StopReason but driven by their HITL/confirmation/remote-WS surface.)

### B5. Stuck detection (KNOWN — `stuck_detector.py`, `types.py:48-72`) — 4 heuristics
| Pattern | Default threshold | Trigger |
|---|---|---|
| `action_observation` | 4 | same action+observation pair repeated N times |
| `action_error` | 3 | same action then AgentErrorEvent repeated |
| `monologue` | 3 | N consecutive `MessageEvent(source="agent")` with no action |
| `alternating_pattern` | 6 | A↔B↔A↔B alternation N times |
When any fires → `status=STUCK`, loop breaks. (= Verso stuck/doom-loop detection. verso-already-has. The 4 named patterns + the `monologue` and `alternating_pattern` heuristics are a concrete checklist Verso could mine.)

### B6. The step lifecycle: `_ActionBatch` (KNOWN — agent.py:111-236)
`@dataclass(frozen=True, slots=True)`:
```python
class _ActionBatch:
    action_events: list[ActionEvent]
    has_finish: bool
    blocked_reasons: dict[str, str]       # hook-blocked actions
    results_by_id: dict[str, list[Event]]
```
3-stage lifecycle:
1. **`prepare(...)`**: `_truncate_at_finish()` finds any `FinishTool` call, truncates to `[:finish_idx+1]`, warn-logs discarded actions after it. For each action `state.pop_blocked_action(ae.id)` — `PreToolUse`-hook-blocked actions are skipped + reason recorded. Survivors dispatched via `ParallelToolExecutor.execute_batch(...)`; default sequential, `tool_concurrency_limit>1` enables thread-pool parallel (caveat: concurrent tools share fs/conv state, base.py:396-405).
2. **`emit(on_event)`**: emits in original action order; blocked actions emit `UserRejectObservation(rejection_source="hook")`; executed emit their observations.
3. **`finalize(...)`**: if batch ended in unblocked `FinishTool`, either `check_iterative_refinement` returns `(should_continue=True, followup)` → emit synthetic `MessageEvent(source="user", ...)` to nudge continue, OR `mark_finished()` → `status=FINISHED`. Subclasses (e.g. `ACPAgent`) substitute their own callables.

### B7. `Agent.step()` single-step entry (KNOWN — agent.py:474-602)
1. `pending_actions = ConversationState.get_unmatched_actions(state.events)`; if present → confirmation mode, execute approved waiting actions, return.
2. If `last_user_message_id` blocked by `UserPromptSubmit` hook → `status=FINISHED`, return.
3. `messages_or_condensation = prepare_llm_messages(state.events, condenser, llm)`; if a `Condensation` → emit + return (condenser ran first).
4. `make_llm_completion(...)`; on `FunctionCallValidationError` → emit `MessageEvent(role=user, text=str(e))` (reask); on `LLMMalformedConversationHistoryError`/`LLMContextWindowExceedError` → if condenser handles requests, emit `CondensationRequest()` + return, else raise.
5. `classify_response(message)` → TOOL_CALLS / CONTENT / REASONING_ONLY / EMPTY handlers.

### B8. Tool-call execution: `_get_action_event` / `_execute_action_event` (KNOWN — agent.py:755-948)
`_get_action_event` converts raw `MessageToolCall` → validated `ActionEvent`:
1. `parse_tool_call_arguments` (JSON-parse w/ error-mining).
2. `normalize_tool_call` (tool aliasing, fallback to `terminal`).
3. missing tool → `_emit_tool_error("Tool '{name}' not found. Available: {list}")`.
4. `fix_malformed_tool_arguments(arguments, tool.action_type)` — coerce types.
5. `_extract_security_risk(...)` — pop `security_risk` from LLM args, default UNKNOWN; read-only tools forced UNKNOWN; if no analyzer set, LLM value ignored.
6. `_extract_summary(...)` — pop `summary` field (always requested, optional).
7. `tool.action_from_arguments(arguments)` — pydantic validate vs schema.
8. Wrap in `ActionEvent(action, thought, reasoning_content, thinking_blocks, ..., security_risk, summary)`.
9. If critic configured → `_evaluate_with_critic` augments with `critic_result`.
`_execute_action_event` (worker thread when parallel): `tool(action_event.action, conversation)` → `Observation`; on `ValueError` returns `[AgentErrorEvent(error=...)]` so agent self-corrects; else `[ObservationEvent(...)]`. Main thread emits in order.
(All of this = Verso's jsonish 4-stage parse waterfall + coerce + tool error-as-observation + in-loop reask. verso-already-has. The split-thought/reasoning_content/thinking_blocks fields on the ActionEvent are richer than a flat message, but Verso streams typed deltas already.)

### B9. EventLog — file-backed event sequence (KNOWN — `event_store.py`)
Append-only sequence over a `FileStore` (local FS or in-mem). Key perf properties:
- `len(state.events)` is **O(1)**.
- `state.events[:N]` materialises only the prefix; "never use `list(state.events)` on large histories ('conversations can reach 30k+ events', agent.py:332-334)".

### B10. `get_unmatched_actions` — the resume/confirmation hook (KNOWN — state.py:472-512)
Scans events in **reverse**, returns `ActionEvent`s with no matching `ObservationEvent`/`UserRejectObservation`/`AgentErrorEvent`. **`AgentErrorEvent` is matched by `tool_call_id` (NOT `action_id`)** — critical for crash-recovery where an error was emitted after a server restart. Drives BOTH the confirmation flow AND crash recovery on resume (executed-but-unobserved actions are re-emitted).
**This is the closest analog to Verso's `repair_history` resume-guard (orphan tool-call/result repair).** verso-already-has — but the exact "match-error-by-tool_call_id-not-action_id" detail is a sharp crash-recovery edge case worth noting.

### B11. State persistence: `ConversationState.create()` open-or-create + `__setattr__` autosave (KNOWN — state.py:276-444)
- Single factory: if `persistence_dir` → `LocalFileStore(persistence_dir, cache_limit_size=max_iterations)`, else `InMemoryFileStore` (warns). Read `base_state.json`; if present → **resume path**: `model_validate(..., context={"cipher": cipher})` (decrypts encrypted MCP/secret fields), validate `state.id==id`, attach `EventLog`, **`agent.verify(state.agent, events)`** — checks runtime Agent class matches persisted + **no tools removed (tools may be ADDED)** (base.py:613-679). Persistent `stats` are KEPT not reset.
- `__setattr__` (state.py:399-444): on field change, if `autosave_enabled` and inside `with self._state` (`_save_depth>0`) mark `_dirty` (defer to `__exit__`), else `_save_base_state`; then fire `_on_state_change(ConversationStateUpdateEvent(key, value))` callback — which is how the WS `/events/{conversation_id}` stream broadcasts state changes to UI.
(= Verso SqliteCheckpointStore + resume() in fresh process + `repair_history` resume-guard. The `agent.verify` "tools may be added but not removed" invariant on resume is a clean rule Verso's resume-guard could mirror. The `cipher`/encrypted-secret-fields-in-state is extra.)

### B12. Condenser (KNOWN — `context/condenser/llm_summarizing_condenser.py:37`)
`LLMSummarizingCondenser`: `llm` (usually agent's own LLM w/ `usage_id="condenser"` for separate cost tracking), `max_size=240` (class default; **default-recipe uses `max_size=80, keep_first=4`**, preset/default.py:73), `keep_first=2` (never-condensed: system prompt + first user msg), `min_condense_fraction≈0.1` (≥10% must condense). Cycle: when needed, condenser returns a `Condensation` event instead of messages; `Agent.step()` emits it + returns; next iter sees condensed view. On `LLMContextWindowExceedError`/`LLMMalformedConversationHistoryError` → emit `CondensationRequest()` → forced condensation next iter. `_condense` prompts w/ `summarizing_prompt.j2`; summary role = `tool`; retained = `events[:keep_first] + [summary] + events[forgetting_end:]`. Others: `NoOpCondenser` (raises on overflow), `PipelineCondenser` (compose multiple).
**Verso NON-GOAL: no LLM-summarization-compaction-by-default.** OpenHands' DEFAULT recipe DOES summarize (every ~80 events). This is the same divergence as browser-use. (avoid-overkill — confirms Verso's `prune()`-masking-by-default stance is the minority/contrarian-but-deliberate position.)

### B13. Hooks + confirmation/security (KNOWN — agent.py:604-645, §4.2)
- `_requires_user_confirmation`: single Finish/Think never confirms; empty → no; if `security_analyzer` set, `analyze_pending_actions(...)` per-action risk else UNKNOWN; `state.confirmation_policy.should_confirm(risk)` → if any True, `status=WAITING_FOR_CONFIRMATION`. Policies: `NeverConfirm` (default), `AlwaysConfirm`, `ConfirmRisky` (med/high).
- Per-tool `security_risk` LOW/MED/HIGH labels; **Repository Context Supply-Chain Rules**: escalate to HIGH when action originates from `<UNTRUSTED_CONTENT>`/`AGENTS.md`/`.cursorrules`/`.agents/skills/` AND touches `pip.conf`/`.npmrc`/registry URLs/`curl|bash`/`~/.ssh`/install-hooks. Explicit defense vs malicious-AGENTS.md prompt-injection supply-chain attacks.
(= Verso Hooks pre/post_tool + PermissionDecision 4-valued + trust_tier + quarantine. verso-already-has. The named supply-chain escalation ruleset is a concrete trust-tier policy Verso could ship as an opt-in default policy, byte-identical-when-unused.)

### B14. Prompt cache (KNOWN — agent.py:388-407, local_conversation.py:194)
Static system message (`base.py:425-466`) is cacheable across conversations; dynamic part (secrets/skills/runtime) is a SECOND content block in the system message WITHOUT a cache marker so cached-prefix still hits. `_pin_prompt_cache_key()` walks `agent.get_all_llms()` and sets a stable `_prompt_cache_key` from conversation_id so prompt caching hits across RESUMES of the same conversation. (= Verso KV-cache-stable system prefix. verso-already-has. "stable cache key across resume of same conversation_id" is a sharp detail.)

---

## C. JUDGMENT — event-stream-as-state vs Verso message-history + checkpoint

KNOWN facts to weigh:
- OpenHands persists a **typed Event log** (14 event types) appended to `EventLog`, replayed on resume; state-mutation auto-saves via `__setattr__`; resume re-derives via `get_unmatched_actions` (match errors by `tool_call_id`). `len(events)` O(1), `events[:N]` lazy — built for **30k+ event** conversations.
- Verso persists **message history + step checkpoints** (`SqliteCheckpointStore`, checkpoint each step, `resume()` in fresh process, `history()`/`fork()`, `repair_history` resume-guard).

INFERRED verdict (on-thesis):
1. **They converge on the SAME guarantees** — crash-recoverable, resume-in-fresh-process, HITL pause/resume, time-travel. OpenHands gets there via event-sourcing + an 8-state FSM + frozen-pydantic-autosave; Verso gets there via message-history + per-step checkpoints + the tactical↔durable seam flag. Verso's is *strictly leaner*: no separate Event-type taxonomy, no FSM enum, no `__setattr__` autosave magic.
2. **Event-stream-as-state is NOT a steal.** It is a different SERIALIZATION of the same thing Verso already checkpoints. Adopting 14 typed Event classes + an EventLog + an 8-state FSM would be exactly the "force the graph / orchestrator-as-primitive" complexity Verso refuses. Verso's message-history is already the event log; the checkpoint is already the replay point. (avoid-overkill.)
3. **What IS worth mining (additive, byte-identical-when-unused):**
   - The `get_unmatched_actions` crash-recovery rule of matching error events by `tool_call_id` not `action_id` — a precise edge case for Verso's `repair_history` resume-guard to be correct after a mid-tool-call crash.
   - `agent.verify` on resume: "tools may be ADDED but not REMOVED" + "Agent class must match" — a clean resume-time invariant.
   - The 4 named stuck patterns (`action_observation`/`action_error`/`monologue`/`alternating_pattern`) as a concrete checklist for Verso's existing STUCK detector.
4. **Both OpenHands default-recipe AND browser-use default to LLM-summarization compaction** — directly opposite Verso's NON-GOAL. This is strong validation that Verso's `prune()`-masking-by-default is a *deliberate minority position*, not an oversight: the two biggest OSS agents both summarize by default. Verso should keep its stance but be aware it's swimming against the field.

---

## D. NON-GOAL confirmations (things NOT to copy)
- Indexed-DOM action grounding (browser-tool-specific).
- 14 Event types + EventLog + 8-state ConversationExecutionStatus FSM (orchestrator/graph-ish; Verso's loop+StopReason+checkpoint already covers it).
- `__setattr__`-autosave-on-frozen-pydantic magic (clever but implicit; Verso's explicit checkpoint-each-step is more legible).
- LLM-summarization-compaction-by-default (both ship it; Verso explicitly refuses it).
- 70-kwarg Agent constructor (browser-use) — config sprawl Verso should avoid.
