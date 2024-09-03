from delb import Document, new_tag_node

# test_subclasses implicitly also tests collapsing and trimming


def test_contained_milestone_tags_each_followed_by_whitespace():
    document = Document("<root><lb/>Hello <lb/> <lb/> <lb/> world!</root>")
    document.reduce_whitespace()
    assert document.root.full_text == "Hello    world!"


def test_empty_text_node():
    node = new_tag_node("node", children=[""])
    assert len(node) == 1
    node._reduce_whitespace()
    assert len(node) == 0


def test_milestone_tag_with_altering_whitespace_neighbour():
    document = Document("<p><hi>then</hi> give<lb/> the</p>")
    document.reduce_whitespace()
    assert " give " in document.root.full_text

    document = Document("<p><hi>then</hi> give <lb/>the</p>")
    document.reduce_whitespace()
    assert " give " in document.root.full_text


def test_samples_from_Manifest_der_kommunistischen_Partei(files_path):  # noqa: N802
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")
    document.reduce_whitespace()
    imprints = document.xpath("//docImprint")

    assert imprints[0].full_text == "Veröffentlicht im Februar 1848."
    assert "46, Liverpool Street" in imprints[1].full_text


def test_space_preserve():
    document = Document(
        """
    <root>
        <title>
            I Roy -
            <hi>Touting I Self</hi>
        </title>
        <matrix xml:space="preserve">HB 243 A  Re</matrix>
        <matrix xml:space="preserve">HB 243 B\tRe</matrix>
    </root>
    """
    )

    document.reduce_whitespace()
    root = document.root

    assert root.first_child.full_text == "I Roy - Touting I Self"
    assert root.css_select("matrix")[0].full_text == "HB 243 A  Re"
    assert root.css_select("matrix")[1].full_text == "HB 243 B\tRe"
