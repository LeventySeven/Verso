# tests/test_ask_once_persistence.py
# Durable HITL: ask_once caches the already-prompted set in the decider's closure, so a durable run that
# resumes in a FRESH process used to re-prompt for an already-decided tool (the seam survives the restart;
# the approval didn't). Optional `remembered` (restore) + `on_remember` (persist) close that — Verso owns
# no store, the caller provides persistence. Both default None => in-memory, byte-identical to before.
from verso import ask_once
from verso.safety.hooks import PermissionDecision as P


def test_ask_once_unchanged_when_no_persistence():
    d = ask_once("send_email")
    assert d(("send_email", {})) is P.ASK       # first time -> ASK
    assert d(("send_email", {})) is P.ALLOW     # thereafter -> ALLOW (byte-identical to before)
    assert d(("read_file", {})) is P.ALLOW      # unnamed tool -> ALLOW


def test_remembered_restores_and_skips_reprompt():
    # simulate a fresh process where the prior session persisted "send_email"
    d = ask_once("send_email", remembered={"send_email"})
    assert d(("send_email", {})) is P.ALLOW     # already decided last session -> no re-ASK


def test_on_remember_fires_once_per_tool_at_first_prompt():
    persisted: list[str] = []
    d = ask_once("send_email", "refund", on_remember=persisted.append)
    assert d(("send_email", {})) is P.ASK
    assert d(("send_email", {})) is P.ALLOW     # second time: already seen -> no duplicate persist
    assert d(("refund", {})) is P.ASK
    assert persisted == ["send_email", "refund"]    # each persisted exactly once, at its first prompt


def test_persist_restore_roundtrip_survives_a_restart():
    store: set[str] = set()                     # the caller's durable store (a DB row, a file, etc.)
    d1 = ask_once("send_email", remembered=store, on_remember=store.add)
    assert d1(("send_email", {})) is P.ASK      # session 1: prompt once + persist
    assert "send_email" in store
    # session 2 = a fresh process: rebuild the decider from the persisted store
    d2 = ask_once("send_email", remembered=store, on_remember=store.add)
    assert d2(("send_email", {})) is P.ALLOW    # no re-prompt — the approval survived the "restart"


def test_remembered_is_copied_not_mutated():
    caller_set = {"send_email"}
    d = ask_once("send_email", "refund", remembered=caller_set)
    d(("refund", {}))                            # would add "refund" to the internal seen set
    assert caller_set == {"send_email"}          # the caller's object is not mutated (we copy on build)
