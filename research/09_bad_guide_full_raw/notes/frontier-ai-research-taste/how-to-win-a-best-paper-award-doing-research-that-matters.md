# How to Win a Best Paper Award (Doing Research That Matters)

**Source**: https://nicholas.carlini.com/writing/2026/how-to-win-a-best-paper-award.html  
**Author**: Nicholas Carlini (Google Brain/DeepMind → Anthropic)  
**Published**: 2026  
**Read time**: ~30 minutes  
**Status**: read_full

---

## Faithful Digest

This is a decade retrospective from one of ML security's most-cited researchers. Carlini frames the essay's nominal subject (winning best paper awards) as a proxy signal for doing work that actually matters. The core argument: you can't optimize for the award directly because the award is sampled from a distribution you shape but don't control. Optimize for the distribution instead — i.e., do work with genuine impact.

### The Real Subject: Taste

> "The single most important skill to develop for high-impact research is good taste in what problems are worth solving."

> "People who haven't refined their taste frequently spend months on problems that don't matter...they write papers that are technically correct but that no one reads."

Taste operates at two scales: (1) which broad areas matter, and (2) which specific approach within an area will succeed technically. Carlini's account of taste development is almost entirely tacit — it accrues through doing, not through reading about it.

### Idea Generation

**Three deliberate reading modes**:
1. **Broad awareness**: Skim to find the one-sentence novel contribution. "Your goal is to find that sentence."
2. **Technical depth**: Read only sections directly relevant to your work.
3. **Critical mastery** (few papers/month): Read top-to-bottom enough to reproduce it independently, find implicit assumptions and errors.

**Collaborative discovery**:

Carlini emphasizes serendipitous collaboration structured by explicit outreach. His EuroCrypt award paper: Shamir gave a Stanford talk → Carlini identified an extension direction → spent 12 hours solo developing partial solutions → emailed results to Shamir → Shamir contributed the missing pieces. The template:

> "Hi [person], I am working on [project] and have done [steps 1-3]. I am now working on [problem]..."

**Deliberate forgetting** (the paradox):

> "Once you've read everything, the second step is to forget it all. The reason is simple: everything that's already been done has already been done."

Three failure modes from over-reading:
1. Accepting field conventions uncritically, including methodological errors
2. Assuming arbitrary early decisions were justified
3. Being "poisoned" by unsuccessful approaches into implicitly dismissing alternatives

His membership inference paper: after reading confusing early work, he set aside their approaches entirely, developed a cleaner solution independently, and only reviewed prior methods afterward.

**Uniqueness requirement**:

> "Find a paper that someone else won't be submitting to the same conference. Because if all you're doing is something someone else would have done, have you really contributed anything at all?"

> "Areas where you keep asking yourself 'why is everyone doing this obviously wrong?'"

**Timing advantage**:

> "If you write a high-quality paper early, you can have an outsized impact compared to writing that same paper even a year later...altering the direction of a field is much harder than starting it in the right direction."

**Serendipity is real**:

> "The most important thing here is to get lucky...Half the papers I've written weren't from some deliberate thought process, but from a spontaneous conversation, or because I was thinking about some problem when I happened to read a paper that introduced a tool I could use."

Web-scale poisoning paper: not deliberately sought, but discovered while studying LAION-5b after recognizing expired domain purchases could inject malicious content.

### Impact Filtering (The Kill Criteria)

The research criterion is not "can this become a paper?" but "will this matter?":

> "Some people go into research with the objective of writing a conference paper. Don't do that. You need to go into research with the objective of discovering something interesting, important, and new."

> "You can't ask 'what is the minimal contribution I can write that will technically still count as a science paper?' You're doomed to fail at having high impact if you take this approach."

**The importance multiplier**: research impact = skill × field importance. Being excellent at a less-valued problem still underperforms being competent on a high-importance problem.

**Ruthless deprioritization** — the 90% rule:

> "Even if you're 90% of the way through a 'just ok' paper, the marginal return on spending the last 10% to finish it versus spending that same 10% on a paper 100x more important makes the latter the clear winner."

Carlini abandoned ongoing work upon GPT-2's release to study language models.

### Execution

**De-risk first**:

> "I start probably five times as many papers as I finish, and each of them I thought was a good idea that had merit, but things just didn't work out as I expected."

> "Start with the sub-problem most likely to fail...You want to de-risk the project as quickly as possible."

> "Fail fast applies just as well here: don't build the polished version of your experiment when a small prototype will tell you whether the core idea works."

