from pathlib import Path

import pytest

# keep this before imports from delb!
from tests import plugins  # noqa: F401

from _delb.nodes import default_filters
from delb import DefaultStringOptions, Document


FAILED_RESULT = "failed_result_of_"
FILES_PATH = Path(__file__).parent / "files"
TEI_FILES = tuple(FILES_PATH.glob("tei_*.xml"))
XML_FILES = tuple(
    p for p in FILES_PATH.glob("*.xml") if not p.name.startswith(FAILED_RESULT)
)


default_filters_default = tuple(default_filters)
_referenced_objects_for_wrapper_cache_tests = {}
phase_report_key = pytest.StashKey()


# per https://docs.pytest.org/en/latest/example/simple.html
#         #making-test-result-information-available-in-fixtures
# for the result_file fixture
@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    rep = yield
    item.stash.setdefault(phase_report_key, {})[rep.when] = rep
    return rep


@pytest.fixture(autouse=True)
def _default_filters():
    default_filters.clear()
    default_filters.extend(default_filters_default)


@pytest.fixture
def files_path():
    return FILES_PATH


@pytest.fixture
def long_term_references():
    return _referenced_objects_for_wrapper_cache_tests


@pytest.fixture
def result_file(request, tmp_path):
    assert request.scope == "function"
    path = tmp_path / "result.xml"
    yield path
    assert path.exists()
    report = request.node.stash[phase_report_key]
    if ("call" not in report) or report["call"].failed:
        test_name = request.node.name.replace("/", "_")[:128]
        target = FILES_PATH / f"{FAILED_RESULT}{test_name}.xml"
        target.write_bytes(path.read_bytes())


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
