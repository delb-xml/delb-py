import pytest

from delb import Document, Namespaces
from delb.names import XML_NAMESPACE


@pytest.mark.parametrize(
    "data",
    ({"xml": "foo"}, {"foo": XML_NAMESPACE}),
)
def test_invalid_namespace_declarations(data):
    with pytest.raises(ValueError, match="(not be overridden|not override)"):
        Namespaces(data)


def test_namespaces():
    node = Document("<node xmlns:foo='bar'/>").root
    with pytest.deprecated_call():
        namespaces = node.namespaces

    assert namespaces == Namespaces({"foo": "bar"})
    assert namespaces["xml"] == XML_NAMESPACE

    with pytest.raises(KeyError):
        namespaces["none"]


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

    with pytest.raises(KeyError):
        namespaces.lookup_prefix("http://void.delb/")
