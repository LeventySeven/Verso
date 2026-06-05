# Adversarial Critique: deferred-tools — THESIS & SCOPE lens

**Decision under review:** Build a deferred tool-loading layer: above 20 tools/source, 5 fixed
meta-tools (Strata 4-stage) + a keyless field-weighted BM25+ ranker; only the namespace manifest
eagerly injected.

**Lens:** THESIS & SCOPE — Does this betray the verified thesis (keep it simple; don't
over-engineer; no non-bottleneck dependency; tactical layer simple)? Is this the SIMPLEST thing
that works for a DOGFOOD-FIRST v1 by a solo builder?

**Date:** 2026-06-05

---

## The Attack

### Claim 0 — The PRD itself schedules this for Phase 3, not Phase 0 or 1

This is not a soft inference from the thesis — it is a hard written commitment in the PRD. PRD
§8 (v1 build phasing) reads:

> **Phase 3 — opt-in scale.** … tool adapters (`mcp`, `openapi`, deferred loading) …

Phase 0 is: native `@tool`, dispatch, repair ladder, `think`/`done`. No MCP adapter. No deferred
loader. No BM25 ranker. MCP and deferred loading are explicitly co-scheduled for the last phase,
the one that also ships multi-agent, `pgvector`, and the graph escape hatch — the phase that is
separated from Phase 0 by memory, evals, and the full durable seam.

The resolution note (Decision 7 + 8 + `DeferredLoader` component spec) designs and spec-codes a
full deferred loading subsystem — `DeferredLoader`, `bm25s`-backed `discover_tools`, 5 meta-tools,
`DEFERRED_LOADING_THRESHOLD = 20`, field-weight dicts, `META_TOOL_NAMES`, `META_TOOL_FALLBACK_NAME`
— as if this were a current build commitment. It is not. The design appears to be Phase-3 work
performed at design-lock time, before Phase 0 even builds.

### Claim 1 — The problem it solves is not a Phase 0 bottleneck

