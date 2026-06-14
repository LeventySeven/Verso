# examples/orchestrator_workers.py
"""\"We don't force the graph.\" — orchestrator-workers in plain async Python.

No graph DSL, no nodes, no edges, no framework state machine: just Agents and asyncio.gather. An
orchestrator fans work out to worker agents that run concurrently, then synthesizes their results.
This is the exact pattern LangGraph/CrewAI wrap in a graph — here it is the language you already
know (if/while/gather), fully debuggable, ~25 lines of real logic.

Run:  uv run python examples/orchestrator_workers.py   (set ANTHROPIC_API_KEY, or swap the provider)
"""
import asyncio

from verso import Agent, init_model


async def map_reduce(docs: list[str]) -> str:
    model = init_model("anthropic:claude-sonnet-4-6")

    # MAP — one worker agent per doc, all running concurrently. The "fan-out" is just gather().
    worker = Agent(model, instructions="Summarize the given text in exactly one sentence.")
    summaries = await asyncio.gather(*(worker.run(doc) for doc in docs))

    # REDUCE — the orchestrator synthesizes the workers' outputs into one answer.
    bullets = "\n".join(f"- {s.output}" for s in summaries)
    orchestrator = Agent(model, instructions="Combine these bullet summaries into one tight paragraph.")
    return (await orchestrator.run(bullets)).output


async def main() -> None:
    docs = [
        "Verso is a small Python agent framework: a ~10-line ReAct loop done right.",
        "Its seam promotes a tactical run to a durable one (checkpoint/resume/HITL) with one flag.",
        "It refuses the forced graph — orchestration is plain async Python, like this file.",
    ]
    print(await map_reduce(docs))


if __name__ == "__main__":
    asyncio.run(main())
