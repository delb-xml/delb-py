from textwrap import dedent

import pytest

from delb import (
    new_comment_node,
    new_processing_instruction_node,
    new_tag_node,
    tag,
    DefaultStringOptions,
    Document,
    ParserOptions,
    PrettyFormatOptions,
    TextNode,
)
from _delb.nodes import DETACHED

from tests.utils import assert_equal_trees


@pytest.mark.parametrize(
    ("indentation", "out"),
    (
        (
            "",
            "<chimeney\n"
            '      califragi="1"\n'
            ' expialidocious="3"\n'
            '         listic="2"\n'
            '          super="0"/>',
        ),
        (
            "  ",
            "<chimeney\n"
            '        califragi="1"\n'
            '   expialidocious="3"\n'
            '           listic="2"\n'
            '            super="0"\n'
            "/>",
        ),
    ),
)
def test_align_attributes(indentation, out):
    DefaultStringOptions.pretty_format_options = PrettyFormatOptions(
        align_attributes=True, indentation=indentation
    )
    node = new_tag_node(
        "chimeney",
        {"super": "0", "califragi": "1", "listic": "2", "expialidocious": "3"},
    )

    assert str(node) == out


def test_document_xml_declaration(files_path):
    assert str(Document(files_path / "tei_marx_manifestws_1848.TEI-P5.xml")).startswith(
        '<?xml version="1.0" encoding="UTF-8"?>'
    )


def test_empty_below_default_namespace():
    # as there's a default namespace and a namespace can't be empty, a prefix must be
    # supplied for all namespaces
    root = Document("<root xmlns='http://fo.org/'/>").root
    root.append_children(new_tag_node(local_name="node", namespace=None))
    assert str(root) == '<ns0:root xmlns:ns0="http://fo.org/"><node/></ns0:root>'


@pytest.mark.parametrize(
    ("indentation", "_in", "out"),
    (
        (
            "  ",
            '<root><a>hi</a><b x="foo"><c/></b></root>',
            """\
             <?xml version="1.0" encoding="UTF-8"?>
             <root>
               <a>hi</a>
               <b x="foo">
                 <c/>
               </b>
             </root>""",
        ),
    ),
)
def test_indentation(indentation, _in, out):
    DefaultStringOptions.pretty_format_options = PrettyFormatOptions(
        indentation=indentation, text_width=0
    )
    assert str(Document(_in)) == dedent(out)


@pytest.mark.parametrize(
    ("_in", "out"),
    (
        (
            '<r xmlns="d1"><b xmlns="d2"/></r>',
            '<r xmlns="d1" xmlns:ns0="d2"><ns0:b/></r>',
        ),
        ('<r><b xmlns="d"/></r>', '<r xmlns:ns0="d"><ns0:b/></r>'),
    ),
)
def test_prefix_collection_and_generation(_in, out):
    assert str(Document(_in).root) == out


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
    assert result_file.read_text() == (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<text><hi>Hello</hi> <hi>world!</hi></text>"
    )

    document.save(result_file, PrettyFormatOptions(indentation="  "))

    assert (
        Document(result_file, parser_options=ParserOptions(reduce_whitespace=True))
        .xpath("hi")
        .first.fetch_following_sibling()
        == " "
    )

    assert result_file.read_text().splitlines() == [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<text>",
        "  <hi>Hello</hi>",
        "   ",  # FIXME?
        "  <hi>world!</hi>",
        "</text>",
    ]


