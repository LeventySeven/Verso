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
