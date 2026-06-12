# Brendan Foody on Teaching AI and the Future of Knowledge Work
**Source:** Conversations with Tyler, Ep. 267  
**URL:** https://www.youtube.com/watch?v=zld39xD4sus  
**Transcript:** https://conversationswithtyler.com/episodes/brendan-foody/  
**Recorded:** October 16, 2025  
**Format:** Podcast (~62 min), Tyler Cowen interviewing Brendan Foody (Mercor, youngest unicorn founder)  
**Status:** read_full (transcript at conversationswithtyler.com + podchemy notes)

---

## What Foody Actually Argues

### 1. Rubrics Are the Real Asset — Not Raw Data

Foody's core thesis: the most valuable thing an expert can produce for AI training is not outputs but *evaluation frameworks*. If you can specify what "good" looks like in a rubric with dimensions and weights, models can attempt the task repeatedly, score each attempt, and improve via RL. Without a rubric, you get RLHF at best (human preference comparisons), which is slower and noisier.

> "If the poem evokes this idea that is inevitably going to come up in this prompt or is a characteristic of a really good response, we'll reward the model a certain amount."

The implication: the bottleneck in AI progress is not compute or data volume — it is the articulation of expert judgment. Organizations that can elicit rubrics from domain experts have a structural advantage.

### 2. Taste Problem — Kant's Objection, Foody's Answer

Tyler raises Kant: taste is that which cannot be captured in a rubric. Foody's response has two prongs:
1. When rubrics fail, fall back to RLHF — people with genuine taste choose which outputs they prefer, repeated many times.
2. Long-run: "models learn what taste do you have and how does it pull on each of those knowledge bases to personalize it to your preferences" — not enshrine any single era's aesthetic.

Key tension he identifies: contemporary consensus ≠ peak quality. He suggests calibrating models against peak-era experts (1980s heavy metal producers, specific poetry traditions) rather than averaging over current preferences.

### 3. APEX Framework — Measuring Real Economic Value

Foody describes Mercor's APEX methodology: survey domain experts on how they actually spend their time, then benchmark models against those exact task distributions.

> "We survey [experts on] how do they spend their time? Using their time is the best proxy we have for economic value associated with their salary."

Finding: models improved ~25-30% per year on these economically valuable tasks. But:

> "The rate of model improvement at economically valuable tasks is incredible...call it a 25 percent–, 30 percent–improvement [per year]."

### 4. The Final 25% — Persistent Human Bottleneck

Cowen presses on integration: a human expert combines many skills in a single entity. Models at zero on that combination. Foody agrees:

> "Models are advancing very, very quickly...will really struggle with that last 25 percent...human expertise will be imperative."

Specific failure modes: (a) longer-horizon tasks (50-100 hours), (b) integrating multiple tools, (c) anything requiring genuine synthesis across incommensurable domains.

### 5. Knowledge Work Transformation — Fixed Cost Replaces Variable Cost

Foody's structural prediction: knowledge workers stop performing repeated analysis and start building RL environments. The investment banker doesn't analyze the data room — they teach the model to do it once.

> "Instead of the investment banker redundantly analyzing...they'll teach the model how to do that once...Similar to building software once."

New job category emerging: "people training agents, building RL environments to help teach models." This is a minority of high-end workers now; Foody predicts majority transition within ~5 years.

Analogy to software economics: demand is elastic. Making engineers 10x efficient → 10x more engineers building 100x more software. Not a shrinking field.

### 6. Hiring Without Vibes — Measure the Actual Thing

Foody is sharply critical of standard hiring:

> "Instead of focusing on how do we measure how well this person does their investment analysis...they have this vibes-based conversation."

His remedy: "Just give them a project and grade them." For non-technical roles where work samples are hard, past performance in a structurally similar environment is the best proxy. He distinguishes:
- **Y-intercept**: current raw ability
- **Slope**: growth trajectory / learning rate

The genuinely hard problem: measuring slope in an interview. AI may outperform humans here by processing historical manager notes and long-term performance data.

### 7. Price Competition to Kill Competitors (Donut Empire Anecdote)

Foody at age ~13: bought Safeway donuts ($5/dozen), sold for $2 each at school. When a competitor emerged:

> "I dropped my prices to $1 for two weeks to drive them out of business."

Then raised prices back. Classic predatory pricing. Cowen's implicit point: this instinct — think structurally about competition, not just margins — is formative.

### 8. Expertise Scarcity and the Cass Sunstein Clock

Foody estimates ~2-3 years until models make it very hard for expert humans to find errors in legal reasoning. The "Cass Sunstein test" = can you find non-trivial errors in model legal output? He treats this as a practical benchmark for expert-level cognitive work.

