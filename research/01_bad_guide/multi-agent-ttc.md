# Multi-agent + test-time compute

## Scaling Test-Time Compute to Multi-Agent Civilizations — https://www.youtube.com/watch?v=ddd4xjuJTyg — transcribed

**Speaker:** Noam Brown (OpenAI, multi-agent team lead). Latent Space podcast, 2025.

### Background: where reasoning came from

- Noam's arc: poker AI (Libratus — first superhuman no-limit Texas hold 'em AI) → Hanabi → Cicero (Diplomacy, 2022, top-10% human players at 2.7B params) → reasoning models (O1/O3 at OpenAI)
- Core insight from poker/Hanabi/Diplomacy: "having the models think before acting made a huge difference in performance — like orders of magnitude. 1,000 to 100,000 times is the equivalent of a model that's 1,000 to 100,000 times bigger."
- In late 2021, Noam told Ilya he thought AGI timelines were long because reasoning hadn't been cracked for general LMs. Ilya agreed the reasoning paradigm was needed but felt it might not be that hard to figure out. OpenAI had ongoing RL research internally (rumored "GPT-0" codename) leading to the O-series strawberry models.
- The reasoning paradigm was recognized as decisive around October–November 2023 internally ("very conclusive signs of life"). What OpenAI did right: recognized it for what it was and scaled investment heavily. Was controversial internally — investing in reasoning came at expense of pre-training-focused compute.

### Test-time compute: ceiling and efficiency

- Pre-training scaling analogy: "pre-training took ~5 years from GPT-1 to GPT-4 scaling; test-time compute is on a similar arc, 5-year window from O1 to wherever."
- Two soft barriers: (1) cost — thinking for longer costs more, soft ceiling on spend; (2) wall-clock time — if model thinks for 3 weeks to answer, iteration loop becomes 3+ weeks, which is the strongest case for long AGI timelines. "A lot of experiments have to run serially — you can't fully parallelize them."
- Key underappreciated point: O3 is not radically longer-thinking than O1 preview, but it's way better. Reason: "it's becoming better at thinking — more capable within the same compute envelope." The gain is mostly quality-per-token, not just more tokens.
- On deep research as proof TTC generalizes beyond verifiable domains: "we've released deep research and people can try it out — it's very clearly a domain where you don't have easily verifiable metric for success, and these models do extremely well. I'm surprised this is still a common perception [that TTC only works in math/code]." People can tell the difference between good and bad research reports — that's sufficient signal to build the improvement loop.

### System-one / system-two analogy — what transfers and what doesn't

- The analogy maps reasonably: pre-training builds "system one" intuition; reasoning is "system two" deliberation.
- What doesn't transfer: "you need a certain level of system one capability to benefit from system two." If you try reasoning on GPT-2, chain-of-thought got almost nothing. "If you ask a pigeon to think really hard about chess for a thousand years, it's not going to play better."
- Information retrieval doesn't benefit from TTC: "if someone asks when a person was born and you don't have web access, you either know it or you don't — you can think for a long time but won't produce the fact." Spatial reasoning like tic-tac-toe benefits strongly from TTC. GeoGuessr visual reasoning benefits. Basic image recognition probably benefits less.
- More system-one knowledge = more efficient system-two. Humans who've built strong intuition in a domain apply system two faster and more accurately. Models too.

### Harnesses and scaffolding: Noam's explicit position

- "The ideal harness is no harness. Harnesses are a crutch that eventually we're going to move beyond."
- Historical example: "before reasoning models, there was all this work engineering agentic systems with lots of GPT-4o calls to get reasoning behavior. Then reasoning models arrived and you just give them the same question without scaffolding and they do it — and in many ways the scaffolding made it worse."
- Same fate predicted for model routers: "we said pretty openly we want to move to a world with a single unifying model — then you shouldn't need a router. Routers will eventually go away."
- Direct advice to builders: "keep in mind the field is evolving very rapidly. Things will change in 3 months, let alone 6. That might require radically changing these things or tossing them out completely. Don't spend 6 months building something that might get tossed in 6 months."
- Exception — reinforcement fine-tuning (RFT): "the data you collect for RFT is useful as models improve. Future more-capable models can still be fine-tuned on your domain data. RFT complements model scaling rather than getting washed away by it." Environment + reward model design is durable investment.

