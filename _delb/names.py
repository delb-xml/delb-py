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

from collections.abc import Iterator, Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from typing import Final

    from _delb.typing import (  # noqa: F401
        Literal,
        NamespaceDeclarations,
        _NamespaceDeclarations,
        TypeAlias,
    )

XML_NAMESPACE: Final = "http://www.w3.org/XML/1998/namespace"
XMLNS_NAMESPACE: Final = "http://www.w3.org/2000/xmlns/"

COMMON_NAMESPACES: Final = MappingProxyType(
    {
        "fo": "http://www.w3.org/1999/XSL/Format",
        "mathml": "http://www.w3.org/1998/Math/MathML",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "sh": "http://www.w3.org/ns/shacl#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "svg": "http://www.w3.org/2000/svg",
        "vxml": "http://www.w3.org/2001/vxml",
        "xforms": "http://www.w3.org/2002/xforms/cr",
        "xhtml": "http://www.w3.org/1999/xhtml",
        "xi": "http://www.w3.org/2001/XInclude",
        "xlink": "http://www.w3.org/1999/xlink",
        "xsd": "http://www.w3.org/2001/XMLSchema",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsl": "http://www.w3.org/1999/XSL/Transform",
    }
)
GLOBAL_NAMESPACES: Final = MappingProxyType(
    {"xml": XML_NAMESPACE, "xmlns": XMLNS_NAMESPACE}
)
GLOBAL_PREFIXES: Final = tuple(GLOBAL_NAMESPACES)


# a generic won't work here because of the required default
Null: TypeAlias = "None | Literal['']"


def deconstruct_clark_notation(name: str, null: Null = None) -> tuple[str | Null, str]:
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
        return null, name


class Namespaces(Mapping):
    """
    A :term:`mapping` of prefixes to namespaces that ensures globally defined prefixes
    are available and unchanged.
    """

    __init_cache: Final[
        dict[int, tuple[_NamespaceDeclarations, _NamespaceDeclarations]]
    ] = {}

    __slots__ = (
        "__data",
        "__inverse_data",
    )

    def __init__(self, namespaces: NamespaceDeclarations):
        self.__data: _NamespaceDeclarations
        self.__inverse_data: _NamespaceDeclarations

        if isinstance(namespaces, Namespaces):
            self.__data = namespaces.__data
            self.__inverse_data = namespaces.__inverse_data
        elif isinstance(namespaces, Mapping):
            self.__data, self.__inverse_data = self.__init_data(namespaces)
        else:
            raise TypeError

    def __contains__(self, item: object):
        return item in self.__data

    def __getitem__(self, item: str) -> str:
        return self.__data.__getitem__(item)

    def __iter__(self) -> Iterator[str]:
        yield from (k for k in self.__data if k is not None)

    def __len__(self) -> int:
        return len(self.__data)

    def __repr__(self) -> str:
        return f"<{self.__class__.__qualname__}({self.__data}) [{hex(id(self))}]>"

    def __str__(self) -> str:
        return str(self.__data)

    def lookup_prefix(self, namespace: str | None) -> Optional[str]:
        """
        Resolves a namespace to a prefix.
        """
        return self.__inverse_data.get(namespace or "")

    @classmethod
    def __init_data(
        cls, declarations: NamespaceDeclarations
    ) -> tuple[_NamespaceDeclarations, _NamespaceDeclarations]:
        _hash = hash(frozenset(declarations.items()))
        if (cached_result := cls.__init_cache.pop(_hash, None)) is not None:
            cls.__init_cache[_hash] = cached_result  # put lru to the end
            return cached_result

        data = cls.__normalize_declarations(declarations)
        inverse_data = {v: k for k, v in data.items()}
        cls.__init_cache[_hash] = (data, inverse_data)
        if len(cls.__init_cache) > 16:  # TODO? configurable
            cls.__init_cache.pop(next(iter(cls.__init_cache)))

        return data, inverse_data

    @classmethod
    def __normalize_declarations(
        cls,
        declarations: NamespaceDeclarations,
    ) -> _NamespaceDeclarations:
        if None in declarations and "" in declarations:
            raise ValueError(
                "A default namespace has been defined redundantly with '' and `None.`"
            )

        prefix: str | None
        namespace: str

        declared_namespaces: set[str] = set()
        result: dict[str, str] = GLOBAL_NAMESPACES.copy()

        for prefix, namespace in declarations.items():
            prefix = cls.__validate_declaration(prefix, namespace, declared_namespaces)

            declared_namespaces.add(namespace)
            result[prefix] = namespace

        for prefix, namespace in COMMON_NAMESPACES.items():
            if namespace not in declared_namespaces:
                result.setdefault(prefix, namespace)

        return result

    @staticmethod
    def __validate_declaration(
        prefix: str | None, namespace: str, declared_namespaces: set[str]
    ) -> str:
        if prefix in GLOBAL_PREFIXES:
            # https://www.w3.org/TR/xml-names/#xmlReserved
            raise ValueError(f"One must not override the global prefix `{prefix}`.")

        if prefix is None:
            prefix = ""

        if namespace in {XML_NAMESPACE, XMLNS_NAMESPACE}:
            raise ValueError(f"The namespace `{namespace}` must not be overridden.")

        # TODO? validate as RFC 3987 compliant
        #       see https://github.com/delb-xml/delb-py/issues/69

        if namespace in declared_namespaces:
            raise ValueError(f"Namespace `{namespace}` is declared redundantly.")

        return prefix


__all__ = (
    "GLOBAL_NAMESPACES",
    "GLOBAL_PREFIXES",
    "XML_NAMESPACE",
    "XMLNS_NAMESPACE",
    deconstruct_clark_notation.__name__,
    Namespaces.__name__,
)
