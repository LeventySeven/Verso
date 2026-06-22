# LETTA / MemGPT — Raw Extraction (memory architecture)

Source read: `/Users/seventyleven/Desktop/researchfms/teardowns/LETTA.md` (2063 lines, 177KB).
Teardown is Tier-1A: open-source repo line-by-line + installed pip package + MemGPT paper (Packer et al., 2023, UC Berkeley) + live `api.letta.com` probe.
All findings KNOWN-from-source unless marked INFERRED/DESIGNED.

---

## 0. The novel primitive (KNOWN, teardown §0, lines 12–14)

> "Letta = self-editing memory blocks + recall search + archival store, presented to the LLM as native tool calls. The novel primitive is **virtual context management**: the LLM doesn't see all its memory; it sees a curated 'core memory' block (the persona, the user model, project state) that it can rewrite *with tool calls*, plus a 'recall memory' search over all past messages, plus an 'archival memory' semantic store for facts that don't fit in core memory."

The "LLM OS" framing (MemGPT paper): context window = **main memory** (small, fast, in-prompt); recall + archival = **disk** (larger, slower, fetched via tools). When the conversation grows past the context window, a separate **compaction** model summarizes the old messages and writes the summary back before eviction.

Three tiers (teardown §0 diagram):
- core memory — in-prompt, agent-editable — persona / human / coding_preferences
- recall memory — DB-backed, agent-searchable — ALL past messages (the message DB itself)
- archival memory — vector store, agent-searchable — facts the agent inserts
- files — open-file system (MemGPT v3+) — PDFs/code/docs mounted as blocks

---

## 1. Core memory blocks (`schemas/block.py`, 209 lines) — KNOWN

`Block` is a Pydantic schema with `validate_assignment=True`. Fields: `value: str` (content), `limit: int = CORE_MEMORY_BLOCK_CHAR_LIMIT` (per-character cap), `label` (`"persona"`/`"human"`/`"coding_preferences"`), `description` ("how this block influences behavior"), `read_only`, `hidden`, plus template/deployment/entity ids.

Subclasses:
- `Human(Block)` — `label="human"`, desc="Stores key details about the person you are conversing with."
- `Persona(Block)` — `label="persona"`, desc="Stores details about your current persona, guiding how you behave and respond."
- `FileBlock(Block)` — `label=<filename>`, has `file_id`, `source_id`, `is_open`, `last_accessed_at`. **File contents are mounted as a block.**

Operational details: null-byte sanitizer strips `\x00` on write (PostgreSQL chokes on it); auto-validate-on-assign re-checks length against `limit` every time `.value` changes.

`Memory` object (`schemas/memory.py`, 884 lines): `get_block(label)`, `set_block`, `update_block_value`, `delete_block`, `rename_block`, `compile_to_string()`. Blocks render to the system prompt as XML at EVERY turn (rebuilt because they change):
```
<persona>{...}</persona>
<human>{...}</human>
<coding_preferences description="The user's coding preferences.">{...}</coding_preferences>
```
"The agent doesn't see a static system prompt; it sees a live one." Injection placeholder `IN_CONTEXT_MEMORY_KEYWORD = "CORE_MEMORY"`.

---

## 2. Self-edit memory tools (`function_sets/base.py`, 527 lines) — KNOWN, verbatim signatures

- `core_memory_append(agent_state, label, content) -> str` (line 246): `new_value = current_value + "\n" + content`.
- `core_memory_replace(agent_state, label, old_content, new_content) -> str` (line 263): raises `ValueError` if `old_content not in current_value`; "To delete memories, use an empty string for new_content."
- `memory_replace(agent_state, label, old_string, new_string)` (line 311): v2 variant **based on Anthropic's computer-use-demo `edit.py`** (cited in code). Stricter: `old_string` must match exactly once including whitespace.
- `memory_insert(agent_state, label, insert_line, insert_text)`: insert at a line number, arrow-format prefix `MEMORY_TOOLS_LINE_NUMBER_PREFIX_REGEX = r"^[ \t]*\d+→[ \t]*"`.
- `memory_rethink(agent_state, new_memory, target_block_label)` (line 283): docstring — "Rewrite memory block... new_memory should contain all current information from the block that is not outdated or inconsistent, integrating any new information, resulting in a new memory block that is organized, readable, and comprehensive." = **active consolidation** (full block rewrite).
- `memory(agent_state, command, path, file_text, ...)` (line 10): v3 **omni-tool** unifying `command ∈ {create, str_replace, insert, delete, rename}`. Designed for Claude Sonnet 4.6 — "Anthropic models prefer one well-designed tool over many small ones, while older models worked better with split tools."

