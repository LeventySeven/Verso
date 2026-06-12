# Ethan Perez — Bottom-Up Alignment Research

**Source:** https://www.youtube.com/watch?v=XDtDljh44DM  
**Format:** The Inside View podcast / Alignment Forum transcript  
**Guests:** Ethan Perez (Anthropic), Mikita Balesni (Apollo Research), Henry Sleight (Astra Fellow)  
**Published:** April 9, 2024  
**Transcript found at:** https://www.alignmentforum.org/posts/7GmDs4BqrFW3kk4nP/how-i-select-alignment-research-projects  
**Status:** read_full (complete transcript read from LessWrong/Alignment Forum mirror)

---

## Core Argument

Perez argues the **bottom-up empirical approach to research** is systematically underrated in the alignment community. The community encourages junior researchers to spend months reading before experimenting; he contends rapid experiments (often within a day) followed by sharing results for feedback almost always outperforms the reading-first pattern.

---

## What Perez Actually Argues — Mechanisms & Verbatim Quotes

### Two modes: top-down vs bottom-up

> "There's two modes for how I pick projects. So one would be thinking about a problem that I want to solve and then thinking about an approach that would make progress on the problem. So that's top down approach, and then there's a bottom up approach, which is [thinking]: 'seems like this technique or this thing is working, or there's something interesting here.' And then following my nose on that."

He uses both. For adversarial robustness the top-level direction is top-down; the specific method choice (test-time monitor vs. adversarial training vs. model internals) is bottom-up.

### Empirical feedback loop as the core unit

The iteration cycle is **within a day**. A negative result is not a failure — it's information gained. Red flags:

- Experiment loop takes >1 week
- Fixed cost to run the first experiment is ≥1 month of FTE time

> "If the experiment loop is going to take more than a day, that's pretty rough because then you can't run experiments overnight and get feedback the next day."

He shares 1-day results in a short doc with collaborators at Anthropic and outside. General positive reaction = continue; fundamental doubts = reconsider.

### The LLM-autogeneration pivot story

He was hand-writing adversarial evaluations and outsourcing to Surge. Turnaround was a week per batch; progress was frustratingly slow. One Friday he told collaborators: "I'm going to get models to write the evaluations for me." By end of weekend: hundreds of working evals.

> "I just had this strong sense. I was like, man, I feel like LLMs should really just be able to do this. I think this project should just be so much easier and so much faster."

This became the "red-teaming language models with language models" paper, and the general frame — **automate the hard task with an LLM** — now applies to many alignment sub-tasks.

### On reading prior work

His view has evolved through three phases:  
1. Spend a month reading → found it demotivating, much was not directly relevant  
2. Privilege own experiments entirely  
3. **Current nuanced view:** topic-dependent. Adversarial robustness: lots of relevant prior art, worth reading. Novel directions: experiments return more per hour than paper review.

> "I would just think and do a little bit of quick reading before starting in a new area about how much actually relevant stuff has been done, and then be critical in your evaluation on that. And then if you're like, oh yeah, I spent a day looking at this, none of the stuff looks like it's actually that relevant, then I would just be like, experiments are going to be much more useful."

### Collaboration selection

Collaborator selection heuristic: complementary skills + genuine enjoyment + not duplicating someone else's identical effort. When another group is pursuing the same thing:

> "Oh, I'm more excited about this other direction. So I'm often just like, wow, it's exciting, I can go do something else."

Even working under controversial researchers (he cites Dan Hendrycks) is high-value because of the mental model it builds.

### Junior researcher advice

> "If you are a junior researchers, the pure bottom up approach is going to be probably less effective unless you have a mentor who gives you a good direction."

Junior researchers should *not* split projects because fixed costs dominate:

> "Each project has a fixed cost. Fixed cost is larger if you're a new researcher... if you're doing 20 hours a week on a project as a first time researcher, that's closer to a net output of 0 and all the gains come super linearly after that point."

But they can maintain **visibility into alternatives** without running experiments — by writing two-page project docs and talking with people, which keeps the pivot option live without incurring the full context cost.

### Timing windows (low-hanging fruit epochs)

