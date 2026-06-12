# Building Claude Code with Boris Cherny
**Speaker:** Boris Cherny (Head of Claude Code, Anthropic)
**Venue:** The Pragmatic Engineer with Gergely Orosz
**URL:** https://www.youtube.com/watch?v=julbw1JuAz0
**Format:** Podcast, ~1h38m
**Transcript status:** READ_PARTIAL. No publicly accessible full transcript for the Pragmatic Engineer episode specifically. Reconstructed from: (1) Pragmatic Engineer newsletter companion post "Building Claude Code with Boris Cherny" (newsletter.pragmaticengineer.com) — show notes with key quotes; (2) companion deep-dive "How Claude Code is Built" (pragmaticengineer.com) — architectural analysis with direct quotes; (3) Every.to full transcript "How to Use Claude Code Like the People Who Built It" — different episode but same speaker, yielding verbatim quotes; (4) note.com summary of the Lenny's Podcast Boris Cherny appearance. Multiple sources cross-validated. The core arguments are consistent across sources, and the specific PRE (Pragmatic Engineer) episode quotes below are drawn from the newsletter companion post which accompanies this podcast.

---

## What Cherny Actually Argues

### Product overhang — the origin story
The breakthrough insight that turned Claude Code from a prototype into a product: "In AI, we talk about 'product overhang', and this is what we discovered with the prototype." The model already had the capability to traverse codebases autonomously — it just needed a product built around that capability. The product was lagging behind the model.

Implication: Claude Code was not built because the model became capable; it was built because someone noticed the model was already capable and the product surface didn't exist yet. This is the reverse of the typical product-then-capability sequence.

### Delete code on every model release — the core operating principle
"Every time there's a new model release, we delete a bunch of code." The specific example: "I just deleted like 2,000 tokens or something from the system prompt yesterday. Just because Sonnet 4.5 doesn't need it anymore."

And at a larger scale: "With Claude 4.0, they eliminated roughly half the system prompt."

The logic is that scaffolding which compensates for model weakness becomes model-hobbling once the model improves. Carrying dead scaffolding means the new model is running with a hand tied behind its back — it's being constrained by infrastructure built for a weaker version of itself.

Broader principle: "We build most things that we think would improve Claude Code's capabilities, even if that means we'll have to get rid of it in three months." Build knowingly temporary scaffolding; delete it without sentiment.

### The shifting capability boundary
"The boundary changes with every model in a surprising way. The newer models, they're more intelligent. So the boundary of what you need plan mode for got pushed out a little bit... the model kind of tends to subsume everything over time."

What this means: no scaffolding decision is permanent. The model reclaims territory. Features that were load-bearing become dead weight. The right posture is to hold scaffolding lightly.

### Bash as the universal interface — why not bespoke tools
Rather than building specialized tool wrappers, Claude Code gives the model Bash and gets out of the way: "The model just wants to use tools. We give it bash and they just started using bash, writing AppleScript to automate stuff in response to questions."

The discovery was empirical: they gave the model Bash and it immediately did useful things they hadn't anticipated, including writing AppleScript to answer questions about what music was playing. No one told it to do that — it just found a way.

For retrieval: "Agentix Search just outperformed everything. And when I say Agentix Search, it's a fancy word for glob and grep." Complex RAG pipelines and vector databases lost to the model running glob and grep on the filesystem. The model's ability to use simple Unix utilities was underestimated.

### Minimal scaffolding — the "get out of the way" philosophy
"The product is the model itself. Expose the model and put only minimal scaffolding around it."

Specific: "Everything you can do, Claude can do. There's nothing in between." This applies bidirectionally — users and the model use the same tool surface.

On removing tools rather than adding them: "We unshipped the LS tool... because we can enforce [permissions] consistently, we don't need this tool anymore. This is nice because it's a little less choice for Claude, a little less stuff in context." Removing tools reduces cognitive load for the model and eliminates decision points that don't need to exist.

### ~90% self-written codebase — the on-distribution tech stack argument
Technology choices were made based on what Claude Code itself could use to build Claude Code: "We wanted a tech stack which we didn't need to teach: one where Claude Code could build itself." TypeScript and React were chosen because "they're on distribution" — the model is already proficient.

Result: "Roughly 90% of Claude Code's codebase is now self-written" (by the model). Boris himself: "I have not written a single line of code since November."

The constraint is intentional on the remaining ~10%: deep understanding of system architecture must remain with the humans so the model's self-written code doesn't drift from the intended design.

### Dual-use tool design — elegance for humans translates to models
"It's surprisingly the same. Elegant design for humans translates really well to models."

Corollary: "Build a product in a way that is hackable, that is kind of open-ended enough that people can abuse it for other use cases it wasn't really designed for. Then you see how people abuse it and then you build for that."

This is the "latent demand" principle applied to tool design: build the tool to be abusable, then let actual usage patterns reveal what to build next.

### Uncorrelated context windows — sub-agents as isolation primitive
"The value is actually the uncorrelated context windows where you have these two context windows that don't know about each other."

