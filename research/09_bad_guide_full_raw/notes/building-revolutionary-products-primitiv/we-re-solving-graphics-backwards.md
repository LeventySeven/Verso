# We're Solving Graphics Backwards

**Source:** https://cvalenzuelab.com/graphicsbackwards
**Author:** Cristóbal Valenzuela (CEO, Runway)
**Date:** November 2024
**Format:** Short essay (~4 min)
**Themes:** strategy, loop_harness (analogical)

---

## Full Digest

A tight, four-minute reframe of where the generative AI field is stuck. Valenzuela is not writing about agent frameworks — he is writing about creative AI tools — but the structural argument has direct architectural analogues for Verso.

### The Historical Claim

Classical computer graphics followed a strict sequencing: **control primitives first, rendering quality later**.

The core primitives — curves, triangles, polygons, meshes — were developed over decades and proved durable. Quote: "A cube modeled in 1987 using the first version of Renderman follows the same geometric principles as one modeled in Blender today. What's dramatically different is the rendering." The geometry layer stayed stable; the rendering layer improved continuously on top of it.

Why this order? The graphics pipeline enforces it structurally: "geometry defines what we want to draw, shaders determine how it looks." The pipeline architecture enshrined control as the first-class layer and rendering as the second-class layer. Even real-time engines follow this: "first establishing level-of-detail controls, then improving rendering quality within those constraints."

### The Inversion

Generative AI inverted this sequencing. "Today's generative models achieve photorealistic rendering quality that rivals or surpasses traditional pipelines... What's missing is control."

Quote: "While we can generate photorealistic scenes in seconds, we lack the precise control that decades of graphics research provided. We can't easily adjust geometry, fine-tune materials, or manipulate lighting with the granularity that artists expect."

This is what he calls the **inverse graphics problem**: rendering solved before control. The system can produce stunning outputs but cannot be reliably directed.

### The Path Forward: Native Primitives, Not Retrofitted Ones

Valenzuela argues against retrofitting classical graphics concepts (triangles, meshes) onto neural nets. Quote: "New primitives for control that are native to neural networks might be the right answer rather than trying to force traditional graphics concepts into this new paradigm."

The goal: "the same level of predictability and precision that made computer graphics a foundational tool for creative expression. That's the ultimate goal, but better: real-time, cheap, and with precise control that is as intuitive and general-purpose as possible."

Closing line: "Control comes last this time. But it's coming."

He notes he does NOT mean "better prompts" when he says control. The control primitives must be architectural, not cosmetic.

### The Structural Argument for Verso (Analogical)

The graphics backwards argument maps onto agent frameworks as follows:

- **Classical graphics (control then quality)** → Classical software engineering (deterministic, testable, composable primitives, THEN complex applications built on top)
- **Generative AI inversion (quality then control)** → Current agent frameworks (powerful capability first, production control primitives missing or bolted on)

LangChain was built in this inverted order: it shipped high-level capability (5-line RAG, easy agents) before the control layer (context visibility, durable execution, human-in-the-loop) was in place. LangGraph was the attempt to add control after the fact — but as Harrison Chase admits, it introduced a new learning curve because the control primitives (graph nodes) were borrowed from existing graph computing paradigms rather than being native to the agent loop.

Verso's approach — design the control primitives (ContextBundle, RunContext, @tool, checkpoint/resume, eval hooks) FIRST, and let the loop be simple on top of them — is structurally the "graphics forward" approach: control before scale.

---

## Verbatim Quotes (Load-Bearing)

1. "First came control, then quality."

2. "A cube modeled in 1987 using the first version of Renderman follows the same geometric principles as one modeled in Blender today. What's dramatically different is the rendering."

3. "AI has completely inverted this progression."

4. "While we can generate photorealistic scenes in seconds, we lack the precise control that decades of graphics research provided."

5. "This is the inverse graphics problem: we've solved rendering before solving control. Our models can create stunning imagery but lack the fundamental abstractions that made computer graphics so powerful."

