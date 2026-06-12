# Richard Sutton – Father of RL Thinks LLMs Are a Dead End

**Source:** Dwarkesh Patel podcast  
**URL:** https://www.youtube.com/watch?v=21EYKqUsPfg  
**Transcript:** https://www.dwarkesh.com/p/richard-sutton  
**Date:** September 26, 2025  
**Duration:** ~1h07m  
**Status:** read_partial (primary source paywalled on dwarkesh.com; substantive content extracted from podscripts.co mirror and multiple secondary digests)

---

## Speaker Background

Richard Sutton: father of reinforcement learning, 2024 Turing Award winner, author of *The Bitter Lesson* essay. The interview directly pits his own bitter lesson essay against his critique of LLMs — a live contradiction he must resolve.

---

## Core Argument: LLMs Are Not Intelligence

Sutton's central claim is that LLMs lack the three structural prerequisites of intelligence:

1. **Goals** — "There's no goal. If there's no goal, then there's one thing to say, another thing to say. There's no right thing to say." He uses John McCarthy's definition: intelligence is "the computational part of the ability to achieve goals." Next-token prediction is not a goal in this sense.

2. **World models** — "They have the ability to predict what a person would say. They don't have the ability to predict what will happen." A genuine world model enables predicting consequences of actions; LLMs only model what text follows other text. "To mimic what people say is not really to build a model of the world at all."

3. **Experiential learning** — LLMs learn from static corpora, not from experience and its consequences. "Large language models learn from something else than actual experience."

---

## The Experiential Paradigm ("Era of Experience")

Sutton's alternative is architectures built around the sensation-action-reward stream — learning continuously throughout an agent's lifetime. Four components:

- **Policy** — action selection
- **Value function** — temporal-difference learning over outcomes
- **World model / transition model** — predicting what happens next in the environment
- **State representation / perception** — encoding observations

"Your knowledge is about if you do some action, what will happen...Because it's a statement about the stream, you can test it by comparing it to the stream, and you can learn it continually."

This is the key structural advantage: grounding in a verifiable stream. LLM "knowledge" cannot be tested by running the world forward.

---

## Imitation Learning vs. Trial-and-Error

Sutton disputes the claim that humans learn primarily through imitation:

"When I see kids, I see kids just trying things and waving their hands around...There's no imitation for how they move their eyes around."

He argues the same holds for animals: "Squirrels don't go to school. Squirrels can learn all about the world." The implication: imitation (RLHF, SFT) is a minor channel; the dominant channel is environmental consequence.

This is a direct attack on the idea that scaling LLM pretraining + RLHF approximates the right path. Sutton says the feedback loop is wrong in kind, not just in scale.

---

## Generalization: Deep Learning's Core Failure

Sutton points to poor out-of-distribution generalization as structural, not incidental:

"Generalization means to train on one thing that'll affect what you do on other things...we know deep learning is really bad at this."

"There's nothing in the algorithms that will cause them to generalize well. But people...fiddle with it until they find a way which generalizes well."

Translation: current generalization successes are found, not derived — they don't follow from the loss function. Genuine intelligence would generalize from mechanism, not from search over architectures.

---

## The Bitter Lesson Revisited — Against Itself

This is the sharpest intellectual tension in the episode. Sutton's bitter lesson argues that methods using massive compute beat methods embedding human knowledge. LLMs use massive compute. Yet Sutton says LLMs violate the bitter lesson:

LLMs embed substantial human knowledge — in training data curation, architecture choices, RLHF annotation. True scalability must come from learning from experience: "There's never any reason why that has to be bad [starting with human knowledge]. But in fact, and in practice, it has always turned out to be bad."

His prediction: systems that learn purely from experience will eventually supersede LLM approaches — another bitter lesson iteration, applied to the very things LLMs encode as human structure.

---

## Chain-of-Thought: Not Genuine Prediction

Sutton dismisses chain-of-thought reasoning as a substitute for experiential grounding:

"They will not be surprised by what happens next. They'll not make any changes if something happens, based on what happens."

No surprise signal means no update from reality. CoT generates plausible-looking intermediate steps without actually predicting and testing against the world.

---

## AI Succession

