# THE FOUNDER OPERATING SYSTEM — Synthesis of the Full BAD GUIDE

*For @Seventydotleven (Slava): solo-ish, AI-native builder, distribution-starved (3 followers), shipping **Verso** — a Python agent framework ("we don't force the graph").*

*Built from all 19 notes in `04_bad_guide_full/` (244 verified sources + 8 books). This file is the one you re-read weekly. Everything else is the evidence trail behind it. When a line stops being true, cut it — the worst thing this becomes is something you respect but don't use.*

---

## 0. The Bet (the one frame everything hangs on)

For thirty years the bottleneck was *building the thing*. That's gone. When you, your competitor, and a smart teenager all have Claude Code and Codex, producing software stops being the edge. **Three things stayed expensive: knowing what to build (taste), staking your name on it (judgment), and owning a channel to put it in front of people (distribution).** The 90% are still optimizing the part that got cheap. Play the part that stayed expensive.

> **The only three things that compound: taste, distribution, and a primitive nobody else has.** If a week's work doesn't grow one of those three, it's the bullshit. Cut it. *(books-and-meta, The Bet)*

For you specifically, the asymmetry is stark: you've already *done the expensive engineering* — Verso is design-locked, evidence-grounded, 28k lines of harvest, a real counter-position. Your gap is not the framework. **Your gap is that ~nobody knows it exists.** This synthesis is weighted accordingly: distribution gets the longest section.

---

## 1. The Highest-Leverage Cross-Cutting Frameworks (the corpus agrees on these)

Every one of these recurs across multiple sections from multiple proven operators. Named, one line each, with who proved it.

1. **Build the primitive; the product is its consequence.** Figma spent ~4 yrs on a WebGL renderer + multiplayer protocol before the design tool; Linear built the sync engine before the kanban board; Perplexity built retrieval+synthesis before the chat UI. If you can't name your primitive in one sentence, you don't have one. — *Truell, Saarinen, Srinivas (revolutionary-products-talks)*. **Verso's primitive: the tactical↔durable seam — the same loop runs ephemeral or event-sourced with one flag, never a rewrite, never a forced graph.**

2. **Code is commodity; taste, judgment, and distribution are the moat.** As AI commoditizes execution, the moat migrates to the part AI can't do — knowing which output is *right* and staking your name on it. — *Packy McCormick "Most Human Wins," Dylan Field, Tuomas Artman (leverage / product-taste / modern-cto)*.

3. **A real opportunity has three parts — most people stop at two.** Conventional wisdom + a contrarian truth + a tech enabler that makes the truth doable *now*. The timing check is where theses die. — *Thiel CS183 / Zero to One (founder-mind, books)*. **Verso's three: (a) "frameworks add power"; (b) the loop is 5–10 lines and isn't where anyone competes, the harness is; (c) models got good enough that the over-engineered scaffolding is now provably depreciating.**

4. **The wrapper test: swap the base model in your head — if the product is ~the same, you built a wrapper.** The right side: a base-model upgrade *helps* you instead of *killing* you. — *Sequoia "Act Two," a16z "AI Moats" (revolutionary-products)*. Verso passes: better models make the durable layer (context, evals, memory, seam) *more* valuable, not obsolete.

5. **Compound architecture beats both wrappers and your own foundation model.** v0 took Claude Sonnet from 64.7% → 93.9% error-free with four engineering layers (RAG injection, stream-time fixing, deterministic AST fixes, a fine-tuned AutoFixer) — zero model training. Keep intelligence in the harness, not in weights you'll rent and lose. — *Malte Ubl, Vercel (revolutionary-products-talks, frontier-research)*.

6. **Retention is the only PMF signal that matters; fix it before any growth tactic.** Plot % monthly-active by day-from-signup; if the curve asymptotes you have PMF, if it falls to zero no distribution fixes it. Median AI app DAU/MAU ≈ 14%; real products hit 25–85%. — *Alex Schultz (Facebook), Sequoia "Act Two" (distribution, revolutionary-products)*.

7. **Operationalize PMF — don't wait to "feel" it.** Sean Ellis survey: "How would you feel if you could no longer use this?" Target >40% "very disappointed," then split the roadmap 50% double-down-on-love / 50% remove-blockers. — *Rahul Vohra, Superhuman (product-taste)*.