### Multi-agent: the "civilizations" thesis

- Noam's framing: "humans occupy what people call a narrow band of intelligence, but I actually think it's quite broad. Anatomically identical cavemen didn't put a man on the moon. The difference is thousands of years, billions of humans cooperating and competing, building up civilization. Today's AIs are the cavemen of AI. If you have them cooperate and compete across billions of agents over long periods of time — building up a civilization — the things they would be able to produce would be far beyond what's possible today."
- What's misguided about current multi-agent field: "a lot of approaches have been very heuristic and haven't really followed the Bitter Lesson approach to scaling and research." OpenAI's approach to multi-agent is "very different from how it's been done historically and how it's being done today by other places."
- Two motivations for multi-agent at OpenAI: (1) scaling TTC to extreme durations (thinking for hours, days, longer); (2) cooperative + competitive multi-agent emergent behavior.
- Self-play convergence properties: works cleanly in **two-player zero-sum games** — self-play converges to minimax equilibrium (the GTO unbeatable policy). "This is exactly what AlphaZero does; Go policies are now incomprehensible to humans."
- Self-play breaks down outside two-player zero-sum: in Diplomacy (7-player mixed cooperation/competition), minimax is not the right target; game-theory-optimal policies are defensive and produce "weird behavior." In math, "pose difficult questions / other model solves them" looks like zero-sum but isn't — a poser can just ask 30-digit multiplication which is hard but not interesting or in the direction you want progress.
- AlphaGo analogy breakdown: "pre-training → MCTS/reasoning → self-play looks like the path. But the self-play step for language tasks is far more nuanced than for Go. What are you optimizing for? That's an open question."
- The civilization metaphor implies: the value is emergent over long timescales and many agents — not from a fixed system-prompt multi-agent topology but from an environment that allows compounding coordination.

### Exploitative vs. GTO: lessons for multi-agent design

- GTO (game-theory optimal) = unexploitable but leaves money on the table against weak opponents. Exploitative = more profitable but creates exploitable holes.
- In Diplomacy (collaborative + competitive), GTO failed. Needed to model other players and adapt. "It's like being at a table where everyone speaks French — you don't keep talking in English."
- Cicero's approach: conditioned on concrete actions → very steerable, interpretable. "A lot of AI safety researchers reached out and said this is potentially a really good way to achieve safety — there's a reasoning system that steers the language model's interactions."
- For future cooperative-competitive AI, adapting behavior to specific other agents (opponent modeling) is unavoidable. This is distinct from environment modeling. Noam shifted view over time: used to believe you must explicitly model other agents; now thinks with sufficient scale, theory-of-mind emerges implicitly.

### Coding agents and current practical state

- Noam's stack: WinSurf + Codex (OpenAI). Uses Codex for anything he'd normally code. "Give it a task that's self-contained, it goes off and comes back 10 minutes later with a pull request."
- For pair-programming flow (tighter loop), prefers GPT-4.1 class fast models. For long-horizon background tasks, O3/Codex class reasoning models.
- Key frustration: "these models are geniuses but it's their first day on the job. Even the smartest person on day one isn't as useful as you'd like. Getting more 'experience' — acting like someone who's been on the job 6 months instead of one day — would make them a lot more useful. But that's on us to build."
- Main missing link in software dev cycle: PR review. "Codex doesn't do it. It could. That's rate-limiting the amount of software you can iterate on."
- Expects expansion beyond software: "anybody doing remote work kind of jobs — I think the breadth of what these models can do will expand over time."

### Model architecture notes

- World models: models implicitly develop better world models as they scale. "I don't think it's something you need to explicitly model — these models develop it with scale." (Shifted from earlier view that agents required explicit opponent/world models.)
- Diffusion vs. autoregressive: declined to comment on diffusion-based reasoning as potentially directionally interesting; prefers not to foreclose research directions.
- Mid-training: "between pre-training and post-training — adding more to the models in interesting ways. You never interact with a raw pre-trained model; they go through mid-training then post-training."

---

## AI Agents and the Path to AGI — https://www.youtube.com/watch?v=eW7rUtYHD9U — transcribed

**Speaker:** Bob McGrew (ex-Chief Research Officer, OpenAI; ex-Palantir). Interviewed by Gary Tan (YC).

