# tests/test_evals_judge.py
from verso.evals.judge import LLMJudge, JudgePanel
from verso.evals.span import VersoSpan, SpanRecord
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


def _judge(verdict):  # one judge whose model returns a fixed verdict
    return LLMJudge(model=FakeModel([ModelResponse(text=verdict, tool_calls=[], usage=Usage())]), rubric="...")


async def test_panel_aggregates_by_majority_no_single_vendor():
    # 3 judges (the Character.AI-style panel is the OVERRIDABLE example default, not hardcoded vendors)
    panel = JudgePanel([_judge('{"passed": true, "value": 0.9}'),
                        _judge('{"passed": true, "value": 0.8}'),
                        _judge('{"passed": false, "value": 0.2}')])
    score = await panel.score(VersoSpan(trace_id="x", output="ok"))
    assert score.passed and score.kind == "judge"      # 2/3 majority → pass
    assert 0.6 < score.value < 0.7                      # mean of [0.9,0.8,0.2] ≈ 0.633


def test_step_pass_rate_is_separate_from_end_to_end():
    # per-step (did each tool call succeed) is distinct from the end-to-end answer being right (§5.5)
    span = VersoSpan(trace_id="x", records=[
        SpanRecord(kind="tool", name="a", ok=True), SpanRecord(kind="tool", name="b", ok=False)])
    assert span.step_pass_rate() == 0.5
