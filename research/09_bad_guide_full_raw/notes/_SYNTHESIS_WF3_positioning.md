# SYNTHESIS — WF3: Positioning, Category, Counter-Position, Persona (§12, with §1/§2/§7 spillover)

**Theme:** Positioning / GTM / product-taste / founder-OS, mapped to PRD §1 (bet/moat), §2 (non-goals), §7+§12 (demo-able wedge + positioning), and the founder-OS index (`research/04_bad_guide_full`).
**Sources read in full:** 39 reader notes across product-taste-the-cpo-half, design-ux-taste-great-vs-slop, the-yc-a16z-game, b2b-go-to-market-founder-led-sales, distribution-growth-b2c, the-founder-mind, leverage-becoming-hunted.
**Date:** 2026-06-12

---

## 0. The cross-source picture (what this batch actually changes)

The prior passes settled the *claim* layer: harness-is-the-moat is consensus, ban Better-Trap language, name a category + POV, the anti-framework triumvirate, switching-costs-at-the-seam, the demo-able wedge, the eval-corpus flywheel, persona = structurally-aware senior/AI engineer, DX-led organic GTM. This batch does **not** re-litigate any of that. It moves the work forward on four axes:

1. **The external word is unvalidated.** The single most load-bearing NEW finding (Lerner, *Finding Language/Market Fit*) is that **"harness" is Verso's *internal* category word and may not be the *external* resonant word.** Prior passes assumed the category name and the GTM headline are the same artifact. They are not. The category name shapes the roadmap (correct: "harness"); the GTM headline must be discovered by interviewing the persona in *their* language about *what broke* — not asserted. This is a process gap, not a copy gap, and it is the highest-leverage delta in the batch.

2. **Non-goals are evidence-updatable, not identity.** PG's *Right Kind of Stubborn* contradicts the natural drift: §2 non-goals are **lower-level decisions** (rational-today, should update on evidence), NOT top-level commitments. Treating "no graph / no visual builder / no hosted observability" as identity is the *obstinacy* failure mode. The top-level commitment is "make tactical→durable cost-zero"; the non-goals serve it and must yield if evidence says so. This reframes the entire §2 register.

