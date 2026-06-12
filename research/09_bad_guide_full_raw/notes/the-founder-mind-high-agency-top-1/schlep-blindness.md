# Schlep Blindness
**Source:** https://paulgraham.com/schlep.html
**Author:** Paul Graham
**Format:** Essay (short, ~900 words)
**Section:** The Founder Mind (high-agency, top-1%)

---

## Faithful Digest

### Core Thesis
There are great startup ideas lying unexploited in plain sight. The reason we don't see them is not that they are hard to find — it is that our unconscious mind hides them from us because of their psychological cost. Graham calls this "schlep blindness": the bias that prevents us from even SEEING ideas that involve tedious, painful, or intimidating work.

"Schlep" (Yiddish, now general American English): a tedious, unpleasant task. Not merely difficult — specifically the kind of work that is unglamorous, socially costly, or psychologically aversive.

### The Core Mechanism
The unconscious won't let you see ideas that involve painful schleps. This is not a conscious decision. Most people don't consciously decide to avoid intimidating work — their unconscious decides for them, and the idea never surfaces to conscious consideration at all. The analogy: most people don't consciously decide not to be in Olympic-athlete shape. Their unconscious decides for them.

Key distinction: the bias is **pre-deliberative**. It is not that you see the idea, consider the schlep, and flinch. It is that the idea never comes to mind.

### The Stripe Example (Primary Case Study)
For over a decade, every hacker who had ever had to process payments online knew how painful the experience was. Thousands of people knew about this problem. And yet when they started startups, they built recipe sites and local event aggregators.

The reason: "their unconscious mind shrank from the complications involved." The complications were real:
- Making deals with banks (how do you even do that?)
- Moving money → fraud risk, server security
- Regulatory compliance layers

"You'd have to make deals with banks. How do you do that?"

Graham's observation: no one who built a recipe site asked "should we fix payments or build a recipe site?" and chose the recipe site. They never considered the payments problem at all, because their unconscious filtered it out before it reached deliberation.

The deeper point is that the recipe-site founders were not stupid — they were subject to an unconscious bias that made the best idea invisible.

### The Scariness Premium
Ambitious ideas that involve large schleps have a compounding advantage:
1. Their intrinsic value (fixing important, broken things)
2. They are undervalued among founders — less competition because the psychological cost filters out most people

"If you pick an ambitious idea, you'll have less competition, because everyone else will have been frightened off by the challenges involved."

This is not merely that hard things have less competition (which is obvious). It is that the schlep creates an **illegibility** that removes the idea from the competitive consideration set entirely. Founders are not choosing Stripe vs. recipe-site; they are only ever choosing among recipe-sites, because Stripe never appears on the list.

### The Ignorance-as-Antidote Paradox
The most effective antidote to schlep blindness may be ignorance. If founders knew the full magnitude of the obstacles before starting, they might never start. Young founders in particular make two mistakes that cancel out: they don't know how much they can grow, and they don't know how much they'll need to grow. Older founders only make the first mistake.

This creates a counter-intuitive principle: deliberately NOT doing due diligence on the full schlep scope can be adaptive. But this is fragile — it depends on the founder growing with the problem, which cannot be foreseen.

### The Practical Antidote (for Knowable Schleps)
For ideas whose schlep is visible, Graham's technique: change the frame of the question.

Instead of: "What problem should I solve?"
Ask: "What problem do I WISH SOMEONE ELSE WOULD SOLVE FOR ME?"

The shift from agency (what should I build?) to need (what do I need?) bypasses the unconscious aversion. The payments problem would have been obvious to any pre-Stripe founder who had tried to accept payments online, if they had asked themselves "what do I most hate about building the web stuff I'm building?"

### The Moat Corollary
Graham makes the moat point explicitly: the schlep IS the moat. Companies that do the painful work no one else will do earn a competitive position that is self-protecting, because the same psychological mechanism that prevented competitors from seeing the idea will continue to prevent them from responding to it. "A company is defined by the schleps it will undertake."

---

## VERSO RELEVANCE

### §1 — The Bet / Moat / Defensibility

**[SHARPENS] The harness IS the schlep — and the schlep IS the moat.**
Context engineering, eval authoring, the tactical-to-durable seam, HITL integration — these are unglamorous. They are not publishable research. They are not demo-able to VCs in 2 minutes. They are exactly the category of work that the conventional AI engineer's unconscious filters out: "I just want to write the clever code that calls the model and handles tool dispatch." The harness is the schlep that everyone needed but no one wanted to think about building.

This is a structural claim about defensibility that goes beyond "harness-is-the-moat": the harness moat is self-reinforcing because the psychological mechanism that prevented LangChain from building it (they built a framework instead, which is the glamorous part) will continue to prevent them from building it. Copying the harness requires embracing the schlep, which is exactly what LangChain's culture and incentives are misaligned to do.

