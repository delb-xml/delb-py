import gc
from pathlib import Path

import pytest


DOCUMENTS = tuple(x for x in (Path(__file__).parent.resolve() / "docs").iterdir())


@pytest.fixture(autouse=True)
def _collect_garbage():
    gc.collect()
    gc.collect()


@pytest.fixture
def docs():
    return DOCUMENTS
