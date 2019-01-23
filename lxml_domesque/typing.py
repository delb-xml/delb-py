from typing import TYPE_CHECKING, Callable, Dict

if TYPE_CHECKING:
    from lxml_domesque.nodes import NodeBase, TagNode  # noqa: F401

Filter = Callable[["NodeBase"], bool]
_WrapperCache = Dict[int, "TagNode"]
