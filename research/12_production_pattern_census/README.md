# 12 — Production pattern census (2026-07-23)

The design-evidence pass that drove `verso/orchestrate/`. 48 agents classified **321 production AI
systems** (from 332 reverse-engineered teardowns in the `researchfms` corpus) against a neutral
35-capability vocabulary. Agents were told nothing about Verso or any hypothesis; the vocabulary
deliberately included Verso's stated non-goals so a high count could contradict the design.

- **`BASELINE.md`** — what Verso *actually implements in source* (not the PRD), fixed before results,
  plus the four-gate decision rule.
- **`VERDICT.md`** — the frequency table, the one gap that cleared every gate (orchestrator-workers,
  69 independent systems → built `orchestrate/`), and the non-goals that held under their own numbers
  (graphs 10%, MCP 102-but-reconciled, state machines 70-but-domain-logic).

Companion to `11_raw_top1pct_validation/` (which asked "is any primitive missing?"); this asks "does
production actually run what Verso builds?" Both answered: spine confirmed, refusals hold, one real
hole — now closed. Raw per-agent output lives in the `researchfms` working tree
(`_scratch/verso-mining/`), not here.
