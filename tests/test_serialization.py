from textwrap import dedent

from pytest import mark

from delb import (
    new_comment_node,
    new_processing_instruction_node,
    new_tag_node,
    tag,
    Document,
    ParserOptions,
    StringSerializer,
    TextNode,
)
from _delb.nodes import DETACHED

from tests.utils import assert_documents_are_semantical_equal, count_pis


@mark.parametrize(
    ("indentation", "_in", "out"),
    (
        (
            "  ",
            '<root><a>hi</a><b x="foo"><c/></b></root>',
            """\
             <?xml version='1.0' encoding='UTF-8'?>
             <root>
               <a>hi</a>
               <b x="foo">
                 <c/>
               </b>
             </root>
            """,
        ),
    ),
)
def test_indentation(indentation, _in, out, result_file):
    Document(_in).save(result_file, indentation=indentation)
    assert result_file.read_text() == dedent(out)


def test_prefixes_collection():
    # a tree with a default namespace and an empty namespace as descendant
    root = Document("<root xmlns='http://fo.org/'/>").root
    root.append_children(new_tag_node(local_name="node", namespace=None))
    assert str(root) == '<root xmlns="http://fo.org/" xmlns:ns0=""><ns0:node/></root>'


def test_significant_whitespace_is_saved(result_file):
    document = Document("<text/>")
    root = document.root
    hi = tag("hi")

    root.append_children(hi)
    root[0].append_children("Hello")
    root.append_children(" ")
    root.append_children(hi)
    root[2].append_children("world!")

    document.save(result_file)
    assert (
        result_file.read_text() == "<?xml version='1.0' encoding='UTF-8'?>"
        "<text><hi>Hello</hi> <hi>world!</hi></text>"
    )

    document.save(result_file, pretty=True)

    assert (
        Document(result_file, collapse_whitespace=True)
        .xpath("hi")
        .first.fetch_following_sibling()
        == " "
    )

    assert result_file.read_text().splitlines() == [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<text>",
        "  <hi>Hello</hi>",
        "   ",  # FIXME?
        "  <hi>world!</hi>",
        "</text>",
    ]


@mark.parametrize(
    ("declarations", "node_constructor", "args", "out"),
    (
        ({}, new_comment_node, ("foo",), "<!--foo-->"),
        ({}, new_processing_instruction_node, ("foo", 'bar="0"'), '<?foo bar="0"?>'),
        ({}, new_tag_node, ("foo",), "<foo/>"),
        ({}, new_tag_node, ("foo", {"bar": "0"}), '<foo bar="0"/>'),
        ({}, TextNode, ("foo", DETACHED), "foo"),
        (
            {None: "ftp://foo.bar"},
            new_tag_node,
            ("n", {}, "ftp://foo.bar"),
            '<n xmlns="ftp://foo.bar"/>',
        ),
        (
            {"p": "ftp://foo.bar"},
            new_tag_node,
            ("n", {}, "ftp://foo.bar"),
            '<p:n xmlns:p="ftp://foo.bar"/>',
        ),
        ({}, new_tag_node, ("n", {"x": "'"}), """<n x="'"/>"""),
        ({}, new_tag_node, ("n", {"x": "&"}), """<n x="&amp;"/>"""),
        ({}, new_tag_node, ("n", {"x": ">"}), """<n x="&gt;"/>"""),
        ({}, new_tag_node, ("n", {"x": "<"}), """<n x="&lt;"/>"""),
        ({}, new_tag_node, ("n", {"x": '"'}), """<n x="&quot;"/>"""),
        ({}, new_tag_node, ("n", {"x": '"&"'}), r"""<n x="&quot;&amp;&quot;"/>"""),
    ),
)
# TODO create node objects in parametrization when the etree element wrapper cache has
#      been shed off
def test_single_nodes(declarations, node_constructor, args, out):
    StringSerializer.namespaces = declarations
    assert str(node_constructor(*args)) == out


def test_that_root_siblings_are_preserved(files_path, result_file):
    Document(files_path / "root_siblings.xml").clone().save(result_file)
    assert count_pis(result_file) == {
        '<?another-target ["it", "could", "be", "anything"]?>': 1,
        '<?target some="processing" instructions="here"?>': 2,
    }

    assert result_file.read_text() == (
        "<?xml version='1.0' encoding='UTF-8'?>"
        '<?target some="processing" instructions="here"?>'
        '<?another-target ["it", "could", "be", "anything"]?>'
        "<!-- a comment -->"
        '<?target some="processing" instructions="here"?>'
        "<root/>"
        "<!-- end -->"
    )


def test_transparency(files_path, result_file):
    for file in (x for x in files_path.glob("[!tei_]*.xml")):
        doc = Document(file, parser_options=ParserOptions(collapse_whitespace=False))
        doc.save(result_file)

        assert_documents_are_semantical_equal(file, result_file)
        assert count_pis(file) == count_pis(result_file)


def test_xml_declaration(files_path, result_file):
    Document(files_path / "tei_marx_manifestws_1848.TEI-P5.xml").save(result_file)
    assert result_file.read_text().startswith("<?xml version='1.0' encoding='UTF-8'?>")
