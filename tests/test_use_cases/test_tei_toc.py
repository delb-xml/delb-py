from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

from delb import Document, NodeBase, TagNode
from _delb.utils import _crunch_whitespace


TEI_NAMESPACE: Final = "http://www.tei-c.org/ns/1.0"


def is_pagebreak(node: NodeBase) -> bool:
    return (
        isinstance(node, TagNode)
        and node.local_name == "pb"
        and node.namespace == TEI_NAMESPACE
    )


def is_section(node: NodeBase) -> bool:
    return (
        isinstance(node, TagNode)
        and node.local_name == "div"
        and node.namespace == TEI_NAMESPACE
    )


@dataclass
class TOCSection:
    """A document's section."""

    index: int
    level: int
    pages_range: tuple[Optional[str], Optional[str]]
    subsections: tuple[TOCSection, ...]
    title: str
    location_path: str

    @property
    def end_page(self):
        return self.pages_range[1]

    @property
    def start_page(self):
        return self.pages_range[0]


class TableOfContents:
    """Not a table but a tree of a document's sections."""

    def __init__(self, document):
        self.document: Document = document

    @property
    def back_sections(self) -> tuple[TOCSection, ...]:
        """A sequence of all top-level back sections."""
        if back_nodes := self.document.xpath("/TEI/text/back"):
            assert back_nodes.size == 1
            return self._parse_sections(back_nodes.first, 0)
        else:
            return ()

    @property
    def body_sections(self) -> tuple[TOCSection, ...]:
        """A sequence of all top-level body sections."""
        if body_nodes := self.document.xpath("/TEI/text/body"):
            assert body_nodes.size == 1
            return self._parse_sections(body_nodes.first, 0)
        else:
            return ()

    @property
    def in_order_of_appearance(self) -> tuple[TOCSection, ...]:
        def get_children(section):
            result = []
            for subsection in section.subsections:
                result.append(subsection)
                result.extend(get_children(subsection))
            return result

        result = []
        for part in ("body", "back"):
            sections = getattr(self, f"{part}_sections")
            for section in sections:
                result.append(section)
                result.extend(get_children(section))
        return tuple(result)

    def _parse_sections(self, node: TagNode, level: int) -> tuple[TOCSection, ...]:
        result = []
        for index, section_node in enumerate(node.xpath("div")):
            pages_range = (
                section_node.fetch_preceding(is_pagebreak).attributes.get("n"),
                section_node.last_descendant.fetch_preceding(
                    is_pagebreak
                ).attributes.get("n"),
            )
            result.append(
                TOCSection(
                    index=index,
                    level=level,
                    pages_range=pages_range,
                    subsections=self._parse_sections(section_node, level + 1),
                    title=self._find_sections_title(section_node),
                    location_path=section_node.location_path,
                )
            )
        return tuple(result)

    @staticmethod
    def _find_sections_title(node: TagNode) -> Optional[str]:
        for xpath in ("head", "table/head"):
            if head_elements := node.xpath(xpath):
                return _crunch_whitespace(head_elements[0].full_text).strip()


def test_table_of_contents(files_path):
    document = Document(files_path / "marx_manifestws_1848.TEI-P5.xml")
    toc = TableOfContents(document)

    expected = (
        {
            "level": 0,
            "index": 0,
            "pages_range": ("[3]", "23"),
            "title": "Manifest der Kommunistischen Partei.",
            "subsections": (
                {
                    "level": 1,
                    "index": 0,
                    "pages_range": ("[3]", "11"),
                    "title": "I. Bourgeois und Proletarier.",
                    "subsections": (),
                },
                {
                    "level": 1,
                    "index": 1,
                    "pages_range": ("11", "16"),
                    "title": "II. Proletarier und Kommunisten.",
                    "subsections": (),
                },
                {
                    "level": 1,
                    "index": 2,
                    "pages_range": ("16", "22"),
                    "title": "III. Socialistische und kommunistische Literatur.",
                    "subsections": (
                        {
                            "level": 2,
                            "index": 0,
                            "pages_range": ("16", "20"),
                            "title": "1) Der reaktionaire Socialismus.",
                            "subsections": (
                                {
                                    "level": 3,
                                    "index": 0,
                                    "pages_range": ("16", "17"),
                                    "title": "a) Der feudale Socialismus.",
                                    "subsections": (),
                                },
                                {
                                    "level": 3,
                                    "index": 1,
                                    "pages_range": ("17", "18"),
                                    "title": "b) Kleinbürgerlicher Socialismus.",
                                    "subsections": (),
                                },
                                {
                                    "level": 3,
                                    "index": 2,
                                    "pages_range": ("18", "20"),
                                    "title": "c) Der deutsche oder der wahre "
                                    "Socialismus.",
                                    "subsections": (),
                                },
                            ),
                        },
                        {
                            "level": 2,
                            "index": 1,
                            "pages_range": ("20", "21"),
                            "title": "2) Der konservative oder Bourgeois-"
                            "Socialismus.",
                            "subsections": (),
                        },
                        {
                            "level": 2,
                            "index": 2,
                            "pages_range": ("21", "22"),
                            "title": "3) Der kritisch-utopistische Socialismus und "
                            "Kommunismus.",
                            "subsections": (),
                        },
                    ),
                },
                {
                    "level": 1,
                    "index": 3,
                    "pages_range": ("22", "23"),
                    "title": "IV. Stellung der Kommunisten zu den verschiedenen "
                    "oppositionellen Parteien.",
                    "subsections": (),
                },
            ),
        },
    )

    def compare_sections(sections, expected):
        assert len(sections) == len(expected)
        for section, expected_record in zip(sections, expected):
            assert section.level == expected_record["level"]
            assert section.index == expected_record["index"]
            assert section.title == expected_record["title"]
            assert section.pages_range == expected_record["pages_range"]
            compare_sections(section.subsections, expected_record["subsections"])

    compare_sections(toc.body_sections, expected)
