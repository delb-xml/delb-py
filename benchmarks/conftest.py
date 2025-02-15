import gc
from pathlib import Path

import pytest


FAILED_RESULT = "failed_result_of_"
FILES_PATH = Path(__file__).parent.parent / "tests/files"
TEI_FILES = tuple(FILES_PATH.glob("tei_*.xml"))
XML_FILES = tuple(
    p for p in FILES_PATH.glob("*.xml") if not p.name.startswith(FAILED_RESULT)
)


@pytest.fixture(autouse=True)
def _collect_garbage():
    gc.collect()
    gc.collect()
