from pathlib import Path

import pytest
from lxml import etree
from pytest_httpx import IteratorStream

from delb import new_tag_node, Document

from tests.utils import chdir

TEST_FILE = (
    Path(__file__).resolve().parent / "files" / "marx_manifestws_1848.TEI-P5.xml"
)
TEST_CONTENTS = TEST_FILE.read_text()
TEST_FILE_URI = f"file://{TEST_FILE}"


def test_buffer_loader():
    with TEST_FILE.open("r") as f:
        document = Document(f)
    assert document.source_url == TEST_FILE_URI

    with chdir(TEST_FILE.parent), Path(TEST_FILE.name).open("r") as f:
        document = Document(f)
    assert document.source_url == TEST_FILE_URI


def test_etree_loader():
    tree = etree.parse(str(TEST_FILE))
    root = tree.getroot()

    with pytest.deprecated_call():
        document = Document(root)
    assert document.root._etree_obj is not root
    assert document.source_url is None


@pytest.mark.parametrize("s", ("", "s"))
def test_http_s_loader(httpx_mock, s):
    httpx_mock.add_response(
        stream=IteratorStream(
            (
                TEST_CONTENTS[i : i + 4096].encode()
                for i in range(0, len(TEST_CONTENTS), 4096)
            )
        )
    )
    url = f"http{s}://bdk.london/das_manifest.xml"
    document = Document(url)
    assert document.root.local_name == "TEI"
    assert document.source_url == url


def test_path_loader():
    document = Document(TEST_FILE)
    assert document.source_url == TEST_FILE_URI

    with chdir(TEST_FILE.parent):
        document = Document(Path(TEST_FILE.name))
    assert document.source_url == TEST_FILE_URI


def test_tag_node_loader():
    node = new_tag_node("root")
    assert node.document is None

    document = Document(node)
    assert node.document is document

    document_clone = Document(node)
    assert node is not document_clone.root

    assert str(document) == str(document_clone)


def test_text_loader():
    document = Document(TEST_CONTENTS)
    assert document.source_url is None
