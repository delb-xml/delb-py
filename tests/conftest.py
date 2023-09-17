from pathlib import Path

import pytest

from tests import plugins  # noqa: F401

from delb import DefaultStringOptions, Document


FILES_PATH = Path(__file__).parent / "files"
RESULTS_FILE = FILES_PATH / ".result.xml"
TEI_FILES = tuple(FILES_PATH.glob("tei_*.xml"))
XML_FILES = tuple(FILES_PATH.glob("[!.]*.xml"))


_referenced_objects_for_wrapper_cache_tests = {}


@pytest.fixture
def files_path():
    return FILES_PATH


@pytest.fixture
def long_term_references():
    return _referenced_objects_for_wrapper_cache_tests


@pytest.fixture
def result_file():
    return RESULTS_FILE


@pytest.fixture
def queries_sample():
    return Document(
        """\
            <root>
                <node n="1"/>
                <node n="2"/>
                <node/>
                <node n="3"/>
            </root>
        """
    )


@pytest.fixture(autouse=True)
def _reset_serializer():
    DefaultStringOptions.reset_defaults()


@pytest.fixture
def sample_document():
    return Document(
        '<doc xmlns="https://name.space">'
        "<header/>"
        "<text>"
        '<milestone unit="page"/>'
        "<p>Lorem ipsum"
        '<milestone unit="line"/>'
        "dolor sit amet"
        "</p>"
        "</text>"
        "</doc>"
    )
