from pathlib import Path

from pytest import fixture

from delb import Document

from tests import plugins  # noqa: F401


FILES_PATH = Path(__file__).parent / "files"
RESULTS_FILE = FILES_PATH / ".result.xml"


@fixture()
def files_path():
    yield FILES_PATH


@fixture()
def result_file():
    yield RESULTS_FILE


@fixture()
def sample_document():
    yield Document(
        """\
    <doc xmlns="https://name.space">
        <header/>
        <text>
            <milestone unit="page"/>
            <p>Lorem ipsum
                <milestone unit="line"/>
                dolor sit amet
            </p>
        </text>
    </doc>
    """
    )
