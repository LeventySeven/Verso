# Design note — progressive tool disclosure (NOT built; here is why, and what the right shape is)

**Status:** deliberately not implemented. The evidence for the *goal* is strong; the evidence against
the *obvious implementation* is equally strong, and they come from the same corpus.

## The pull

- `articles/code-execution-with-mcp.md:138` — *"This reduces the token usage from 150,000 tokens to 2,000 tokens—a time and cost saving of 98.7%."*
- `TRANSCRIPTS_OPENAI.md:1512` — a production split of always-on core tools vs schema-appended-on-demand tools cut tool-schema tokens 45% and total cost 33%.
- `TRANSCRIPTS_GOOGLE.md:12984` — real deployments reach ~10 integrations / 200 tools / 50 skills.
- Independent convergence that tool *selection* degrades well before context does: ~10–20 tools
  (`TRANSCRIPTS_DEEPLEARNINGAI_COURSES.md:5810`), AWS warning against MCP-ifying every endpoint
  (`TRANSCRIPTS_AWS_REINVENT.md:10416`), Anthropic advising collapsing narrow endpoints into broader
  tools (`TRANSCRIPTS_ANTHROPIC.md:1836`).

## The block — from the same corpus

Tool schemas sit **early** in the context. Mutating anything early invalidates the KV cache for every
token after it:

> `- The KV cache makes mid-context eviction economically ruinous: removing anything from an early context block (like the tools list) invalidates the cache for every token after it` — `TRANSCRIPTS_CODE_WITH_CLAUDE.md:4621`

> KV/prompt caching in an agent loop hard-requires the context window to be append-only — any mutation earlier in context (tool schema updates, a changing system-prompt timestamp) invalidates it — `TRANSCRIPTS_OPENAI.md:1494`

And cached input is ~1/10 list price (`TRANSCRIPTS_CLAUDE.md:3347`). **So the naive version — swap the
tool block per turn based on what the model seems to need — spends more than it saves.** It is a
plausible-looking optimization that the corpus says is a net loss.

## The shape that survives both

Not dynamic re-selection. A **static core set + append-only disclosure**:

1. `@tool(core=True)` — tools present in the system prefix on every turn. Chosen once, per agent, by
   the caller. The prefix never mutates, so the cache prefix stays intact.
2. Non-core tools contribute **name + one-line description only** to the prefix — the fixed small cost
   Anthropic's Skills pay (`TRANSCRIPTS_ANTHROPIC.md:7677`: progressive disclosure, name+description
   resident, full file loaded on match).
3. A builtin `load_tool_schema(name)` returns the full schema **as a tool result** — i.e. appended at
   the tail, never spliced into the prefix. Cache-safe by construction.
4. Nothing changes when nobody marks a tool `core` — every tool stays fully resident, byte-identical.

## Why it is not built yet

It needs a new builtin tool and it changes what the model sees on turn 1 for anyone who opts in. That
is a design decision with a real failure mode (a model that never calls `load_tool_schema` and so
never discovers the tool it needed), and it wants an eval before it ships, not after — the corpus is
explicit that reflection/self-selection without an external signal is unreliable. It is the largest
remaining item from this sweep and the only one that deserves its own plan.

**The cheap precursor, if you want signal first:** `Agent.inspect(task)` already returns the exact
bundle. Counting tool-schema tokens as a fraction of the turn-1 bundle across a few real agents costs
nothing and tells you whether the 45% is even on the table here.
