# Recipe: custom control flow in plain async Python

You do not need a graph DSL to orchestrate Verso agents. `agent.run()` is an
ordinary `async` call that returns an `AgentResult` — so the "graph" is just the
Python you already know: `if` for routing, `while` for retries, `asyncio.gather`
for fan-out. No node/edge bookkeeping, no framework to learn, full debugger
support.

## Routing — an `if` on a result

Run a cheap classifier agent, then branch to a specialist based on its output.

```python
async def handle(ticket: str) -> str:
    kind = (await classifier.run(ticket)).output.strip().lower()
    if kind == "billing":
        return (await billing_agent.run(ticket)).output
    if kind == "bug":
        return (await engineering_agent.run(ticket)).output
    return (await general_agent.run(ticket)).output
```

## Retry — a `while` with your own stop condition

The loop already retries tools and re-asks for structured output. For
*application-level* retries (e.g. "keep going until the draft passes my own
check"), wrap the call in a `while`:

```python
async def draft_until_ok(brief: str, max_tries: int = 3) -> str:
    feedback = ""
    for _ in range(max_tries):
        result = await writer.run(f"{brief}\n{feedback}".strip())
        if looks_good(result.output):          # your own predicate
            return result.output
        feedback = "Previous attempt was rejected; tighten it up."
    return result.output                       # best effort after max_tries
```

## Fan-out — `asyncio.gather` over independent runs

Independent sub-tasks run concurrently with `asyncio.gather`; then reduce the
results however you like.

```python
import asyncio

async def summarize_all(docs: list[str]) -> str:
    summaries = await asyncio.gather(*(summarizer.run(d) for d in docs))
    joined = "\n\n".join(s.output for s in summaries)
    return (await reducer.run(f"Combine these summaries:\n{joined}")).output
```

## When you need to steer mid-run

The three patterns above compose *whole runs*. To steer a *single* run from the
outside — cap its length, stop on a budget, halt on an external signal — use the
[`should_continue` hook](../../README.md): a predicate the loop checks at the top
of every step. Return `False` and the run ends cleanly with `END_TURN`.

```python
from verso import Agent
from verso.safety.hooks import Hooks

cap = {"left": 5}
def keep_going(bundle):
    cap["left"] -= 1
    return cap["left"] >= 0                 # stop after 5 steps, whatever the model wants

agent = Agent(model=..., tools=[...], hooks=Hooks(should_continue=keep_going))
result = await agent.run(task)              # ends with StopReason.END_TURN when the cap trips
```

That is the whole story: ordinary async Python for between-run control flow, one
hook for within-run steering. No graph required.
