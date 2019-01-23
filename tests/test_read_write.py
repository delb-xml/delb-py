from pathlib import Path

import pytest

from lxml_domesque import Document

from tests.utils import assert_documents_are_semantical_equal, count_pis


FILES = Path(__file__).resolve().parent / "files"
RESULTS_FILE = FILES / ".result.xml"


def _(datafiles_path):
    return Path(str(datafiles_path))


@pytest.mark.datafiles(FILES / "initial_processing_instructions.xml")
def test_initial_processing_instructions_are_retained(datafiles):
    Document(_(datafiles / "initial_processing_instructions.xml")).clone().save(
        RESULTS_FILE
    )
    assert count_pis(RESULTS_FILE) == {
        '<?another-target ["it", "could", "be", "anything"]?>': 1,
        '<?target some="processing" instructions="here"?>': 2,
    }


@pytest.mark.datafiles(FILES / "marx_manifestws_1848.TEI-P5.xml")
def test_transparency(datafiles):
    for file in datafiles.listdir():
        doc = Document(_(file))
        doc.save(RESULTS_FILE)

        assert_documents_are_semantical_equal(file, RESULTS_FILE)
        assert count_pis(_(file)) == count_pis(RESULTS_FILE)
