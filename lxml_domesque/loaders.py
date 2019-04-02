# TODO docs

from copy import deepcopy
from io import IOBase
from pathlib import Path
from typing import cast, Any, Callable, IO, List, Optional, Tuple

from lxml import etree

from lxml_domesque import utils
from lxml_domesque.nodes import TagNode
from lxml_domesque.typing import _WrapperCache

try:
    import requests
except ImportError:
    requests = None  # type: ignore


# types

LoaderResult = Tuple[Optional[etree._ElementTree], _WrapperCache]
Loader = Callable[[Any, etree.XMLParser], LoaderResult]


# utils


class HttpsStreamWrapper:
    def __init__(self, response: requests.Response) -> None:
        self._iterator = response.iter_content(chunk_size=None, decode_unicode=False)

    def read(self, _) -> bytes:
        try:
            return next(self._iterator)
        except StopIteration:
            return b""


# loaders


def buffer_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    if isinstance(data, IOBase):
        return etree.parse(cast(IO, data), parser=parser), {}
    return None, {}


def etree_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    if isinstance(data, etree._ElementTree):
        return deepcopy(data), {}
    if isinstance(data, etree._Element):
        return etree.ElementTree(element=deepcopy(data), parser=parser), {}
    return None, {}


def ftp_http_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    if isinstance(data, str) and data.lower().startswith(("http://", "ftp://")):
        return etree.parse(data, parser=parser), {}
    return None, {}


if requests:

    def https_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
        if isinstance(data, str) and data.lower().startswith("https://"):
            response = requests.get(data, stream=True)
            return (
                etree.parse(cast(IO, HttpsStreamWrapper(response)), parser=parser),
                {},
            )
        return None, {}


def path_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    if isinstance(data, Path):
        return etree.parse(str(data.resolve()), parser=parser), {}
    return None, {}


def tag_node_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    if isinstance(data, TagNode):
        tree = etree.ElementTree(parser=parser)
        root = data.clone(deep=True)
        tree._setroot(root._etree_obj)
        utils.copy_heading_pis(data._etree_obj, root._etree_obj)
        return tree, root._wrapper_cache
    return None, {}


def text_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    if isinstance(data, str):
        data = data.encode()
    if isinstance(data, bytes):
        root = etree.fromstring(data, parser)
        return etree.ElementTree(element=root), {}
    return None, {}


configured_loaders: List[Loader] = [
    path_loader,
    buffer_loader,
    ftp_http_loader,
    text_loader,
    etree_loader,
]


if requests:
    configured_loaders.insert(2, https_loader)


__all__ = ("Loader", "configured_loaders")