@pytest.mark.parametrize(
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
    DefaultStringOptions.namespaces = declarations
    node = node_constructor(*args)
    assert (
        node.serialize(namespaces=DefaultStringOptions.namespaces) == str(node) == out
    )


@pytest.mark.parametrize(
    ("indentation", "text_width", "out"),
    (
        (
            "",
            11,  # longest word has 12 characters
            '<p xmlns="http://www.tei-c.org/ns/1.0">\n'
            "Die\n"
            "Entdeckung\n"
            "Amerika’s,\n"
            "die\n"
            "Umschiffung\n"
            "Afrika’s,\n"
            "schufen der\n"
            "aufkommenden\n"
            "Bourgeoisie\n"
            "ein neues\n"
            "Terrain.\n"
            "Der\n"
            "ostindische\n"
            "und\n"
            "chinesische\n"
            "Markt, die\n"
            "Kolonisirung\n"
            "von\n"
            "Amerika,\n"
            "der\n"
            "Austausch\n"
            "mit den\n"
            "Kolonien,\n"
            "die\n"
            "Vermehrung\n"
            "der\n"
            "Tauschmittel\n"
            "und der\n"
            "Waaren\n"
            "überhaupt\n"
            "gaben dem\n"
            "Handel, der\n"
            "Schifffahrt,\n"
            "der\n"
            "Industrie\n"
            "einen\n"
            "niegekannten\n"
            "Aufschwung,\n"
            "und damit\n"
            "dem\n"
            "revolutionären\n"
            "Element in\n"
            "der\n"
            "zerfallenden\n"
            "feudalen\n"
            "Gesellschaft\n"
            "eine rasche\n"
            "Entwicklung.\n"
            "</p>",
        ),
        (
            "",
            68,
            '<p xmlns="http://www.tei-c.org/ns/1.0">\n'
            "Die Entdeckung Amerika’s, die Umschiffung Afrika’s, schufen der\n"
            "aufkommenden Bourgeoisie ein neues Terrain. Der ostindische und\n"
            "chinesische Markt, die Kolonisirung von Amerika, der Austausch mit\n"
            "den Kolonien, die Vermehrung der Tauschmittel und der Waaren\n"
            "überhaupt gaben dem Handel, der Schifffahrt, der Industrie einen\n"
            "niegekannten Aufschwung, und damit dem revolutionären Element in der\n"
            "zerfallenden feudalen Gesellschaft eine rasche Entwicklung.\n"
            "</p>",
        ),
        (
            "\t",
            68,
            '<p xmlns="http://www.tei-c.org/ns/1.0">\n'
            "\tDie Entdeckung Amerika’s, die Umschiffung Afrika’s, schufen der\n"
            "\taufkommenden Bourgeoisie ein neues Terrain. Der ostindische und\n"
            "\tchinesische Markt, die Kolonisirung von Amerika, der Austausch mit\n"
            "\tden Kolonien, die Vermehrung der Tauschmittel und der Waaren\n"
            "\tüberhaupt gaben dem Handel, der Schifffahrt, der Industrie einen\n"
            "\tniegekannten Aufschwung, und damit dem revolutionären Element in der\n"
            "\tzerfallenden feudalen Gesellschaft eine rasche Entwicklung.\n"
            "</p>",
        ),
    ),
)
def test_text_width(files_path, indentation, text_width, out):
    document = Document(files_path / "tei_marx_manifestws_1848.TEI-P5.xml")
    paragraph = document.xpath("//p")[14]
    DefaultStringOptions.pretty_format_options = PrettyFormatOptions(
        indentation=indentation, text_width=text_width
    )
    assert (
        paragraph.serialize(
            pretty_format_options=PrettyFormatOptions(
                indentation=indentation, text_width=text_width
            )
        )
        == str(paragraph)
        == out
    )


def test_text_with_milestone_tag(files_path):
    document = Document(
        files_path / "tei_stevenson_treasure_island.xml",
        parser_options=ParserOptions(reduce_whitespace=True),
    )
    paragraph = document.css_select("fileDesc sourceDesc p").first
    assert "\t" not in paragraph.full_text

    DefaultStringOptions.indentation = "  "
    DefaultStringOptions.text_width = 68
    assert str(paragraph) == (
        # the first line's length matches the configured text_width
        '<p xmlns="http://www.tei-c.org/ns/1.0">This text is a TEI version of\n'
        "  a Project Gutenberg text originally located at\n"
        '  <ptr target="http://www.gutenberg.org/dirs/1/2/0//120/"/>. As per\n'
        "  their license agreement we have removed all references to the\n"
        "  project's trademark, however have included this pointer to the\n"
        "  original in case you want the plain text, or their XHTML version.\n"
        "</p>"
    )


def test_that_root_siblings_are_preserved(files_path, result_file):
    origin_path = files_path / "root_siblings.xml"
    Document(origin_path).save(
        result_file, pretty_format_options=PrettyFormatOptions(indentation="  ")
    )

    assert (
        origin_path.read_text()
        == result_file.read_text()
        == (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<?target some="processing" instructions="here"?>\n'
            '<?another-target ["it", "could", "be", "anything"]?>\n'
            "<!-- a comment -->\n"
            '<?target some="processing" instructions="here"?>\n'
            "<root/>\n"
            "<!-- end -->"
        )
    )


def test_unaltered_transparency(files_path, result_file):
    for file in files_path.glob("[!tei_]*.xml"):
        origin = Document(file, parser_options=ParserOptions(reduce_whitespace=False))
        origin.save(result_file)
        _copy = Document(result_file)
        assert_equal_trees(origin.root, _copy.root)
        assert origin.head_nodes == _copy.head_nodes
        assert origin.tail_nodes == origin.tail_nodes


@pytest.mark.parametrize(
    "pretty_format_options",
    (
        {"indentation": ""},
        {"indentation": "  "},
        {"indentation": "\t"},
        {"text_width": 0},
        {"text_width": 77},
        {"indentation": "  ", "text_width": 77},
    ),
)
def test_whitespace_cleaned_transparency(
    files_path, result_file, pretty_format_options
):
    parser_options = ParserOptions(reduce_whitespace=True)
    for file in files_path.glob("tei_*.xml"):
        origin = Document(file, parser_options=parser_options)
        origin.save(result_file, PrettyFormatOptions(**pretty_format_options))
        _copy = Document(result_file, parser_options=parser_options)
        assert_equal_trees(origin.root, _copy.root)