Tool-set versioning (back-compat preserved):
```python
BASE_MEMORY_TOOLS    = ["core_memory_append","core_memory_replace","memory","memory_apply_patch"]
BASE_MEMORY_TOOLS_V2 = ["memory_replace","memory_insert"]
BASE_MEMORY_TOOLS_V3 = ["memory"]   # omni-tool, for Anthropic
```

Key prompt instruction (v2 prompt, anti-redundant-tool-call): "You always first check what is immediately in your context and you never call tools to search up information that is already in an open file or memory block."

---

## 3. Recall memory (`conversation_search`, line 87) — KNOWN

`conversation_search(self, query, roles, limit, start_date, end_date)`. Hybrid text + semantic search over the agent's **entire message history** (recall = the message DB itself). `roles` filters `assistant`/`user`/`tool`. `limit` default `RETRIEVAL_QUERY_DEFAULT_PAGE_SIZE`. ISO-8601 dates; date-only inclusivity is explicit ("includes messages starting from 00:00:00 of that day") because "the agent talks to humans who think in days." Impl calls `message_manager.list_messages_for_agent`, returns `{role, content}` JSON.

---

## 4. Archival memory (vector store) — KNOWN

- `archival_memory_insert(self, content, tags: Optional[list[str]])` (line 164). Stores a **passage** (one entry). Docstring best-practices: "Store self-contained facts or summaries, not conversational fragments / Add descriptive tags / Use for: meeting notes, project updates, conversation summaries, events, reports / persists indefinitely and can be searched semantically." Example tags: `["meetings","roadmap","q2-2024"]`.
- `archival_memory_search(self, query, tags, tag_match_mode='any', top_k, start_datetime, end_datetime)` (line 194). `tag_match_mode ∈ {"any","all"}`. top-k default 10. Date filtering.

Storage: `ArchiveManager` (718 lines) → `Passage` ORM → PostgreSQL + `pgvector` (`CREATE EXTENSION IF NOT EXISTS vector;`).
Embedding constants (`constants.py:93`): `MAX_EMBEDDING_DIM = 4096` ("do NOT change or DBs need reset"), `DEFAULT_EMBEDDING_CHUNK_SIZE = 300`, `DEFAULT_EMBEDDING_DIM = 1024`, `EMBEDDING_BATCH_SIZE = 200`.

Note: `archival_memory_insert`/`archival_memory_search` are marked **deprecated** in `BASE_TOOLS` (superseded by the `memory` omni-tool family + files layer).

---

## 5. Files memory layer (`function_sets/files.py`) — KNOWN (post-paper, newest)

- `open_files(file_paths)` — mounts file contents as FileBlocks in core memory; agent reads inline thereafter.
- `grep_files(pattern, file_paths)` — regex search within open files.
- `semantic_search_files(query)` — vector search across attached files.
`is_open` flag controls whether content is mounted in the system message; agent must `close_file_for_agent` (REST) to evict.

---

## 6. Compaction / summarization (`services/summarizer/`, 2,116 lines, 9 files) — KNOWN

- Trigger: `SUMMARIZATION_TRIGGER_MULTIPLIER = 0.9` → compact at 90% of `context_window`. GPT-5 family (regex `r"(^|/)gpt-5($|[.-])"`) triggers **proactively at 90%** — comment: "We observed GPT-5 runs hitting max_output_tokens exceeded when prompt input got close to the 272k input context window; this aligns GPT-5 behavior with the codex harness' proactive 90% compaction policy."
- Model routing (`compact.py:42`, INFERRED from comment): `letta/auto` agents route summarization to **Anthropic Claude Haiku 4.5** (cheap), falling back to **ZAI GLM-5**. "Full-conversation summarization happens with a small model, leaving budget for the main agent's frontier model."
- Three compaction modes: **sliding window** (keep N recent verbatim, summarize rest), **summarize all** (replace ALL prior with one summary), **self-summarize** (agent uses its own model). Summary becomes a synthetic message `role="summary"`.
- `CompactionStats`: `messages_before/after`, `tokens_before/after`, `compaction_time_ms`, `summary_token_count` — surfaced to operator.

---

## 7. Sleep-time agents (`voice_sleeptime_agent.py`, prompt 75 lines) — KNOWN

