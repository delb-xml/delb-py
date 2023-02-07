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

from collections.abc import Mapping
from typing import TYPE_CHECKING, Iterator, Optional

if TYPE_CHECKING:
    from _delb.typing import Final, NamespaceDeclarations

XML_NAMESPACE: Final = "http://www.w3.org/XML/1998/namespace"
XMLNS_NAMESPACE: Final = "http://www.w3.org/2000/xmlns/"

XML_ATT_ID: Final = f"{{{XML_NAMESPACE}}}id"
XML_ATT_SPACE: Final = f"{{{XML_NAMESPACE}}}space"


def deconstruct_clark_notation(name: str) -> tuple[Optional[str], str]:
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


def is_valid_namespace(value: str) -> bool:
    if value == "":
        return True

    if value in {XML_NAMESPACE, XMLNS_NAMESPACE}:
        raise ValueError(f"The namespace `{value}` must not be overridden.")

    # TODO? validate as RFC 3987 compliant
    #       see https://github.com/delb-xml/delb-py/issues/69

    return True


class Namespaces(Mapping):
    """
    A :term:`mapping` of prefixes to namespaces that ensures globally defined prefixes
    are available and unchanged.
    """

    __slots__ = ("__data", "fallback", "__hash")

    def __init__(
        self,
        namespaces: NamespaceDeclarations,
        *,
        fallback: Optional[Namespaces] = None,
    ):
        self.__data: NamespaceDeclarations
        if isinstance(namespaces, Namespaces):
            self.__data = namespaces.__data

        elif isinstance(namespaces, Mapping):
            # https://www.w3.org/TR/REC-xml-names seems not to care about redundantly
            # declared namespaces.
            self.__data = {}
            for prefix, namespace in namespaces.items():
                if prefix in ("xml", "xmlns"):
                    # https://www.w3.org/TR/xml-names/#xmlReserved
                    raise ValueError(
                        f"One must not override the global prefix `{prefix}`."
                    )
                if not is_valid_namespace(namespace):
                    raise RuntimeError("Unexpected code path")
                self.__data[prefix] = namespace

        else:
            raise TypeError

        self.fallback: NamespaceDeclarations = (
            {"xml": XML_NAMESPACE, "xmlns": XMLNS_NAMESPACE}
            if fallback is None
            else fallback
        )

        data_hash = hash(tuple(self.__data.items()))
        if isinstance(self.fallback, Namespaces):
            self.__hash = hash((data_hash, hash(self.fallback)))
        else:
            self.__hash = data_hash

    def __getitem__(self, item) -> str:
        return self.__data.get(item) or self.fallback[item]

    def __hash__(self) -> int:
        return self.__hash

    def __iter__(self) -> Iterator[Optional[str]]:
        return iter(self.__data)

    def __len__(self) -> int:
        return len(self.__data)

    def __str__(self) -> str:
        return str(self.__data)


__all__ = (
    "XML_NAMESPACE",
    "XMLNS_NAMESPACE",
    deconstruct_clark_notation.__name__,
    Namespaces.__name__,
)
