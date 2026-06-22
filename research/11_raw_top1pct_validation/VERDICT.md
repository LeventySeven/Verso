# Verso — Raw-Source Top-1% + Competitive Validation (Verdict)

**Provenance.** 37 parallel agents, ~2.96M tokens, 362 tool calls, reading the **raw** primaries (no digests): `guidesfm/BAD_GUIDE.md` (279KB), the `researchfms/core/*` transcripts + architecture maps (incl. the 2.99MB YC Root Access file, grep-bounded), and 27 raw `researchfms/teardowns/*` — each cross-checked against shipped `verso/` source. Per-unit artifacts: `methodology/` (10), `frameworks/` (20), `production/` (7). This pass exists because every prior Verso layer (incl. the Plan 22 GAP_REPORT) mined *digests* of the teardowns/transcripts; the user asked for the raw, with the top-1% founder/researcher methodology weighted first. 37/37 units returned, 0 failed.

---

## 1. Top-line verdict

**The full raw corpus independently validates the thesis: "just build agents, no overkill, don't force the graph."** This is not a sample anymore. 37 independent reads — methodology, competitive frameworks, *and* production agents — converge, with no shared bias. The ones that read as a *challenge* (Pydantic AI, LangGraph, Mastra, DSPy, Letta) each resolve to "that is exactly the complexity Verso correctly refuses, or the one structural property the seam must match without a graph."

- **No new primitive category.** Independently reproduces Plan 22's conclusion, this time from raw primaries. The 98 raw "steal" candidates collapse: most are already-shipped, already-deliberately-deferred (§13/§14), or already on the §14.15 RESIST list.
- **The genuine delta is small and verified:** ~4 recurring, source-verified-absent, on-thesis additive knobs (Tier 1, §5), a short Tier-2 tail, and a strengthened case for two items Verso already chose to defer (Tier 3).
- **The real risk is the opposite of overkill.** After 22 additive plans the failure mode to watch is "desiccated simplicity" (§14.2) — an API so minimal there's nothing to hold onto. Verso avoids it because the seam + the eval surface + `inspect()` are the things you hold onto. Leanness is intact (§7).

---

## 2. The methodology, raw (the #1 focus) — the top-1% consensus, quoted

Nearly every finding below was tagged **`verso-already-has`** by the extracting agent. That tagging *is* the result: Verso is a faithful implementation of what the best builders say, not an interpretation of it.

**The loop is not the moat.**
> "The agent core is a model, a loop and three tools in **~315 lines** of Go, and every hard, valuable thing lives elsewhere: editor integration, prompt craft, feedback timing, orchestration. Read it to **stop treating the agent loop as the moat**." — Thorsten Ball (Amp/Sourcegraph), *The Emperor Has No Clothes* (BAD_GUIDE L741).
Verso's `<200-line` loop (`core/loop.py` `_drive` ≈130 lines) is the literal embodiment.

**The harness is the moat.**
> "v0 took Claude Sonnet's **64.71% → 93.87%** with engineering, not model training… the compounding moat is the harness around the model." — Malte Ubl (Vercel CTO). And same-model-different-harness: "Opus 4.5 ran **50.2% → 55.4%** purely on context management and tool orchestration." "**The moat is the system, not the weights**… vaccinated against the bitter lesson." (BAD_GUIDE §Modern CTO L210-211, L381, §Research L636.)
Verso's context + evals + the seam *are* that harness; the wrapper test is in PRD §12.

**Don't force the graph / don't build multi-agents.**
> "Multi-agent default: share the full agent trace, not only the messages… parallel agents make conflicting implicit decisions that produce broken output." — Walden Yan (Cognition), *Don't Build Multi-Agents*. Anthropic's own orchestrator-workers number: "**90.2% improvement… ~15× more tokens**" — for one task class (breadth-first research), and "three factors explain 95% of variance: **token usage (80%)**, tool-call count, model choice." Claude Code "implements this as a single while-loop… **no state machine, no workflow graph**." (BAD_GUIDE L737-740; core/06 L825-832, L155-177.)

**Context is the product.**
> "**LLMs are pure functions**… the only thing that improves output quality is the quality of what you put in." "Keep context utilization **under 40%**." "/compact is trash — a summary over which you have no authorial control." — Dex Horthy (HumanLayer). "Performance **drops precipitously** as token length grows; the 10,000-token point has already degraded dramatically — curate your context." — Jeff Huber (Chroma). "The agent that wins is the one with the best **context assembly pipeline**." — Peter Yang. (YC Root Access L13914-14170; A16Z.)
Verso ships `ContextBundle` + `prune()` (observation-masking, never silent-drop) + RRF + the KV-cache-stable prefix.

