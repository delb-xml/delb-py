from textwrap import dedent
from typing import Final

import pytest

from delb import (
    new_comment_node,
    new_processing_instruction_node,
    new_tag_node,
    parse_tree,
    tag,
    DefaultStringOptions,
    Document,
    FormatOptions,
    TextNode,
)
from _delb.parser import ParserOptions
from _delb.nodes import DETACHED, Serializer
from tests.conftest import TEI_FILES

from tests.utils import assert_equal_trees, skip_long_running_test


TEI_NAMESPACE: Final = "http://www.tei-c.org/ns/1.0"


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
    DefaultStringOptions.format_options = FormatOptions(
        align_attributes=True, indentation=indentation, width=0
    )
    node = new_tag_node(
        "chimeney",
        {"super": "0", "califragi": "1", "listic": "2", "expialidocious": "3"},
    )

    assert str(node) == out

    assert str(new_tag_node("foo", {"bar": "baz"})) == '<foo bar="baz"/>'


@pytest.mark.parametrize("with_newline", (True, False))
def test_document_xml_declaration(sample_document, with_newline):
    DefaultStringOptions.format_options = (
        FormatOptions(indentation="") if with_newline else None
    )
    assert str(sample_document).startswith(
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" if with_newline else ""
    )


def test_empty_below_default_namespace():
    # as there's a default namespace and a namespace can't be empty, a prefix must be
    # supplied for all other namespaces, including one declared as default
    root = parse_tree("<root xmlns='http://fo.org/'/>")
    root.append_children(new_tag_node(local_name="node", namespace=None))
    # just to be explicit here:
    DefaultStringOptions.namespace = {"": "http://fo.org/"}
    assert str(root) == '<ns0:root xmlns:ns0="http://fo.org/"><node/></ns0:root>'


@pytest.mark.parametrize(
    ("indentation", "in_", "out"),
    (
        (
            "  ",
            "<p>Hold <hi>the</hi> thieves!</p>",
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <p>
              Hold
              <hi>
                the
              </hi>
              thieves!
            </p>""",
        ),
        (
            "  ",
            '<root><a>hi</a> <b x="foo">x <c/> y</b></root>',
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <root>
              <a>
                hi
              </a>
              <b x="foo">
                x
                <c/>
                y
              </b>
            </root>""",
        ),
    ),
)
def test_indentation(indentation, in_, out):
    DefaultStringOptions.format_options = FormatOptions(
        align_attributes=False, indentation=indentation, width=0
    )
    document = Document(in_, parser_options=ParserOptions(reduce_whitespace=True))
    serialisat = str(document)
    assert_equal_trees(
        document.root,
        Document(serialisat, parser_options=ParserOptions(reduce_whitespace=True)).root,
    )
    assert serialisat == dedent(out)


@pytest.mark.parametrize(
    ("in_", "namespaces", "prefixes"),
    (
        (
            '<r xmlns="d1"><b xmlns="d2"/></r>',
            None,
            {"d1": "", "d2": "ns0:"},
        ),
        ('<r><b xmlns="d"/></r>', None, {"": "", "d": "ns0:"}),
        (
            '<r><ignored:d xmlns:ignored="d"/></r>',
            {"wanted": "d"},
            {"": "", "d": "wanted:"},
        ),
        ('<root xmlns:x="d" x:y=""/>', {"x": "d"}, {"": "", "d": "x:"}),
        (
            '<root xmlns="https://foo.org"><node/></root>',
            {"foo": "https://foo.org"},
            {"https://foo.org": "foo:"},
        ),
        (
            '<node xmlns:x="http://namespace" x:bar="X"/>',
            {None: "http://namespace"},
            {"": "", "http://namespace": "ns0:"},
        ),
        (
            '<node xmlns:x="http://namespace" x:bar="X"/>',
            {"": "http://namespace"},
            {"": "", "http://namespace": "ns0:"},
        ),
    ),
)
def test_prefix_collection_and_generation(in_, namespaces, prefixes):
    # all namespace declarations are included in the root node.
    # definitions from higher levels are preferred.
    serializer = Serializer(None, namespaces=namespaces)
    serializer._collect_prefixes(parse_tree(in_))
    assert serializer._prefixes == prefixes


