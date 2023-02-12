from pytest import mark, raises

from delb import Document, Namespaces
from delb.names import XML_NAMESPACE


def test_cleanup_namespaces():
    document = Document('<root xmlns="D" xmlns:y="Y"><x:a xmlns:x="X"/></root>')

    document.cleanup_namespaces(retain_prefixes=("y",))
    assert str(document) == '<root xmlns="D" xmlns:y="Y"><x:a xmlns:x="X"/></root>'

    document.cleanup_namespaces()
    assert str(document) == '<root xmlns="D"><x:a xmlns:x="X"/></root>'

    document.cleanup_namespaces(namespaces={"x": "X"})
    assert str(document) == '<root xmlns="D" xmlns:x="X"><x:a/></root>'


@mark.parametrize(
    "data",
    ({"xml": "foo"}, {"foo": XML_NAMESPACE}),
)
def test_invalid_namespace_declarations(data):
    with raises(ValueError):
        Namespaces(data)


def test_namespaces():
    node = Document("<node xmlns:foo='bar'/>").root
    namespaces = node.namespaces

    assert namespaces == Namespaces({"foo": "bar"})
    assert namespaces["xml"] == XML_NAMESPACE

    with raises(KeyError):
        namespaces["none"]


def test_namespaces_hashing():
    namespaces1 = Namespaces({"ns0": "0", "ns1": "1"})
    namespaces2 = Namespaces({"ns0": "00"}, fallback=namespaces1)
    assert hash(namespaces1) != hash(namespaces2)
    assert hash(namespaces2) != hash(Namespaces({"ns0": "00"}))


def test_prefix_lookup():
    namespaces = Namespaces({"foo": "ftp://super.delb/", "sko": "https://extra.delb/"})

    # global
    assert namespaces.lookup_prefix(XML_NAMESPACE) == "xml"
    # this namespace's scope
    assert namespaces.lookup_prefix("ftp://super.delb/") == "foo"

    namespaces = Namespaces({"bar": "ftp://super.delb/"}, fallback=namespaces)
    # this namespace's scope
    assert namespaces.lookup_prefix("ftp://super.delb/") == "bar"
    # a fallback's scope
    assert namespaces.lookup_prefix("https://extra.delb/") == "sko"

    namespaces = Namespaces(
        {"alt": "mailto:duper@delb", None: "mailto:duper@delb"}, fallback=namespaces
    )
    # default namespaces are preferred
    assert namespaces.lookup_prefix("mailto:duper@delb") is None

    namespaces = Namespaces({None: "https://something.delb/"}, fallback=namespaces)
    # fallbacks don't override the overrides of the
    # default namespace declared in a descendant
    assert namespaces.lookup_prefix("mailto:duper@delb") == "alt"

    with raises(KeyError):
        namespaces.lookup_prefix("http://void.delb/")