6. "New primitives for control that are native to neural networks might be the right answer rather than trying to force traditional graphics concepts into this new paradigm."

7. "Control comes last this time. But it's coming."

8. "I often speak about control in AI. But I have realized sometimes people think I mean 'better prompts.'"

---

## VERSO RELEVANCE

### Finding 1: The "inverse graphics problem" is a precise analogy for the agent framework design sequence — Verso inverts the inversion
**Tag:** [NEW-IDEA §1 the bet / §4 architecture]

The agent framework ecosystem reproduced the generative AI mistake at the framework level: LangChain shipped capability-first (easy agents, lots of integrations) and then tried to bolt on control primitives (LangGraph, LangSmith). Verso's architectural bet is to design the control primitives first — ContextBundle, @tool decorator, RunContext injection, checkpoint/resume, eval hooks — and keep the loop itself clean and simple on top of them. This is the "graphics forward" approach for agent frameworks: control before scale.

This is a NEW framing device for Verso's §1 bet and §4 architecture narrative. It provides a memorable, non-technical analogy that explains why "control-first design" is the right sequencing without requiring the reader to know agent frameworks.

**Verdict:** adopt-now — use "we're not solving agents backwards" as a positioning frame in §1 and §12. Verso's architecture explicitly sequences control primitives (context, eval hooks, durability) before capability expansion.

---

### Finding 2: "Native primitives, not retrofitted ones" — validates @tool over MCP-first, ContextBundle over middleware
**Tag:** [CONFIRMS §5.3 tools / SHARPENS §5.2 context-engineering]

Valenzuela's key warning: "trying to force traditional graphics concepts into this new paradigm" produces the wrong control primitives. For Verso, the analogous mistake would be: retrofitting MCP (a protocol designed for a different layer) as the primary tool abstraction, or adding LangChain-style middleware hooks onto an existing loop. Verso's native Python @tool decorator and ContextBundle are the "native neural network primitives" for agent control — designed for the agent loop, not borrowed from adjacent paradigms.

This SHARPENS §5.3 (tools): the @tool path is native; MCP is a retrofit adapter for external tools (exactly as LangChain's middleware is a retrofit for context control).

**Verdict:** sharpen — reinforce in §5.3 that @tool is the native primitive; MCP is a compatibility shim, not the primary path. The framing: "native control primitives vs. retrofitted adapters."

---

### Finding 3: "Control comes last this time. But it's coming." — the timing argument for Verso's market window
**Tag:** [SHARPENS §12 positioning/GTM]

The graphics backwards essay implicitly identifies a market timing window: the period between "quality without control" (early generative AI tools, early LangChain) and "quality with control" (when the control primitives crystallize). Verso is explicitly building in this window — the period before the field settles on control primitives for agents. The analogy suggests that whoever establishes the right control abstractions will define the field the way Catmull's geometry primitives defined computer graphics.

**Verdict:** sharpen — §12 positioning should articulate the timing window explicitly: we are in the "quality before control" phase for agents, and Verso is the first framework to sequence it correctly (control primitives designed first, loop on top).

---

### Finding 4: "Better prompts" is explicitly NOT what control means — validates Verso's non-prompt-engineering stance
**Tag:** [CONFIRMS §5.2 context-engineering / §2 non-goals]

Valenzuela opens with: "I have realized sometimes people think I mean 'better prompts.'" This is a precise dismissal of the most common misunderstanding of the control problem. Verso's context engineering (ContextBundle, prefix discipline, inspect(), observation masking) is structural — it is NOT about writing better system prompts. The analogy: better prompts are the generative AI equivalent of "better artist intuition" — a workaround for missing control primitives, not a solution.

This validates §2 (non-goals): Verso is not a prompt engineering framework. Context engineering in Verso is architectural — structured preparation of the model's input, not decoration of the prompt string.

**Verdict:** confirm — cite in §5.2 and §2: context engineering is structural input discipline, not prompt decoration. The framing distinguishes Verso from prompt-engineering-centric tools.
