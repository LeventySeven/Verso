# tests/test_builtins.py
from verso.tools.builtins import think, done
from verso.tools.tool import Tool
from verso.types import StopReason


def test_think_and_done_are_tools():
    assert isinstance(think, Tool) and think.name == "think"
    assert isinstance(done, Tool) and done.name == "done"
    assert "thought" in think.parameters["properties"]
    assert "result" in done.parameters["properties"]


def test_done_returns_its_result():
    assert done.fn(result="the answer") == "the answer"


def test_stop_reason_done_exists():
    assert StopReason.DONE == "done"
