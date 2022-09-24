from delb import (
    Document,
    is_comment_node,
    CommentNode,
    altered_default_filters,
    new_comment_node,
    new_processing_instruction_node,
)


def test_appended_text_node():
    document = Document("<root><!-- c -->tail</root>")
    document.root.last_child.add_following_siblings("|appended")
    assert str(document) == "<root><!-- c -->tail|appended</root>"


def test_comment_node():
    document = Document("<root><tag/><!-- comment -->text</root>")
    root = document.root

    with altered_default_filters():
        comment = root[1]

    assert isinstance(comment, CommentNode)
    assert comment.content == " comment "
    assert str(comment) == "<!-- comment -->"

    tag = root[0]
    tag.append_children(new_comment_node("b"))
    comment.content = "comment"
    assert str(root) == "<root><tag><!--b--></tag><!--comment-->text</root>"

    assert comment == new_comment_node("comment")
    assert comment != tag
    with altered_default_filters(is_comment_node):
        assert comment != tag.first_child

    comment.detach()
    assert str(root) == "<root><tag><!--b--></tag>text</root>"

    with altered_default_filters():
        b = tag.first_child

    b.add_preceding_siblings(new_comment_node("a"))
    b.add_following_siblings(new_comment_node("c"))
    assert str(root) == "<root><tag><!--a--><!--b--><!--c--></tag>text</root>"

    b.detach()
    assert str(root) == "<root><tag><!--a--><!--c--></tag>text</root>"

    text = root.last_child
    x = new_comment_node("x")
    text.add_preceding_siblings(x)
    text.add_following_siblings(new_comment_node("y"))
    assert str(root) == "<root><tag><!--a--><!--c--></tag><!--x-->text<!--y--></root>"

    with altered_default_filters():
        for node in [x for x in root.iterate_children()]:
            node.detach()
    root.add_preceding_siblings(new_comment_node("before"))
    root.add_following_siblings(new_comment_node("after"))

    assert str(document) == "<!--before--><root/><!--after-->"


def test_processing_instruction_node():
    root = Document("<root/>").root

    root.append_children(new_processing_instruction_node("foo", "bar"))

    with altered_default_filters():
        pi = root.first_child

    assert pi.target == "foo"
    assert pi.content == "bar"
    assert str(pi) == "<?foo bar?>"

    assert pi == new_processing_instruction_node("foo", "bar")
    assert pi != root
    assert pi != new_processing_instruction_node("ham", "bar")

    assert str(root) == "<root><?foo bar?></root>"

    assert pi.new_tag_node("ham").local_name == "ham"
