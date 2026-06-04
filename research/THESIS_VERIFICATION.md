# Verso — Thesis Verification (Step 1)

**Question:** Is the "keep AI agents simple, everything else is legacy in 1–2 years" thesis *true*?
**Method:** 3 independent layers, no single point of bias.
1. **Track B** — independent multi-agent web workflow: 1 fact-finder + 1 adversarial skeptic per claim (12 agents, 674K tokens, all "high" confidence, primary-source URLs, self-correcting).
2. **My own layer** — `WebSearch`/`WebFetch` spot-checks of the highest-stakes facts against primary sources (a *different* search backend than Track B).
3. **Track A** (`bad-research` full pipeline) — **could not complete**: its keyless search backend (ddgs/searxng) returned blocked/garbage pages in this sandbox (it scraped `google.com`, `speedtest`, EA forums). Honestly reported, not faked. Tracks B + my layer carried the verification.

Date: 2026-06-04. Verdict scale: TRUE / MOSTLY TRUE / MIXED / MOSTLY FALSE / FALSE / **OPINION** (not falsifiable) / **PREDICTION** (unprovable).

---

## Per-claim verdicts

| # | Claim | Type | Verdict |
|---|---|---|---|
| 1 | AI agent projects have a 1–2 year shelf life; stronger models + mature frameworks make today's workarounds legacy | mech=FACT, "1–2yr"=PREDICTION | **MIXED** — mechanism TRUE, the number is an unfalsifiable forecast |
| 2 | GPT-4 had 8,192 *output* tokens; modern models have ~128,000 output tokens | FACT | **MIXED** — right trend, imprecise numbers |
| 3 | Hand-built CoT pipelines obsoleted by reasoning models (now standard) | FACT + OPINION | **MOSTLY TRUE** as a trend; **MIXED** as literal "obsolete" |
| 4 | Anthropic only got native Structured Output in November; before that, prefilling | FACT | **MOSTLY TRUE** on the date (Nov **2025**); **MOSTLY FALSE** on "everything via prefilling" |
| 5 | 20-node LangGraph graphs are overkill; ReAct + good tooling (MCP) covers ~90% | OPINION | **Core TRUE**; "~90%" is **OPINION**; "graphs always overkill" is **MOSTLY FALSE** |
| 6 | LangChain is popular because first, not best; Pydantic-AI/Agno/ADK/Claude SDK/OpenCode SDK/Mastra are better; best products use plain Python + OpenAI SDK | FACT + OPINION | **MIXED** — frameworks real, "first not best" is OPINION, OpenCode SDK is a factual error |
| 7 | Keep it simple; you'll regret over-engineered code in 1–2 years | OPINION | **Vindicated as a default heuristic** by the two most authoritative sources |

---

### Claim 1 — "1–2 year shelf life" — MIXED (mechanism TRUE, number is a PREDICTION)
- **For:** The obsolescence mechanism is well-precedented on a ~1–2yr clock: JSON-coercion hacks → OpenAI Structured Outputs (~12 mo); manual CoT → reasoning models (~12–18 mo); naive small-context chunking → 1M-token windows (~12–24 mo). The underlying principle is Sutton's *Bitter Lesson*, explicitly applied to agents in rlancemartin's "Learning the Bitter Lesson" (Jul 30 2025).
- **Against:** "1–2 years" has **no defined metric** for "shelf life" or "most problems" → unfalsifiable as stated. Directly contradicted at the hard-problem level by **Karpathy's "decade of agents / march of nines"** (Oct 2025): core *reliability* takes ~10 years, not 1–2. And **durable architecture** (ReAct since 2022, RAG-as-grounding, evals/observability ~89% adoption, orchestration/memory) has survived 3+ model generations — the blanket "1–2yr legacy" wrongly sweeps these in.
- **Truth:** bimodal. *Tactical workarounds* churn on ~1–2 yr; *durable architecture* persists much longer.

### Claim 2 — token limits — MIXED (right arc, imprecise figures)
- **Correction (load-bearing):** GPT-4 at launch (Mar 14 2023) had an **8,192-token SHARED context window** (input+output combined), *not* a separate 8,192 output cap. (OpenAI's own docs list 8,192 as *both* context and max-output — so the number isn't "wrong," the *interpretation* is.) The first dedicated, smaller output cap was **GPT-4 Turbo's 4,096** (Nov 2023).
- **Correction:** "~128,000 output tokens" is true only for **select Anthropic models** (Opus 4.6/4.7/4.8; Claude 3.7 Sonnet via the `output-128k-2025-02-19` beta). The field broadly sits lower: **GPT-4o 16,384 · GPT-4.1 32,768 · o3/o4-mini 100,000 · Gemini 2.5 65,536 · Claude Sonnet 4.6 / Haiku 4.5 64,000.** 128K is the high end of a subset, not "modern models" generally.
- **For:** the *arc* is sound — output ceilings rose 4,096 → 16K–128K, so chunked-continuation / map-reduce workarounds are genuinely **less necessary**.
- **Against "legacy":** map-reduce still wins on cost/latency for huge corpora; reasoning models burn output budget on hidden tokens. "Less necessary," not "legacy."

### Claim 3 — reasoning models obsolete CoT — MOSTLY TRUE (trend) / MIXED (literal)
- **For:** Timeline TRUE (o1 Sep 2024, DeepSeek-R1 Jan 20 2025, Claude 3.7 extended thinking Feb 24 2025, Gemini 2.5 thinking Mar 2025, GPT-5 router default Aug 7 2025). OpenAI's own docs say to **avoid** "think step by step" on reasoning models ("unnecessary," "can sometimes hinder"). Wharton (Jun 8 2025): explicit CoT adds only +2.9–3.1% on reasoning models (−3.3% on one) vs +11.7–13.5% on older models.
- **Against "obsolete":** CoT **migrated, didn't vanish** — it's now RL-trained *inside* the model. It still helps non-reasoning models (still widely used for cost), and *structured* reasoning still matters in agent loops. "Reasoning is default **for hard tasks**" is the accurate framing (routine queries still route to cheap non-reasoning models).

