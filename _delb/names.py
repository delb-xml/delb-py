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

from collections import ChainMap
from collections.abc import MutableMapping
from typing import Mapping, Optional, Tuple


XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
XMLNS_NAMESPACE = "http://www.w3.org/2000/xmlns/"

XML_ATT_ID = f"{{{XML_NAMESPACE}}}id"
XML_ATT_SPACE = f"{{{XML_NAMESPACE}}}space"

GLOBAL_PREFIXES = {"xml": XML_NAMESPACE, "xmlns": XMLNS_NAMESPACE}


def deconstruct_clark_notation(name: str) -> Tuple[Optional[str], str]:
    """
    Deconstructs a name in Clark notation, that may or may not include a namespace.

    :param name: An attribute's or tag node's name.
    :return: A tuple with the extracted namespace and local name.

    >>> deconstruct_clark_notation('{http://www.tei-c.org/ns/1.0}text')
    ('http://www.tei-c.org/ns/1.0', 'text')

    >>> deconstruct_clark_notation('div')
    (None, 'div')
    """
    if name.startswith("{"):
        a, b = name.split("}", maxsplit=1)
        return a[1:], b
    else:
        return None, name


class Namespaces(MutableMapping):
    """
    A :term:`mapping` of prefixes to namespaces that ensures globally defined prefixes
    are available and unchanged.
    """

    # https://www.w3.org/TR/xml-names/#xmlReserved

    __slots__ = ("data",)

    def __init__(self, namespaces: Mapping[Optional[str], str]):
        self.data: Mapping[Optional[str], str]
        if isinstance(namespaces, Namespaces):
            self.data = namespaces.data
        else:
            self.data = namespaces

    def __delitem__(self, key):
        if key not in GLOBAL_PREFIXES:
            del self.data[key]

    def __getitem__(self, item):
        return GLOBAL_PREFIXES.get(item) or self.data[item]

    def __iter__(self):
        return iter(ChainMap(GLOBAL_PREFIXES, self.data))

    def __len__(self):
        return len(self.data) + 2

    def __setitem__(self, key, value):
        if key in GLOBAL_PREFIXES:
            raise ValueError(f"One must not override the prefix '{key}'.")
        self.data[key] = value

    def __str__(self):
        return str(dict(self))


__all__ = (
    "XML_NAMESPACE",
    "XMLNS_NAMESPACE",
    deconstruct_clark_notation.__name__,
    Namespaces.__name__,
)
