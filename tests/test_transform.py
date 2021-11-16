from typing import NamedTuple

from delb import Document
from delb.transform import Transformation, TransformationSequence


class ResolveCopyOf(Transformation):
    def transform(self):
        for node in self.root.css_select("*[copyOf]"):
            source_id = node["copyOf"]
            # FIXME remove str() when attributes were fixed
            # FIXME there could be something wrong with the query
            source_node = self.origin_document.xpath(
                f'//*[@xml:id="{str(source_id)[1:]}"]'
            ).first
            cloned_node = source_node.clone(deep=True)
            cloned_node.id = None
            node.replace_with(cloned_node)


class ResolveChoiceOptions(NamedTuple):
    corr: bool = True
    reg: bool = True


class ResolveChoice(Transformation):
    options_class = ResolveChoiceOptions

    def __init__(self, options):
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


def test_transform():
    document = Document(
        """\
        <root>
            <div id="1">
                <choice><sic>taeteraetae</sic><corr>täterätä</corr></choice>
            </div>
            <div copyOf="#1"/>
        </root>
    """
    )

    second_div = document.css_select("div").last.clone()
    transformation = TransformationSequence(
        ResolveCopyOf, ResolveChoice(ResolveChoiceOptions(corr=True))
    )
    assert str(transformation(second_div, document)) == "<div>täterätä</div>"
