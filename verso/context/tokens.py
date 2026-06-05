# verso/context/tokens.py
from __future__ import annotations

CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Cheap, provider-agnostic token estimate (~chars/4). Approximate BY DESIGN —
    used for budget guards, not billing. Swap for a real tokenizer later."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)
