# CURSOR + CODEX — Raw Extraction (production track)

Sources read (bounded reads, grep-first):
- `/Users/seventyleven/Desktop/researchfms/teardowns/CURSOR.md` (4,659 lines / 287 KB)
- `/Users/seventyleven/Desktop/researchfms/teardowns/CODEX.md` (7,145 lines / 540 KB)

Each finding tagged KNOWN-from-source / INFERRED / DESIGNED as the source itself tagged it. Verso-relation tagged against current shipped state.

---

## A. APPLY / EDIT MODEL

### A1. Codex `apply_patch` — model-friendly structured diff (KNOWN, CODEX §5)
- Crate `codex-rs/apply-patch/` (4,384 lines / 7 files). OpenAI's "flagship contribution": "a model-friendly diff format that's simpler than unified diff but more robust than raw before/after pairs."
- **Grammar is 14 lines of Lark BNF** (`apply_patch.lark`) — the single source of truth. Six markers:
  - `*** Begin Patch` / `*** End Patch` (envelope)
  - `*** Add File: <path>` (then `+` lines), `*** Delete File: <path>` (no body), `*** Update File: <path>` (then chunks)
  - `*** Move to: <path>` (rename inside Update), `*** End of File` (EOF anchor)
  - Inside change chunks: `@@ <signature>` anchor, then `+`/`-`/` ` add/remove/context lines.
- `Hunk` enum = `AddFile{path,contents}` | `DeleteFile{path}` | `UpdateFile{path, move_path, chunks: Vec<UpdateFileChunk>}`. Chunks are **ordered by source position** — parser enforces "the change_context of one chunk should occur later in the file than the previous chunk" (a forward-only seek pointer invariant).
- **Strict vs lenient**: `const PARSE_IN_STRICT_MODE: bool = false;` hardcoded. Comment: "the only OpenAI model that knowingly requires lenient parsing is gpt-4.1... it is a pain to thread it through all of the call sites, so we resign ourselves allowing lenient parsing for all models." A **one-way ratchet** — one model needed lenience, every caller got it.

### A2. The fuzzy seek algorithm — "the secret sauce" (KNOWN, CODEX §5.5)
`seek_sequence(lines, pattern, start, eof)` finds the chunk's `old_lines` in the file. **5 tiers of decreasing strictness:**
1. **Exact** slice equality.
2. **rstrip** — ignore trailing whitespace per line.
3. **trim** — ignore leading AND trailing whitespace.
4. **Unicode normalization** — comment: "mirrors the fuzzy behaviour of `git apply`." Maps smart dashes `‐-―,−`→`-`, single quotes `‘-‛`→`'`, double quotes `“-‟`→`"`, Unicode spaces (` , - , , ,　`)→ASCII space.
5. **EOF start** — if chunk ended with `*** End of File`, search starts at `lines.len()-pattern.len()` (the actual file end), falling back to `start`.
- Defensive: empty pattern → `Some(start)` no-op; `pattern.len() > lines.len()` → `None` (notes a pre-2025-04-12 panic from OOB slicing).
- **Handled failure modes**: indentation drift (tier 3), smart quotes from copy-paste (tier 4), trailing-whitespace auto-strip (tier 2), last-line newline diff (eof). **NOT handled**: a non-context line in the middle changed; lines reordered.
- **Why it matters (verbatim):** "It's the difference between `apply_patch` and naive search-and-replace." Lets the model emit stale/imperfect context lines and still apply.

### A3. apply_patch invocation surface + error taxonomy (KNOWN, CODEX §5.8)
- `maybe_parse_apply_patch_verified(argv, cwd) -> MaybeApplyPatchVerified`. Result variants: `Body(action)` (clean), `ShellParseError`, `CorrectnessError(ApplyPatchError)`, `NotApplyPatch`.
- `ApplyPatchError`: `ParseError`, `IoError`, `ComputeReplacements(String)` (seek couldn't locate the chunk — model's old_lines match nowhere), `ImplicitInvocation` ("patch detected without explicit call to apply_patch. Rerun as ['apply_patch', '<patch>']").
- **Dual-mode binary** (§5.9): `CODEX_CORE_APPLY_PATCH_ARG1 = "--codex-run-as-apply-patch"`. The codex binary self-execs with this flag to run apply INSIDE a sandbox — "the same binary in a different mode." Sandbox needn't know apply_patch as a separate program.
- **Streaming parser** (`streaming_parser.rs`, 813 lines): consumes patch bytes incrementally over tool-arg deltas, emits `PatchApplyUpdated` events so the TUI renders the patch as it's authored ("typewriter-effect patch display"). More lenient than batch parser — partial hunks valid mid-stream.
- LLM-facing teaching prompt `apply_patch_tool_instructions.md` bundled at compile time, shipped to gpt-4.1 in the system prompt.

