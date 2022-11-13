import pytest
from lxml.etree import XMLParser

from delb import Document


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_lxml_parser():
    Document("<root/>", parser=XMLParser())
