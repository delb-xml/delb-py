# Copyright (C) 2019  Frank Sachsenheim
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


"""
The ``loaders`` module provides a set loaders to retrieve documents from common kinds
of storage and mechanics to register custom loaders and to alter the loaders
configuration.
"""

from copy import deepcopy
from io import IOBase
from pathlib import Path
from typing import cast, Any, Callable, IO, List, Optional, Tuple

from lxml import etree

from delb import utils
from delb.nodes import TagNode
from delb.typing import Loader, LoaderResult

try:
    import requests
except ImportError:
    requests = None  # type: ignore


# loader registration


configured_loaders: List[Loader] = []
"""
This list contains the loaders that are tried in order when a new
:class:`delb.Document` instance is created.
"""


def register_loader(position: Optional[int] = None) -> Callable[[Loader], Loader]:
    """
    This is a decorator that registers a document loader. E.g. to register a loader
    that retrieves a document from IPFS:

    .. testcode::

        from lxml import etree
        from delb.loaders import register_loader, text_loader
        from delb.typing import LoaderResult

        @register_loader()
        def ipfs_loader(source: Any, parser: etree.XMLParser) -> LoaderResult:
            if isinstance(source, str) and source.startswith("ipfs://"):
                # let's assume the document is loaded as string here:
                data = "<root/>"
                return text_loader(data, parser)
            # return nothing to indicate that this loader is not suited or failed to
            # load the document:
            return None, {}

    You might want to specify the loader to be considered before another one. Let's
    assume a loader shall figure out what to load from a remote resource that contains
    a reference to the actual document.
    That one would have to be considered before the one loads XML documents from a URL
    into a :class:`delb.Document`:

    .. testcode::

        from lxml import etree
        from delb.loaders import (
            configured_loaders, https_loader, register_loader
        )
        from delb.typing import LoaderResult

        @register_loader(position=configured_loaders.index(https_loader))
        def mets_loader(source: Any, parser: etree.XMLParser) -> LoaderResult:
            # loading logic here
            return None, {}

    Admittedly it would be simpler to just specify the position as ``0``, but the point
    is to show that the position can be figured out dynamically.

    :param position: The index at which the loader is added to
                     :obj:`configured_loaders`, it will be appended if omitted.
    """

    if position is None:

        def register(loader: Loader) -> Loader:
            configured_loaders.append(loader)
            return loader

    else:

        def register(loader: Loader) -> Loader:
            assert isinstance(position, int)
            configured_loaders.insert(position, loader)
            return loader

    return register


# loaders


@register_loader()
def tag_node_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    """
    This loader loads, or rather clones, a :class:`delb.TagNode` instance and
    its descendant nodes.
    """
    if isinstance(data, TagNode):
        tree = etree.ElementTree(parser=parser)
        root = data.clone(deep=True)
        tree._setroot(root._etree_obj)
        utils.copy_root_siblings(data._etree_obj, root._etree_obj)
        return tree, root._wrapper_cache
    return None, {}


@register_loader()
def etree_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    """
    This loader processes :class:`lxml.etree._Element` and
    :class:`lxml.etree._ElementTree` instances.
    """
    if isinstance(data, etree._ElementTree):
        return deepcopy(data), {}
    if isinstance(data, etree._Element):
        return etree.ElementTree(element=deepcopy(data), parser=parser), {}
    return None, {}


@register_loader()
def path_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    """
    This loader loads from a file that is pointed at with a
    :class:`pathlib.Path` instance.
    """
    if isinstance(data, Path):
        with data.open("r") as file:
            return buffer_loader(file, parser)
    return None, {}


@register_loader()
def buffer_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    """
    This loader loads a document from a :term:`file-like object`.
    """
    if isinstance(data, IOBase):
        return etree.parse(cast(IO, data), parser=parser), {}
    return None, {}


if requests:

    class HttpsStreamWrapper(IOBase):
        def __init__(self, response: requests.Response):
            self._iterator = response.iter_content(
                chunk_size=None, decode_unicode=False
            )

        def read(self, _) -> bytes:
            try:
                return next(self._iterator)
            except StopIteration:
                return b""

    @register_loader()
    def https_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
        """
        This loader loads a document from a URL with the ``https`` scheme and is only
        available when requests_ is installed.

        .. _requests: http://python-requests.org
        """
        if isinstance(data, str) and data.lower().startswith("https://"):
            response = requests.get(data, stream=True)
            return buffer_loader(HttpsStreamWrapper(response), parser)
        return None, {}


@register_loader()
def ftp_http_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    """
    Loads a document from a URL with either the ``ftp`` or ``http`` schema.
    """
    if isinstance(data, str) and data.lower().startswith(("http://", "ftp://")):
        return etree.parse(data, parser=parser), {}
    return None, {}


@register_loader()
def text_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
    """
    Parses a string containing a full document.
    """
    if isinstance(data, str):
        data = data.encode()
    if isinstance(data, bytes):
        try:
            root = etree.fromstring(data, parser)
        except etree.XMLSyntaxError:
            pass
        else:
            return etree.ElementTree(element=root), {}
    return None, {}


__all__: Tuple[str, ...] = ("configured_loaders", register_loader.__name__)
__all__ += tuple(x.__name__ for x in configured_loaders)