> "Each time there's a new model capability or there's a new model generation which is clearly more capable than previous model generation, that's definitely a time to be opportunistic because there's a ton of low hanging fruit that's not been explored."

Multimodal capabilities, code interpreter, GPT-4 launches — all created temporary windows of abundant unexplored territory.

### Field maturation and sequencing

> "Right now, there's just a bunch of safety problems that do need to be solved now before we continue scaling up... if we don't solve adversarially robustness, bad things will actually happen."

The responsible scaling plan logic drives him *toward* top-down sequencing: which problems have to be solved by which capability level?

### Final takeaway verbatim

> "The bottom up research approach is probably underrated in a lot of alignment research, where you just try some things that seem somewhat plausible and then see how they pan out and then go from there... I've seen lots of junior alignment researchers spend a month reading about alignment, and that's highly encouraged by the alignment community. There's tons of writing out there. A lot of it seems like you're making intellectual progress on this, and it's very critical of different directions. And so you can feel demotivated... just the opposite attitude of 'oh this seems actually plausible. I can do this fine tuning run in an hour'... if more people on the margin did that that would be great."

---

## VERSO RELEVANCE

### [SHARPENS §5.5 evals] — Quick-turnaround eval feedback loop as product primitive

Perez's core workflow: **run experiment in a day → write short doc → circulate for feedback**. His pivot to LLM-generated evals cut a week-per-batch turnaround to hours. For VERSO, this sharpens the rationale for embedded in-process evals (already in PRD §5.5): the value is not correctness per se but **feedback loop velocity**. The eval layer should be optimized for "overnight-to-morning" cadence, not scientific rigor. One-line verdict: ship a fast-path eval that surfaces signal in <60s, not a perfect judge panel for every run.

### [CONFIRMS §5.5 evals + NEW-IDEA] — Two-page project doc as a named artifact in the evals layer

Perez's "two page doc" pattern (problem → motivation → proposed experiments → share externally) is a concrete protocol for defining outcomes before running. VERSO's `define_outcome(bounded)` + `judge_panel` combination maps exactly to this. The new idea: VERSO could expose a lightweight `Spec` object that agent authors write before running — capturing the "what would make this successful" before the loop starts. This would catch misalignment between the harness author's intent and the model's trajectory.

### [CONFIRMS §5.2 context] — Caching accumulated context as a research productivity multiplier

His "fixed cost" framing for project focus is a direct analogy to context engineering: the first N hours of a project pay the fixed cost; after that you have the whole codebase in working memory. This is identical to VERSO's KV-cache prefix discipline — the first tokens in a session pay to establish context; subsequent calls amortize it. The PRD's existing emphasis on prefix caching is confirmed as the right investment.

### [NEW-IDEA §4 seam] — Visibility-into-alternatives as a first-class design principle

Perez's advice for junior researchers is: maintain awareness of alternative project directions *without* paying the full context-switching cost. This maps cleanly to VERSO's tactical↔durable seam: an ephemeral agent should be able to signal "I'm at a decision point, here are the alternatives" without requiring a full checkpoint/resume cycle. A lightweight `checkpoint_hint()` or `yield_decision(alternatives=[...])` in the tactical layer — below the durable threshold — would let humans inspect branching points without forcing graph-style architecture.

### [CONFIRMS §12 positioning] — Bottom-up empiricism vs. top-down architecture religion

Perez's core contrast (empiricism vs. planning-heavy month-long reading) mirrors VERSO's positioning against frameworks that force you to draw a graph before you can run anything. The alignment community's "spend a month reading" pathology = AI framework's "define all nodes and edges upfront." VERSO's claim — start with 10-line ReAct, promote only when durable behavior is needed — is the software equivalent of Perez's fast-experiment then-evaluate cycle.

---

## Verdict (no-overkill)

No claim here requires a rewrite of existing VERSO plans. The main delta is: (1) the eval layer should be optimized for feedback loop velocity over completeness, and (2) a lightweight pre-run `Spec` artifact — two pages worth of intent — could prevent the most common failure mode where the agent succeeds at the wrong thing.