8. **Founder Mode / stay in the details on purpose.** Your discomfort with "hire good people and delegate" advice is accurate signal, not insecurity. Skip-levels and staying close to the code is a strategy. Charity Majors' pendulum + PG's Founder Mode = same principle. — *Paul Graham, Chesky, Charity Majors (founder-mind, modern-cto)*.

9. **Relentlessly resourceful is the founder gene — not IQ, not determination.** The opposite is *hapless*: passive in the face of a novel obstacle. It's a response pattern you can train. — *Paul Graham (founder-mind)*.

10. **Distribution, not capital/code, is the durable moat — and it's permissionless.** Naval's leverage taxonomy: code and media are the only two permissionless levers; you hold both. Harry Stebbings built a $400M fund from a bedroom podcast; "$4.4B of demand chases one $250M round — distribution is the only durable moat." — *Naval, Stebbings (leverage)*.

11. **Spiky point of view: opinionated stance grounded in real expertise beats safe takes.** "If you put 20 experts in a room, 19 would disagree — with good reason." Safe takes die in the feed; spiky takes are the bat signal that pulls your exact 1,000 people. — *Wes Kao (leverage)*.

12. **Build for the capability 18 months out, not today's.** METR: AI's task-time-horizon doubles ~every 7 months; the model that "almost works" on your hardest workflow today does it well in 7–14 months. The harness, evals, and domain context are the binding constraint when the capability lands — and they take months to build. — *METR arXiv 2503.14499, Jared Kaplan (modern-cto, frontier-research)*.

13. **Build the verifier first; the training/quality loop follows.** Any auto-checkable domain (code, math, "did the reply book a meeting") can be driven hard. 4,000 high-quality verifiable examples beat 4M low-quality ones; RLVR took a model 5%→50% on MATH-500 in 50 steps by *unlocking* existing knowledge. — *Hyung Won Chung, Raschka, Hamel Husain (frontier-research)*. **For Verso this is literally a product feature: evals are first-class, `define_outcome(rubric)` is bounded generate→grade→revise.**

14. **Saying no is a product capability; every feature costs you forever.** Jobs cut Apple 350→10 products. The discipline is refusing the ten plausible integrations that each dull the core loop. — *Des Traynor, Jobs (product-taste)*. **Verso's non-goals list IS this framework applied: not an SDK, not graph-by-default, not the kernel, not MCP-first, not multi-language, not a router cult.**

15. **The Bitter Lesson: bet against hand-crafted heuristics outrunning scale + search.** Any edge that depends on a clever encoding beating compute is on a 12–18 month expiration clock. — *Richard Sutton (frontier-research)*. Verso's correct application: keep the smarts in a model-agnostic harness; never bet the product on a fine-tune.

---

## 2. The Distribution Playbook — 3 followers → hunted

This is your single biggest constraint, so it gets the most room. The corpus is unusually unanimous here: **pick one channel, design loops not funnels, fix retention before virality, and make high-effort technical posting your proof-of-work.** For you, the channel is decided by where your buyers already live.

### 2a. Channel: pick ONE and go 90% deep — and it's X (build-in-public + Show HN)

- **Most winners used exactly one channel.** Lenny's synthesis of 40+ launches: spreading across five gets you zero on all five. — *distribution-growth-essays*.
- **Reverse-engineer where your users already congregate.** The people who'd use a Python agent framework — Python engineers fighting LangGraph's graph tax, AI-infra builders, indie AI hackers — are *posting publicly on X right now*. "The whole AI industry is on X and they're all anime avatars." — *Andrew Chen "Airbnb/Craigslist hack," Pieter Levels (distribution, leverage)*.
- **The two concrete surfaces for a dev tool:** (1) **X build-in-public** as the always-on channel; (2) **Show HN** as the repeatable spike (every meaningful ship). HN "overindexes on open-source, privacy-first products" — Verso's OSS-ready, no-lock-in design is native to this audience. — *markepear "How to Launch a Dev Tool on HN," Cursor/Bolt/Lovable cases (distribution)*.

### 2b. Cold start: the atomic network is ~5–10 specific people, recruited by hand