---

## Verbatim Quotes (High-Confidence)

1. "If the poem evokes this idea that is inevitably going to come up in this prompt or is a characteristic of a really good response, we'll reward the model a certain amount."
2. "The rate of model improvement at economically valuable tasks is incredible...call it a 25 percent–, 30 percent–improvement [per year]."
3. "We survey [experts on] how do they spend their time? Using their time is the best proxy we have for economic value."
4. "Instead of the investment banker redundantly analyzing...they'll teach the model how to do that once."
5. "Models are advancing very, very quickly...will really struggle with that last 25 percent...human expertise will be imperative."
6. "I dropped my prices to $1 for two weeks to drive them out of business."
7. "Just give them a project and grade them."
8. "You want consensus but also healthy disagreement to capture edge case scenarios models might miss."
9. "The final 25% of expertise will remain a human-driven bottleneck for a very long time."

---

## VERSO RELEVANCE

### [SHARPENS] §1 Bet/Moat — Rubrics-as-Moat, Not Just Data

Foody's rubrics-vs-data framing maps directly onto VERSO's eval-corpus-as-flywheel thesis. The specific sharpening: what matters is not that VERSO *runs* evals but that it makes rubric-creation tractable for production engineers who are not ML researchers. The moat is the schema for expressing "what good looks like" — not the runner. Every eval VERSO captures is a rubric that improves the loop. Foody names the exact bottleneck VERSO is positioned to solve.

**Tag: SHARPENS** | Section §1 | Verdict: the harness that makes rubric creation frictionless for senior engineers owns the eval flywheel; frame VERSO's inspect() + eval corpus as the rubric layer.

### [CONFIRMS] §1 Bet — Final 25% = Human-in-the-Loop Necessity

Foody's "final 25%" argument directly confirms VERSO's HITL design choice. The tactic<->durable seam is not a "nice to have" — it is structurally necessary because the tail of hard cases cannot be automated. Production agents will always need escalation paths.

**Tag: CONFIRMS** | Section §1/§2 | Verdict: Foody's data-backed claim about the 25% ceiling validates the architectural decision to make HITL a first-class primitive, not a bolt-on.

### [SHARPENS] §7/§12 Demo-able Wedge — The "Give Them a Project" Principle

Foody's hiring philosophy ("give them a project, grade them") maps onto VERSO's wedge: show the diff, not the claim. The demo-able wedge should be structured exactly like a work sample — here is the harness running, here is what the eval caught, here is the diff that 3-line side-by-side makes visible. The target persona (structurally-aware senior engineer) responds to this. They are Foody's "slope, not Y-intercept" people.

**Tag: SHARPENS** | Section §7/§12 | Verdict: Demo design principle — measure the actual thing; the VERSO wedge is a work sample, not a pitch.

### [NEW-IDEA] Founder-OS — Slope vs. Y-Intercept as Hiring Rubric for VERSO's Community

Foody's slope/Y-intercept distinction is directly usable for VERSO's cold-start persona targeting. The ~5 vocal production leads VERSO needs at Stage-1 are slope-maximal engineers — they are not the most credentialed, they are the ones who are growing fastest in production-agent work. Targeting slope-high people (posting about failures, asking deep questions, building in public) beats targeting title-high people. This is a concrete GTM filter.

**Tag: NEW-IDEA** | Section founder-OS / §12 GTM cold-start | Verdict: recruit Stage-1 atomic network by slope signal, not credential signal — find engineers publicly processing production-agent failures.

### [CONFIRMS] §12 Positioning — Taste Cannot Be Fully Codified, but Rubrics Come First

Foody's Kant section confirms the VERSO positioning principle that "explain without AI" is an invariant. The harness must be legible without magic-box trust. Foody's framing: when you can't write a rubric, fall back to RLHF — but always try rubrics first. VERSO's inspect() is the rubric-first tool.

**Tag: CONFIRMS** | Section §12 | Verdict: legibility-first design is confirmed by the structure of how experts actually encode judgment.

### [NEW-IDEA] §2 Non-Goals — Consensus vs. Edge Cases as Eval Design Principle

"You want consensus but also healthy disagreement to capture edge case scenarios models might miss." This is a concrete principle for VERSO's eval corpus design: a corpus that only captures happy-path agreement is brittle. VERSO should actively surface minority-verdict evals (cases where human reviewers disagreed) as the most informative training signal.

**Tag: NEW-IDEA** | Section §2 / §1 eval flywheel | Verdict: VERSO eval schema should capture disagreement vectors, not just majority verdict — disagreement-flagged evals are the highest-signal rows.
