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


# --- ACI: a docstring Args: section becomes per-parameter JSON-schema descriptions ---
# (argument extraction is the tool-reliability failure point; the param doc is where the model reads it)

def test_docstring_args_become_param_descriptions():
    @tool
    def search(query: str, limit: int = 10) -> str:
        """Search the corpus.

        Args:
            query: the exact search string to look up.
            limit: maximum number of results to return.
        """
        return "ok"

    props = search.parameters["properties"]
    assert props["query"]["description"] == "the exact search string to look up."
    assert props["limit"]["description"] == "maximum number of results to return."
    # the tool-level description is the summary ONLY — the Args block is lifted onto the params
    assert search.description == "Search the corpus."


def test_docstring_arg_description_can_wrap_lines():
    @tool
    def f(path: str) -> str:
        """Read a file.

        Args:
            path: an absolute path to the file,
                not a relative one.
        """
        return path

    assert f.parameters["properties"]["path"]["description"] == (
        "an absolute path to the file, not a relative one."
    )


def test_arg_with_parenthetical_type_is_parsed():
    @tool
    def g(n: int) -> int:
        """Square a number.

        Args:
            n (int): the value to square.
        """
        return n * n

    assert g.parameters["properties"]["n"]["description"] == "the value to square."


def test_tool_without_args_section_is_byte_identical():
    # no Args: block ⇒ description unchanged, NO per-param descriptions injected (the default path)
    @tool
    def add(a: int, b: int) -> int:
        "Add two integers."
        return a + b

    assert add.description == "Add two integers."
    assert "description" not in add.parameters["properties"]["a"]
    assert "description" not in add.parameters["properties"]["b"]