**The verifier is the real engineering.**
> "A reliable **verifier** is the most crucial element in RL fine-tuning, **not the algorithm**." — Denny Zhou (DeepMind). "Whatever is solvable and easy to verify gets solved. **Build the verifier first**." — Jason Wei. "The #1 cause of failed AI products is no eval." — Hamel Husain. "**Evaluation before optimization**" is the universal ordering across all nine DLAI technical talks; "categorical labels beat numeric scores — LLMs hallucinate numbers." (BAD_GUIDE §Research L378/L578/L455; DLAI L5601, L5521.)
This is precisely Verso's wedge (`Eval.*`, `LLMJudge`, `TrajectoryCheck`, `from_trace`).

**Reliability beats capability.**
> "You'd rather have a less capable agent that works **95%** than a more capable one that works **70%**… production bar `>90%`… don't break the happy path." — Amjad Masad (Replit). The dominant failure mode every operator names is the spiral: "when an agent gets stuck it tends to spiral — tries the same approach, hallucinates progress." — Cursor. (A16Z/Stanford.)
Verso: `StopReason.STUCK` doom-loop detection + `pass^k` + the durable seam.

**Simplicity is the documented law, not a preference.**
> "**Do the simple thing that works.** Build the simplest agent possible, scale complexity when evals show meaningful returns." — Anthropic (DLAI L734). "**Skip the high-level SDKs** because model differences force your own abstraction; prefer explicit cache control; **reinforce the objective on every tool return** rather than once up front; isolate failures in throwaway sub-agents that report only outcomes." — Armin Ronacher (Flask), *Agent Design Is Still Hard* (BAD_GUIDE L282). "**Every abstraction is a liability**… ~99% of the value is in the RL'd model." — Gregor Zunic (browser-use).

**Taste is a trainable, nameable skill** (the meta-principle over the whole project).
> "You don't say 'I don't like it,' you name **which property is violated**." — Paul Graham. "Product sense becomes the only durable PM skill." — Shreyas Doshi. (BAD_GUIDE §Product L860-908.)

---

## 3. The one structural challenge worth taking seriously

Pydantic AI and LangGraph earn durability / HITL / resume **"for free" because every node is a persistence boundary**. The agent reading Pydantic AI said it plainly: Verso's tactical↔durable seam "must structurally deliver the same snapshot-per-step + idempotent resume **without the graph** to win the head-to-head."

**Verified: Verso does.** `core/loop.py:205` checkpoints each step; `resume_loop` rebuilds state and runs in a fresh process; `repair_history` repairs orphan tool-calls at the model-call boundary; HITL tools are idempotent-up-to-`ctx.hitl.request`; `history()`/`fork()` give time-travel. The seam delivers the node-boundary guarantee as a per-step checkpoint instead of as a graph. **This is the single property to never regress** — it is also exactly what wedge artifacts W1 (10 lines vs a 150-line `StateGraph`) and W2 (the one-flag diff) demonstrate. Keep an eval on it.

---

## 4. What NOT to copy — the overkill map (independent re-confirmation)

The 173-item overkill catalog compresses to a dozen themes, **every one already on Verso's NON-GOALS or §14.15 RESIST**:

| count | theme | named exhibits |
|---|---|---|
| 52 | graph / DAG / StateGraph DSL | Mastra (4570-line `workflow.ts`, 2 engines, 10-state enum), LangGraph Pregel, CrewAI Flow, LlamaIndex Workflow |
| 47 | orchestrator / actor / message-bus runtime | AutoGen (~9.5K LOC, in maintenance mode), SK/MAF actor pub-sub, Magentic ledger |
| 28 | heavy multi-agent / teams | Agno Team, CrewAI hierarchical, constellation/debate frameworks |
| 27 | config / CEL / state-machine DSL | SK Processes, Agno CEL workflows, MAF graph signature |
| 13 | planner component | SK Stepwise/Handlebars (**Microsoft itself deprecated these** for the native function-calling loop) |
| 13 | kernel / plugin registry | Semantic Kernel central registry |
| 13 | LLM-summarization compaction | Letta 2116-line summarizer + sleep-time agents, browser-use default summarize, Claude Code `/compact` |
| 13 | platform / hosted / SaaS | CrewAI Rails+Paragon, LangGraph Platform, Together serving fleet |
| 9 | learned / price router DSL | gateway routing strategies |
| 4 | code-as-action / sandbox-as-default | smolagents CodeAgent, Anthropic Code Execution |
| 3 | self-edit / graph / bi-temporal memory engine | Letta blocks, Graphiti communities |

