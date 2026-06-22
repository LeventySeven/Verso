# tests/test_builtins.py
from verso.tools.builtins import think, done, todo
from verso.tools.dispatch import dispatch
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


# --- todo: an agent-owned, recited plan checklist (think/done's sibling builtin) ---

def test_todo_is_a_tool_with_items_param():
    assert isinstance(todo, Tool) and todo.name == "todo"
    assert "items" in todo.parameters["properties"]


def test_todo_renders_a_status_marked_checklist():
    # dispatch passes items as dicts (validated.model_dump()), so the fn body must accept dicts
    out = todo.fn(items=[
        {"content": "scope the task", "status": "completed"},
        {"content": "write the code", "status": "in_progress"},
        {"content": "run the tests", "status": "pending"},
    ])
    assert "[x] scope the task" in out
    assert "[~] write the code" in out
    assert "[ ] run the tests" in out


def test_todo_empty_plan_is_safe():
    assert todo.fn(items=[]) == "(no items)"


async def test_todo_dispatches_with_dict_items_and_defaults_status():
    # the REAL contract: the model emits dict items; status omitted defaults to pending
    res = await dispatch(todo, {"items": [{"content": "first step"}]})
    assert res.ok and "[ ] first step" in res.data


async def test_todo_rejects_unknown_status():
    # a Literal status is enforced by the generated args model (typed @tool is THE path)
    res = await dispatch(todo, {"items": [{"content": "x", "status": "bogus"}]})
    assert not res.ok and "ValidationError" in res.error
