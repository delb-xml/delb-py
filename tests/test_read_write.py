from pathlib import Path

from lxml_domesque import Document

from tests.utils import assert_documents_are_semantical_equal, count_pis


FILES = Path(__file__).resolve().parent / "files"
RESULTS_FILE = FILES / ".result.xml"


def _(datafiles_path):
    return Path(str(datafiles_path))


def test_initial_processing_instructions_are_retained(files_path):
    Document(files_path / "initial_processing_instructions.xml").clone().save(
        RESULTS_FILE
    )
    assert count_pis(RESULTS_FILE) == {
        '<?another-target ["it", "could", "be", "anything"]?>': 1,
        '<?target some="processing" instructions="here"?>': 2,
    }


def test_transparency(files_path):
    for file in (x for x in files_path.iterdir() if x.suffix == ".xml"):
        doc = Document(_(file))
        doc.save(RESULTS_FILE)

        assert_documents_are_semantical_equal(file, RESULTS_FILE)
        assert count_pis(_(file)) == count_pis(RESULTS_FILE)


def test_xml_declaration(files_path):
    Document(files_path / "marx_manifestws_1848.TEI-P5.xml").save(RESULTS_FILE)
    with RESULTS_FILE.open("rt") as f:
        first_line = f.readline()
    assert first_line.startswith("<?xml version='1.0' encoding='UTF-8'?>")
