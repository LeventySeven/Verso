# Books + Meta Sections (Bet / Bullshit Filter / Operating System / Cheat Sheet)

---

## Poor Charlie's Almanack — https://stripe.press/poor-charlies-almanack — partial — MUST

**Thesis:** Build a latticework of 80–90 mental models drawn from multiple disciplines (psychology, economics, math, biology, physics, history). No single model is enough; wisdom comes from the intersection of many applied simultaneously.

**The Latticework of Mental Models**
Munger's core epistemological claim: "You've got to have models in your head, and array your experience on this latticework." Cross-disciplinary thinking is the edge — borrow the big ideas from physics, biology, mathematics, psychology, and economics, and apply them in combination. A person with only one model sees everything through that lens and distorts reality to fit it.

Key quote: "80 or 90 important models will carry about 90% of the freight in making you a worldly-wise person."

**Circle of Competence**
Act only within areas of genuine expertise. The cost of straying outside your circle is not proportional to the distance — it's catastrophic. Know the edges of what you know. Intellectual honesty about ignorance is a competitive advantage.

**Inversion**
Instead of asking "How do I succeed?", ask "What would guarantee failure?" and avoid those paths systematically. Works in investing (what kills a business?), product design (what makes users hate this?), and decision-making (what are the ways this decision goes wrong?). "Invert, always invert."

**Lollapalooza Effect**
When multiple psychological forces act simultaneously in the same direction, the result is non-linearly large — an outsized outcome nobody predicted from the individual forces. This is why cults work, why bubbles inflate, and why some products go viral unexpectedly. Recognize when several biases are stacking and prepare for extreme outcomes.

**The 24 Psychological Tendencies (Psychology of Human Misjudgment)**
Munger's complete list — each one a source of predictable irrationality:

1. Reward and Punishment Super-Response — incentives drive almost all behavior; follow the incentives
2. Liking/Loving — favor people we like, overlook their flaws
3. Disliking/Hating — reject ideas from disliked sources even when valid
4. Doubt-Avoidance — under stress, rush to eliminate doubt with poor logic
5. Inconsistency-Avoidance — resist changing beliefs or habits despite contrary evidence
6. Curiosity — must be actively nurtured to maintain
7. Kantian Fairness — unfair treatment triggers outsized reactions
8. Envy/Jealousy — constant relative comparison to others
9. Reciprocation — feel obligated to return favors
10. Influence-from-Mere-Association — link ideas/emotions by proximity not causation
11. Simple, Pain-Avoiding Psychological Denial — ignore painful truths
12. Excessive Self-Regard — overestimate own skills (above-average effect)
13. Over-Optimism — excessive hopefulness when emotionally invested
14. Deprival Super-Reaction — losing something hurts more than gaining the same thing helps
15. Social Proof — follow the crowd, especially under uncertainty
16. Contrast Misreaction — misjudge based on relative comparisons instead of absolutes
17. Stress-Influence — revert to worst thinking habits under pressure
18. Availability-Misweighing — overweight vivid or recent information
19. Use-It-or-Lose-It — skills fade without consistent practice
20. Drug-Misinfluence — judgment clouded by substances
21. Senescence-Misinfluence — mental decline accelerates without active resistance
22. Authority-Misinfluence — obey authority even when wrong
23. Twaddle Tendency — waste time on nonsense
24. Reason-Respecting — prefer any explanation to none, even false ones

**The Two-Track Analysis**
When evaluating any decision: (1) rational factors — the evidence, logic, and explicit arguments; (2) subconscious psychological influences — which biases are active, which incentives are at play. Most people only do track 1. Munger does both.

**On Reading and Learning**
Munger reads obsessively across disciplines, carrying books everywhere. His framework: find the big ideas in each discipline and add them to your latticework. Once in place, each new idea finds a hook and sticks. Without the latticework, knowledge is inert.

**Memorable Quotes**
- "Invert, always invert." (attributed to Jacobi via Munger)
- "A great investor has a good temperament, not just a good IQ."
- "You don't have to pee on every fire hydrant." (on focus)
- "Show me the incentive and I'll show you the outcome."

**Why it's in the guide:** The single best judgment upgrade per hour of reading time. Free. The latticework concept is the intellectual foundation for why being multi-disciplinary is a moat, not a distraction.

---

## Build a Large Language Model (From Scratch) — Sebastian Raschka — https://github.com/rasbt/LLMs-from-scratch — partial — STRONG

