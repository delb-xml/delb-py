from _delb.nodes import NodeBase, TagNode
from _delb.utils import *  # noqa
from _delb.utils import __all__


def compare_trees(a: NodeBase, b: NodeBase) -> bool:
    """
    Compares two node trees for equality. While node types that can't have descendants
    are comparable with a comparison expression, the :class:`TagNode` type deliberately
    doesn't implement the ``==`` operator, because it isn't clear whether a comparison
    should also consider the node's descendants as this function does.
    """
    if not isinstance(a, TagNode):
        return a == b

    if (
        not isinstance(b, TagNode)
        or a.namespace != b.namespace
        or a.local_name != b.local_name
        or a.attributes != b.attributes
        or len(a) != len(b)
    ):
        return False

    return all(
        compare_trees(x, y) for x, y in zip(a.iterate_children(), b.iterate_children())
    )


__all__ = __all__ + (compare_trees.__name__,)