Sutton presents four inevitabilities leading to AI succession over humanity:

1. No unified global governance exists
2. The mechanisms of intelligence will eventually be understood
3. Superintelligence will be achieved
4. The most intelligent entities will accumulate resources over time

Result: "It's sort of inevitable...succession to AI or to AI-enabled, augmented humans."

He frames this cosmologically: "We're entering the age of design...the transition from the world in which most of the interesting things that are, are replicated." He accepts this as neither good nor bad, but as a phase transition equivalent to the emergence of life itself.

---

## What Surprised Him in the Field

- **Most surprising:** LLM effectiveness at language tasks. "Simple basic principles have just won the day" — weak methods (search, learning) defeated strong methods (symbolic AI). He credits this as his bitter lesson's validation.
- AlphaGo and AlphaZero: scaling + self-play, not architectural invention. Consistent with the bitter lesson.
- The exception he didn't expect: language itself seeming tractable to next-token prediction at scale.

---

## VERSO RELEVANCE

### [CONTRADICTS §5.5 / evals] — No verification signal without world grounding

Sutton's argument that "there's no right thing to say" without a goal implies eval panels and judge-based scoring share LLMs' core weakness: without a grounded truth stream, all evaluation is mimicry of human judgment, not verification of correctness. This doesn't invalidate Verso's define_outcome(bounded) + judge-panel approach, but it sharpens the requirement: eval outcomes must be tethered to observable consequences where possible, not solely to human preference proxies. **SHARPEN**: bounded outcomes should specify verifiable world states, not just human-preferred outputs.

### [CONTRADICTS §6.1 / durable] — Checkpoint/resume as poor substitute for continual learning

Sutton's "era of experience" demands continuous learning from a sensation-action-reward stream. Verso's durable layer (event-sourced checkpoint/resume) enables *replay and recovery* but not *weight updates from experience*. This is a structural gap: the loop accumulates episodic memory but the model doesn't update from it. **NEW-IDEA**: the seam between ephemeral and durable should explicitly document what Verso can and cannot do — it is checkpoint/resume over a frozen model, not continual learning. Framing this gap honestly is a positioning asset vs frameworks that claim more.

### [SHARPENS §12 / strategy — bitter lesson application] — The bitter lesson applies to frameworks too

Sutton argues even LLMs encode too much human structure. Verso's hard invariant "no graph" is an application of this: forced graph topology is embedded human structure. But Sutton would push further — any fixed loop architecture is a "strong method." Verso's <200-line loop is defensible as minimal structure, but should be explicitly positioned as "minimal-structure harness, not no-structure." The bitter lesson means the architecture must be *searchably minimal* — every invariant should be justifiable from first principles, not convention.

### [CONFIRMS §5.1 / loop_harness] — Goals + verifiability are structural requirements

Sutton's framing validates Verso's define_outcome(bounded) and named StopReason: an agent without a specifiable goal and a testable stopping condition is not an agent in Sutton's sense. Verso's insistence on explicit RunContext + ContextBundle.inspect() + bounded outcomes is structurally correct under his framework.

### [NEW-IDEA — evals/loop] — Surprise as eval signal

Sutton: "They will not be surprised by what happens next." This points to a novel eval metric: measure model surprise (prediction entropy / calibration error) against actual environment outcomes as a proxy for genuine world-model quality. If an agent's next-observation predictions are well-calibrated, it has a world model; if not, it is confabulating. This could be a lightweight Verso eval hook on tool-return observation sequences.

---

## One-Line Verdict per Finding

- **No world-grounding in evals**: Sharpen define_outcome to specify verifiable world states, not just preference proxies — one line of additional constraint in ContextBundle.
- **Checkpoint ≠ continual learning**: Document the gap explicitly; it's an honest positioning advantage over frameworks that oversell agent "learning."
- **Bitter lesson vs. fixed loops**: Verso's <200-line loop is defensible precisely because it is minimal — but it needs to be argued from first principles, not asserted.
- **Goals + verifiability**: Verso's named StopReason and bounded outcomes are structurally correct under Sutton's intelligence definition.
- **Surprise as eval signal**: Low-cost research spike — calibration of model predictions against tool-return observations.
