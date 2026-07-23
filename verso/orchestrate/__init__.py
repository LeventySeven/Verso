"""Opt-in multi-agent orchestration — a SEPARATE import, never the default.

    from verso.orchestrate import fan_out, spawn, Reviewer

The whole module is helpers over `asyncio`, not a runtime. There is no graph, no node/edge DSL, no
scheduler — the control flow stays plain Python you can read and step through. Importing this changes
nothing about a plain `Agent`; a program that never imports it is byte-identical.

Why it exists (PRD §6.2, and measured): a lead delegating to workers is the single most common
multi-agent shape in production — 69 of 321 reverse-engineered systems. It is also the pattern
`examples/orchestrator_workers.py` already writes by hand in raw `asyncio.gather`. This module gives
that hand-written pattern the three things the raw version lacks and everyone re-implements:

  1. `fan_out`  — bounded concurrency (LLMs are bad at self-managing 50 parallel calls; you should
                  not hand-roll a semaphore every time), with per-item failure isolation.
  2. `spawn`    — a sub-agent as a CONTEXT-ISOLATION device: its tokens never pollute the parent, it
                  returns a compact result, and nesting is depth-capped so an orchestrator cannot
                  accidentally recurse into a fork bomb.
  3. `Reviewer` — the cross-model "rubber duck": the cheapest multi-agent win, a critic from a
                  different model family checking the first agent's output.

Deliberately NOT here (PRD §6.2): adversarial self-play, convergence-based termination, nested
orchestrators by default, and sub-agents writing the final report. The lead synthesizes.
"""
from verso.orchestrate.core import (
    DepthCapExceeded,
    Reviewer,
    Subagent,
    fan_out,
    spawn,
)

__all__ = ["fan_out", "spawn", "Subagent", "Reviewer", "DepthCapExceeded"]
