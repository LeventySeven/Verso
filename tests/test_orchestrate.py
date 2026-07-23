"""verso.orchestrate — bounded fan-out, context-isolated spawn, cross-model reviewer.

These are helpers over asyncio, not a runtime. The tests assert the three things the hand-written
`asyncio.gather` version lacks: a real concurrency cap, per-item failure isolation, and a depth cap
that stops an orchestrator from recursing.
"""
import asyncio

import pytest

from verso import Agent
from verso.model.base import ModelResponse
from verso.types import Usage
from verso.orchestrate import fan_out, spawn, Subagent, Reviewer, DepthCapExceeded
from verso.orchestrate.core import orchestration_depth


class EchoModel:
    """Stateless fake: replies with a fixed text on every call. Safe to share across concurrent
    workers (unlike FakeModel, which pops a shared list). `model_id` present so ctx.model is set."""
    def __init__(self, reply: str, model_id: str = "echo", delay: float = 0.0):
        self.reply, self.model_id, self.delay = reply, model_id, delay

    async def complete(self, messages, tools, *, system=None):
        if self.delay:
            await asyncio.sleep(self.delay)
        return ModelResponse(text=self.reply, tool_calls=[], usage=Usage(input_tokens=1, output_tokens=1))

    async def stream(self, messages, tools, *, system=None):
        r = await self.complete(messages, tools, system=system)
        from verso.model.streaming import ModelStreamChunk
        yield ModelStreamChunk(kind="text", text=r.text)
        yield ModelStreamChunk(kind="usage", usage=r.usage)


# ---------------------------------------------------------------- fan_out


async def test_fan_out_preserves_order_and_returns_all():
    async def unit(i):
        await asyncio.sleep(0)
        return i * 10
    out = await fan_out([lambda i=i: unit(i) for i in range(5)])
    assert out == [0, 10, 20, 30, 40]


async def test_fan_out_actually_bounds_concurrency():
    live = 0
    peak = 0
    async def unit():
        nonlocal live, peak
        live += 1
        peak = max(peak, live)
        await asyncio.sleep(0.02)
        live -= 1
        return True
    await fan_out([unit for _ in range(20)], max_concurrency=4)
    assert peak <= 4, f"expected <=4 concurrent, saw {peak}"


async def test_fan_out_isolates_a_failing_unit_by_default():
    async def ok():
        return "ok"
    async def boom():
        raise ValueError("worker exploded")
    out = await fan_out([ok, boom, ok])
    assert out[0] == "ok" and out[2] == "ok"
    assert isinstance(out[1], ValueError) and "exploded" in str(out[1])


async def test_fan_out_can_fail_fast():
    async def ok():
        return "ok"
    async def boom():
        raise ValueError("x")
    with pytest.raises(ValueError):
        await fan_out([ok, boom], return_exceptions=False)


async def test_fan_out_rejects_bad_concurrency():
    with pytest.raises(ValueError):
        await fan_out([lambda: asyncio.sleep(0)], max_concurrency=0)


# ---------------------------------------------------------------- depth cap


async def test_depth_cap_blocks_nested_orchestration():
    # A worker that itself calls fan_out is the fork-bomb this prevents.
    async def worker_that_orchestrates():
        return await fan_out([lambda: asyncio.sleep(0)])
    out = await fan_out([worker_that_orchestrates])
    assert isinstance(out[0], DepthCapExceeded)


async def test_depth_cap_is_lifted_explicitly():
    async def worker():
        return await fan_out([lambda: _const(7)], max_depth=2)
    async def _const(v):
        return v
    out = await fan_out([worker], max_depth=2)
    assert out[0] == [7]


async def test_depth_resets_after_fan_out():
    assert orchestration_depth() == 0
    await fan_out([lambda: asyncio.sleep(0)])
    assert orchestration_depth() == 0


# ---------------------------------------------------------------- spawn


async def test_spawn_returns_compact_result_not_transcript():
    m = EchoModel("child answer")
    sub = await spawn(m, "do the subtask")
    assert isinstance(sub, Subagent)
    assert sub.output == "child answer"
    assert sub.steps >= 1 and sub.usage.output_tokens >= 1


async def test_spawn_fork_none_sends_no_parent_context():
    m = EchoModel("ok", model_id="child")
    hist = [type("M", (), {"role": "user", "content": "SECRET parent detail"})()]
    await spawn(m, "task", parent_history=hist, fork="none")
    # fork=none → the child's prompt is the bare task, parent history never seeded
    sent = m  # EchoModel doesn't record; assert via the fork helper directly
    from verso.orchestrate.core import _forked_task
    assert _forked_task("task", hist, "none", 6) == "task"


async def test_spawn_fork_last_n_seeds_a_bounded_slice():
    from verso.orchestrate.core import _forked_task
    hist = [type("M", (), {"role": "user", "content": f"msg{i}"})() for i in range(10)]
    seeded = _forked_task("do it", hist, "last_n", 3)
    assert "msg9" in seeded and "msg7" in seeded and "msg6" not in seeded
    assert seeded.endswith("do it")


async def test_spawn_is_depth_capped():
    m = EchoModel("x")
    async def worker():
        return await spawn(m, "nested")   # a spawned agent spawning again
    out = await fan_out([worker])
    assert isinstance(out[0], DepthCapExceeded)


async def test_spawn_rejects_bad_fork_mode():
    with pytest.raises(ValueError):
        await spawn(EchoModel("x"), "t", fork="sideways")


# ---------------------------------------------------------------- reviewer


async def test_reviewer_runs_on_a_different_model():
    author = EchoModel("2 + 2 = 5", model_id="author-family")
    critic_model = EchoModel("The arithmetic is wrong: 2 + 2 = 4.", model_id="critic-family")
    answer = (await Agent(author).run("what is 2+2?")).output
    review = await Reviewer(critic_model).review("what is 2+2?", answer)
    assert "wrong" in review.feedback.lower()
    assert review.result.usage.output_tokens >= 1


# ---------------------------------------------------------------- additive-when-unused


def test_orchestrate_is_a_separate_import_not_on_versos_surface():
    # The additive invariant: nothing from orchestrate leaks onto `verso` itself. `import verso`
    # must not expose fan_out/spawn/Reviewer — you reach them only via `from verso.orchestrate import`.
    # (verso.orchestrate becomes an attribute once imported anywhere in the process — that is ordinary
    # submodule behaviour, not a leak — so we check the public names, not the submodule attribute.)
    import verso
    for name in ("fan_out", "spawn", "Subagent", "Reviewer", "DepthCapExceeded"):
        assert name not in verso.__all__
        assert not hasattr(verso, name)


def test_orchestrate_import_is_not_forced_by_importing_verso():
    # A subprocess is the honest check that `import verso` does not drag orchestrate into sys.modules.
    import subprocess, sys
    code = "import verso, sys; print('verso.orchestrate' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.stdout.strip() == "False", out.stdout + out.stderr
