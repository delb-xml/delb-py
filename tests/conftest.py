from pathlib import Path

from pytest import fixture


FILES_PATH = Path(__file__).parent / "files"


@fixture()
def files_path():
    yield FILES_PATH