- **Solve the cold-start before scaling anything.** You need one atomic network — the smallest group for which Verso is already useful with zero other users. That's **you first** (the PRD literally says "personal infra, dogfood-first") + 3–5 named Python engineers who currently hate LangGraph's graph model. — *Andrew Chen "Cold Start Problem" (distribution)*.
- **Do things that don't scale; recruit the first users one at a time.** "Collison installation" — don't send a link, get on a call and build their first Verso agent with them. The manual version teaches you what to automate; the automated version teaches you nothing. — *Paul Graham "Do Things That Don't Scale," YC "How to Get Your First Users" (b2b-gtm, distribution-talks)*.
- **DM 30 specific people who posted about the pain.** Not a blast — 30 individuals who tweeted frustration with agent-framework complexity, each with a message referencing their exact post, offering early access. Founder-led, by hand. — *distribution-growth-talks takeaway #9*.
- **Launch into a crowd you already have.** Cursor (dev ecosystem), Lovable (52K-star GPT-Engineer following → #1 PH + #1 HN), Bolt (one tweet matched 7 years of ARR). You don't have the following yet — which is exactly why §2c (building it now) is urgent. — *distribution-growth-essays*.

### 2c. The loop: build-in-public is your acquisition loop, not a side activity

- **Loops compound; funnels leak.** Design the self-reinforcing cycle: you post a real build log / benchmark / teardown → the right engineers find and follow → some try Verso → they post about it → that's distribution for the next ship. The output of one cycle is the input to the next; CAC compounds *down*. — *Reforge "Growth Loops," Tony Dinh's exact loop: audience → low-CAC launches → revenue → more content (distribution)*.
- **Radical transparency is the highest-signal content and it can't be faked.** Pieter Levels' revenue numbers and Sahil Lavingia's failure post went viral *because* they were specific and honest, not polished. Your raw Verso build logs, the design forks you killed, the abstraction-cursor mistakes you only found by dogfooding — worth more than any curated highlight. — *Pieter Levels, Sahil Lavingia (leverage)*.
- **Proof-of-work is your moat on X.** Every platform rewards a specific proof-of-work; on X for the AI/infra crowd it's opinionated technical insight, and the barrier (most people won't do it) IS the moat. Early movers in a new proof-of-work game earn outsized social capital — and AI-native Python-infra build-in-public is a wide-open lane. — *Eugene Wei "Status as a Service" (leverage)*.

### 2d. The content shape: spiky POV + sell the outcome + hook in the first line

- **Post the architectural thesis, not the announcement.** "Verso v1 is out" is a claim. The spiky POV underneath is the bat signal: *"Most agent frameworks make you author a graph for an agent that's a 5-line loop. You're paying ~3× complexity for ~0 benefit. The loop was never the hard part — context and evals are, and every framework buries them."* That's defensible, grounded in your 28k-line harvest, and 19 of 20 framework authors would argue back. — *Wes Kao "Spiky POV" (leverage)*.
- **Sell the outcome, not the artifact.** Not "a Python agent framework with an async ReAct loop." Instead: *"the same agent runs simple by default and survives a crash, resumes, and pauses for human approval by flipping one flag — no rewrite."* McKenzie's rule: don't call yourself a programmer; sell the outcome the buyer can't read source to see. — *Patrick McKenzie "Don't Call Yourself a Programmer" (leverage)*.
- **Hook in the first 36 seconds / first sentence.** If the key insight isn't up front, churn is 82% higher. First line of every thread is the hook; thesis goes in paragraph 1, never 3. This is engineering, not inspiration. — *Harry Stebbings (leverage)*.
- **Tune for WHO, not HOW MANY.** One Python eng with budget authority frustrated by LangGraph is worth 10,000 generic followers. You need ~1,000 true fans, not a million followers. Build the magnet for the exact archetype; ignore everyone else. — *Kevin Kelly "1,000 True Fans," Shaan Puri (leverage)*.

### 2e. The shareable artifact: design the demo that makes the user look smart

- **The aha-moment must be a screenshottable artifact.** Bolt = the live-build clip; Midjourney = the Discord gallery image. For Verso: the **side-by-side** — `Agent(...).run()` in ~10 lines next to the equivalent 150-line `StateGraph`, OR the one-flag `durable=True` diff that adds crash-resume + HITL with zero loop changes. That diff is the tweet. — *a16z "Momentum is the Moat," distribution-talks (Bier "products live and die in the pixels")*.
- **Make acquisition the primary action, designed from day one.** The viral mechanic should BE the product experience (`agent.inspect()` printing exactly what the model sees is inherently demo-able). If you have to *ask* people to share, you haven't found the loop. — *Nikita Bier (distribution-talks)*.

### 2f. Retention gate — don't pour distribution into a leaky bucket

