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


"""
The ``core_loaders`` module provides a set loaders to retrieve documents from various
data sources.
"""

from __future__ import annotations

from contextlib import suppress
from io import IOBase, UnsupportedOperation
from pathlib import Path
from typing import TYPE_CHECKING, Any

from _delb.builder import parse_nodes
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
        if data.parent is not None:
            return "Node has a parent node."
        if data.document is not None:
            data = data.clone(deep=True)
        return (data,)
    return "The input value is not a TagNode instance."


@plugin_manager.register_loader()
def path_loader(data: Any, config: SimpleNamespace) -> LoaderResult:
    """
    This loader loads from a file that is pointed at with a :class:`pathlib.Path`
    instance. That instance will be bound to ``source_path`` on the document's
    :attr:`Document.config` attribute.
    """
    if isinstance(data, Path):
        if not hasattr(config, "source_url"):
            config.source_url = (Path.cwd() / data).as_uri()
        with data.open("rb") as file:
            return buffer_loader(file, config)
    return "The input value is not a pathlib.Path instance."


@plugin_manager.register_loader(after=path_loader)
def buffer_loader(data: Any, config: SimpleNamespace) -> LoaderResult:
    """
    This loader loads a document from a :term:`file-like object` that reads binary data.
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
        return tuple(
            parse_nodes(data, config.parser_options, base_url=config.source_url)
        )
    return "The input value is no buffer object."


@plugin_manager.register_loader()
def text_loader(data: Any, config: SimpleNamespace) -> LoaderResult:
    """
    Parses a string containing a full document.
    """
    if isinstance(data, (bytes, str)):
        return tuple(parse_nodes(data, config.parser_options, base_url=None))
    return "The input value is not a byte sequence or a string."


__all__ = (
    buffer_loader.__name__,
    path_loader.__name__,
    tag_node_loader.__name__,
    text_loader.__name__,
)
