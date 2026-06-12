# tests/test_evals_judge.py
from verso.evals.judge import LLMJudge
from verso.evals.span import VersoSpan
from verso.model.fake import FakeModel
from verso.model.base import ModelResponse
from verso.types import Usage


async def test_llm_judge_scores_a_span_posthoc_and_is_isolated():
    # The judge model returns a verdict; the judge sees ONLY the captured span, never the agent's
    # mutable state (the eval-gaming guard). FakeModel returns the judge's JSON verdict.
    judge_model = FakeModel([ModelResponse(text='{"passed": true, "value": 0.9, "detail": "answers the question"}', tool_calls=[], usage=Usage())])
    judge = LLMJudge(model=judge_model, rubric="Does the answer resolve the task?")
    span = VersoSpan(trace_id="x", output="the answer is 3", stop_reason="end_turn", steps=2)
    score = await judge.score(span)
    assert score.passed and score.value == 0.9 and score.kind == "judge"


async def test_judge_failure_is_a_score_not_an_exception():
    judge_model = FakeModel([ModelResponse(text='{"passed": false, "value": 0.1, "detail": "wrong number"}', tool_calls=[], usage=Usage())])
    judge = LLMJudge(model=judge_model, rubric="...")
    score = await judge.score(VersoSpan(trace_id="x", output="seven"))
    assert not score.passed
