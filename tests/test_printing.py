import lxml
import re

from delb import Document


def _clws(line: str) -> int:
    """
    counts leading whitespace.

    >>> _clws('   hi!')
    3

    >>> _clws('𓆉')
    0

    >>> _clws('  ')
    -1

    """
    match = re.match(r"^\s*\S", line)
    if match is None:
        return -1
    return match.span()[-1] - 1


def unindent(multilinestr: str) -> str:
    """
    unindents multiline string by outermost indentation level.

    >>> unindent('''
    ... <a>
    ...  <b/>
    ... </a>''')
    '<a>\\n <b/>\\n</a>'

    >>> unindent(
    ...   '''
    ...     <c>
    ...       <d/>
    ...     </c>
    ...   '''
    ... )
    '<c>\\n  <d/>\\n</c>\\n'

    """
    lines = list(filter(lambda line: len(line) > 0, multilinestr.split("\n")))
    indent = max(map(_clws, (lines[i] for i in [0, -1])))
    return "\n".join((line[indent:] for line in lines))


def test_pretty_print():
    d = Document('<root><a>hi</a><b x="foo"><c/></b></root>', collapse_whitespace=True)
    pp = lxml.etree.tostring(d.root._etree_obj, pretty_print=True)
    assert (
        unindent(
            """
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
