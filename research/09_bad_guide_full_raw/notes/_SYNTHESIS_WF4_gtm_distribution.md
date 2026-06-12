# SYNTHESIS — WF4: Go-to-Market, Distribution, Launch, Cold-Start (§12)

**Theme:** GTM / distribution loops / launch-in-hours / cold-start / becoming-hunted-leverage · THEME KEY `gtm_distribution`
**synthesis_path:** `research/09_bad_guide_full_raw/notes/_SYNTHESIS_WF4_gtm_distribution.md`
**Pass:** WF4 (transcript-hunt re-pass over the founder/product/GTM video+podcast cluster). Supersedes nothing; **layers on top of** `_SYNTHESIS_WF3_gtm_distribution.md` (read first — its deltas are NOT re-listed here).

**Sources read in full (16 GTM-cluster notes):** Cold Start Problem · Come-for-the-Tool · Growth Loops · Four Fits · Braindump on Viral Loops · Momentum-is-the-Moat · First 1,000 Users · Superhuman Acquisition Loops · Invisible Asymptotes · Growth (Schultz) · How-to-Launch-on-HN · The Best Way to Launch (Mañalac) · How to Get Your First Users (Gupta) · Adjacent Users (Kaba) · Lovable $200M / Elena Verna · Building Lovable / Anton Osika · Inside Bolt / Eric Simons · Rise of Cursor / Truell · Nikita Bier viral playbook. Plus VERSO-section scans of the 3 bootstrapping notes (Levels, Dinh, Chen-growth-hacker).
**Unreachable:** 0 hard-unreachable. **Every primary transcript in this cluster is paywalled or video-only** (Lenny's ×6, YC Library ×3, YouTube ×3) — all notes are `read_partial` reconstructed from ≥2 independent secondaries (PodPulse, Recall, Yahoo Finance direct quotes, Andrew Chen canonical blog proxies, First Round Review full transcript for Lerner). Verbatim quotes flagged in-note where multi-source-confirmed. Coverage honest; reconstruction quality high.

---

## CROSS-SOURCE PICTURE

WF4 re-reads essentially the **same distribution cluster WF3 already consolidated**, so the headline is a *negative* one and it is load-bearing: **the GTM shape does not move.** Cursor (Truell: "lived like monks… spread by word of mouth," $0→$300M ARR, no sales org), Bolt (Simons: single tweet, zero-signup, $0→$4M in 30 days, zero paid), and Lovable (Osika: GPT-Engineer 52K stars → waitlist → "mainly posting what we shipped") are now **three more maximal-strength public proofs** of the already-locked thesis: DX-led organic, no sales motion, no paid, build-in-public, Show HN / OSS-star cold-start, superconsumer-first. None of these is a new claim; together they harden it past the point where it should ever be re-litigated. Treat as `confirm`.

What is genuinely **new in WF4** is concentrated in two notes WF3 did **not** read — **Kaba (Adjacent Users)** and **Bier (viral playbook)** — plus a handful of **sharper external-language artifacts** the three AI-coding founders supply that the prior "don't-finalize-copy" rule (WF3 delta #2, Lerner) explicitly invited someone to A/B. The four real increments:

1. **The adjacent-user diagnostic is the missing *operational* half of the atomic-network finding (Kaba).** WF3 named the atomic network (5 vocal leads) and the stage (Stage 1). Kaba adds the instrument that tells you *when the network is leaking*: **cohort decay** — when conversion from install→first-successful-eval declines week-over-week, adjacent users (ML researchers; pre-wall seniors) are arriving and silently churning, and the correct response is a **product investigation, not more marketing**. And TikTok's move — explicitly courting "users who were not successful on Instagram" — is the sharpest available framing of the struggling-moment persona: **name the failure the engineer escaped** (the LangChain graph wall, the un-debuggable CrewAI run) the way TikTok named what Instagram denied. This is a §12 increment, not founder-OS, because it changes *who the positioning addresses*.

2. **"If there's any uncertainty, the product isn't working" sets the Stage-1 *exit bar* at unanimity (Bier).** WF3's atomic network said "5 leads generating + sharing eval results." Bier sharpens the success *test*: not "5 people tried it" but "5 people are **unambiguously, vocally** recommending it." Ambiguity = failure signal. This is the binary-signal discipline applied to Verso's exit criterion — a real sharpen on the established cold-start gate.

3. **Three concrete external-language candidates the AI-coding founders hand us — to A/B, per WF3's Lerner rule, not to adopt blind.** (a) Osika's **scarcity-shift headline**: "the bottleneck moved from *who can build* to *who knows what to build*" → Verso's form: **"The agent loop is solved. The harness is not."** — more concrete than the internal word "harness." (b) Truell's **"own the surface"** (fork-vs-extension): the plain-language anti-graph analogy — building *on* LangChain inherits its abstraction and its ceiling, exactly as a VS Code extension couldn't ship Cursor's features; the clean loop *is* the fork. (c) Osika's **"unsticking" / "we don't re-prompt the agent, we recover the run"** as the user-visible name for the checkpoint/resume seam. All three are §12/§7 copy *candidates*, gated behind the language-market-fit validation WF3 already mandated.

4. **Path-dependency makes early-adopter *selection* an architecture decision, not a sales decision (Gupta).** "The product you build with your first 100 users encodes their preferences into the architecture." WF3 named *who* the hard side is; Gupta adds *why the choice is load-bearing*: if Verso's first 5 leads are reliability-heavy enterprise AI teams, the harness evolves that way — so the atomic-network roster is a **deliberate moat/scope decision** feeding §1/§2, with a stated early-adopter selection thesis ("lead engineers with a real agent in prod deciding how to scale it," **not** "anyone who installs").

Two further notes (Verna; Simons) supply **sharpens that mostly reinforce WF3** and are reported as such, plus one **RESIST** clarification: Verna's "90-day PMF reset" gives the WF3 "non-goals-are-evidence-updatable" finding an explicit *cadence* (quarterly persona stress-test) — useful as founder-OS tempo, **must not** become a PRD instruction to churn positioning. Simons's "WebContainers + Claude-3.5 convergence" reframes the launch-now argument as **schlep-infra + model-unlock timing** (distinct from WF3's wave-timing/Law-of-Shitty-Clickthroughs) — a `confirm`-sharpen on §1 timing.

---

## DEDUP — already established (do NOT re-list) + already in WF3 (do NOT re-list)

Reported only as bare `confirm`, no new action, because WF4 adds no load-bearing increment over the prior consolidation:

- **DX-led organic / no sales / no paid / build-in-public / Show-HN / OSS-star cold-start / superconsumer-first** — now additionally proved by Cursor, Bolt, Lovable at maximal strength. Established CONSENSUS + WF3. `confirm`.
- **Harness-is-the-moat / schlep-as-moat / eval-corpus flywheel as the *output*/retention layer** — Bolt (WebContainer schlep → economics competitors can't match) and Truell (custom models as *discovered* necessity) are clean analogs; established. `confirm`.
- **Stage-1 / atomic-network = ~5 vocal production leads** — WF3 delta. Cold-Start re-read confirms; Kaba/Bier *sharpen the instrumentation + exit bar* (see deltas), don't re-state the network. `confirm` on the network itself.
- **Loop-not-funnel / Category-2 structural-dependency / K≈0.3–0.5 / sub-loop inventory** — WF3 deltas (Reforge, Chen-viral, Dixon). `confirm`.
- **Language-market-fit BEFORE finalizing taglines; "harness" is the internal word, A/B problem-language; 5-second test** — WF3 delta #2 (Lerner, highest single-source). WF4's three copy candidates **feed this rule**, they don't replace it. `confirm` on the rule.
- **Legibility ceiling / non-adopter "what do you HATE" / Prime-move (restructure don't explain) / two new counter-positioning mechanisms (Wei proof-of-work, Balfour Tugboat)** — WF3 §1 deltas. `confirm`.
- **Shareability + surprise + feeling wedge constraint; tweetable-without-context; garage-door-up + opinionated-init good-friction** — WF3 §7 deltas. Levels/Kim re-confirm. `confirm`.
- **Each-primitive-its-own-Show-HN; one-channel discipline; wave-timing; organic-as-signal-not-budget; borrowed-ecosystem entry; starter-pack alliances; Verso-Fellow free tier** — WF3 §12/founder-OS deltas. Levels/Dinh/Chen-growth-hacker re-confirm verbatim. `confirm`.

---

## DELTAS (WF4 — new vs BOTH the established list AND WF3; or a distinct sharpen)

### §12 — positioning / GTM

**D1. [adopt-now · NEW] Adjacent-user diagnostic + cohort-decay canary as the Stage-1 GTM health instrument.** *(Kaba, Adjacent Users)*
Track **conversion from install → first successful eval, by weekly cohort**, from day one. **Cohort-over-cohort decay is the canary** that adjacent users (ML researchers who never owned prod ops; seniors who haven't hit the reliability wall) are arriving via referral and silently churning — and the response is a **product investigation, not more distribution**. This is the operational half WF3's atomic-network finding lacks: it tells you when the network is leaking and why. Feeds §12 (metrics) — a *diagnostic*, not a growth program (stays Stage-1-appropriate).

**D2. [adopt-now · NEW] Name the failure the engineer escaped — TikTok-courts-Instagram's-rejects as the positioning move.** *(Kaba; pairs with Wei non-adopter, WF3 #11)*
The most natural adjacent entry point is **the engineer who *tried* LangChain/CrewAI and churned at the graph wall / the un-inspectable run** — they have intent, they tried, they bounced. Positioning should explicitly **name that failure mode** (the way TikTok offered success to "users not successful on Instagram"), not address a generic "AI agent dev." This sharpens the established struggling-moment persona from a market insight into a *copy directive*: lead with the escaped pain, in their words.

**D3. [sharpen · NEW vocab] "The agent loop is solved. The harness is not." — scarcity-shift headline candidate for §1/§12.** *(Osika; gated by Lerner language-market-fit, WF3 #2)*
Osika's bottleneck-has-moved framing ("who can build" → "who knows what to build") translated to Verso is a **more concrete external one-liner than the internal word "harness."** Add to the §12 A/B headline pool (against problem-language variants). **Do NOT finalize as the tagline** — it is a candidate to validate, per the standing rule. `sharpen` not `adopt` because it must survive the 5-second test first.

**D4. [sharpen · NEW analogy] "Own the surface" / fork-vs-extension as the plain-language anti-graph argument.** *(Truell, Rise of Cursor)*
Cursor *forked* VS Code because the extension API permanently capped the product; Verso building *on* LangChain/LlamaIndex inherits that framework's abstraction **and its ceiling** — the clean loop *is* the fork. This is a second, more concrete counter-positioning analogy alongside WF3's native/skeuomorphic angle (Dixon). Use in pitches; same "different tradeoff, not better-than" register (never "unlike LangChain").

### §7 — demo-able wedge / product taste

**D5. [adopt-now · NEW] Design the *first-failure* experience (inspect/error/traceback) with pixel-level intensity — the dev-tool analogue of Bier's 3-second rule.** *(Bier)*
"Consumer products live and die in the pixels" → **dev tools live and die in the first error message.** The magic moment isn't only the happy-path 3-line diff; it is the first time `inspect()` is called on a *real failure*, the first traceback, the first recovery. If that output is verbose/confusing/non-actionable on first use, the marginal user (Schultz) churns exactly as a consumer who didn't see value in 3 seconds. **Spend disproportionate design time on the failure surface, not the happy path.** Distinct from WF3's shareability/surprise constraints (those are about the *demo*; this is about the *first bad day*).

**D6. [sharpen · NEW framing] "We don't re-prompt the agent — we recover the run." — "unsticking" as the user-visible name for the checkpoint/resume seam.** *(Osika)*
Lovable's differentiator was codifying AI self-recovery vs competitors' re-prompt-on-every-failure. Verso's one-flag durable + checkpoint/resume + HITL has the same user-visible win: **recover the run, don't restart the prompt.** A demo-able framing for the seam (pairs with the one-flag-durable-diff artifact). Copy candidate, gated by language-market-fit.

### §1 / §2 — moat / scope (new mechanism only)

**D7. [adopt-now · NEW] Early-adopter *selection* is an architecture decision: state a deliberate selection thesis.** *(Gupta, First Users — path dependency)*
"The product you build with your first 100 users encodes their preferences into the architecture." The atomic-network roster therefore steers what the harness *becomes* — choosing reliability-heavy enterprise leads vs solo builders is a **moat/scope decision (§1/§2), not a sales decision (§12).** Add an explicit early-adopter selection thesis: target **"lead engineers with a real agent in production deciding how to scale it,"** refuse "anyone who installs." Sharpens WF3's hard-side persona by making the *consequence* (path-dependent architecture) explicit.

**D8. [confirm-sharpen] Launch-now timing = schlep-infra + model-unlock convergence.** *(Simons, Bolt)*
Bolt waited 7 years with WebContainers until Claude-3.5 could use them, then moved fast. Verso's analogue: **the models are now capable enough that the harness layer is the bottleneck** — "we're at the WebContainers+Claude-3.5 convergence moment for agent reliability." A distinct timing argument from WF3's wave-timing (Dinh) / Law-of-Shitty-Clickthroughs (Chen): those are about *channel decay*; this is about *enabling-technology readiness*. Sharpen on §1 timing.

### Founder-OS (lands in `research/04_bad_guide_full`, NOT the PRD)

**D9. [founder-OS · NEW] Stage-1 exit bar = unanimity, not headcount.** *(Bier: "if there's any uncertainty, it's not working")*
The exit criterion from the atomic-network stage is **unambiguous, vocal enthusiasm from all ~5 leads** — ambiguity is a failure signal, not a "needs more time" signal. Operating discipline for reading the cold-start signal honestly; pairs with WF3's stage diagnostic.

**D10. [founder-OS · NEW tempo] 90-day PMF reset: a quarterly persona stress-test, not a positioning churn.** *(Verna, Lovable $200M)*
"PMF is a perishable good" → run a **quarterly** "does this still win the structurally-aware senior?" review. This gives WF3's "non-goals are evidence-updatable" an explicit *cadence*. Founder-OS operating rhythm only — see RESIST #2; it must **not** become a PRD instruction to re-open positioning every quarter.

---

## RESIST (no-overkill / no-bullshit — keep OUT of PRD product scope)

1. **B2C viral mechanics are a non-domain for Verso — do not import them (hard boundary).** *(Bier, explicit CONTRADICTS; echoes WF3 RESIST #1 on Kim)* No K-factor engineering, no contact-graph, no 3-second-onboarding transplant, no referral bonuses. There is no viral loop in a `pip install`. "Organic" for Verso = structural-dependency Category-2 + social capital, **not** Bier/consumer virality. Adopt only the *transferable* abstractions (sequential validation, binary signal, first-failure design); reject the mechanics.

2. **Do NOT bake the 90-day PMF reset into the PRD as a process.** *(Verna)* Quarterly persona stress-testing is founder-OS tempo. The PRD is stable model-agnostic product truth; an instruction to churn positioning every quarter would corrupt that. Keep it in `04_bad_guide_full`.

3. **Do NOT promote any WF4 copy candidate to settled tagline.** D3 ("loop is solved, harness is not"), D4 ("own the surface"), D6 ("recover the run") are **candidates for the language-market-fit A/B** (WF3 #2), not finalized §12 copy. Resist finalizing before the 5-second test.

4. **Do NOT treat the AI-coding-founder ARR curves as Verso's expectation.** Cursor/Bolt/Lovable hit $0→$Xm in weeks because they are **B2C-ish, instant-gratification, zero-friction consumer-adjacent** products. Verso is B2D, slow-clock (weeks–months), deliberate adoption, K<1. Their *GTM posture* (organic, build-in-public, product-as-demo) transfers; their *velocity* does not. No launch-day-spike dependency.

5. **Do NOT spin up the cohort-decay/adjacent-user work as a growth-analytics program.** *(Kaba)* D1 is a *single diagnostic metric* (install→first-eval by cohort) read as a canary, appropriate at Stage 1. It is **not** a mandate for a growth-instrumentation stack, A/B platform, or a growth team — that would be the Stage-3 wrong-stage trap (WF3 RESIST #3).

6. **Do NOT let founder-OS execution apparatus leak into §1/§2/§5/§6/§7.** D9 (unanimity bar), D10 (90-day tempo), and all launch-tactics belong in the founder-OS playbook, not the product spec — same firewall WF3 RESIST #2 draws.

---

## NET FOR THE PRD

§12 stays a **thin pointer** (as designed). The PRD-affecting WF4 increments are small and surgical:
- **§12:** add the **adjacent-user/cohort-decay canary** (D1) and the **"name the escaped failure"** persona-copy directive (D2); drop the three copy candidates (D3/D4/D6) into the **language-market-fit A/B pool**, not the body.
- **§7:** add **first-failure-experience design** (D5) as a taste constraint beside the shareability constraints.
- **§1/§2:** add the **early-adopter selection thesis** (D7, path-dependent architecture) and the **convergence-timing** sharpen (D8).
- **`04_bad_guide_full`:** the unanimity exit bar (D9) and 90-day tempo (D10).
Everything else in this cluster is `confirm` over the established consensus + WF3.
