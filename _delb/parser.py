# Copyright (C) 2018-'22  Frank Sachsenheim
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

from typing import Optional
from warnings import warn

from lxml import etree


class ParserOptions:
    """
    The configuration options that define an XML parser's behaviour.

    :param cleanup_namespaces: Consolidate XML namespace declarations.
    :param collapse_whitespace: :meth:`Collapse the content's whitespace
                                <delb.Document.collapse_whitespace>`.
    :param remove_comments: Ignore comments.
    :param remove_processing_instructions: Don't include processing instructions in the
                                           parsed tree.
    :param resolve_entities: Resolve entities.
    :param unplugged: Don't load referenced resources over network.
    """

    def __init__(
        self,
        cleanup_namespaces: bool = False,
        collapse_whitespace: bool = False,
        remove_comments: bool = False,
        remove_processing_instructions: bool = False,
        resolve_entities: bool = True,
        unplugged: bool = False,
    ):
        self.cleanup_namespaces = cleanup_namespaces
        self.collapse_whitespace = collapse_whitespace
        self.remove_comments = remove_comments
        self.remove_processing_instructions = remove_processing_instructions
        self.resolve_entities = resolve_entities
        self.unplugged = unplugged

    def _make_parser(self) -> etree.XMLParser:
        return etree.XMLParser(
            no_network=self.unplugged,
            ns_clean=self.cleanup_namespaces,
            remove_blank_text=False,
            remove_comments=self.remove_comments,
            remove_pis=self.remove_processing_instructions,
            resolve_entities=self.resolve_entities,
            strip_cdata=False,
        )


def _compat_get_parser(
    parser: Optional[etree.XMLParser],
    parser_options: Optional[ParserOptions],
    collapse_whitesppace: Optional[bool],
) -> tuple[etree.XMLParser, Optional[bool]]:
    if parser is not None and parser_options is not None:
        raise ValueError(
            "Only either the deprecated `parser` argument or `parser_options` "
            "argument can be provided."
        )

    if parser is None:
        if parser_options is None:
            if collapse_whitesppace is not None:
                warn(
                    "The `collapse_whitespace` argument is deprecated, use the "
                    "property with the same name on the `parser_options` instead.",
                    category=DeprecationWarning,
                    stacklevel=2,
                )
                parser_options = ParserOptions(collapse_whitespace=collapse_whitesppace)
            else:
                parser_options = ParserOptions()
        return parser_options._make_parser(), parser_options.collapse_whitespace

    else:
        warn(
            "Directly providing a lxml-parser is deprecated, use the "
            "`parser_options` argument instead.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return parser, collapse_whitesppace or False


__all__ = (ParserOptions.__name__,)
