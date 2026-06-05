# tests/test_tool.py
from verso.tools.tool import tool, Tool


def test_tool_builds_schema_from_signature():
    @tool
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    assert isinstance(add, Tool)
    assert add.name == "add"
    assert add.description == "Add two integers."
    props = add.parameters["properties"]
    assert props["a"]["type"] == "integer"
    assert props["b"]["type"] == "integer"
    assert set(add.parameters["required"]) == {"a", "b"}


def test_tool_optional_param_not_required():
    @tool
    def greet(name: str, loud: bool = False) -> str:
        """Greet someone."""
        return name

    assert "name" in add_required(greet)
    assert "loud" not in add_required(greet)


def add_required(t: Tool) -> set[str]:
    return set(t.parameters.get("required", []))


def test_tool_call_invokes_underlying_fn():
    @tool
    def mul(a: int, b: int) -> int:
        "Multiply."
        return a * b

    assert mul.fn(3, 4) == 12