**Kill criteria**:
1. Technical failure: core assumptions prove false; "trying harder won't let you prove a statement that's false."
2. Low-impact realization: "You could probably, with some work, turn this into a paper. But it's not going to become a *good* paper. When this happens, just kill the idea and pick something new."

**Unreasonable effort**:

> "Sometimes magic is just someone spending more time on something than anyone else might reasonably expect."

> "Every experiment should be as precisely performed as you can manage. Run multiple trials. Control for confounders...On multiple occasions I've put in several hours of work just to strengthen a 'sometimes' to 'usually', because this is what it means to care."

Wildlife photography metaphor: correct positioning + developed skill + "an unreasonable amount of time waiting for exactly the right circumstances."

**Singular focus**:

Papers must express one core idea, documented before writing begins.

> "Every experiment should connect to the core idea...Every paragraph and every figure you'll eventually write should be directly attributable to the goal of the paper."

> "Readers will forget why you're doing whatever you're doing, and lose track of the core idea."

But: "Your paper should be at a local optimum; the reader must not be left with the thought 'I really wish the authors had done X.'"

### Writing

**Abstract — five-sentence formula**:
- S1: Topic identification
- S2: Specific problem statement
- S3-S4: Results and methods
- S5: Significance

> "Be specific and explain exactly what you're going to get out of your paper...Include at least one specific number...Don't hedge: just state the clean (but true) version of your result."

**Title**: "Your paper title matters if your paper is good...As long as your title is accurate you'll be fine." If struggling with title, the paper combines too many ideas — fix the paper, not the label.

**Introduction as framework-building**: Guides readers from current beliefs into the paper's conceptual space. The hardest case: "presenting conclusions the reader must reach themselves rather than stating them outright, requiring evidence so overwhelming that by the end, the reader arrives at that conclusion on their own."

His cryptography paper required 3 pages easing theoretical cryptographers into viewing model stealing as cryptanalysis. His SSL poisoning paper had to convince readers that unlabeled data training would become standard — arguing about the future before defending the present.

**Conclusion as reflection**: "CONCLUSIONS ARE NOT ABSTRACTS OR INTRODUCTIONS IN THE PAST TENSE." They answer "so what?" — the paper's moral meaning beyond numerical results.

> "If this paper were to succeed wildly...what could I say in a conclusion? If I have nothing to say beyond repeating the results, then what I've done mustn't have mattered very much."

**Writing quality**:

> "The only rule that matters is delivering the message to your reader; all other rules come second."

Read work aloud or use text-to-speech to catch issues invisible on screen.

His membership inference paper exemplifies writing impact: "The reason this paper has been cited so frequently over the last few years is that we did a far better job writing down what a membership inference attack is than anyone had done before...even though our exact method no longer really matters...it's now one of the canonical papers people point to for this field."

### Post-Submission Factors (What You Can't Control)

**Persistence through rejection**:

> "The majority of my papers that have received best paper awards were rejected at least once before they got in. In one case, a paper of mine was rejected four times first."

Pattern: initial rejection of heretical ideas → authors strengthen argument → later reviewers at different time encounter more convincing paper on now-slightly-less-novel ideas.

**Timing failures**: Novel ideas rejected when premises not yet accepted (his SSL poisoning paper rejected repeatedly at security conferences until unlabeled data importance became obvious).

**The core reframe**:

> "You don't control the sampling process — that's determined by, among others, the program committee, the timing of your work, who else submitted that year. But you *do* control the distribution."

> "You shouldn't go into research with the objective of winning a best paper award. It's unhealthy, counter-productive, and out of your control...Instead, write papers with the goal of having an impact."

### Comparative Advantage Self-Mapping

Carlini explicitly catalogs his strengths:
- Clarifying evaluation methodologies (adversarial robustness evaluation)
- Making abstract concepts visceral (neural network memorization)
- Cross-disciplinary synthesis (differential cryptanalysis meets model stealing)
- Identifying emerging vulnerability classes before standard practice

> "I'm not very good at proposing entirely new research directions...But I am reasonably competent at taking a fuzzy field someone else defined, and bringing clarity and order to how things should be done."

---

## VERSO RELEVANCE

### [NEW-IDEA §1 the bet / §12 positioning] — "Deliberate Forgetting" as Framework Design Principle

Carlini's deliberate-forgetting pattern (set aside prior work, develop independently, review afterward) is directly applicable to Verso's market positioning discipline. The failure modes from over-reading prior frameworks:
1. Accepting framework conventions uncritically (LangChain-style graph abstraction, AutoGen-style class hierarchy)
2. Assuming arbitrary early decisions (e.g., the "chain" metaphor, the "agent" as subclass) were justified
3. Being "poisoned" into dismissing alternatives

