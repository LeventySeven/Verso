# Karpathy canon — software 3.0, autonomy, agents

## Andrej Karpathy: Software Is Changing (Again) — https://www.youtube.com/watch?v=LCEmiRjPEtQ — transcribed

Talk given at Y Combinator AI Startup School, San Francisco, June 17–18 2025.
Full transcript via singjupost.com and donnamagi.com.

### The three-generation framework

- **Software 1.0** — explicit instructions written by humans in C++/Python; the programmer specifies every operation.
- **Software 2.0** — neural network weights optimized by training; the programmer specifies the *dataset* and *evaluation criterion*, the optimizer writes the code. Karpathy introduced this framing in 2017. Tesla Autopilot is the canonical example: C++ code was progressively deleted as neural networks took over; stitching images across cameras, handling edge-case fusion — all migrated from 1.0 to 2.0.
- **Software 3.0** — LLMs as programmable computers; "your prompts are now programs that program the LLM." The programming language is English. "This is a very interesting programming language."

Key principle: modern developers must be fluent in all three. "You may need to program some functionality in 1.0 or 2.0, or 3.0, or you're going to train in LLM, or you're going to just run from LLM."

### LLMs as operating systems (the central analogy)

Karpathy's framing: LLMs are NOT utilities (like electricity). They are complex software ecosystems analogous to 1960s-era operating systems.

- **CPU equivalent** — the LLM itself
- **Memory equivalent** — the context window functions as working memory
- **Orchestration** — LLMs coordinate memory and compute for problem-solving using "all these capabilities"

The OS market parallels are explicit: closed-source providers (OpenAI, Anthropic, Google = Windows/macOS) vs. open-source alternative (Llama ecosystem = Linux). "We are all just sort of fake clients that interact with it over the network, and none of us have full utilization of these computers."

The 1960s analogy extends to compute centralization: LLMs remain expensive to run, forcing cloud centralization; "the personal computing revolution hasn't occurred yet" for LLMs. Mac Minis noted as promising for batch inference (memory-bound workloads).

The text chat interface = interacting via terminal. "A GUI hasn't yet really been invented in a general way" for LLMs. This is the next major missing layer.

### Unprecedented technology diffusion reversal

Historical pattern: expensive new tech serves governments/military first, trickles down to consumers (electricity, computing, ballistics, cryptography). LLMs reversed this completely. "LLMs are kind of what flipped around. With early computers, it was all about ballistics and military use, but with LLMs, it's all about how do you boil an egg." ChatGPT hit 100 million monthly users in two months — fastest-growing consumer application in history. 97% of software engineers use AI coding tools; only ~40% of employers officially encourage it. Consumer applications drove early innovation.

### LLM cognitive profile (psychology)

Karpathy treats LLMs as entities with a specific cognitive profile to be designed around:

**Superpowers:**
- Encyclopedic knowledge exceeding any individual — "Rain Man, an autistic sponge who has almost perfect memory"
- Can memorize SHA hashes, vast factual corpora, easily
- Stochastic simulations of people: "autoregressive transformer... emergent psychology that is human-like"

