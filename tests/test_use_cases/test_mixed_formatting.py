from __future__ import annotations

from typing import NamedTuple, Optional

from _delb.parser import ParserOptions
from delb import (
    is_tag_node,
    DefaultStringOptions,
    Document,
    FormatOptions,
    TagNode,
    TextNode,
)
from delb.transform import Transformation


# mark docs inclusion start
class MixedFormattingOptions(NamedTuple):
    indentation: str = "  "
    text_width: int = 79


class MixedFormatting(Transformation):
    options: MixedFormattingOptions

    def mind_the_gaps(self, node: TagNode):
        for child in tuple(node.iterate_children(is_tag_node))[:-1]:
            if not isinstance(child.fetch_following_sibling(), TextNode):
                child.add_following_siblings(" ")
            self.mind_the_gaps(child)

    def transform(self):
        if isinstance((first_child := self.root.first_child), TextNode):
            first_child.content = "\n"
        else:
            self.root.insert_children(0, "\n")

        self.mind_the_gaps(self.root[1])
        self.replace_with_formatted(
            self.root[1],
            FormatOptions(
                align_attributes=False,
                indentation=self.options.indentation,
                text_width=0,
            ),
        )

        if isinstance((separator := self.root[2]), TextNode):
            separator.content = "\n"
        else:
            self.root.insert_children(1, "\n")

        self.replace_with_formatted(
            self.root[3],
            FormatOptions(
                align_attributes=False,
                indentation=self.options.indentation,
                text_width=self.options.text_width,
            ),
        )

        if len(self.root) > 4:
            self.root.last_child.content = "\n"
        else:
            self.root.append_children("\n")

    @staticmethod
    def replace_with_formatted(node: TagNode, format_options: FormatOptions):
        node.replace_with(
            Document(
                node.serialize(format_options=format_options),
                parser_options=ParserOptions(reduce_whitespace=False, unplugged=True),
            ).root
        )


def mixed_format(document: Document, options: Optional[MixedFormattingOptions]) -> str:
    document = document.clone()
    MixedFormatting(options)(document.root)
    default_formatting_options = DefaultStringOptions.format_options
    DefaultStringOptions.format_options = None
    result = str(document)
    DefaultStringOptions.format_options = default_formatting_options
    return result[: (i := result.find(">") + 1)] + "\n" + result[i:]
    # mark docs inclusion end


def test_mixed_formatting(files_path):
    document = Document(files_path / "serialization-example-input.xml")
    assert (
        mixed_format(
            document,
            MixedFormattingOptions(
                text_width=59,
            ),
        )
        == (files_path / "mixed-formatting-reference.xml").read_text()
    )