### A4. Cursor Fast Apply — separate model, separate service (KNOWN, CURSOR §7, §6)
- **Apply is a fine-tuned Llama-3-70B** (`llama-70b-ft-spec`), served via Fireworks AI **speculative decoding**, DISTINCT from the planner model (Claude/GPT-5/Composer 2). Throughput ~1,000 tok/s (~3,500 char/s); **~13x** over vanilla Llama-3-70B, **~9x** over the prior GPT-4 speculative-edits deployment.
- Spec-decode mechanism: "users speculate a larger number of tokens in parallel... server finds the longest prefix of the 'speculation' field that matches the model's generation with temperature=0, then continues with standard generation." **Why it works for apply**: "Apply is not creative — the planner has already decided what the edit is." The original file is ~95% of the output: "copy the original until you hit the diff zone, then emit the new tokens, then resume copying." Typical ~1500ms apply for a 500-line file.
- **`FastApplyService` is a top-level service** in Cursor's 57-service mesh, NOT a method on AiService. Chat model emits a "proposed change"; IDE intercepts and routes to a separate apply call; apply produces final patched file; IDE syntactic-validates and shows the diff. **Apply invoked atomically on a full-file diff, not chunk-by-chunk** (KNOWN: "there is no `ApplyContent` or `ApplyChunk` type").
- `ApplyAgentDiffParams` inputs (KNOWN structural + DESIGNED): `original_file_content: bytes`, `proposed_diff: string` (unified diff OR `// ... existing code ...` placeholder form), `file_path`, `language` (for syntax validation), `apply_source: FastApplySource`, `agent_context`.
- `FastApplySource` enum (DESIGNED values): COMPOSER / CMD_K / TAB_FOLLOWUP / AGENT_TOOL / BACKGROUND_COMPOSER — **server selects different prompts (and possibly models) per source** because each needs different behavior (Cmd-K must preserve everything else byte-exact; agent-tool apply must be deterministic for safe retries; CI apply must produce a committable diff). "at least 5 apply modes."
- Fine-tune teaches: recognize the `// ... existing code ...` placeholder, preserve byte-exact whitespace/ordering of unchanged lines, **reject diffs that would produce invalid syntax (refuses to apply, returns error)**.
- `reapply` tool: "Calls a smarter model to apply the last edit" — invoked when `edit_file` produces wrong output.
- **Shadow Workspace** (§7.1): hidden Electron window (`show: false`) running LSP-based lint on in-memory `TextModel` objects (not disk). Feedback loop: apply → shadow workspace runs linter → lint output fed back to planner → planner decides whether to `reapply`. Parallel agents share ONE shadow window — requests interleaved, "AI agent processes are paused an indefinite amount of time without even noticing." gRPC+buf IPC.

---

## B. CONTEXT / RETRIEVAL

### B1. Cursor codebase indexing — Merkle incremental (KNOWN arch, CURSOR §7)
- IDE-side client = `cursor-retrieval` extension; server = `repo42.cursor.sh` embedding/chunk store + `CodebaseSnapshotService` + `FastSearchService`.
- **Merkle tree trick**: hash each file (`file_hash`) and each chunk (`chunk_hash`); build Merkle tree (chunks=leaves, files/dirs=inner nodes, repo-root=top); on save recompute up the tree; **send only roots first** to server; if root hashes differ, walk down and **re-embed only changed chunks**. A 50k-file repo costs only the re-embed of `<100` chunks even after a meaningful refactor.
- `repo_query_auth_token` = per-repo token scoping the indexing backend; "Cursor's server cannot read a repo unless the IDE provides this token, generated client-side and stored encrypted on the server."
- **Multiple chunkers** (`chunking_strategies` plural, KNOWN naming): AST-aware (tree-sitter) for code, section-based for markdown, top-level-key for YAML/JSON, sliding-window for prose, skip binaries. `rechunker` re-processes when the strategy itself changes (server pushes new chunker → clients re-chunk).
- **Two ignore files**: `.cursorignore` (NOT sent to AI at all — privacy/secrets) vs `.cursorindexingignore` (lexically searchable but NOT semantically indexed — e.g., minified bundles). `.gitignore` auto-respected.

