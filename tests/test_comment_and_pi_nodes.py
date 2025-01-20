import pytest

from delb import (
    CommentNode,
    Document,
    altered_default_filters,
    is_comment_node,
    new_comment_node,
    new_processing_instruction_node,
    new_tag_node,
    parse_tree,
)


def test_appended_text_node():
    root = parse_tree("<root><!-- c -->tail</root>")
    root.last_child.add_following_siblings("|appended")
    with altered_default_filters():
        assert str(root) == "<root><!-- c -->tail|appended</root>"


def test_comment_node():
    root = Document("<root><tag/><!-- comment -->text</root>").root

    with altered_default_filters():
        comment = root[1]

    assert isinstance(comment, CommentNode)
    assert comment.content == " comment "
    assert str(comment) == "<!-- comment -->"

    tag = root[0]
    tag.append_children(new_comment_node("b"))
    comment.content = "comment"
    with altered_default_filters():
        assert str(root) == "<root><tag><!--b--></tag><!--comment-->text</root>"

    assert comment == new_comment_node("comment")
    assert comment != tag
    with altered_default_filters(is_comment_node):
        assert comment != tag.first_child

    comment.detach()
    with altered_default_filters():
        assert str(root) == "<root><tag><!--b--></tag>text</root>"

        b = tag.first_child

    b.add_preceding_siblings(new_comment_node("a"))
    b.add_following_siblings(new_comment_node("c"))
    with altered_default_filters():
        assert str(root) == "<root><tag><!--a--><!--b--><!--c--></tag>text</root>"

    b.detach()
    with altered_default_filters():
        assert str(root) == "<root><tag><!--a--><!--c--></tag>text</root>"

    text = root.last_child
    x = new_comment_node("x")
    text.add_preceding_siblings(x)
    text.add_following_siblings(new_comment_node("y"))
    with altered_default_filters():
        assert (
            str(root) == "<root><tag><!--a--><!--c--></tag><!--x-->text<!--y--></root>"
        )

    with altered_default_filters():
        for node in tuple(root.iterate_children()):
            node.detach()

    root.add_preceding_siblings(new_comment_node("before"))
    root.add_following_siblings(new_comment_node("after"))

    with altered_default_filters():
        assert (
            str(root.document)
            == '<?xml version="1.0" encoding="UTF-8"?><!--before--><root/><!--after-->'
        )


@pytest.mark.parametrize("content", ("a--z", "foo-"))
def test_invalid_comment_content(content):
    with pytest.raises(ValueError, match=r"Invalid Comment content\."):
        new_comment_node(content)
    node = new_comment_node("comment")
    with pytest.raises(ValueError, match=r"Invalid Comment content\."):
        node.content = content


@pytest.mark.parametrize("target", ("xml", "XML", "xMl", ""))
def test_invalid_pi_target(target):
    with pytest.raises(ValueError, match=r".* target name\."):
        new_processing_instruction_node(target, "data")
    node = new_processing_instruction_node("target", "data")
    with pytest.raises(ValueError, match=r".* target name\."):
        node.target = target


def test_processing_instruction_node():
    root = parse_tree("<root/>")

    root.append_children(new_processing_instruction_node("foo", "bar"))

    with altered_default_filters():
        pi = root.first_child

    assert pi.target == "foo"
    assert pi.content == "bar"
    assert str(pi) == "<?foo bar?>"

    assert pi == new_processing_instruction_node("foo", "bar")
    assert pi != root
    assert pi != new_processing_instruction_node("ham", "bar")

    with altered_default_filters():
        assert str(root) == "<root><?foo bar?></root>"
    pi.target = "space"
    with altered_default_filters():
        assert str(root) == "<root><?space bar?></root>"

    assert new_tag_node("ham").local_name == "ham"