Distinctive primitive. After a conversation ends (or at scheduled interval), a SEPARATE agent runs against the chat log to consolidate memory: reads recent messages → rewrites core blocks via `memory_rethink` → optionally archives old messages via `store_memories` → `finish_rethinking_memory` and shuts down. "Modeled on biological sleep/REM consolidation. The active-conversation agent doesn't have time/budget to reorganize its memory; the sleep-time agent does this asynchronously."
```python
BASE_SLEEPTIME_TOOLS       = ["memory_replace","memory_insert","memory_rethink","memory_finish_edits"]
BASE_VOICE_SLEEPTIME_TOOLS = ["store_memories","rethink_user_memory","finish_rethinking_memory"]
```
Sleep-time prompt opens: "You are an autonomous agent responsible for maintaining and improving an LLM agent's long-term memory." A meta-agent whose whole job is curating ANOTHER agent's memory.

---

## 8. Loop / heartbeat / tool rules (context) — KNOWN

- `step(max_steps=DEFAULT_MAX_STEPS=50)`; per-step: prepare in-context msgs → adapter select → loop → tool exec (sandboxed) → check `request_heartbeat`.
- Heartbeat: `REQUEST_HEARTBEAT_PARAM = "request_heartbeat"` injected as a param on EVERY tool: "You MUST set this value to `True` if you want to send a follow-up message or run a follow-up tool call (chain multiple tools together). If set to `False` (the default), then the chain of execution will end immediately." = agent decides whether to yield or keep thinking.
- 13 stop reasons enum (`end_turn`, `max_steps`, `tool_rule_violation`, `context_window_exceeded`, `rate_limit_exceeded`, `invalid_tool_call`, ...).
- Tool rules solver: `MaxCountPerStepToolRule`, `ContinueToolRule`, `TerminalToolRule`, `InitToolRule`, `RequiresApprovalToolRule`, `ChildToolRule`/`ParentToolRule` (directed-graph constraints). Violations → `tool_rule_violation`.
- `LETTA_PARALLEL_SAFE_TOOLS` = {conversation_search, archival_memory_search, run_code, web_search, fetch_webpage, grep_files, semantic_search_files}. **Memory WRITES are NOT parallel-safe — they serialize.**
- Conversation-isolated blocks: `apply_isolated_blocks_to_agent_state` — same agent, different core memory per conversation thread.

---

## 9. Comparison verdict (teardown §16) — KNOWN

"Letta is the **only one** that ships memory as a first-class native primitive with tools. LangGraph leaves memory to the developer; CrewAI gives you conversation history; OpenAI Assistants give you a vector store but no self-editing blocks. Letta = MemGPT productionized + multi-tenanted + multi-provider." 17 providers (incl. own `inference.letta.com`).

---

## 10. Judgment vs Verso memory layer

Verso already has: typed 4-tier memory (FACT/...), temporal, RRF recall, `recall_as_of` (time-travel), `reflect()` consolidation, ADD-only/supersede, bounded, sqlite/sqlitevec/inmem.

- **Self-editing in-prompt core blocks** (persona/human, agent rewrites its own system prompt): NOT Verso's model. Verso uses ContextBundle + prune() + retrieval; it does NOT let the model freely rewrite the system prefix (KV-cache-stable prefix is a deliberate Verso invariant). Mounting agent-mutable blocks into the system message would BREAK KV-cache stability → **avoid-overkill** against thesis.
- **`reflect()` ≈ `memory_rethink` / sleep-time consolidation**: Verso already has consolidation. Letta's sleep-time-as-separate-async-agent is a heavier orchestration; Verso's `reflect()` covers the substance → verso-already-has (the async meta-agent wrapper is avoid-overkill).
- **Recall/archival/temporal/tag-filter/semantic search**: Verso already has (4-tier + RRF + temporal + recall_as_of).
- **Block `description` field** ("how this block influences behavior" — a per-memory steering hint shown to the model): small, additive, byte-identical-when-unused. Genuinely not obviously present in Verso's typed memory. Low-cost candidate.
- **`tag_match_mode` any/all on recall**: tiny additive filter primitive; Verso has RRF retrieval but an explicit any/all tag-match filter is a small ergonomic add.
- LLM-summarization-compaction-by-default, omni-tool memory, multi-provider proxy, ADE, grammar-constrained local LLM: all either Verso NON-GOALS or avoid-overkill.