### B2. Cursor hybrid search + agentic retrieval (KNOWN, CURSOR §7.5, §7.7)
- **Hybrid planes**: Lexical (bundled `rg`, runs in IDE) | Semantic (`repo42` vector store via `FastSearchService.StartFastSearch`) | Symbol (LSP `textSearchProvider2`) | Web. Semantic flow: embed query → top-K nearest chunks → optional cross-encoder rerank.
- **Deep Search subagent** (`DeepSearchSubagentParams{query, max_iterations, scope}` → `DeepSearchSubagentReturnValue{summary, cited_files, raw_chunks}`): "**deep retrieval is done by a sub-agent**, not a single retrieval call." It runs ITS OWN ReAct loop: search → read → search-again → read-again → synthesize. "agentic retrieval — not a one-shot embed/search/rerank." `DeepSearchStream` streams progress ("looking through 47 files...").
- Vector store identity is DESIGNED/unconfirmed: bundle has no `turbopuffer`/`pgvector`/`qdrant` string hits; best guess "Turbopuffer for vector + S3 for raw chunk storage, Cursor's own service mesh fronting both."

### B3. Codex context injection per turn (KNOWN, CURSOR §13 / CODEX §3.2, §7, §9)
- Cursor injects per turn: open files + cursor position, recently viewed files, edit history, linter errors, always-on `.cursor/rules/*.md`, dynamically-loaded `SKILL.md`, memories.
- Codex system prompt composed at runtime (§7): **base instructions + approval-policy fragment + sandbox-mode fragment + AGENTS.md hierarchy + skill injections + plugin injections + environment context**. Approval/sandbox fragments are separate `.md` files dynamically inserted per current policy (e.g. `on_request.md`, `workspace_write.md`) — "the model is told 'you can/cannot escalate' depending on which file is loaded."
- **AGENTS.md hierarchy** (CODEX §16): root-to-cwd walk; filename precedence; `AGENTS.override.md` local override. **Byte budget** `project_doc_max_bytes` (default ~20-40K): when exhausted, subsequent files skipped entirely; boundary file `data.truncate(remaining)`; `tracing::warn!` logs "Project doc {} exceeds remaining budget ({} bytes) - truncating." `instruction_sources()` surfaces exactly which files influence the model (shown in `/status`, `/debug-config`).
- Tool-output truncation: `truncation_policy: TruncationPolicyConfig` default `bytes(10_000)`; per-turn `TruncationPolicy::Bytes(usize) | Tokens(usize)`.

---

## C. LOOP SHAPE

### C1. Codex `run_turn` — classic ReAct + auto-compaction, NO max-iterations (KNOWN, CODEX §3)
- Loop lives in `session/turn.rs` (2,274 lines); `RegularTask::run` (87 lines) wraps it in a **continuation loop** ("keeps calling `run_turn` while the user has piped in more input mid-turn. Each call to `run_turn` IS one ReAct cycle").
- **Phase B ReAct loop per iteration**: drain pending input (hook-inspected, Accepted/Blocked/re-queued) → build sampling input `clone_history().for_prompt(&model_info.input_modalities)` (drops images if model text-only) → sample (`run_sampling_request` returns `{needs_follow_up, last_agent_message}`) → auto-compact decision → end-of-turn path (stop hooks) → continue if `needs_follow_up`.
- **Stated architecture (verbatim §3.3):** "This is a **classic ReAct loop with auto-compaction** — NOT plan-execute." `needs_follow_up` boolean drives continuation. "There's no separate planning phase; the model can call the `plan` tool... but that's just one tool among many — `update_plan` events fire mid-loop, not before it."
- **Termination**: `!needs_follow_up` && no pending input && stop-hook approves → break; token limit && !needs_follow_up → break; `Op::Interrupt` cancels `CancellationToken` → break; hook `should_stop` → break; error → break.
- **"Implicit max-iterations: NONE. The loop runs as long as the model keeps emitting tool calls. The only safety nets are token budgets (auto-compact) and the cancellation token."**
- Auto-compact: triggers at `total_usage_tokens >= auto_compact_limit` (from `model_info.auto_compact_token_limit()`, default `i64::MAX` = never) && `needs_follow_up`, mid-turn, `CompactionReason::ContextLimit`. Comment: "as long as compaction works well in getting us way below the token limit, we shouldn't worry about being in an infinite loop." `effective_context_window_percent: 95` = trigger at 95% (5% margin).
- Error recovery `InvalidImageRequest` = **sanitize-and-retry**: replace last-turn images with `"Invalid image"` placeholder, continue.
- Public entry `CodexThread::submit(op) -> CodexResult<String>`; submissions → `mpsc::UnboundedSender<Submission>`; events → `broadcast::Sender<Event>` (TUI + telemetry + recorder subscribe).
- 4 `SessionTask` impls: RegularTask / CompactTask / UserShellTask / ReviewTask, each with `kind()`, `span_name()` (tracing), `records_turn_token_usage_on_span()`, `run()`.

