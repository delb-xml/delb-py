from pathlib import Path

from pytest import fixture

from delb import Document
from delb.plugins import plugin_manager

from tests import plugins as _test_plugins


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


@fixture()
def test_plugins():
    plugin_manager.register(_test_plugins)
    plugin_manager.check_pending()

    plugin_manager.trace.root.setwriter(print)
    undo = plugin_manager.enable_tracing()

    yield

    undo()
    plugin_manager.unregister(_test_plugins)
