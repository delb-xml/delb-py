from pathlib import Path
from subprocess import run


XPATH_MODULE_PATH = Path(__file__).parent / ".." / "_delb" / "xpath"
if (XPATH_MODULE_PATH / "xpath.gram").stat().st_mtime > (
    XPATH_MODULE_PATH / "parser.py"
).stat().st_mtime:
    run(
        "just generate-xpath-parser",
        shell=True,
        check=True,
    )


from pytest import fixture

from tests import plugins  # noqa: F401

from delb import Document


FILES_PATH = Path(__file__).parent / "files"
RESULTS_FILE = FILES_PATH / ".result.xml"


_referenced_objects_for_wrapper_cache_tests = {}


@fixture()
def files_path():
    yield FILES_PATH


@fixture()
def long_term_references():
    yield _referenced_objects_for_wrapper_cache_tests


@fixture()
def result_file():
    yield RESULTS_FILE


@fixture()
def queries_sample():
    yield Document(
        """\
            <root>
                <node n="1"/>
                <node n="2"/>
                <node/>
                <node n="3"/>
            </root>
        """
    )


@fixture()
def sample_document():
    yield Document(
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


@fixture()
def traverser_sample():
    yield Document(
        """\
            <root>
                <a>
                    <aa/>
                    <ab>
                        <aba/>
                    </ab>
                    <ac/>
                </a>
                <b/>
                <c>
                    <ca>
                        <caa/>
                        <cab/>
                    </ca>
                    <cb/>
                </c>
            </root>
        """
    )
