from delb import Document


def test_multiple_identical_location_paths():
    document = Document("<root><foo/></root>")
    assert document.xpath("/foo | /foo").size == 1


def test_multiple_predicates():
    document = Document(
        "<root><n x='1'/><n a='' x='2'/><n a='' x='3'/><n x='4'/><n a='' x='5'/></root>"
    )
    result = document.xpath("/n[@a][2]")
    assert result.size == 1
    assert result.first["x"] == "3"
