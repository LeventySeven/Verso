# Verso baseline — what is ACTUALLY implemented (source, not PRD)

Established 2026-07-23 by grepping `~/Desktop/Verso/verso/` directly. Recorded **before** the mining
results landed so the comparison cannot be tuned to the answer.

**Why source and not the PRD:** the PRD describes the designed architecture, and parts of it were
never built. Comparing production frequency against an aspirational surface would silently inflate
Verso's coverage and hide real gaps. Confirmed instance: **PRD §4.2's module map and §6.2 both list
`orchestrate/`** (subagent-as-context-isolation, parallel fan-out, graph escape hatch) — **the module
does not exist.** Only `examples/orchestrator_workers.py` does. The README is honest about this and
points at the example; the PRD is not. That is a doc-truth fix regardless of what the census says.

## Implemented (20)

`model_driven_tool_loop` · `bounded_step_budget` · `stuck_or_loop_detection` · `context_compaction` ·
`context_window_budgeting` · `prompt_cache_discipline` · `tool_output_budget` ·
`tool_retry_or_self_heal` · `checkpoint_resume` · `human_in_the_loop_gate` ·
`idempotency_for_side_effects` · `cross_provider_failover` · `output_schema_validation` ·
`offline_eval_suite` · `llm_as_judge` · `permission_or_sandbox` · `typed_or_scoped_memory` ·
`cross_session_memory` · `memory_consolidation_job` · `multi_model_routing` (partial — model policy +
failover, no routing DSL)

## Absent — DELIBERATE non-goals (PRD §2, §14.15 RESIST)

Do **not** propose these regardless of frequency; a high count is evidence about the market, not a
reason to violate a stated non-goal. Flag the count, let the owner decide.

- `explicit_graph_runtime` — "not a graph-DSL by default"; graphs are an opt-in escape hatch
- `agent_to_agent_messaging` — "A2A protocol / message-bus / agent-marketplace" explicitly RESISTed
- `finetuned_task_model` — "task-specialized fine-tuned worker models" explicitly RESISTed
- `knowledge_graph_memory` — "enterprise knowledge-graph memory topology" explicitly RESISTed
- `multi_model_routing` as a DSL — "model-router DSL / learned router" explicitly RESISTed
- `named_state_machine` on the loop — "a phase/mode state machine on the loop" explicitly RESISTed

## Absent — GENUINELY OPEN (the candidate set)

These are not non-goals. If the census puts one at **≥10–15 independent products**, it earns a
serious design conversation; below that it stays out.

| Capability | Status in Verso |
|---|---|
| `subagent_spawn` | designed in PRD §6.2, **not built** |
| `orchestrator_worker_topology` | designed in PRD §6.2, **not built** (example only) |
| `separate_critic_or_verifier` | `verify-before-done` gate exists; no distinct critic agent/model |
| `plan_then_execute_phase` | `mode="plan"` in the PRD API sketch; **not in source** |
| `progressive_tool_disclosure` | absent entirely |
| `code_execution_as_action` | absent entirely |
| `mcp_integration` | present but deliberately demoted/opt-in |
| `durable_execution_engine` | checkpoint/resume yes; Temporal-class engine no (deferred by design) |

## The decision rule (fixed now)

A capability is proposed for Verso only if **all four** hold:

1. **≥10 independent products** in the census have it (the owner's threshold — one or two startups is anecdote).
2. It is **absent** from the implemented list above.
3. It is **not** a stated non-goal.
4. It can be added **additively** — byte-identical behavior when unused, per the repo's first rule.

Anything failing (3) gets reported with its count and explicitly **not** recommended — the count is
information for the owner, not a mandate. Anything failing (4) gets reported as "needs a design
conversation," not shipped.