### C2. Cursor agent loop — same tool-use loop, loop_limit on stop hook (INFERRED, CURSOR §13)
- "Cursor's agent loop is a **tool-use loop** — identical pattern to Claude Code and Codex CLI." Steps: input+context → model emits 0+ tool calls → execute (parallel where safe) → append results → hooks fire → loop → 0 tool calls ends turn → stop hook → if `followup_message` returned, inject as new user message and loop.
- "No explicit plan-execute separation at the loop level. Planning happens inside the model's reasoning." v1.2 prompt: "if you make a plan, immediately follow it, do not wait for the user to confirm."
- "No hardcoded max iterations in the agent loop itself — the only limit is the `loop_limit` on the `stop` hook" (default 5).

### C3. Codex Op/EventMsg wire protocol (KNOWN, CODEX §2)
- `Op` enum 28 variants (`#[non_exhaustive]` — "clients must handle unknown variants gracefully"); `EventMsg` ~70 variants. Every type derives `JsonSchema` (schemars, "self-documenting") + `TS` (ts-rs, mechanical TypeScript bindings). Legacy V1 wire `task_started` aliases V2 `turn_started`.

---

## D. MODEL ROUTING

### D1. Codex model selection / provider abstraction (KNOWN, CODEX §8)
- `ModelInfo` struct fields incl: `slug`, `default_reasoning_level` + `supported_reasoning_levels`, `shell_type` (Default vs `container.exec`), `supported_in_api` (false = ChatGPT-only), `service_tiers`, `apply_patch_tool_type` (`Function` vs `FreeForm` for older models), `truncation_policy` (default bytes(10_000)), `context_window`/`max_context_window` (272,000 default for gpt-5 family), `auto_compact_token_limit` (None=never), `effective_context_window_percent` (95), `input_modalities`, `supports_parallel_tool_calls`.
- **Six per-model system prompt files** shipped (gpt-5-codex, gpt-5.2, gpt-5.2-codex, gpt-5.1-codex-max, gpt-5.1, prompt_with_apply_patch_instructions for gpt-4.1) + fallback `default.md`. BASE_INSTRUCTIONS = generic prompt for any model without an override.
- **Personality system** (template `{HEADER}\n\n{{personality}}\n\n{BASE}`): `personality_default` (""), `personality_friendly`, `personality_pragmatic`. Chosen via `Op::UserTurn{personality}`.
- `ReasoningEffortConfig`: `Minimal|Low|Medium|High`. `service_tier: Option<Option<String>>` (double-Option: Some(Some)=set, Some(None)=clear, None=keep) — `flex|priority|default|scale`.
- **`EventMsg::ModelReroute`**: when backend swaps model (e.g. quota exhaustion → fallback), emits informational reroute event; **"the turn continues with the new model."** `ModelVerification` event = backend recommends extra account verification (2FA/email).
- Provider abstraction: API key (env/keyring/config), ChatGPT OAuth, AWS (Bedrock), device-key; local `lmstudio/` (`localhost:1234`) + `ollama/` (`localhost:11434`) crates.

