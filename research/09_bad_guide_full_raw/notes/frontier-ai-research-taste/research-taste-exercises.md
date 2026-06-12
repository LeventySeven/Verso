# Research Taste Exercises
**Source:** Chris Olah (Anthropic), colah.github.io, Jan 9 2021
**URL:** https://colah.github.io/notes/taste/
**Status:** read_full
**Themes:** strategy, evals

---

## Full Digest

Olah opens with the core problem: "actually testing whether a research idea you come up with is good is very expensive. Often it takes months, so you only really get a few pieces of feedback on your taste every year." The essay is a collection of exercises to get *more* noisy-but-cheap feedback faster.

### What Research Taste Is

Taste = the ability to choose good problems. The bottleneck is not execution; it is problem selection. Olah's fundamental diagnosis: execution feedback is high-quality but rare (months per cycle), so you need proxy feedback pipelines that are low-quality but *orders-of-magnitude more frequent*.

### The Exercises

**Exercise 1 — Mentor rating:** Write down a list of research ideas. Have a respected mentor rate each 1-10. Discuss disagreements after reflection. The rationale: "It often takes several months of work to truly test an idea. Asking a mentor is a cheap proxy."

**Exercise 2 — Passive tracking:** "Pay attention when other people try ideas you've had. How did the results compare with your expectations?" This turns other researchers' published work into free evaluation of your prior judgments. Emotionally uncomfortable when someone publishes your idea, but "it's an opportunity to get precious feedback for free."

**Exercise 3 — Interview researchers on taste:** Ask colleagues: why do they work on the problems they do? How do they pick problems? What's their "big picture" of research? Bonus: write up the interview. Olah observes that PhD students often pitch their own project to visitors; he suspects they'd get more out of meta-research conversation.

**Exercise 4 — History of science books:** "Read books about the history of science. Reflect on why some researchers focused on important directions their contemporaries ignored." Olah's favorite: Kuhn, *The Structure of Scientific Revolutions*.

**Exercise 5 — Critical self-reflection:** Critically examine your own taste AND your community's taste. Questions to work through:
- "In what ways has your own research taste or your community's taste been wrong over the last few years?"
- "Are there adjacent research 'schools' with significantly different research taste?"
- "What are the underlying goals of your research taste?"

### Failure Modes

**Failure Mode 1 — Sunk cost attachment:** "A lot of researchers start working on one problem (often more due to circumstance than contemplated decision) and then find it hard to move on." Antidote: set aside a week or two every 1-2 years, create a list of the other most promising directions, and ask what you'd want to work on if starting from scratch.

**Failure Mode 2 — Lack of research intimacy:** "Theoretical knowledge is table stakes for research taste. You can't have research taste in a vacuum. You need theoretical knowledge and research intimacy." People who try to pick the perfect problem before getting their hands dirty produce nothing. Antidote: help someone else with their project first—"lower stress" and "you'll learn a lot and get your hands dirty without becoming overly committed."

**Failure Mode 3 — Environment misalignment:** PhD students who contort their interests to match their advisor's produce "ideas optimized for compromise rather than quality." This "starves you of an opportunity to build taste." Antidote: move environments OR temporarily buy into the group's interests and exercise taste within those constraints.

### Notable Guest Contributions

**Rachel Prudden's heuristic:** "Imagining that another group has published the paper you have in mind. Are you excited to read it?" Olah: "I think this is a pretty good heuristic."

**Andy Matuschak's anti-Hamming question:** "What are the most interesting (not important!) problems in your field? Why aren't you working on them?" Matuschak also flags a failure mode: "running to make an idea happen as soon as it seems tractable... if I sit with an idea longer I can often evolve a deeper variant and run with that instead."

**Michael Nielsen on messes:** "When you identify such a mess, the natural inclination of many people is to shy away... But a field that is a mess is really an opportunity. Chances are good that there are deep unifying and simplifying concepts still waiting to be understood and developed by someone."

**Arthur Allshire on bottlenecks:** "What are the bottlenecking problems in your field? Eg. in a lot of reinforcement learning research, a lot focus on slight tweaks to algorithms, but the biggest improvements have come from improving simulation for RL."

**Preetum Nakkiran on project proposals:** "Once you decide to commit the next >1 month of time to something, write up a few pages explaining: why the question is interesting, why the answer will be valuable, and what you expect to find (with initial evidence). And then get feedback." Also: "ask everyone you meet about their 'big picture' research goals. This is almost never written in papers, but is much more interesting/important."

