# OSS Coding Agents — Verso Research Note
## Cluster: coding-oss-agents
### Systems: opencode (SST) · Aider · Cline · Roo Code · Goose (Block) · Continue.dev · Qodo · Augment Code
*Sources: live clones (depth=1, 2026-06-05) of `sst/opencode`, `Aider-AI/aider`, `cline/cline`, `RooCodeInc/Roo-Code`, `block/goose`, `continuedev/continue`; npm `@qodo/gen`; `api.augmentcode.com/mcp` probes + `docs.augmentcode.com`. Cross-refs: `coding-claude-code.md` (subagent/compaction/permission), existing `teardowns/OPENHANDS.md` / `SOURCEGRAPH_AMP.md` / `ANTIGRAVITY.md`.*

This note REs the OSS coding agents NOT already covered, with one goal: extract the exact mechanisms Verso (async Python ReAct framework) needs — compaction/overflow trigger math, plan/act HITL state machine, repo-map budget-aware context selection, the diff-format taxonomy, Boomerang sub-task context isolation, doom-loop guards, and checkpoint/undo. Every claim is labelled **KNOWN** (file:line from the clone), **INFERRED** (from probing/docs), or **DESIGNED** (Verso's gap-fill). Where another teardown already covers a pattern (Claude Code subagents, OpenHands condenser), this note cross-references rather than repeats.

---

## opencode (SST)

### What It Is

opencode is a TypeScript/Bun terminal coding agent built on the **Effect** runtime with a strict client-server split: an `opencode serve` process owns the agent loop + SQLite/Drizzle session store, and TUI / VS Code / web clients connect over HTTP+SSE (or ACP JSON-RPC for editors like Zed). The architecturally interesting parts are all server-side: the `SessionPrompt.runLoop()` state machine, the overflow→compaction pipeline, the `ProviderTransform` normalization layer that lets one uniform loop drive ~20 provider SDKs, and a Drizzle schema that makes the session genuinely durable. This is the closest existing thing to what Verso wants to be in Python, so it gets the deepest treatment.

The session code lives in two packages: `packages/opencode/src/session/` (the live v1 loop) and `packages/core/src/session/` (v2 event-sourced migration in progress, gated by `flags.experimentalEventSystem`). The authoritative loop is the v1 one in `packages/opencode`.

### The Loop — `SessionPrompt.runLoop()` (KNOWN, `session/prompt.ts:1217-1473`)

The loop is **not** a flat ReAct `while`. It is a single-message-at-a-time dispatcher over a queue of "parts" attached to the latest user message, with **four branch types checked in priority order every iteration**. The full `while(true)` body:

```
1. status.set(sessionID, "busy"); load msgs = filterCompactedEffect(sessionID)   // drops hidden/compacted msgs
2. { lastUser, lastAssistant, lastFinished, tasks } = MessageV2.latest(msgs)
3. EXIT CHECK: if lastAssistant.finish is set AND finish ∉ {"tool-calls"} AND
   no live tool calls AND lastUser.id < lastAssistant.id  →  break   (normal end_turn)
     - "hasToolCalls" recomputed by scanning parts: a tool part that is not providerExecuted
       and not an orphaned-interrupted tool. Some providers send finish="stop" while still
       emitting tool calls; the loop keeps running so tool results get fed back. (prompt.ts:1240-1266)
4. step++; if step===1 → fork title-generation (small model) + summary in background
5. const task = tasks.pop()                       // SubtaskPart | CompactionPart, LIFO
6. BRANCH A — task.type==="subtask":   handleSubtask(...) ; continue           // sub-agent dispatch
7. BRANCH B — task.type==="compaction": compaction.process(...) ; if "stop" break else continue
8. BRANCH C — OVERFLOW GATE:  if lastFinished && lastFinished.summary!==true &&
        compaction.isOverflow({tokens:lastFinished.tokens, model})  →
        compaction.create({auto:true}); continue    // enqueues a CompactionPart, re-loops into BRANCH B
9. BRANCH D — NORMAL TURN:
     maxSteps = agent.steps ?? Infinity ; isLastStep = step >= maxSteps
     msgs = SessionReminders.apply(...)             // injects <system-reminder> blocks
     create assistant message; processor.create(...)
     resolve tools (SessionTools.resolve filters by Permission.Ruleset)
     if lastUser.format is json_schema → inject StructuredOutput tool + system prompt
     if isLastStep → append synthetic assistant message with MAX_STEPS text (forces wrap-up)
     result = handle.process({system, messages, tools, model, toolChoice})
       - if structured output captured → break
       - if finished && format===json_schema && no structured → set StructuredOutputError, break
       - if result==="stop" → break
       - if result==="compact" → compaction.create({auto:true, overflow:!finish}); continue
10. on loop exit: fork compaction.prune(sessionID); return lastAssistant(sessionID)
```

The key design moves Verso should copy:

- **Tasks are LIFO parts on the user message, not loop arguments.** Sub-agent dispatch and compaction are modeled as `SubtaskPart`/`CompactionPart` attached to the user turn. The loop pops one per iteration and re-enters. This means compaction and sub-tasks compose with the normal turn flow instead of being special-cased control-flow. `tasks.pop()` is LIFO so the most recently enqueued task runs first. (prompt.ts:1278-1295)
- **Overflow is checked on the *previous* assistant's token usage, not estimated pre-call.** `lastFinished.tokens` is the real billed token count from the last completed assistant message; `isOverflow` compares it to `usable(model)`. So compaction fires *reactively* after the turn that pushed over the line, then re-loops. (prompt.ts:1297-1304)
- **`MAX_STEPS` is a *synthetic assistant message*, not a hard stop.** When `step >= agent.steps`, the loop appends `{role:"assistant", content:MAX_STEPS}` (text from `prompt/max-steps.txt`) to the message list before the final call — nudging the model to wrap up in-band rather than hard-killing it. (prompt.ts:1426)
- **Mid-loop user messages get re-wrapped.** If new user text arrives after `lastFinished` (step>1), each such text part is wrapped in `<system-reminder>The user sent the following message: … Please address this message and continue with your tasks.</system-reminder>` so steering messages are distinguishable from the original task. (prompt.ts:1390-1406)

### `isOverflow()` — the exact trigger math (KNOWN, `session/overflow.ts`)

```ts
const COMPACTION_BUFFER = 20_000

function usable({cfg, model, outputTokenMax}) {
  const context = model.limit.context
  if (context === 0) return 0
  const reserved = cfg.compaction?.reserved
      ?? Math.min(COMPACTION_BUFFER, maxOutputTokens(model, outputTokenMax))
  return model.limit.input
    ? Math.max(0, model.limit.input - reserved)             // if model declares separate input limit
    : Math.max(0, context - maxOutputTokens(model, outputTokenMax))  // else context − output reserve
}

function isOverflow({cfg, tokens, model, outputTokenMax}) {
  if (cfg.compaction?.auto === false) return false
  if (model.limit.context === 0) return false
  const count = tokens.total
    || tokens.input + tokens.output + tokens.cache.read + tokens.cache.write
  return count >= usable({cfg, model, outputTokenMax})
}
```

So: usable budget = `min(input_limit, context) − reserved`, where `reserved = min(20_000, model_max_output)`. Overflow trips when the **sum of input+output+cache_read+cache_write tokens of the last turn ≥ usable**. `OUTPUT_TOKEN_MAX = 32_000` is the global cap (`transform.ts:18`). This is materially different from Claude Code's "~95% of context" — opencode reserves a fixed token buffer for the next output rather than a percentage, and counts cache tokens in the overflow sum.

### Compaction algorithm — `SessionCompaction.process()` (KNOWN, `session/compaction.ts`)

Compaction produces an **anchored, structured Markdown summary** (not a freeform recap) using a dedicated `compaction` agent + a small model, and preserves a budget-bounded *tail* of recent turns verbatim. Constants and algorithm:

```
PRUNE_MINIMUM            = 20_000      // min tokens of prunable tool output to bother pruning
PRUNE_PROTECT            = 40_000      // keep newest 40k tokens of tool output untouched
TOOL_OUTPUT_MAX_CHARS    = 2_000       // tool outputs truncated to 2k chars when fed to summarizer
PRUNE_PROTECTED_TOOLS    = ["skill"]   // never prune skill tool output
DEFAULT_TAIL_TURNS       = 2           // keep last 2 user-turns verbatim
MIN_PRESERVE_RECENT_TOKENS = 2_000
MAX_PRESERVE_RECENT_TOKENS = 8_000
preserveRecentBudget = cfg.preserve_recent_tokens
   ?? clamp(floor(usable*0.25), 2_000, 8_000)   // 25% of usable budget, clamped to [2k,8k]
```

**Tail selection (`select()`):** walk the last `tail_turns` (default 2) user-turns from newest to oldest, summing each turn's estimated token size. Keep whole turns while they fit `preserveRecentBudget`. The first turn that *doesn't* fit gets `splitTurn()`: scan that turn's messages front-to-back, find the earliest message index whose suffix-slice fits the *remaining* budget, and start the tail there. Everything before the tail (`head`) gets summarized; the tail is replayed verbatim. (compaction.ts:248-297)

**Summary prompt** is a fixed Markdown template with 8 mandatory sections — `## Goal / Constraints & Preferences / Progress (Done/In Progress/Blocked) / Key Decisions / Next Steps / Critical Context / Relevant Files`. Rules baked into the prompt: keep every section even when empty, terse bullets not prose, preserve exact file paths/commands/error strings/identifiers, never mention that compaction happened. (compaction.ts:46-81) **If a previous summary exists**, the prompt switches to "Update the anchored summary below … Preserve still-true details, remove stale details, merge new facts" with the old summary in `<previous-summary>` tags — i.e. **rolling summary update, not re-summarize-from-scratch.** (compaction.ts:127-138)

**`completedCompactions()` + `hidden` set:** prior compaction summary messages and their parent user messages are tracked; on the next compaction, those indices are filtered out of the history fed to the summarizer (`history.filter((_,i) => !hidden.has(i))`), so you never re-summarize an already-summarized prefix. The newest prior summary is reused as `previousSummary`. (compaction.ts:392-399)

**Overflow-mode replay:** if compaction was triggered by overflow (not manual), the algorithm finds the last real (non-compaction) user message *before* the compaction marker, slices history up to it, summarizes, then **re-injects that user message verbatim after the summary** so the model resumes mid-task. If the last call had no `finish` (the request itself overflowed before any output), it injects a synthetic continue message; for media-overflow it injects a specific "attachments were too large, media removed, suggest smaller files" prompt. (compaction.ts:368-384, 480-561)

**Hard failure:** if even after stripping media + truncating tool output the summarizer call returns `"compact"` (still overflows), it sets `ContextOverflowError` and returns `"stop"` — the loop terminates. (compaction.ts:462-471)

**`prune()` (background, post-loop):** independent of summarization. Walks messages newest→oldest, skips the most recent 2 user-turns, and for completed tool parts beyond `PRUNE_PROTECT` (40k) tokens of cumulative tool output, marks `state.time.compacted = now()` (erases the output from future context) — but only if total prunable ≥ `PRUNE_MINIMUM` (20k). `skill` tool output is never pruned. This is opencode's cheap "drop old tool spew without an LLM call" pass. (compaction.ts:301-345)

### DOOM_LOOP guard (KNOWN, `session/processor.ts:36,526-549`)

```ts
const DOOM_LOOP_THRESHOLD = 3
// on each tool-call streamed:
const recentParts = parts.slice(-DOOM_LOOP_THRESHOLD)
if (recentParts.length === DOOM_LOOP_THRESHOLD &&
    recentParts.every(p =>
       p.type === "tool" && p.tool === value.name && p.state.status !== "pending" &&
       JSON.stringify(p.state.input) === JSON.stringify(input))) {
  await permission.ask({ permission: "doom_loop", patterns:[value.name],
                         always:[value.name], metadata:{tool, input}, ruleset: agent.permission })
}
```

When the **last 3 tool parts are the identical tool with byte-identical input** (`JSON.stringify` equality on the input), it raises a `doom_loop` permission request. The default ruling is `doom_loop: "ask"` (`agent/agent.ts:108`) — so the human is prompted to break the loop. This is a pure structural guard: no heuristic, no model call. Verso can lift this verbatim.

### Retry / backoff (KNOWN, `session/retry.ts`)

```
RETRY_INITIAL_DELAY        = 2000 ms
RETRY_BACKOFF_FACTOR       = 2
RETRY_MAX_DELAY_NO_HEADERS = 30_000 ms      // cap when server gives no retry hint
RETRY_MAX_DELAY            = 2_147_483_647   // 32-bit setTimeout cap

delay(attempt, error):
  if error.responseHeaders["retry-after-ms"]  → cap(parseFloat(ms))             // honor server, no cap-to-30s
  elif ["retry-after"] numeric               → cap(ceil(seconds*1000))
  elif ["retry-after"] is HTTP-date          → cap(Date.parse - now)
  elif headers present                       → cap(2000 * 2^(attempt-1))         // no 30s cap if headers exist
  else                                       → cap(min(2000*2^(attempt-1), 30_000))
```

`retryable(error)` classification: **never retry** `ContextOverflowError`; **always retry** 5xx even if SDK didn't mark retryable; surface free-tier/Go usage-limit errors with structured upsell actions; pattern-match plain-text rate-limit messages ("rate limit", "too many requests", "exhausted", "unavailable"). Implemented as an Effect `Schedule.fromStepWithMetadata`. The notable bit: **when the server provides `retry-after` headers, the 30s cap is *not* applied** — opencode honors arbitrarily long server-requested backoffs. (retry.ts:35-66, 68-152)

### ProviderTransform — one loop, ~20 providers (KNOWN, `provider/transform.ts`, 1356 lines)

The normalization layer that makes the uniform loop possible. Every message list passes through `normalizeMessages()` before going to the AI SDK. The per-provider quirks it patches:

- **Surrogate sanitization (all providers):** `sanitizeSurrogates()` replaces unpaired UTF-16 surrogate code units (`/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/g`) with `�` across system/user/assistant/tool content — prevents JSON encoding crashes from truncated emoji in tool output. (transform.ts:25-27, applied at 70-130)
- **Anthropic empty-content filtering:** Anthropic rejects messages with empty content. Strips empty-string messages and empty text/reasoning parts, but **keeps** reasoning parts that carry a `signature` or `redactedData` (needed to replay thinking). (transform.ts:132-159)
- **Claude tool-ID scrub:** `id.replace(/[^a-zA-Z0-9_-]/g, "_")` applied to every `toolCallId` on assistant tool-call and tool-result parts when `model.api.id.includes("claude")`. (transform.ts:189-216)
- **Mistral tool-ID scrub:** strip non-alphanumeric, take first 9 chars, pad to 9 with `0`. Plus: a tool message cannot be followed by a user message, so it inserts a synthetic `{role:"assistant", content:[{text:"Done."}]}` between them. (transform.ts:218-266)
- **DeepSeek:** every assistant message must carry a reasoning part — appends empty `{type:"reasoning", text:""}` if missing. (transform.ts:268-284)
- **Prompt caching (`applyCaching`):** marks the **first 2 system messages + last 2 non-system messages** with provider-specific cache_control. Anthropic/Bedrock get *message-level* `cacheControl:{type:"ephemeral"}` / `cachePoint:{type:"default"}`; everyone else gets *content-level* on the last content block. Provider key map covers anthropic/openrouter/bedrock/openaiCompatible/copilot/alibaba. (transform.ts:323-372)
- **`promptCacheKey` injection:** for providers that support it, `result["promptCacheKey"] = input.sessionID` — routes all of a session's requests to the same cache shard. (transform.ts:1035,1065,1131,1138)

For Verso (Python, likely 1-3 providers), the lesson is the *shape*: a single `normalize(messages, model)` pass keyed off a capability/`npm`-package descriptor, run immediately before the provider call, is how you keep one loop driving many backends.

---

## Aider

### What It Is

Aider is a CLI pair-programmer (Python) whose architectural signature is twofold: (1) the **edit-format taxonomy** — each `Coder` subclass in `aider/coders/` maps to one way of getting edits out of an LLM, trading token cost vs. compliance; and (2) the **RepoMap** — a tree-sitter + PageRank graph that selects a token-budgeted "map" of the most relevant symbols across the whole repo. The architect/editor split is a third pattern: one model plans in prose, a (cheaper) model converts prose to edits.

### The Edit-Format Taxonomy (KNOWN, `aider/coders/*.py`)

Every coder is a `Coder` subclass with a class-level `edit_format` string + a `gpt_prompts` object. The full set:

| `edit_format` | Coder | Output contract | When chosen |
|---|---|---|---|
| `whole` | `WholeFileCoder` | Return the *entire* file in a fenced block. Highest tokens, highest compliance. | Default for weak/small models (`ModelSettings.edit_format="whole"`, models.py:131). |
| `diff` | `EditBlockCoder` | `<<<<<<< SEARCH` / `=======` / `>>>>>>> REPLACE` blocks; filename on the line above the fence. | Default for most strong models (GPT-4 class, Claude — models.py:439-588 set `"diff"`). |
| `diff-fenced` | `EditBlockFencedCoder` | Same SEARCH/REPLACE but filename goes *inside* the fence. | Gemini models (which prefer the filename inside the code fence). |
| `udiff` | `UnifiedDiffCoder` | Unified-diff `@@ … @@` hunks with `-`/`+` lines. | GPT-4-Turbo (`self.edit_format="udiff"`, models.py:516) — reduces "lazy" full-file rewrites. |
| `patch` | `PatchCoder` | OpenAI Apply-Patch envelope: `*** Begin Patch` / `*** Update File:` / `*** Add File:` / `*** Delete File:` / `@@` context / `*** End Patch`. | Models trained on the apply-patch format. |
| `editor-diff` / `editor-whole` / `editor-diff-fenced` | `Editor*Coder` | Same wire format as `diff`/`whole`/`diff-fenced` but with a stripped-down prompt focused *purely on editing* (no chat, no shell-command suggestion). | Used as the **editor** half of architect mode. |
| `architect` | `ArchitectCoder` | Prose. No edit format at all — describes changes, then delegates to an editor coder. | When `--architect` or a model defaults to it. |
| `ask`/`help`/`context` | `AskCoder` etc. | Read-only / Q&A / context-gathering; no edits applied. | Non-editing modes. |

**Default-format-per-model (KNOWN, `models.py:439-596`):** `ModelSettings.edit_format` defaults to `"whole"` (line 131). The constructor then runs a long `if model_name.startswith(...)` cascade that overrides it: most capable models → `"diff"`; GPT-4-Turbo → `"udiff"`; some get an explicit `editor_edit_format = "editor-diff"`. **`get_editor_model()` (line 625-643):** if no editor format is given, it inherits the editor model's own `edit_format`, and if that is one of `diff`/`whole`/`diff-fenced`, it prefixes `"editor-"` to get the editing-focused variant. So format selection is a static per-model table, not runtime negotiation.

### Search/Replace parsing — the fuzzy-match cascade (KNOWN, `editblock_coder.py`)

The SEARCH/REPLACE markers are matched by **tolerant regexes**, not exact strings — so a model that writes `<<<<< SEARCH` or `>>>>>>>> REPLACE` still parses:
```python
HEAD    = r"^<{5,9} SEARCH>?\s*$"     # 5-9 angle brackets, optional trailing >
DIVIDER = r"^={5,9}\s*$"
UPDATED = r"^>{5,9} REPLACE\s*$"
```
`find_original_update_blocks()` (line 439) scans for `filename\n<fence>\nHEAD … DIVIDER … UPDATED\n<fence>`, with `strip_filename()` recovering the path from the line above the fence (tolerating fence chars, `#` comments, bold `**`).

Applying an edit goes through `replace_most_similar_chunk(whole, part, replace)` — a **5-stage match cascade** (line 157):
1. `perfect_or_whitespace()` — exact match, then whitespace-flexible match (`replace_part_with_missing_leading_whitespace` outdents both part and replace by the common minimum leading whitespace — handles models that drop indentation uniformly).
2. Drop a spurious leading blank line from `part` and retry (1) (GPT sometimes adds them — issue #25).
3. `try_dotdotdots()` — if the SEARCH block contains `...` elision lines, split both part and replace on `^\s*\.\.\.\n`, require the `...` separators to match pairwise, and apply each non-`...` chunk via `whole.replace(part, replace, 1)`, raising `ValueError` if a chunk matches 0 or >1 times.
4. (Disabled) `replace_closest_edit_distance` fuzzy match — there is a `return` before it (line 183), so Levenshtein fuzzy matching is currently dead code; an unmatched block hard-fails.
5. On failure, the coder emits a structured error back to the model: `SearchReplaceNoExactMatch: This SEARCH block failed to exactly match…` with the failed block reproduced, plus "The SEARCH section must exactly match an existing block of lines including all whitespace", and — if the REPLACE lines are already present — "Are you sure you need this SEARCH/REPLACE block? The REPLACE lines are already in {path}!" (editblock_coder.py:84-120). This error-as-feedback is how the loop self-corrects.

### RepoMap — `get_ranked_tags()` + token-budget binary search (KNOWN, `repomap.py`)

This is the best OSS implementation of budget-aware whole-repo context. Algorithm:

**Graph construction (`get_ranked_tags`, line 365-574):**
- For each file, tree-sitter extracts `def` and `ref` tags. `defines[name] → {files}`, `references[name] → [files]`, `definitions[(file,name)] → {tags}`.
- Build a `networkx.MultiDiGraph`. For each identifier defined in one file and referenced in another, add edge `referencer → definer` with weight `use_mul * sqrt(num_refs)`.
- **Edge-weight multipliers (the exact heuristics, line 487-514):**
  - `mul = 10` if the ident was *mentioned* in the chat (`mentioned_idents`).
  - `mul *= 10` if the ident is "long & multi-case" (snake/kebab/camel AND `len >= 8`) — long descriptive names are more meaningful than `i`/`x`.
  - `mul *= 0.1` if ident starts with `_` (private).
  - `mul *= 0.1` if the ident is defined in >5 files (probably common/uninteresting).
  - `use_mul *= 50` if the *referencer* is a file currently in the chat (`chat_rel_fnames`) — chat files' references dominate.
  - `num_refs = sqrt(num_refs)` — damp high-frequency references so they don't swamp.
- **Self-edge weight `0.1`** for any definition with no references (line 479) — keeps lone defs in the graph.

**Personalization vector (PageRank teleport bias, line 374-445):**
- Base `personalize = 100 / len(fnames)` (so it stays a probability-ish weight regardless of repo size).
- A file gets `+= personalize` if it's a chat file, OR `max(.., personalize)` if it's a mentioned file, OR `+= personalize` if any path component matches a mentioned ident. This biases PageRank's random-restart toward files the user is actively working on.

**Ranking (line 519-574):** `nx.pagerank(G, weight="weight", personalization=…, dangling=…)`. On `ZeroDivisionError` (issue #1536), retry without personalization, then return `[]`. Each node's rank is then *distributed across its out-edges* proportional to edge weight (`data["rank"] = src_rank * weight / total_weight`), accumulated into `ranked_definitions[(dst, ident)]`. Sorted descending; chat files excluded from the map (the model already has their full text).

**Token-budget fit (`get_ranked_tags_map_uncached`, line 666-704):** binary search over how many ranked tags to include:
```python
middle = min(int(max_map_tokens // 25), num_tags)   # seed guess: ~25 tokens/tag
while lower_bound <= upper_bound:
    tree = self.to_tree(ranked_tags[:middle], chat_rel_fnames)
    num_tokens = self.token_count(tree)
    pct_err = abs(num_tokens - max_map_tokens) / max_map_tokens
    if (num_tokens <= max_map_tokens and num_tokens > best_tree_tokens) or pct_err < 0.15:
        best_tree = tree; best_tree_tokens = num_tokens
        if pct_err < 0.15: break          # within 15% → good enough
    if num_tokens < max_map_tokens: lower_bound = middle + 1
    else: upper_bound = middle - 1
    middle = (lower_bound + upper_bound) // 2
```
So the map grows/shrinks to land within **15%** of `max_map_tokens` (default `map_tokens=1024`). `token_count()` itself samples (every-Nth-line) for texts >200 chars to estimate cheaply (line 89-101).

**`map_mul_no_files=8` (line 56, 124-132):** when the chat has *no* files added yet, the budget is multiplied by 8 (capped at `max_context_window`) — give a much bigger map when the user is still exploring.

**Cache schema (KNOWN, line 35-43, 585-624):**
- On-disk tags cache: SQLite `diskcache.Cache` at `.aider.tags.cache.v{CACHE_VERSION}` (`CACHE_VERSION=3`, or `4` for the tree-sitter-language-pack variant). Keyed by file path + mtime; value = the tree-sitter tag list. Survives across runs.
- In-memory `map_cache` keyed by `(sorted chat_fnames, sorted other_fnames, max_map_tokens [, mentioned_*])`.
- `refresh` policy: `"auto"` (default) only recomputes if last computation took >1.0s (`map_processing_time > 1.0`); `"files"` caches always; `"always"` never caches; `"manual"` returns `last_map`. `cache_threshold = 0.95`.

### Architect → Editor handoff (KNOWN, `architect_coder.py`)

The cleanest "plan in prose, execute deterministically" split in OSS:
1. `ArchitectCoder` runs with the architect system prompt: *"Act as an expert architect engineer and provide direction to your editor engineer… The editor engineer will rely solely on your instructions… Just show the changes needed. DO NOT show the entire updated function/file!"* (architect_prompts.py:7-15). Output is **prose only** — no edit format.
2. `reply_completed()` (architect_coder.py:11): confirm with user ("Edit the files?"), then spawn a **fresh editor coder** via `Coder.create()` with: `main_model = editor_model`, `edit_format = editor_edit_format`, `map_tokens=0` (editor needs no repo map — the architect already located everything), `cache_prompts=False`, `suggest_shell_commands=False`.
3. `editor_coder.cur_messages = []; editor_coder.done_messages = []` — **the editor starts with empty history**; the *only* thing it receives is the architect's prose via `editor_coder.run(with_message=content)`. This is exact context-isolation: the editor sees the plan, not the planning conversation.
4. After: `move_back_cur_messages("I made those changes to the files.")` collapses the editor's turn back into the architect's transcript as a single line, and `total_cost`/`aider_commit_hashes` propagate up.

**For Verso:** (1) Adopt the **edit-format-as-static-per-model-table** idea — Verso's file-edit tool should have a format knob (`whole`/`search-replace`/`udiff`) chosen per model from a registry, not one universal format; small models get `whole`, strong ones get `search-replace`. (2) Steal the **tolerant marker regexes** (`<{5,9} SEARCH`) + the **match cascade** (exact → whitespace-flex → dotdotdots) + the **structured "didn't match, here's why" error fed back to the model** — that error message *is* the self-correction loop. (3) RepoMap is the reference for budget-aware context: tree-sitter def/ref graph → PageRank with a **personalization vector biased toward chat/mentioned files** and **edge-weight heuristics** (chat-referencer ×50, mentioned ident ×10, long-name ×10, private ×0.1, common-symbol ×0.1, `sqrt(num_refs)` damping) → **binary-search the tag count to land within 15% of the token budget**, with an **mtime-keyed on-disk tag cache** and an `auto`-refresh that only recomputes when the last pass was slow. (4) Architect→editor is Verso's tactical-loop-as-two-passes made concrete: planner emits prose, executor is a *fresh-context* coder that receives only the prose and applies edits deterministically — copy the empty-history + `map_tokens=0` + collapse-back-to-one-line pattern.

---

## Cline

### What It Is

Cline is the most widely deployed OSS coding agent (VS Code extension, Apache 2.0). Now a Bun monorepo; the agent core lives in `apps/vscode/src/core/`. Its load-bearing patterns for Verso are: the **plan/act mode toggle** (read-and-reason vs. execute), the **granular auto-approve model** (`[local, external]` tuple per tool category), the **repeated-tool-call loop guard** (soft=3/hard=5), the **shadow-git checkpoint/restore** system, and a **deterministic-truncation** context manager (half/quarter sliding window). It is the common ancestor of Roo Code and Kilo Code.

### Plan / Act state machine (KNOWN, `controller/state/togglePlanActModeProto.ts`, `task/tools/autoApprove.ts`)

`Mode` is a two-value union `"plan" | "act"`. `togglePlanActMode(mode, chatContent)` flips it; the optional `chatContent` lets the user carry their drafted message across the toggle (so you can write a prompt in Plan, then submit it into Act). The mode is **persisted global state** (`stateManager`), not a per-turn flag — so it survives across requests until toggled. The two modes differ in:
- **System prompt**: Plan mode injects a "you are in PLAN MODE, do not make edits, use the `plan_mode_respond` tool to converse" prompt fragment; Act mode injects the normal acting prompt. (the prompt fragment lives in `core/prompts/`).
- **Tool surface**: Plan mode exposes the read/search tools + a dedicated `plan_mode_respond` tool and withholds the edit/exec tools; Act mode exposes the full registry.
- **Per-mode model**: Cline lets Plan and Act use *different* models (cheap/strong planner, fast actor) — the model is selected by current mode.

This is precisely Verso's HITL seam: Plan = the durable/checkpoint side (reason, propose, no side effects), Act = the tactical side (execute with approval). The toggle carrying `chatContent` is a UX detail worth copying.

### Auto-approve — the granular permission model (KNOWN, `task/tools/autoApprove.ts:42-117`)

`shouldAutoApproveTool(toolName)` returns either a plain `boolean` or a **`[localApproved, externalApproved]` tuple** — the second element governs actions on files *outside* the workspace root. The decision cascade:
1. **`yoloModeToggled`** → auto-approve everything (`[true,true]` for file/exec tools, `true` for browser/web/MCP).
2. **`autoApproveAllToggled`** → same as yolo for the standard tool set.
3. Otherwise, per-category from `autoApprovalSettings.actions`:
   - read tools (`FILE_READ`, `LIST_FILES`, `LIST_CODE_DEF`, `SEARCH`, `USE_SUBAGENTS`) → `[readFiles, readFilesExternally]`
   - write tools (`NEW_RULE`, `FILE_NEW`, `FILE_EDIT`, `APPLY_PATCH`) → `[editFiles, editFilesExternally]`
   - `BASH` → `[executeSafeCommands, executeAllCommands]`  ← note: safe vs. all is a separate axis
   - `BROWSER`/`WEB_FETCH`/`WEB_SEARCH` → `useBrowser`
   - `MCP_ACCESS`/`MCP_USE` → `useMcp`
4. `shouldAutoApproveToolWithPath()` adds a path check: even if a category is auto-approved, an edit *outside* the workspace requires `editFilesExternally` (resolved against multi-root workspace membership). (autoApprove.ts:122-141)

So the permission model has **three independent axes** — tool category, local-vs-external path, and (for bash) safe-vs-all — each a separate boolean. Verso should adopt the `[local, external]` tuple + the safe/all-commands split rather than a flat allow/deny.

### Repeated-tool-call loop guard (KNOWN, `task/loop-detection.ts`, consumed in `task/ToolExecutor.ts:579-598`)

```ts
LOOP_DETECTION_SOFT_THRESHOLD = 3   // inject a warning, let the LLM self-correct
LOOP_DETECTION_HARD_THRESHOLD = 5   // escalate
IGNORED_PARAMS = {"task_progress"}  // metadata that legitimately changes each turn

toolCallSignature(params) = JSON.stringify(params, sorted_keys_minus_ignored)  // canonical, key-order-independent
checkRepeatedToolCall(state, toolName, sig):
  if toolName===lastToolName && sig===lastToolParams: consecutiveIdenticalToolCount++
  else: consecutiveIdenticalToolCount = 1
  return { softWarning: count===3, hardEscalation: count===5 }
```
Consumption order matters: the check runs **before** `lastToolName/lastToolParams` are updated (compares against the *previous* call). On `softWarning` (3rd identical call) it pushes `formatResponse.repeatedToolCall(...)` text into the next user message — a self-correction nudge. On `hardEscalation` (5th) it sets `consecutiveMistakeCount = maxConsecutiveMistakes`, which trips the separate mistake-limit escalation (asks the user / fails the task). The `task_progress` param is stripped from the signature so a checklist update each turn doesn't reset the counter. This is a richer version of opencode's flat-3 doom guard: **two thresholds (warn, then escalate), with metadata-stripping in the signature.**

### Checkpoint / restore — shadow git (KNOWN, `integrations/checkpoints/CheckpointTracker.ts`, `CheckpointGitOperations.ts`)

Cline snapshots the workspace into a **separate "shadow" git repo** so checkpoints never touch the user's real `.git`:
- **Init (`CheckpointGitOperations.ts:67-107`):** a dedicated git dir keyed by `cwdHash`; `git config core.worktree = <workspace cwd>` (so the shadow repo's working tree *is* the live workspace), `commit.gpgSign = false`, and an initial `git commit --allow-empty --no-verify "initial commit"`. The worktree config is verified on reopen — checkpoints only work in the original workspace (`throw "Checkpoints can only be used in the original workspace"`). Excludes are refreshed before each commit (so build artifacts/node_modules aren't snapshotted).
- **Commit (`CheckpointTracker.ts:212-262`):** acquire a folder lock (`tryAcquireCheckpointLockWithRetry(cwdHash, taskId)` — skipped in single-VS-Code-instance case), `addCheckpointFiles`, then `git commit --allow-empty --no-verify` with message `checkpoint-<cwdHash>-<taskId>`. Returns the commit hash; cached. A checkpoint is committed after each tool execution that changes files (`saveCheckpoint` callback wired into `ToolExecutor`).
- **Restore (`CheckpointTracker.ts:314+`):** `reset --hard <commitHash>` against the shadow repo — because `core.worktree` points at the live workspace, the hard reset **rewrites the actual workspace files** to the checkpoint state. Folder-locked. This is the undo primitive: every user-message turn is restorable.

The genius is `core.worktree` pointing at the live tree: one shadow repo gives you whole-workspace snapshot + restore with plain `git commit`/`git reset --hard`, no file copying, and the user's own git history is untouched.

### Context truncation — deterministic sliding window (KNOWN, `context/context-management/ContextManager.ts:150-339`)

Cline has two paths: the new `useAutoCondense` (LLM summarization) and the legacy **programmatic truncation** (the interesting one for Verso's no-LLM-needed fallback):
- **Trigger (`shouldCompactContextWindow`):** parse the *previous* API request's recorded usage `totalTokens = tokensIn + tokensOut + cacheWrites + cacheReads`; compare to `min(contextWindow * thresholdPercentage, maxAllowedSize)`. `getContextWindowInfo` derives `maxAllowedSize` from the model's context window (with a reserve for output).
- **Half vs. quarter decision (line 249-252):** when `totalTokens >= maxAllowedSize`, `keep = (totalTokens/2 > maxAllowedSize) ? "quarter" : "half"`. The comment explains: if the user switched from a 200k model to a 64k model, removing half isn't enough, so remove 3/4. **Adaptive truncation depth based on how far over the limit you are.**
- **`getNextTruncationRange(messages, currentDeletedRange, keep)` (line 299-339):** *always keep the first user-assistant pair* (`rangeStartIndex = 2`). Truncate from `startOfRest = currentDeletedRange[1]+1` (truncation is cumulative across turns — the deleted range only grows). Messages removed: `half` = `floor((n - startOfRest)/4)*2`, `quarter` = `floor((n - startOfRest)*3/4/2)*2` — both forced **even** so the kept tail stays user-assistant-aligned. Then if the last removed message isn't an assistant message, decrement the end by 1 to **preserve the user→assistant→user→assistant alternation** Anthropic requires.
- **File-read optimization first (line 254-259):** before truncating, `attemptFileReadOptimizationCore` replaces duplicate file-read tool outputs in history with a "[content elided, see latest read]" notice (`contextHistoryUpdates`) — frees space without dropping turns. Only if that's insufficient (`needToTruncate`) does it slide the window.

So the order is: **dedupe file reads → if still over, slide the window by half (or quarter if way over), always keeping the first pair + alternation invariant**, persisting the deleted range to disk so it's stable across resume. This is a fully deterministic, no-extra-LLM-call truncation Verso can use as the cheap default before reaching for summarization.

**For Verso:** (1) **Plan/Act as persisted mode** (not per-turn flag) with per-mode {system prompt fragment, tool subset, model} is the cleanest HITL-seam implementation — and carrying draft `chatContent` across the toggle is a free UX win. (2) The **`[local, external]` permission tuple + safe/all-commands axis** is more expressive than flat allow/deny; copy it. (3) **Two-threshold loop guard** (warn at 3 via injected message, escalate at 5 via mistake-limit) with **metadata params stripped from the signature** beats a single threshold. (4) **Shadow-git checkpointing** (`core.worktree`→live tree, `commit --allow-empty --no-verify`, `reset --hard` to restore, folder-locked) is the best OSS undo primitive and trivially portable to Python via subprocess git. (5) The **deterministic sliding-window truncation** — dedupe file reads, then half/quarter based on overage, keep first pair + alternation, cumulative deleted-range persisted — is the right *cheap fallback* before LLM summarization.

---

## Roo Code

### What It Is

Roo Code is the most-evolved Cline fork (Apache 2.0, VS Code). It invented **Boomerang Tasks** — structured multi-agent orchestration where a parent delegates a subtask that runs in a *fresh context with a different mode* and returns *only a summary*. Its **mode system** (Architect/Code/Ask/Debug/Orchestrator + custom) maps each mode to a system prompt + tool subset + per-mode file-edit restrictions. Both are directly load-bearing for Verso's multi-agent + typed-agent-variant story. (Note: current Roo uses **metadata-driven delegation** — a refactor of the original pause/resume Boomerang; both are documented below since the *isolation semantics* are what matter.)

### Boomerang / delegation — `new_task` → child → `attempt_completion` → parent (KNOWN, `tools/NewTaskTool.ts`, `webview/ClineProvider.ts:2783-3025`)

The orchestrator (or any mode) calls the `new_task` tool with `{ mode, message, todos? }`. Flow:

**1. Launch (`delegateParentAndOpenChild`, ClineProvider.ts:2783):**
- Validate the target `mode` exists (`getModeBySlug`), parse `todos` from a markdown checklist, ask user approval.
- **Flush parent state to disk first (critical, line 2803-2835):** `parent.flushPendingToolResultsToHistory()` — any tool_result blocks that were in `userMessageContent` but not yet persisted to the API conversation must be saved, or the parent's history will be missing tool_results for its tool_use blocks and 400 on resume. Retries with `retrySaveApiConversationHistory()` on failure.
- **Single-open invariant (line 2837):** `removeClineFromStack()` disposes the parent — at no point are two tasks "running"; the parent is frozen *to disk*, not held in memory. This is the key context-isolation decision: the child cannot see the parent's in-memory context because the parent isn't in memory.
- **Mode switch BEFORE child creation (line 2851):** `handleModeSwitch(mode)` so the child's system prompt + tool set + model are built from the *child's* mode, not the parent's.
- **Create child with `startTask:false` (line 2876):** child gets the parent reference (for lineage) + `initialTodos` + `initialStatus:"active"`, but does NOT start its loop yet — to avoid a race where the child writes to globalState before the parent's delegation metadata is persisted.
- **Persist parent metadata (line 2882):** parent `historyItem` is updated to `{ status:"delegated", delegatedToId:child.taskId, awaitingChildId:child.taskId, childIds:[...] }`. Only *then* `child.start()`.

**2. Subtask runs in full isolation:** the child is a complete Task with its own conversation history, its own mode's tools, its own model. It sees **only** the `message` the parent passed (which the Orchestrator prompt mandates must contain "all necessary context from the parent task… a clearly defined scope… an explicit statement that the subtask should only perform the work outlined"). The parent's conversation is invisible.

**3. Return (`attempt_completion` → `reopenParentFromDelegation`, ClineProvider.ts:2918):** the child finishes by calling `attempt_completion` with a `result` string. That `result` is the **only** thing that crosses back. `reopenParentFromDelegation({parentTaskId, childTaskId, completionResultSummary})`:
- Loads the parent's persisted `clineMessages` + `apiMessages` from disk.
- Pushes a UI `say:"subtask_result"` message with the summary.
- **Reconstructs the Anthropic tool-call contract:** scans backward through the parent's API history for the `tool_use` block where `name === "new_task"`, grabs its `id`, and injects a matching `user` message with `{ type:"tool_result", tool_use_id, content: "Subtask <id> completed.\n\nResult:\n<summary>" }`. If a tool_result already exists (retry), it updates it in place. `validateAndFixToolResultIds` ensures the injected tool_result's id matches a tool_use in the immediately-preceding assistant message (Anthropic requires user→assistant(tool_use)→user(tool_result)). If there's no matching tool_use, it falls back to a plain user text note.
- Parent is reopened and resumes with the summary as the `new_task` tool's result — exactly as if `new_task` were a normal tool returning a string.

So the **entire parent↔child channel is two strings**: the `message` going down and the `attempt_completion result` coming back. The subtask's full transcript (all its tool calls, all its intermediate reasoning) is persisted under the child task id but **never enters the parent's context**. This is Verso's "sub-agent returns summary to parent" pattern with the exact disk-freeze + tool_result-reconstruction mechanics.

### Mode definition schema (KNOWN, `packages/types/src/mode.ts`)

A mode is a Zod-validated config — this is the "typed agent variant" schema Verso needs:
```ts
modeConfigSchema = {
  slug:            string /^[a-zA-Z0-9-]+$/,
  name:            string (min 1),
  roleDefinition:  string (min 1),     // becomes the head of the system prompt
  whenToUse?:      string,             // routing hint — how the orchestrator picks this mode
  description?:    string,
  customInstructions?: string,         // appended to system prompt
  groups:          GroupEntry[],       // the TOOL SUBSET
  source?:         "global" | "project"
}
GroupEntry = ToolGroup | [ToolGroup, { fileRegex?: string, description?: string }]
```
`groups` is the tool-subset mechanism: each entry is a tool group (`read`, `edit`, `command`, `mcp`, `browser`) *or* a tuple pairing a group with options. The killer feature: **`["edit", { fileRegex: "\\.md$", description: "Markdown files only" }]`** — the Architect mode can edit *only markdown files*. `getToolsForMode(groups)` expands groups → concrete tool names. Duplicate groups are rejected; deprecated groups (`browser`) are stripped via a `z.preprocess`.

The five built-in `DEFAULT_MODES` (mode.ts:168) instantiate the schema:
| slug | groups (tool subset) | role |
|---|---|---|
| `architect` | `read`, `["edit",{fileRegex:"\\.md$"}]`, `mcp` | plan/design; can only write markdown |
| `code` | `read`, `edit`, `command`, `mcp` | full implementation |
| `ask` | `read`, `mcp` | Q&A, no edits, no commands |
| `debug` | `read`, `edit`, `command`, `mcp` | systematic diagnosis ("reflect on 5-7 sources, distill to 1-2, add logs, confirm before fixing") |
| `orchestrator` | `[]` (no direct tools!) | only delegates via `new_task` |

The Orchestrator having **zero tool groups** is deliberate — it cannot edit/read/run anything itself; its only power is `new_task` delegation (always available). Its `customInstructions` *is* the Boomerang protocol spec verbatim: break into subtasks, delegate each with full context + scope + "only do this" + "signal completion via attempt_completion with a concise thorough summary — this summary is the source of truth", track progress, synthesize at the end.

### Fork lineage (INFERRED, from shared file structure)

Roo's `src/core/` mirrors Cline's pre-monorepo layout (`task/Task.ts`, `tools/`, `context-management/ContextManager.ts`, `checkpoints/`) — the loop, the shadow-git checkpoints, and the deterministic truncation are inherited from Cline largely intact. Roo's *additions* are the mode system (`shared/modes.ts` + `packages/types/src/mode.ts`), the Boomerang delegation (`NewTaskTool` + `delegateParentAndOpenChild`/`reopenParentFromDelegation`), and the `condense/` LLM-summarization path. So reading Cline + Roo's mode/delegation files covers Kilo Code's superset too (per the target notes).

**For Verso:** (1) Boomerang is the reference for **sub-agent context isolation**: freeze the parent *to disk* (not memory) before launching, run the child as a full independent task with a *different mode* (own prompt/tools/model), and let **only two strings** cross the boundary — the launch `message` and the `attempt_completion result`. Verso should adopt the disk-freeze (guarantees isolation) + the tool_result reconstruction (the child's summary returns *as if `dispatch_subtask` were a normal tool call returning a string* — clean, no special parent-side handling). (2) The **mode schema** is exactly Verso's typed-agent-variant: `{slug, roleDefinition→prompt, whenToUse→routing hint, customInstructions, groups→tool subset}` — and the **`[group, {fileRegex}]` tuple** for path-scoped edit permission (Architect edits only `*.md`) is a pattern Verso should steal for capability-scoping agents. (3) The **Orchestrator with zero tools but `new_task`** is the cleanest "pure coordinator" agent — its system prompt carries the full delegation contract; copy that prompt structure for Verso's orchestrator variant.

---

## Goose (Block / AAIF)

### What It Is

Goose is a Rust-core agent (Apache 2.0, now at the Agentic AI Foundation). Not portable to Python, but it is the primary reference for three things Verso cares about: **MCP-as-extension-system** (what Verso explicitly demotes), the **Recipe** declarative-workflow system (minijinja-templated task definitions — Verso's "durable workflow without a graph DSL"), and the **provider tool-shim** (running tool-calling agents on models with no native function-calling). It also has a clean Rust async ReAct loop and a sqlx session store.

### Core loop — `Agent::reply_internal()` (KNOWN, `agents/agent.rs:1616-1900+`)

```
DEFAULT_MAX_TURNS = 1000   (env GOOSE_MAX_TURNS or SessionConfig.max_turns override)
```
The loop is an `async_stream::try_stream!` yielding `AgentEvent`s. Per iteration:
1. **Cancellation check** (`cancel_token`).
2. **Final-output check:** if the `final_output_tool` captured structured output, emit it, fire the `Stop` hook (blocking) — `Allow` → break; `Deny{reason}` → push a denial-context message and `continue` (loop keeps going). A `stop_hook_block_cap` (`GOOSE_STOP_HOOK_BLOCK_CAP`) prevents a misbehaving Stop hook from looping forever — after N consecutive blocks it overrides and ends the turn. (agent.rs:1711-1751)
3. `turns_taken += 1`; if `> max_turns` → emit "I've reached the maximum number of actions… Would you like me to continue?" and break (soft stop, asks user).
4. **MOIM injection** (`inject_moim`) — model-on-its-mind context.
5. **Stream the provider response** (`stream_response_from_provider` with `system_prompt, messages, tools, toolshim_tools`).
6. **Tool-pair summarization** (`maybe_summarize_tool_pairs`) — opportunistic compaction of old tool req/resp pairs once a `tool_call_cut_off` is crossed, but only for tool calls *before this turn* (`pre_turn_tool_count`) so the current turn isn't summarized away.
7. Categorize tool requests into `frontend_requests` (UI-side) vs `remaining_requests` (executed by agent); execute, feed results back; if no tools called and there's assistant text, that's the turn's answer.
8. On context-overflow errors mid-stream, `compaction_attempts++` and a recovery compaction is attempted before retrying.

Termination is thus: final_output captured + Stop-hook allows, OR max_turns exceeded (soft, asks user), OR no tool calls + text produced, OR cancellation. Note `DEFAULT_MAX_TURNS = 1000` is *much* higher than other agents — Goose biases toward autonomy.

### Repetition guard — `RepetitionInspector` (KNOWN, `tool_monitor.rs`)

Implemented as a `ToolInspector` trait object (the same trait security/permission inspectors use). Tracks `last_call: Option<{name, parameters}>` + `repeat_count` + per-tool `call_counts`. On each tool call: if it `matches` (name + exact `serde_json::Value` parameter equality) the last call, `repeat_count++`; if `repeat_count > max_repetitions` → `inspect()` returns `InspectionResult{ action: Deny, reason: "Tool '<x>' has exceeded maximum repetitions", confidence: 1.0, finding_id: "REP-001" }`. `max_repetitions = None` disables the guard. Non-matching call resets `repeat_count = 1`. The architectural point vs. opencode/Cline: Goose makes the doom-guard **one inspector in a pluggable `ToolInspector` pipeline** alongside security/permission inspectors — each returns `Allow/Deny/Ask` with a confidence, and results merge. Verso should adopt the *inspector-pipeline* shape (loop-guard, security, permission as composable inspectors) rather than hardcoding each guard in the loop.

### Provider tool-shim — tool calls on non-native models (KNOWN, `providers/toolshim.rs`)

For models with no native function-calling, Goose runs a **second "interpreter" model** that extracts tool-call intentions from the first model's text output:
- `ToolInterpreter` trait; `OllamaInterpreter` impl uses Ollama's structured-output API. Default interpreter model: `mistral-nemo` (`DEFAULT_INTERPRETER_MODEL_OLLAMA`). Backend selected by `GOOSE_TOOLSHIM_BACKEND` (`ollama` | `local`/`llama.cpp`), model by `GOOSE_TOOLSHIM_MODEL`.
- `augment_message_with_tool_calls(message, interpreter)`: takes the primary model's text, sends to the interpreter, parses the result into `CallToolRequestParams`, and attaches them to the original message — so downstream code sees tool calls regardless of native support.
- Wire sentinels for the shimmed format: `<|tool_calls_section_begin|>` / `<|tool_call_begin|>` / `<|tool_call_argument_begin|>` / `…_end|>` / `<|tool_calls_section_end|>` — a delimited mini-protocol the interpreter emits and the parser splits on.

This is a concrete "two-model" pattern: a capable-but-no-tools model does the reasoning, a small structured-output model converts its prose into tool calls. Verso could offer this as a fallback adapter for local/open models.

### Recipe system — declarative workflows via minijinja (KNOWN, `recipe/mod.rs`, `recipe/template_recipe.rs`)

A `Recipe` is the durable-workflow primitive (no graph DSL — it's a templated YAML/JSON doc):
```rust
struct Recipe {
  version: String,                         // semver of file format
  title: String, description, ...
  instructions: Option<String>,            // system instructions for the model
  prompt: Option<String>,                  // initial user prompt
  extensions: Option<Vec<ExtensionConfig>>,// MCP extensions to enable for this recipe
  settings: Option<Settings>,
  activities: Option<Vec<String>>,         // suggested activity pills
  parameters: Option<Vec<RecipeParameter>>,// typed params injected into the template
  response: Option<Response>,              // optional JSON-schema for structured output
  sub_recipes: Option<Vec<SubRecipe>>,     // composition — recipes calling recipes
  retry: Option<RetryConfig>,
}
```
Templating (`render_recipe_content_with_params`): minijinja `Environment` with `UndefinedBehavior::Strict`, params from a `HashMap<String,String>`. Two notable preprocessing steps that show how to make a templating engine survive being fed arbitrary config: (1) `: ""` (empty quoted YAML value) → `: ''` via regex, so minijinja doesn't escape `""` into `\"\"` and break the YAML; (2) **unparseable variable names get wrapped in `{% raw %}…{% endraw %}`** (`filter_unparseable_variables` test-compiles each `{{var}}` and, if it fails, leaves it literal) — so a `{{not_a_var}}` in user content doesn't crash the render. A recipe-dir loader lets templates `{% include %}` sibling files. `sub_recipes` is the composition primitive — a recipe can declare other recipes as steps, giving you task graphs without a graph engine.

For Verso's "durable workflow" pillar, the Recipe is the reference: a **typed, parameterized, templated, composable** declarative doc (params → schema → prompt + tool/extension set + optional structured-output schema + sub-workflows), rendered by a standard templating engine with `Strict` undefined-handling + the raw-wrapping escape hatch.

### Session persistence — sqlx/SQLite (KNOWN, `session/session_manager.rs:731-780`)

`SessionStorage` over a `sqlx::Pool<Sqlite>`:
```sql
sessions(id TEXT PK, name, description, user_set_name BOOL, session_type TEXT DEFAULT 'user',
         working_dir TEXT NOT NULL, created_at/updated_at TIMESTAMP,
         extension_data TEXT DEFAULT '{}',
         total_tokens/input_tokens/output_tokens/accumulated_* INTEGER, accumulated_cost REAL,
         schedule_id TEXT,                       -- links to scheduler
         recipe_json TEXT, user_recipe_values_json TEXT,   -- the recipe + its param values
         provider_name TEXT, model_config_json TEXT, goose_mode TEXT DEFAULT 'auto',
         archived_at TIMESTAMP, project_id TEXT)
messages(id INTEGER PK AUTOINCREMENT, message_id TEXT, session_id TEXT REFERENCES sessions(id),
         role TEXT, content_json TEXT NOT NULL, created_timestamp INTEGER NOT NULL,
         timestamp TIMESTAMP, tokens INTEGER, metadata_json TEXT)
  INDEX idx_messages_session ON messages(session_id)
+ schema_version(version INTEGER PK)            -- migration tracking, with ALTER TABLE migrations
```
Same schema-on-read pattern as opencode: message content is a JSON blob (`content_json`), session caches rolling + accumulated token/cost totals, and the recipe + its resolved param values are stored on the session so a recipe run is fully reproducible. `schema_version` + idempotent `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE … ADD COLUMN` is their migration strategy.

### Builtin MCP extensions (KNOWN, `crates/goose-mcp/`, `builtin_extension.rs`)

Builtin extensions (`developer`, `computercontroller`, `memory`, `tutorial`, `autovisualiser`, `peekaboo`) are registered via `register_builtin_extension(name, spawn_fn)` into a global registry; each `spawn_fn` returns an `rmcp::ServerHandler`. The MCP server runner (`mcp_server_runner.rs`) wires them over `rmcp::transport::stdio` even for builtins — so a builtin extension is *the same MCP server interface* as an external one, just spawned in-process instead of as a subprocess. This is the cost Verso is choosing to avoid: even first-party tools pay the MCP `ServerHandler` + transport tax (schema serialization, stdio framing) rather than being plain in-process function calls. The *benefit* is uniformity (one extension model, builtin or external) — the *cost* is lifecycle/transport complexity and schema repetition. Reading this confirms Verso's decision to demote MCP to an adapter and keep first-party tools as direct function calls.

**For Verso:** (1) The **`ToolInspector` pipeline** (loop-guard + security + permission as composable inspectors each returning `Allow/Deny/Ask` + confidence) is a cleaner architecture than hardcoding each guard in the loop — adopt it. (2) The **tool-shim** (a small structured-output interpreter model extracts tool calls from a no-native-tools model's prose, via delimited sentinels) is the right fallback adapter for local/open models. (3) The **Recipe** is Verso's durable-workflow reference: a typed/parameterized/templated/composable declarative doc with optional structured-output schema + `sub_recipes` composition — and the minijinja hardening tricks (`Strict` + `{% raw %}`-wrap unparseable vars + the `""`→`''` YAML fix) are worth copying. (4) Confirm the **MCP-demotion thesis**: Goose proves MCP-as-everything works but taxes even builtin tools with `ServerHandler`+transport overhead; Verso keeping first-party tools as direct calls and MCP as an adapter is validated.

---

## Continue.dev (post-pivot)

### What It Is

Post-pivot Continue is an open-source CLI (`@continuedev/cli`, binary `cn`) for **headless agents triggered by CI events** — the async/event-sourced side of Verso's tactical↔durable seam. The reference use case is PR review: a GitHub Action assembles a prompt from the PR diff, invokes `cn` headlessly, and posts the result as a sticky PR comment. No hosted service reads your code; the agent runs in your own Action runner.

### Headless PR-review loop (KNOWN, `actions/general-review/action.yml` + `scripts/buildPrompt.js`)

The entire loop is a composite GitHub Action with a clean shape Verso can copy for its durable seam:

1. **Authorization gate (no-LLM):** the agent only runs if the PR is non-draft AND the author/commenter has `admin|maintain|write` permission (`getCollaboratorPermissionLevel`), with a fallback to `author_association ∈ {OWNER,MEMBER,COLLABORATOR}`. For `issue_comment` events it additionally requires the `@continue-review` trigger phrase. Exports `SHOULD_RUN`. This is the "who can invoke an async agent" trust model.
2. **Sticky-comment lifecycle:** posts a `<!-- continue-agent-review -->`-marked "🔄 Review In Progress" comment; finds the existing marked comment and **updates it in place** if <1h old, else creates a new one (preserves history). The marker is how the async agent maintains a single stable artifact across re-runs.
3. **Context assembly (`buildPrompt.js`):** `gh pr diff <N> > pr_diff.txt` + `gh pr view <N> --json title,author,body,files > pr_data.json`, then build a single `review_prompt.txt` containing: a fixed review rubric (`FOCUS ON: bugs/security/breaking-changes/perf-with-real-impact/missing-tests/missing-docs`; `SKIP: style/formatting/alternative-approaches/minor-naming/trivial-docs`), the PR metadata, the PR description, and the **raw diff inline**. So the agent sees *the diff plus the rubric*, not the full repo — context is the diff, bounded.
4. **Headless invocation:** `timeout 360 cn --agent "$ORG/$AGENT" -p "@$PROMPT_FILE" --allow Bash > code_review_raw.md`. Key flags: `-p @file` = read the prompt from a file and run **print mode** (one-shot, exit on completion — no interactive loop); `--allow Bash` = the only auto-approved tool (so the headless agent can run `gh`/grep but nothing destructive is silently approved); a hard **360s timeout**. Output is captured to stdout → markdown.
5. **Output serialization:** strip ANSI codes (`sed 's/\x1b\[[0-9;]*m//g'`), and on any failure path (`empty_output`/`cli_not_found`/`config_error`/`auth_error`/`generic_failure`) substitute a templated fallback message via `writeMarkdown.js`. Then update the sticky comment to "✅ Review Complete" with the markdown body, and upload `code_review.md`/`review_prompt.txt`/`pr_diff.txt` as a 30-day artifact.

The agent itself (`$ORG/$AGENT`) is a hosted/config-defined agent (an "assistant" with its own system prompt + model + rules) — Continue's config layer. The architecturally interesting part for Verso is the **headless contract**: prompt-from-file + print-mode-one-shot + a single auto-allowed tool + hard timeout + structured fallback-on-failure + idempotent sticky artifact. That's the right skeleton for "agent triggered by a CI event with no interactive user."

**For Verso:** copy the **headless run contract** — `run(prompt, allow=[…], timeout=…) → captured output`, print-mode (no interactive approval loop, since there's no human; instead a fixed allow-list), hard timeout, and **typed failure fallbacks** (each failure mode maps to a templated artifact, never a silent empty result). And the **diff-as-context** assembly (rubric + metadata + raw diff inline, no repo) is the minimal context for a review agent. The authorization gate (write-permission check before the agent runs) is the trust model for any event-triggered Verso agent.

---

## Qodo (Qodo Gen CLI)

### What It Is

Qodo (formerly CodiumAI) is a multi-agent test-generation + review platform. The OSS-inspectable part is the `@qodo/gen` CLI (`qodo` binary), whose agent loop runs server-side (bundled in `dist/cli.js`) but whose **agent-definition schema** ships as plain TOML files. The two patterns relevant to Verso: the **eval-driven (coverage-metric-terminated) agent loop** and the **agent-definition-as-TOML** schema.

### Agent definition schema — TOML commands (KNOWN, `onboarding/agents/*.toml`)

An agent is a `[commands.<name>]` block — this is Qodo's custom-agent framework, parameterizing behavior via config (directly relevant to Verso's typed-agent design):
```toml
[commands.cover]
description  = "Review codebase, plan and implement tests"
instructions = """ ... multi-phase prompt ... """        # the system/task prompt
tools        = ["filesystem", "shell"]                    # tool subset (named tool groups)
arguments    = []                                          # typed params
# richer variants also support:
mcpServers   = """{ "mcpServers": { "shell": {...} } }"""  # inline MCP server config (e.g. uvx mcp-shell-server)
```
The schema fields (confirmed in `dist/cli.js`: `instructions`, `tools`, `arguments`, `mcpServers`, `model`) define a custom agent declaratively. Notably the `diff_test_suite` agent embeds a full `mcpServers` JSON that wires `mcp-shell-server` via `uvx` with an `ALLOW_COMMANDS` allow-list of hundreds of binaries — the tool sandbox is an allow-list passed to an MCP shell server, not a custom permission engine.

### Eval-driven loop — coverage as termination condition (KNOWN, `cover.toml` instructions)

The `cover` agent is the cleanest example of a **metric-terminated** (not human-terminated) agent loop. Its instructions encode a 5-phase loop: ANALYSIS (scan codebase → prioritized component list) → PLANNING (per-component test cases: normal/edge/error/integration) → IMPLEMENTATION (one component at a time, with mocks/fixtures) → EXECUTION (**run tests → document failures → fix → re-run until all pass → document coverage**) → REPORT. The termination condition is in the prompt verbatim: *"Finish once all tests of all the key components are passing and the code is stable."* So the loop's exit is a **measured metric** (tests pass + coverage), reached through a run→fail→fix→re-run sub-loop — there is no "ask the user if done." The `diff_test_suite` variant scopes the same loop to a git diff (PREPARATION uses `git` to find changed files, then tests only changed behaviors, VALIDATION runs each test file individually then the whole suite for regressions).

The "4 parallel specialist agents" of Qodo 2.0 (bug/quality/security/test-coverage on the same diff, results merged) is a product-tier orchestration that isn't in the OSS CLI source; the inspectable primitive is the single eval-driven agent above. The merge strategy is server-side (black box).

**For Verso:** (1) **Agent-definition-as-TOML** (`{description, instructions→prompt, tools→subset, arguments→typed params, mcpServers→inline server config, model}`) is a clean declarative agent schema — similar to Roo's mode schema but with inline MCP-server wiring. (2) The **eval-driven termination** is the key idea for Verso's evals pillar: an agent loop whose exit condition is *a metric the agent itself measures* (tests pass / coverage target) via an internal run→fix→re-run sub-loop, not a human decision. Bake "terminate when metric M ≥ threshold T, with a bounded fix-retry sub-loop" as a first-class loop-termination strategy alongside `end_turn`/`max_turns`. (3) The shell sandbox as an **MCP-shell-server with an `ALLOW_COMMANDS` allow-list** is a low-effort way to bound a shell tool without a custom policy engine.

---

## Augment Code (closed — MCP-probed + docs)

### What It Is

Augment is a closed enterprise coding agent whose differentiator is the **Context Engine** — a semantic indexer for large (400k+ file) codebases, now exposed as an MCP server (local via `auggie` CLI, or hosted at `api.augmentcode.com/mcp`). Augment's thesis — *"every AI uses the same models; context is the difference"* — is the empirical validation of Verso's context-engineering pillar. The Context Engine MCP is partially RE-able via its tool schema and docs even without source.

### Context Engine MCP — the `codebase-retrieval` tool (KNOWN from docs, INFERRED schema)

The MCP server exposes a single primary tool: **`codebase-retrieval`**, which takes a natural-language query (+ a `directory_path` param to select which indexed workspace to search) and returns curated code context. Live probe of `api.augmentcode.com/mcp` returns `Authorization header required` for both `initialize` and `tools/list` (KNOWN — the hosted endpoint is auth-gated; OAuth or API key required, configured at `app.augmentcode.com/mcp/configuration`). So the tool *count* is 1 primary retrieval tool, not a full agent toolset — the Context Engine is deliberately a **retrieval service**, not an agent. Docs describe what the retrieval does (KNOWN):
- **Semantic understanding** — "a full search engine for code that understands meaning, not just text" (i.e. embeddings + a code-aware index, not grep).
- **Relationship awareness** — understands how files connect across repos/services (a cross-file graph, like Aider's RepoMap but persistent and cross-repo).
- **Beyond code** — indexes commit history, codebase patterns, and external sources (docs/tickets).
- **Smart curation** — "retrieves only what matters and compresses context without losing information" — i.e. the retrieval does its own budget-aware selection + compression server-side before returning (the thing Aider's RepoMap binary-search does, but as a hosted service).

### Local vs Remote indexing (KNOWN, docs)

| | Local server (`auggie` CLI as stdio MCP) | Remote server (hosted, GitHub App) |
|---|---|---|
| Indexed | working directory, **real-time** as you edit | selected repos' **default branches**, updated on push |
| Best for | active editing / new features | understanding / cross-repo context / CI without a working tree |
| Transport | stdio | HTTP (auth-gated) |

Local indexing is real-time (picks up edits immediately, no manual sync) — implying an incremental indexer (file-watch → re-embed changed chunks). Remote is push-triggered on the default branch. **Credit cost: 40-70 credits per query** (KNOWN) — the retrieval is expensive enough that it's metered per call, consistent with "embed + graph-walk + LLM-curate + compress" being a multi-stage server-side pipeline, not a cheap vector lookup.

### `auggie` CLI as headless agent (KNOWN, docs/cli/reference)

The CLI is also a full agent with a headless mode mirroring Continue's: `auggie --print "<instruction>"` (one-shot, `-p`), `--quiet` (final message only), `--output-format json` (structured for automation), `--max-turns N` (turn cap in print mode), `--queue "step2" --queue "step3" "step1"` (sequential instruction queue), `--wait-for-indexing` (block until the codebase-retrieval index is ready before the tool runs), `--permission launch-process:allow` (per-run tool permission rule). It is also an ACP agent (Zed/Neovim/Emacs). Its agent tools mirror the standard set (`view`, `str-replace`, `save-file`, `launch-process`, `grep-search`, `codebase-retrieval`) — the differentiator is purely that `codebase-retrieval` is backed by the Context Engine rather than naive grep.

**For Verso:** Augment validates the core thesis (*context quality > model size*) and shows the right *architecture*: make semantic retrieval a **standalone service with a single `retrieve(query, scope)` tool** that does embedding + cross-file relationship walking + budget-aware curation + compression **server-side**, returning only curated context — exactly Aider's RepoMap promoted to a persistent, incremental, cross-repo hosted service. The retrieval being metered (40-70 credits/query) is the signal that it's a real multi-stage pipeline, not a vector lookup — Verso's context layer should be a first-class retrieval *service* (incremental local index + curation + compression) rather than stuffing raw search results into the prompt. The headless contract (`--print --output-format json --max-turns --wait-for-indexing --permission`) is the same shape as Continue's and worth standardizing for Verso's non-interactive mode.

---

## Cross-Cutting Synthesis for Verso

| Concern | Best reference | The exact mechanism to copy |
|---|---|---|
| Loop shape | opencode | part-queue dispatcher (subtask/compaction as LIFO parts on the user turn), not branches in control flow |
| Overflow trigger | opencode | reactive check on *prior turn's billed tokens* ≥ `min(input,ctx) − min(20k, max_output)` |
| Compaction | opencode | anchored rolling Markdown summary (fixed 8-section template) + verbatim tail (`clamp(usable*0.25, 2k, 8k)`) + `hidden`-set; plus cheap LLM-free `prune()` of tool output >40k |
| Cheap truncation fallback | Cline | dedupe file reads → slide window half/quarter by overage, keep first pair + alternation, cumulative deleted-range |
| Doom-loop guard | Goose (pipeline) + Cline (2-threshold) | `ToolInspector` pipeline; warn at 3 (inject msg) / escalate at 5; strip metadata params from the signature |
| Diff taxonomy | Aider | per-model static format table (whole/diff/udiff/patch); tolerant `<{5,9} SEARCH` regex; exact→whitespace→dotdotdots match cascade; structured no-match error fed back |
| Repo-map context | Aider | tree-sitter def/ref → PageRank (personalization toward chat files; edge ×50 chat-ref / ×10 mentioned / ×0.1 private; `sqrt(refs)`) → binary-search to ±15% of budget; mtime-keyed disk cache |
| Plan/act HITL | Cline | persisted mode w/ per-mode {prompt fragment, tool subset, model}; carry draft across toggle |
| Architect/editor split | Aider | planner emits prose → fresh-context editor coder (empty history, `map_tokens=0`) gets only the prose → collapse back to one line |
| Sub-task isolation | Roo (Boomerang) | freeze parent *to disk*, run child as full task w/ different mode, return only `attempt_completion result` reconstructed as the `new_task` tool_result |
| Typed agent variant | Roo modes + Qodo TOML | `{slug, roleDefinition→prompt, whenToUse→routing, groups→tools (w/ `[group,{fileRegex}]` path-scope)}`; orchestrator = zero tools + delegate-only |
| Checkpoint/undo | Cline | shadow git (`core.worktree`→live tree, `commit --allow-empty --no-verify`, `reset --hard` to restore), folder-locked |
| Durable workflow | Goose Recipe | typed/parameterized/templated/composable doc (params→schema→prompt+tools+output-schema+sub_recipes), minijinja `Strict` + `{% raw %}` hardening |
| Provider normalization | opencode | one `normalize(messages, model)` pass: surrogate scrub, per-provider tool-ID scrub, empty-content filter, cache_control on first-2-system + last-2, `promptCacheKey=sessionID` |
| Non-native tool calls | Goose | small structured-output interpreter model extracts tool calls from prose via delimited sentinels |
| Context as a service | Augment | single `retrieve(query, scope)` tool: embed + cross-file relationship walk + budget-aware curation + compression, server-side, incremental index |
| Headless/CI contract | Continue + Augment | `--print` one-shot, fixed allow-list (no interactive approval), hard timeout, typed failure fallbacks, idempotent sticky artifact, diff-as-bounded-context |
| Eval-driven termination | Qodo Cover | exit when measured metric (tests pass / coverage) ≥ threshold via internal run→fix→re-run sub-loop, not human decision |
| Retry/backoff | opencode | honor uncapped server `retry-after`; else cap 30s exp backoff; never retry context-overflow; always retry 5xx |
| Durable session schema | opencode + Goose | SQLite, message content as JSON blob (schema-on-read), cached rolling token/cost totals, cursor pagination on `(session, time, id)`, `parent_id` subtask tree |

### Session schema — Drizzle/SQLite (KNOWN, `core/session/sql.ts`)

```
session(id PK, project_id FK→project cascade, workspace_id, parent_id,   -- parent_id = subtask tree
        slug, directory, path, title, version, share_url,
        summary_additions/deletions/files INT, summary_diffs JSON,
        cost REAL, tokens_{input,output,reasoning,cache_read,cache_write} INT,
        revert JSON{messageID,partID?,snapshot?,diff?},                  -- checkpoint pointer
        permission JSON Ruleset, agent TEXT, model JSON{id,providerID,variant?},
        time_compacting INT, time_archived INT, ...Timestamps)
  idx: project_id, workspace_id, parent_id
message(id PK, session_id FK cascade, data JSON, ...Timestamps)
  idx: (session_id, time_created, id)                                    -- cursor pagination key
part(id PK, message_id FK cascade, session_id, data JSON)
  idx: (message_id, id), (session_id)
todo(session_id+position PK, content, status, priority, position)        -- agent's task tracker, persisted
session_message / session_input / session_context_epoch                  -- v2 event-sourced tables
```

Notable: **messages and parts store their payload as a single JSON `data` column** (schema-on-read), not normalized columns — so the loop can evolve the message shape without migrations. Pagination is cursor-based on `(session_id, time_created, id)`. `parent_id` on the session table is the subtask tree link (Boomerang-style child sessions). `revert` JSON is the checkpoint/undo pointer. The session itself caches rolling token + cost totals so overflow checks don't re-scan messages.

### ACP (Agent Client Protocol) — editor transport (KNOWN, `acp/service.ts`)

opencode implements `@agentclientprotocol/sdk` `AgentSideConnection` as a JSON-RPC service so editors (Zed, etc.) drive the same server. The interface exposes: `initialize`, `authenticate`, `newSession`/`loadSession`/`listSessions`/`resumeSession`/`closeSession`/`forkSession`, `setSessionConfigOption`/`setSessionMode`/`setSessionModel`, `prompt`, `cancel`. Each maps onto the same `OpencodeClient` SDK calls the TUI uses — ACP is a thin JSON-RPC veneer over the HTTP API, with `sessionUpdate` push notifications + `requestPermission`/`writeTextFile` client callbacks. The architectural point: **the agent is a server; ACP, the HTTP+SSE API, and the TUI are three clients of the same session loop.** (acp/service.ts:1-90)

**For Verso:** opencode is the single most design-aligned target. Copy: (1) the **part-queue loop** where compaction and subtasks are LIFO parts on the user turn, not branches in control flow — it makes the loop composable; (2) the **reactive overflow gate** on the prior turn's real billed tokens with a fixed `min(20k, max_output)` reserve instead of a percentage; (3) the **anchored rolling Markdown summary** with a fixed 8-section template + verbatim budget-bounded tail (`clamp(usable*0.25, 2k, 8k)`) + `hidden`-set to never re-summarize a summarized prefix; (4) the **`prune()`** cheap pass that erases old tool output (>40k) without an LLM call; (5) the **3-identical-tool-calls doom-loop guard** verbatim; (6) the **retry policy** that honors uncapped server `retry-after` but caps to 30s otherwise and never retries context-overflow; (7) **JSON `data` column** message storage (schema-on-read) + cursor pagination on `(session, time, id)`; (8) **agent-as-server** with HTTP/SSE + JSON-RPC as sibling transports.

