# tests/test_prune_edge.py — slate D3: prune(keep_last_n<=0) must mask ALL (the [:-0] slice gotcha)
from verso.context.prune import prune, MASK
from verso.model.base import Message


def _tools(n: int) -> list[Message]:
    return [Message(role="tool", content=f"obs{i}", tool_call_id=str(i), name="t") for i in range(n)]


def test_keep_last_n_zero_masks_all():
    out = prune(_tools(5), keep_last_n=0)
    assert all(m.content == MASK for m in out)        # keep none -> every tool result masked


def test_negative_keep_last_n_treated_as_zero_masks_all():
    out = prune(_tools(3), keep_last_n=-2)
    assert all(m.content == MASK for m in out)        # negative -> 0, not "mask the wrong end"


def test_default_keeps_recent_unmasked():
    out = prune(_tools(15))                            # keep_last_n=10 default
    masked = [m for m in out if m.content == MASK]
    assert len(masked) == 5 and out[-1].content == "obs14"   # 5 oldest masked, recent kept (unchanged)