Plus the unmatched tail: owning the vector-DB / reranker / fine-tune stack, A2A / MCP-first as the primary tool path, RL-grade reproducible eval environments, 12-strategy edit-match waterfalls + 21-class error hierarchies, the `10007` "effectively unbounded" recursion limit (Verso's STUCK detector is strictly safer — do not copy the unbounded default), a 9-migration Postgres saver as the default backend, the Batch API as a first-class path, per-request infra-routing flags. **The refusals are correct.** The competitors' bulk is graph + orchestrator + planner + platform; that is the structural opening Verso is built on.

---

## 5. The genuinely-fresh harvest (verified-absent, small, additive, byte-identical-when-unused — NOT new categories)

Each item below was checked against shipped source. None is a new pillar; all are knobs.

**Tier 1 — recurring across ≥2 independent units, source-verified absent, on-thesis:**
1. **`todo`/recited-plan builtin.** `tools/builtins.py` ships only `think` + `done`. A 3-status agent-owned list that re-injects every step and survives `prune()` is the single most-corroborated missing primitive (core/07 leaked prompts + Claude Code `TodoWrite` + Manus `todo.md` recitation). §14.4 already says `[adopt]` "ship a todo/echo builtin." Not shipped. *Cheapest real win on the board.*
2. **`inspect()` per-category token breakdown** `{instructions / tools / history / memory: tokens}` (Claude Agent SDK `getContextUsage`, Claude Code `systemPromptSections`). `inspect()` returns a flat render today. On-thesis because `inspect()` is *the* demo surface (§14.13 re-specs it as a data viewer).
3. **Stuck-detector enrichment.** `core/stuck.py` fires on `repeated_action` + `tool_errors` only. Add `monologue` (N assistant turns, zero tool calls) and `alternating` (A-B-A-B oscillation) — the two patterns OpenHands documents — plus AutoGen's hysteresis counter (no-progress → +1, progress → `max(0, n-1)`) for a sharper signal than a flat strike count.
4. **`ModelResponse.truncated` + IncompleteToolCall diagnostic.** `ModelResponse` carries `text/tool_calls/usage` only; adapters discard provider `finish_reason`. When `finish_reason=='length'` with unparseable tool args, emit "increase `max_tokens`" instead of burning a retry budget on a structural truncation (Pydantic AI). This was GAP #10; never shipped.

**Tier 2 — small, verified absent, on-thesis:**
5. **Tool-ACI batch** (GAP #22/23/28, all confirmed absent on `Tool`): per-parameter docstring→schema descriptions, plus optional `instructions` and `examples` fields. §14.6's ACI thesis ("argument extraction is the failure point") is the rationale. Ship as one "tool ergonomics" PR.
6. **Per-tool `validate()` pre-side-effect callback** (Parahelp: deterministic check *before* the side effect commits → cited 99% success on billing actions). Distinct from `idempotent`/`timeout`/permission; returns correct / escalate-to-ask / reject-with-feedback. Pairs with the 4-valued `ask`.
7. **Negative-constraints slot across compaction** (Supermemory: preserve "things forbidden or that already failed" as a first-class carried-forward field at compaction). On-thesis context-engineering.
8. **Deterministic sorted tool-result ordering** (Pydantic AI: run concurrent, record in call-index order) — makes `TrajectoryCheck` transcripts reproducible. On-thesis for the eval moat.
9. **Datadog tool-agnostic eval lens** — the one cross-cutting `steal-additive` on evals across two units: an eval mode that scores only the final result + tool effects and treats autonomous mid-trajectory recovery as success (don't assert *which* tool was called; tool-specific asserts become silent change-detectors when you refactor 5 tools into 3). A recipe + a lint, not a primitive. (Note: Verso already "defanged the judge" so it doesn't grade the CoT trace — git log — which is the same family.)

**Tier 3 — already deliberately deferred; evidence strengthened, note the trigger, don't act yet:**
- **Deferred tool-schema loading (`defer_loading`)** — §13 Resolved #7 defers this to Phase 3 ("the >20-tools problem doesn't exist for a solo dev writing 5–15 tools"). It is now the **single most-corroborated steal** (core/06 + core/12-13 + Claude Code), with hard numbers: **77K → 8.7K tokens (95% cut), Opus 4 accuracy 49% → 74%**. The defer is still right for the default user. The honest update: the gate is concrete — *the first time anyone wires >~20 tools or an MCP catalog into Verso, pull it forward.* It is additive and works for native `@tool` (not MCP-only), so it doesn't touch the non-goals.
- **Per-run USD budget guard → `StopReason.BUDGET`** (Mastra `CostGuard`, gateway cluster). Blocked on an absent layer: there is **no cost/pricing layer** (`Usage` has no `cost_usd`; `StopReason` has no `BUDGET`). §13/§14 put this at Phase 2. Ship a thin per-model price table + `cost_usd` first; the guard is ~5 lines after that.
- **Schema-versioned checkpoint guard** (OpenAI Agents SDK `RunState`, MAF signature hash, Mastra) — recurring across 3 frameworks; GAP backlog. Cheap; worth doing *before* the first breaking checkpoint change, not after.
- **Semantic response cache** (gateway cluster; reuse the existing `sqlitevec` store, opt-in behind `cache=`). Borderline — real cost lever, but cache-correctness is a footgun. Opt-in only, off by default, if at all.

**Refuse (independently re-confirmed overkill, listed so the refusal stays legible):** code-as-action / sandbox-as-default, DSPy optimizer, Letta self-editing memory + summarizer, LLM-summarization-as-default-compaction (Verso's `prune`-not-summarize is the vindicated minority call — OpenHands/browser-use pay for summarization Verso provably doesn't need), learned/price routers, graph/orchestrator/planner/kernel/actor-bus, A2A/MCP-first core, owning vector-DB/reranker/fine-tune.

---

## 6. One doc-truth note

`README.md` quickstart shows `result.cost_usd`, but `verso/types.py` `AgentResult`/`Usage` have **no cost field** — the cost/pricing layer is genuinely unshipped (deliberately, per §13). Either ship the thin price-table + `cost_usd` (which also unlocks Tier-3 budget guard) or correct the doc. Same class of doc-vs-code gap the Plan 22 report cleaned up; this one survived.

---

## 7. Leanness verdict (the brutal answer)

**Verso has not drifted into overkill.** Every one of the 22 plans' additions is additive and byte-identical-when-unused, and source confirms it: `stuck_thresholds=None` disables detection identically; `max_attempts=None` keeps the global path; `max_steps_policy="stop"` is the silent default; unused hooks are no-ops. The loop is ~130 lines where every branch earns its place (the vetoed-`done` re-drive, sibling-tool-call closing for well-formed checkpoints, per-tool retry budgets keyed on `idempotent`). The corpus's own best builders — Ball's 315-line core, Cognition's "don't build multi-agents," Anthropic's "scale complexity only when evals show returns," Ronacher's "skip the high-level SDKs" — are a near-verbatim chorus for exactly Verso's shape.

The discipline holds. The move is: **ship the Tier-1 four if and when dogfood asks for them** (the `todo` builtin is the one to do first, and is already `[adopt]` in the PRD), keep the Tier-3 triggers written down, and keep refusing the entire §4 catalog. The framework is on the right side of the wrapper test, and the raw corpus — not a summary of it — now says so.

---

## 8. Shipped this pass (TDD, all additive + byte-identical-when-unused; full suite 457 passed / 1 skipped / 0 fail)

- **Tier-1.1 — `todo` builtin** (`tools/builtins.py`): `think`/`done`'s sibling. A typed `list[TodoItem]` (`content` + `status: pending|in_progress|completed`) that renders a status-marked checklist (`[ ]`/`[~]`/`[x]`) and echoes it back. Opt-in tool; absent unless you pass it. Tests: `tests/test_builtins.py`.
- **Tier-1.3 — stuck `alternating` (period-2) detector** (`core/stuck.py`): catches the A-B-A-B doom-loop the period-1 detector missed (`StuckThresholds.alternating=3`, `0` disables; changing results = progress, never flagged). Byte-identical until a 2-cycle with stable results repeats 3×. Tests: `tests/test_stuck_detection.py`. **Dropped `monologue`** as genuine overkill: Verso's loop returns `END_TURN` on the first no-tool turn and the only re-drive path is already bounded by `max_verify_retries`, so a monologue doom-loop is structurally unreachable here.
- **Tier-1.4 — `ModelResponse.truncated` + `AgentResult.truncated`** (`model/base.py`, all 3 adapters, `types.py`, `core/loop.py`): the provider's max-tokens cut is no longer discarded (GAP #10). Anthropic `stop_reason=="max_tokens"`, OpenAI `finish_reason=="length"`, Gemini `MAX_TOKENS`; surfaced on the terminal `END_TURN`/grace-`MAX_STEPS` result so evals can assert `not truncated`. Defaults `False` everywhere. Tests: `tests/test_truncated.py`. *(Scoped to surfacing the signal; auto-recovery/re-drive deliberately NOT built.)*
- **Tier-1.2 — `inspect()` per-category token breakdown: NOT shipped because it already exists.** `ContextBundle.sections()` already returns `{instructions, tools, history: tokens}`, reachable via `agent.inspect(task).sections()`. Verified against source — this was the one over-flagged candidate.

**Not yet done (deliberate):** the Tier-2 tail (tool-ACI batch, per-tool `validate()`, negative-constraints slot, provider-native JSON-schema fast-path, deterministic tool-result ordering, Datadog tool-agnostic eval lens) and all Tier-3 deferred items. README/PRD status-line reconciliation for the three shipped primitives is pending.
