from pathlib import Path

from lxml import etree

from delb import Document


TEST_FILE = (
    Path(__file__).resolve().parent / "files" / "marx_manifestws_1848.TEI-P5.xml"
)


def test_buffer_loader():
    with TEST_FILE.open("r") as f:
        Document(f)


def test_etree_loader():
    tree = etree.parse(str(TEST_FILE))
    root = tree.getroot()

    document = Document(root)
    assert document.root._etree_obj is not root


def test_ftp_http_loader():
    Document("http://deutschestextarchiv.de/book/download_xml/marx_manifestws_1848")


def test_https_loader():
    Document(
        "https://raw.githubusercontent.com/funkyfuture/delb/master/tests/"
        "files/marx_manifestws_1848.TEI-P5.xml"
    )


def test_pathloader():
    Document(TEST_FILE)


def test_text_loader():
    with TEST_FILE.open("rt") as f:
        text = f.read()
    Document(text)
