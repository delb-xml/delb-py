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

import sys

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, AnyStr, BinaryIO, Protocol, TypeVar


if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from types import SimpleNamespace

    if sys.version_info < (3, 10):  # DROPWITH Python 3.9
        from typing_extensions import TypeAlias
    else:
        from typing import TypeAlias

    from _delb.nodes import NodeBase, _TagDefinition
    from _delb.xpath.ast import EvaluationContext


if sys.version_info < (3, 11):  # DROPWITH Python 3.10
    from typing_extensions import Literal, Self
else:
    from typing import Literal, Self


class BinaryReader(Protocol):
    def close(self):
        pass

    def read(self, n: int = -1) -> bytes:
        pass


QualifiedName: TypeAlias = tuple[str, str]
AttributeAccessor: TypeAlias = QualifiedName | str
_AttributesData: TypeAlias = dict[QualifiedName, str]

GenericDecorated = TypeVar("GenericDecorated", bound=Callable[..., Any])
SecondOrderDecorator: TypeAlias = "Callable[[GenericDecorated], GenericDecorated]"

Filter: TypeAlias = "Callable[[NodeBase], bool]"
NamespaceDeclarations: TypeAlias = "Mapping[str | None, str]"
_NamespaceDeclarations: TypeAlias = "Mapping[str, str]"
NodeSource: TypeAlias = "str | NodeBase | _TagDefinition"

InputStream: TypeAlias = AnyStr | BinaryIO
LoaderResult: TypeAlias = "Sequence[NodeBase] | str"
Loader: TypeAlias = "Callable[[Any, SimpleNamespace], LoaderResult]"
LoaderConstraint: TypeAlias = "Loader | Iterable[Loader] | None"

NodeTypeNameLiteral: TypeAlias = Literal[
    "CommentNode", "ProcessingInstructionNode", "TagNode", "TextNode"
]


XPathFunction: TypeAlias = "Callable[[EvaluationContext, *Any], Any]"


__all__ = (
    "AttributeAccessor",
    "_AttributesData",
    "BinaryReader",
    "Filter",
    "GenericDecorated",
    "InputStream",
    "Loader",
    "LoaderConstraint",
    "LoaderResult",
    "NamespaceDeclarations",
    "NodeSource",
    "QualifiedName",
    "SecondOrderDecorator",
    "Self",
    "XPathFunction",
)
