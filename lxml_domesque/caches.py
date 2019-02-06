from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

if TYPE_CHECKING:
    from lxml_domesque import Document, TagNode  # noqa: F401


roots_of_documents = (
    WeakKeyDictionary()
)  # type: WeakKeyDictionary["Document", "TagNode"]
