# examples/orchestrate_helpers.py
"""The opt-in `verso.orchestrate` helpers — bounded fan-out, context-isolated spawn, cross-model review.

`orchestrator_workers.py` shows the pattern in raw `asyncio.gather` (the "we don't force the graph"
proof). This file shows the three helpers you reach for once the hand-rolled version starts wanting a
concurrency cap, failure isolation, sub-agent context isolation, or a critic — none of which is a
graph, all of which are ~one line here.

Run:  uv run python examples/orchestrate_helpers.py   (set ANTHROPIC_API_KEY, or swap the provider)
"""
import asyncio

from verso import Agent, init_model
from verso.orchestrate import fan_out, spawn, Reviewer


async def main() -> None:
    model = init_model("anthropic:claude-sonnet-4-6")
    docs = [f"Document {i}: lorem ipsum about topic {i}." for i in range(12)]

    # 1) BOUNDED fan-out — 12 workers, at most 4 model calls in flight, order preserved, and a worker
    #    that raises lands as an exception in its slot instead of sinking the batch.
    worker = Agent(model, instructions="Summarize the text in one sentence.")
    results = await fan_out(
        [lambda d=d: worker.run(d) for d in docs],
        max_concurrency=4,
    )
    summaries = [r.output for r in results if not isinstance(r, Exception)]

    # 2) SPAWN — offload a synthesis into a sub-agent so its working tokens never enter this context;
    #    only the compact result comes back.
    synthesis = await spawn(
        model,
        "Combine these bullet summaries into one tight paragraph:\n" + "\n".join(f"- {s}" for s in summaries),
    )

    # 3) REVIEWER — a critic on a DIFFERENT model family checks the paragraph before you trust it.
    reviewer = Reviewer(init_model("openai:gpt-5.1"))
    review = await reviewer.review("Summarize these 12 documents into one paragraph.", synthesis.output)

    print("PARAGRAPH:\n", synthesis.output)
    print("\nREVIEW:\n", review.feedback)


if __name__ == "__main__":
    asyncio.run(main())