### Pre-training scaling wall and the TTC transition

- "In the big picture, we're reaching the bottleneck for pre-training and data. But we have this new mechanism with reasoning and test-time compute." Framed as an S-curve transition, same as Moore's law consisting of successive S-curves: "Dennard scaling breaks, Nvidia finds another mechanism, the overall exponential continues."
- The five-step OpenAI AGI levels: chatbots → reasoners (here now) → agents → innovators → organizations. "Reasoners are here. Innovators — hooking O3 Pro to a biolab for autonomous exploration of scientific hypotheses — is close."
- Getting from 90% to 99% correct, or 99% to 99.9%: "historically requires an order of magnitude increase in compute. We used to only be able to do that by training bigger models. With reasoning we can now do it by letting models think longer." This is the direct path to higher-reliability agents.
- "What reasoning is is the ability for a model to have a coherent chain of thought steadily making progress on a problem over a long period of time — and the techniques that give you that in terms of thinking harder also apply to taking action in the real world / virtual world."

### Agents: the reliability threshold

- "Agents have always been possible but never quite good enough. You really need a lot of reliability — the thing that prevents people from trusting an agent is how often that action is the correct one versus wrong one."
- "I think that is now in sight" — reasoning models move the reliability dial in the direction needed to justify delegating multi-step tasks. "You need to be willing to wait 5 minutes or 5 hours for something to happen — it's got to actually work at the end."
- Adoption mystery: even after GPT-4 class capabilities (code, images, conversation), productivity stats don't show the effect. "This is a really deep mystery — why is AI adoption so slow relative to what we thought in 2018?" Hypothesis: the missing piece is not intelligence or data but software — "the UI, the workflow integration, the tool that packages AI for a particular person's specific problem."
- Palantir forward-deployed engineer analogy: "you're sitting next to the customer, watching how they do something, building the perfect software for that very person — not an off-the-rack tool they have to figure out." That model — deeply specialized software that re-imagines the workflow rather than just automating the old one — is what unlocks AI adoption.

### TTC enabling agents specifically

- The loop: reasoning → longer reliable chains of thought → agents that can act over long horizons without going off the rails. Not a separate research track but the same capability unlocking agentic behavior.
- "It's going to unlock the possibility of agents to do actions on your behalf — which has always been possible but just never been good enough."
- Science bottleneck: "we're probably going to have a model that can explore scientific hypotheses and figure out how to run experiments before we have a model that can actually run the experiments themselves. Innovators come before experiment-doers — we'll automate the scientist before the lab technician."
- Robots are on the same S-curve but 5 years behind LLMs. "Robotics companies now are where LLM companies were 5 years ago. In 5 years we'll see the ChatGPT moment for robotics."

### Distillation and the build-with-frontier-first rule

- Large models → smaller distilled models: "the big Frontier labs have figured out the tricks to take big models and train a model that is almost as good but much smaller and faster. Sonnet vs Haiku, Gemini vs Flash, O1 vs O1-mini — every lab is focused on this."
- Startup advice: "start with the very best model you can — your startup is only successful if it exploits something about AI that is going to be on the frontier. Get it working. Then use distillation, try prompting a dumber model, have the frontier model train the smaller model." Most important thing is time-to-value; don't pre-optimize for cost before you've validated the product.

### Future roles in an AI-heavy world

