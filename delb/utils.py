import enum
from itertools import zip_longest
from typing import Optional

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
        lhn: Optional[NodeBase],
        rhn: Optional[NodeBase],
    ):
        self.difference_kind = difference_kind
        self.lhn: Optional[NodeBase] = lhn
        self.rhn: Optional[NodeBase] = rhn

    def __bool__(self):
        return self.difference_kind is TreeDifferenceKind.None_

    def __str__(self):
        difference_kind = self.difference_kind

        if difference_kind is TreeDifferenceKind.None_:
            return "Trees are equal."

        parent = self.lhn.parent
        if parent is None:
            parent_msg_tail = ":"
        else:
            parent_msg_tail = f", parent node has location_path {parent.location_path}:"

        if difference_kind is TreeDifferenceKind.NodeContent:
            return f"Nodes' content differ{parent_msg_tail}\n{self.lhn!r}\n{self.rhn!r}"
        elif difference_kind is TreeDifferenceKind.NodeType:
            return (
                f"Nodes are of different type{parent_msg_tail} "
                f"{self.lhn.__class__} != {self.rhn.__class__}"
            )

        assert isinstance(self.lhn, TagNode)
        assert isinstance(self.rhn, TagNode)

        if difference_kind is TreeDifferenceKind.TagAttributes:
            return (
                f"Attributes of tag nodes at {self.lhn.location_path} differ:\n"
                f"{self.lhn.attributes}\n{self.rhn.attributes}"
            )
        elif difference_kind is TreeDifferenceKind.TagChildrenSize:
            result = f"Child nodes of tag nodes at {self.lhn.location_path} differ:"
            for a, b in zip_longest(
                self.lhn.iterate_children(), self.rhn.iterate_children(), fillvalue=None
            ):
                result += f"\n\n{a!r}\n{b!r}"
            return result
        elif difference_kind is TreeDifferenceKind.TagLocalName:
            return (
                f"Local names of tag nodes at {self.lhn.location_path} differ: "
                f"{self.lhn.local_name} != {self.rhn.location_path}"
            )
        elif difference_kind is TreeDifferenceKind.TagNamespace:
            return (
                f"Namespaces of tag nodes at {self.lhn.location_path} differ: "
                f"{self.lhn.namespace} != {self.rhn.namespace}"
            )


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
