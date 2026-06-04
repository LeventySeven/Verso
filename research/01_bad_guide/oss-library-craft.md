# OSS library craft + API/DX taste

## Lessons from Building Open Source Libraries — Thomas Wolf (Hugging Face co-founder & CSO) at YC Eureka 2025 / NeurIPS 2025 — https://www.youtube.com/watch?v=6g8qRhCI8AU — [transcribed]

### Context
Talk is a ~15-minute fireside between Diana Hu (YC) and Thomas Wolf at the Eureka 2025 conference (San Diego). Wolf built the `transformers` and `datasets` libraries at Hugging Face — two of the most-used ML OSS libraries in history. He describes his mental model as "chief product officer for the open-source community" even though his title is CSO.

### On open-source clients and competitive pressure

- "Your clients is basically the open-source community and they're very difficult to please as clients because everything is free so they want actually the best. It's very easy for them to move from one to the other framework if they have to."
- This is the fundamental forcing function of OSS library design: zero switching cost means you cannot ship mediocre DX. Users leave silently without filing a support ticket.
- OSS is "probably the best thing that computer science brought to humanity" — Wolf explicitly frames community/open-science as a strategic distribution moat, not just altruism: "distribution of power is actually extremely powerful and power catalyzing ecosystem instead of just cannibalizing them."
- The `transformers` library went viral and caused HF to pivot the company — the library being excellent was the product.

### The two axes of library quality (Wolf's explicit framework)

Wolf says these are "both equally important" and treats them as the only two things that matter:

**Axis 1 — Onboarding experience (first-encounter DX)**

- "The distance from 'I download this library' to 'I run the first non-trivial example of what I want to do' — this should be an extremely pleasant experience." Analogizes it to Apple product unboxing.
- The first example must produce a "wow — this is something I was not able to do before I had this library" moment. Not "hello world" — a non-trivial, meaningful result.
- Abstractions must be "almost tangible and they look obvious to you." If the user has to work to understand an abstraction, you failed.
- "You should have very few abstractions because the more you have, each new abstraction you impose on your user to learn is like a friction point."
- Users do not want to read documentation. "Everything should look really obvious. It shouldn't even have to write the documentation." (The documentation should be the code itself.)
- The discipline he used: before every release, put yourself in the shoes of a first-time user with no context. "I install, I try this first thing. Does it look obvious? I install, I try this first thing." Repeat until it is obvious.
- The hardest part: "It's getting harder and harder as you know your library more and more because you start to not have this fresh mind." The curse of knowledge erodes your ability to feel what a new user feels. Actively maintaining the beginner's mind is a skill to cultivate.

**Axis 2 — The abstraction cursor (depth vs. simplicity tradeoff)**

- "There's always a cursor between how easy to use, how much control you give, and how complex it is. And this cursor is something extremely hard to pinpoint really well."
- The only way to find the right cursor: "try it a lot yourself on many use cases and see where if you get this balance between flexibility and intuitiveness."
- "There's a lot of taste here. I think there's a lot of design and I think a good open-source library overall is something that's extremely design opinionated."
- Key insight: the abstraction level is not a technical decision — it is a *taste* and *design* decision. You cannot derive it from first principles. You must develop taste by building and using the library at many abstraction levels and feeling where it breaks.

### On the demo-to-production gap (directly relevant to framework builders)

- "It can be easy to get a cool demo quickly but it's actually hard to get something that actually passes the bar to build a good product."
- "I think in any case there is no super shortcut from demo to production — it's still a painful process. But as part of the moat and the knowledge and like what you're building, the pain is also... once you made it work you actually solved something non-trivial and that's where your company value lies."
- Scaffolding is unavoidable: "Most of the company right when you want to build your product it most of the time you won't fall exactly squarely in this like good example. So they start building the scaffolding all the time — oh we need to pre-process, we need to be careful about this edge case because now it doesn't work."
- Implication: a great framework does NOT try to make the scaffolding disappear — it makes the scaffolding ergonomic and composable so users can build their own on top of your primitives.

### On open-source vs. closed-source and the application layer

- Value is shifting to the interaction/application layer: "The model is something but basically ChatGPT is very interesting because the interaction friction is very low because it's a product that really works."
- "The user interface and how you use the model in application or application that exists in your application is I think where the value will really lie."
- Open-source advantage: "If I want to use it outside of the training domain... the only option is to have access to this and tweak it. It's really vital for exploration, creativity and entrepreneurial creativity."
- Models as building blocks: "People have distilled in it like 100 million hours of GPU time and data and you can use that as a very powerful starting point to explore new use cases."

---