- Two remaining high-value roles: **lone genius** (Alec Radford archetype — brilliant individual idea with AI as leverage multiplier) and **manager** (CEO of a firm that's mostly AI — orchestrating, directing, judging).
- Both roles involve humans setting direction and evaluating outcomes, not executing mechanical tasks. "The AI is your life coach, your assistant — but it needs huge amounts of context about you, your goals, your preferences." Deep personalization is the unsolved product hole.
- AI as personalized proxy: "Gary's AI bot — if I want to know what Gary's thinking I could just ask your AI bot, get a good enough answer and go about my day." Requires AI seeing Slack, Gmail, all productivity tools.

### OpenAI research culture notes (relevant for scaling insights)

- Early bet on scale over many small experiments: "one big experiment is much more valuable than 100 small ones" — Ilya insight from 2016-17 founding emails, differentiator from Google Brain's approach.
- Startup culture vs. academic lab culture: "OpenAI functions like a startup — make hard calls about resource allocation, pool compute, move fast." Other labs tried to replicate later. Key cultural piece: collective credit ("cite as OpenAI" on early robotics papers) eliminated infighting.

---

## → Verso implications

- **Harnesses are tactical, not architectural.** Noam Brown explicitly says scaffolding that compensates for model limitations gets washed away when models improve. Verso's design thesis — simple ReAct loop + first-class tools + evals — is directionally correct. Don't build what model scale will absorb. The durable layer is: correct loop structure, tool integration contract (MCP), memory persistence, eval hooks.

- **The "genius on day one" problem IS the memory/context problem.** Noam frames the biggest current frustration as lack of "job experience" — the model solves the same kind of task from scratch each time without building project-specific intuitions. Verso's memory primitives (short-term, episodic, long-term/KV) directly address this. Make memory a first-class concern, not an afterthought plugin.

- **TTC at extreme durations requires async orchestration natively.** Models will think for hours, days, longer. A framework that assumes synchronous request/response will break. Verso needs first-class support for: (a) background task execution, (b) checkpoint-resume (the "durable execution" escape hatch mentioned in the thesis is actually mandatory for long-running TTC tasks, not optional), (c) streaming partial results back while deliberation continues.

- **Multi-agent value is NOT from graph topology — it's from parallelism and independence.** Noam's critique: current multi-agent approaches are "heuristic" and not Bitter Lesson-compliant. The civilization metaphor implies value from many independent agents iterating over long time vs. a fixed orchestration graph. Verso's multi-agent stance: opt-in, breadth-first parallelism (fan-out on independent subtasks, not a fixed DAG). Resist adding complex orchestration graphs as defaults; they're the scaffolding that gets washed away.

- **Self-play / competitive multi-agent is a research track, not a product primitive.** The self-play convergence result (minimax equilibrium) is clean only in two-player zero-sum games. For general tasks (writing, research, code review), what the competing agents optimize toward is undefined. Verso should not expose "adversarial self-play" as a first-class pattern — too much rope. Collaborative parallel fan-out is the safe, high-value primitive.

- **GTO policy → exploitative adaptation is the right mental model for multi-agent coordination.** In cooperative/competitive tasks (most real-world multi-agent work), a fixed unexploitable strategy leaves value on the table. Agents that model other agents (or the user's actual behavior pattern) and adapt do better. Verso's agent loop should support: per-agent persona/instructions, shared context with configurable visibility, result synthesis with explicit attribution. Don't just average outputs; design for agents that see each other's partial outputs and can build on them.

- **Reliability threshold is the agent adoption gate.** Bob McGrew's "90%→99%→99.9% requires order-of-magnitude compute" framing means Verso's eval primitives are adoption infrastructure. Evals that measure per-step reliability and surface regressions early are how you cross the reliability threshold. Build evals as a first-class loop, not a post-hoc test suite.

- **Start with frontier models; distillation is the cost optimization second step.** McGrew's startup advice directly: start with the best available model, validate product, then distill/route to cheaper models for specific distributions. Verso should make it easy to swap models per agent or per task — model-agnostic agent definitions with a clear model binding layer. Don't bake in any assumption about which model is "the" model.

- **The software integration gap is the adoption problem.** McGrew's "forward deployed engineer" framing: AI adoption is bottlenecked not by model capability but by lack of software that re-imagines the workflow for a specific person/domain. Verso's value prop should be: batteries-included opinionated defaults (tool contracts, memory, evals) that let developers build the workflow-reimagination layer quickly, not just the raw loop.

- **Theory-of-mind / agent modeling emerges at scale; don't bake in brittle heuristics.** Noam shifted from "you must explicitly model other agents" to "scale + capability produces this implicitly." For Verso: design the multi-agent API so explicit agent-modeling is possible (a tool an agent can call to introspect another agent's state/outputs) but not required. The default path should be clean shared context + independent reasoning; explicit modeling is an opt-in extension.

- **Wall-clock time is the TTC scaling bottleneck.** For Verso's orchestration layer: this is the argument for maximum parallelism at the multi-agent level. If one agent is thinking for 3 hours, other agents should be doing parallel work. The framework should schedule independent sub-tasks concurrently and synchronize only at dependency boundaries — not a linear pipeline.
