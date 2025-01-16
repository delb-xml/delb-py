from typing import NamedTuple

import pytest

from delb import Document, ParserOptions, parse_tree, tag
from delb.transform import Transformation, TransformationSequence


class DoNothing(Transformation):
    def transform(self):
        pass


class ResolveChoiceOptions(NamedTuple):
    corr: bool = True
    reg: bool = True


class ResolveChoice(Transformation):
    options_class = ResolveChoiceOptions

    def __init__(self, options=None):
        super().__init__(options)
        self.keep_selector = ",".join(
            (
                "corr" if self.options.corr else "sic",
                "reg" if self.options.reg else "orig",
            )
        )
        self.drop_selector = ",".join(
            (
                "sic" if self.options.corr else "corr",
                "orig" if self.options.reg else "reg",
            )
        )

    def transform(self):
        for choice_node in self.root.css_select("choice"):
            node_to_drop = choice_node.css_select(self.drop_selector).first
            node_to_drop.detach()

            node_to_keep = choice_node.css_select(self.keep_selector).first
            node_to_keep.detach(retain_child_nodes=True)

            choice_node.detach(retain_child_nodes=True)


class ResolveCopyOf(Transformation):
    def transform(self):
        for node in self.root.css_select("*[copyOf]"):
            source_id = node["copyOf"]
            source_node = self.origin_document.xpath(
                f'//*[@xml:id="{source_id[1:]}"]'
            ).first
            cloned_node = source_node.clone(deep=True)
            cloned_node.id = None
            node.replace_with(cloned_node)


class ResolveItemList(Transformation):
    def transform(self):
        for i, node in enumerate(self.root.xpath("//ul/li")):
            source_node = self.origin_document.xpath(f"//item[{i+1}]/name").first
            node.append_children(source_node.full_text)


class ResolveItems(Transformation):
    def transform(self):
        ul = self.root.css_select("body > ul").first
        for node in (
            n for n in self.origin_document.xpath("//name") if n.full_text.strip()
        ):
            ul.append_children(tag("li"))
            cloned_node = node.clone(deep=True)
            node.replace_with(tag("item", cloned_node))


def test_simple_transformation():
    root = parse_tree('<root><node copyOf="#foo"/><node copyOf="#bar"/></root>')
    document = Document(
        """<radix>
             <a>
               <b xml:id="foo"><c>hi</c></b>
               <b xml:id="baz"/>
             </a>
             <a xml:id="bar">na?</a>
          </radix>
        """
    )
    resolve_copy_of = ResolveCopyOf()
    tree = resolve_copy_of(root, document)
    assert str(tree) == "<root><b><c>hi</c></b><a>na?</a></root>"


def test_transformation_options():
    document = Document(
        """\
        <root>
            <choice><sic>taeteraetae</sic><corr>täterätä</corr></choice>
        </root>
        """,
        parser_options=ParserOptions(reduce_whitespace=True),
    )
    transformation = ResolveChoice()
    result = transformation(document.root)
    assert str(result) == "<root>täterätä</root>"


def test_transformation_sequence():
    document = Document(
        """\
        <root>
            <div xml:id="d1">
                <choice><sic>taeteraetae</sic><corr>täterätä</corr></choice>
            </div>
            <div copyOf="#d1"/>
        </root>
        """,
        parser_options=ParserOptions(reduce_whitespace=True),
    )
    transformation = TransformationSequence(
        ResolveCopyOf, ResolveChoice(ResolveChoiceOptions(corr=False))
    )
    result = transformation(document.root, document)
    second_div = result.css_select("div").last
    assert str(second_div) == "<div>taeteraetae</div>"


def test_transformation_sequence_sequence():
    document = Document(
        """<cast>
            <name/>
            <name>abla fahita</name>
            <name/>
            <name>caro</name>
            <name>boudi</name>
        </cast>""",
        parser_options=ParserOptions(reduce_whitespace=True),
    )
    root = parse_tree("<doc><body><ul/></body></doc>")
    transformation = TransformationSequence(
        DoNothing,
        TransformationSequence(ResolveItems, DoNothing()),
        TransformationSequence(ResolveItemList),
    )
    assert str(transformation(root, document)) == (
        "<doc><body><ul><li>abla fahita</li>"
        "<li>caro</li><li>boudi</li></ul></body></doc>"
    )

    with pytest.raises(TypeError):
        TransformationSequence(transformation, None)
