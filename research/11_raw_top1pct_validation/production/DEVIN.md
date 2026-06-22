# DEVIN — Raw Extraction (production track)

Source read: `/Users/seventyleven/Desktop/researchfms/teardowns/DEVIN.md` (2817 lines, 266 KB).
Focus: planning + long-horizon durable execution; planner/executor split; multi-hour task handling.
Each finding tagged KNOWN (verbatim from leak/bundle/API probe) vs INFERRED (teardown author's reconstruction).

---

## 1. Two-mode state machine — "planning" vs "standard" (the planner/executor split)

KNOWN (verbatim `Prompt.txt:41-52`):
> "You are always either in 'planning' or 'standard' mode. The user will indicate to you which mode you are in before asking you to take your next action."
> "While you are in mode 'planning', your job is to gather all the information you need... You should search and understand the codebase using your ability to open files, search, and inspect using the LSP as well as use your browser..."
> "Once you have a plan that you are confident in, call the `<suggest_plan ... />` command. At this point, you should know all the locations you will have to edit."
> "While you are in mode 'standard', the user will show you information about the current and possible next steps of the plan."

KNOWN mechanics (`Prompt.txt:57-60`, §2.2):
- **Planning mode allowed:** open files, search, LSP introspection, browse web, message user. **NOT allowed: code edits.**
- **Planning mode exit:** agent calls `<suggest_plan/>` — a **self-closing tag with NO args**. The plan content itself is conveyed via prior `<message_user>` calls; this tag is only the *request for user approval* (`§3.10`, line 294-296).
- **Standard mode:** user approved the plan; the current + next steps are **injected by Cognition's runtime each turn**.
- **Asymmetry:** agent enters planning mode by DEFAULT at start of each user request; agent NEVER self-promotes to standard mode — **the user must toggle it.** Code edits are gated behind explicit human plan-approval.

v1→v2 diff (KNOWN, §R2.2, lines 951/961):
- Devin 1.0 (March 2024, Claude 3 Opus): `<output_plan>...full plan text...</output_plan>` — plan body INLINE in the tag.
- Devin 2025: `<suggest_plan/>` self-closing signal + side-channel (`<message_user>`) for plan content.

Event-stream correlates (KNOWN, bundle `/tmp/devin-index.js`, §R2.8):
- `plan` — Devin's plan body (rendered as a step list)
- `plan_accepted` — user toggled planning → standard
- `user_update_master_plan` — **user edited the plan during planning mode** (human-in-the-loop plan editing)
- `set_mode` — explicit mode-switch event

INFERRED (§1, line 18): "the same pattern Antigravity formalized 18 months later — Devin invented it." Planning-mode gate later adopted by Antigravity, Cursor `plan first`, most enterprise coding agents.

---

## 2. Durable session lifecycle — the 6-state machine (KNOWN VERBATIM)

KNOWN (`qa-devin/devin_api_client.py:32-41`, §R2.5.1):
```python
status_enum: (
    Literal[
        "working",
        "blocked",
        "finished",
        "suspend_requested",
        "resume_requested",
        "resumed",
    ] | None
)
```
- `working` — agent actively running tool calls.
- `blocked` — agent awaiting user input (e.g. `<message_user request_auth="true">` or `<wait on="user">`).
- `finished` — agent reported completion (TERMINAL).
- `suspend_requested` — user sent "SLEEP" / session archived → orchestrator preparing to snapshot the VM.
- `resume_requested` — user sent "WAKE UP" / unarchived → orchestrator restoring VM from blockdiff snapshot.
- `resumed` — VM restored, agent loop resuming.

KNOWN: "The lifecycle proves session state is durable and recoverable via the `blockdiff`+`otterlink` snapshot path." Sleep/wake corroborated in `qa-devin/tests.py:111-117` and `:138-159` ("User types SLEEP → Devin replies → suspend_requested").

Significance for Verso: Devin's durability is **VM-disk-level** (whole OS snapshot), NOT event-sourced agent state. This is the opposite axis from Verso's checkpoint-the-step approach.

---

## 3. BlockDiff — VM-disk snapshotting (the durability substrate)

KNOWN (`github.com/cognition-labs/blockdiff`, §5.2, now-archived repo):
- Devin VMs snapshotted/restored using **block-level diffs** (block-device level, not filesystem level — "conceptually similar to Docker layer caching but at the VM block-device level").
- Each task starts from a base/golden snapshot (clean Ubuntu + pre-installed deps).
- During execution blockdiff captures VM state as a diff against the base.

KNOWN otterlink clone mechanism (§R2.6.2, line 1320): `cp --reflink=always` to clone the golden snapshot (instant, CoW) → boot via KVM → start the Devin agent loop. XFS on local NVMe with CoW + reflink enabled.

KNOWN storage split (§R2.6.2):
- `devin_customer_data_bucket` (S3) — repo/code/snapshot storage.
- `devin_hypervisor_storage_bucket` (S3) — blockdiff snapshot archive (long-term cold; local NVMe is ephemeral).

KNOWN infra constraint (§R2.6.2, line 1239-1243): ASG `suspended_processes = ["AZRebalance"]` — Cognition explicitly opts OUT of AWS AZ-rebalancing because every instance has live VMs with attached local-NVMe disk state that can't survive instance termination.

INFERRED (§5.2, §5.4): enables (a) fast resume after user closes browser, (b) parallel branch exploration (snapshot, try approach A, restore, try approach B), (c) reproducible replays. Idle timeout ~30 min → hibernate → blockdiff snapshot → restore on user message.

---

## 4. Event stream as source of truth — deterministic replay

KNOWN (§R2.8, line 1506):
> "The event stream is **the source of truth** for the Devin UI. The session can be replayed deterministically by replaying the event stream in order."
> Enables: (a) shareable public session URLs `app.devin.ai/sessions/{uuid}`, (b) Session Insights post-hoc analysis, (c) admin operator views (`admin/sessions/{id}/dump`, `.../timing-events`, `.../live-chain-status`).

Consumed via WebSocket (likely Socket.IO/raw WS, JWT-gated). `subscribe_devin` event confirms subscription model.

KNOWN event taxonomy (100+ types, bundle-verified). Durability/long-horizon-relevant ones:
- `progress_update` — Devin emitted a progress signal.
- `max_iterations_reached` — **agent loop hit the iteration cap (KNOWN failure mode — max-iterations safety termination).**
- `cancel_running_test_command` — Devin or user cancelled a long-running test.
- `declare_setup_level` — Devin declared completion of dev-env setup.
- `worklog` — **Devin's structured task log (right sidebar; persists across sessions in the Knowledge feature).**
- `system_event` — orchestrator-side (snapshot taken, VM restored, etc.).
- `multi_edit_result` — merge summary from `<find_and_edit>` dispatch.
- `tool_group` — batch of parallel tool calls.

Note: this is an event-sourced UI/replay log, but the AGENT's recoverable state lives in the VM snapshot, not (per evidence) reconstructed by replaying events into a fresh agent.

---

## 5. Multi-tool-call-per-turn with fail-fast (loop shape)

KNOWN (`Prompt.txt`, §2.6 line 101-108):
> "Output multiple actions at once, as long as they can be executed without seeing the output of another action in the same response first. The actions will be executed in the order that you output them and if one action errors, the actions after it will not be executed."
- Sequential ordering, **fail-fast** (subsequent calls aborted on first error). Same model as Anthropic parallel tool-use but explicit sequential ordering.

---

## 6. find_and_edit — sub-LLM fan-out refactor primitive (the "planner/executor" at edit granularity)

KNOWN (`Prompt.txt:176-177`, §3.6, §R2.4):
- `<find_and_edit dir="..." regex="..." exclude_file_glob="..." file_extension_glob="..."><edit instruction></find_and_edit>`
- Each regex match dispatched to a **SEPARATE sub-LLM** which independently decides: (a) make the edit, (b) `<no_edit reason="..."/>` skip (false positive), (c) variant edit.
- KNOWN constraint (verbatim): *"so it's no big deal to have false positive matches for your regex"* — confirms the 2-step decision: **edit-or-skip THEN write-the-edit**, one sub-LLM per location.
- Result returned to main agent as `multi_edit_result` event: *"Edited 7/12 matches. Files: a.py, b.py, c.py. Skipped 5 (false-positive regex hits)."*

INFERRED dispatch (§R2.4, §9.2): server-side fan-out, 8-32 concurrent calls (line 996); per-sub-LLM context 4-8K tokens (~200 lines around match); sub-LLM model = cheaper than main. Bundle's `ksi` array lists `opus-4.6-fast` first as `Asi=admin-side-conversation-model` → strong evidence find_and_edit sub-LLMs default to Opus 4.6 Fast.

This is the same shape as Verso's parallel-agent dispatch / Claude Code Task tool, but baked into ONE tool primitive.

---

## 7. Cross-task persistent memory — Knowledge / Playbooks / Notes / AGENTS.md

KNOWN (§R2.11, prompt+bundle+blog): **persistent per-org institutional memory** distinct from per-session conversation memory. Three layers:
1. **Knowledge notes** — short factual statements ("we use pytest-cov", "main branch is `main` not `master`", "deploys go through ArgoCD"). Stored as named records, **surfaced to Devin's prompt at session start.**
2. **Playbooks** — reusable task templates. Each playbook has: **outcome, steps, postconditions, advice, forbidden actions, required inputs.**
3. **AGENTS.md** — file-based repo knowledge (analogous to CLAUDE.md / .cursorrules).

KNOWN bundle features (§R2.11):
- Knowledge has folder structure, citations, **regen-on-staleness**, auto-generated suggestions (user dismisses/accepts).
- `knowledge_agentic_create` / `_update` / `_delete` — **Devin can autonomously propose changes to the knowledge base**; user reviews via Suggestions queue.
- Events: `knowledge_citation`, `knowledge_contents`, `knowledge_regen_request` (Devin asks runtime to regenerate a stale note), `note_used_group`, `playbook_triggered`, `playbook_retrieved`, `playbook_step_report` (per-step status during playbook execution).
- MCP tools: `devin_knowledge_manage`, `devin_playbook_manage` (CRUD).

KNOWN (blog verbatim): *"Devin automatically indexes your repositories every couple hours, creating detailed wikis..."*

INFERRED storage (§R2.11): Postgres rows (FastAPI/SQLAlchemy) + vector embeddings (OpenAI text-embedding-3 or Cohere/Voyage) for semantic note search → per-org RAG index surfaced at task start.

---

## 8. Wait / async / HITL semantics

KNOWN (`Prompt.txt:340`, §14.12):
```
<wait on="user/shell/etc" seconds="5"/>
```
- `on="user"` — block until user responds (the async "I'm done, ping me" signal; underlies Devin's async UX).
- `on="shell"` — wait for active shell process output.
- `<message_user request_auth="true">` — moves session to `blocked` state pending user input.

---

## 9. Long-horizon guardrails (anti-infinite-loop)

KNOWN (§3.8/§2.4, line 288): **3-attempt CI-failure rule** — explicit "don't loop forever" guardrail; combined with a "report environment setup issue" affordance and `<kill_shell_process>` (SIGKILL stuck/runaway processes, line 176). "Devin has explicit affordances for 'I'm stuck, ask the user' that prevent infinite retry loops."

KNOWN: `max_iterations_reached` event = hard iteration cap on the agent loop (safety termination).

The mandatory `<think>` tool (§2.3) lists 10 trigger situations including: "(2) When transitioning from exploring code... to actually making code changes. You should ask yourself whether you have actually gathered all the necessary context, found all locations to edit, inspected references..."

---

## 10. Automations / Scheduled Sessions / triggers (long-horizon autonomy)

KNOWN (§R2.5.3, §R2.17):
- `POST /v1/automations` — create trigger (event: PR opened, Slack mention, scheduled cron, Linear ticket label change). `GET`/`PATCH (pause/resume)`/`DELETE`.
- **Scheduled Sessions**: cron schedules ("every weekday at 9am", "1 hour after deploy") auto-trigger Devin with fixed prompt + repo context. MCP tool `devin_schedule_manage`.
- **Auto-Triage**: bug ticket lands → automation fires `!triage-bug` playbook → Devin investigates → posts root cause + fix.
- INFERRED scheduler: Temporal or APScheduler reading `automations`/`scheduled_sessions` tables.

---

## 11. Session Insights — post-hoc analysis / prompt-iteration loop

KNOWN (blog verbatim, §R2.16): analyzes COMPLETED sessions; examines issues/challenges, session timeline w/ efficiency metrics, action items, and **"Improved prompt suggestions with enhanced instructions"** — "We can spin up new sessions directly from the insights using the improved prompts." After `status_enum='finished'` → orchestrator enqueues a Session Insights job that reads the full event stream and emits a rewritten prompt → one-click re-run.

---

## 12. Concurrent Devins (multi-agent)

KNOWN (blog `devin-2` verbatim, §R2.10): *"Spin up multiple parallel Devins, each equipped with its own interactive, cloud-based IDE... tackling numerous tasks concurrently and stepping in to steer when needed."*
Throughput datapoint (§R2.10): 659 PRs/week ≈ 95/day ≈ 1 every 15 min into Cognition's own codebase → INFERRED 50-100 concurrent agents.
`monitor_session` event = "Devin watching another Devin".

---

## 13. Models / infra numbers (context)

- Main agent: Claude Sonnet-class; sub-agents historically Claude Haiku 3.5 (§5/§7), current bundle default side-conversation = `opus-4.6-fast`. Current frontier tiers (line 1386): GPT-5.5 + Claude Opus 4.8.
- DeepWiki Q&A budget: 200,000 tokens (input+output), runtime-enforced (§4, §14.18).
- Bare-metal EC2 `i3.metal`/`i3en.metal`/`i4i.metal` (KVM direct, no nested-virt penalty); 256 GB gp3 root; local NVMe holds VM disks + blockdiff snapshots.
- Stack: FastAPI + uvicorn; `/v1` customer API + `/admin` internal cockpit.

---

## Verso seam mapping (does no-graph durable seam cover Devin-style long horizons?)

- **Planner/executor split (planning vs standard mode):** Verso has plan-gate intent via HITL (`ctx.hitl.request` pause/resume) + Hooks `should_continue`/`ask` + PermissionDecision (allow/deny/ask/defer). Verso can gate edits behind human approval WITHOUT a separate "mode" primitive or a graph. Devin's two-mode FSM is a UX convention; Verso achieves the same gate additively. NOT a gap.
- **Durable 6-state lifecycle:** Verso's durable seam = SqliteCheckpointStore + checkpoint-each-step + resume() in fresh process + history()/fork(). Devin's suspend/resume is VM-disk snapshot (blockdiff), a heavier substrate for a different reason (full Linux sandbox). Verso's per-step event-sourced checkpoint COVERS the agent-state durability; it does NOT (and should not) snapshot a whole VM — that's an environment concern, not a framework concern.
- **Branch/fork time-travel:** Devin's "snapshot, try A, restore, try B" = Verso's `fork()` + `history()`. Verso already has this.
- **Cross-task memory (Knowledge/Playbooks):** Verso ships typed 4-tier memory + RRF recall + recall_as_of + reflect(). Playbooks-as-structured-templates and AGENTS.md-as-loaded-knowledge map to Verso scaffolds (load_skills) + memory. Verso-already-has.
- **Long-horizon guardrails:** Devin's max_iterations + 3-CI-fail + "I'm stuck → ask user" == Verso's StopReason.STUCK / doom-loop detection / max_steps grace-call / done() + Hooks. Verso-already-has.
- **Event stream as source of truth + deterministic replay:** Verso has VersoSpan + OTel + from_trace + checkpoint replay. Devin's UI event log is a different thing (UI rendering), but the replayable-source-of-truth idea Verso already has via checkpoints.