## Is There Such a Thing as Good Taste? (Paul Graham) — https://www.paulgraham.com/goodtaste.html — [read]

### Core thesis

Graham argues through reductio ad absurdum that good taste is real: if we deny it, we must deny that any art is better than any other, that artists can be skilled, that Leonardo is better than a random eight-year-old. "If we start from the premise that there's no such thing as good taste, we end up with conclusions that are obviously false."

### The definition

- Good taste in the narrow sense: "You have better taste than me if the art you like is better than the art I like."
- Operationalized: show unknowns to judges who have deep knowledge of the field and are free from extraneous influences — see who selects the better work.

### Why people think good taste doesn't exist

**Reason 1 — Disagreement and extraneous noise:** Most responses to art are "a tangle of unexamined impulses" dominated by irrelevant factors: artist fame, subject attractiveness, prestige of museum/venue, expensive framing. When you strip those away, expert agreement increases substantially.

**Reason 2 — The apparent subjectivity of responses:** Goodness "seems to be something happening in the heads of each of the observers" — it doesn't seem like a property of the object in the way mass is a property of an object.

**Reason 3 — Expert disagreement across time:** "Paintings admired by the so-called experts in one generation are often so different from those admired a few generations later." But this proves taste changes, not that it doesn't exist.

### The solution: partial objectivity

