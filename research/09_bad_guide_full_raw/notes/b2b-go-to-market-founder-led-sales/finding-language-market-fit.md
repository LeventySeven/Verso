# Finding Language/Market Fit
**Source:** https://review.firstround.com/finding-language-market-fit-how-to-make-customers-feel-like-youve-read-their-minds/  
**Author:** Matt Lerner (ex-PayPal, SYSTM)  
**Format:** Essay · ~20 min  
**Section:** B2B Go-To-Market (founder-led sales)

---

## Faithful Digest

### The Central Claim

Matt Lerner argues that **language-market fit** — finding the exact words that match what prospects already think about — is a precondition for product-market fit. The sequence he recommends: find the language first, then use it to validate the product, then build. The common failure mode is building the product and then trying to find language to describe it, at which point the messaging ends up founder-centric rather than customer-centric.

The quantitative case: when messaging aligns with how prospects already think, conversion rates jump from 0.5–3% to 8–40%. That's roughly a 10–20x multiplier on every subsequent distribution effort.

### The Cognitive Mechanism: Information Foraging

Lerner grounds the argument in a specific cognitive model: prospects use **goal-directed attention** when evaluating products. They rapidly pattern-match incoming information against their internal goals through a subconscious process called "information foraging." Within seconds, their lizard brain decides: does this look like food? If yes, read more. If no, bounce.

The implication: no amount of clever copy can compensate for messaging that doesn't pattern-match to the prospect's existing mental model. You have to find the frame they're already using, then use it back.

"Your messaging must 'look like food' to their lizard brain within seconds, or they bounce."

### The Four-Step Process

**Step 1: Interview recent customers using Jobs-to-Be-Done methodology**

Ask them to walk through their purchase journey, not their product experience. The key questions are about the moment of trigger (what happened that made you look?), the alternatives they considered, and what they were hoping to achieve. Capture their **exact language** — the specific verbs they used, the specific pain they described. Do not paraphrase.

**Step 2: Draft headlines completing "Now you can..."**

Use the customer vocabulary from the interviews. Avoid vague category terms like "all-in-one" or "convenient" or "powerful." These are placeholders for thinking, not actual messages. The "now you can..." frame forces the message to be about an outcome the customer wants, not a feature you built.

**Step 3: Validate comprehension (five-second test)**

Show the headline to five people for five seconds. Ask: "What do you think this product does? Who do you think it's for?" Iterate until people grasp it naturally without explanation. If you have to explain it, the language doesn't fit yet.

**Step 4: A/B test quantitatively**

Use ads or landing pages to identify the top performers among your language candidates. This is where you discover which specific word choice or frame converts — and the answer is often surprising. The headline you think is best rarely wins.

### The 10X Example

A headline about "organizing notes and remembering content" converted 10X better (30% vs. 3%) than generic "accelerate learning" messaging for Mindstone. The winning message used the customer's own words (captured from interviews) about what they wanted to do. The losing message used the founder's frame about what the product achieved.

Lerner's key observation: "Your marketers and agency will call these messages boring" — because they lack the creative flourish that makes ad people happy. But for an unfamiliar startup without brand equity, boring and specific beats creative and vague. The prospect who doesn't know you needs recognition, not delight.

### Why Founders Get This Wrong

Founders describe their product. Customers think about their struggles and desired outcomes. These are different vocabulary sets. Founders who use their own vocabulary create messaging that resonates with other founders (who understand the product space) but not with the actual buyers (who understand their own problem, not the solution space).

The discipline is to sit on your hands during customer interviews and not correct their vocabulary. If they call it "losing track of things" instead of "knowledge management," that's the message. Use "losing track of things."

### The Competitive Moat Hidden in Language

Lerner makes a structural point: once you find the language that resonates, it's very hard for competitors to copy it because it requires them to do the same interviews. You're not copying a feature; you're encoding the customer's own mental model back to them. That's not replicable from the outside.

---

## VERSO RELEVANCE

This is the highest-delta source in the batch for Verso's §12 positioning work. The established constraint — ban "-er-than-LangChain" Better-Trap language, name a category + POV — is correct but incomplete. Lerner adds the operational method for finding the *right* language, not just avoiding the wrong language.

### [NEW-IDEA] §12 Positioning — Language-Market Fit Test Before Finalizing the Category Name

The PRD's established positioning work has correctly identified the category frame (harness > framework) and banned comparison language. But it has not established how to *validate* which specific words within that category resonate with the structurally-aware senior / AI engineer persona. Lerner's four-step process gives the method:

1. Interview 10–15 senior/AI engineers who have adopted (or considered and rejected) agent frameworks. Ask them to walk through their decision journey, capturing exact language.
2. Draft 5–8 headline variants using "Now you can..." with their words.
3. Five-second test each variant.
4. A/B test the survivors in ads or landing page variants.