**Thesis:** Understanding transformer internals by building them from scratch (not by analogy) gives you a genuine edge when reasoning about capability limits, failure modes, architecture choices, and what to expect from future models.

**What the free notebooks give you:**
- Tokenization from scratch (BPE, vocabulary construction)
- Attention mechanism implementation (scaled dot-product, multi-head)
- Transformer block: layer norm, MLP, residual connections
- GPT-style decoder architecture
- Pretraining loop and loss curve interpretation
- Fine-tuning on instruction data

**The real value:** Not the code itself (you can read the PyTorch docs) but the mental model of what each component does and why. When you see a benchmark, you understand the mechanism behind the number. When a model fails in a specific way, you recognize the architectural reason.

**Why it's in the guide:** The guide's AI engineering content is already captured in the 01_bad_guide/ cluster. This note captures the judgment angle: run the notebooks to own the substrate, not to become a researcher. An AI-native founder who can read a paper and say "that's a KV-cache optimization for long-context" has an edge over one who treats the model as a black box.

---

## High Output Management — Andy Grove — (book) — read — MUST

**Thesis:** A manager's output is not what they personally produce — it is the output of their organization plus the output of neighboring organizations under their influence. Everything else follows from this.

**Core Formula**
`Manager's Output = Output of Organization + Output of Neighboring Organizations Under Influence`

The implication: individual-contributor thinking is the #1 failure mode for new managers. Stop optimizing your personal work; optimize leverage.

**Leverage as the Organizing Principle**
High-leverage activities affect many people through brief effort. Grove's ranking:
- Training: 12 hours of preparation → 200 hours of improved output from 10 people (highest leverage)
- Role modeling: what you do, not what you say, sets the standard
- Information-giving with context: lets subordinates make better decisions independently
- Nudging: subtle steering toward preferred outcomes without directives
- Decision-making: participate, don't monopolize

"The art of management is selecting and concentrating on one, two, or three high-leverage activities and ignoring the rest."

**The Breakfast Factory Analogy**
Grove treats management as production management. Key principles:
- Find the limiting step (the slowest-cooking egg) and schedule everything around it
- Output ≠ activity (measuring eggs boiled, not breakfasts sold, is the failure mode)
- Inspect at the lowest-value stage (reject raw eggs, not finished plates)
- Variable inspection: when things run clean, sample; when problems appear, gate everything

**Task-Relevant Maturity (TRM)**
The right management style is not fixed — it's calibrated to the subordinate's competence and motivation for each specific task:
- Low TRM: structured instruction (tell them what, when, how)
- Medium TRM: supportive communication, emotional scaffolding
- High TRM: delegate and confirm objectives only

The failure mode: treating a high-TRM engineer with low-TRM micro-management. Or delegating to a low-TRM person with no structure.

**One-on-Ones**
- Minimum 1 hour; weekly for new/low-TRM, monthly for veterans
- The report sets the agenda and owns the meeting — this is the source of leverage
- Manager listens and asks follow-up questions until reaching the core problem
- Use a "hold file" for non-urgent items to batch them efficiently
- Schedule next 1:1 before ending current one

**OKRs (Objectives and Key Results)**
Grove invented this. Two questions:
1. Where do I want to go? (Objective)
2. How will I know I'm getting there? (Key Results)

Set quarterly, not annually. Keep objectives few. KRs must provide timely feedback that drives decisions.

**Decision-Making Process**
1. Free Discussion — all views aired regardless of status; most junior person speaks first
2. Clear Decision — articulate and confirm understanding
3. Full Support — everyone commits, including those who disagreed ("disagree and commit")

The Peer-Group Syndrome: people withhold opinions fearing judgment. Fix: have the most junior person speak first.

**Performance Reviews**
Dual purpose: assess capability AND increase motivation at same skill level. For top performers: spend MORE time here, not less — this is where leverage is highest. For poor performers: trace through five stages (ignore → deny → blame → accept → commit) and identify which stage they're in.

**Promotions**
"No action communicates your values more clearly than who you promote." Every promotion creates a role model. Base solely on performance.

**Retaining Employees**
When a valuable person resigns: drop everything immediately (signals they matter), ask why without arguing, find the real issue beneath the stated one, pursue every avenue including transfers before accepting loss.

