import pytest
import sys

if sys.version_info < (3, 7):
    pytest.skip("Requires Python 3.7.", allow_module_level=True)


from dataclasses import dataclass  # noqa: E402
from typing import Optional, Tuple, Union  # noqa: E402

from lxml_domesque import Document, NodeBase, TagNode  # noqa: E402


def is_pagebreak(node: NodeBase) -> bool:
    return isinstance(node, TagNode) and node.local_name == "pb"


def is_section(node: NodeBase) -> bool:
    return isinstance(node, TagNode) and node.local_name == "div"


@dataclass
class TOCSection:
    """ A document's section. """

    index: int
    level: int
    pages_range: Tuple[Optional[str], Optional[str]]
    subsections: Tuple["TOCSection", ...]
    title: str
    location_path: str

    @property
    def end_page(self):
        return self.pages_range[1]

    @property
    def start_page(self):
        return self.pages_range[0]


class TableOfContents:
    """ Not a table but a tree of a document's sections.  """

    def __init__(self, document):
        self.document = document

    @property
    def back_sections(self) -> Tuple[TOCSection, ...]:
        """ A sequence of all top-level back sections. """
        back_nodes = self.document.xpath("./text/back")
        if back_nodes:
            assert len(back_nodes) == 1
            back_node = back_nodes[0]
            return self._parse_sections(back_node, 0)
        else:
            return ()

    @property
    def body_sections(self) -> Tuple[TOCSection, ...]:
        """ A sequence of all top-level body sections. """
        body_nodes = self.document.xpath("./text/body")
        if body_nodes:
            assert len(body_nodes) == 1
            body_node = body_nodes[0]
            return self._parse_sections(body_node, 0)
        else:
            return ()

    @property
    def in_order_of_appearance(self) -> Tuple[TOCSection, ...]:
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

    def _parse_sections(self, node: TagNode, level: int) -> Tuple[TOCSection, ...]:
        result = []
        for index, section_element in enumerate(node.xpath("./div")):
            pages_range = (
                section_element.previous_node_in_stream(is_pagebreak).attributes.get(
                    "n"
                ),
                self._find_sections_last_page(section_element),
            )
            result.append(
                TOCSection(
                    index,
                    level,
                    pages_range,
                    self._parse_sections(section_element, level + 1),
                    self._find_sections_title(section_element),
                    section_element.location_path,
                )
            )
        return tuple(result)

    @staticmethod
    def _find_sections_last_page(section_node: TagNode) -> str:
        sections_last_node = section_node.last_child
        while sections_last_node.last_child is not None:
            sections_last_node = sections_last_node.last_child

        pagebreak = sections_last_node.previous_node_in_stream(is_pagebreak)

        return pagebreak.attributes.get("n")

    @staticmethod
    def _find_sections_title(element) -> Union[str, None]:
        for xpath in ("./head", "./table/head"):
            head_elements = element.xpath(xpath)
            if head_elements:
                text = head_elements[0].full_text.strip()
                text = text.replace("\n", " ")
                while "  " in text:
                    text = text.replace("  ", " ")
                return text


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
