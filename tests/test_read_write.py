from lxml_domesque import Document

from tests.utils import assert_documents_are_semantical_equal, count_pis


def test_initial_processing_instructions_are_retained(files_path, result_file):
    Document(files_path / "initial_processing_instructions.xml").clone().save(
        result_file
    )
    assert count_pis(result_file) == {
        '<?another-target ["it", "could", "be", "anything"]?>': 1,
        '<?target some="processing" instructions="here"?>': 2,
    }


def test_significant_whitespace_is_saved(result_file):
    document = Document("<text/>")
    root = document.root
    hi = root.new_tag_node("hi")

    root.append_child(hi, clone=True)
    root[0].append_child("Hello")
    root.append_child(" ")
    root.append_child(hi, clone=True)
    root[2].append_child("world!")

    document.save(result_file)
    with result_file.open("rt") as result:
        assert result.readlines() == [
            "<?xml version='1.0' encoding='UTF-8'?>\n",
            "<text><hi>Hello</hi> <hi>world!</hi></text>",
        ]

    document.save(result_file, pretty=True)
    with result_file.open("rt") as result:
        assert result.readlines() == [
            "<?xml version='1.0' encoding='UTF-8'?>\n",
            "<text><hi>Hello</hi> <hi>world!</hi></text>\n",
        ]


def test_transparency(files_path, result_file):
    for file in (x for x in files_path.iterdir() if x.suffix == ".xml"):
        doc = Document(file)
        doc.save(result_file)

        assert_documents_are_semantical_equal(file, result_file)
        assert count_pis(file) == count_pis(result_file)


def test_xml_declaration(files_path, result_file):
    Document(files_path / "marx_manifestws_1848.TEI-P5.xml").save(result_file)
    with result_file.open("rt") as f:
        first_line = f.readline()
    assert first_line.startswith("<?xml version='1.0' encoding='UTF-8'?>")