*Adopt-now:* Add a "schlep-as-moat" argument to §1. The counter-positioning is not just about LangChain's incentives to preserve its framework tier — it is also about the psychological aversion to doing the harness work that makes it hard to copy even for a motivated copycat.

**[NEW-IDEA] The reliability work is the canonical schlep in the AI engineering space.**
"Making it work 61% of the time is impressive; making it work 99% of the time is the thing no one wants to build." Evals, invariants, context budget management, systematic retry logic — these are the exact psychological aversion that the ecosystem has been avoiding. The "measured harness lift" data (Sierra 61%/35%, Glean 0.9^10 march-of-nines) is what happens when someone actually does the schlep. Frame this explicitly: Verso exists because we are doing the schlep the ecosystem is avoiding.

*Adopt-now:* The reliability angle in §7/§12 should lead with "this is the work everyone knows they need and everyone avoids." The demo-able wedge is not just showing the 3-line diff — it is showing that someone actually did the unglamorous work.

### §2 — Non-Goals / Principled Refusal

**[SHARPENS] Non-goals as schlep-avoidance refusal.**
Verso's principled refusals (no forced graph, no visual workflow builder, no LangSmith-style platform play) are partly about counter-positioning and partly about NOT doing the schlep of the wrong things. But the framing can be sharpened: we refuse the glamorous-but-wrong schleps (graph DSL, visual editor, hosted observability) in order to do the unglamorous-but-right schleps (eval infrastructure, context engineering primitives, checkpoint/resume).

*Sharpen:* When articulating non-goals, frame them as "we are not doing the schlep of X because it is the wrong schlep" — this makes the refusal principled rather than merely reactive.

### §7 / §12 — Demo-able Wedge + Positioning / GTM

**[NEW-IDEA] The "what do you wish someone else would solve?" frame is a positioning diagnostic for Verso.**
Apply Graham's reframe directly: what does the structurally-aware AI engineer most hate about their current agent work that they would desperately wish someone else had solved?
- "I hate that my agent fails after 9 steps and I can't restart from checkpoint without rewriting everything."
- "I hate that I don't know if my context is actually what the model is seeing."
- "I hate that evals are treated as a separate product I have to pay for."

These are the exact Verso product surfaces. The GTM insight: Show HN / X posts should be framed as "here is the thing you've been wishing someone would build" — not "here is a new framework." The difference is schlep-acknowledgment vs. feature-announcement.

*Adopt-now:* Draft Show HN opening as: "You've been dealing with [specific aversion] for months. We did the boring work to fix it."

**[CONFIRMS] The "anti-framework" counter-position is a schlep-acknowledgment.**
Anthropic's "use the APIs directly" / Chase's "we traded power for ease of use" / Ronacher's "build your own abstraction" — all three are telling engineers to do the schlep themselves. Verso's positioning is: we did the schlep FOR you at the harness layer, so you don't have to do the schlep OR accept the framework tax. This is a third option the anti-framework camp does not articulate.

*Confirm:* Existing counter-position is correct; add "we did the schlep" framing to make it actionable rather than purely theoretical.

### Founder-OS Layer

**[NEW-IDEA] The ignorance-as-antidote principle as a decision-filter for early scoping.**
Graham's observation that young founders make two canceling mistakes (don't know how much they can grow; don't know how much they'll need to) applies directly to the Verso harness scope decision. The risk of knowing too much: you scope the harness too conservatively ("we can't build a full eval infrastructure in 3 months, so let's not include it"). The risk of not knowing: you underscope and miss the seam.

Practical application: when deciding what to include in the harness scope, distrust the "realistic" assessment that is really schlep-aversion in disguise.

*Lock-defer:* This is a useful self-check but doesn't need to be in the PRD. File in founder-OS notes.

**[SHARPENS] "A company is defined by the schleps it will undertake."**
This is a formulation worth internalizing verbatim as a Verso operating principle. It implies that Verso's identity is defined by which unglamorous work it is committed to doing: eval infrastructure, context engineering, checkpoint/resume seam. The company's competitive position is the list of schleps it will not flinch from. This should be stated explicitly in the internal operating manual.

*Adopt-now:* Encode as an operating principle: "Verso is defined by the schleps we commit to. The list of schleps we will undertake is the list of things competitors will avoid."

---

## Verdict Summary

| Finding | Verdict |
|---|---|
| Harness-as-schlep / schlep-as-moat structural argument | Adopt-now |
| Reliability work = canonical ecosystem schlep | Adopt-now |
| Non-goals as "wrong schlep" refusal framing | Sharpen |
| "What do you wish someone else would solve?" as Show HN/X frame | Adopt-now |
| "Anti-framework" = schlep-acknowledgment; Verso = did-the-schlep | Confirm |
| Ignorance-as-antidote as scope-decision filter | Lock-defer |
| "Company defined by schleps it will undertake" as operating principle | Adopt-now |
