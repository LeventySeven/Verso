# AI Agents and the Path to AGI — Bob McGrew (YC)

**Source**: https://www.youtube.com/watch?v=eW7rUtYHD9U
**Speaker**: Bob McGrew, ex-Chief Research Officer, OpenAI
**Format**: YC "How to Build the Future" interview with Garry Tan (~30m)
**Status**: read_partial — no official transcript found; content reconstructed from detailed blog summaries (jetthoughts.com, antoinebuteau.com) and Sequoia podcast notes covering overlapping McGrew talks. Verbatim quotes below are from summaries, not a raw transcript.

---

## What McGrew Actually Argues

### The Three Pillars of AGI (his framing)

McGrew's position: the fundamental conceptual breakthroughs needed for AGI are already in hand. "If you look back from 2035, we're not going to see anything new and fundamental" — the three pillars are:

1. **Transformers** (language models as universal function approximators)
2. **Scaled pre-training** on those models
3. **Reasoning** woven throughout with increasing multimodal capabilities

The implication: the game now is engineering and scaling, not discovering new paradigms.

### Test-Time Compute as the New Axis

Pre-training hit exponential compute requirements for marginal gains — "it faces exponential compute requirements for marginal gains." The pivot: instead of pushing pre-training harder, invest in test-time compute, letting the model "think longer and more deeply about problems, leading to more reliable outcomes."

McGrew's explanation of the mechanism: reasoning capabilities transfer directly from "thinking about problems" to "taking action in the world." The same technique that lets a model reason more carefully also enables agentic action. Quote: "The techniques that give that to you in terms of thinking harder also apply to taking action in the real world."

### Reliability as the Agent Unlock

The clearest causal chain McGrew draws: reasoning → reliability → user willingness to delegate. "You really need a lot of reliability in order for you to be willing to wait five minutes or five hours for something to happen." Unreliable agents aren't just annoying — they fail the fundamental trust contract that makes delegation rational.

This is not a capability argument; it's a trust argument. Users don't need agents to be smarter; they need to be able to predict whether the agent will succeed before committing to wait.

### Pre-Training's Diminishing Returns (explicit)

"While pre-training isn't disappearing, McGrew emphasizes it faces exponential compute requirements for marginal gains. The focus now shifts to architectural improvements rather than pure scale increases." This is the scaling plateau thesis from a practitioner who ran GPT-4 and o1.

Note: this is the most significant claim in the talk — the person who scaled pre-training to GPT-4 is saying the axis of competition has shifted.

### Agent Economics

A surprisingly strong structural argument: once an AI agent achieves human-level legal or knowledge-work capability, it faces infinite supply from frontier model providers. "Some other startup can come in and compete that away" using the same frontier models. Commodity pricing follows — agents will be priced at compute cost, not at human-replacement value.

The escape: enterprise infrastructure that extracts and structures business context to feed to models. Companies like Distyl and Palantir cited as exemplars — they solve integration problems frontier labs won't tackle individually.

Proprietary data caveat: most proprietary data is "embodied labor" that AI can now replicate (customer calls, case studies). The exception is customer-specific data (portfolios, preferences) that enables personalization rather than teaching general skills.

### Robotics Inflection

McGrew predicts a robotics breakthrough comparable to ChatGPT's language impact is "forthcoming," enabled by the combination of LLMs (natural language interface) and strong vision encoders. Physical Intelligence solving diverse tasks in months contrasts with 2016's single-problem robotics efforts.

### Startup Guidance

- Use the best available frontier models, not optimized older ones
- Speed to market over lengthy development cycles
- Target CEO-level priority problems to bypass organizational bureaucracy
- Obvious improvements (e.g., adding tool use to chain-of-thought) took months to implement at OpenAI — "many more advances remain undiscovered" suggests enormous whitespace for startups

---

## Verbatim Quotes (from summaries, attributed)

- "From the outside, it feels like everything's accelerating. From the inside, it looks different."
- "We solved a big chunk of reasoning. Now the challenge is scaling it, which is very hard."
- "Progress won't slow — it'll just change direction."
- "The techniques that give that to you in terms of thinking harder also apply to taking action in the real world."
- "You really need a lot of reliability in order for you to be willing to wait five minutes or five hours for something to happen."
- "If you look back from 2035, we're not going to see anything new and fundamental."
- "Some other startup can come in and compete that away" [on agent commodity pricing using frontier models]

---

## VERSO RELEVANCE

### [SHARPENS §5.5 evals] Reliability as the agent trust contract, not a capability ceiling

McGrew's argument is not "make agents smarter" but "make agents predictable enough that users rationally commit to wait." This sharpens Verso's evals story: the purpose of evals is not improving accuracy scores — it's establishing the reliability floor that unlocks user delegation. The eval harness should surface reliability metrics (success rate, failure mode distribution) not just correctness scores.

**Verdict**: Sharpens the why behind evals-first. No overkill.

### [CONFIRMS §6.4 model] Pre-training plateau confirmed by the person who ran it

McGrew ran GPT-4 and o1 at OpenAI. His claim that pre-training faces "exponential compute requirements for marginal gains" and the axis has shifted to architectural improvements and test-time compute confirms Verso's §6.4 model layer assumptions: don't bet on pre-training getting linearly better, do bet on reasoning/test-time compute expanding agent capability. Cross-model failover and role-tiered models remain the right tactical posture.

**Verdict**: Strong confirmation from the most credible possible source.

### [SHARPENS §12 positioning] Agent commodity pricing → context-extraction infra as moat

The framing that agents will be priced at compute cost and frontier models commoditize agent capability directly supports Verso's positioning: the moat is the harness, not the model. But McGrew adds precision — the specific moat is enterprise context extraction and integration infrastructure. Verso's §12 positioning should emphasize the context engineering layer as the durable differentiation, not the loop itself.

**Verdict**: Sharpens the counter-positioning. The competitor to worry about is the context-integration platform, not the loop library.

### [NEW-IDEA] "Obvious improvements took months to implement" as whitespace signal

McGrew notes that adding tool use to chain-of-thought reasoning took months after the capability was available. This is a consistent pattern: there is always a large gap between capability emergence and systematic product-side exploitation. Verso can exploit this gap specifically around test-time compute and reasoning — systematic harness support for extended reasoning, parallel sampling, and judge-panel selection is likely still in the gap.

**Verdict**: Actionable whitespace, not overkill.

### [CONFIRMS §5.1 loop] Test-time compute as agent reliability axis

McGrew's framing that reasoning/test-time compute is "the new scaling axis" confirms the direction of Verso's sampling-over-completions approach (parallel runs + judge selection, as validated by Parahelp). The loop design should make test-time compute investment first-class: budget parameter, sampling count, judge integration.

**Verdict**: Confirms loop design direction.
