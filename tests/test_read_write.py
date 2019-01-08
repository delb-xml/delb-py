from pathlib import Path

import pytest

from lxml_domesque import Document

from .utils import assert_documents_are_semantical_equal


FILES = Path(__file__).resolve().parent / "files"


@pytest.mark.datafiles(FILES / "marx_manifestws_1848.TEI-P5.xml")
def test_transparency(datafiles):
    result_file = FILES / ".result.xml"
    for file in datafiles.listdir():
        doc = Document(Path(str(file)))
        doc.save(result_file)
        assert_documents_are_semantical_equal(file, result_file)
