# tests/test_history_merge.py
from verso.model.base import Message
from verso.context.history import merge_messages, RemoveMessage, REMOVE_ALL_MESSAGES
from verso.durable.serde import msg_to_dict, msg_from_dict


def test_dedup_replaces_in_place():
    existing = [
        Message(role="assistant", content="a", id="m1"),
        Message(role="user", content="b", id="m2"),
    ]
    result = merge_messages(existing, [Message(role="assistant", content="A!", id="m1")])
    assert len(result) == 2                       # replaced, not appended
    assert result[0].content == "A!"              # m1 updated in its original position
    assert result[1].content == "b"               # m2 untouched, order preserved


def test_new_id_appends_and_keeps_order():
    existing = [
        Message(role="assistant", content="a", id="m1"),
        Message(role="user", content="b", id="m2"),
    ]
    result = merge_messages(existing, [Message(role="assistant", content="c", id="m3")])
    assert [m.id for m in result] == ["m1", "m2", "m3"]
    assert result[-1].content == "c"


def test_no_id_messages_always_append_and_do_not_collide():
    result = merge_messages(
        [Message(role="user", content="x")],
        [Message(role="assistant", content="y")],
    )
    assert len(result) == 2                        # two id=None messages don't dedup against each other
    assert [m.content for m in result] == ["x", "y"]


def test_remove_message_drops_target():
    existing = [
        Message(role="assistant", content="a", id="m1"),
        Message(role="user", content="b", id="m2"),
    ]
    result = merge_messages(existing, [RemoveMessage("m2")])
    assert len(result) == 1
    assert result[0].id == "m1"


def test_remove_all_then_replace_is_compaction():
    existing = [
        Message(role="user", content="a", id="m1"),
        Message(role="assistant", content="b", id="m2"),
        Message(role="user", content="c", id="m3"),
    ]
    result = merge_messages(
        existing,
        [RemoveMessage(REMOVE_ALL_MESSAGES), Message(role="assistant", content="summary", id="s1")],
    )
    assert len(result) == 1                        # everything prior cleared, only post-marker survives
    assert result[0].content == "summary"
    assert result[0].id == "s1"


def test_does_not_mutate_existing():
    existing = [
        Message(role="assistant", content="a", id="m1"),
        Message(role="user", content="b", id="m2"),
    ]
    before_len = len(existing)
    before_first = existing[0]
    merge_messages(existing, [
        Message(role="assistant", content="A!", id="m1"),   # replace
        Message(role="user", content="c", id="m3"),         # append
        RemoveMessage("m2"),                                # remove
        RemoveMessage(REMOVE_ALL_MESSAGES),                 # clear
    ])
    assert len(existing) == before_len             # caller's list untouched
    assert existing[0] is before_first             # same object, not mutated in place
    assert existing[0].content == "a"


def test_serde_round_trips_id_and_stays_byte_identical_when_none():
    assert msg_from_dict(msg_to_dict(Message(role="user", content="x", id="k"))).id == "k"
    assert "id" not in msg_to_dict(Message(role="user", content="x"))   # additive, byte-identical default