- Before spending real effort on reach: run the Schultz retention test and the Vohra >40% survey on your own dogfood + first 5 users. For a framework, "retention" = *do they reach for Verso again on the next agent without being prompted?* If not, fix that first — momentum is the moat only if people stay. — *Schultz, Vohra, Andrew Chen (distribution, product-taste)*.

---

## 3. Product-Taste + Research-Taste Checklist (how to pick what to build and judge quality)

### 3a. Picking what to build

- [ ] **Feature / Product / Company — which tier is this?** Feature ships in days and gets cloned next Tuesday; product solves a complete problem in months; only company-level moats compound (data flywheel, distribution, lock-in). Know the tier and the moat behind it before building. — *product-taste*. *(Verso: the clean loop is differentiation; the accreting memory + eval corpus + tool registry is the company.)*
- [ ] **Run Seibel's 6 questions in order:** problem in one sentence? experienced it yourself? defined narrowly? actually solvable? who *specifically* is the customer? how often do they have the problem? Weak answer → don't build yet. — *Building Product (product-taste-videos)*.
- [ ] **Three-part opportunity check:** conventional wisdom + contrarian truth + the *now*-enabler. If your insight leads to the same architecture as the incumbent, it isn't contrarian enough. — *Thiel (founder-mind)*.
- [ ] **Wrapper test + AI-completeness test:** does a better base model *help* you (good) or *replace* you (bad)? — *Srinivas, Sequoia (revolutionary-products)*.
- [ ] **Counter-positioning first (your earliest moat):** what can the incumbent NOT copy without destroying their existing business? LangGraph can't drop the graph — it's their whole identity and existing users. That's Verso's counter-position. — *Hamilton Helmer 7 Powers, a16z (revolutionary-products)*.
- [ ] **The bypass question, weekly:** not "what should I build?" but "what problem do I wish someone else would solve for me?" — opens the schlep filter that hides the best ideas. — *PG "Schlep Blindness" (founder-mind)*.
- [ ] **Does AI drive the customer's revenue (no ceiling) or just cut cost (ceiling = headcount displaced)?** Lead with the revenue story. — *product-taste, The Bet*.

### 3b. Judging quality (taste is objective — name the violated property)