**Christian Szegedy's contrarian observation:** "Most of the errors are made in my research was when I listened to the criticisms of my respected mentors and most of the cool stuff I did were the ones those everybody called initially useless, uninteresting or 'good luck!'... Ideas in research need to be either ahead of the others or should defy conventional wisdom." Olah qualifies this with survivorship bias warning and notes it's career-stage dependent.

**Boaz Barak on 20/80 projects:** "Do 80% of work to get 20% of goals: Rather than asking 'what's coolest result I can get with smallest effort?' ask 'can I find problem that distills the main obstacle even if end result doesn't sound cool?'"

**One final Olah dictum:** "I don't recommend forcing yourself to work on something you don't find exciting, even if you intellectually think it's more important. You'll be a lot less effective. Ideally, you want to get to a point where the problems you think are most important also feel most exciting."

---

## VERSO RELEVANCE

### Finding 1: The proxy-feedback pipeline is exactly what evals infrastructure is for [SHARPENS §5.5]

Olah's core problem — "testing whether a research idea is good takes months, so you only really get a few pieces of feedback per year" — maps directly onto Verso's eval challenge: testing whether an *agent architecture decision* is correct also takes months of real deployments unless you build fast, cheap proxies. Verso's `define_outcome(bounded)` + judge-panel evals system is structurally the same solution: orders-of-magnitude more noisy-but-cheap signal to steer architecture choices. The frame "get proxy feedback on more ideas faster" validates the entire evals-first bet.

**Verdict: sharpen.** Position evals not just as "test coverage" but as the *proxy feedback pipeline* — the mechanism by which framework design taste (on primitives, APIs, the loop boundary) is tested at 10x the speed of waiting for real user deployments.

### Finding 2: The "excited to read it" heuristic is a non-goals filter [SHARPENS §2]

Prudden's test — "if another group published the paper you have in mind, would you be excited to read it?" — translates cleanly to framework positioning: "if a competitor shipped the Verso feature you're about to build, would Verso users be excited to switch?" This operationalizes §2 (non-goals). If the answer is no, the feature is likely redundant with what the market already has (LangChain graphs, etc.). If yes, it must be a hard invariant or a genuinely novel primitive.

**Verdict: adopt-now.** Use this as the informal veto test when evaluating new primitive proposals.

### Finding 3: Environment misalignment failure mode predicts framework fragmentation [NEW-IDEA §12]

Olah's failure mode 3 — ideas optimized for compromise rather than quality when you're misaligned with your environment — maps exactly to the LangChain failure pattern: a framework that tries to satisfy every ML engineer's workflow preference produces APIs that satisfy nobody well. The "move environments" antidote is what Verso does by positioning: it explicitly targets the durable-infra-aware Python developer and *rejects* the graph-required workflow. The non-goal section is what enables taste.

**Verdict: sharpen.** The strategic story is: Verso refuses to compromise into environment misalignment. §12 GTM can use this: the framework with the clearest non-goals has the best product taste.

### Finding 4: "Messes are opportunities" validates the context-engineering bet [CONFIRMS §5.2]

Nielsen's observation (quoted by Olah): "A field that is a mess is really an opportunity. Chances are good that there are deep unifying and simplifying concepts still waiting to be understood." Context engineering in agent frameworks is precisely this mess right now — no one has a clean primitive model for what goes into the context window, in what order, with what prefixes. The fact that it's a mess validates making ContextBundle first-class.

**Verdict: confirm.**

### Finding 5: Sunk-cost attachment predicts the trajectory of LangChain/LlamaIndex [SHARPENS §12]

Failure Mode 1 — starting on a problem due to circumstance then finding it hard to move on — perfectly describes the incumbent frameworks. They started with naïve string-chaining, then added graphs, then added LCEL, each layer locked in by existing users. Verso's positioning as the "ruthlessly simple loop" with no accumulated accretion is the antidote. This is GTM ammunition.

**Verdict: sharpen.** §12 positioning can frame Verso as a fresh start unburdened by sunk costs.

### Finding 6: The 20/80 project framing is a lens for the loop file [CONFIRMS §5.1]

Barak's "80% of work to get 20% of goals" — doing the work that distills the main obstacle — maps to the <200-line loop constraint. The loop is the 20/80 project: it does 80% of the effort to prove the core is feasible, and all the interesting product work goes in the harness around it. This validates the "loop is not where anyone competes" thesis.

**Verdict: confirm.**
