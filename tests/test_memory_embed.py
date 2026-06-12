# tests/test_memory_embed.py
from verso.memory.embed import HashEmbedder, cosine


def test_embed_is_deterministic_and_normalized():
    e = HashEmbedder(dim=64)
    v1, v2 = e.embed("the cat sat"), e.embed("the cat sat")
    assert v1 == v2                                   # deterministic
    assert abs(sum(x * x for x in v1) - 1.0) < 1e-6   # L2-normalized


def test_similar_text_scores_higher_than_unrelated():
    e = HashEmbedder(dim=128)
    base = e.embed("database connection pooling")
    near = e.embed("database connection pool")
    far = e.embed("strawberry cake recipe")
    assert cosine(base, near) > cosine(base, far)
