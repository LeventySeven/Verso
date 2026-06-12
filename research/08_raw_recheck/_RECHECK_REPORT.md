# Verso — Raw-Source Recheck (Plan + PRD)

**Date:** 2026-06-12
**Trigger:** Pre–Phase-1 recheck. Read the FULL raw sources behind *The Bad Guide* CTO + AI sections (not the existing harvest summaries), then recheck the locked PRD + plans against them under the no-overkill / no-bullshit / simplicity rule.
**Method:** 4 parallel read-only research workers over disjoint source clusters; every finding mapped to a PRD section and gated against the invariants. Per-cluster evidence (verbatim quotes + URLs):
- `cluster1-harness-craft.md` — Anthropic "Effective harnesses for long-running agents" + "Effective context engineering"; Ronacher "Agent Design Is Still Hard"; Thorsten Ball "How to Build an Agent".
- `cluster2-adversarial.md` — browser-use "Bitter Lesson of Agent Frameworks"; Huntley "Ralph"; Goedecke "code review"; Cursor "Instant Apply" + "Real-time RL".
- `cluster3-multiagent-reliability.md` — Cognition "Don't Build Multi-Agents" + the 2026 "Multi-Agents: What's Actually Working" update; Sierra (Bavor, Sequoia transcript); Hippocratic constellation.
- `cluster4-evals-info.md` — Shunyu Yao "The Second Half"; Hamel "Your AI Product Needs Evals"; Goyal/Braintrust; Hebbia "Goodbye RAG".

These were the genuinely-NEW, fetchable-text sources (0–1 prior harvest hits): the BAD_GUIDE's **"2026 additions"**, added *after* the PRD's 2026-06-04/05 research pass.

---

## Verdict: **APPROVED — design holds.** Apply 1 code fix + 6 surgical PRD enhancements; do not rebuild.

