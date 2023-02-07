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

from collections.abc import Callable, Iterable
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Mapping, Optional
from typing import Union  # noqa: UNT001


from lxml import etree

if TYPE_CHECKING:
    import sys

    if sys.version_info < (3, 10):
        from typing_extensions import TypeAlias
    else:
        from typing import TypeAlias

    from _delb.nodes import NodeBase, _TagDefinition


Filter: TypeAlias = Callable[["NodeBase"], bool]
NamespaceDeclarations: TypeAlias = Mapping[Optional[str], str]
NodeSource: TypeAlias = Union[str, "NodeBase", "_TagDefinition"]

LoaderResult: TypeAlias = etree._ElementTree | str
Loader: TypeAlias = Callable[[Any, SimpleNamespace], LoaderResult]
LoaderConstraint: TypeAlias = Optional[Loader | Iterable[Loader]]


__all__ = (
    "Filter",
    "Loader",
    "LoaderConstraint",
    "LoaderResult",
    "NamespaceDeclarations",
    "NodeSource",
)
