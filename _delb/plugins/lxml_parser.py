# Copyright (C) 2018-'25  Frank Sachsenheim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from _delb.names import deconstruct_clark_notation
from _delb.parser import EventType, TagEventData
from _delb.plugins import XMLEventParserInterface


if TYPE_CHECKING:
    from collections.abc import Iterator

    from _delb.parser import Event, ParserOptions
    from _delb.typing import _AttributesData, BinaryReader


class LxmlParser(XMLEventParserInterface):
    __slots__ = ("parser",)

    name = "lxml"

    def __init__(self, options: ParserOptions, base_url: str | None, encoding: str):
        if encoding.endswith(("-be", "-le")):
            encoding = encoding[:-3]

        self.parser = etree.XMLPullParser(
            base_url=base_url,
            dtd_validation=False,
            encoding=encoding,
            events=("comment", "end", "pi", "start"),
            load_dtd=options.load_referenced_resources,
            no_network=options.unplugged,
            remove_blank_text=False,
            remove_comments=options.remove_comments,
            remove_pis=options.remove_processing_instructions,
            resolve_entities=True,
            strip_cdata=False,
        )

    def emit_events(self) -> Iterator[Event]:
        for event in self.parser.read_events():
            yield from self.handle_event(event)

    def handle_element_preceding_text(self, element: etree._Element):
        if ((parent := element.getparent()) is not None) and (
            parent.index(element) == 0
        ):
            if parent.text:
                yield EventType.Text, parent.text
        elif (previous := element.getprevious()) is not None:
            if previous.tail:
                yield EventType.Text, previous.tail
            previous.clear()

    def handle_event(self, event: etree._ParseEvent) -> Iterator[Event]:
        action, element = event
        assert isinstance(element, etree._Element)
        if action in ("comment", "pi", "start"):
            yield from self.handle_element_preceding_text(element)

        if action == "comment":
            assert isinstance(element, etree._Comment)
            text = element.text or ""
            yield EventType.Comment, text
        elif action == "end":
            if len(element):
                if element[-1].tail:
                    yield EventType.Text, element[-1].tail
                    element[-1].tail = None
            else:
                if element.text:
                    yield EventType.Text, element.text

            yield EventType.TagEnd, self.tag_event_data_from_element(element)
        elif action == "pi":
            assert isinstance(element, etree._ProcessingInstruction)
            assert isinstance(element.target, str)
            assert isinstance(element.text, str)
            yield EventType.ProcessingInstruction, (element.target, element.text)
        elif action == "start":
            yield EventType.TagStart, self.tag_event_data_from_element(element)

    def parse(self, data: BinaryReader | str) -> Iterator[Event]:
        if isinstance(data, str):
            self.parser.feed(data)
        else:
            while chunk := data.read():
                self.parser.feed(chunk)
                yield from self.emit_events()

        self.parser.close()
        yield from self.emit_events()

    def process_attributes(
        self, attributes: etree._Attrib, node_namespace: str
    ) -> _AttributesData:
        result = {}
        for name, value in attributes.items():
            assert isinstance(name, str)
            assert isinstance(value, str)
            namespace, local_name = deconstruct_clark_notation(name)
            result[namespace or node_namespace, local_name] = value
        return result

    def tag_event_data_from_element(self, element: etree._Element) -> TagEventData:
        qname = etree.QName(element)
        return TagEventData(
            namespace=qname.namespace or "",
            local_name=qname.localname,
            attributes=self.process_attributes(element.attrib, qname.namespace or ""),
        )


__all__ = (LxmlParser.__name__,)