3. **Three genuinely-new counter-position angles** that sharpen §1 beyond "we don't force the graph": the **legibility ceiling** (Wei — LangChain's scale is its asymptote *for engineers who need to see what's happening*), the **schlep-as-moat** (PG — the harness is the unglamorous work the ecosystem's psychology filters out, and that filter protects it even from motivated copycats), and **feature-blackmail immunity** (Traynor — incumbents with big install bases cannot refuse enterprise feature-bloat; a small team can).

4. **A taste/design invariant layer for §7** that prior passes did not have: **frequency×novelty** (Rauno), **aesthetic integrity = function-appearance coherence** (Apple HIG), **"ask to save only when necessary" = auto-checkpoint** (HIG), **implicit input** (Rauno), and the **Einstein/Grossmann + neti-neti irreducibility test** (McCormick) for deciding whether any claim is moat-layer or table-stakes.

Everything else in the batch resolves to **confirm** or **sharpen** of already-established positions, OR is GTM-execution / fundraising / founder-OS apparatus that must be kept OUT of the PRD product scope (see §3 Resist).

---

## 1. DELTAS — genuinely new or contradicting (deduped, with source + verbatim)

### A. POSITIONING / §12

**[A1] "Harness" is the internal word; the external word is unvalidated and likely problem-language, not category-language.**
*Lerner, Finding Language/Market Fit:* "Your messaging must 'look like food' to their lizard brain within seconds, or they bounce." Mindstone: "organize notes and remember content" beat "accelerate learning" **30% vs 3%** because it used the customer's words about what they wanted to do, not the founder's frame about what the product achieves. → The persona's vocabulary is "my agent broke in production," "I can't debug what happened," "I had to rewrite everything when requirements changed," "the context window filled up and it just stopped" — NOT "harness." **Recommendation: SHARPEN §12** — keep "harness" as the roadmap-shaping category word internally; run 10-15 JTBD decision-journey interviews with engineers who adopted *any* agent framework in the last 6 months and A/B test problem-language headlines against "harness." Do not assume the category word is the headline.

**[A2] The "legibility ceiling" — LangChain's scale is its asymptote for engineers who need to see what's happening.**
*Wei, Invisible Asymptotes:* a diseconomy-of-scale ceiling (Facebook's graph became its own constraint). LangChain analog: the bigger the configuration surface and ecosystem, the more opaque the product becomes to inspect/debug/customize for the structurally-aware engineer. New, specific counter-position sub-point not in prior PRD language. **Recommendation: ADOPT-NOW §1/§12** — add "legibility ceiling" as a named counter-position angle: incumbents get *less* legible as they scale; Verso's inspect()/in-process model gets legibility as a structural property. Pair with "don't explain the aversion, restructure it" (Wei's Prime lesson) — the one-flag durable diff removes the friction rather than arguing about it.

**[A3] Neti-neti + Einstein/Grossmann as the irreducibility stress-test for every positioning claim.**
*McCormick, Most Human Wins:* "I am not a computer, because I can use a computer" / "Einstein commoditized Grossmann… he used Grossmann's output as his input, while he himself provided the spark that could not be reduced." → Every Verso claim must be classed: is it the **Grossmann layer** (execution scaffolding AI/simpler tools will commoditize — the graph DSL, the orchestration) or the **Einstein layer** (irreducible judgment — *which* invariants to enforce, *when* to promote to durable, *what* context to preserve)? Only the Einstein layer is a moat. Neti-neti also gives an elegant non-goal frame: "the harness is what remains when you strip away the framework, the runtime, and the orchestration graph." **Recommendation: ADOPT-NOW §12 (test) + §1** — use as an internal QA filter; test neti-neti framing in launch copy. Tag the risk: keep it concrete, not mystical.

**[A4] "Tool, not app" / "avocado slicer" / "Verso is the kitchen, not the recipe."**
*Ink & Switch, Malleable Software:* "Many applications are avocado slicers" (bundled single-use-case gadgets) vs. knives (general tools); "bringing AI coding tools into today's software ecosystem is like bringing a talented sous chef to a food court." → Sharper vocabulary for both the non-goal ("we are not an avocado slicer" = no EmailAgent/SlackAgent/RAGAgent feature-bundles) and the defensibility argument against "LLMs will auto-generate frameworks" ("Verso is the kitchen — AI generates the loop body, the harness is the environment that makes generated code reliable"). **Recommendation: SHARPEN §1/§2/§12** — adopt "tool-shaped vs app-shaped" as a counter-position axis that needs no mention of LangChain; "kitchen not recipe" strengthens the moat-vs-codegen rebuttal.

**[A5] "Bit-rotting sophistication" — the precise rebuttal to "isn't this too simple?"**
*PG, Earnestness:* "Naive optimism can compensate for the bit rot that rapid change causes in established beliefs." → The sophisticated LangChain user's "but what about complex multi-step orchestration?" objection is calibrated against a *pre-Claude-3.5 / pre-better-models* baseline. That calibration is bit-rotting. Verso's "the loop is ~10 lines" reads as naive only to someone over-indexed on the old model landscape. **Recommendation: ADOPT-NOW §12** — "bit-rotting sophistication" is the named handling for the "too simple?" objection in Show HN / X replies. (Pairs with the established "decade not year" honesty register.)

**[A6] "Floors in the building" + "your competitor is doing nothing" — the cold-start category frame.**
*Saarinen (Linear PMF):* the incumbent "is like the floors in the building — you don't think about the floors, you just walk on them." *Christensen (JTBD/SNHU):* the real competitor was **inaction**, not a named rival. → Verso's actual competitor is not LangChain — it is the engineer's own hand-rolled `while True:` loop they keep meaning to fix. The category to name is the *unnamed* space between prototype and production-reliable agent that practitioners already live in. (Reinforced by PG *Founder Mode*: "no books specifically about founder mode" → naming the unnamed thing practitioners already do is itself a positioning move.) **Recommendation: ADOPT-NOW §12** — frame GTM copy as "the upgrade path from the working prototype you've been putting off," not "better than framework X." The struggling-moment is the first prod failure / first 2am page.

**[A7] "Specificity" + "surprise" as the two pass/fail tests for positioning and demo.**
*Perell, Ultimate Guide to Writing Online:* "Surprise signals when someone's mental model of the world has changed" + the Specificity criterion ("could two different products satisfy this description? if yes, too generic"). *Kao (spiky POV):* "eyes light up and they want to hear more." → Two concrete, falsifiable QA tests. Positioning test: could two products satisfy the sentence? ("better reliability" fails; "one flag, no graph, no rewrite, ephemeral→durable" passes). Demo test: does it produce *skepticism-then-confirmation* ("wait — I never rewrite to go durable? that can't be right") rather than "that's clean"? **Recommendation: ADOPT-NOW §7/§12** — apply both as literal acceptance criteria for positioning drafts and the wedge demo.

### B. MOAT / §1

**[B1] Non-goals are lower-level decisions that update on evidence — NOT identity. (CONTRADICTS the natural drift.)**
*PG, Right Kind of Stubborn:* persistent = stubborn on the goal, flexible on means; obstinate = attached to first ideas, driven by ego. Top-level (the goal) may be irrational/loved; lower-level (how) must be rational and yield to evidence. → §2 non-goals ("no forced graph," "no visual builder," "no hosted observability") are **rational-today conclusions serving the top-level goal (tactical→durable cost-zero), not commitments to defend for their own sake.** The obstinacy failure mode is becoming attached to the non-goals *because they are yours*. **Recommendation: ADOPT-NOW §2** — frame each non-goal as "current rational conclusion + the evidence that would change it," not as identity. This is the single most important §2 reframe in the batch and it cuts against the seductive "principled refusal = sacred" reading.

**[B2] Schlep-as-moat: the harness is self-protecting because the psychology that hid it from competitors keeps hiding it.**
*PG, Schlep Blindness:* "A company is defined by the schleps it will undertake" / the unconscious "shrank from the complications." → Context engineering, eval authoring, the durable seam, HITL are unglamorous, non-publishable schleps. The same psychological filter that made LangChain build the *glamorous* part (the framework) keeps it from embracing the harness work even when motivated. This is defensibility *beyond* incentive-misalignment: it's psychological-aversion-as-moat. **Recommendation: ADOPT-NOW §1** — add "schlep-as-moat" alongside Helmer counter-position and switching-costs. The reliability work is the canonical ecosystem schlep; "we did the boring work" is the wedge frame.

**[B3] Mental-model capture as a distinct moat layer ("design for someone" → irrational loyalty).**
*Saarinen:* "High quality builds irrational loyalty where users won't leave" + "It's impossible to design something really good for everyone." → Linear's "cycles" became how ICs *think about work*, not just track it. Verso's opinionated seam (one flag, not a config matrix) should become how AI engineers *think about reliability* — the switching cost is then abandoning a mental model, not just migrating an API. Distinct from the established API/corpus switching costs. **Recommendation: SHARPEN §1** — name "mental-model capture" as a moat layer; opinionated constraints (the refusal to add escape hatches) are the *mechanism*, not a limitation.

**[B4] Feature-blackmail immunity — incumbents structurally cannot refuse; a small team can.**
*Traynor, Product Strategy Means Saying No:* the "retention argument" / feature blackmail ("a customer will leave if we don't build this"); incumbents with large install bases get blackmailed into coherence-diluting features. *Growth+Sales (a16z):* "adapting to the growth+sales era is near impossible for the top-down sales incumbents." → "We are small enough to refuse" is a structural counter-position asset. **Recommendation: ADOPT-NOW §1** — add feature-blackmail immunity to the counter-position; "feature repository vs. product" (Traynor) is the negative contrast (don't name LangChain; let the category speak).

**[B5] Cold-start stage correction: the eval-corpus flywheel is a Stage-3 framing; Verso is at Stage 1. (Sequencing contradiction.)**
*Chen, Cold Start Problem:* network effects have 5 stages; running wrong-stage tactics is the sophisticated-founder trap. The flywheel is *Escape Velocity* (Stage 3). Before it activates, Verso must solve cold-start: the **atomic network** = the first ~3-5 structurally-aware leads running Verso in production AND sharing eval results publicly; the **hard side** = the lead engineer evaluating a harness for their *second/third* production agent. "Come for the tool (3-line diff), stay for the harness (corpus)" is the tipping-point strategy. **Recommendation: SHARPEN §1** — present the flywheel correctly as the *later* compounding asset; do not let §1 imply the moat is live at launch. The load-bearing moat at launch is the *seam switching cost*, not the flywheel (Chen confirms: network effects are not bulletproof — Skype→Slack).

### C. PRODUCT TASTE / DESIGN — §7

**[C1] Frequency × Novelty as the primary taste filter for every output surface. (New invariant.)**
*Rauno, Invisible Details:* high-frequency, low-novelty interactions must NOT carry animation/ceremony; "I removed motion from core interactions and suddenly felt like I was moving much faster." → `inspect()`, CLI output, streaming, progress indicators: the test is "how does this feel after 200 invocations *today*?" Anything satisfying on first use that turns sluggish on the 50th fails. **Recommendation: ADOPT-NOW §7** — make frequency×novelty the stated taste filter for all Verso output surfaces. Genuinely new; prior passes had "invariants-as-taste" but not this filter.

**[C2] Aesthetic integrity = function-appearance coherence (not "looks good"). (Sharpens the taste definition.)**
*Apple HIG:* "aesthetic integrity… is a measure of how well the appearance of the app integrates with its function." → A progress bar that adds richness without communicating actionable state has *poor* aesthetic integrity; a plain timestamped log line that says exactly what the agent did has *excellent* aesthetic integrity. **Recommendation: SHARPEN §7** — adopt "function-appearance coherence" as Verso's working definition of taste.

**[C3] "Ask to save only when necessary" = auto-checkpoint design principle. (New, concrete.)**
*Apple HIG (1987):* "ask people to save only when necessary." → The harness should checkpoint silently and surface the checkpoint only when the decision is genuinely consequential (before a destructive action / before crossing the HITL seam). "Configure checkpointing in advance" is the anti-pattern. **Recommendation: ADOPT-NOW §7** (with §5/§6 implementation implication) — a specific UX principle for checkpoint/resume that prior passes didn't state.

**[C4] Implicit input — "the mother of all inputs is no input at all." (New framing for context-engineering.)**
*Rauno:* a harness that infers the right context window / checkpoint granularity / eval threshold from usage, without explicit per-call config, is the "magic." → Frames context-engineering as Verso's attempt at implicit input. **Recommendation: ADOPT-NOW §7/§1** — framing device for the context-engineering narrative. (Tag the risk: "infer, don't configure" must not collide with the "no magic box / explain it without AI" register — implicit input must stay inspectable.)

**[C5] inspect() is a *data viewer*, not a debugger — with a concrete feature spec. (Sharpens inspect().)**
*Husain, Field Guide:* "Teams with thoughtfully designed viewers iterate 10x faster"; spec = all context in one place, one-click feedback, open-ended annotation, keyboard shortcuts, fast filter/sort. *Appleton (Squish/Structure):* compositionality / step-level observable I/O. *HIG:* direct manipulation (inspect() should trend toward interactive state, not read-only). → inspect() is the surface through which product intuition about the agent compounds; build it to the viewer spec. **Recommendation: SHARPEN §7** — adopt the viewer spec as inspect()'s implicit feature spec; frame as in-place toolchain (no cliff to a LangSmith equivalent).

**[C6] Spell-check-sized + "no Magic AI input." (Sharpens primitive scoping + a §2 non-goal.)**
*Appleton:* "most language model implementations should be 'spell-check sized'… do one specific thing well"; the generic "Magic AI" input "has no affordances!" *Wattenberger:* "good tools make it clear how they should be used… and how they should not be." → Each Verso primitive must be describable in one sentence; Verso offers no "magic" do-everything surface — every interaction has affordances. **Recommendation: SHARPEN §7 + §2** — "spell-check sized" as scoping heuristic; "no Magic AI input surfaces / explicit affordances everywhere" as a §2 non-goal with citable language. ("Simultaneously incredibly dumb and incredibly capable" is the cleaner market-education line than "hallucination.")

### D. FRAMING / RHETORIC (positioning copy, §12) — adopt as register, not product scope

**[D1] "What becomes possible if you discard X?" as the counter-position rhetorical frame.**
*PG, How to Do Great Work:* "What are people in your field religious about… What becomes possible if you discard it?" → The religious attachment is "agent frameworks need a graph/DAG." Frame the counter-position as discovery ("we asked what becomes possible if you discard the graph requirement"), not comparison. **Recommendation: ADOPT-NOW §12 (copy).**

**[D2] Tradeoff-description language, never "unlike X." (Sharpens the Better-Trap ban.)**
*How to Launch a Dev Tool on HN:* HN's fraud-detector punishes superlatives and "unlike X"; "modest language is stronger." *Kao:* competitor-relative language signals *borrowed conviction*. → Convert all "unlike LangChain" → "we chose not to force the graph because…". **Recommendation: SHARPEN §12** — audit positioning language for "unlike X" / superlatives; replace with tradeoff descriptions. (This operationalizes the already-banned Better-Trap.)

**[D3] Output-language not input-language; "don't call your product a framework."**
*patio11, Don't Call Yourself a Programmer:* lead with outcomes, not category. → "Verso is a Python agent framework" describes the artifact (input); lead with the outcome ("the reason your agents don't fail silently in production"); the category label belongs in the technical detail. **Recommendation: SHARPEN §12** — audit every positioning statement for input-language vs outcome-language.

---

## 2. FOUNDER-OS — lands in `research/04_bad_guide_full`, NOT the PRD

These are operating principles for the founder/maintainer. They are real and high-value but must not leak into the PRD's product sections.

- **Persistence self-check at the wall:** "does the evidence still support the goal, or only my pride?" Separate the goal-level claim from the lower-level claim; update lower-level without asking permission from ego (PG, *Stubborn*).
- **Founder-mode gaslighting diagnostic:** resistance to "add a node editor / no-code layer / broader abstraction" is *correct detection*, not stubbornness — advisors pattern-match LangChain-mode templates (PG, *Founder Mode*). Distinguish **technical** pushback (evidence → update) from **social** pushback (fashion-enforcement → confirm) (PG, *Think for Yourself*).
- **Schlep as operating identity:** "Verso is defined by the schleps we commit to" (PG, *Schlep Blindness*).
- **Code + media = multiplicative permissionless leverage:** every non-trivial design decision yields two artifacts — a commit AND a thread explaining the *judgment* (Naval). Judgment is the scarce resource to protect; high bar for what gets a post.
- **Earnest + formidable as the dual Show-HN signal**; "interest in the problem for its own sake" as persona filter; OSS infra is earnestness-compatible (PG, *Earnestness*).
- **PMF instrument (Superhuman):** Q1 "how would you feel if you could no longer use Verso?", target = activated users (shipped ≥1 agent), 40% threshold, the *only* KR until crossed; "politely pass over" the non-disappointed (vibe-coders / ML researchers).
- **Cold-start operating order:** personal network → community (B2B first-10 pattern); Collison Installation (zero friction from "I'm curious" → "let me pull up your repo now"); first cohort = free + feedback, not commercial pricing; hand-curate first ~50 by taste (Figma pattern); "do things that don't scale."
- **Diagnose your network-effect stage before choosing tactics; wrong-stage tactics are the sophisticated trap** (Chen).
- **Spiky-POV X cadence:** opinionated, debate-inviting claims (not neutral benchmark posts); cadence for Grossmann-layer notes, no-deadline for Einstein-layer essays; Public→Private bridge (X acquires, owned changelog/email retains); Personal Monopoly = the specific intersection, posted as the founder, tightly coupled to the brand early.
- **Fundraising mechanics (16 Questions / Your Pitch Deck Isn't Enough / a16z Speedrun):** raise on narrative momentum (post-Show HN) not burn; milestone-alignment; tweener-trap; SCQA pitch front-loading the 0.9^10 complication; the standalone investment-memo / "why Verso" champion artifact; the specific unfair-advantage sentence ("we run this on our own production agents — no other framework builder has the loop closed"). **All of this is founder-OS, not PRD.**
- **"Tweener trap" applied to positioning** is the one fundraising idea that touches §12: don't make category claims the product can't survive scrutiny on; positioning should lead the product by one step, not three (16 Questions). Keep this as a discipline note, not new product scope.

---

## 3. RESIST — keep OUT of the PRD product scope (no-overkill / no-bullshit gate)

1. **All GTM-execution apparatus.** PMF survey design, viral sub-loop inventory (README badges, PyPI trending, error-message attribution), Show-HN 7-step template + reply sheet + priming list, cold-start staging, evangelist activation, K-factor math, channel-mix ratios, "do things that don't scale" sessions. These belong in a GTM runbook / founder-OS index — **not** §1/§2/§7/§12. The PRD describes the product; it does not contain the launch checklist.
2. **Pricing/packaging mechanics.** "Charge more" / mild-friction pricing / freemium-as-channel-model-fit / $500-per-seat → $100M math / rabbit-deer ARPA tiering. Real, but commercial-model material, not product-spec. (The *one* legitimate product-spec spillover: the free→paid path must be self-discoverable without a sales call — i.e., the one-flag durable upgrade is discoverable — which is already the wedge.)
3. **Fundraising tactics.** Memo structure, valuation/round-size signaling, stage-matching investors, secondary-sale signal. Founder-OS only.
4. **"Squish-Structure / Goldilocks zone" as category language — LOCK-DEFER.** Powerful vocabulary (Appleton) but risks sounding imprecise next to the established crisp counter-position; evaluate only in a dedicated category-design sprint, do not adopt into PRD now.
5. **Neti-neti / Einstein-Grossmann mysticism creep.** Adopt the *test* (moat-layer vs table-stakes) and optionally the concrete neti-neti non-goal line; resist letting the meditation/aphorism framing into the PRD register, which must stay intellectually-honest and concrete.
6. **"Company Brain" / org-durable-context-layer downstream TAM (YC RFS).** Genuine Series-A narrative, but a second-order use case — do not let it widen §2 scope or dilute the persona lock now.
7. **The temptation to treat non-goals as sacred.** Per [B1]: resist framing §2 as identity/principle-for-its-own-sake. Non-goals serve the goal and update on evidence.
8. **Persona widening.** JTBD, Linear depth-not-width, "design for someone," and the superlinear independent-mindedness analysis all *converge* on the existing persona lock (structurally-aware senior / making-mode engineer / "interest in the problem for its own sake"). Resist any source's pull toward the ML-researcher or vibe-coder; the convergence is a CONFIRM, not a reason to broaden.

---

## 4. One-line disposition table

| # | Finding | Source | PRD | Disposition |
|---|---|---|---|---|
| A1 | "Harness" is internal word; validate external word via JTBD/A-B | Lerner | §12 | sharpen |
| A2 | Legibility ceiling (incumbent scale = its asymptote) | Wei | §1/§12 | adopt-now |
| A3 | Neti-neti + Einstein/Grossmann irreducibility test | McCormick | §1/§12 | adopt-now (test) |
| A4 | Tool-not-app / avocado-slicer / kitchen-not-recipe | Ink&Switch | §1/§2/§12 | sharpen |
| A5 | "Bit-rotting sophistication" rebuts "too simple?" | PG Earnestness | §12 | adopt-now |
| A6 | "Floors in the building" / competitor = inaction | Saarinen/Christensen | §12 | adopt-now |
| A7 | Specificity test + surprise/skepticism-then-confirmation test | Perell/Kao | §7/§12 | adopt-now |
| B1 | Non-goals = evidence-updatable lower-level, NOT identity | PG Stubborn | §2 | adopt-now (contradicts drift) |
| B2 | Schlep-as-moat (psychological filter protects the harness) | PG Schlep | §1 | adopt-now |
| B3 | Mental-model capture as a moat layer | Saarinen | §1 | sharpen |
| B4 | Feature-blackmail immunity / feature-repo vs product | Traynor | §1 | adopt-now |
| B5 | Cold-start: flywheel is Stage-3; Verso is Stage-1; seam = launch moat | Chen | §1 | sharpen |
| C1 | Frequency×novelty = primary output-surface taste filter | Rauno | §7 | adopt-now |
| C2 | Aesthetic integrity = function-appearance coherence | Apple HIG | §7 | sharpen |
| C3 | "Ask to save only when necessary" = auto-checkpoint | Apple HIG | §7 | adopt-now |
| C4 | Implicit input = context-engineering magic (stay inspectable) | Rauno | §7/§1 | adopt-now |
| C5 | inspect() = data viewer (concrete spec), step-level I/O | Husain/Appleton/HIG | §7 | sharpen |
| C6 | Spell-check-sized + no Magic AI input | Appleton/Wattenberger | §7/§2 | sharpen |
| D1 | "What becomes possible if you discard X?" frame | PG Great Work | §12 | adopt-now (copy) |
| D2 | Tradeoff-description, never "unlike X" | HN/Kao | §12 | sharpen |
| D3 | Output-language not input-language | patio11 | §12 | sharpen |

---

## 5. Net for the PRD author (the 8 that actually move §1/§2/§7/§12)

1. **§12 process:** separate the category word ("harness," internal, roadmap-shaping) from the external headline (discover by JTBD interviews in problem-language; A/B it). [A1]
2. **§2 register:** rewrite non-goals as evidence-updatable rational conclusions, not identity/sacred refusals. [B1]
3. **§1 counter-position, add three angles:** legibility ceiling [A2], schlep-as-moat [B2], feature-blackmail immunity [B4]; plus name mental-model capture as a moat layer [B3] and present the flywheel as Stage-3 with the seam as the launch moat [B5].
4. **§7 taste invariants, add:** frequency×novelty filter [C1], aesthetic integrity = function-appearance coherence [C2], auto-checkpoint / "save only when necessary" [C3], implicit-input-but-inspectable [C4]; sharpen inspect() to the data-viewer spec [C5] and "spell-check sized / no Magic AI input" [C6].
5. **§12 copy register:** "what becomes possible if you discard the graph?" [D1]; tradeoff-not-"unlike-X" [D2]; outcome-not-artifact language [D3]; "bit-rotting sophistication" as the "too simple?" handler [A5]; "floors in the building / competitor = your own procrastination" as the cold-start frame [A6].
6. **§7/§12 acceptance tests:** Specificity ("could two products satisfy this?") and Surprise/skepticism-then-confirmation as literal pass/fail gates for positioning drafts and the wedge demo. [A7]
7. **§1/§2/§12 vocabulary:** "tool-shaped vs app-shaped" / "kitchen not recipe" / "we are not an avocado slicer." [A4]
8. **Internal QA filter:** the Einstein/Grossmann test on every claim — Grossmann-layer = table stakes, Einstein-layer = moat. [A3]

Everything else CONFIRMS prior passes (harness-is-moat consensus, ban Better-Trap, persona lock, DX-led organic, demo-able wedge, eval-corpus flywheel, switching-costs-at-the-seam, intellectual-honesty register, OSS/Show-HN/X channel) or is founder-OS/GTM-execution that must stay out of the PRD (§3 Resist).