**Self-Actualization as Peak Leverage**
Set stretch objectives 50% above current capability (50% failure rate acceptable). Self-actualized people become intrinsically motivated — manager no longer needs to push them.

**Memorable Quotes**
- "Delegation without monitoring is abdication."
- "One-on-ones are the report's meeting."
- "Output increases when everybody strives for a level of performance beyond their immediate grasp, even if they fail half the time."
- "All large organizations with a common business purpose end up in a hybrid organizational form." (Grove's Law)
- "Saying yes to one thing is saying no to something else."

**Why it's in the guide:** The only management book that's pure signal. Grove treats management as an engineering problem — measurable, optimizable, with explicit leverage ratios. Short. Dense. Every page is load-bearing.

---

## Zero to One — Thiel & Masters — (book) — read — MUST

**Thesis:** The most valuable companies create something entirely new (0→1, vertical progress) rather than copying what exists (1→N, horizontal progress). Every great company is built on a secret — an important truth most people don't yet believe — and holds a monopoly position.

**The Contrarian Question**
"What important truth do very few people agree with you on?"
Formula: "Most people believe X, but the truth is the opposite of X."
Business version: "What valuable company is nobody building?"
This is not just an interview question — it's the test for whether an idea is a company or a wish.

**Monopoly vs. Competition**
- Competition destroys profits for everyone; monopolists can plan long-term
- "All happy companies are different: each earns monopoly by solving a unique problem. All failed companies are the same: they failed to escape competition."
- Monopoly is not a bug — it's the condition of every successful business
- Monopolists can afford to think about workers, ethics, and long-term; competitors cannot

**Four Characteristics of a Durable Monopoly**
1. Proprietary Technology — at least 10x better than the closest substitute in one critical dimension
2. Network Effects — more users → more valuable; must start small enough for effects to be felt immediately
3. Economies of Scale — fixed costs spread wider as business grows
4. Branding — every company has a monopoly on its own brand

**Seven Questions Every Startup Must Answer**
1. Engineering — breakthrough technology, not incremental?
2. Timing — is now the right moment?
3. Monopoly — starting with big share of a small market?
4. People — right team?
5. Distribution — a way to deliver the product?
6. Durability — defensible in 10–20 years?
7. Secret — unique opportunity others don't see?

**The Power Law**
In VC: the best investment in a successful fund equals or outperforms the entire rest of the fund combined. In distribution: most businesses get zero channels to work — getting ONE channel working is the whole game. In companies: one secret is the spine of the whole business.
"Most businesses get zero distribution channels to work. Poor sales, not bad product, is the most common cause of failure."

**Last Mover Advantage**
Being first is a tactic, not a goal. The goal is to be LAST — to make the last great development in a market and enjoy decades of monopoly profits. First-mover advantage is only valuable if it helps you become the last mover.

**Distribution Insights**
- "Superior sales and distribution by itself can create monopoly, even with no product differentiation. The converse is not true."
- The best sales is hidden — disguised as relationship-building, account management, business development
- CLV must exceed CAC; this equation governs every distribution channel
- Distribution channels by deal size: complex sales (CEO-direct, $7M+) → personal sales ($10K–$100K) → marketing/advertising → viral

**Founding Team**
- "Thiel's Law: A startup messed up at its foundation cannot be fixed."
- Ideal board: 3 people, max 5 before IPO
- Binary employment: on the bus or off the bus; no part-time, no remote in early days
- CEO salary ceiling: $150K. Lower CEO salary = better company performance. One of the clearest patterns across hundreds of investments.
- Equity: unequal distribution reflects real differences; keep details secret

**The Four Post-Dotcom Dogmas (to invert)**
| The Wrong Lesson | The Correction |
|---|---|
| Make incremental advances | Risk boldness over triviality |
| Stay lean and flexible | A bad plan beats no plan |
| Improve on competition | Competitive markets destroy profits |
| Focus on product, not sales | Sales matters as much as product |

**Secrets**
Two kinds: secrets of nature (undiscovered physical facts) and secrets about people (what they want but won't say). Every great company is built on one. Why people stop believing in secrets: incrementalism, risk aversion, complacency, and the "flat world" illusion that someone smarter would have found it already.

**Memorable Quotes**
- "What important truth do very few people agree with you on?"
- "Competitive markets destroy profits."
- "Monopoly is the condition of every successful business."
- "Most businesses get zero distribution channels to work."
- "You are not a lottery ticket."
- "The most contrarian thing of all is not to oppose the crowd but to think for yourself."
- "Everybody has a product to sell. If you don't see salespeople, you're the salesman."
- "A startup is the largest group of people you can convince of a plan to build a different future."

**Why it's in the guide:** The contrarian-secret thesis is the spine of how to evaluate ideas. The guide explicitly calls this out: "already your spine, so read it once, end to end." The seven questions and monopoly characteristics are the most actionable framework in the guide for testing whether a company is real.

---

## The Hard Thing About Hard Things — Ben Horowitz — (book) — read — STRONG

**Thesis:** There is no playbook for running a company when it's on fire. The skills required are not taught in business school and cannot be learned from peacetime success. The only curriculum is experience.

**Wartime vs. Peacetime CEO**
The most important framework in the book:

| Peacetime CEO | Wartime CEO |
|---|---|
| Maximizes and broadens current opportunity | Has a single bullet in the chamber; must hit the target |
| Encourages broad-based creativity | Violates protocol in order to win |
| Minimizes conflict, seeks buy-in | Heightens contradictions; tolerates no disagreement |
| Focuses on the big picture | Focuses on one thing: survival |
| Proper protocol leads to winning | Protocol gets abandoned when survival is at stake |

Key insight: most management advice is written for peacetime. When the company is in existential trouble, peacetime rules actively destroy the company. The ability to switch modes — and to know which mode you're in — is a rare executive skill.

**The Struggle**
The CEO's internal crisis (the gap between vision and reality) is the normal state, not the exception. The key is not to avoid it but to operate within it without losing your mind. Horowitz on The Struggle: it's when you feel utterly alone, your solution doesn't work, and you have no playbook. Everyone who builds a company faces it. Most people who fail do so because they try to hide it.

**Lead Bullets, Not Silver Bullets**
When the product is behind and the company is losing, the instinct is to reposition, pivot, or find a clever shortcut. The real answer is usually "build a better product." "There are no silver bullets for this, only lead bullets."

**Key Leadership Principles**
- Share bad news with the top team immediately; transparency creates a culture where problems can actually be solved
- "If there is one skill that stands out, it's the ability to focus and make the best move when there are no good moves."
- Personnel decisions test courage more than intelligence; most leaders fail because they lack the courage to act, not the intelligence to know what to do
- When someone quits, drop everything and find out why — treating people right when they leave defines your culture for those who stay

**Courage Over Intelligence**
High-impact decisions — hiring, firing, performance conversations — test courage first. The answer is usually obvious. The failure is in the doing.

**What Are We Not Doing?**
Weekly staff meeting agenda item. Forces leaders to surface technical debt and business opportunities they're actively avoiding. One of the highest-leverage recurring meetings an organization can have.

**Why it's in the guide:** "The honest psychology of running a company when it's on fire. War stories, not a playbook." Not a how-to manual — a permission structure. Horowitz's candor about failure, self-doubt, and the absence of right answers is the real lesson. Builds emotional resilience and calibration.

---

## Thinking in Systems — Donella Meadows — (book) — read — STRONG

**Thesis:** Complex systems behave in non-intuitive ways because of stocks, flows, and feedback loops — not because of individual actors' intentions. Understanding system structure predicts behavior better than analyzing intentions. Leverage is real but counterintuitive.

**Stocks and Flows**
- Stock: the accumulation at any moment (water in a bathtub, money in a bank, trust in a relationship)
- Flow: the rate of change (faucet filling, interest earning, interactions building trust)
- The stock changes only through flows — you cannot instantly change a stock, only its rate of change
- This is why institutions resist change, populations take decades to shift, trust takes months to build and minutes to destroy

**Feedback Loops**
Two types:
- Balancing (negative) loop: self-corrects toward a goal (thermostat, market price signal)
- Reinforcing (positive) loop: self-amplifies until collapse (compound growth, viral spread, "success to the successful")

Key insight: reinforcing loops always destroy themselves eventually. Reducing the gain around a reinforcing loop is usually more powerful than strengthening a balancing loop.

**12 Leverage Points (Ranked Lowest to Highest)**
Meadows' hierarchy — most people push on #12, which is the least powerful:

12. Numbers/parameters (taxes, subsidies, standards) — "99% of our attention goes here; there's not a lot of leverage"
11. Buffer sizes (cash reserves, inventory) — stability but limited flexibility
10. Physical structure (road networks, age distributions) — requires expensive, slow rebuilding; leverage is in initial design
9. Delays (speed of feedback relative to rate of change) — mismatches cause oscillations
8. Balancing feedback loop strength (how well systems self-correct)
7. Reinforcing feedback loop gain (slowing growth is more powerful than strengthening correction)
6. Information flows (who has access to what data) — missing feedback is a common system failure; the Toxic Release Inventory example: no law, no fines, just public data → 40% drop in emissions by 1990
5. Rules (incentives, punishments, constraints) — power over rules is high-leverage power
4. Self-organization (power to change the system's own structure) — requires diversity and experimentation mechanisms
3. Goals of the system — a single leader articulating new goals shifts all lower leverage points
2. Mindset/paradigm — the deepest source from which goals, rules, and structure arise; paradigm shifts are mentally fast but societally slow
1. Transcending paradigms — "recognize that every paradigm, including the one shaping your own worldview, is a tremendously limited understanding" and gain the ability to choose any paradigm strategically

**Counterintuitive System Behavior**
Forrester's observation: "Everyone is trying very hard to push leverage points IN THE WRONG DIRECTION." The more powerful the leverage point, the more the system resists change at that point.

**System Traps and Archetypes**
Common failure modes from misconfigured feedback loops:
- Tragedy of the commons: reinforcing individual exploitation of a shared resource
- Drift to low performance: balancing loop to a goal that drifts downward
- Success to the successful: reinforcing loop that concentrates resources
- Rule beating: optimizing for the metric, not the goal the metric represents

**Why it's in the guide:** "Stocks, flows, feedback, leverage points. Useful for multi-agent loops and distribution." The distribution analogy is direct: growing an audience is a stock that changes through flows (content output) modulated by feedback loops (engagement, amplification). Optimizing parameters (posting frequency) has far less leverage than changing information flows (who sees what) or goals (what you're building toward).

---

## The Beginning of Infinity — David Deutsch — (book) — read — STRONG

**Thesis:** All progress results from the quest for good explanations. A good explanation is hard to vary while still fulfilling its function — it is resistant to casual modification. There is no upper limit to what humans can eventually understand or achieve, subject only to the laws of physics.

**Good Explanations**
The distinguishing criterion: a good explanation is hard to vary while still explaining what it purports to explain. Myths and bad theories are easy to vary — you can adjust them ad hoc to fit any new observation. Good explanations are falsifiable and constrained.

"All progress has resulted from the quest for what I call good explanations."

The practical test: if you can modify your theory without cost to accommodate contradictory evidence, you don't have an explanation — you have a narrative.

**Fallibilism**
Deutsch rejects justificationism (the idea that knowledge requires authoritative justification). Instead: "There are no authoritative sources of knowledge, nor any reliable means of justifying ideas as being true or probable." The right response to any theory is to try to improve it, not defend it.

Implication for founders: the startups that die defending their original thesis die of justificationism. The ones that survive are fallibilists — they update their beliefs faster than their ego defends them.

**The Optimism Principle**
"All evils are caused by insufficient knowledge." Problems are inevitable because knowledge is always incomplete. But problems are also always soluble — given the right knowledge, any transformation not forbidden by the laws of physics is achievable.

"What lies ahead of us is in any case infinity. All we can choose is whether it is an infinity of ignorance or of knowledge."

This is not naive optimism. It is bounded: constrained only by physics, not by current capability.

**Anti-Inductivism**
Experience does not generate theories. "Experience's main use is to choose between theories that have already been guessed." Observation doesn't produce knowledge — conjecture does. You discover by generating ideas and testing them, not by accumulating data until patterns emerge.

Direct implication: user interviews don't generate product ideas. They test them. The creative leap must come first.

**Static vs. Dynamic Societies**
Static societies: enforce existing memes through taboo and suppress criticism; optimized for stability; progress impossible
Dynamic societies: use critical faculties to replicate and improve ideas; progress is the steady state

Modern civilization is "an unstable transitional period between stable, static societies consisting of anti-rational memes and a stable dynamic society consisting of rational memes."

**Humans as Universal Explainers**
Humans are already "universal explainers and constructors" — we can understand and build anything not forbidden by physics. There is no category of superhuman mind that can do things we categorically cannot.

Implication: the question is not whether AI will eventually do X — it's when. The laws of physics don't forbid it.

**Memorable Quotes**
- "All progress has resulted from the quest for what I call good explanations."
- "Problems are soluble. By 'soluble' I mean that the right knowledge would solve them."
- "What lies ahead of us is in any case infinity. All we can choose is whether it is an infinity of ignorance or of knowledge."
- "Becoming better at pretending to think is not the same as coming closer to being able to think."
- "All evils are caused by insufficient knowledge."

**Why it's in the guide:** "The epistemic substrate the best founders and researchers cite. Rewards patience." Deutsch gives you a theory of knowledge that is more useful than any business framework — it tells you how to think about whether you know what you think you know, why analogies are unreliable, and why the right response to a failing thesis is to generate better explanations, not to defend the current one.

---

## Shoe Dog — Phil Knight — (book) — partial — OPTIONAL

**Thesis:** Building something real is an act of irrational belief sustained through crises, cash shortages, and near-death experiences. The founder's emotional truth is not heroism — it's obsession carried far past the rational stopping point.

**The Founding Bet**
Knight borrowed $50 from his father, flew to Japan, pitched Onitsuka's Tiger shoes before he had a real company, and sold them from the trunk of his car. Sales doubled every year. The lesson is not cleverness — it's the willingness to act on a thesis before the evidence is there.

**Cash Flow as Existential Threat**
Nike's early years were a constant battle with cash flow, not competition or product. 100% year-over-year growth plus supplier payment terms that required cash long before revenue arrived meant the company was perpetually near bankruptcy while growing faster than any competitor. The lesson: growth can kill you. Know the difference between profitable and cash-flow-positive.

**Distribution Was the Business**
Knight won by controlling his distribution channel. When Onitsuka tried to replace him, he had already built Blue Ribbon's relationship with American runners. The product mattered; the channel was the moat.

**The HHH Triangle at Nike's Founding**
- Knight (Hustler): direct sales, relationship building, channel control
- Bowerman (Hacker): product obsession, waffle sole innovation from a kitchen appliance
- Davidson (Hipster): Swoosh, brand, identity

**Key Lessons**
- Launch before you're ready — readiness is a decision, not a feeling
- Shared identity of your early team (they were all runners) drives quality standards nobody mandates
- The Michael Jordan bet: spot asymmetric talent before consensus catches up
- Brand compounds: the Swoosh multiplied margins far beyond product cost

**Knight's Regret**
He acknowledges sacrificing family time and describes building the company as an obsession that cost him personally. "Build the company and life you won't need to escape from."

**Why it's in the guide:** "The emotional truth of building something that nearly dies on repeat. Best as an audiobook." Not a strategy manual — a calibration tool. Reminds you that the companies you admire as overnight successes were mostly in crisis while growing. Builds resilience and sets expectations.

---

## BAD_GUIDE Meta Sections (from the guide itself)

### The Bet — what the game actually is now

**The shift:** For thirty years the bottleneck was building the thing. That's gone. When you, your competitor, and a smart teenager all have Claude Code and Codex, producing software stops being the edge. What's scarce is knowing *what* to build, having the *taste* to make it good, and owning a *channel* to put it in front of people. The 90% are still optimizing the part that got cheap. Play the part that stayed expensive.

**The five core principles:**

1. **Code is commodity; taste, judgment, and distribution are the moat.** Anyone can generate a working app this afternoon. Almost no one can tell you which app deserves to exist, why it's shaped the way it is, and how the first thousand people will find it. That last sentence is the whole job now.

2. **You don't want the median YC slot — you want the 1% slot.** The top-1% slot needs three things: a secret (a contrarian truth you can defend with evidence), proof you ship faster than anyone in the room, and founder-market fit that looks unfair. Pedigree gets the median in. Those three get you to the top of the batch.

3. **Plan in days and hours, because building is no longer the long pole.** A product that took a quarter in 2021 takes a weekend in 2026. Stop budgeting time for construction. Start spending it on deciding what's worth building and getting people to care.

4. **Feature → Product → Company: know which one you're building.** Features ship in days, products in months, only company-level moats compound. An AI feature anyone can clone by next Tuesday is not a company. Before you build, ask which tier this is. If it's a feature, it's a wedge at best — have the company-level moat mapped behind it.

5. **The business-model test: does AI drive revenue, or just cut cost?** The strongest AI companies sell AI that grows the customer's revenue (no ceiling). The weak ones sell AI that cuts the customer's cost (ceiling = the headcount you displaced, then you're done). Lead with the revenue story.

6. **The only three things that compound:** Taste, distribution, and a primitive nobody else has. If a week's work doesn't grow your taste, your distribution, or your primitive — that's the bullshit. Cut it.

---

### The Bullshit Filter — what to skip on purpose

**The shift:** Most "learning" is procrastination with a respectable face. Your risk isn't ignorance. It's spending new hours relearning skills you already have because relearning feels safe and shipping feels scary.

**Skip without guilt:**
- Language syntax and "learn X in 30 days" — you look things up, like every senior engineer alive
- ML-101 and re-deriving backprop — research taste beats textbook knowledge
- Generic system design interview prep — you design systems for real; that is the skill
- Tutorial hell, productivity content, and founder motivation — "a video about hustle is a tax on the hustle"
- Summaries of summaries — go to the primary source every time

**The honest correction (where the brief is slightly wrong):**
- Frontier researchers ignore *textbook* theory, not all theory. Chollet, Sutton, and the Anthropic interpretability team are deeply theoretical — about abstraction, search, and mechanism, not about memorizing 2015 architectures. The move: skip stale theory, go deep on load-bearing theory.
- You can't fake taste; you can only build it. The 80/20 leverage sits on top of having shipped enough to recognize quality. It's not a shortcut around the work — it's the leverage earned by already doing it.

**Filter in one line:** Don't spend new time relearning what you have; spend it on taste, distribution, and a primitive.

---

### Operating System — days and hours, not months

**The shift:** A guide you read changes nothing. A guide that becomes a cadence changes everything. Solo-ish operator, AI-native stack, distribution-starved (3 followers at time of writing). The real constraint is not the code.

**The weekly loop:**
1. One bet — pick a single thing that grows taste, distribution, or the primitive. Write it as one sentence. If you can't, you don't have a bet yet.
2. Ship something public by Friday — a feature, a teardown, a demo, a thread. Building in public is distribution and accountability in one move.
3. Talk to 3 users — founder-led sales and product taste both die without this. Use the exact words they use back to them.
4. Cut one thing — kill a feature, a doc, a half-built repo. Velocity comes from subtraction.

**The daily loop:**
- Mornings: the hard calls only you can make — what to build, the architecture, the taste bar, the thesis. Judgment is the scarce input; spend it when fresh.
- Middays: direct the machines — Claude Code / Codex grinds the 95%. Your job is the spec, the review, and the taste pass, not the typing.
- Evenings: distribution — one real post on X. Not "engagement" — a thing you actually learned or built. Over a year this compounds into the network that funds you.

---

### Frameworks Cheat Sheet (one screen) — the guide's own synthesis

| Framework | In one line | Use it when |
|---|---|---|
| Noticing, not ideating | Ideas are *noticed* by a prepared mind, not brainstormed | Tempted to "come up with" an idea — go live in the problem instead |
| Schlep is the business | The tedious work everyone avoids is the moat (Stripe) | An idea looks like too much annoying work — that's the signal |
| Contrarian-insight structure | Real opportunity = conventional wisdom + contrarian truth + tech enabler that makes it doable *now* | Testing whether an idea is a company or a wish |
| Relentlessly resourceful | The founder gene is resourceful vs hapless, not smart vs dumb | Self-auditing: having your way with the world, or being battered by it? |
| Architecture-first / primitive-first | Build the primitive; the product is its consequence (Figma: 4 yrs of renderer first) | Deciding what to build first — build the unfair core, not the demo |
| Compound architecture beats better models | v0 took Sonnet ~65% → ~94% via 4 engineering layers, no model swap | Waiting on a better model — engineer the harness around the one you have |
| Agent architecture beats model quality | Same model = 50–55% on SWE-bench Pro purely from harness/context | Agent underperforms — fix context management before fixing the model |
| Apply-model / decouple | Smart model decides the edit; small fast model executes it (~13×) | Anything slow and repetitive — split "what to do" from "doing it" |
| KV-cache is the #1 cost lever | Agents run ~100:1 input:output; cache the static prefix | AI bill scares you — cache before optimizing anything else |
| Task-horizon | AI does ~1–2 hr human tasks at >50%, doubling ~every 7 months | Roadmapping — build for the capability 18 months out, not today's |
| Feature / Product / Company | Features ship in days, products in months, only companies compound | Before building anything — know which tier it is and the moat behind it |
| Business-model reinforcement | Sell AI that drives revenue (no ceiling), not just cuts cost | Writing any pitch — lead with the revenue story |
| Verifiable-reward thesis | Auto-verifiable domains (code, math) can be driven hard with RL; 4k good examples > 4M bad | Picking where AI can go superhuman — find the verifier |
| Wrapper test | If a base-model upgrade kills your product, it was a feature, not a company | Sanity-checking your moat — survive the next model release on purpose |
| Decisions that looked wrong | Cursor forked VS Code; Midjourney went Discord-only; StackBlitz built WebContainers 7 yrs early | When the obviously-correct move is the crowded one — the right call often looks dumb at the time |

---

## Section body — the guide's own annotations per book

From the guide's book section (lines 1395–1418):

- **Poor Charlie's Almanack:** "The latticework of mental models. The single best judgment upgrade here, and it costs nothing."
- **Build a Large Language Model:** "Understand transformer internals by hand, not by analogy. The free notebooks are the real value. Run them."
- **High Output Management:** "Managerial leverage as an actual equation. The one management book that's pure signal, and it's short."
- **Zero to One:** "The contrarian-secret thesis in full. Already your spine, so read it once, end to end."
- **The Hard Thing About Hard Things:** "The honest psychology of running a company when it's on fire. War stories, not a playbook."
- **Thinking in Systems:** "How complex systems actually behave: stocks, flows, feedback, leverage points. Useful for multi-agent loops and distribution."
- **The Beginning of Infinity:** "How knowledge and good explanations actually work. The epistemic substrate the best founders and researchers cite. Rewards patience."
- **Shoe Dog:** "The founder memoir. The emotional truth of building something that nearly dies on repeat. Best as an audiobook."

Guide's closing line: "It's a living file — when a section stops being true, cut it. The worst thing this document could become is something you respect but don't use."

---

## Top Actionable Takeaways for @Seventydotleven

1. **The bet you're playing has changed.** Code is the cheapest input now. Taste, distribution, and a primitive nobody else has are the scarce ones. Every hour spent re-optimizing code quality over distribution is misallocated.

2. **Run the weekly loop without exception.** One bet (one sentence). Ship something public by Friday. Talk to 3 users. Cut one thing. This is the operating system, not a suggestion.

3. **The daily split is the leverage.** Mornings = judgment calls only you can make. Middays = direct the machines. Evenings = one real post. Stick to this or the scarce input (your judgment) gets diluted by the cheap inputs.

4. **Apply inversion every week.** Before deciding what to build: what would guarantee this fails? List 5 things. Avoid those. Then build.

5. **Use the seven questions before any new build.** Engineering, Timing, Monopoly, People, Distribution, Durability, Secret. If you can't answer all seven, the thesis has a hole.

6. **Fix distribution before the code.** Thiel's most underrated claim: "Most businesses get zero distribution channels to work. Poor sales, not bad product, is the most common cause of failure." You build fast. The gap is the channel.

7. **Your managerial leverage is your prompts and specs.** Grove's formula applies to AI: your output = the AI's output on your tasks + the output of anyone you influence. The highest-leverage activity is improving how you specify problems — the spec is the training task.

8. **Build the 10x primitive, not the wrapper.** Thiel: proprietary technology must be 10x better in one critical dimension. Meadows: change the goal of the system (leverage point #3), not the parameters (leverage point #12). Combining both: don't optimize an existing workflow — replace the primitive the workflow runs on.

9. **The bullshit filter is active, not passive.** Don't just "not read bad content." Actively cut tutorials, syntax learning, motivation content, and summaries-of-summaries from your calendar. The time doesn't disappear — it goes to taste, distribution, or the primitive.

10. **Deutsch's test for your thesis:** Is your explanation hard to vary? If you can modify the core claim easily to accommodate contradictory evidence, you don't have an explanation — you have a narrative. Apply this to every product thesis you hold.

11. **Paradigm is the highest leverage point (Meadows).** Don't fight the system parameters. Change what the system is for. The companies that win distribution don't optimize posting frequency — they change what "valuable content" means in that channel.

12. **The fundraising bar is concrete:** contrarian truth you can defend with evidence + proof you ship faster than anyone in the room + founder-market fit that looks unfair. Before any YC app, answer all three in writing.
