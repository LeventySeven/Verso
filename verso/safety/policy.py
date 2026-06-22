# verso/safety/policy.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Iterable

from verso.safety.hooks import PermissionDecision

ToolCallView = tuple[str, dict]                      # (tool_name, arguments) — same shape hooks use
Decider = Callable[[ToolCallView], PermissionDecision]


@dataclass
class PermissionRule:
    """One rule: if `match(call)` is True, the policy returns `decision`."""
    match: Callable[[ToolCallView], bool]
    decision: PermissionDecision


@dataclass
class PermissionPolicy:
    """A composable, priority-ordered permission policy. The first rule whose `match` is True decides;
    if none match, `default`. A policy IS a pre_tool hook — use it directly: `Hooks(pre_tool=[policy])`.
    Compose layers by ordering rules most-restrictive-first (deny a destructive tool before a broad allow)."""
    rules: list[PermissionRule] = field(default_factory=list)
    default: PermissionDecision = PermissionDecision.ALLOW

    def decide(self, call: ToolCallView) -> PermissionDecision:
        for r in self.rules:
            if r.match(call):
                return r.decision
        return self.default

    def __call__(self, call: ToolCallView) -> PermissionDecision:
        return self.decide(call)


# --- session-mode presets (each returns a pre_tool hook: (call) -> PermissionDecision) ---

def allow_all() -> Decider:
    """Auto-approve every tool — the tactical default, made explicit and nameable."""
    return lambda call: PermissionDecision.ALLOW


def ask_every(*tools: str) -> Decider:
    """ASK on each named tool every time (or on ALL tools if none named); allow the rest."""
    names = set(tools)
    def decide(call: ToolCallView) -> PermissionDecision:
        return PermissionDecision.ASK if (not names or call[0] in names) else PermissionDecision.ALLOW
    return decide


def ask_once(*tools: str, remembered: Iterable[str] | None = None,
             on_remember: Callable[[str], None] | None = None) -> Decider:
    """ASK the first time each (named) tool is seen, then ALLOW it thereafter — the 'approve once,
    trust for the session' UX. (It trusts after the first PROMPT, regardless of the human's answer.)
    State lives in the returned decider; build a fresh one per session.

    Durable persistence (optional — the seam-consistent path): pass `remembered` to RESTORE the
    already-prompted set from a prior session/process, and `on_remember(tool_name)` to be notified when a
    new tool is first prompted so you can PERSIST it — so a durable run that resumes in a fresh process does
    NOT re-prompt for an already-decided tool (the seam survives the restart; now the approval does too).
    Verso owns no store: the caller provides the persistence. Both default None → in-memory, session-scoped,
    byte-identical to before. `remembered` is copied, never mutated."""
    names: set[str] = set(tools)
    seen: set[str] = set(remembered or ())
    def decide(call: ToolCallView) -> PermissionDecision:
        name = call[0]
        if (not names or name in names) and name not in seen:
            seen.add(name)
            if on_remember is not None:
                on_remember(name)
            return PermissionDecision.ASK
        return PermissionDecision.ALLOW
    return decide


def confidence_router(score: Callable[[ToolCallView], float], *, ask_below: float = 0.7,
                      deny_below: float = 0.3) -> Decider:
    """Route by a confidence score in [0,1]: DENY below `deny_below`, ASK below `ask_below`, else ALLOW.
    `score` is your signal (a model logprob, a heuristic, a cheap classifier) — Verso doesn't prescribe it."""
    def decide(call: ToolCallView) -> PermissionDecision:
        s = score(call)
        if s < deny_below:
            return PermissionDecision.DENY
        if s < ask_below:
            return PermissionDecision.ASK
        return PermissionDecision.ALLOW
    return decide
