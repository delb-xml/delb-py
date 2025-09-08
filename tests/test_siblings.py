import pytest

from delb import TextNode
from _delb.nodes import Siblings


def test_index():
    with pytest.raises(IndexError):
        Siblings(None, ()).index(TextNode("foo"))


def test_invalid_getitem_type():
    siblings = Siblings(None, ())
    with pytest.raises(TypeError):
        siblings["a"]


def test_invalid_sibling_type():
    siblings = Siblings(None, ())
    with pytest.raises(TypeError):
        siblings.append(0)
