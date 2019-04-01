from pathlib import Path

from pytest import fixture


FILES_PATH = Path(__file__).parent / "files"
RESULTS_FILE = FILES_PATH / ".result.xml"


@fixture()
def files_path():
    yield FILES_PATH


@fixture()
def result_file():
    yield RESULTS_FILE
