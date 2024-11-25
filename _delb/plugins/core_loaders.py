# Copyright (C) 2018-'24  Frank Sachsenheim
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
The ``core_loaders`` module provides a set loaders to retrieve documents from various
data sources.
"""

from __future__ import annotations

from contextlib import suppress
from copy import deepcopy
from io import IOBase, UnsupportedOperation
from pathlib import Path
from typing import TYPE_CHECKING, cast, Any, IO
from warnings import warn

from lxml import etree

from _delb import utils
from _delb.nodes import TagNode
from _delb.plugins import plugin_manager

if TYPE_CHECKING:
    from types import SimpleNamespace

    from _delb.typing import LoaderResult


def tag_node_loader(data: Any, config: SimpleNamespace) -> LoaderResult:
    """
    This loader loads, or rather clones, a :class:`delb.TagNode` instance and its
    descendant nodes.
    """
    if isinstance(data, TagNode):
        tree = etree.ElementTree()
        if data.document is None:
            tree._setroot(data._etree_obj)
        else:
            root = data.clone(deep=True)
            tree._setroot(root._etree_obj)
            utils._copy_root_siblings(data._etree_obj, root._etree_obj)
        return tree
    return "The input value is not a TagNode instance."


@plugin_manager.register_loader()
def etree_loader(data: Any, config: SimpleNamespace) -> LoaderResult:
    """
    This loader processes :class:`lxml.etree._Element` and
    :class:`lxml.etree._ElementTree` instances.
    """
    if isinstance(data, etree._ElementTree):
        warn(
            "lxml's etree models will not be usable inputs with the "
            "contributed core loaders.",
            category=DeprecationWarning,
        )
        return deepcopy(data)
    if isinstance(data, etree._Element):
        warn(
            "lxml's etree models will not be usable inputs with the "
            "contributed core loaders.",
            category=DeprecationWarning,
        )
        return etree.ElementTree(
            element=deepcopy(data), parser=config.parser_options._make_parser()
        )
    return "The input value is neither an etree.Element or …Tree instance."


@plugin_manager.register_loader(after=etree_loader)
def path_loader(data: Any, config: SimpleNamespace) -> LoaderResult:
    """
    This loader loads from a file that is pointed at with a :class:`pathlib.Path`
    instance. That instance will be bound to ``source_path`` on the document's
    :attr:`Document.config` attribute.
    """
    if isinstance(data, Path):
        config.source_url = (Path.cwd() / data).as_uri()
        with data.open("r") as file:
            return buffer_loader(file, config)
    return "The input value is not a pathlib.Path instance."


@plugin_manager.register_loader(after=path_loader)
def buffer_loader(data: Any, config: SimpleNamespace) -> LoaderResult:
    """
    This loader loads a document from a :term:`file-like object`.
    """
    if isinstance(data, IOBase):
        if (
            not hasattr(config, "source_url")
            and isinstance(name := getattr(data, "name", None), (bytes, str))
            and (
                path := Path.cwd()
                / Path(name if isinstance(name, str) else name.decode())
            ).is_file()
        ):
            config.source_url = path.as_uri()
        with suppress(UnsupportedOperation):
            data.seek(0)
        return etree.parse(
            cast("IO", data), parser=config.parser_options._make_parser()
        )
    return "The input value is no buffer object."


@plugin_manager.register_loader()
def text_loader(data: Any, config: SimpleNamespace) -> LoaderResult:
    """
    Parses a string containing a full document.
    """
    if isinstance(data, str):
        data = data.encode()
    if isinstance(data, bytes):
        root = etree.fromstring(data, config.parser_options._make_parser())
        return etree.ElementTree(element=root)
    return "The input value is not a byte sequence."


__all__ = (
    buffer_loader.__name__,
    etree_loader.__name__,
    path_loader.__name__,
    tag_node_loader.__name__,
    text_loader.__name__,
)
