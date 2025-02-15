import pytest

from benchmarks.conftest import XML_FILES


def serialize(document):
    str(document)


@pytest.mark.parametrize("file", XML_FILES)
def test_serialization(benchmark, file):
    benchmark(serialize, file)