- Graham argues objectivity is not binary — it is a matter of degree, "depending on how much the subjects have in common."
- His vaccine analogy: effectiveness of a vaccine isn't meaningless just because immune systems vary. Similarly, art effectiveness varies by observer but remains meaningful as an aggregate claim about human response.
- Personal evidence: "Studying painting revealed that you could do it well or badly and improvement was achievable." The gap between his work and Leonardo's was "not imaginary" — it was demonstrably, measurably real to anyone who looked.
- Result: a *partial order* exists for art quality. Not a total order (you can't rank everything), but enough structure to say X is clearly better than Y in many cases, and to say "I have good taste" or "I have bad taste" meaningfully.

### What "good taste" requires

- Deep knowledge of the domain — you cannot assess quality in a domain you don't understand well.
- Ability to ignore extraneous influences — fame, context, price, how many people say it's good.
- The imagined ideal observer is "subjects with deep knowledge of art, and enough clarity of mind to ignore extraneous influences" — not the average untrained observer.

### Implications for quality in general

- Graham uses this to establish that design, writing, code, and APIs can be "better" or "worse" in ways that aren't purely subjective.
- The test of good taste in a designed artifact: can an expert, free from external signals, consistently identify it as better? If yes, the quality is real.
- Notable quote: "any painter is better than a randomly chosen eight-year-old" — this is what you commit to when you accept that good taste exists. It seems obvious when stated this way, which is Graham's point.

---

## Invisible Details of Interaction Design (Rauno) — https://rauno.me/craft/interaction-design — [read]

*Note: This is a design/UI essay. Its lessons are directly applicable to API/SDK design and developer tool DX — the principle that "invisible details" compound into felt quality maps exactly onto library design.*

### Core frame

"Interaction design [is] an artform to make experiences that fluidly respond to human intent" — balancing form and function. The "invisible" in the title means: these are the details users never consciously notice, but feel as the difference between something that feels *right* versus something that feels slightly wrong.

The author's meta-observation: "Searching the Internet for depth on interaction design yields a plethora of recycled content obsessing over user personas, storyboards, and Venn diagrams." Real craft requires "fanatically digging through research or maniacally replaying hundreds of slow motion screen recordings." Same problem in software library design.

### Metaphors and real-world physics

- Great interfaces reuse metaphors users already have from the physical world. Horizontal swiping = book page-turning (thousands of years of precedent). Vertical swiping = revealing layers (deck of cards). Pinching = picking up small objects (precision motor skill).
- Key payoff: when metaphors are reused, learning in one context transfers to another — the user learns once, gets fluent everywhere.
- Physics must feel right: momentum, angle, friction, interruptability. Animations should be interruptible the same way physical actions are interruptible — you can stop flipping a page mid-flip.

### The trigger timing principle: match intent confidence to action weight

- Lightweight actions (search overlays, peeks): trigger *during* swipe, immediately — user grasps intent fast, and aborting mid-gesture is low cost.
- Destructive actions (app dismissal, closing without saving): trigger only *on gesture end* — prevents accidental loss from a half-committed gesture.
- The principle: "trigger timing should match the cost of being wrong." Light actions demand instant feedback. Heavy actions demand explicit commitment.
- Naive implementation failure: triggering everything at threshold (0→1 animation) "provides no affordance that element is pinchable; feels unsatisfying." Immediate delta application + threshold-triggered animation is the correct two-phase design.

### Immediate feedback as a fundamental design requirement

- "Feeling the scale delta applying immediately, and then performing an animation past a given threshold" — the interface must prove it heard you in real time. Animation after a delay loses the trust signal.
- Counterexample: iOS Settings back-gesture doesn't interrupt mid-animation; you must wait for completion. Contrast with App Switcher's immediate responsiveness. The inconsistency breaks the model.
- Applied to developer tools: error messages must arrive at the right time (inline vs. compile-time vs. runtime) and must be immediately actionable. A delayed or batch error feels like the tool "didn't hear" you.

### Frequency and novelty: animation is only worth its cost at low frequency

- High-frequency interactions (command menu — "hundreds of times a day") should minimize or eliminate animation. Animation has a novelty budget that depletes. After the 100th time, it's cognitive burden.
- Case study: bookmarking tool animation "felt great initially; after days felt sluggish despite optimization. Removed motion from core interactions — felt faster immediately."
- Rule: "interaction novelty is diminished" at high frequency. The design that's appropriate for a first-time user is NOT appropriate for a daily-driver user. Design for the expert, not the tourist.
- macOS App Switcher never animates. macOS context menus have no appearance animation. Selected item blinks accent color; menu subtly fades out — "graceful and intentional" versus abrupt disappearance.

### Spatial consistency: motion communicates location and relationship

- Dynamic Island expanded → app launches from icon (shows where sound is coming from) or slides from right (shows it's first in App Switcher stack). Motion is not decoration — it encodes *where things are* and *how they relate*.
- Exception that proves the rule: Clock app always jumps from Island because there's no icon ambiguity — spatial clarity is unnecessary, so the cost of enforcing it is unjustified.
- Applied to developer tools: error messages should point to the right place in code, not just report that something failed. Stack traces that don't tell you *where* are the equivalent of spatial inconsistency.

### Fitts's Law: minimize movement cost for frequent targets

- "Time to click depends on distance and size. Bigger targets closer to pointer = faster interaction."
- Magic corners: pointer can't overshoot screen edges — infinite effective target area at corners. macOS Apple menu, Launchpad, corner gestures exploit this.
- Radial menus: all targets equidistant from cursor, same size. Distance and precision are constant for all actions. Muscle memory enables direction-only selection.
- Applied to APIs: the most common operations should have the shortest call paths. The "magic corners" of a library API are the zero-argument or single-argument constructors for the most common use cases.

### Implicit input: the best input is no input

- "The mother of all inputs: no input at all." Context-aware interfaces infer intent without asking. Apple Maps shows active route without unlock. Wallet increases brightness when presenting a pass to scan. Spotify adjusts UI for driving.
- Applied to libraries: good default inference (auto-detect types, auto-configure based on context) is always better than requiring explicit configuration. The best parameter is the one the user never has to think about.

### Fidgetability: intentional affordance for non-goal interaction

- Apple Pencil tip twists, AirPods case clicks — designed for casual, thoughtless manipulation during thinking breaks. These are not accidental; they are deliberate friction points that feel satisfying precisely *because* they provide resistance.
- Applied to developer tools: a REPL, a `--dry-run` mode, an `--explain` flag, a sandbox — these are fidgetability affordances. They invite exploration without commitment, which builds familiarity and trust.

### Taste development: articulation and execution are different but complementary

- "Understanding *why* something feels right ('articulating why') differs from designing it to feel right, but they're complementary."
- Articulation aids: taste refinement, execution amplification, appreciation for the difficulty of pursuing excellence.
- The essay is "not a tutorial nor a collection of guidelines. But rather an observation on the invisible details." — the author is doing what PG describes: building a framework for recognizing quality through specific examples, not rules.

---

## → Verso implications

### From the Thomas Wolf transcript

- **Zero-friction first example is the highest-leverage design decision.** The path from `pip install verso` to running a real agent (not hello-world, but something that genuinely couldn't be done without the library) must be under 10 lines with no required config. This is the "unboxing moment." Every additional line in the hello-world example is a potential abandonment point.

- **Abstract as late as possible; every abstraction is a tax.** Wolf's rule: each abstraction is a friction point. Verso should default to the concrete, un-abstracted form (run a loop, call a tool, get a response) and only introduce abstractions when the user explicitly needs them (multi-agent coordination, durable execution). `Agent()` with no arguments should do something useful.

- **"Extremely design opinionated" is a virtue, not a fault.** Libraries that try to be neutral on DX end up being mediocre at everything. Verso should have strong opinions about how agents are structured, how tools are defined, how memory works — and enforce those opinions in the default path, while making the escape hatch visible but non-intrusive.

- **Regularly re-test with the fresh-mind ritual.** Wolf's practice: before every release, reinstall the library as if you've never seen it, run the first example, ask "does this look obvious?" This should be a Verso release checklist item — not just unit tests but "does this still feel obvious to a new user?"

- **Open-source clients have zero switching cost — DX IS the moat.** If Verso is harder to use than LangGraph or CrewAI on the day-one experience, it will lose. Not because it's technically inferior but because OSS users leave without complaining. Every rough edge is a silent churn.

- **The abstraction level is a taste decision, not a technical decision.** There is no correct answer derivable from requirements. The team must use Verso to build real agents, feel where the abstractions feel wrong, and iterate. If the library isn't being dogfooded by the people building it, the abstraction cursor will be wrong.

- **The scaffold is unavoidable — design for composable scaffolding.** Users will build scaffolding on top of Verso no matter what. The framework's job is not to eliminate scaffolding but to make it composable and unsurprising. Provide the primitives (loop, tools, memory, context) at the right granularity so scaffolding built on top of them feels natural, not like hacking around the library.

### From the Paul Graham essay

- **Verso can have objectively good or bad API design.** This is not a matter of preference. A senior engineer with deep framework experience, free from hype and familiarity effects, can assess whether Verso's API is better or worse than alternatives. That assessment is real and should be pursued actively — not "different people have different styles."

- **Strip extraneous influence when evaluating design choices.** The equivalent of fame/prestige in library design: "this is how LangGraph does it," "this is the popular pattern," "this is what the docs show." These are extraneous. The test is: does this API feel right to an expert who has never seen LangGraph, knows nothing about Verso's positioning, and is just trying to build an agent?

- **Taste requires deep domain knowledge AND ability to ignore noise.** For Verso, this means the design team must have built real production agents (deep knowledge) AND be willing to discard patterns they used before if those patterns no longer feel right (ignoring the extraneous influence of familiarity).

- **The partial order is enough.** Verso doesn't need a perfect API — it needs an API that is clearly better than LangGraph for the target use case (simple, clean ReAct + tools + memory), even if it is not better in every possible dimension. Establish the partial order where it matters most.

### From the Rauno essay

- **Trigger timing for operations should match the cost of being wrong.** Verso API parallel: fast, reversible operations (read memory, call a read-only tool, log a trace) should have instant, non-blocking interfaces. Destructive or side-effectful operations (write to external systems, finalize a run, commit a checkpoint) should require explicit confirmation or produce loud feedback. Do not use the same calling convention for both.

- **Immediate feedback at every interaction point.** A Verso agent that runs silently for 30 seconds is like a gesture that doesn't respond until released. Every loop iteration should emit observable state — the framework must support streaming progress by default, not as an afterthought. Silence is equivalent to an unresponsive UI.

- **Design for the expert, not the tourist.** Once users are running Verso agents hundreds of times a day (in development), every "helpful" animation/verbose output/confirmation prompt becomes cognitive burden. Verso's verbose debug mode and quiet production mode must be first-class, with the quiet mode being the default once a user has crossed the "I know what I'm doing" threshold. The escape-hatch into more detail should require one flag, not a full reconfiguration.

- **Fitts's Law for API surface: most-common operations must have shortest call paths.** The magic corners of the Verso API: zero-config `Agent()` constructor; single-decorator `@tool`; one-line memory read/write. These are the infinite-size targets. Everything more complex is a smaller target further from the cursor — that's fine, it just means the user has to work harder for more power.

- **Implicit input: infer, don't require.** `Agent()` should auto-detect available tools (from decorated functions in scope), auto-configure memory backend (in-memory if no backend configured, Redis if `REDIS_URL` is in env), auto-select model tier (fast/cheap for simple tasks, powerful for complex) if routing hints are available. Every required config parameter is an implicit tax. Default behavior should be "best reasonable guess" not "error because not configured."

- **Fidgetability: build exploration affordances.** `verso run --dry-run`, `verso trace`, `verso explain`, a sandbox REPL where users can test a tool before wiring it into an agent. These are the AirPods case of the framework — they invite low-stakes exploration that builds muscle memory and trust. Users who have "played" with a tool are far more confident when using it in production.

- **The invisible details compound.** No single one of these decisions creates the difference between "feels great" and "feels slightly wrong." All of them together do. Every small friction point — a confusing parameter name, an error message that doesn't point to the right file, a default that requires overriding 80% of the time — accumulates into a developer who says "Verso feels clunky" without being able to say why. The discipline is treating every friction point as a design defect, not a "that's just how frameworks work" inevitability.
