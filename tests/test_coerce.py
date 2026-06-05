# tests/test_coerce.py
import pytest
from pydantic import BaseModel
from verso.tools.coerce import coerce, CoercionError


class Point(BaseModel):
    x: int
    y: int


def test_coerce_clean_json_into_model():
    p = coerce('{"x": 1, "y": 2}', Point)
    assert isinstance(p, Point) and p.x == 1 and p.y == 2


def test_coerce_from_messy_text():
    p = coerce('Here: ```json\n{"x": 3, "y": 4}\n```', Point)
    assert p.x == 3 and p.y == 4


def test_coerce_unparseable_raises_coercion_error():
    with pytest.raises(CoercionError):
        coerce("no json here", Point)


def test_coerce_schema_mismatch_raises_coercion_error():
    with pytest.raises(CoercionError):
        coerce('{"x": "not-an-int", "y": 2}', Point)


def test_coerce_list_type():
    assert coerce("[1, 2, 3]", list[int]) == [1, 2, 3]
