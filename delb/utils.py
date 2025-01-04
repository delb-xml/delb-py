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

import enum
from itertools import zip_longest

from _delb.exceptions import InvalidCodePath
from _delb.nodes import NodeBase, TagNode
from _delb.utils import *  # noqa
from _delb.utils import __all__


# TODO increase test coverage


class TreeDifferenceKind(enum.Enum):
    None_ = enum.auto()
    NodeContent = enum.auto()
    NodeType = enum.auto()
    TagAttributes = enum.auto()
    TagChildrenSize = enum.auto()
    TagLocalName = enum.auto()
    TagNamespace = enum.auto()


class TreesComparisonResult:
    """
    Instances of this class describe one or no difference between two trees.
    Casting an instance to :class:`bool` will yield :obj:`True` when it describes no
    difference, thus the compared trees were equal.
    Casted to strings they're intended to support debugging.
    """

    def __init__(
        self,
        difference_kind: TreeDifferenceKind,
        lhn: NodeBase | None,
        rhn: NodeBase | None,
    ):
        self.difference_kind = difference_kind
        self.lhn: NodeBase | None = lhn
        self.rhn: NodeBase | None = rhn

    def __bool__(self):
        return self.difference_kind is TreeDifferenceKind.None_

    def __str__(self):
        if self.difference_kind is TreeDifferenceKind.None_:
            return "Trees are equal."
        elif self.difference_kind in (
            TreeDifferenceKind.NodeContent,
            TreeDifferenceKind.NodeType,
        ):
            return self.__str_child()
        else:
            return self.__str_tag()

    def __str_child(self) -> str:
        assert self.lhn is not None
        parent = self.lhn.parent
        if parent is None:
            parent_msg_tail = ":"
        else:
            parent_msg_tail = f", parent node has location_path {parent.location_path}:"

        if self.difference_kind is TreeDifferenceKind.NodeContent:
            return f"Nodes' content differ{parent_msg_tail}\n{self.lhn!r}\n{self.rhn!r}"
        else:  # difference_kind is TreeDifferenceKind.NodeType
            return (
                f"Nodes are of different type{parent_msg_tail} "
                f"{self.lhn.__class__} != {self.rhn.__class__}"
            )

    def __str_tag(self) -> str:

        assert isinstance(self.lhn, TagNode)
        assert isinstance(self.rhn, TagNode)

        if self.difference_kind is TreeDifferenceKind.TagAttributes:
            return (
                f"Attributes of tag nodes at {self.lhn.location_path} differ:\n"
                f"{self.lhn.attributes}\n{self.rhn.attributes}"
            )
        elif self.difference_kind is TreeDifferenceKind.TagChildrenSize:
            result = f"Child nodes of tag nodes at {self.lhn.location_path} differ:"
            for a, b in zip_longest(
                self.lhn.iterate_children(),
                self.rhn.iterate_children(),
                fillvalue=None,
            ):
                result += f"\n\n{a!r}\n{b!r}"
            return result
        elif self.difference_kind is TreeDifferenceKind.TagLocalName:
            return (
                f"Local names of tag nodes at {self.lhn.location_path} differ: "
                f"{self.lhn.local_name} != {self.rhn.location_path}"
            )
        elif self.difference_kind is TreeDifferenceKind.TagNamespace:
            return (
                f"Namespaces of tag nodes at {self.lhn.location_path} differ: "
                f"{self.lhn.namespace} != {self.rhn.namespace}"
            )

        raise InvalidCodePath()


def compare_trees(lhr: NodeBase, rhr: NodeBase) -> TreesComparisonResult:
    """
    Compares two node trees for equality. Upon the first detection of a difference of
    nodes that are located at the same position within the compared (sub-)trees a
    mismatch is reported.

    :param lhr: The node that is considered as root of the left hand operand.
    :param rhr: The node that is considered as root of the right hand operand.
    :return: An object that contains information about the first or no difference.

    While node types that can't have descendants are comparable with a comparison
    expression, the :class:`TagNode` type deliberately doesn't implement the ``==``
    operator, because it isn't clear whether a comparison should also consider the
    node's descendants as this function does.
    """
    if not isinstance(rhr, lhr.__class__):
        return TreesComparisonResult(TreeDifferenceKind.NodeType, lhr, rhr)

    if isinstance(lhr, TagNode):
        assert isinstance(rhr, TagNode)
        if lhr.namespace != rhr.namespace:
            return TreesComparisonResult(TreeDifferenceKind.TagNamespace, lhr, rhr)
        if lhr.local_name != rhr.local_name:
            return TreesComparisonResult(TreeDifferenceKind.TagLocalName, lhr, rhr)
        if lhr.attributes != rhr.attributes:
            return TreesComparisonResult(TreeDifferenceKind.TagAttributes, lhr, rhr)
        if len(lhr) != len(rhr):
            return TreesComparisonResult(TreeDifferenceKind.TagChildrenSize, lhr, rhr)

        for lhn, rhn in zip(lhr.iterate_children(), rhr.iterate_children()):
            result = compare_trees(lhn, rhn)
            if not result:
                return result

    elif lhr != rhr:
        return TreesComparisonResult(TreeDifferenceKind.NodeContent, lhr, rhr)

    return TreesComparisonResult(TreeDifferenceKind.None_, None, None)


__all__ = __all__ + (compare_trees.__name__,)
