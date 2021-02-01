from pathlib import Path

from lxml import etree

from delb import Document


TEST_FILE = (
    Path(__file__).resolve().parent / "files" / "marx_manifestws_1848.TEI-P5.xml"
)


def test_buffer_loader():
    with TEST_FILE.open("r") as f:
        document = Document(f)
    assert document.source_url is None


def test_etree_loader():
    tree = etree.parse(str(TEST_FILE))
    root = tree.getroot()

    document = Document(root)
    assert document.root._etree_obj is not root
    assert document.source_url is None


def test_ftp_http_loader():
    url = "http://textgridlab.org/1.0/tgcrud-public/rest/textgrid:mhpz.0/data"
    document = Document(url)
    assert document.source_url == url


def test_https_loader():
    url = (
        "https://raw.githubusercontent.com/funkyfuture/delb/master/tests/files/"
        "marx_manifestws_1848.TEI-P5.xml"
    )
    document = Document(url)
    assert document.source_url == url


def test_pathloader():
    document = Document(TEST_FILE)
    assert document.source_url == f"file://{TEST_FILE}"


def test_text_loader():
    with TEST_FILE.open("rt") as f:
        document = Document(f.read())
    assert document.source_url is None