**The Verso design recommendation**: when evaluating primitives for the harness, start from first principles (what does a running agent actually need?) before surveying what existing frameworks provide. Carlini's membership inference breakthrough came from ignoring early work and developing cleaner framing independently.

**Verdict: adopt-now** — apply this principle explicitly in Verso's primitive-design process. For each proposed API surface, write the interface from user needs first, survey prior art second.

### [SHARPENS §5.1 loop / §1 the bet] — De-Risk-First as Loop Architecture Principle

> "Start with the sub-problem most likely to fail...You want to de-risk the project as quickly as possible."

The fail-fast principle maps directly to Verso's loop design. The current loop runs tools and processes observations sequentially. A de-risk-first architectural variant would: (1) identify the most likely failure point in a planned action sequence before executing, (2) test that sub-problem first (minimal probe), (3) only commit full resources after the probe succeeds. This is not a graph — it's a loop heuristic the model can apply via its `think` builtin or explicit planner output.

For Verso: the observation-masking compaction (already harvested, N=10) is a kind of de-risk primitive — compacting before the context saturates, not after. The analog here is a **failure-probe pattern**: before executing a complex multi-tool plan, have the loop issue a lightweight verification call first.

**Verdict: sharpen** — add failure-probe pattern to §5.1 loop primitives docs. Not a new architectural construct; implement as a recommended prompt pattern + optional planner output hint.

### [SHARPENS §5.5 evals] — Singular Focus Test as Eval Quality Gate

> "Papers must express one core idea...Every paragraph and every figure you'll eventually write should be directly attributable to the goal of the paper."

This single-focus discipline maps to Verso's `define_outcome(bounded)` primitive design. An eval with multiple mixed goals (does the agent complete the task AND stay under cost AND produce well-formatted output?) is exactly the "too many ideas" paper that cannot have a clear title. Verso's eval framework should enforce **one primary bounded outcome per eval run**, with secondary metrics collected but not gating.

> "If struggling with titles, the paper combines too many ideas — fix the paper, not the label."

For evals: if you can't state the eval's success criterion in one sentence, the eval has too many goals. Verso could lint this at `define_outcome()` call time.

**Verdict: adopt-now** — enforce single-primary-outcome discipline in `define_outcome()` API design. Secondary metrics are fine as observability, but `define_outcome()` takes exactly one bounded success criterion.

### [SHARPENS §12 positioning] — "Timing: Altering Direction vs. Starting in the Right Direction"

> "Altering the direction of a field is much harder than starting it in the right direction."

This is a precise articulation of Verso's first-mover framing for the context-engineering + evals layer. The window where Verso can establish primitive naming (what is a `ContextBundle`? what is a `RunContext`?) and evaluation semantics is short. Once LangChain/LlamaIndex/AutoGen establish those names, Verso is altering direction rather than starting it. This reframes Verso's urgency on the interface-lock phase.

**Verdict: sharpen** — use this framing explicitly in §12 GTM: interface-lock on naming and primitives is a time-bounded competitive advantage.

### [CONFIRMS §2 non-goals / §5.1 loop] — The 90% Rule Confirms Loop Minimalism

The 90% rule (abandon a "just ok" direction even when nearly complete) is a strong endorsement of Verso's "loop file stays <200 lines" invariant. The temptation to add one more feature to the loop file is exactly the "90% done just-ok paper" trap. Ship the minimal loop, resist expansion.

**Verdict: confirm** — reinforces the invariant; no new action needed.

### [NEW-IDEA §5.5 evals] — Write Quality as a Proxy Eval

Carlini's membership inference paper being canonical not because of method novelty but because of writing quality — "we did a far better job writing down what a membership inference attack is than anyone had done before" — suggests a **documentation eval** for Verso primitives: does the primitive's interface communicate what it does clearly enough that someone can use it without reading the source? This is testable: write the interface doc, give it to a developer without the source, see if they can use it correctly. This is a form of eval applied to the framework itself, not just to agents built on it.

**Verdict: lock-interface-defer** — adopt as a principle for interface review; don't implement as automated eval yet.

---

**Overall verdict**: High-value source for §12 positioning and §5.5 eval design. Deliberate-forgetting is the most actionable new idea for Verso's design process discipline. The timing framing for interface-lock sharpens the GTM urgency argument.
