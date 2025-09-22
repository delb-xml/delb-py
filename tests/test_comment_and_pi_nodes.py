from copy import copy

import pytest

from delb import (
    CommentNode,
    Document,
    ProcessingInstructionNode,
    parse_tree,
)
from delb.filters import altered_default_filters, is_comment_node


def test_appended_text_node():
    root = parse_tree("<root><!-- c -->tail</root>")
    root.last_child.add_following_siblings("|appended")
    assert str(root) == "<root><!-- c -->tail|appended</root>"


def test_comment_node():
    root = Document("<root><tag/><!-- comment -->text</root>").root

    with altered_default_filters():
        comment = root[1]

    assert isinstance(comment, CommentNode)
    assert comment.content == " comment "
    assert str(comment) == "<!-- comment -->"

    tag = root[0]
    tag.append_children(CommentNode("b"))
    comment.content = "comment"
    assert str(root) == "<root><tag><!--b--></tag><!--comment-->text</root>"

    assert comment == CommentNode("comment")
    assert comment != tag
    with altered_default_filters(is_comment_node):
        assert comment != tag.first_child

    comment.detach()
    assert str(root) == "<root><tag><!--b--></tag>text</root>"

    with altered_default_filters():
        b = tag.first_child

    b.add_preceding_siblings(CommentNode("a"))
    b.add_following_siblings(CommentNode("c"))
    assert str(root) == "<root><tag><!--a--><!--b--><!--c--></tag>text</root>"

    b.detach()
    assert str(root) == "<root><tag><!--a--><!--c--></tag>text</root>"

    text = root.last_child
    x = CommentNode("x")
    text.add_preceding_siblings(x)
    text.add_following_siblings(CommentNode("y"))
    assert str(root) == "<root><tag><!--a--><!--c--></tag><!--x-->text<!--y--></root>"

    with altered_default_filters():
        for node in tuple(root.iterate_children()):
            node.detach()

    root.add_preceding_siblings(CommentNode("before"))
    root.add_following_siblings(CommentNode("after"))

    assert (
        str(root.document)
        == '<?xml version="1.0" encoding="UTF-8"?><!--before--><root/><!--after-->'
    )

    with pytest.raises(ValueError, match=r"Invalid XML character data\."):
        comment.content = "\x00"

    clone = copy(comment)
    assert comment == clone
    assert comment is not clone


@pytest.mark.parametrize("content", ("a--z", "foo-"))
def test_invalid_comment_content(content):
    with pytest.raises(ValueError, match=r"Invalid Comment content\."):
        CommentNode(content)
    node = CommentNode("comment")
    with pytest.raises(ValueError, match=r"Invalid Comment content\."):
        node.content = content


@pytest.mark.parametrize(
    ("content", "message"),
    (
        ("\x00", r"Invalid XML character data\."),
        ("blob?>blob", r"Content text must not contain '\?>'\."),
    ),
)
def test_invalid_pi_content(content, message):
    with pytest.raises(ValueError, match=message):
        ProcessingInstructionNode("target", content)


@pytest.mark.parametrize("target", ("xml", "XML", "xMl", ""))
def test_invalid_pi_target(target):
    with pytest.raises(ValueError, match=r".* target name\."):
        ProcessingInstructionNode(target, "data")
    node = ProcessingInstructionNode("target", "data")
    with pytest.raises(ValueError, match=r".* target name\."):
        node.target = target


def test_processing_instruction_node():
    root = parse_tree("<root/>")

    root.append_children(ProcessingInstructionNode("foo", "bar"))

    with altered_default_filters():
        pi = root.first_child

    assert pi.target == "foo"
    assert pi.content == "bar"
    assert str(pi) == "<?foo bar?>"

    assert pi == ProcessingInstructionNode("foo", "bar")
    assert pi != root
    assert pi != ProcessingInstructionNode("ham", "bar")

    assert str(root) == "<root><?foo bar?></root>"
    pi.target = "space"
    assert str(root) == "<root><?space bar?></root>"

    clone = copy(pi)
    assert pi == clone
    assert pi is not clone

    # in _ChildLessNode:
    assert pi.full_text == ""
    assert len(pi) == 0

    for _ in pi.iterate_children():
        raise AssertionError

    for _ in pi.iterate_descendants():
        raise AssertionError
