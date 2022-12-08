import lxml

from delb import Document

# from tests.utils import assert_documents_are_semantical_equal, count_pis


def test_pretty_print():
    d = Document(
        '<root><a>hi</a><b x="foo"><c/></b></root>',
        collapse_whitespace=True
    )
    pp = lxml.etree.tostring(d.root._etree_obj, pretty_print=True)
    assert '''<root>
  <a>hi</a>
  <b x="foo">
    <c/>
  </b>
</root>
''' == pp.decode()
