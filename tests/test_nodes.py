from lxml_domesque import Document


def test_add_previous():
    document = Document("<root><e1/></root>")
    document.root[0].add_previous(
        document.new_tag_node("e2"), document.new_tag_node("e3")
    )

    assert str(document) == "<root><e3/><e2/><e1/></root>"