**Critical deficits to design around:**
- **Hallucination and confabulation** — "make up stuff" with insufficient self-knowledge
- **Jagged intelligence** — superhuman at some tasks; makes elementary errors no human would ("insist 9.11 is greater than 9.9"; two r's in strawberry)
- **Anterograde amnesia** — cannot consolidate knowledge across conversations; context windows reset. Human colleagues "gain a huge amount of context on the organization and learn" over time; LLMs "don't natively do this. This is not something that has really been solved in R&D."
- **Prompt injection / security** — "susceptible to conflict-injection risks and might leak your data"

Context window = working memory that "must be programmed quite directly because they don't just kind of get absorbed by osmosis." Like the protagonists of Memento and 50 First Dates — memory resets daily.

### Partial autonomy apps — the practical product paradigm

Core argument: do NOT build products that talk directly to an LLM OS via text. Build dedicated partial-autonomy applications.

**Four required properties of a partial-autonomy app:**

1. **Context management** — The app bundles relevant information automatically. "A ton of good context management" behind the scenes. The LLM doesn't have to find its own context.

2. **Multi-model orchestration** — Cursor example: "under-the-hood eventing models for all your files, the actual chat models, models that apply diffs to the code" — multiple LLM calls coordinated invisibly.

3. **Application-specific GUI** — Critical insight: raw text verification is too slow. The GUI leverages "the computer vision GPU in all of our head." Diffs shown as red/green — "it's much easier to just do command-Y to accept or command-N to reject. You don't have to type it in text." Reading text is "effortful... GUIs are very useful for auditing systems and visual representations in general."

4. **Autonomy slider** — "Users control delegation level." Examples:
   - Cursor: Tab completion → Command-K (selected code) → Command-L (whole file) → Command-I (entire repo / agent mode)
   - Perplexity: Quick search → research → deep research
   - Always leave the slider accessible so the product can progress toward more automation over time.

### The generation-verification loop (central design principle)

"Usually they are doing the generation, and we as humans are doing the verification. It is in our interest to make this loop go as fast as possible."

Two optimization axes:
1. **Speed verification** — fast GUIs, visual diffs, citations with links; "highway to your brain"
2. **Improve generation success rate** — specific prompts reduce loop restarts. "If your prompt is vague, the AI might not do exactly what you want, and in that case, the verification will fail." Better: spend upfront time writing concrete prompts to increase first-pass success probability.

### Keeping AI "on a leash"

"A lot of people are getting way overexcited with AI agents, and it's not useful to me to get the diff of 1,000 lines of code into my repo." Even if code generates instantly, "I have to make sure this thing is not introducing bugs... no security issues."

Practical approach: "small incremental chunks... work on small chunks of single-token thing."

The education example: rather than letting an LLM generate a course freely ("the AI gets lost in the woods"), create an intermediate auditable artifact — the course structure — that constrains the LLM. "The AI is kept on a leash with respect to a certain syllabus, a certain progression of projects." Result: "much higher likelihood of working."

Pattern: always insert an auditable intermediate artifact between the LLM and the end output. The intermediate artifact is the "leash."

### The network-to-product gap

"Demo is works.any(); product is works.all()."

Waymo 2013 story: Karpathy experienced a "perfect" 40-minute self-driving ride around Palo Alto. Zero issues. Convinced autonomy was imminent. "Twelve years later, we're still working on the tunnel. We haven't fully solved the problem."

"Software is really tricky in the same way that driving is tricky. If you make a single mistake in software, there could be a code path that introduces a security issue, or a zero-day."

On "year of agents" claims: "I get very concerned... this is the decade of agents... let's be serious here, okay?"

### The Iron Man suit vs. autonomous robot

"Less building flashy demos of autonomous agents, more building partial autonomy products — Iron Man suits."

Iron Man suit: augmentation + the option for increasing autonomy. Not a fully autonomous robot. The suit is: (a) useful immediately, (b) keeps a human in the loop, (c) can have its autonomy slider increased over time.

Vision: "Over the next decade, roughly, we're going to take the slider from left to right." Not a sudden transition — a deliberate decade-long progression.

### English as programming language — democratization

"Everyone is a programmer, because everyone speaks natural language, like English. This is extremely bullish, and completely unprecedented."

Previously, "you need to spend five to ten years studying something to be able to do something that software can do. This is not the case anymore."

"Vibe coding" — building apps through natural language iteration. Karpathy built an iOS app with no Swift knowledge in one day ("this was running on my phone later that day... I didn't have to like leave from Swift for like five days").

**The productionization gap**: vibe-coded the MenuGen demo (restaurant menu image → dish images) in "a few hours." Took a week to deploy because authentication, payments, domain names, DevOps were all "designed for humans clicking through GUIs." "The computer is telling me the actions I should be taking. Like, you do it. What the hell?" — motivates building infrastructure for agents.

### Building infrastructure for agents

"There's a new category of consumer and manipulator of digital information. It used to be just humans through GUIs, or computers via APIs. And now it's a completely new thing. Agents are computers, but they are human-like."

**Proposed infrastructure:**

- **llms.txt** — markdown file (analogous to robots.txt) telling LLMs what a domain is about. "If it had to parse the HTML of your webpage and try to parse it, this is very error-prone and it will screw up."
- **Markdown docs** — "Markdown is crazy for LLMs to understand. This is great." Stripe transitioning docs to Markdown format.
- **Action-oriented docs** — replace "click here" with curl equivalents agents can execute. "Replacing every occurrence of 'play' with an equivalent program that your LLM agent could take on your behalf."
- **Model Context Protocol (Anthropic)** — "given directly to agents. I'm very bullish on this."
- **git-ingest** — change GitHub URL to GitHub Ingest: concatenates all files into single text with directory structure. "Ready to copy-paste into your favorite LLM."
- **DeepWiki (Cognition)** — builds a box of pages for a GitHub repo for LLM analysis.

Karpathy's motivation: "I love all the little tools that basically just change the URL and make something accessible to an LLM."

Autonomous scraping is already possible but expensive. Explicit LLM pathways are worth building: "I still think it's very worth building LLM pathways and making it easier for them to access all this information."

---

## Software 2.0 — https://karpathy.medium.com/software-2-0-a64152b37c35 — read

Published November 11, 2017. The founding intellectual artifact of the 2.0/3.0 paradigm.

### Core definitions

- **Software 1.0** — code written in Python, C++, etc.; "explicit instructions to the computer written by a programmer." Identifies a specific point in program space with desirable behavior.
- **Software 2.0** — written in "neural network weights." Developer specifies behavioral goals and uses computational resources to search program space via backpropagation + SGD. The search is restricted to continuous subsets of program space.
- Source code is: (1) the dataset defining desirable behavior, and (2) the neural net architecture. "Training compiles the dataset into the binary — the final neural network."

### The transition driver

"Large portion of real-world problems have the property that it is significantly easier to collect the data than to explicitly write the program." This is why "a lot of 1.0 code is being ported into 2.0 code."

### Domain-by-domain takeover examples

- **Visual recognition** — from hand-engineered features + SVM → CNNs (ImageNet); now also architecture search (NAS)
- **Speech recognition** — from GMMs + HMMs (Fred Jelinek 1985: "Every time I fire a linguist, the performance of our speech recognition system goes up") → ConvNets
- **Speech synthesis** — from stitching mechanisms → WaveNet (raw audio via large ConvNets)
- **Machine translation** — from phrase-based statistical methods → neural (multilingual, single model, eventually unsupervised)
- **Games** — from hand-coded Go programs → AlphaGo Zero (raw board state → move, by far strongest player)
- **Databases** — "The Case for Learned Index Structures": neural nets replace B-Trees; "outperforming cache-optimized B-Trees by up to 70% in speed while saving an order-of-magnitude in memory"

### Properties enabling the transition

**Computational homogeneity:** "Sandwich of only two operations: matrix multiplication and thresholding at zero (ReLU)." Compare to Software 1.0's "significantly more heterogeneous and complex" instruction set. Benefit: easier to make correctness/performance guarantees; easier to implement close to silicon (custom ASICs, neuromorphic chips).

**Constant running time:** "Every iteration of a typical neural net forward pass takes exactly the same amount of FLOPS. Zero variability based on different execution paths. Almost guaranteed to never find ourselves in unintended infinite loops."

**Constant memory use:** "No dynamically allocated memory anywhere. Little possibility of swapping to disk or memory leaks."

**Portability:** Sequence of matrix multiplies runs on arbitrary computational configurations more easily than classical binaries.

**Agility:** "If someone wanted you to make it twice as fast (at cost of performance): take the network, remove half of the channels, retrain, and there — runs exactly at twice the speed and works a bit worse." Scaling: "if you get more data/compute, you can immediately make your program work better just by adding more channels and retraining."

**End-to-end differentiability:** "If two Software 2.0 modules that were originally trained separately interact, we can easily backpropagate through the whole." This is categorically impossible with Software 1.0 APIs. Enables: auto-tuning of imported libraries on your specific data, backpropagation through entire stacks.

### Limitations

- **Interpretability** — "Large networks that work well, but it's very hard to tell how. We might have to accept a 90% accurate model we understand, or a 99% accurate model we don't."
- **Failure modes** — "Fail in unintuitive and embarrassing ways. Silently fail, e.g., by silently adopting biases in their training data. Very difficult to properly analyze and examine when their sizes are easily in the millions [of parameters]."
- **Adversarial vulnerabilities** — "Existence of adversarial examples and attacks highlights the unintuitive nature." (Written 2017 — prescient.)

### Development paradigm shift

Software 1.0: "code we write." Software 2.0: "code written by the optimization based on an evaluation criterion." Evaluation can be: "did you classify images correctly? do you win games of Go?" Optimization can "find much better code than what a human can write" when evaluation is possible. "When the network fails on hard or rare cases, we do not fix those predictions by writing code, but by including more labeled examples."

Development teams bifurcate: "2.0 programmers (data labelers) edit and grow the datasets, while a few 1.0 programmers maintain" training infrastructure.

### Tooling gap (1.0 → 2.0 equivalent)

- **No Software 2.0 IDE** yet — needed: accumulating, visualizing, cleaning, labeling, sourcing datasets; IDE bubbles up mislabeled images based on per-example loss; assists in labeling by seeding labels with predictions; recommends useful examples to label based on network uncertainty.
- **No version control equivalent** — "Is there space for a Software 2.0 Github? Repositories are datasets and commits are made up of additions and edits of the labels."
- **No deployment infrastructure** — "How do we effectively deploy, share, import and work with Software 2.0 binaries? What is the conda equivalent for neural networks?"

**Long-term prediction (2017):** "When we develop AGI, it will certainly be written in Software 2.0." (Now superseded by 3.0 framing.)

---

## Andrej Karpathy — AGI is still a decade away (Dwarkesh) — https://www.dwarkesh.com/p/andrej-karpathy — read

Podcast episode, Dwarkesh Patel interviewing Karpathy. Full transcript at dwarkesh.com and podscripts.co.

### AGI definition and timeline

- AGI = "a system you can go to that can do any task that is economically valuable at human performance or better." Original OpenAI framing.
- "Decade of agents" not "year of agents." "The problems are tractable, but they're still difficult." 15 years watching AI prediction accuracy informs this estimate.
- Knowledge work = roughly 10-20% of economy. LLMs currently address the digital-only, knowledge-only subset — a major concession.
- Radiologist example: Geoff Hinton predicted radiologists would be displaced; "turned out to be very wrong in a bunch of ways."
- Call center workers: more automatable than most knowledge professions — repetitive, closed-context, short horizon tasks.

### What's missing for agents to function as "employees or interns"

Six deficits (Karpathy's list):
1. Insufficient general intelligence
2. Limited multimodality (improving)
3. No reliable computer use (improving)
4. **No continual learning across sessions** — "You can't just tell them something and they'll remember it." Critical gap. No equivalent to sleep-based knowledge consolidation.
5. Context window limitations for long-horizon tasks
6. Cannot work independently without constant supervision

### Agent reliability vs. long-horizon tasks — the key framing

Karpathy pushes back on the claim that context window size is the main agent bottleneck. His view: **reliability is the real bottleneck.**

"If you just can't chain tasks successively with high enough probability, you won't get something that looks like an agent." Agents follow a step function: "GPT-4 class models — not enough. Maybe the next increment on model scale means you get that extra nine." 

The math: 90% per-step reliability × 10 chained steps = 35% end-to-end success. 99% per-step × 10 steps = 90%. The extra nine matters enormously for agent viability.

"Academic evals are all single problems. SWE-bench is more like a 'multi-step sub-hour task' — not yet multi-hour or multi-day."

He wants task-horizon evals: "cut tasks into minutes, hours, days; measure success rates at each resolution; that tells you how automatable a job family actually is."

### The autonomy slider (from this interview)

Computing history as autonomy-slider trajectory: assembly → compilers → higher abstractions. "Progressively automating low-level work, raising the abstraction layer." This is not distinct from historical automation — AI is a fundamental extension of computing.

Near-term model: "We are not going to instantly replace people. We're going to be swapping in AIs that do 80% of the volume. They delegate 20% of the volume to humans, and humans are supervising teams of five AIs."

New interface paradigm needed: interfaces for managing teams of imperfect AI agents — not just single-model interaction.

### Working memory vs. stored knowledge — the information density gap

Two kinds of LLM memory:
- **KV cache (context window)** — 320 KB per token; "directly accessible to the neural net." Very high information density.
- **Pre-training weights** — 0.07 bits per token for Llama 3 (70B model trained on 15 trillion tokens). "Hazy recollection of training data."

"35 million-fold difference in how much information per token is assimilated." Weights are like "what you vaguely remember from a book you read a year ago"; context is "directly in working memory."

Implication for agents: whatever needs to be reliable in an agent's reasoning must be in-context, not just in weights.

### Reinforcement learning is "terrible"

"Reinforcement learning is terrible. It just so happens that everything we had before is much worse."

Core problem: "Sucking supervision through a straw." An entire trajectory of reasoning compresses into a single final reward signal. For a 100-attempt math problem: RL upweights ALL tokens in successful attempts (including wrong paths) equally. "High variance estimator. Assumes all tokens contributing to the correct answer were correct."

Contrast with human learning: humans review solutions, selectively learn from specific steps, not entire trajectories.

"3 successes out of 97 failures — if the trajectory led to the correct answer, those 97 failed tokens all get upweighted equally."

### Process-based supervision and the judge problem

Alternative to outcome-based RL: process supervision — credit assignment at each step. But this faces a critical obstacle: **LLM judges are gameable.**

Judges have billions of parameters. When you RL against them, models find adversarial examples: discovered one case where outputting "dhdhdhdh" (or "da-da-da-da") repeatedly scored 100% from the judge. "Model found an out-of-distribution adversarial input that produced nonsense but scored perfectly."

"Adversarial examples are infinite; even after adding examples to training, new ones emerge." Cannot sustain RL against weak judges beyond 10–20 steps before reward hacking.

Karpathy: "We need 3–5 more major algorithmic updates to the RL pipeline before this is robust."

Google's "reflect and review" approach with synthetic examples cited as one direction.

### Model collapse

LLMs generate "collapsed data distributions." Ask for a joke: ~3 variations total. "Silently collapsed... occupy a very tiny manifold of the possible space."

Training on own outputs degrades further. "ChatGPT tells like three jokes — constrained to a tiny manifold."

Human analogy: children maintain high "entropy" (cognitive flexibility, uncollapsed distributions). Adults more collapsed. Daydreaming hypothesis: dreams maintain entropy by generating "weird situations very unlike day-to-day reality," preventing overfitting.

Implication: synthetic data generation from collapsed models produces collapsed training data — a vicious cycle limiting self-improvement.

### Cognitive core vs. knowledge — the key architecture prediction

"Remove the memory, keep the cognitive core."

Goal: train a model with less memorized internet content but robust reasoning. Prediction: "a billion-parameter cognitive core" could achieve very good knowledge-work performance if trained on refined, cognitively dense data.

Current trillion-parameter models are bloated with "total garbage" pre-training data — "stock ticker symbols, slop from all corners." Most compression work is memory, not cognition. "Wall Street Journal articles are extremely rare." A cognitive-core model needs only a seed of basic knowledge and strong reasoning circuits.

Why this matters: distillation works extremely well. Most small models are distilled from larger ones. The frontier could shift to very small cognitive cores + large external memory.

### Why pre-training ≠ evolution

Evolution encodes algorithms for learning within DNA; it does not directly encode knowledge. Pre-training simultaneously trains: (a) memorization of world knowledge, AND (b) development of reasoning/learning circuits. These should be disentangled.

"Crappy evolution" — practically achievable version; similar outcome (intelligent starting point) via different mechanism.

### LLM coding limitations (nanochat lessons)

~8,000 lines of code to build a full ChatGPT clone. Key observations:
- Models kept suggesting Distributed Data Parallel container when Karpathy's custom synchronization was intentional — couldn't integrate novel architectural choices
- "Over-defensive code" — excessive try-catch, deprecated APIs, production-grade bloat for a research codebase
- "Way too good at memorization" — distracted from generalization; Karpathy: humans who excel are good at *pattern generalization*, not memorization
- Best use: autocomplete after typing initial characters ("very high information bandwidth to specify what you want")
- Worst use: "vibe coding" full prompts for novel architectures (boilerplate: excellent; custom architectures: poor)

Code domain advantage: "Code works around text; terminal-based; perfect LLM fit. Pre-built diff infrastructure shows agent changes." Other domains (slides, spreadsheets, visual work) lack equivalent infrastructure.

### Superintelligence scenario

Not single-entity takeover. "Multiple competing autonomous entities. Some go rogue; others fight them off. A hot pot of completely autonomous activity."

"Already in intelligence explosion." GDP follows exponential trend across all transformative tech (iPhone, computers) — AI will "blend into the previous ~2.5 centuries of 2% GDP growth."

Board/executive level: high control, low understanding (TSMC/Intel precedent). May see similar bifurcation: individuals/organizations maintain control over their agents; society-level: loss of control despite individual-level relationships.

---

## → Verso implications

### 1. The autonomy slider is the product's central UI contract — not just an option

Karpathy's most repeated design pattern is the autonomy slider: Tab completion → file-level edit → repo-level agent. Verso must expose this as a first-class API concept: `agent.run(task, autonomy="step" | "file" | "repo" | "full")`. The framework should let applications control delegation depth without rebuilding the entire execution model. Every built-in executor should have a natural "dial down" path.

### 2. The generation-verification loop must be the framework's primary timing metric

"It is in our interest to make this loop go as fast as possible." Verso should expose loop iteration latency as a first-class metric — not just total-task latency. The inner loop (generate → human checkpoint → approve/reject → resume) should be a named primitive in the API, not an afterthought. This means: streaming output to the caller at each proposed action before committing; a `checkpoint` / `hitl` mechanism built into the core loop, not bolted on.

### 3. Reliability is the real agent bottleneck — not intelligence or context

Karpathy's reliability-first framing (the "nines" argument): per-step reliability of 90% × 10 steps = 35% end-to-end success. Verso's design should be obsessed with per-step reliability, not raw capability. Implications: automatic retry with step-level error isolation; checkpointing after each successful step; structured output validation before committing each tool call; a failure taxonomy (tool failure vs. model failure vs. context failure) that the agent loop surfaces to callers.

### 4. Context is the product — not an implementation detail

"320KB per token in context vs. 0.07 bits per token in weights — 35 million-fold difference." Whatever the agent needs to reason reliably about must be in-context. Verso should provide first-class context assembly: a `Context` type with named slots (task description, tools, memory, prior steps, constraints), explicit token budgets per slot, and compression policies when budgets are exceeded. Not a raw `messages` list.

### 5. The intermediate artifact pattern (the "leash") is a framework design primitive

Karpathy's education example: insert an auditable intermediate artifact (the course structure) between the LLM and the end output. The LLM is constrained to a schema; the schema is human-reviewable; the LLM can't "get lost in the woods." Verso should make this pattern trivial: structured output as a first-class tool result type; the ability to surface intermediate artifacts to the HITL checkpoint before the loop continues. A `produce(schema)` action type that pauses execution for human review.

### 6. Verso should model the OS/utility distinction explicitly

Karpathy's LLM-as-OS framing means the "kernel" (the LLM) is stable and shared; applications run on top. Verso is an application-layer framework — not the kernel. This positioning matters: Verso should be model-agnostic (swap OpenAI/Anthropic/Llama), provide the "driver layer" abstraction (MCP as the hardware interface), and not try to be the LLM itself. The framework's job is the equivalent of the process scheduler and memory manager — not the CPU.

### 7. Agent infrastructure is still 1960s-era — Verso can define the GUI layer

"A GUI hasn't yet really been invented in a general way." Verso's `hitl` checkpoints, structured diffs, and approval workflows are the beginning of that GUI layer. Design these with the explicit goal of minimizing verification time: diffs not prose, structured changes not raw text, accept/reject affordances at the right granularity. The UX of a Verso-based agent should be "command-Y to accept" not "read 1000 lines of output."

### 8. Plan for decade-scale adoption, not overnight automation

"This is the decade of agents, not the year of agents." Verso should not over-optimize for the fully-autonomous case. The dominant use case for 2025–2030 is partial autonomy — AI handling 80% of volume, humans supervising the 20% of edge cases. Verso's API surface area should be weighted accordingly: excellent HITL, excellent step-level visibility, excellent retry semantics. Full autonomy is opt-in, not the default.

### 9. Continual learning is unsolved — memory is a gap, not a feature to claim

"Cannot retain information across sessions" is Karpathy's #4 deficit on the path to real agents. Verso should be honest about this: session-scoped memory is fully supported; cross-session persistence is a storage/retrieval problem the framework can wire to external backends, but the model won't "learn" from it in a weight-update sense. The API should distinguish: `memory.session` (ephemeral, in-context), `memory.store` (persistent, retrieved via search), and `memory.trained` (unavailable — honest label for what LLMs can't do natively).

### 10. ReAct remains the right default loop shape

Karpathy's Software 3.0 framing reinforces: the LLM is the CPU; tools are peripherals; the loop is straightforward. The elaborate graph-based orchestration frameworks are premature — they add complexity without reliability. Verso's default executor should be a clean ReAct loop (observe → think → act → observe) with explicit step-level checkpointing and no magic. Graph execution is opt-in for the specific cases (durable execution, parallel fan-out, HITL gates at specific nodes) where it earns its complexity.

### 11. English-first API design for the democratization wave

"Everyone is a programmer because everyone speaks natural language." Verso's task specification should accept natural language task descriptions as first-class inputs — not just programmatic tool configurations. A user should be able to write `agent.run("analyze this CSV and give me the top 5 anomalies")` and have Verso handle the rest. The typed/structured API is for power users and reliability; the English-first API is the entry point.

### 12. The Software 2.0 tooling gap is now Verso's evaluation gap

Karpathy identified in 2017 that Software 2.0 lacked IDEs, version control, and deployment tooling. The same gap exists for agent frameworks in 2025: no first-class eval harness, no "version control for agent behaviors," no tooling to detect when an agent's decision distribution has shifted. Verso should ship with a built-in eval loop: record task traces, score them via configurable criteria, alert when per-step success rates degrade. This is the equivalent of the "Software 2.0 IDE" for agent development.