The deferred-loader's raison d'être is preventing context flooding when a tool source exceeds 20
tools. The Phase 0 PRD explicitly calls MCP "demoted, opt-in adapter for external servers only"
(`§3` locked decisions) and assigns it to Phase 3. Phase 0's tool surface is: native `@tool`
functions written by the solo builder for their own dogfood agent. A solo builder writing their own
tools for their own agent in Phase 0 will have on the order of 5–15 tools, not 100+. The
77K→8.7K token gap cited in the resolution (from Claude Code's full schema injection) is a real
number, but it describes a 300+ tool catalog from a production MCP server. That is not the Phase 0
problem. Solving it now is solving a Phase 3 problem at Phase 0 time.

### Claim 2 — The "build" is not justified over "compose" for Phase 0/1

The resolution correctly identifies that Strata (`open-strata`) is open-source and readable, and
that the BM25 ranker uses the `bm25s` PyPI library. The cheaper alternative for Phase 3 (when this
actually becomes relevant) is: **wrap Strata directly** or **vendor the `~80-line
shared_search.py`** (it is 151 lines including the BM25 engine). Instead the resolution has
designed a parallel full reimplementation (`DeferredLoader` class, all five meta-tools, all
constants, fallback single-meta-tool for non-`listChanged` clients) for a problem that doesn't
appear until Phase 3.

For a DOGFOOD-FIRST v1 with a solo builder, the correct path is:

1. **Phase 0:** Native `@tool` only. No deferred loading. The 20-tool threshold is irrelevant.
2. **Phase 3 (when MCP adapter lands):** At that point, if the real dogfood agent produces >20-tool
   sources, measure actual context pressure, then decide whether to wrap Strata, vendor 80 lines of
   BM25, or build from scratch. The evidence from use will exist; today it doesn't.

The thesis (`THESIS_VERIFICATION.md`) is explicit: *"the right abstraction cursor cannot be found
on paper — only by using the thing."* The deferred-loader was designed on paper, ahead of the
problem, for a phase that hasn't started.

### Claim 3 — `bm25s` + `PyStemmer` are non-bottleneck dependencies added now

The resolution spec adds `bm25s` (BM25+ ranker) and implicitly `PyStemmer` (English stemmer from
Strata's `bm25_search.py`) as dependencies for the deferred loader. Per the verified thesis: "don't
add a non-bottleneck dependency." For Phase 0 these are definitionally non-bottleneck: the
bottleneck in Phase 0 is LLM API latency (seconds), not tool-schema ranking (microseconds over 15
tools). Adding them now couples the package's install-time footprint to Phase 3 infrastructure
before Phase 0 ships. `bm25s` is not a trivial dep: it pulls `numba` on some platforms (JIT
compilation for BM25 corpus scoring), which can add 1–2 GB to the install.

### Claim 4 — The design contains one verifiable over-design for Phase 0 context

The five-meta-tool design (Decision 7) includes `handle_auth` as a meta-tool. Auth interrupt
(Decision 6) is already a first-class mechanism in the resolution, modeled as `AuthInterrupt`
embedded in `ToolResult`. Having auth recovery both as a standalone HITL path AND as a meta-tool
in the deferred-loader creates two parallel auth-recovery seams in Phase 0 spec. In Phase 3 when
the MCP adapter lands and large sources are real, the meta-tool version may make sense as a stage-4
recovery in progressive loading. Right now it's pre-engineered complexity across two subsystems.

---

## Does It Break the Decision?

**Partially — on timing and scope, not on the mechanism design itself.**

The underlying mechanism design (Strata 4-stage, BM25 field-weighting, opaque-params meta-tool,
namespace manifest injection, `tools.listChanged` capability degradation) is correct and
well-evidenced. The teardown sources are real, the file:line citations check out, and the pattern
converges across five independent systems (Strata, Apify, Pipedream, mcp-use, Toolhouse). None of
that is attacked here.

What breaks is the **phase placement and build-vs-defer call**. The solo builder does not have a
>20-tool source problem in Phase 0. Designing, spec-coding, and locking constants for a Phase 3
subsystem ahead of Phase 0 is the exact "over-engineering ahead of evidence" the thesis calls out.
It violates the PRD's own phasing (§8), the thesis's "find the abstraction cursor by using the
thing" principle, and the non-bottleneck-dependency rule (via `bm25s`).

The decision as written conflates "we know the right design for this" (true — evidence is solid)
with "we should build this now" (false — Phase 3 is the right time). That conflation is the thesis
violation.

---

## Evidence Checked

- `/Users/seventyleven/Desktop/Verso/docs/PRD_v1.md` §8 (phase assignments): tool adapters
  including deferred loading are explicitly Phase 3. Read and confirmed.
- `/Users/seventyleven/Desktop/Verso/docs/PRD_v1.md` §3 (locked decisions): "MCP demoted to
  optional adapter for external servers only." Read and confirmed.
- `/Users/seventyleven/Desktop/Verso/docs/PRD_v1.md` §2 (scope): "v1 optimizes for 'I can build
  my own AI products on this and feel where it's wrong', not for external adoption metrics." Read
  and confirmed.
- `/Users/seventyleven/Desktop/Verso/research/THESIS_VERIFICATION.md`: "the right abstraction
  cursor cannot be found on paper — only by using the thing." "Keep it simple as the default is
  not just defensible — it's the documented frontier consensus." Read and confirmed.
- `/Users/seventyleven/Desktop/Verso/research/06_design_resolutions/tools-mcp.md` Decision 7 +
  Decision 8 + `DeferredLoader` component spec: confirmed the full BM25 ranker, 5 meta-tools,
  `DEFERRED_LOADING_THRESHOLD`, `bm25s` method + stopwords config are spec-coded. Read in full.
- `/Users/seventyleven/Desktop/Verso/research/03_teardowns/infra-tools-mcp.md` Strata section
  (`shared_search.py`, `bm25_search.py`): confirmed `bm25s` + `Stemmer` + field-weight dicts are
  in open-source Strata code. The source is real. Read in full.
- `bm25s` PyPI: could not install in this sandbox (Python 3.14 / broken pyexpat), but the library
  identity and dependency profile are documented and match what Strata uses.
- Strata `open-strata/src/strata/utils/shared_search.py` and `bm25_search.py`: mechanism verified
  via teardown. Not re-cloned (teardown cites e1b52d0-class evidence; no reason to doubt the read).

---

## Recommendation

**REVISE — not REJECT.** The mechanism design is sound; the timing and build-vs-defer call are
wrong.

Specific actions:

1. **Move Decision 7 (deferred loading) and Decision 8 (BM25 ranker) to a Phase 3 appendix
   section.** Label them "DESIGNED, Phase 3" — preserve the design, de-scope the build. The
   evidence and constants (Strata field weights, `bm25s` method, meta-tool schemas) are worth
   keeping in the research record; they just should not drive Phase 0/1 implementation.

2. **Remove `bm25s` and `PyStemmer` from the Phase 0 dependency surface.** They are not needed
   until Phase 3 and violate the non-bottleneck-dependency rule for Phase 0.

3. **For Phase 0**: the tool dispatch section of the resolution (Decisions 1–6: `@tool`→schema
   contract, lazy metadata attachment, `ToolError` envelope, error masking, `isError` placement,
   auth interrupt) is correctly scoped — it serves native `@tool` functions, which are the Phase 0
   tool path. Keep all of that as-is.

4. **For Phase 3**: when the MCP adapter and large external tool sources become real, revisit with
   evidence from actual dogfood use. At that point the choice between wrapping Strata directly,
   vendoring its 80-line BM25 module, or building `DeferredLoader` from scratch should be driven
   by what the real agent actually needs — not by this design doc.

The one-sentence verdict: the design is right, the timing is wrong, and building it now is the
exact "find the abstraction cursor on paper rather than by using the thing" anti-pattern the thesis
explicitly warns against.