### D2. Cursor model routing — per-mode + two-model pipelines + best-of-n (INFERRED/KNOWN, CURSOR §10)
- "The five-layer harness (Interface → Orchestration → Execution → Verification → Output) is model-agnostic. The model is below all five layers. Swapping the LLM doesn't change harness behavior."
- Per-mode routing: Agent = user-selected/auto; **Explore + Bash subagents = faster/cheaper model** (KNOWN docs: "using faster models for parallel searches"); Apply = always Llama-3-70B; shadow-workspace lint = no LLM.
- **Plan-then-execute two-model pipeline** (changelog 2.0): "Create your plan with one model and build the plan with another."
- **`/best-of-n` racing**: dispatch SAME task to N models simultaneously, one per isolated worktree, results side-by-side, user cherry-picks. "Composer 2 vs. Claude vs. GPT."
- Composer modes Ask/Manual/Agent gate tool surface + routing per-message (server stateless on this dim; client sends new capability context, no session reset).

---

## E. DURABLE / RELIABILITY PATTERNS

### E1. Codex rollouts — JSONL event-sourced session log (KNOWN, CODEX §10)
- Every session = JSONL rollout at `~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl` (date hierarchy "for filesystem performance — a heavy user could have thousands of sessions; flat directories degrade").
- `RolloutItem` enum (5 variants, `#[serde(tag="type", content="payload")]`): SessionMeta / ResponseItem / Compacted / TurnContext / EventMsg. Each line = `RolloutLine{timestamp, item}`.
- **`SessionMeta`** (first line) snapshots: id, `forked_from_id`, cwd, originator, cli_version, base_instructions snapshot (for reproducibility), dynamic_tools inventory, agent_role/nickname/path, plus `git: GitInfo{commit_hash, branch, repository_url}` at session start.
- **`TurnContextItem`** = "complete settings snapshot per turn" (approval_policy, sandbox_policy, network, model, personality, effort, user/developer instructions, final_output_json_schema, truncation_policy). Comment: "Persist once per real user turn... and again after mid-turn compaction... so resume/fork replay can recover the latest durable baseline." "`--resume` can re-establish exact policy state at any point."
- **`CompactedItem{message, replacement_history: Option<Vec<ResponseItem>>}`**: compaction writes a rollout item, replaces in-memory history with replacement_history. `From<CompactedItem> for ResponseItem` — summary becomes an assistant message the model sees post-compact.
- **Resume**: replay rollout line-by-line, restore state; on `Compacted`, `replacement_history` IS the history (skip earlier ResponseItems). **Fork** (`/fork`): new rollout file, new id, `forked_from_id = original.id`, state copied up to fork point.
- **Persistence policy** (`policy.rs`): `is_persisted_rollout_item` — SessionMeta/TurnContext/Compacted always; ResponseItem filtered (`should_persist_response_item` drops streaming deltas); EventMsg filtered by `EventPersistenceMode`. "the rollout is a CURATED subset of the wire stream... not bloated with delta tokens. The full event stream goes to telemetry; the rollout goes to persistence."
- Separate **SQLite state DB** (`state_db.rs`, 668 lines) indexes sessions for fast list/search (session_id→path, ts, cwd, model, branch, summary).
- **Mechanical truncation** (`thread_rollout_truncation.rs`): when rollouts huge, drops the middle, preserves SessionMeta + early context + recent turns — distinct from model-summarization Compact.

### E2. Cursor server-side resume + idempotency keys (KNOWN/DESIGNED, CURSOR §3.1, §3.5)
- `StreamUnifiedChatRequestWithToolsIdempotent`: "the request carries an **idempotency key**, so retries on connection drop don't double-execute side-effecting tools (write_file, run_command). This is how Cursor 3 makes Composer crash-resilient — the older WithTools could double-write a file if the SSE stream broke at the wrong moment."
- **Server-side resume**: `PauseBackgroundComposerRequest`/`ResumeBackgroundComposerRequest`, `AttachBackgroundComposerLogsResponse`, `AddAsyncFollowupBackgroundComposerRequest`. Close laptop → SSE drops → reopen hours later → client calls Attach with saved BC ID → "server re-attaches to the still-running pod, replays the last N events, resumes streaming." Contrasted: Claude Code = no resume; Codex CLI = resume only via local rollout files; Cursor = server-side.