Sub-agents are not primarily useful because they parallelize work; they're useful because they start with clean, uncontaminated contexts. An orchestrator that has accumulated 50 tool results and multiple failed attempts will pass that noise to child agents. Isolation prevents error propagation.

Practical pattern: "Start 10 agents and then just go like, 10 at a time and just migrate all the stuff over." Map-reduce at the agent level.

### The Bitter Lesson as required reading
The Bitter Lesson (Rich Sutton) is required reading for Claude Code team members. Boris's interpretation: "Always bet on general-purpose models. Don't use small models, don't fine-tune." Scaffolding gains are temporary; model capability gains are durable. Therefore investment priority goes to the model, not the scaffold.

### CI-integrated code review — Claude reviewing Claude
"Every pull request at Anthropic is code reviewed by [Claude Code]... CLAUDE will automatically address some of these." Result: approximately 80% of bugs caught before human review. Human review remains the final gate for security and enterprise-sensitive changes.

### Future form factors — terminal is not the final form
"My prediction is that the terminal is not the final form factor... there's going to be a few more form factors in the coming months."

And: "Pretty soon we're going to be in this mode of Claudes monitoring Claudes." Agent supervision becomes a product category.

### Permission system as the most complex component
Deliberately sparse interface plus one complex thing: "The most complex component implements tiered permission checks before irreversible actions, allowing users to grant one-time or persistent access." Everything else is minimal. Safety is the one place complexity is warranted.

### Resource scarcity as creative forcing function
"You should intentionally keep resources low at first" — forces creative problem-solving and maintains intrinsic motivation. This is how Boris explains building Claude Code solo in a terminal rather than immediately building an IDE integration.

---

## VERSO RELEVANCE

### [CONFIRMS §5.1 + SHARPENS §5.3] Delete scaffolding on model release — this is the Verso loop-harness anti-pattern to avoid
Boris's core operating principle — delete scaffolding when the model improves — is a direct CONFIRMS of Verso's §5.1 philosophy (loop <200 lines, minimal scaffolding). But it SHARPENS the argument: the danger isn't complexity per se, it's scaffolding that was built for a weaker model and never removed. Verso needs a design discipline, not just a size limit: scaffolding added to compensate for model weakness must be flagged as model-version-dependent and reviewed at each model bump.
**Verdict:** Actionable for §5.1. Add a "version-tagged scaffolding" convention to the harness design docs. [SHARPENS §5.1]

### [CONFIRMS §5.3] Bash / glob / grep beats RAG for retrieval — tool minimalism confirmed by production evidence
"Agentix Search just outperformed everything. And when I say Agentix Search, it's a fancy word for glob and grep." This is production evidence at scale (4% of public GitHub commits) that simple, on-distribution tools outperform complex RAG. Already known as a pattern; Boris provides the strongest practitioner confirmation available.
**Verdict:** [CONFIRMS §5.3]. Cite in tool design section as production benchmark evidence.

### [SHARPENS §5.3] Dual-use tool design: elegant for humans = elegant for models
"Elegant design for humans translates really well to models." This sharpens Verso's ACI tool-design principle: the test for a tool's quality is whether a human engineer would find it natural to call. If the tool requires a human to read the docs, the model will struggle with it too. The converse also holds: if the schema is machine-legible but not human-legible, it's probably poorly designed for both.
**Verdict:** Add as explicit design criterion to §5.3. [SHARPENS §5.3]

### [NEW-IDEA] Uncorrelated context windows as the primary value of sub-agents — not parallelism
Boris's framing is a meaningful reframe: sub-agents are valuable primarily because of isolation (uncorrelated context = no error propagation), and secondarily because they parallelize. Verso's §6.2 (multi-agent) currently frames sub-agents around failure-quarantine and scheduler-offload (already known). The isolation-of-context framing adds a third primitive: sub-agents as compaction units. When the orchestrator's context is dirty, launch a sub-agent with a clean context, give it the specification only, and let it work without inheriting the orchestrator's accumulated noise.
**Verdict:** Adds a third multi-agent pattern to §6.2. [NEW-IDEA for §6.2]

### [CONFIRMS §12] ~90% self-written code via on-distribution tech stack — confirms Verso's Python-native positioning
Boris chose TypeScript/React because the model already knows them well; 90% of the codebase is now model-written. Verso's Python-only choice (§12 hard invariant) is the same bet: Python is the most on-distribution language for LLMs. Boris provides a production-scale confirmation that "on-distribution tech stack" is a real design principle with measurable results.
**Verdict:** [CONFIRMS §12]. No new mechanism but strongest available practitioner proof point.

### [CONFIRMS §2] Product overhang as the warning against over-scaffolding
Product overhang (capability exists, product doesn't capture it) is the mirror image of Verso's non-goal §2: don't overkill. The scaffolding that doesn't exist yet lets the model breathe; the scaffolding that persists after the model surpasses it constrains it. Both Boris and Verso are pointing at the same failure mode from opposite sides.
**Verdict:** [CONFIRMS §2]. Useful rhetorical framing for the non-goals section.
