# tests/test_tokens.py
from verso.context.tokens import estimate_tokens


def test_empty_is_zero():
    assert estimate_tokens("") == 0


def test_roughly_chars_over_four():
    assert estimate_tokens("a" * 40) == 10


def test_nonempty_is_at_least_one():
    assert estimate_tokens("hi") >= 1
