import pytest

from delb.names import XML_NAMESPACE, Namespaces, deconstruct_clark_notation


@pytest.mark.parametrize(
    ("in_", "out"),
    (
        ("a", (None, "a")),
        ("{http://clark}a", ("http://clark", "a")),
    ),
)
def test_deconstruct_clark_notation(in_, out):
    assert deconstruct_clark_notation(in_) == out


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


def test_invalid_namespace_type():
    with pytest.raises(TypeError):
        Namespaces(("foo", "http://foo"))


def test_namespaces():
    # low expectations here, this aims to cover all lines
    # more specific test shall have their own test function

    namespaces = Namespaces({"a": "http://a.org/"})

    assert len(namespaces) == 18  # includes common and global declarations

    assert str(namespaces)

    # to hit the cache eviction in Namespaces.__init_data
    for i in range(17):
        Namespaces({chr(97 + i): "http://foo.org"})


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
