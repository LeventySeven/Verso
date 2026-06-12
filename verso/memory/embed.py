# verso/memory/embed.py
from __future__ import annotations
import hashlib
import math
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    dim: int
    def embed(self, text: str) -> list[float]: ...


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))          # inputs are L2-normalized → dot == cosine


class HashEmbedder:
    """Deterministic, offline dev embedder: hash char-trigrams into a fixed-dim bag, L2-normalize.
    Good enough that near-identical text scores high; swap a real semantic embedder for production
    (the Embedder protocol is the seam). The FTS5 lexical arm carries real retrieval quality."""
    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        t = f"  {text.lower().strip()}  "
        for i in range(len(t) - 2):
            h = int(hashlib.blake2b(t[i:i+3].encode(), digest_size=8).hexdigest(), 16)
            v[h % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]
