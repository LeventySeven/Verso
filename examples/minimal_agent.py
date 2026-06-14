# examples/minimal_agent.py
"""The floor: a complete Verso agent in well under 80 lines — one model, two tools, one run.
No checkpointer, no hooks, no memory, no graph. This is the whole surface you need to start.

Run:  uv run python examples/minimal_agent.py
Set ANTHROPIC_API_KEY first, or swap the init_model string for any provider — "openai:gpt-4o",
"groq:llama-3.3-70b-versatile", "google:gemini-2.0-flash", "ollama:llama3", … (see the README).
"""
import asyncio

from verso import Agent, init_model, tool


@tool
def add(a: int, b: int) -> int:
    "Add two integers."
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    "Multiply two integers."
    return a * b


async def main() -> None:
    agent = Agent(
        init_model("anthropic:claude-sonnet-4-6"),
        tools=[add, multiply],
        instructions="Use the tools to compute. Show your reasoning briefly.",
    )
    result = await agent.run("What is (12 + 30) * 7? Use the tools.")
    print(result.output, "·", result.stop_reason, "·", result.usage)


if __name__ == "__main__":
    asyncio.run(main())
