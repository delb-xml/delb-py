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

from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Iterator, Optional

if TYPE_CHECKING:
    from typing import Final
    from _delb.typing import NamespaceDeclarations

XML_NAMESPACE: Final = "http://www.w3.org/XML/1998/namespace"
XMLNS_NAMESPACE: Final = "http://www.w3.org/2000/xmlns/"

GLOBAL_NAMESPACES: Final = MappingProxyType(
    {"xml": XML_NAMESPACE, "xmlns": XMLNS_NAMESPACE}
)
GLOBAL_PREFIXES: Final = tuple(GLOBAL_NAMESPACES)


def deconstruct_clark_notation(name: str) -> tuple[str | None, str]:
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

    __slots__ = (
        "__data",
        "_fallback",
        "__prefixes_lookup_cache",
    )

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
            self.__data = {}
            for prefix, namespace in namespaces.items():
                if prefix in {"xml", "xmlns"}:
                    # https://www.w3.org/TR/xml-names/#xmlReserved
                    raise ValueError(
                        f"One must not override the global prefix `{prefix}`."
                    )
                if not is_valid_namespace(namespace):
                    raise RuntimeError("Unexpected code path")
                self.__data[prefix] = namespace

        else:
            raise TypeError

        self._fallback: MappingProxyType[str, str] | NamespaceDeclarations = (
            {"xml": XML_NAMESPACE, "xmlns": XMLNS_NAMESPACE}
            if fallback is None
            else fallback
        )

        self.__prefixes_lookup_cache: dict[str, str | None] = {
            v: k for k, v in GLOBAL_NAMESPACES.items()
        }

    def __getitem__(self, item) -> str:
        return self.__data.get(item) or self._fallback[item]

    def __iter__(self) -> Iterator[str | None]:
        return iter(self.__data)

    def __len__(self) -> int:
        return len(self.__data)

    def __str__(self) -> str:
        return str(self.__data)

    def lookup_prefix(self, namespace: str) -> str | None:
        """
        Resolves a namespace to a prefix while considering namespace declarations of
        ascending nodes.
        """
        if namespace in self.__prefixes_lookup_cache:
            return self.__prefixes_lookup_cache[namespace]

        encountered_prefixes: set[None | str] = set()
        scope: Namespaces = self
        result = None

        while result is None:
            for prefix, _namespace in scope.__data.items():
                if namespace == _namespace:
                    if prefix is None and None not in encountered_prefixes:
                        self.__prefixes_lookup_cache[namespace] = None
                        return None
                    elif result is None:
                        result = prefix

                encountered_prefixes.add(prefix)

            if not isinstance(scope._fallback, Namespaces):
                break
            scope = scope._fallback

        if result is None:
            # this is necessary, b/c with the lxml semantics, a None value represents
            # the default namespace's empty prefix; they're carried over to avoid
            # conversions that'd affect too much operations.
            # TODO when changing this, mind that there's a code depending on this:
            raise KeyError(f"The namespace `{namespace}` hasn't been declared.")

        self.__prefixes_lookup_cache[namespace] = result
        return result


__all__ = (
    "GLOBAL_NAMESPACES",
    "GLOBAL_PREFIXES",
    "XML_NAMESPACE",
    "XMLNS_NAMESPACE",
    deconstruct_clark_notation.__name__,
    Namespaces.__name__,
)
