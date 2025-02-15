from typing import NamedTuple

import pytest

from benchmarks.conftest import TEI_FILES
from delb import is_text_node, Document, TagNode
from delb.transform import Transformation

TEI_NAME_TAG_TYPE_MAP = {"persName": "person", "placeName": "place"}


def warn(message: str):
    pass


class Options(NamedTuple):
    corr: bool = True
    expan: bool = True
    reg: bool = True


class NormalizeDocument(Transformation):
    options_class = Options

    def __init__(self, options=None):
        super().__init__(options)
        self.choice_keep_selector = ",".join(
            (
                "corr" if self.options.corr else "sic",
                "expan" if self.options.expan else "abbr",
                "reg" if self.options.reg else "orig",
            )
        )
        self.choice_drop_selector = ",".join(
            (
                "abbr" if self.options.expan else "expan",
                "orig" if self.options.reg else "reg",
                "sic" if self.options.corr else "corr",
            )
        )
        self.normalize_type_selector = ",".join(TEI_NAME_TAG_TYPE_MAP.keys())

    def transform(self):
        self.normalize_named_entities()
        self.resolve_choice()
        self.clean_tables()
        self.resolve_copyOf()

    def clean_tables(self):
        for node in self.root.css_select(
            "table, table > row, table > supplied, table > supplied > row"
        ):
            for child in tuple(node.iterate_children(is_text_node)):
                if not child.content.isspace():
                    warn(
                        "Found text node with non-whitespace characters between table "
                        "nodes: " + child.content
                    )
                child.detach()

    def normalize_named_entities(self):
        for node in self.root.css_select(self.normalize_type_selector):
            node.attributes["type"] = TEI_NAME_TAG_TYPE_MAP[node.local_name]
            node.local_name = "name"

    def resolve_choice(self):
        drop_selector = self.choice_drop_selector
        keep_selector = self.choice_keep_selector
        for choice_node in self.root.css_select("choice"):
            choice_node.css_select(drop_selector).first.detach()
            choice_node.css_select(keep_selector).first.detach(retain_child_nodes=True)
            choice_node.detach(retain_child_nodes=True)

    def resolve_copyOf(self):  # noqa: N802
        document = self.origin_document
        for node in self.root.css_select("*[copyOf]"):
            source_id = node.attributes.pop("copyOf", "")
            assert source_id
            source = document.xpath(f'//*[@xml:id="{source_id[1:]}"]').first
            assert isinstance(source, TagNode)
            _copy = source.clone(deep=True)
            _copy.id = None
            node.replace_with(_copy)


def normalize_documents(transformation, document):
    transformation(document.root, origin_document=document)


@pytest.mark.parametrize("file", TEI_FILES)
def test_normalize_documents(benchmark, file):
    benchmark(normalize_documents, NormalizeDocument(), Document(file))
