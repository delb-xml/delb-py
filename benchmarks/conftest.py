import gc
from pathlib import Path

from pytest import fixture


DOCUMENTS = tuple(x for x in (Path(__file__).parent.resolve() / "docs").iterdir())


@fixture(autouse=True, scope="function")
def collect_garbage():
    gc.collect()
    gc.collect()
    yield


@fixture()
def docs():
    yield DOCUMENTS
