# Verso

A Python agent framework whose primitive is *the boring core done right*: one clean async ReAct loop, with the two things every other framework buries made first-class — **context engineering** and **evals + reliability**.

Its organizing idea is the **tactical↔durable seam**: the same agent runs ephemeral-and-simple by default and is *promoted* to durable (event-sourced, checkpoint-resume, human-in-the-loop) with one flag — never a rewrite, never a forced graph.

> The pitch, and the counter-position to LangGraph/CrewAI: **we don't force the graph.**

## Quickstart (Phase 0 — walking skeleton)

```python
import asyncio
from verso import Agent, tool, init_model

@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b

async def main():
    agent = Agent(model=init_model("anthropic:claude-sonnet-4-6"), tools=[add])
    result = await agent.run("What is 20 + 22? Use the add tool.")
    print(result.output, "·", result.stop_reason, "·", result.usage)

asyncio.run(main())
```

Set `ANTHROPIC_API_KEY` first. Tests run offline via a `FakeModel`: `uv run pytest`.

**Structured output** — ask for a type and get it back parsed:

```python
from pydantic import BaseModel

class Point(BaseModel):
    x: int
    y: int

result = await agent.run("Give me a point at 1,2 as JSON.", output_type=Point)
print(result.parsed)            # Point(x=1, y=2)  — reasks once if the model's first answer won't parse
```

**`done` tool** — explicit, structured termination instead of sentinel strings:

```python
from verso.tools import builtins
agent = Agent(model=..., tools=[builtins.done, my_tool])   # loop ends when the model calls done(result=...)
```

**Inspect the context** — see exactly what the model will receive (byte-for-byte):

```python
agent = Agent(model=..., tools=[add], instructions="Be terse.", max_context_tokens=8000)
print(agent.inspect("What is 2+2?").render())
# [system] Be terse.
# [tools] [{"description": "...", "name": "add", "parameters": {...}}]
# [user] What is 2+2?
```

Instructions become a stable **system** prefix (KV-cache friendly); when the running context exceeds `max_context_tokens`, old tool outputs are masked (`prune()`), never silently dropped.

**Reliability** — retry + cross-model failover, error-typed:

```python
from verso import Agent, FailoverModel, RetryPolicy, init_model

model = FailoverModel(
    [init_model("anthropic:claude-sonnet-4-6"), init_model("anthropic:claude-opus-4-8")],
    retry=RetryPolicy(max_attempts=6, initial=4.0, max=240.0),
)
agent = Agent(model=model)
# transient errors + rate limits retry with backoff, then fail over to the next candidate;
# auth / content-policy errors raise immediately (no blind retry). Every try is in model.attempts.
```

**Streaming** — a typed, true-delta event stream (and SSE for HTTP):

```python
async for ev in agent.stream("What is 2+2? Use the add tool."):
    if ev.type.value == "message.delta":
        print(ev.text, end="", flush=True)
    elif ev.type.value == "tool.start":
        print(f"\n[calling {ev.tool}({ev.arguments})]")
    elif ev.type.value == "done":
        print("\n", ev.result.stop_reason)

# ship it over HTTP:
from verso.stream.sse import sse
async for frame in sse(agent.stream("...")):   # 'data: {json}\n\n' ... 'data: [DONE]\n\n'
    ...
```

## Status

Design-locked, pre-implementation. The full v1 design lives in **[`docs/PRD_v1.md`](docs/PRD_v1.md)**.

## How this was built

The design is grounded in evidence, not vibes:

1. **Thesis verification** — the "keep it simple, everything else is legacy in 1–2 years" thesis was verified across three independent research layers before any design. See [`research/THESIS_VERIFICATION.md`](research/THESIS_VERIFICATION.md). Verdict: the *instinct* is frontier consensus; the *absolutes* ("90% with a simple agent", "graphs always overkill", "1–2 year shelf life") are opinion/prediction, and two specific claims were factually corrected.
2. **Harvest** — 54 reverse-engineered design notes + 3 synthesis briefs distilled from agent-framework, coding/research-agent, and LLM-infra teardowns plus practitioner sources, under [`research/`](research/):
   - `01_bad_guide/` — field-manual sources (Karpathy, Anthropic, context-engineering, evals, primitives-not-wrappers)
   - `02_core/` — agentic-architecture corpus + practitioner transcripts
   - `03_teardowns/` — RE of LangChain/LangGraph, CrewAI, Letta, Claude Agent SDK, Cursor, Codex, Devin, Perplexity, model-routing/retrieval/vector-memory infra
   - `04_bad_guide_full/` — founder-OS / go-to-market layer: a 244-source deep index of *The Bad Guide* (`INDEX.md`) + a synthesis (cross-cutting frameworks, distribution playbook, taste checklists, fundraising, operating loop, Verso GTM)
   - `05_re_targets/` — gap analysis: `teardowns/` cross-referenced against the mid-2026 agentic landscape → a prioritized RE-target list (`TARGETS.md`)
   - `06_design_resolutions/` — per-subsystem resolutions turning the RE into concrete Verso decisions + component specs (`_RESOLUTIONS.md`)
   - `07_adversarial/` — a 30-agent adversarial audit of those decisions (`_VERDICT.md`): per-decision verdicts + the build/compose/defer v1 scope
3. **Design** — the PRD ([`docs/PRD_v1.md`](docs/PRD_v1.md)) synthesizes the technical layers into a phased, dogfood-first build plan, **adversarially audited**: §10 resolved decisions, §12 positioning + the demo-able wedge, §13 the BUILD vs COMPOSE vs DEFER v1 scope — build the loop + context + `jsonish` parser; compose DBOS / Mem0 / Langfuse / Instructor; defer owned engines until dogfood proves the gap.

## Non-goals

Not an SDK, not a graph-DSL by default, not the model/kernel, not MCP-first (native Python `@tool` is the tool path; MCP is an opt-in adapter), not multi-language (Python only, no Rust), not a router/planner cult.
