# How to Launch a Dev Tool on Hacker News

**Source:** Jakub Czakon (markepear.dev)  
**URL:** https://www.markepear.dev/blog/dev-tool-hacker-news-launch  
**Published:** ~2023-2024  
**Read status:** read_full  
**Format:** tactical essay with HN admin guidelines digest, Fly.io case study, and extended recommendations for developer tool launches

---

## Faithful Digest

### The Official HN Admin Guidelines (Distilled)

The essay synthesizes official HN launch guidelines (https://news.ycombinator.com/yli.html) into actionable principles:

**Style principles:**
- "Write in your own voice, not a corporate one"
- "Talk to HN as fellow builders and engineers" — insider register, not pitch register
- "Don't use superlatives (fastest, biggest, first, best)" — superlatives trigger the audience's fraud detector
- "Don't sell to this audience. If you try, they will close the tab" — the HN audience is allergic to marketing language
- "Modest language is stronger" — understatement earns credibility

**Product/offer requirements:**
- Free access with minimal barriers is the gold standard; demos/videos are a secondary option when live access isn't possible
- Transparent pricing — explain the business model, even if incomplete
- Frame CTAs around gathering feedback, not making sales — "I'd love your feedback" beats "try it now"

**Announcement structure (7-step):**
1. Introduce yourselves (who are the founders, briefly)
2. State what you do in one clear sentence (not a tagline — a plain sentence)
3. Explain the problem and why it matters (the pain, not your solution yet)
4. Share your backstory (why you built this — authentic motivation)
5. Explain your solution with technical details (this is where you can go deep — HN wants specifics)
6. Describe what differentiates your approach (not "we're better" — "we made a different tradeoff because...")
7. Invite community feedback ("what would make this useful for you?")

**Engagement strategy:**
- Answer comments quickly and thoroughly — the first 2 hours are critical; comments without replies look abandoned
- Avoid fake booster comments from colleagues — HN detects patterns of new accounts with no history voting on the same submission
- Address criticism gracefully by finding agreement first, then offering your perspective — "You're right that X is a limitation; here's why we made that tradeoff..."
- Remember: you're convincing the lurking audience of 10,000, not the one critic in the thread

### Fly.io Case Study

The highest-upvoted dev tool launch on HN at time of writing. Key attributes:
- Avoided hyperbole entirely; described what the product does in precise technical terms
- Used conversational language as if writing to one specific engineer friend
- Positioned around user benefits and tradeoffs, not feature lists
- The founder engaged deeply with every technical question in the thread
- Title was crystal-clear: readers knew exactly what they were clicking into

### Additional Tactical Recommendations

**Title framing:**
- Be explicit and specific — no clever wordplay, no mystery
- Include the technical category in the title (not just the product name)
- Good template: "Show HN: [Product Name] – [plain description of what it does]"

**Signaling:**
- Link to GitHub repo — open-source or not, the repo signals seriousness and lets people verify claims
- If OSS: emphasize it prominently — HN values open-source deeply
- If privacy-first or self-hostable: say so — these are credibility signals with the HN audience

**Infrastructure:**
- Prepare for sudden traffic spikes — HN can send 5-10K visitors in 90 minutes; sites that go down during a launch lose the moment permanently

**Priming without vote-begging:**
- The guide distinguishes between vote-begging (explicitly asking friends/colleagues to upvote — against HN rules) and legitimate priming (sharing the post in communities where it's genuinely relevant, letting the relevance speak)
- Timing: weekday mornings US Eastern time have highest HN activity

**Community engagement loop:**
- Each substantive reply in the thread is visible to the full audience
- Thoughtful, specific technical replies demonstrate product understanding and founder quality simultaneously
- The thread IS the product demo for a significant fraction of readers who won't click through to the site

---

## VERSO RELEVANCE

### Finding 1: The 7-Step Structure Maps Directly to Verso's Show HN Draft [SHARPENS]

The 7-step HN announcement structure is the most actionable immediate output from this source. Mapping it to Verso:

1. **Introduce yourselves:** "We're [name], ex-[credible context] — we've been building AI agents for [X] months"
2. **One clear sentence:** "Verso is a Python harness that makes agent loops reliable without forcing you to adopt a graph abstraction"
3. **The problem:** "Most agent frameworks make reliability a second thought — you get a fast prototype but replacing it with something production-ready means a rewrite"
4. **Backstory:** "We dogfooded this on our own agents and kept hitting the same ceiling — not intelligence, reliability. That's what we built for"
5. **Technical details:** The 3-line side-by-side; the one-flag durable diff; the invariant contract; the eval loop — HN wants specifics, give them
6. **Differentiator:** "We deliberately don't force the graph. Other frameworks give you a DAG abstraction because it makes the framework's state management easier. We think that's the wrong tradeoff for most agents"
7. **Feedback invite:** "We'd love to know: what reliability problems are you hitting with your current stack?"

**Verdict:** adopt-now — this structure should be the literal template for Verso's Show HN post.

**Tag:** [SHARPENS] — §12 (GTM / Show HN launch)

### Finding 2: "Don't Sell — Talk as Fellow Builders" = Verso's Natural Register [CONFIRMS]

The HN audience requirement — insider register, not pitch register — maps exactly to Verso's existing voice discipline. The anti-framework counter-position ("we don't force the graph") is insider language that signals structural awareness. The 3-line side-by-side is a technical argument, not a marketing argument. The founding persona is already in the right register.

**Risk:** the counter-positioning language ("unlike LangChain," "better than X") triggers the fraud detector. The rule is: never say "unlike X" — instead, describe your tradeoff. "We chose not to force the graph because..." vs "Unlike LangChain, we don't force you into a graph."

**Verdict:** sharpen — audit all §12 positioning language for "unlike X" patterns and convert to tradeoff-description language.

**Tag:** [SHARPENS] — §12 (positioning language / anti-framework register)

### Finding 3: The Thread IS the Demo for Non-Clickers [NEW-IDEA]

A significant fraction of HN readers will read the thread without clicking through to the site. This means the founder's replies in the HN thread are a parallel demo surface — distinct from the website, the README, and the actual product. Thoughtful, specific, technically honest replies demonstrate:
- Founder understands the domain deeply
- Founder can engage with criticism without getting defensive
- The product has been thought through at the edge cases
- The team is the kind of team that deserves trust

This sharpens the Show HN preparation requirement: prepare 10-15 "likely hard questions" with technically honest answers in advance. Not to dodge them — to engage them at quality.

**Prepared hard questions for Verso:**
- "Why not just use LangChain/LangGraph?" (tradeoff answer, not Better-Trap)
- "Why Python and not TypeScript?" (persona-first answer)
- "What happens when models get better? Does the harness become less necessary?" (intellectual honesty answer)
- "How does this compare to DSPy?" (already established: evals as gradient, optimization stays in Python)
- "Can't I just write 10 lines of Python myself?" (exactly right — and here's what those 10 lines miss at scale)

**Verdict:** adopt-now — pre-draft the thread reply sheet as a launch artifact.

**Tag:** [NEW-IDEA] — §12 (GTM / Show HN execution)

### Finding 4: Superlative-Free Language = Invariant-Language Discipline [CONFIRMS]

HN's rule against superlatives ("fastest, biggest, first, best") maps to Verso's already-established invariant-language discipline. Invariants are precise claims ("this context always contains X") not superlatives. The product taste principle — invariants-as-taste — is also the correct communication register for HN.

**Verdict:** confirm — existing taste discipline already HN-compatible.

**Tag:** [CONFIRMS] — §7 (product taste)

### Finding 5: OSS Signaling + GitHub Repo = Credibility Mechanism for Verso [CONFIRMS]

HN values OSS deeply, and GitHub repo links are a credibility signal. Verso's OSS-ready positioning is already aligned. The specific tactical requirement: the GitHub repo must be polished before launch — clear README, working examples, clean commit history. The repo is read as evidence of product quality by HN engineers.

**Verdict:** confirm — OSS posture is correct. Pre-launch task: GitHub repo polish as launch prerequisite.

**Tag:** [CONFIRMS] — §12 (GTM / launch execution)

### Finding 6: "Priming Without Vote-Begging" — Legitimate Early Amplification [SHARPENS]

The distinction between vote-begging (asking friends to upvote — against rules) and legitimate priming (sharing in relevant communities where the content is genuinely useful) is a tactical clarity. For Verso, legitimate priming targets:
- Latent Space Discord (AI engineering community)
- AI Engineer Slack
- Python packaging communities
- Personal X followers who are genuine AI engineers (share the Show HN link, don't ask for upvotes, trust the relevance to drive clicks)

The HN algorithm rewards early velocity — posts that get 5-10 upvotes in the first 15 minutes rise quickly. Legitimate pre-notification of genuinely interested people captures this without rule-breaking.

**Verdict:** sharpen — build the pre-notification list as a launch artifact, categorized by "genuinely relevant" (notify) vs. "favor-based" (don't notify).

**Tag:** [SHARPENS] — §12 (GTM / Show HN launch execution)

---

## Verdict Summary

| Finding | Tag | Section | Action |
|---|---|---|---|
| 7-step structure = Verso Show HN template | SHARPENS | §12 | adopt-now: draft Show HN using structure |
| No "unlike X" — use tradeoff-description language | SHARPENS | §12 | sharpen: audit positioning language |
| Thread replies = parallel demo surface | NEW-IDEA | §12 | adopt-now: pre-draft reply sheet |
| Superlative-free = invariant language discipline | CONFIRMS | §7 | confirm |
| GitHub repo polish as launch prerequisite | CONFIRMS | §12 | confirm |
| Legitimate priming list pre-launch | SHARPENS | §12 | sharpen: build pre-notification list |
