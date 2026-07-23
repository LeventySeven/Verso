# Verso pattern-mining — verdict

**2026-07-23.** 48 agents · **321 products classified** (2 unreadable) from 332 teardowns, sliced
mechanically. Agents got a neutral 35-capability vocabulary and **were told nothing** about Verso,
any framework, or any hypothesis. Baseline = Verso *source* (not the PRD), fixed in `BASELINE.md`
before results. Decision rule, all four required: **≥10 independent products · absent from Verso
source · not a stated non-goal · addable additively.**

Counts below are **independent companies** (sub-teardowns like `COMPOSIO_R4_*`, `HERMES_DEEP_*`
collapsed to their parent) — the dedup barely moved anything, so the signal is real.

## First result: the corpus validates Verso's spine

The capabilities Verso builds are exactly the ones production converges on:

| Capability Verso HAS | production freq |
|---|---:|
| native_function_tools | **52%** |
| model_driven_tool_loop | **46%** |
| cross_session_memory | 46% |
| output_schema_validation | 45% |
| permission_or_sandbox | 45% |
| human_in_the_loop_gate | 43% |
| checkpoint_resume | 36% |
| bounded_step_budget | 30% |
| context_compaction / tool_output_budget / retry / idempotency | 21–26% |

Nothing Verso ships is rare enough to be over-engineering: the lowest are `stuck_or_loop_detection`
(9%) and `memory_consolidation_job` (10%), both small and opt-in/default-conservative. **I looked for
things to cut and found none.** The "boring core done right" thesis survives contact with 321
shipped products.

## Second result: the ONE gap that clears all four gates

**`orchestrator_worker_topology` (69 companies) + `subagent_spawn` (72 companies).**

- **≥10?** 69–72 independent companies — the strongest signal in the census.
- **Absent from source?** Yes. `verso/orchestrate/` **does not exist** — only `examples/orchestrator_workers.py`.
- **A non-goal?** **No — the opposite.** PRD §4.2's module map and §6.2 both *design* `orchestrate/`
  (subagent-as-context-isolation, parallel fan-out) and it was never built. This is the largest
  designed-but-unshipped gap in Verso.
- **Additive?** Yes — a separate `from verso.orchestrate import …`, byte-identical when unused.
- **Aligned?** Fully. The pattern in production is a lead + workers merging results — the
  `asyncio.gather` fan-out Verso's own example already shows. **This is not "add graphs." It is
  "build the opt-in fan-out module you already designed," in plain async Python.**

Companies: 11X, Agentforce, AI-Co-Scientist, Anthropic Research/Claude Code, AutoGen, Devin, Hermes,
Manus, Magentic-One, and 60+ more.

**→ ACTION: build `verso/orchestrate/` for real.**

## Candidates that clear the count but are pattern/recipe, not a new primitive

- **`separate_critic_or_verifier` (46)** — Abridge, CodeRabbit, Claude Research, AI-Co-Scientist, …
  Verso has a `verify-before-done` gate but no *distinct critic agent*. The PRD §14.10 already names
  "reviewer-as-supervisor." **→ ship as a documented recipe + a thin helper on top of orchestrate/,
  not a heavy subsystem.**
- **`progressive_tool_disclosure` (33)** — Claude Code, Codex, Composio, Glean, … Absent from Verso,
  and it lands squarely in Verso's stated moat (context engineering). Additive. **→ a real candidate;
  a `tool_search`-style deferred-schema helper. Second priority after orchestrate/.**

## High count, but REPORT-not-build (number is information, not a mandate)

- **`mcp_integration` — 102 companies (highest non-core).** Verso HAS it, deliberately demoted to
  opt-in. Fails gate 2 (not absent). And the transcript pass found Anthropic's own Applied AI team
  calling MCP-*first* an anti-pattern. **Verso's "have it, don't center it" is the reconciled
  position** — 102 companies use MCP, and the people who built the biggest ones say don't lead with
  it. No change; the number vindicates the demotion rather than challenging it.
- **`named_state_machine` — 70 companies.** High, but these are *products' domain state machines*
  (Abridge's `ML_STARTED→ML_PROCESSING`, 11X's 119 enums) — business logic on top of the agent, not a
  framework primitive. Forcing one is exactly the LangGraph tax Verso rejects; §14.15 RESISTs "a
  phase/mode state machine on the loop." **The count supports Verso's refusal, it doesn't challenge
  it.**
- **`plan_then_execute_phase` — 72 companies.** Borders the same non-goal. The PRD API sketch has
  `mode="plan"` as a knob (not in source). **→ flag the tension; a plan-mode *knob* is defensible, a
  plan/execute *state machine* is not. Owner's call, not an auto-build.**
- **`code_execution_as_action` — 71 companies.** The model writing+running code (Claude Code, Devin).
  Verso is tool-agnostic — a code-exec tool is *a tool the user brings*, already supported via `@tool`.
  **→ a reference sandboxed-exec tool + recipe, not a framework primitive.**
- **`explicit_graph_runtime` — 32 companies (10%).** A stated non-goal. The count (10%, consistent
  with the earlier orchestration census's 7%) **confirms graphs are a production minority.** Report,
  do not build.
- **`finetuned_task_model` — 63 companies.** You cannot ship a fine-tune inside a framework; non-goal
  by nature. Report only.

## What actually changes

1. **Build `verso/orchestrate/`** (subagent-as-context-isolation + fan-out, plain asyncio, no graph) —
   the one all-gates-pass enhancement, and the PRD's own designed-but-unbuilt module.
2. **Fix PRD doc-truth:** §4.2/§6.2 describe `orchestrate/` as if it exists. Until #1 lands it must
   say "designed, not yet built (see `examples/`)."
3. **Queue** `progressive_tool_disclosure` (context-engineering moat) and the critic *recipe* as the
   next two, below orchestrate/ in priority.
4. **Change nothing** for graphs / state machines / MCP-centering / fine-tuned workers. The census
   put numbers on the non-goals and they hold.

**The headline:** the corpus does not say Verso is wrong. It says Verso is right about its spine and
its refusals, and has one real hole — the opt-in orchestration module it designed and never built.
Everyone talking about graphs (10% of production) is arguing about a minority pattern; the majority
that isn't a static pipeline runs a loop with tools, HITL, and — when it fans out — a lead delegating
to workers. Which is exactly Verso, minus the module we're about to build.