### Claim 4 — Anthropic structured output — MOSTLY TRUE (date) / MOSTLY FALSE (mechanism)
- **Date:** "November" = **November 14, 2025** (public beta, header `structured-outputs-2025-11-13`); **GA Jan 29, 2026** (Haiku 4.5 Feb 4, 2026). The user left the year blank — it's **2025**. For comparison OpenAI shipped Structured Outputs **Aug 6, 2024** — ~15 months earlier.
- **"Everything via prefilling" = MOSTLY FALSE:** assistant-prefill (seed with `{`) was *one* real workaround, but **tool use / function calling was GA May 31, 2024** and was equally used to get schema-shaped JSON, as was plain prompting. None *guaranteed* schema conformance — that constrained-decoding guarantee is what's actually new in Nov 2025.

### Claim 5 — graphs overkill / ReAct+MCP covers 90% — Core TRUE, "90%" OPINION, anti-graph MOSTLY FALSE
- **Core (start simple) — strongly supported.** Anthropic *Building Effective Agents* (Dec 19 2024, verbatim): *"the most successful implementations weren't using complex frameworks… simple, composable patterns"*; *"start by using LLM APIs directly"*; frameworks *"obscure the underlying prompts and responses, making them harder to debug."*
- **"~90%" = OPINION / unsourced rhetoric.** No authoritative source quantifies it. The only hard "90%" runs the **other way**: Anthropic's **multi-agent system beat a single agent by +90.2%** on breadth-first research (at ~15× tokens). So a *simple* single agent is materially worse for an important class of tasks (but multi-agent is *not* for shared-context/most coding).
- **"Graphs always overkill" = MOSTLY FALSE.** LangGraph earns its keep for **durable execution / checkpoint-resume, human-in-the-loop approval, fault-tolerance, deterministic branching, time-travel debugging, long-running workflows** (AWS even published a LangGraph+DynamoDB durable-agent reference). Honest framing: *"don't reach for a 20-node graph by default,"* not *"graphs never help."*

### Claim 6 — LangChain "first not best" + alternatives — MIXED
- **"First not best" = OPINION.** LangChain (Oct 2022, Harrison Chase) was first, but its durable lead is **ecosystem-driven** (~138K stars, ~258M PyPI dl/30d, LangGraph + LangSmith + ~600 integrations), not pure first-mover inertia. LangChain itself conceded in its 1.0 post (Oct 22 2025) that early abstractions were *"too heavy."* So the *criticism* is real and even self-admitted, but "only because first" is reductive.
- **Alternatives — all real & correctly attributed:** Pydantic-AI (Pydantic team, type-safe, ~17.5K★), Agno (ex-Phidata, ~40.5K★), Google ADK (Apr 2025), Claude Agent SDK (ex-Claude Code SDK, Sep 29 2025), Mastra (ex-Gatsby team, TS, ~24.8K★).
- **Factual error:** **"OpenCode SDK (Python)" is a category error** — it's a **Stainless-generated HTTP client** (~230★) for the opencode coding-agent server, *not* a general agent-authoring framework. Per this repo's own rule ("an SDK that is just an HTTP client is not the product"), it doesn't belong in a list beside LangChain/Pydantic-AI.
- **"Best products use plain Python + OpenAI SDK" = OPINION** — sound default heuristic, but SDK-agnostic (same argument applies to the Anthropic SDK or raw HTTP); singling out the OpenAI SDK is arbitrary.

### Claim 7 — keep it simple — vindicated as a DEFAULT heuristic
- Both most-authoritative practitioner sources endorse it: Anthropic *Building Effective Agents* (*"finding the simplest solution possible, and only increasing complexity when needed"*) and Cognition's *Don't Build Multi-Agents* (Jun 12 2025, single-threaded control). Cognition's Apr 22 2026 follow-up *refined* (not reversed) this: "one writer, augmented by other agents." The instinct is mainstream frontier consensus.

---

## Meta-verdict

**The user's instinct is right; several specific facts are imprecise; the punchiest lines are opinion/prediction dressed as fact.**

- ✅ **"Keep it simple as the default" is not just defensible — it's the documented frontier consensus** (Anthropic, Cognition, the Bitter Lesson, the LangChain backlash, LangChain's own 1.0 retreat).
- ✅ **The obsolescence mechanism is real and well-precedented** — tactical workarounds (JSON hacks, manual CoT, small-context chunking) genuinely died on a ~1–2yr clock.
- ⚠️ **But "everything is legacy in 1–2 years" overreaches.** Durable architecture (ReAct, RAG-as-grounding, evals, orchestration, memory) persists across 3+ model generations; hard reliability is a "decade" problem (Karpathy). The clock applies to *workarounds*, not *architecture*.
- ⚠️ **The absolutes are opinion/prediction, not fact:** "~90% with a simple ReAct agent," "graphs are overkill," "LangChain only because first," "1–2 year shelf life." Each has a legitimate counter-case.
- ❌ **Two factual fixes:** GPT-4's 8,192 was a *shared context window*, not an output cap; the **OpenCode SDK is an HTTP client, not a framework**.

**Bottom line for building Verso:** build for the *durable* layer and stay ruthlessly simple in the *tactical* layer. The thesis is the right north star — just don't enshrine the disputable numbers as design law.