The key risk for Verso: the words that resonate with the AI-researcher persona ("semantic kernel," "reasoning traces," "tool-use orchestration") are different from the words that resonate with the structurally-aware senior engineer ("my loop keeps breaking," "I can't tell what went wrong," "I have to rewrite everything when the requirements change"). Verso's persona is the senior engineer — the language must match that persona's vocabulary, not the researcher's.

*Tag: [NEW-IDEA] §12 positioning*  
*Verdict: adopt-now — run language-market fit interviews with 10-15 target persona members before finalizing category name or tagline; use JTBD protocol*

### [SHARPENS] §12 Positioning — "What Broke" is Likely the Resonant Frame, Not "Framework vs. Harness"

Lerner's "organize notes and remember content" won over "accelerate learning" because it used the customer's language about what they *actually wanted to do*, not the product's language about what it achieved. For Verso, the analogous risk is that "harness > framework" is Verso's language — correct and precise — but the structurally-aware senior engineer may not think in those terms.

Their vocabulary is likely closer to: "my agent broke in production," "I can't debug what happened," "I had to rewrite everything when the requirements changed," "the context window filled up and it just stopped working," "I can't tell if it's getting better or worse." These are the "organizing notes" equivalents — specific, problem-adjacent, outcome-adjacent.

The implication: test whether "harness" resonates or whether a more problem-adjacent frame (e.g., "the agent framework that doesn't break when your requirements change" — functional, not categorical) converts better. "Harness" may be the right category word internally while a different word is the right GTM word externally.

*Tag: [SHARPENS] §12 positioning*  
*Verdict: sharpen — do not assume "harness" is the resonant word with the target persona; A/B test it against problem-language alternatives*

### [NEW-IDEA] §12 GTM — The "Boring and Specific" Principle for Show HN / X Threads

Lerner's finding that "your marketers will call these messages boring" but boring-and-specific beats creative-and-vague for unfamiliar startups is directly applicable to Verso's Show HN and X build-in-public channel. The temptation in Show HN titles and X threads is to use clever, high-concept language ("the OS for agents"). The conversion insight says: use the customer's exact words about their specific problem.

A Show HN title like "Verso: agent framework without the framework" is Verso's language. A title like "Verso: one flag to make your agent loop resumable and debuggable" uses the outcome the engineer wants. Test both.

*Tag: [NEW-IDEA] §12 GTM / distribution*  
*Verdict: adopt-now — A/B test Show HN titles and X thread openers using problem-language variants vs. category-language variants; track engagement rate as proxy for language-market fit*

### [SHARPENS] §12 GTM — JTBD Interviews as a Positioning Research Method, Not Just a Product Research Method

The established prior passes identified the primary persona (structurally-aware senior / AI engineer) but relied on inferred persona modeling rather than systematic interview research. Lerner's method requires interviews with **recent customers** (people who actually adopted, not people who theoretically would adopt). For Verso at pre-launch, the analog is: interview engineers who recently adopted *any* agent framework (including competitors) and ask them to walk through their decision journey.

The decision journey questions reveal: what triggered the search, what alternatives they considered, what language they used to describe their problem, what made them commit. This is not the same as asking "what do you want in an agent framework?" — which produces feature lists. It's asking for the story, which produces language.

*Tag: [SHARPENS] §12 GTM*  
*Verdict: adopt-now — run 10-15 JTBD decision-journey interviews with engineers who adopted any agent framework in the last 6 months; capture exact language for messaging*

### [CONFIRMS] §2 Non-Goals — "All-in-One" and "Convenient" Are Dead Words

Lerner explicitly names "all-in-one" and "convenient" as placeholders for thinking — words that signal the founder hasn't done the work of finding what actually resonates. This confirms the PRD's ban on "-er-than-LangChain" Better-Trap language. Both are negative constraints on positioning language. The positive constraint (what to say instead) comes from the interviews.

*Tag: [CONFIRMS] §2 non-goals*  
*Verdict: confirm*

---

## Load-Bearing Quotes

- "Your messaging must 'look like food' to their lizard brain within seconds, or they bounce."
- "Your marketers and agency will call these messages boring" — deliberately so, for unfamiliar startups.
- Mindstone example: 30% vs. 3% conversion (10X) using customer's exact words vs. founder's frame.
- "Prospects aren't thinking about features. They're thinking about struggles and desired outcomes."

---

## Verdict Summary

| Finding | Action |
|---|---|
| Language-market fit test before finalizing category name | adopt-now — 10-15 JTBD interviews with target persona |
| "Harness" may not be the resonant external word | sharpen — A/B test vs. problem-language alternatives |
| Boring + specific beats creative + vague for Show HN / X | adopt-now — A/B test title variants |
| JTBD decision-journey interviews as positioning research | adopt-now — run before launch |
| "All-in-one" / "convenient" confirmed as dead words | confirm |
