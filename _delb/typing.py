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


from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, Iterable, Union

from lxml import etree

if TYPE_CHECKING:
    from _delb.nodes import NodeBase, _TagDefinition


# TODO annotate as TypeAlias(es) when support for Python 3.9 is dropped


Filter = Callable[["NodeBase"], bool]
NodeSource = Union[str, "NodeBase", "_TagDefinition"]

LoaderResult = Union[etree._ElementTree, str]
Loader = Callable[[Any, SimpleNamespace], LoaderResult]
LoaderConstraint = Union[Loader, Iterable[Loader], None]


__all__ = (
    "Filter",
    "Loader",
    "LoaderConstraint",
    "LoaderResult",
    "NodeSource",
)