@pytest.mark.parametrize(
    ("format_options", "out"),
    (
        (
            None,
            (
                """<?xml version="1.0" encoding="UTF-8"?>"""
                """<text><hi>Hello</hi> <hi>world!</hi></text>"""
            ),
        ),
        (
            FormatOptions(align_attributes=False, indentation="  ", width=4),
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <text>
              <hi>
                Hello
              </hi>
              <hi>
                world!
              </hi>
            </text>""",
        ),
    ),
)
def test_significant_whitespace_is_saved(result_file, format_options, out):
    document = Document("<text/>")
    document.root.append_children(tag("hi", ["Hello"]), " ", tag("hi", ["world!"]))

    document.reduce_whitespace()
    document.save(result_file, format_options=format_options)
    result = Document(
        result_file,
        parser_options=ParserOptions(reduce_whitespace=format_options is not None),
    )
    assert result.root.full_text == "Hello world!"
    assert_equal_trees(document.root, result.root)
    assert result_file.read_text() == dedent(out)


@pytest.mark.parametrize(
    "format_options",
    (
        None,
        FormatOptions(align_attributes=True, indentation="", width=0),
        FormatOptions(align_attributes=False, indentation="  ", width=0),
        FormatOptions(align_attributes=False, indentation="\t", width=89),
    ),
)
@pytest.mark.parametrize(
    ("namespaces", "node_constructor", "args", "out"),
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
            {"": "ftp://foo.bar"},
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
        (
            {"": "http://namespace"},
            new_tag_node,
            ("node", {("http://namespace", "bar"): "x"}),
            """<node xmlns:ns0="http://namespace" ns0:bar="x"/>""",
        ),
    ),
)
# TODO create node objects in parametrization when the etree element wrapper cache has
#      been shed off
def test_single_nodes(format_options, namespaces, node_constructor, args, out):
    DefaultStringOptions.namespaces = namespaces
    node = node_constructor(*args)
    assert (
        node.serialize(namespaces=DefaultStringOptions.namespaces) == str(node) == out
    )


@pytest.mark.parametrize(
    ("source", "prefix", "align_attributes", "width", "namespaces"),
    (
        # this contains many interesting phenomena for wrapped content
        (
            "tei_gsa_390707",
            "gsa_390707",
            False,
            77,
            {"http://www.faustedition.net/ns": ""},
        ),
        # these test the examples in the docs
        (
            "serialization-example-input",
            "serialization-example-indented",
            True,
            0,
            {"pi": "https://pirates.code/"},
        ),
        (
            "serialization-example-input",
            "serialization-example-wrapped",
            False,
            59,
            {"pi": "https://pirates.code/"},
        ),
    ),
)
def test_text_document_production(
    files_path, source, prefix, align_attributes, result_file, width, namespaces
):
    document = Document(files_path / f"{source}.xml")
    reference_path = files_path / f"{prefix}-reference.xml"

    document.save(
        result_file,
        format_options=FormatOptions(
            align_attributes=align_attributes, indentation="  ", width=width
        ),
        namespaces=namespaces,
    )
    assert result_file.read_text() == reference_path.read_text()


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
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")
    paragraph = document.xpath("//p")[14]
    format_options = FormatOptions(indentation=indentation, width=text_width)
    DefaultStringOptions.format_options = format_options
    assert paragraph.serialize(format_options=format_options) == str(paragraph) == out


@pytest.mark.parametrize(
    ("text_width", "expected"),
    (
        (
            0,
            """\
            <p xmlns="http://www.tei-c.org/ns/1.0">
              This text is a TEI version of a Project Gutenberg text originally located at
              <ptr target="http://www.gutenberg.org/dirs/1/2/0//120/"/>. As per their license agreement we have removed all references to the project's trademark, however have included this pointer to the original in case you want the plain text, or their XHTML version.
            </p>""",  # noqa: E501
        ),
        # the first line's length matches the configured text_width:
        (
            73,
            """\
            <p xmlns="http://www.tei-c.org/ns/1.0">
              This text is a TEI version of a Project Gutenberg text originally located
              at <ptr target="http://www.gutenberg.org/dirs/1/2/0//120/"/>. As per
              their license agreement we have removed all references to the project's
              trademark, however have included this pointer to the original in case you
              want the plain text, or their XHTML version.
            </p>""",
        ),
    ),
)
def test_text_with_milestone_tag(files_path, text_width, expected):
    document = Document(
        files_path / "tei_stevenson_treasure_island.xml",
        parser_options=ParserOptions(reduce_whitespace=True),
    )
    paragraph = document.css_select("fileDesc sourceDesc p").first
    assert "\t" not in paragraph.full_text

    DefaultStringOptions.format_options = FormatOptions(
        indentation="  ", width=text_width
    )
    assert str(paragraph) == dedent(expected)


@pytest.mark.parametrize(
    ("format_options", "in_", "out"),
    (
        (
            FormatOptions(align_attributes=False, indentation="", width=60),
            """<p><lb/>When you shall see especiall cause then give to <lb/>the lady two
            sponefuls &amp; a halfe of the vomyting syrope <lb/>mixed <glyph/></p>""",
            """\
            <p>
            <lb/>When you shall see especiall cause then give to
            <lb/>the lady two sponefuls &amp; a halfe of the vomyting
            syrope <lb/>mixed <glyph/>
            </p>""",
        ),
        (
            FormatOptions(align_attributes=False, indentation="", width=77),
            """<p><lb/>When you shall see especiall cause <choice><sic>they</sic><corr>then</corr></choice> give to <lb/>the lady two sponefuls &amp; a halfe of the vomyting syrope <lb/>mixed <glyph/></p>""",  # noqa: E501
            """\
            <p>
            <lb/>When you shall see especiall cause
            <choice><sic>they</sic><corr>then</corr></choice> give to <lb/>the lady two
            sponefuls &amp; a halfe of the vomyting syrope <lb/>mixed <glyph/>
            </p>""",
        ),
        (
            FormatOptions(align_attributes=False, indentation="  ", width=77),
            """\
            <p>“Come, come!” he said, from his corner. “Don't go on in that way, Mr. Gridley. You are only
             a little low. We are all of us a little low, sometimes. <hi>I</hi> am. Hold up, hold up!
             You'll lose your temper with the whole round of 'em, again and again; and I shall take you on
             a score of warrants yet, if I have luck.”</p>""",  # noqa: E501
            """\
            <p>
              “Come, come!” he said, from his corner. “Don't go on in that way, Mr.
              Gridley. You are only a little low. We are all of us a little low, sometimes.
              <hi>I</hi> am. Hold up, hold up! You'll lose your temper with the whole round
              of 'em, again and again; and I shall take you on a score of warrants yet, if
              I have luck.”
            </p>""",  # noqa: E501
        ),
        (
            FormatOptions(align_attributes=False, indentation="  ", width=77),
            """\
            <layout columns="1" ruledLines="22" writtenLines="21">
               <!--  xml:id="LO16" -->
               <locus from="128" to="137"> Fols 128–137 (Quire 17) </locus>: ruled space <dimensions type="ruled" unit="mm">
                  <height>187</height>
                  <width>90</width>
                  <!-- check: was 904 -->
               </dimensions> 22 long lines with double bounding lines, right and left. </layout>""",  # noqa: E501
            """\
            <layout columns="1" ruledLines="22" writtenLines="21">
              <!--  xml:id="LO16" -->
              <locus from="128" to="137">Fols 128–137 (Quire 17)</locus>: ruled space
              <dimensions type="ruled" unit="mm">
                <height>187</height> <width>90</width> <!-- check: was 904 -->
              </dimensions> 22 long lines with double bounding lines, right and left.
            </layout>""",  # noqa: E501
        ),
        (
            FormatOptions(align_attributes=False, indentation="  ", width=77),
            """\
            <layout columns="2" ruledLines="23" writtenLines="22">
               <!-- xml:id="LO15??" -->
               <locus from="1" to="8"> Fols 1–8 </locus>: ruled space <dimensions type="ruled" unit="mm">
                  <height>198</height>
                  <width>108</width>
                   </dimensions> 23 lines of two columns for table of contents, with double bounding lines right, left, and centre. </layout>""",  # noqa: E501
            """\
            <layout columns="2" ruledLines="23" writtenLines="22">
              <!-- xml:id="LO15??" --> <locus from="1" to="8">Fols 1–8</locus>: ruled space
              <dimensions type="ruled" unit="mm">
                <height>198</height> <width>108</width>
              </dimensions> 23 lines of two columns for table of contents, with double
              bounding lines right, left, and centre.
            </layout>""",  # noqa: E501
        ),
        (
            FormatOptions(align_attributes=False, indentation="  ", width=77),
            """\
            <text>
               <div>
                  <list>
                     <item xml:space="preserve">
               <ref/>
                 </item>
                  </list>
               </div>
            </text>""",
            """\
            <text>
              <div><list><item xml:space="preserve">
               <ref/>
                 </item></list></div>
            </text>""",
        ),
    ),
)
def test_text_wrapping(format_options, in_, out):
    DefaultStringOptions.format_options = format_options
    in_tree = parse_tree(dedent(in_), options=ParserOptions(reduce_whitespace=True))

    serialisat = str(in_tree)
    assert serialisat == dedent(out)
    result = parse_tree(serialisat, options=ParserOptions(reduce_whitespace=True))
    assert_equal_trees(in_tree, result)


@pytest.mark.parametrize(
    "in_",
    (
        """\
        <root>
           <a>B</a> C<d/>.<e/>
        </root>""",
        """\
        <root>
        <a>$</a><b/>
        </root>""",
    ),
)
@pytest.mark.parametrize(
    "format_options",
    (
        {"indentation": ""},
        {"indentation": "  "},
        {"indentation": "\t"},
        {"width": 0},
        {"width": 1},
        {"width": 77},
        {"indentation": "  ", "width": 77},
    ),
)
def test_that_no_extra_whitespace_is_produced(in_, format_options):
    parser_options = ParserOptions(reduce_whitespace=True)
    DefaultStringOptions.format_options = FormatOptions(**format_options)

    origin = parse_tree(in_, options=parser_options)
    assert_equal_trees(origin, parse_tree(str(origin), options=parser_options))


def test_that_root_siblings_are_preserved(files_path, result_file):
    origin_path = files_path / "root_siblings.xml"
    Document(origin_path).save(result_file, format_options=FormatOptions())

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


@skip_long_running_test
@pytest.mark.parametrize("file", TEI_FILES)
@pytest.mark.parametrize(
    "format_options",
    (
        None,
        FormatOptions(align_attributes=False, indentation="", width=0),
        FormatOptions(align_attributes=False, indentation="  ", width=0),
        FormatOptions(align_attributes=True, indentation="\t", width=0),
        FormatOptions(align_attributes=False, indentation="", width=77),
        FormatOptions(align_attributes=False, indentation="  ", width=77),
        FormatOptions(align_attributes=True, indentation="  ", width=77),
    ),
)
def test_transparency(file, format_options, result_file):
    """
    Tests that a serialization of a document will be parsed back to the identical
    document representation. (Prologue and epilogue are ignored here as whitespace is
    insignificant in these happy places.)
    This test is targeted to documents that follow this recommendation:
    https://wiki.tei-c.org/index.php/XML_Whitespace
    The serialization streams can't be compared directly, b/c of possible alterations in
    namespace prefixes, attributes order, dropped processing instructions and
    character / entity references that are expanded / serialized as unicode encoding.
    integrations-tests/test-parse-and-serialize-equality.py does the same on large
    scale. Thus anything caught there should be added to the `tei_*.xml` files here to
    for further investigations.
    """
    parser_options = ParserOptions(
        load_referenced_resources=True,
        preferred_parsers="expat",
        reduce_whitespace=format_options is not None,
        unplugged=True,
    )
    origin = Document(file, parser_options=parser_options)
    origin.save(result_file, format_options=format_options)
    _copy = Document(result_file, parser_options=parser_options)
    assert_equal_trees(origin.root, _copy.root)


@pytest.mark.parametrize(
    ("width", "out"),
    (
        (
            FormatOptions().width,
            """\
            <root>
              <a/>A
              <b xml:space="preserve"><x/><y/><z/></b>
              Z<c/>
            </root>""",
        ),
        (
            89,
            """\
            <root>
              <a/>A <b xml:space="preserve"><x/><y/><z/></b> Z<c/>
            </root>""",
        ),
    ),
)
def test_xml_space(width, out):
    DefaultStringOptions.format_options = FormatOptions(indentation="  ", width=width)

    # preserve in a subtree
    root = parse_tree(
        '<root><a/>A <b xml:space="preserve"><x/><y/><z/></b> Z<c/></root>'
    )
    assert str(root) == dedent(out)

    # ensure that it's considered at the root too
    root = parse_tree('<root xml:space="preserve"><t/></root>')
    assert str(root) == '<root xml:space="preserve"><t/></root>'

    # illegal values are ignored
    if width == 0:
        root = parse_tree('<root xml:space="illegal"><t/></root>')
        with pytest.warns(UserWarning, match=".*illegal.*"):
            assert str(root) == dedent(
                """\
                <root xml:space="illegal">
                  <t/>
                </root>"""
            )

    # and the application's default behaviour is determined by formatting options
    DefaultStringOptions.format_options = None
    root = parse_tree('<root xml:space="default"><t/></root>')
    assert str(root) == '<root xml:space="default"><t/></root>'
