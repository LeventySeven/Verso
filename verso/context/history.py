# verso/context/history.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

from verso.model.base import Message

REMOVE_ALL_MESSAGES = "__remove_all__"


@dataclass
class RemoveMessage:
    """A marker passed through merge_messages to delete history by id (LangGraph RemoveMessage port).
    id == a message's id → drop that message; id == REMOVE_ALL_MESSAGES → clear everything accumulated so far."""
    id: str


def merge_messages(existing: Sequence[Message],
                   incoming: Sequence[Message | RemoveMessage]) -> list[Message]:
    """`add_messages`-style reducer for safe compaction (OPT-IN utility; NOT wired into the loop).
    - a Message whose `.id` matches an accumulated message's `.id` REPLACES it in place (dedup, not append)
    - a Message with a new id, or no id (`id is None`), is APPENDED — no-id messages always append (a
      documented limitation: give a message an `id` to make it dedup-able/removable)
    - RemoveMessage(id=X) drops the accumulated message with `.id == X`
    - RemoveMessage(id=REMOVE_ALL_MESSAGES) clears everything accumulated so far (the compaction reset)
    Returns a NEW list; never mutates `existing`."""
    result = list(existing)
    for item in incoming:
        if isinstance(item, RemoveMessage):
            result = [] if item.id == REMOVE_ALL_MESSAGES else [m for m in result if m.id != item.id]
            continue
        if item.id is not None and any(m.id == item.id for m in result):
            result = [item if m.id == item.id else m for m in result]   # replace in place, preserve order
        else:
            result.append(item)
    return result


def repair_history(history: Sequence[Message]) -> list[Message]:
    """Make a possibly-malformed message history (crash-recovered, forked, or hand-built) into a VALID
    provider payload — shape-preserving (no-op) on a healthy history. Fixes the structural faults that
    otherwise cause cryptic provider 400s on durable resume:
      - an assistant tool_call with NO matching tool result -> append a synthetic '[interrupted]' result
      - a tool result with NO matching assistant tool_call   -> drop it (orphan)
      - a duplicate tool_call_id among results               -> keep the first
    Tool results are emitted right after the assistant turn that opened them, in tool_call order (already
    true for a healthy fresh history → the sequence is preserved; a resume-shaped history whose results
    arrived out of tool_call order is normalized to that order — benign, providers match by id). Returns a
    NEW list; never mutates `history`."""
    results: dict[str, Message] = {}
    for m in history:
        if m.role == "tool" and m.tool_call_id is not None and m.tool_call_id not in results:
            results[m.tool_call_id] = m         # first occurrence wins (dedup)
    out: list[Message] = []
    consumed: set[str] = set()
    for m in history:
        if m.role == "tool":
            continue                            # re-emitted below, right after the assistant turn
        out.append(m)
        if m.role == "assistant" and m.tool_calls:
            for tc in m.tool_calls:
                if tc.id in consumed:
                    continue
                consumed.add(tc.id)
                out.append(results.get(tc.id) or Message(
                    role="tool", tool_call_id=tc.id, name=tc.name,
                    content="[interrupted: no tool result was recorded]"))
    return out
