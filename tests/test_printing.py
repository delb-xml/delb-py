import lxml
from textwrap import dedent

from delb import Document


def test_pretty_print():
    d = Document('<root><a>hi</a><b x="foo"><c/></b></root>', collapse_whitespace=True)
    pp = lxml.etree.tostring(d.root._etree_obj, pretty_print=True)
    assert (
        dedent(
            """\
            <root>
              <a>hi</a>
              <b x="foo">
                <c/>
              </b>
            </root>
            """
        )
        == pp.decode()
    )
