# Invisible Asymptotes

**Source:** Eugene Wei · Essay · https://www.eugenewei.com/blog/2018/5/21/invisible-asymptotes  
**Date read:** 2026-06-12  
**Strength rating:** STRONG  
**Section:** Distribution & Growth (B2C + launch-in-hours)

---

## I. FAITHFUL DIGEST OF THE ARGUMENT

### The Core Concept

Wei coins "invisible asymptote" to mean "a ceiling that our growth curve would bump its head against if we continued down our current path." The invisibility is the point: companies can feel momentum, see growth, run all normal metrics — and still be hurtling toward a wall that doesn't show up in any dashboard until it's too late to course-correct. The insight is that most growth curves are shaped not by demand for what you do, but by aversion to something you haven't yet removed.

He frames this with a Sun Tzu epigraph: "If you know your enemies and know yourself, you will not be imperiled in a hundred battles." The enemy here is the invisible ceiling, not a competitor.

### Amazon: The Canonical Case Study

Wei was on Amazon's strategic planning team. The task was to identify the biggest obstacle to Amazon e-commerce growth. They ran two simultaneous research methods:
1. **Post-purchase surveys** asking buyers: "Why didn't you purchase more often?"
2. **Third-party market research** with non-customers asking: "Why don't you shop at Amazon?"

Both converged on a single factor, "without ambiguity": shipping fees.

The verbatim finding: "People don't just hate paying for shipping, they hate it to literally an irrational degree." The rational math — that Amazon's prices more than offset shipping costs — was irrelevant. The emotional aversion was the wall. Customers knew the math; they still hated the fee. Explaining the math didn't solve it.

The response was not iterative optimization. Bezos skipped testing and committed to Amazon Prime: customers pre-pay for shipping annually, Amazon absorbs the cost on individual orders, and the demand curve shift — in Wei's telling — was "stunning and game-changing." Prime transformed a per-transaction friction into a sunk cost, changing the psychological accounting entirely.

The follow-on insight: Prime built a moat because Amazon's logistics scale and customer concentration made the same move prohibitively expensive for competitors. The asymptote fix itself became a 7-Powers source.

### The Method: Ask Non-Customers What They Dislike

Wei's recommended approach to finding asymptotes:

1. **Ask customers what they dislike** (not what they want). Customers are "divinely discontent" — they can articulate what stops them better than they can articulate what they want next.
2. **Analyze non-adopters**, not just funnel drop-offs. The people who never converted tell you more about your ceiling than the people who almost converted.
3. **Ask: "Why doesn't everyone use your product?"** The answer defines your actual TAM boundary. Most TAM analysis is top-down (global book market, etc.); this method is bottom-up and locates the friction that collapses the market.
4. **Blend intuition with data** rather than relying on product genius alone. Pattern recognition is backward-looking.

Wei: "For people who'd never shopped with Amazon, we had a third party firm conduct a market research survey." The rigor was deliberate — not just listening to existing customers, but actively recruiting and interviewing non-customers.

### Social Networks as Case Studies in Asymptote Recognition

**Twitter:** The asymptote is the product's core attributes. The character limit, algorithmic randomness, and text-density suit "infovores" — journalists, techies, intellectuals — but feel "bewildering and unattractive" to mainstream users. The ceiling is structural, not fixable with minor product tweaks. Twitter has a TAM that is definitionally smaller than the social media market.

**Snapchat:** The asymptote is generational, not interface complexity. Camera-first, ephemeral content creation is a behavior native to youth who need a platform they can claim as their own. Older cohorts lack the use case. You cannot market your way past a missing use case.

**Facebook:** The asymptote is a **diseconomy of scale** — the product's growth becomes its ceiling. "Imagine you're in a room with all your family, friends, coworkers, casual acquaintances... What would you say to them?" The massive graph produces broadcasting anxiety. A few over-sharers crowd the News Feed; normal users post less. Viral growth engineers the conditions for declining engagement.

**Instagram:** Better positioned (visual purity + Stories), but faces messaging friction and consumption exhaustion from infinite scroll as potential asymptotes.

### The Broader Argument: Personal Asymptotes

Wei closes by applying the framework to individual careers: successful people identify their personal asymptotes early — the hidden ceiling on their own growth trajectory — and find the structural fix before the curve flattens. This is a founder-OS principle, not just a product one.

The final note: "Customer satisfaction has an infinite time scale and no asymptote when framed correctly" — chasing an ever-receding target is the counter to complacency.

---

## II. VERBATIM QUOTES (load-bearing)

1. "It is said that if you know your enemies and know yourself, you will not be imperiled in a hundred battles" — Sun Tzu (epigraph)
2. "a ceiling that our growth curve would bump its head against if we continued down our current path"
3. "People don't just hate paying for shipping, they hate it to literally an irrational degree."
4. "For people who'd never shopped with Amazon, we had a third party firm conduct a market research survey"
5. "One thing I love about customers is that they are divinely discontent. Their expectations are never static"
6. "Imagine you're in a room with all your family, friends, coworkers, casual acquaintances... What would you say to them?"
7. "In the short run, the stock market is a voting machine, in the long run, it's a scale" — Jeff Bezos (cited by Wei)
8. "The more you sell, the more you lose is not and has never been a sustainable business model"

