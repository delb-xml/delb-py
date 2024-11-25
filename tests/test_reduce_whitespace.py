# test_subclasses implicitly also tests collapsing and trimming

from textwrap import dedent
from typing import Final

import pytest
from delb import new_tag_node, Document, TagNode

from tests.utils import assert_equal_trees


TEI_NAMESPACE: Final = "http://www.tei-c.org/ns/1.0"


def test_contained_milestone_tags_each_followed_by_whitespace():
    document = Document("<root><lb/>Hello <lb/> <lb/> <lb/> world!</root>")
    document.reduce_whitespace()
    assert document.root.full_text == "Hello    world!"


def test_empty_text_node():
    node = new_tag_node("node", children=[""])
    assert len(node) == 1
    node._reduce_whitespace()
    assert len(node) == 0


def test_empty_before_stripable_node():
    document = Document("<root> 1<b/></root>")
    document.root.insert_children(0, "")
    document.reduce_whitespace()
    assert len(document.root) == 2
    assert document.root.full_text == "1"


def test_milestone_tag_with_altering_whitespace_neighbour():
    document = Document("<p><hi>then</hi> give<lb/> the</p>")
    document.reduce_whitespace()
    assert " give " in document.root.full_text

    document = Document("<p><hi>then</hi> give <lb/>the</p>")
    document.reduce_whitespace()
    assert " give " in document.root.full_text


def test_nodes_in_between():
    # this is about the "; E…, s. xi" part in a specific context
    document = Document("<head>G… I, <t>H… in E…</t>; E…, s. xi<hi>x</hi></head>")
    document.reduce_whitespace()
    assert document.root.full_text == "G… I, H… in E…; E…, s. xix"

    document = Document("<head>G… I, <t>H… in E…</t>\n; E…, s. xi<hi>x</hi></head>")
    document.reduce_whitespace()
    assert document.root.full_text == "G… I, H… in E… ; E…, s. xix"

    document = Document("<head>G… I, <t>H… in E…</t>; E…, s. xi  <hi>x</hi></head>")
    document.reduce_whitespace()
    assert document.root.full_text == "G… I, H… in E…; E…, s. xi x"


def test_samples_from_Manifest_der_kommunistischen_Partei(files_path):  # noqa: N802
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")
    document.reduce_whitespace()
    imprints = document.xpath("//docImprint", namespaces={None: TEI_NAMESPACE})

    assert imprints[0].full_text == "Veröffentlicht im Februar 1848."
    assert "46, Liverpool Street" in imprints[1].full_text


# TODO remove warning filter when empty declarations are used as fallback
@pytest.mark.filterwarnings("ignore:.* namespace declarations")
def test_space_preserve():
    document = Document(
        """
    <root>
        <title>
            I Roy -
            <hi>Touting I Self</hi>
        </title>
        <matrix xml:space="preserve">HB 243 A  Re</matrix>
        <matrix xml:space="preserve">HB 243 B\tRe</matrix>
    </root>
    """
    )

    document.reduce_whitespace()
    root = document.root

    assert root.first_child.full_text == "I Roy - Touting I Self"
    assert root.css_select("matrix")[0].full_text == "HB 243 A  Re"
    assert root.css_select("matrix")[1].full_text == "HB 243 B\tRe"


def test_tei_recommendation_examples():
    # it's not much unfortunately
    # https://wiki.tei-c.org/index.php/XML_Whitespace
    # the contained errors are fixed w/o annotations

    def parse_sample(s: str) -> TagNode:
        d = Document(s)
        d.reduce_whitespace()
        return d.root

    # ## "Where XML Considers Whitespace to be Significant"

    sample_1 = parse_sample('<title type="main"/>')
    sample_2 = parse_sample('<title     type = "main" />')
    assert_equal_trees(sample_1, sample_2)

    sample_1 = parse_sample("<name>JoAnn</name>")
    sample_2 = parse_sample("<name>Jo Ann</name>")
    assert sample_1.full_text != sample_2.full_text

    # ## "Normalize = Collapse + Trim"  # noqa: E800

    reference_sample = "<name>Jo Ann</name>"
    assert str(parse_sample("<name>Jo    Ann</name>")) == reference_sample
    assert str(parse_sample("<name>Jo\n    Ann</name>")) == reference_sample
    assert str(parse_sample("<name> Jo Ann</name>")) == reference_sample
    assert str(parse_sample("<name>\n    Jo Ann</name>")) == reference_sample
    assert str(parse_sample("<name>\n    Jo   \n    Ann\n</name>")) == reference_sample

    # ## "Default Whitespace Processing"

    sample = parse_sample(
        dedent(
            """\
        <persName>
          <forename>Edward</forename>
          <forename>George</forename>
          <surname type="linked">Bulwer-Lytton</surname>, <roleName>Baron Lytton of
          <placeName>Knebworth</placeName>
          </roleName>
        </persName>"""
        )
    )
    assert sample.full_text == "Edward George Bulwer-Lytton, Baron Lytton of Knebworth"
    assert (
        sample.full_text != " Edward George Bulwer-Lytton, Baron Lytton of Knebworth "
    )
    assert sample.full_text != "EdwardGeorgeBulwer-Lytton,BaronLyttonofKnebworth"

    # #### "Text-Only Elements"

    sample_1 = parse_sample("<country>Australia</country>")
    sample_2 = parse_sample("<country>   Australia   </country>")
    sample_3 = parse_sample("<country>\n        Australia     \n</country>")
    assert sample_1.full_text == sample_2.full_text == sample_3.full_text

    assert (
        parse_sample(
            "<emph xml:space='preserve' rend='underline'> Yes! </emph>"
        ).full_text
        == " Yes! "
    )

    sample_1 = parse_sample("<name>Ralph Waldo Emerson</name>")
    sample_2 = parse_sample("<name>   Ralph Waldo  Emerson   </name>")
    sample_3 = parse_sample(
        dedent(
            """\
        <name>
                Ralph    
                Waldo    
               Emerson   
        </name>"""  # noqa: W291
        )
    )  # noqa: E124
    assert sample_1.full_text == sample_2.full_text == sample_3.full_text

    # #### "Mixed-Content Elements"

    sample_1 = parse_sample(
        dedent(
            """\
        <p>  The <emph> cat </emph> ate  the <foreign>grande croissant</foreign>. I didn't!
          </p>"""  # noqa: E501
        )
    )
    sample_2 = parse_sample(
        """\
        <p>The 
        <emph>cat</emph>
        ate the 
        <foreign>grande croissant</foreign>. 
        I didn't!</p>"""  # noqa: W291
    )
    sample_3 = parse_sample(
        "<p>The <emph>cat</emph> ate the <foreign>grande croissant</foreign>. "
        "I didn't!</p>"
    )
    assert sample_1.full_text == sample_2.full_text == sample_3.full_text

    assert (
        parse_sample(
            "<p>The<emph> cat </emph>ate the <foreign>grande croissant</foreign>. "
            "I didn't!</p>"
        ).full_text
        == "Thecatate the grande croissant. I didn't!"
    )

    # ## "Structured Elements and xsl:strip-space"  # noqa: 800

    sample_1 = parse_sample(
        "<root><settlement>New</settlement><settlement>York</settlement></root>"
    )
    sample_2 = parse_sample(
        "<root><settlement>New</settlement> <settlement>York</settlement></root>"
    )
    assert sample_1.full_text != sample_2.full_text
