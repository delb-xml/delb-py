import pytest

from delb import Namespaces
from delb.names import XML_NAMESPACE


@pytest.mark.parametrize(
    "data",
    (
        {"xml": "foo"},
        {"foo": XML_NAMESPACE},
        {"one": "mailto:duper@delb", "two": "mailto:duper@delb"},
        {"": "http://a.org", None: "http://b.net"},
    ),
)
def test_invalid_namespace_declarations(data):
    with pytest.raises(ValueError):  # noqa: PT011
        Namespaces(data)


def test_prefix_lookup():
    namespaces = Namespaces({"foo": "ftp://super.delb/", "sko": "https://extra.delb/"})
    # global
    assert namespaces.lookup_prefix(XML_NAMESPACE) == "xml"
    # this namespace's scope
    assert namespaces.lookup_prefix("ftp://super.delb/") == "foo"

    assert namespaces.lookup_prefix("http://void.delb/") is None


@pytest.mark.parametrize("prefix_for_default", ("", None))
def test_prefix_lookup_default_namespace(prefix_for_default):
    namespace = "https://something.delb/"
    namespaces = Namespaces({prefix_for_default: namespace})
    assert namespaces.lookup_prefix("https://something.delb/") == ""