### E3. Codex ToolOrchestrator — approval → sandbox → escalate-retry (KNOWN, CODEX §5.8)
- `ToolOrchestrator.run(...)` flow: **STEP 1** pre-flight approval (`ExecApprovalRequirement::Skip|Forbidden|NeedsApproval`; permission-request hooks have **top precedence**, then guardian reviewer, then user prompt) → **STEP 2** select sandbox for first attempt (`select_initial` from fs+network policy) → **STEP 3** first attempt under sandbox → **STEP 4** on `SandboxErr::Denied`, if `tool.escalate_on_failure()` && `wants_no_sandbox_approval`, ask approval → **STEP 5** second attempt with `SandboxType::None`.
- `ReviewDecision` variants: Denied/Abort/TimedOut/Approved/ApprovedForSession/ApprovedExecpolicyAmendment/NetworkPolicyAmendment{Allow|Deny}.
- `ToolHandler::is_mutating` "must be **defensive — return true if any doubt**" (drives sandbox selection).

### E4. Codex Ghost Commits — undo via detached git commit, temp index (KNOWN, CODEX §5.9)
- `git-utils/src/ghost_commits.rs`. Snapshot uses a **TEMPORARY git index** (`$GIT_INDEX_FILE=/tmp/codex-git-index-xxx/index`), never touches user's real index: `git read-tree HEAD` → `git add --all` → `git write-tree` → `git commit-tree <tree> -p <parent> -m "codex snapshot"` (**detached, no ref update → invisible in branch history**).
- Stores commit_id + parent (HEAD SHA) + preexisting untracked files/dirs. Excludes files >10 MiB, dirs >200 files (but preserves on restore). Always-ignored dirs: node_modules, .venv, venv, env, .env, dist, build, .pytest_cache, .mypy_cache, .cache, .tox, __pycache__.
- Restore: `git restore --source <commit> --worktree -- <prefix>` (intentionally avoids `--staged` to preserve user's staged changes; removes new untracked files not in snapshot).

### E5. Codex approval modes + auto-approval gate (KNOWN, CODEX §7)
- `AskForApproval`: UnlessTrusted / OnFailure(deprecated) / OnRequest(default) / Never; per-mode prompt fragments dynamically inserted into system prompt.
- `is_safe_command()` (`safety.rs`, 197 lines): conservative read-only allowlist (`ls cat head tail pwd wc file which tree`, read-only `grep`/`rg`, `find` no `-exec`, `git status/log/diff`). Rejects `sed` entirely, interpreters (`python node bash -c`), network (`curl wget nc ssh`), shell metacharacters (`$(...)`, backticks, `>`, `>>`, pipes). "heavily false-positive (ask too much) over false-negative."
- `Granular(GranularApprovalConfig)` 5 booleans (sandbox_approval, rules, skill_approval, request_permissions, mcp_elicitations); when a category is false, requests are **auto-rejected, not shown** — lets a managed org ban specific approval flows.
- `request_permissions` tool: model calls mid-turn to request file/network elevation for the rest of the turn ("I need write to /tmp/foo and outbound to pypi.org"); user grants (optional persistence) or denies. "granular, in-flight elevation path — distinct from approval policy which gates whole commands."

---

## F. OVERKILL SIGNALS (complexity Verso must refuse)
- Cursor's **57-service gRPC mesh**, dual streaming planes (legacy `StreamChat*` + new `StreamUnified*`) mid-migration, Anyrun/Firecracker VM-per-agent, server-side vector store (repo42), three-tier streaming RPC family, **~80-tool registry** (Cursor 3.x), 50+ BackgroundComposer RPC methods. Production IDE-scale; Verso is a library.
- Codex: 3 independent sandbox backends (Seatbelt SBPL / bubblewrap / seccomp+Landlock), Windows AppContainer, 6 per-model prompt files, 49 slash commands, separate SQLite session index + JSONL + telemetry stream + mechanical-truncation, multi-agent v1+v2 + Mailbox + AgentRegistry concurrency control. The single-agent loop is ~200 lines of intent; the rest is product surface.
- Cursor separate **fine-tuned apply model + Fireworks spec-decode + shadow-workspace LSP loop** — a whole model-training + inference-infra commitment Verso (a harness, not the model/kernel) must not own.