---

## III. VERSO RELEVANCE

### Finding 1: The "Non-Adopter" Question is the Right GTM Research Frame [SHARPENS]
**Maps to:** §12 Positioning + GTM

Wei's method — interrogate people who don't buy, not people who love the product — is the exact research protocol Verso should run for positioning. The question is not "what do senior engineers want from an agent framework" but "why aren't senior engineers using existing agent frameworks?" The answer almost certainly is NOT "insufficient features" — it is one of: forced graph = loss of agency, LangChain's debuggability/observability gap, inability to promote a prototype to production without a rewrite, or lack of principled evals. These are asymptote framing, not feature requests.

**Verdict:** adopt-now — run this as the literal research protocol for Verso's ICP interviews before the §12 positioning doc is finalized.

### Finding 2: The "Hate" Heuristic — Irrational Aversion is the Asymptote Signal [SHARPENS]
**Maps to:** §1 Bet / Moat

The shipping fee story is precise: the aversion was irrational, which meant rational explanation couldn't fix it. For Verso, the analogous irrational hatred is "forced graph" — senior engineers don't just find LangChain graphs complex; they find them philosophically offensive. They know graphs can model anything; they hate the imposition anyway. This is the identical dynamic. The fix (one flag to checkpoint, no graph required) is the Prime equivalent: it restructures the psychological accounting without asking users to reason themselves into acceptance.

**Verdict:** lock-defer (sharpens §1 counter-positioning framing; confirms the "hate" signal is structural, not negotiable).

### Finding 3: Diseconomy of Scale as a Counter-Positioning Weapon [NEW-IDEA]
**Maps to:** §1 Bet / Moat, §12 Positioning

Facebook's asymptote was that its scale became its ceiling: too many relationships created broadcasting anxiety, reducing the behavior that made it valuable. LangChain has a direct analog: its scale (10M downloads, massive ecosystem, enterprise integrations) created a configuration surface so large that the product became opaque to inspect, difficult to debug, and impossible to customize without understanding the entire abstraction stack. The bigger LangChain gets, the worse the DX for the structurally-aware senior engineer who wants to know exactly what is happening. Verso can name this: "LangChain's scale is its asymptote for engineers who need legibility." This is a new counter-positioning angle, not yet in the established PRD language.

**Verdict:** adopt-now — add "legibility ceiling" as a named sub-point under counter-positioning.

### Finding 4: TAM Redefinition via Asymptote Logic [SHARPENS]
**Maps to:** §12 Positioning (category design / POV)

Wei's method reframes TAM from top-down ("how big is the AI agent market") to bottom-up ("what fraction of engineers who would otherwise use agents are blocked by specific aversions"). This is the correct TAM frame for Verso. The real TAM is not "all agent developers" — it is "senior engineers currently blocked by forced graph, observability gaps, and the prototype-to-production rewrite." That is a much more actionable and defensible claim than broad "AI agent market" sizing.

**Verdict:** sharpen — use this frame in the §12 category design section to bound and define Verso's actual addressable market.

### Finding 5: The Prime Model — Pre-Pay the Friction, Don't Explain It Away [CONFIRMS]
**Maps to:** §7 Demo-able Wedge, §2 Non-goals

The Prime insight is that you cannot rationally argue users out of an irrational aversion. You must restructure the economics so the aversion never triggers. Verso's one-flag durable promotion is exactly this: instead of explaining why event-sourcing + checkpoint/resume is worth the engineering overhead, one flag removes the friction entirely. The non-goal equivalent: Verso will NOT spend cycles explaining why its approach is technically superior to LangGraph — it will show the one-line diff and let the demo speak.

**Verdict:** confirm — already established in the PRD, but the Wei framing strengthens the "don't explain, restructure" principle for §2 non-goals writing.

### Finding 6: Personal Asymptotes as Founder-OS Principle [NEW-IDEA]
**Maps to:** Founder-OS layer (research/04_bad_guide_full)

Wei's closing applies the asymptote framework to individual career trajectories. For a founder, this means: what is the hidden ceiling on YOUR growth as a builder/operator? The answer might be audience size (asymptote: no distribution channel), credibility (asymptote: no shipped product), or scope (asymptote: trying to build everything alone). The stair-step and solopreneur notes in this same batch address the same pattern. For the Verso founder-OS index, this is a named diagnostic tool: "run the non-adopter question on yourself — who doesn't follow you, who dismisses your work, and why."

**Verdict:** adopt-now for the founder-OS index; tag as invisible-asymptote-personal-version.

---

## IV. VERDICT TABLE

| Finding | Verdict |
|---|---|
| Non-adopter interrogation as GTM research protocol | adopt-now |
| Irrational "hate" as the asymptote signal → one-flag fix | lock-defer |
| Diseconomy of scale → LangChain legibility ceiling | adopt-now |
| Bottom-up TAM via asymptote logic | sharpen |
| Prime model → don't explain, restructure | confirm |
| Personal asymptotes as founder-OS diagnostic | adopt-now (founder-OS) |
