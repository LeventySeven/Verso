from verso import Agent, tool
from verso.evals.suite import Eval, Assertion
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse, ToolCall
from verso.types import Usage


@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b


def _agent(answer="3"):
    return Agent(model=FakeModel([
        ModelResponse(text="", tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 1, "b": 2})], usage=Usage()),
        ModelResponse(text=answer, tool_calls=[], usage=Usage()),
    ]), tools=[add])


# Deterministic, execution-grade assertions (the preferred tier).
called_add = Assertion("called_add", lambda s: "add" in s.tool_names())
answered_3 = Assertion("answered_3", lambda s: "3" in s.output)


async def test_unit_reports_per_case_pass_fail():
    report = await Eval.unit(
        agent_factory=lambda: _agent(),
        cases={"happy": "add 1 and 2"},
        assertions=[called_add, answered_3],
    )
    assert report.passed                                  # all assertions passed
    assert report.scores["happy"]["called_add"].passed
    assert report.scores["happy"]["answered_3"].kind == "assertion"   # deterministic tier


async def test_unit_surfaces_a_real_failure():
    report = await Eval.unit(
        agent_factory=lambda: _agent(answer="seven"),
        cases={"happy": "add 1 and 2"},
        assertions=[answered_3],
    )
    assert not report.passed
    assert not report.scores["happy"]["answered_3"].passed


async def test_pass_k_reports_distribution_not_a_point():
    # reliability is a distribution: run the same case k times, report the pass rate.
    rate = await Eval.pass_k(lambda: _agent(), "add 1 and 2", answered_3, k=5)
    assert rate == 1.0
