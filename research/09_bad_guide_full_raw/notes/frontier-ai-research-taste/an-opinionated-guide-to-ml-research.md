# An Opinionated Guide to ML Research

**Author:** John Schulman (PPO/RLHF creator; OpenAI co-founder)
**URL:** http://joschu.net/blog/opinionated-guide-ml-research.html
**Published:** January 24, 2020
**Status:** read_partial — joschu.net socket-closed on direct fetch; content reconstructed from multiple high-fidelity secondary sources: jeonsworld summary, braindump.jethro.dev, podchemy.com podcast notes (Schulman Dec 2025 update on the essay's durability), hardmaru Twitter quotes, and Gordon response post. Core structure and quotes confirmed cross-source.

---

## Faithful Digest

Schulman's essay is organized around three pillars: (1) working on the right problems, (2) making sustained progress on them, and (3) achieving continual personal growth. The frame is explicitly "research is a learnable skill, and the key bottleneck is taste, not intelligence."

### Pillar 1: Problem Selection

**Idea-driven vs. goal-driven research** is the essay's central split:

- **Idea-driven**: Follow a sector of the literature. As you read a paper showing how to do X, you have an idea of how to do X even better. You then embark on a project to test that idea. Risk: duplicates effort, follows consensus, depends on literature exposure. Quote from hardmaru tweet (verbatim from the essay): *"To make breakthroughs with idea-driven research, you need to develop an exceptionally deep understanding of your subject, and a perspective that diverges from the rest of the community—some can do it, but it's hard."*

- **Goal-driven**: Develop a vision of some new AI capabilities you'd like to achieve, and solve the problems that bring you closer to that goal. Schulman recommends this for most people because: (a) it differentiates you from other communities, reducing competition; (b) it provides stronger motivation for long-term effort; (c) teams can collaborate on different aspects simultaneously — *"Goals also make it possible for a team of researchers to work together and attack different aspects of the problem, whereas idea-driven research is most effectively carried out by 'teams' of 1-2 people."*

**Building taste:**
- Read many papers critically and discuss them with people who have deeper knowledge
- Work in research groups to absorb others' experiences and judgment
- Seek advice from experienced researchers
- Reflect on what makes research useful and widely adopted
- Observe the **dependency graph of ideas**: which ideas became foundational and opened doors to other ideas? Build taste by tracking this graph, not just the surface-level content of papers

**Why top institutions concentrate talent:** Not because they work harder, but because researchers there possess "high-level expertise and perspective" — accumulated taste and judgment that compounds.

**Setting ambitious goals:**
- Ask: "Does this improve by 10% or 10x?" Small incremental improvements gain value only when they contribute to larger objectives
- Review work you admire; ensure your research trajectory could plausibly reach similar impact
- Avoid overly literal goal interpretation — aim broadly

### Pillar 2: Sustained Progress

**Maintaining research notes:** Schulman creates an entry for each day (confirmed via jethro braindump: "John Schulman creates an entry for each day, and conducts a review to condense entries every 1 or 2 weeks"). Benefits: retrieve forgotten details, make unexpected connections, centralize results for easy reference, monitor time allocation across projects. LLMs have made notebook-based feedback loops even more valuable (2025 update from Schulman).

**Knowing when to switch problems:** His experience suggests researchers more often abandon promising ideas *prematurely* than persist too long. Most months-long reviews show projects yielding publications rather than dead threads. He recommends either committing fully or allocating a fixed time budget — perhaps 80% to main work and 20% to exploring new directions.

**Recognizing dead ends vs. requiring persistence:** The essay distinguishes between a project that is genuinely stuck vs. one that is just hard. This is one of the most underrated skills. Schulman noted in his 2025 podcast update: "There is a lot of value in knowing about exactly what's going on in every line of code. And the people who have done the best work really have that understanding of the whole thing all the way to the nuts and bolts."

**Personal anecdote on unexpected subproblems:** During his PhD on robotics (goal: make RL work for complex locomotion), various unexpected subproblems arose — trajectory optimization became the most influential output. The goal-driven approach allowed him to follow value wherever it emerged within the goal space, rather than being locked to one idea.

### Pillar 3: Personal Development

**Reading strategy:**
- Read many papers with a critical eye — not to absorb all content but to notice trends and assess quality
- Implement papers' methods and compare results: "Deepens understanding and accelerates feedback"
- PhD dissertations are underrated: their introductions and conclusions are written by experts with a full-field perspective
- Books over papers for foundational knowledge: "Textbooks condense information in an ordered fashion with proper notation" — recommended: *Numerical Optimization* (Nocedal & Wright), *Elements of Information Theory* (Cover & Thomas)
- Track less-published work to identify emerging field trends before they become mainstream

---

## Key Quotes (verbatim or near-verbatim, sourced)

1. *"To make breakthroughs with idea-driven research, you need to develop an exceptionally deep understanding of your subject, and a perspective that diverges from the rest of the community—some can do it, but it's hard."* — joschu.net via hardmaru tweet

2. *"Goals also make it possible for a team of researchers to work together and attack different aspects of the problem, whereas idea-driven research is most effectively carried out by 'teams' of 1-2 people."* — joschu.net via search results

3. Three pillars: *"working on the right problems, making continual progress on them, and achieving continual personal growth."* — joschu.net via jeonsworld/braindump

4. *"[Researchers there possess] high-level expertise and perspective [rather than simply working harder]."* — joschu.net via jeonsworld

5. From the 2025 podcast update (confirming the essay's continuing relevance): *"I'd say probably engineering skill matters more now... as opposed to like research taste and like the ability to do like exploratory research."* — podchemy.com Dec 2025

6. *"[Distinguishing goal-directed from idea-driven work, maintaining detailed notebooks, and building taste through extensive reading.] Schulman's 2020 advice about research remains applicable."* — podchemy.com Dec 2025 framing

---

## VERSO RELEVANCE

### Finding 1: Goal-driven > idea-driven maps directly onto Verso's "durable architecture vs. tactical workaround" thesis
[SHARPENS §1 the bet]
The Schulman split is almost exactly Verso's bitter-lesson insight: idea-driven agent frameworks (LangChain's "how to do tool calling even better") vs. goal-driven ones (Verso's "what does an agent runtime that persists for 3+ model generations look like?"). Schulman warns that idea-driven work requires exceptional divergence from community consensus to produce breakthroughs — Verso's counter-positioning ("no graph required," "simplicity earns its place") is goal-driven in Schulman's sense. **Verdict: adopt-now as rhetorical/positioning frame.** The enemy is idea-driven framework design (constant churn matching the literature); the mission is goal-driven: build the durable harness.

### Finding 2: Taste-building via dependency graph = how to pick which Verso primitives earn their place
[SHARPENS §5.5 evals / §2 non-goals]
Schulman's specific mechanism for taste — observe which ideas became foundational and opened other ideas — is a design filter for Verso. A primitive earns its place if it unlocks other primitives (e.g., RunContext enables tool injection, typed event stream enables evals, checkpoint/resume enables human-in-the-loop). This is a sharper criterion than "is it simple?" **Verdict: sharpen — use the dependency-graph test as the internal design review question: "does this unlock something else, or is it a leaf node?"**

### Finding 3: 80/20 time split (main vs. exploration) mirrors Verso's tactical/durable seam
[CONFIRMS §4 the seam/architecture]
Schulman's recommendation to allocate fixed time to exploratory divergence (20%) while committing to main work (80%) structurally mirrors Verso's seam: the same agent code runs tactical-by-default (80% of usage) and can be promoted to durable (the 20% that actually needs it) with one flag. The insight is that forcing users to choose upfront is a false dichotomy — Verso's "same agent, one flag" is the implementation of Schulman's time-budget insight applied to architecture. **Verdict: confirm.**

### Finding 4: Unexpected subproblems yield the most influential outputs
[NEW-IDEA §5.3 tools / §5.2 context-engineering]
Schulman's PhD story (robotics goal → trajectory optimization became the most cited output) is a NEW warning for Verso: the harness primitives that will become most influential may not be the ones planned. The append-only event stream, the ContextBundle.inspect() API, or the StopReason enum may outlast the loop itself. Design all interfaces as if they are the real product. **Verdict: sharpen — every public interface in Verso should be treated as potentially the most influential output, not as internal scaffolding.**

### Finding 5: 2025 update — engineering skill > research taste for "scaling established ideas in existing infrastructure"
[SHARPENS §12 positioning/GTM]
Schulman's 2025 observation that engineering skill now matters more than research taste for current AI work (scaling within existing infrastructure) is directionally relevant to Verso's GTM. The target Verso user is the engineer who wants to *run* an agent reliably, not the researcher inventing new architectures. This confirms the positioning: Verso is for engineers who want the boring durable core, not researchers exploring new loop designs. **Verdict: confirm GTM positioning.**

---

## One-line Verdicts per Finding
- Goal-driven frame maps to Verso's counter-positioning: **adopt-now**
- Dependency-graph test as design filter for primitives: **sharpen**
- 80/20 split mirrors tactical/durable seam: **confirm**
- Unexpected subproblems = real product — design all interfaces seriously: **sharpen**
- Engineering > taste for current AI work → confirms Verso's target user: **confirm GTM**
