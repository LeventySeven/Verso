# tests/test_evals_outcome.py
from verso import Agent
from verso.evals.outcome import define_outcome
from verso.evals.span import VersoScore
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse
from verso.types import Usage


def _agent(answers):
    return Agent(model=FakeModel([ModelResponse(text=a, tool_calls=[], usage=Usage()) for a in answers]))


async def test_stops_on_pass():
    # grader passes on attempt 2 → exactly 2 generations, loop stops.
    attempts = {"n": 0}
    def grader(span) -> VersoScore:
        attempts["n"] += 1
        return VersoScore("rubric", passed=(attempts["n"] >= 2), value=1.0)
    result = await define_outcome(_agent(["v1", "v2", "v3"]), "task", grader, max_iterations=3)
    assert result.passed and result.iterations == 2


async def test_is_bounded_never_unbounded():
    # grader never passes → must stop at max_iterations, not loop forever.
    result = await define_outcome(_agent(["a", "b", "c", "d"]), "task",
                                  lambda span: VersoScore("rubric", passed=False), max_iterations=3)
    assert not result.passed and result.iterations == 3