The locked design survived a full adversarial raw-source pass, including a dedicated steelman that read the strongest "frameworks are a mistake" essays. **No architecture broke; no non-goal reversed; the §1 bet is independently vindicated** (Cursor: the frontier model *cannot* do the latency-critical executor job, and the harness's reward flywheel *generates the weights* — "the harness is upstream of the model"). The pass produced one grounded code gap, six small design enhancements (mostly interface-reservations and correctness sharpenings that *earn their place*), and an explicit RESIST list where adopting the source's idea would be overkill for a v1 personal-infra framework.

This is the expected shape for a design that was already adversarially audited: the raw sources **sharpen** it, they don't redirect it.

---

## Findings (cheapest-disqualifying-first; severity by impact)

### 1 — Goals / principles alignment: **PASS.** Not overkill; every wedge is reconfirmed by a primary source.
- §5.5 evals wedge is **real and under-sold**, not mis-chosen. Ronacher (shipping a production agent): evals are *"the hardest problem… we haven't found something that really makes us happy."* Yao: *"evaluation becomes more important than training."* The wedge solves genuine top-tier pain.
- §1 harness-as-moat **vindicated against its strongest attack** (see Finding 5).

### 2 — Plan alignment: **PASS, with one grounded code gap.**

**[Important → Deferred (intent-verified 2026-06-12)] `verso/model/anthropic.py` — KV-cache *discipline* shipped; provider *activation* (`cache_control`) deliberately deferred to Phase 2.**
- issue: `stable_prefix` is byte-stable (the hard part — done), but no code emits `cache_control: {type:"ephemeral"}`; `grep -ri cache_control verso/` returns **zero hits**. The Anthropic call just sets `kwargs["system"]=system`.
- why: Anthropic prompt caching is **not automatic** (unlike OpenAI ≥1024 tok). Without an explicit breakpoint, the byte-stable prefix is re-billed at full price every turn — so §5.2's headline *"~10× cost reduction from architecture alone"* is **not realized** by Phase-0 code. This is the single highest-ROI concrete change the whole pass surfaced.
- fix: place one `cache_control` breakpoint at the end of the stable prefix (system + tool schemas); model it as a **positioned breakpoint object** (Ronacher: a second, *moving* breakpoint at the conversation tail is the next increment).
- **resolution (intent-verified 2026-06-12):** *deliberate, not a defect.* Plan 3 scoped KV-cache **discipline** (stable prefix + deterministic serialization) and **explicitly deferred cache-hit telemetry** (plan3 lines 13, 816); the plan-3 RECHECK accepted that discipline as the Phase-0 deliverable (§5, line 106); PRD §13 keeps the model layer thin until Phase 2. → **Confirmed Phase-2 model-layer item.** When it lands it must pair with cache-token telemetry (`cache_read_input_tokens`, which the `Usage` type doesn't yet capture) and respect Anthropic's ~4096-token minimum prefix (a small dogfood prefix won't cache regardless — so "~10×" is a *scale* claim). **No code change made now.**

### 3 — Bugs / correctness sharpenings introduced by the new evidence (apply regardless of scope, like the §10 panel fixes):

**[Important] §5.5 judge design — alignment metric.** Hamel: judge↔human agreement must be scored as **precision/recall, not raw agreement** (*"raw agreement… can be misleading when classes are imbalanced"*). The PRD's judge-panel + human-alignment review under-specifies this; a judge validated on raw agreement over a 90/10 class split looks calibrated while being useless.

**[Minor] §5.5 experiment surface — `compare()` must return a per-case regression list,** not just aggregate p50/p80 (Braintrust: *"Is that 8% better on everything, or 15% better and 7% worse? Where it's 7% worse, what cases regressed?"*). An aggregate win hides per-case regressions — the exact failure an eval exists to catch.

### 4 — New genuine gaps (small; lock the interface now, build in the phase that earns it):

**[Important] §5.2 ↔ §6.1 boundary — compaction ≠ cross-cold-start handoff.** Anthropic (verbatim): *"compaction isn't sufficient… even a frontier coding model… in a loop across multiple context windows will fall short… if it's only given a high-level prompt."* Verso's in-context compaction (observation-masking, summarize-replace) keeps **one run** under budget but does **not** carry a task across a cold start / durable resume. The fix is a **persisted, re-readable structured-handoff artifact** (goal / done / files / failed-and-why / next / constraints) surfaced at durable resume — the durable twin of compaction. This is load-bearing for §4's whole durable-seam story. **Lock the concept; build in Phase 2.**

**[Minor] run-scoped writable workspace (`ctx.workspace`).** 3 of 4 harness sources independently converge on a filesystem-shaped durable handle (progress file + git workspace; a "virtual file system" so tools share artifacts by path; file-based memory). Verso has JIT *read* retrieval but **no write side** — nowhere for a tool to drop a blob and hand back a path. Unifies with the progress artifact above (the workspace *holds* the progress file). **Lock the concept; build Phase 2/3** (needs durable + sandbox to earn weight).

**[Minor] §5.5 — `eval.from_trace(trace_id)` / incident→regression.** Sierra *and* Hippocratic independently: *"every time we make one of these improvements, we create a new test so that we can see forever into the future."* §5.5 already has the substrate (eval == run, native traces, trace→JSONL). A captured production failure **is already a trace**; the only missing affordance is a thin freeze-this-trace-into-the-permanent-suite call. This **is** §1's accreting eval-corpus moat made concrete. **Lock the interface (Phase 1, where traces land); RESIST synthetic conversation generation** (Phase 3+).

### 5 — The steelman (the adversarial cluster's job): **bet survives; one locked decision needs a hedge.**
- Strongest attack (browser-use): *"All the value is in the RL'd model, not your 10,000 lines of abstractions… every abstraction is a liability."* It lands on **loop-bloat and hand-authored tool abstractions** — *not* on Verso's non-goals; the same essay **keeps evals and context discipline**, which are Verso's two named wedges.
- The one blow that draws blood: **`@tool`-as-THE-path (§3) is the single abstraction the next model is most likely to delete** (Code Mode / raw protocol). Verso defers Code Mode to Phase 3 while browser-use says raw protocol *is the whole point*.
- **[Important] Fix (hedge, don't reverse):** reserve a **tax-free raw / code-execution escape hatch** now — pull the *interface* of §13's deferred `CodeSandbox` / a raw-tool path forward, so `@tool` stays the ergonomic default but is not the *only* door. This is the wrapper-test applied to Verso's own most-deletable abstraction; it costs an interface line, not a build.
- Vindication to cite, not act on: Cursor (in the most capability-saturated domain, coding): *"It is not possible to build speculative edits into any of Anthropic's models, so we… train and deploy a performant custom model"* + *"we serve model checkpoints to production… aggregate responses as reward signals."* The harness is irreducible and upstream of the weights — Verso's §1, proven by its own attacker's sister team.

### 6 — Patterns / framing sharpenings (fold in; no new types):
- **§6.2** — promote the cross-model reviewer hook to a *named* "supervisor / intelligence-not-actions" pattern (Cognition 2026: *"multi-agent works best when writes stay single-threaded and the additional agents contribute intelligence rather than actions"* — Verso's exact lock, in their words) + a `persona` knob (Sierra). Sub-agent summary budget = **1,000–2,000 tokens** + a **"failed approaches"** slot.
- **§6.4** — name the **decider/executor split** as a pattern (big model decides, small fast model executes) and the invariant **"every seam is an audited exploit surface"** (Cursor RL: the model emitted *broken tool calls to dodge negative reward* — directly relevant to `{data,error,ok}` dispatch + eval scoring).
- **§5.2** — adopt the names **"context rot"** / **"attention budget"**, and the second degradation cause the harvest lacked: long-context failure is *not only* n² attention but **training-distribution scarcity of long sequences** — strengthens compaction-over-bigger-windows.

---

## RESIST (anti-overkill wins — explicitly do NOT build for v1)
- **Supervisor *chains* of N models** (Sierra 15+/Hippocratic 30+): enterprise-scale, contradicts single-agent-first, and no published stacking law proves clean compounding. One optional reviewer is the right dose.
- **Synthetic conversation/eval generation.** Verso's version is "freeze the *real* failures you already captured," not generate new ones.
- **An agentic-retrieval backend in §5.4.** Hebbia read raw **kept vector** for retrieval (*"classical hybrid search… and filtering"*); their "Full Attention" is answer *synthesis* over an already-scoped doc — which Verso already expresses as `fan_out` + `verify_grounding`. RRF/vector default holds. (Lock-defer only a feedback-biased-retrieval seam: `proof_count`/`access_count` boosts.)
- **Fine-tuning-specific eval tooling** (Braintrust: OSS-model use *"<5% and declining," "fine-tuning is not a viable standalone product"*). Keep the flywheel outcome-agnostic.
- **A non-i.i.d./sequential eval mode** (Yao's i.i.d. critique is real) — reserve the seam on `EvalRun`, don't build it for v1.

## Corrections to the harvest (minor)
- Thorsten Ball's agent core is **"less than 400 lines… most of which is boilerplate,"** not "~315 lines" (`03_teardowns` misquote).
- Do not cite the "Sierra τ-bench 0.61^8 ≈ 25%" figure (arithmetically wrong, ≈1.9%); use Hippocratic's verified `0.98^10 ≈ 82%` as the compounding-ceiling illustration (independently confirms §5.5 per-step-vs-end-to-end p50/p80 reporting).

---

*Net: the design is sound and stays simple. One code fix (cache_control) realizes a claim already made; six surgical PRD enhancements (recorded as §14) — two interface-reservations, three correctness sharpenings, one steelman hedge — earn their place; everything else is a confirm or an explicit resist. Next: write Phase-1 plans (memory + eval wedge) incorporating §14's Phase-1 items.*
