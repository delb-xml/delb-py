import types

from pytest import mark

from delb import Document, TagNode


# this is also used as example in docs/extending.rst
class TEIDocument(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **{**kwargs, "collapse_whitespace": True})
        self.text_characters = len(self.root.full_text)

    @staticmethod
    def __class_test__(root: TagNode, config: types.SimpleNamespace) -> bool:
        return root.universal_name == "{http://www.tei-c.org/ns/1.0}TEI"

    @property
    def title(self) -> str:
        return self.css_select('titleStmt title[type="main"]').first.full_text


class DTABfDocument(TEIDocument):
    @staticmethod
    def __class_test__(root, config) -> bool:
        if TEIDocument.__class_test__(root, config):
            for node in root.css_select("publicationStmt publisher[xml|id]"):
                if node.id == "DTACorpusPublisher":
                    return True
        return False


def test_klass(files_path):
    document = Document(
        files_path / "tei_marx_manifestws_1848.TEI-P5.xml", klass=Document
    )
    assert not isinstance(document, DTABfDocument)


def test_no_subclass():
    assert isinstance(Document("<root/>"), Document)


@mark.parametrize(
    "filename",
    ("tei_marx_manifestws_1848.TEI-P5.xml", "tei_stevenson_treasure_island.xml"),
)
def test_tei_subclass(files_path, filename):
    document = Document(files_path / filename)

    if isinstance(document, DTABfDocument):
        assert document.text_characters == 74737
        assert document.title == "Manifest der Kommunistischen Partei"

    elif isinstance(document, TEIDocument):
        assert document.text_characters == 357940
        assert (
            document.title
            == "Treasure Island [Electronic resource] / Robert Louis Stevenson"
        )

    else:
        raise AssertionError
