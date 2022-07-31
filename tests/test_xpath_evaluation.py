from delb import Document


def test_multiple_identical_location_paths():
    document = Document("<root><foo/></root>")
    assert document.xpath("/foo | /foo").size == 1
