# verso/tools/builtins.py
from verso.tools.tool import tool


@tool
def think(thought: str) -> str:
    """Record a private reasoning step before acting. Use this to plan; it has no side effects."""
    return "noted"


@tool
def done(result: str) -> str:
    """Signal that the task is complete and return the final result to the user."""
    return result
