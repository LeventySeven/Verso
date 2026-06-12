# Is There Such a Thing as Good Taste?

**Source:** Paul Graham · PaulGraham.com  
**URL:** https://www.paulgraham.com/goodtaste.html  
**Published:** November 2021 (derived from a talk at the Cambridge Union)  
**Status:** read_full  

---

## Faithful Digest

Graham's core argument is a proof by reductio ad absurdum: if there is no such thing as good taste, there is no such thing as good art. If there is no good art, there is no way for artists to be good at their jobs. If artists cannot be good at their jobs, then Leonardo and Bellini are not better than a randomly chosen eight-year-old. That conclusion is obviously false. Therefore the premise — no such thing as good taste — must be wrong.

> "If we start from the premise that there's no such thing as good taste, we end up with conclusions that are obviously false, and therefore the premise must be wrong."

### Why People Doubt Taste Exists

Graham identifies two reasons people default to "taste is subjective":

1. **Disagreement is pervasive.** "Most people's response to art is a tangle of unexamined impulses. Is the artist famous? Is the subject attractive? Is this the sort of art they're supposed to like?" In practice, extraneous factors dominate most people's aesthetic responses. Experts in one generation often admire different works than experts two generations later. The noise makes the signal invisible.

2. **The "room in the object" problem.** The argument: if being good really is a property of artworks, it should *be in the object somehow*. But it seems to be in the observers' heads, not the object. If observers disagree, how do you adjudicate?

### The Resolution: Partial Order, Not Total Order

Graham's solution to the "room in the object" problem is the crucial technical move:

> "The solution to this puzzle is to realize that the purpose of art is to work on its human audience, and humans have a lot in common. And to the extent the things an object acts upon respond in the same way, that's arguably what it means for the object to have the corresponding property."

The vaccine analogy is load-bearing: saying a vaccine "works" means it causes immune response in people, even though immunity "happens in" individuals. The fact that people's immune systems vary does not make the vaccine's effectiveness meaningless or non-objective. Similarly, art's effectiveness is real even though it "happens in" observers.

The distinction between "objective" and "subjective" is *a matter of degree* — not binary. Particles interacting with each other sit at one pole; people interacting with art are not all the way at the other pole: "their reactions aren't random."

> "There is definitely not a total order either of works or of people's ability to judge them. But there is equally definitely a partial order of both. So while it's not possible to have perfect taste, it is possible to have good taste."

### How Graham Arrived at This Conviction

Not abstract philosophy: painting. Studying painting revealed that you can do it well or badly, that improvement comes from effort, and that the gap between his skill and Leonardo/Bellini's is "not imaginary. They were so good." Personal craft practice is the mechanism that makes taste visible as a real property.

---

## VERSO RELEVANCE

### [CONFIRMS] §12 Positioning — taste is real and testable (not claim-based)

The entire Verso positioning rests on "we have better taste than LangChain." Graham shows this claim is meaningful and non-arbitrary — but only if you can isolate the force (as he could only see it by actually trying to paint). The practical implication: Verso must show the mechanism that makes taste visible, not assert it.

For Verso, the taste-isolating mechanism is the **three-line side-by-side** and the **inspect() surface**: these are the equivalent of "try to paint and compare to Bellini." The diff is the test. Without that test artifact, "we have better taste" is just noise.

**Verdict: confirm** — already the wedge; this is the theoretical foundation for why the demo has to be present.

### [SHARPENS] §12 Positioning — "partial order, not total order" as the honest register

Graham's precision matters for Verso's tone: taste exists as a *partial order*, not a total ranking. This is the intellectual-honesty register already established (decade not year, no magic box). Applied to positioning: Verso should never claim to be globally better than all alternatives. It claims to be *demonstrably better on the specific dimension of harness taste* for structurally-aware engineers. That is a partial order claim — and it is both defensible and testable.

> "It is not possible to have perfect taste, it is possible to have good taste."

Translated: Verso is not the perfect agent framework. It is the one that has thought hardest about the right seam, and you can see that by looking at the API.

**Verdict: sharpen** — this is the exact register for the launch copy: "not perfect, but demonstrably considered on the thing that matters."

### [NEW-IDEA] §7 Demo-able Wedge — "isolate the force" as demo design principle

Graham says taste becomes visible only when you isolate it: "It's only when you isolate this force, for example by trying to paint and comparing your work to Bellini's, that you can see that it does in fact exist." 

This is the design principle behind the three-line side-by-side: it *isolates the force* (the context seam, the one-flag durable diff) so the audience can see the property that would otherwise be buried in noise. The demo is doing epistemics, not just marketing. This framing is worth making explicit in how Verso describes its demos and launch materials.

**Verdict: adopt-now** — frame the demo explicitly as "isolating the force so the property becomes visible." Useful in Show HN text and the README opening.

### [NEW-IDEA] §1 Bet/Moat — the vaccine analogy reframes the "taste moat"

Graham's vaccine analogy provides a better way to articulate why Verso's taste advantage is a real moat and not just aesthetic preference. A vaccine is effective because of what it reliably does to human immune systems; Verso's API design is effective because of what it reliably does to structurally-aware engineers who try it — recognition, confidence, reduced friction at the seam. That is a measurable response, not subjective preference.

This means the moat is not "we have good taste" (an assertion) but "we produce reliable recognition responses in the target user population" — which is something that can be studied (DX interviews, activation metrics, time-to-first-working-agent).

**Verdict: adopt-now** — sharpen §1 moat language: frame taste advantage as "reliably produces recognition and confidence responses in structurally-aware engineers," then show how to measure it.

### [SHARPENS] product_taste — extraneous factors corrupt taste perception

Graham's diagnosis of why people doubt taste ("is the artist famous? is this what I'm supposed to like?") maps directly onto Verso's positioning problem: engineers evaluating frameworks are dominated by extraneous factors (GitHub stars, company backing, LangChain familiarity). The Verso positioning challenge is to isolate the force — get the structurally-aware engineer to look at the seam cleanly, before the extraneous signals overwhelm judgment.

This is a design challenge for the Show HN post: sequence the demo so the seam is visible before the framework name / comparison / credentials appear.

**Verdict: sharpen** — Show HN post structure should lead with the isolating demo, not with positioning claims. Let the partial-order judgment form first.

---

## One-Line Verdict Per Finding

| Finding | Verdict |
|---|---|
| Taste is real (partial order, not total) → partial-order claims are defensible and honest | confirm |
| "Isolate the force" → demo must make the property visible, not assert it | adopt-now |
| Vaccine analogy → taste moat = reliably produces recognition in target users | adopt-now |
| Extraneous factors corrupt judgment → Show HN must sequence demo before claims | sharpen |
| Partial order framing → Verso's honest register: "demonstrably considered, not globally perfect" | sharpen |
