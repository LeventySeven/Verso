# Andrej Karpathy: Software Is Changing (Again)

**Source:** https://www.youtube.com/watch?v=LCEmiRjPEtQ  
**Transcript:** https://singjupost.com/andrej-karpathy-software-is-changing-again/  
**Status:** read_full (full transcript via SinjuPost; corroborated by Medium summary)  
**Speaker:** Andrej Karpathy  
**Event:** AI Startup School, San Francisco, June 18 2025 (YC-hosted)  
**Duration:** ~39 min

---

## Core Thesis: Three Eras of Software

Karpathy identifies three fundamental programming paradigms:

- **Software 1.0** — Traditional explicit code written by humans ("Computers obeyed. If it broke, it was your fault.")
- **Software 2.0** — Neural network weights optimized via data and training ("we stopped telling computers what to do and started showing them")
- **Software 3.0** — LLMs programmed through natural language. *"We're programming computers in English now. This is insane."*

The key claim: software has not changed so fundamentally in 70 years, and now it has changed twice in rapid succession.

---

## The OS Analogy (Core Architectural Frame)

Karpathy positions LLMs as analogous to a 1960s-era operating system:

| LLM Component | Traditional OS Analogy |
|---|---|
| LLM itself | CPU / kernel |
| Context window | Working memory / RAM |
| Tool use & APIs | System calls |
| Prompt engineering | Programming interface |

Verbatim: *"LLMs are kind of like a new operating system, right? So the LLM is a new kind of a computer."*

LLM labs resemble electricity grids (centralized, metered, utility-like), but they are fundamentally complex software ecosystems — more akin to Windows/macOS/Linux than commodity infrastructure. The LLAMA ecosystem may evolve as the "open-source Linux alternative."

**The implication for builders:** you are not building the OS; you are building the applications that run on top of it. The value is in the app layer.

---

## LLM Psychology: Capabilities and Critical Deficits

Karpathy frames LLMs as "stochastic simulations of people" — autoregressive transformers trained on human text exhibiting emergent psychology.

### Superhuman capabilities
- Encyclopedic recall across diverse domains (compared to Rain Man)
- SHA hash recall, breadth across disciplines

### Critical deficits (all must be engineered around)
- **Hallucination / confabulation**: makes up facts confidently
- **Jagged intelligence**: superhuman in some domains, fails basic tasks (e.g., *"9.11 is greater than 9.9"*)
- **Anterograde amnesia**: no native learning from repeated interactions; context windows reset each time
- **Gullibility**: susceptible to prompt injection and data leakage

These are "fallible systems" requiring human oversight — not autonomous agents ready for full deployment.

---

## Where to Build: Partial Autonomy Apps (The Value Layer)

Rather than end-to-end automation, Karpathy champions **hybrid human-AI systems** with adjustable autonomy. The Cursor example illustrates a spectrum:

- Tab completion (minimal autonomy)
- Command-K / chunk edits (medium)
- Command-L / file scope (higher)
- Command-I / repo-wide changes (agentic)

Similar autonomy slider at Perplexity: Quick search → Research → Deep research.

Four essential properties of a valuable partial-autonomy app:

1. **Context management** — The app handles retrieval, ranking, and presentation; the LLM doesn't see raw data
2. **Multi-LLM orchestration** — Embedding models, chat models, diff models coordinated by the application layer
3. **Application-specific GUI** — Visual diffs (red/green), command shortcuts, audit trails replace text. *"You don't just want to talk to the operating system directly in text."* GUIs leverage human visual processing for fast verification
4. **Autonomy slider** — Adjustable delegation granularity, never binary on/off

---

## The Generation-Verification Loop

*"We're now kind of like cooperating with AIs. Usually they are doing the generation, and we as humans are doing the verification."*

Two ways to accelerate the loop:
1. **Faster verification** via GUI/visual affordances — parsing diffs is <10% the cognitive load of parsing prose
2. **Better prompts** — reduce failed generations; concrete > vague; specific syllabus > "teach me physics"

Anti-pattern: vague prompts + poor verification = spinning loop with no signal.

---

## Building for Agents as Users

A new consumer category emerges: agents as users of infrastructure. Infrastructure changes required:

1. **`lms.txt` files** in plain markdown describing domain functionality (readable by LLMs, not HTML parsing) — analogous to `robots.txt`
2. **LLM-friendly documentation** — Markdown over bold/lists/images; Vercel and Stripe cited as pioneers
3. **API redesign for agents** — Replace "click here" UI instructions with equivalent curl commands
4. **Data ingestion tools** — `git-ingest` (GitHub repo → concatenated text), DeepWiki (AI-analyzed repo docs)
5. **Model Context Protocol (Anthropic)** cited as the standard agent-infrastructure interface

Philosophy: *"meet LLMs halfway"* rather than waiting for agents to navigate human UIs.

---

## Vibe Coding Phenomenon

Karpathy built an iOS app (no prior Swift knowledge) in one day. Created MenuGen.app in hours. But the hard part: infrastructure (auth, payments, DevOps) took a week — not because of code but because of human-hostile SaaS configuration dashboards.

Insight: LLM-assisted coding removes the language barrier; infrastructure tooling remains agent-hostile and should be redesigned.

---

## The Decade Caution

Tesla Autopilot parallel — the 2013 Waymo demo looked like imminent self-driving; 12 years later, still iterating.

*"Software is really tricky... when I see things like '2025 is the year of agents,' I get very concerned. This is the decade of agents."*

The Iron Man suit (augmentation + agency with human control) is the right model, not flashy autonomous robots. Partial autonomy with human-in-the-loop remains the correct stance for this decade.

---

## Flipped Technology Diffusion

Unlike electricity/flight/internet (government/corporate adoption first), LLMs inverted:

*"Maybe with early computers it was all about ballistics... but with LLMs it's all about how do you boil an egg."*

Consumers led adoption; governments lag. This shapes which problems get solved first — personal productivity dominates the early wave.

---

## Verbatim Quotes

- *"LLMs are kind of like a new operating system, right? So the LLM is a new kind of a computer."*
- *"We're programming computers in English now. This is insane."*
- *"Everyone speaks natural language, so everyone is now a programmer."*
- *"You don't just want to talk to the operating system directly in text."*
- *"This is the decade of agents."*
- *"We're now kind of like cooperating with AIs. Usually they are doing the generation, and we as humans are doing the verification."*
- *"Meet LLMs halfway by building agent-accessible infrastructure."*

---

## VERSO RELEVANCE

### [CONFIRMS §5.1 — loop harness]
The autonomy slider concept directly confirms Verso's "no graph for tactical agents" stance. Karpathy shows the spectrum (tab → chunk → file → repo) is managed by the application layer, not by a graph DSL. Verso's single-flag seam between tactical and durable is exactly this slider, done in Python. Verdict: confirms; no overkill.

### [SHARPENS §5.2 — context]
The context management requirement for partial-autonomy apps sharpens RunContext's role: the harness must handle retrieval, ranking, and presentation before the model sees anything. This maps directly to ContextBundle.inspect() and just-in-time retrieval. New precision: the GUI (diff display, visual verification) is part of context engineering for the human side, not just the model side. Verdict: sharpens; actionable.

### [SHARPENS §5.3 — tools]
The "build infrastructure for agents as users" argument (lms.txt, agent-friendly APIs, markdown docs, curl over click) sharpens the tool design principle: native Python @tool should return minimal structured data, not HTML or GUI-dependent blobs. Aligns with ACI tool design. The MCP citation as standard interface is relevant — Verso demotes MCP to opt-in, but the ecosystem reality is that MCP is the agent-infra interface standard. Verdict: sharpens §5.3 and §12 positioning.

### [CONFIRMS §6.3 — safety]
The "fallible systems" framing (hallucination, jagged intelligence, amnesia, gullibility) directly confirms why HITL and the quality gate layer matter in Verso's durable tier. Karpathy's decade-caution is the intellectual backing for Verso's "reliability first-class" positioning. Verdict: confirms; strong public authority for the premise.

### [NEW-IDEA — §5.2 context / §5.5 evals]
The generation-verification loop acceleration — two levers are (a) faster human verification via visual affordances and (b) better prompts to reduce failed generations — suggests Verso should think about eval output format as a verification-acceleration mechanism. If evals produce human-scannable diffs/structured output rather than prose, verification is faster. Not yet in PRD.

### [SHARPENS §12 — strategy]
The OS analogy crystallizes the positioning argument: Verso is an application on top of the LLM OS, not a competitor to the OS. The value is the harness (context, evals, seam) not the loop itself (~10 lines). Karpathy's framing gives vocabulary for the "you build on top of this" pitch. Verso's counter-position to graph frameworks maps: don't replicate the OS internals (graph = kernel-level over-engineering), build the app.
