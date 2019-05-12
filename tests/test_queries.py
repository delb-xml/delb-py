from delb import Document


def test_css_select_or(files_path):
    document = Document(files_path / "stevenson_treasure_island.xml")

    result = document.css_select("titleStmt title, titleStmt author")

    assert len(result) == 2
    assert set(x.local_name for x in result) == {"author", "title"}