- [ ] **Never say "I don't like it" — name *which property* is violated** (too slow, wrong mental model, missing emotional resonance on state X). "I don't like it" is not a product call. — *PG "Is There Such a Thing as Good Taste," Artman (product-taste, modern-cto)*.
- [ ] **The spec is the floor, not the ceiling** — after any implementation, ask what would make it *excellent*, not just functional. — *Karri Saarinen's 10 Rules (product-taste)*.
- [ ] **Start from the experience, work backward to the tech** — Jobs WWDC '97. The AI-slop trap is the inverse: grid-perfect, tonally dead output. Every default the model hands you is a decision you didn't make; override the ones that matter. — *product-taste, design-ux*.
- [ ] **Latency is a taste decision, not an infra afterthought.** Linear holds sub-50ms; under 200ms feels instant, over 500ms feels slow. *(For Verso: `agent.inspect()` and streaming true-delta are perceived-speed surfaces — treat them as taste work.)* — *design-ux, modern-cto*.
- [ ] **Run every animation/interaction through the six tests** (natural motion, <300ms, clear purpose, 60fps, interruptible, accessible); most fail on *purpose* and *interruptible*. — *Emil Kowalski (design-ux)*.
- [ ] **Fewer, more opinionated primitives = more coherence.** Linear collapsed 98 color variables → 3. Constraint is generative. *(Verso's "3 pluggable edges only" is this principle as architecture.)* — *design-ux, Teenage Engineering*.
- [ ] **Founder-mode the weekly product review yourself** — no delegate, no PM layer averaging taste toward safe. — *Chesky (product-taste)*.

### 3c. Research-taste (you're building dev-infra in a moving field — this matters)

- [ ] **Keep a written list of the 10 problems that would change your field if solved; check weekly whether your work is on it.** — *Hamming "You and Your Research" (frontier-research)*.
- [ ] **"If another group shipped this, would I be excited to read it?"** The sharpest filter for whether a feature/teardown/post is important enough or differentiated enough. — *Olah "Research Taste Exercises" (frontier-research)*.
- [ ] **De-risk the load-bearing assumption first, not the fun part.** Order work by information-gained-per-unit-time; kill the riskiest assumption before building on it. *(Verso's deferred-decisions list in §10 of the PRD is already this discipline.)* — *Steinhardt (frontier-research)*.
- [ ] **Evals before prompts; instrument before you iterate.** Build the feature×scenario unit-test matrix before spending a week tuning. The #1 cause of failed AI products is no eval system. — *Hamel Husain "Your AI Product Needs Evals" (frontier-research)*. *(This is also Verso's wedge — practice it on Verso itself.)*
- [ ] **Stay close to the run; treat every weird agent failure as a research lead, not a bug ticket.** Taste is built by noticing where models break. — *Sholto Douglas & Trenton Bricken (frontier-research)*.
- [ ] **Steelman the strongest disagreement before you bet** (LeCun vs Ilya, Sutton vs Gwern). When two sources you respect collide, that spot is the frontier — sit in it. — *frontier-research section body*.
- [ ] **Read architecture/SOTA claims for load-bearing vs cosmetic, interpolation vs generalization.** A 50,000× compute scale-up moving the needle 10% is interpolation, not a capability jump. — *Raschka, Chollet (frontier-research)*.

---

## 4. The Fundraising / YC Game in One Page (only when relevant)

You're pre-implementation and the PRD says "personal infra, dogfood-first, OSS-ready later." **You likely don't need to raise yet** — and the corpus says that's the strong position. Keep this page in your back pocket; act on it only if/when Verso has dogfood proof + early external pull.

- **Build toward Type-A fundraising: raise when you don't need to.** Ramen profitability or genuine pull = walk-away power = better terms than any pitch technique. "Be so good they can't ignore you" beats "make your pitch better." — *PG "How to Raise Money," Marc Andreessen (yc-a16z, founder-mind-talks)*.
- **YC grades velocity between apply and interview, not the idea.** Ship aggressively *after* you submit; the 10-min interview is "what did you build since we read your app." For an OSS dev-tool, that's stars/usage/PRs since submission. — *Dalton Caldwell, Garry Tan (yc-a16z)*.
- **The 1% slot needs three things, in writing:** a *secret* (contrarian truth defended with evidence — "the loop isn't where anyone competes; the harness is, and everyone buries it"), proof you *ship faster than anyone in the room*, and *founder-market fit that looks unfair* (28k-line RE harvest + thesis verification + a working framework = exactly that — don't bury it). — *a16z speedrun, Garry Tan (yc-a16z)*.
- **Check against the tar-pit and the RFS.** "Better LangGraph" framed as a wrapper is a tar pit; "software for agents / company brain" framing matches YC's live RFS. Use their language. — *Dalton Caldwell, YC RFS (yc-a16z)*.
- **If you run a process: breadth-first, compressed, terms over valuation.** All first meetings in a 2-week window; never name other investors until a term sheet is signed; close money immediately ("not a deal till it's in the bank"); optimize terms/round-size, not headline valuation; never name your valuation first. Onion theory: size the round to peel 2–3 named risk layers. — *PG, Elad Gil, a16z, Rahul Vohra (yc-a16z)*.
- **"Just don't die" beats every pitch trick.** Most failures are founders giving up, not wrong ideas. Survive long enough to find the answer. — *Dalton Caldwell (yc-a16z)*.

---

## 5. The Operating Loop — Weekly + Daily (tuned and expanded for you)

A guide you read changes nothing; a guide that becomes a cadence changes everything. The real constraint is not the code — it's that judgment and distribution don't compound unless you make them a rhythm. *(Base loop from books-and-meta "Operating System"; expanded with the corpus.)*

### The Weekly Loop (run it every week, no exceptions)

1. **One bet — write it in one sentence.** Pick a single thing that grows *taste, distribution, or the primitive*. If you can't write it in one sentence, you don't have a bet yet. *(For most weeks now: a distribution bet OR a Phase-0 dogfood bet, since the primitive is design-locked.)*
2. **Ship something public by Friday.** A Verso build log, a benchmark, a teardown, a Show HN, a spiky thread, a `durable=True` diff clip. Building in public is distribution + accountability in one move — and it's the only way the audience starts existing. *(This is the non-negotiable one given your 3-follower constraint.)*
3. **Talk to 3 users.** Founder-led sales and product taste both die without it. Use their exact words back to them (language/market fit). Early on, "users" = Python engineers who'll dogfood Verso or tell you why they won't. — *Matt Lerner, Jen Abel (b2b-gtm)*.
4. **Cut one thing.** Kill a feature, a doc, a half-built branch, a deferred decision that's actually dead. Velocity comes from subtraction; saying no is the product skill. — *Des Traynor (product-taste)*.
5. **(Add) Run the research-taste check once:** is this week's work on the 10-problem list? Would another team be excited to read it? If no to both, the week was misallocated.
6. **(Add) Re-validate PMF/retention monthly** (not weekly): are new dogfood sessions / new users reaching the aha as fast as the first ones? AI-product PMF degrades on a quarterly treadmill. — *Elena Verna (distribution-talks)*.

### The Daily Loop (protect the split — judgment is the scarce input)

- **Mornings — the hard calls only you can make.** What to build, the architecture, the taste bar, the thesis, the spiky POV for the week's post. Judgment is scarce; spend it when fresh. *(For Verso: abstraction-cursor decisions found by dogfooding, the next deferred-decision to resolve.)*
- **Middays — direct the machines.** Claude Code / Codex grind the 95%. Your job is the spec, the review, and the taste pass — not the typing. Spec-first, small chunks, keep the AI on the leash, treat output like an over-confident junior. — *Karpathy, Willison, Osmani (modern-cto)*.
- **Evenings — distribution.** One real post on X: a thing you actually learned or built today, not "engagement." Over a year this is the network that funds you and the audience that adopts Verso. **This is the habit that closes your single biggest gap; treat it with the same discipline as a code commit.**

### Standing disciplines layered on top

- **You are the upper bound** for how much anyone in your orbit cares; too much is the right amount. — *Alex Wang "Do Too Much" (founder-mind)*.
- **Inaction is the insidious risk.** The hard thing that matters > the easy thing that doesn't. Plan in decades, execute in weeks (for you: in days). — *Sam Altman (founder-mind)*.
- **Burn tokens, not headcount.** The constraint is token budget, not headcount; your managerial leverage is your prompts and specs. — *Tom Blomfield, Andy Grove (modern-cto, books)*.
- **Inversion weekly:** before deciding what to build, list 5 things that would guarantee this fails; avoid them. — *Munger (books)*.

---

## 6. How This Maps onto Shipping Verso Specifically

Verso is unusually well-positioned against this corpus — the *product* design already obeys most of the frameworks. The work left is almost entirely §2 (distribution) and §5 (the loop). Concrete moves:

### Positioning

- **One-sentence primitive (lead with it everywhere):** *"The same agent runs simple by default and is promoted to durable — crash-resume, checkpoint, human-in-the-loop — with one flag. We don't force the graph."* That's your primitive (framework #1), your spiky POV (#11), and your counter-position (3b) in one line.
- **Sell the outcome, not the artifact** (§2d): not "async ReAct loop + context engineering," but "LangGraph's power without the graph tax, with evals and reliability in the box." Run McKenzie's translation on every post.
- **Category framing, not "-er" framing** (revolutionary-products / category design): avoid "better/simpler LangGraph" (concedes their frame, reads as a wrapper/tar-pit). Name the thing you actually are — *the tactical↔durable seam* — and make graph-by-default look like the compromise. The non-goals list is your principled-refusal moat; publish it proudly.
- **Lead with the secret** (yc-a16z, Thiel): "the loop is 5–10 lines and isn't where anyone competes — the harness is, and every framework buries it." Defended by your harvest, not asserted.

### Launch (10+ micro-launches, not one big bang)

- **Sequence (Kat Mañalac):** silent page now → dogfood proof → spiky threads building the audience → Show HN on Phase-0 release → repeat Show HN every phase → each new primitive (the seam, evals-in-the-box, the durable flag) is its own re-launch.
- **Show HN, by the book** (§2a): personal voice, technical depth, transparent design rationale, GitHub link, modest language ("we don't force the graph" not "the best framework"), live in comments, reframe critics as doing you a favor. HN over-indexes on OSS + no-lock-in — Verso's exact design.
- **The shareable artifact** (§2e): build the **10-line-agent vs 150-line-StateGraph** screenshot AND the **one-flag `durable=True` diff** clip *before* launch. Those two images are your viral mechanic. `agent.inspect()` (prints exactly what the model sees) is an inherently demo-able "transparency-as-correctness" moment — clip it.

### First users

- **Atomic network = you + 3–5 named Python engineers** who currently fight LangGraph's graph model (§2b). The PRD's "dogfood-first, author is the first user" is the cold-start solved correctly — now extend it by hand: build their first Verso agent *with* them on a call (Collison installation).
- **DM 30 people** who've publicly complained about agent-framework complexity, each referencing their exact post (§2b).
- **Come for the tool, stay for the network** (distribution): Verso must be fully worth it for one engineer with zero other users (it is — personal infra). The network layer (shared memory corpus, eval corpus, tool registry — your eventual moat) comes after the single-player tool pulls.

### Build-in-public as the acquisition loop (your #1 distribution move)

- **Post the build, the forks you killed, the abstraction-cursor mistakes dogfooding surfaced** (§2c). You have a rare asset: a 28k-line evidence trail and a thesis-verification doc that *corrected two of its own claims*. Radical-transparency content like "here's where my own thesis was wrong" is the highest-signal, least-fakeable post you can write. — *Sahil Lavingia, Pieter Levels (leverage)*.
- **Turn the 27 anti-patterns and 22 copyable mechanisms from your harvest into a content engine.** Each anti-pattern (LangGraph's hidden `DEFAULT_RECURSION_LIMIT=10007`, Letta's 2,134-line agent, CrewAI's fake streaming, Perplexity's true-delta DX bug) is a spiky technical thread that proves your expertise and seeds Verso's necessity. This is proof-of-work content (§2c) and a near-infinite backlog.

### Quality / dogfood gate (taste + research-taste)

- **The dogfood gate IS the retention/PMF gate** (§2f, framework #6): "at least one of your own AI products runs on Verso before any OSS release" (PRD §9) = the Schultz retention test in disguise. Do you reach for Verso on the *next* agent without forcing yourself? If not, fix that before reaching for distribution.
- **Evals on Verso, by Verso** (§3c): practice your own wedge — build the feature×scenario eval suite for Verso's core loop using `eval.unit()`. "Eval == run" means this is free dogfooding and a credibility artifact ("the agent framework that ships its own eval suite").
- **Name the violated property** (§3b) on every API decision; spec is the floor; the loop stays <200 lines as a taste constraint, not just an engineering one.

### The build cadence (don't over-build ahead of evidence)

- **Phase-order is already de-risked** (Steinhardt, §3c): Phase 0 dogfoodable core → 1 memory+evals → 2 durable seam → 3 opt-in scale. The exit gate on each phase ("build a real personal agent on it") is "build the verifier first" applied to your own roadmap.
- **Compound architecture, not a fine-tune** (framework #5): the no-Rust, model-agnostic, harness-is-the-moat decisions are exactly right — every base-model release makes Verso's durable layer *more* valuable. Say this out loud in your launch (it's a wrapper-test win the audience will recognize).
- **Build for 18 months out** (framework #12): the durable layer (ReAct, context engineering, memory, evals, the seam) persists 3+ model generations; the tactical workarounds depreciate on a ~1–2 year clock. Verso's whole thesis is this framework — make sure the *messaging* says it, because it's also the strongest reason for someone to adopt now.

---

### The one-paragraph version (if you read nothing else)

The framework is done; the gap is that nobody knows. **Code is commodity now — taste, judgment, and distribution are the moat, and distribution is your weakest.** Pick one channel (X build-in-public + Show HN, because your buyers live there), recruit the first 5 users by hand, and make a real public post *every single day* — the spiky thesis ("the loop isn't where anyone competes; the harness is, and everyone buries it"), the build logs, the 27 anti-patterns from your harvest, the 10-line-vs-150-line and one-flag-`durable=True` diffs. Run the weekly loop (one bet, ship public by Friday, talk to 3 users, cut one thing) and protect the daily split (mornings = judgment, middays = direct the machines, evenings = one real post). Dogfood Verso until you reach for it without forcing yourself — that's your retention/PMF gate — then launch into the crowd you'll have built. Don't raise until you have pull. Treat posting with the same discipline as a commit, because it's the other half of the leverage equation that turns design-locked code into a hunted founder.

---

*Sources: all 19 notes in `/Users/seventyleven/Desktop/Verso/research/04_bad_guide_full/` (INDEX.md + the 18 section files). Verso grounding: `Verso/README.md`, `Verso/docs/PRD_v1.md`. Citations name the section note(s) where each framework is proven; per-person attributions trace to the named source inside that note.*
