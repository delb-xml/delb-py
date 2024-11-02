# Copyright (C) 2018-'24  Frank Sachsenheim
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


from lxml import etree


class ParserOptions:
    """
    The configuration options that define an XML parser's behaviour.

    :param reduce_whitespace: :meth:`Reduce the content's whitespace
                                <delb.Document.reduce_whitespace>`.
    :param remove_comments: Ignore comments.
    :param remove_processing_instructions: Don't include processing instructions in the
                                           parsed tree.
    :param resolve_entities: Resolve entities.
    :param unplugged: Don't load referenced resources over network.
    """

    def __init__(
        self,
        reduce_whitespace: bool = False,
        remove_comments: bool = False,
        remove_processing_instructions: bool = False,
        resolve_entities: bool = True,
        unplugged: bool = False,
    ):
        self.reduce_whitespace = reduce_whitespace
        self.remove_comments = remove_comments
        self.remove_processing_instructions = remove_processing_instructions
        self.resolve_entities = resolve_entities
        self.unplugged = unplugged

    def _make_parser(self) -> etree.XMLParser:
        return etree.XMLParser(
            no_network=self.unplugged,
            remove_blank_text=False,
            remove_comments=self.remove_comments,
            remove_pis=self.remove_processing_instructions,
            resolve_entities=self.resolve_entities,
            strip_cdata=False,
        )


__all__ = (ParserOptions.__name__,)
