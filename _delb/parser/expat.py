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

import codecs
from collections import deque
from typing import TYPE_CHECKING, Final
from urllib.parse import urljoin, urlparse
from xml import sax

from _delb.exceptions import InvalidCodePath, ParsingProcessingError
from _delb.parser.base import Event, EventType, TagEventData, XMLEventParserInterface

if TYPE_CHECKING:
    from collections.abc import Iterator

    from _delb.parser import ParserOptions
    from _delb.typing import BinaryReader


NAMESPACE_SEPARATOR: Final = " "


class ContentHandler(sax.handler.ContentHandler):
    __slots__ = ("events", "options")

    def __init__(self, events: deque[Event], options: ParserOptions):
        self.events = events
        self.options = options

    def characters(self, content: str):
        self.events.append((EventType.Text, content))

    def endElementNS(self, name: tuple[None | str, str], qname: str):  # noqa: N802
        self.events.append(
            (EventType.TagEnd, TagEventData(name[0] or "", name[1], None))
        )

    def ignorableWhitespace(self, whitespace: str):  # noqa: N802
        raise InvalidCodePath

    def processingInstruction(self, target: str, data: str):  # noqa: N802
        assert isinstance(target, str)
        assert isinstance(data, str)
        if not self.options.remove_processing_instructions:
            self.events.append((EventType.ProcessingInstruction, (target, data)))

    def skippedEntity(self, name: str):  # noqa: N802
        raise NotImplementedError

    def startElementNS(  # noqa: N802
        self,
        name: tuple[None | str, str],
        qname: str,
        attrs: sax.xmlreader.AttributesNSImpl,
    ):
        assert hasattr(attrs, "_attrs")
        self.events.append(
            (
                EventType.TagStart,
                TagEventData(
                    name[0] or "",
                    name[1],
                    {(ns or "", ln): v for (ns, ln), v in attrs._attrs.items()},
                ),
            )
        )


class EntityResolver(sax.handler.EntityResolver):
    __slots__ = ("base_url", "options", "scheme")

    def __init__(self, options: ParserOptions, base_url: str | None):
        self.base_url = base_url
        self.options = options
        if base_url is None:
            self.scheme = None
        else:
            self.scheme, *_ = urlparse(base_url)

    def resolveEntity(  # noqa: N802
        self, publicId: str | None, systemId: str | None  # noqa: N803
    ):
        if not self.options.load_referenced_resources:
            raise ParsingProcessingError(
                "The document includes character entities that are declared in "
                "external resources."
            )

        _id = systemId or publicId
        assert _id is not None

        if self.base_url is None or (
            self.options.unplugged
            and self.scheme is not None
            and self.scheme.startswith("http")
        ):
            raise ParsingProcessingError(f"Cannot load external resource '{_id}'.")

        return urljoin(self.base_url, _id, allow_fragments=False)


class LexcialHandler(sax.handler.LexicalHandler):
    __slots__ = ("events", "options")

    def __init__(self, events: deque[Event], options: ParserOptions):
        self.events = events
        self.options = options

    def comment(self, content: str):
        assert isinstance(content, str)
        if not self.options.remove_comments:
            self.events.append((EventType.Comment, content))

    def endCDATA(self):  # noqa: N802
        pass

    def endDTD(self):  # noqa: N802
        pass

    def startCDATA(self):  # noqa: N802
        pass

    def startDTD(  # noqa: N802
        self, name: str, public_id: None | str, system_id: None | str
    ):
        pass


class ExpatParser(XMLEventParserInterface):
    __slots__ = ("encoding", "events", "options", "parser")

    def __init__(self, options: ParserOptions, base_url: str | None, encoding: str):
        self.encoding = encoding
        self.events: deque[Event] = deque()
        self.options = options
        self.parser = self.make_parser(base_url=base_url)

    def make_parser(self, base_url: str | None) -> sax.xmlreader.IncrementalParser:
        parser = sax.make_parser()
        assert isinstance(parser, sax.xmlreader.IncrementalParser)
        parser.setContentHandler(ContentHandler(self.events, self.options))
        parser.setEntityResolver(EntityResolver(self.options, base_url))
        parser.setFeature(sax.handler.feature_external_ges, True)
        parser.setProperty(
            sax.handler.property_lexical_handler,
            LexcialHandler(self.events, self.options),
        )
        # TODO ErrorHandler?
        parser.setFeature(sax.handler.feature_namespaces, True)
        return parser

    def parse(self, data: BinaryReader) -> Iterator[Event]:
        decoder = codecs.getincrementaldecoder(self.encoding)()
        eof = False
        prior_text = ""
        while not eof:
            if chunk := data.read():
                self.parser.feed(decoder.decode(chunk))
            else:
                self.parser.feed(decoder.decode(b"", final=True))
                self.parser.close()
                eof = True

            while self.events:
                event_type, event_data = self.events.popleft()
                if event_type is EventType.Text:
                    assert isinstance(event_data, str)
                    prior_text += event_data
                else:
                    if prior_text:
                        yield EventType.Text, prior_text
                        prior_text = ""
                    yield event_type, event_data

        if prior_text:
            yield EventType.Text, prior_text


__all__ = (ExpatParser.__name__,)
