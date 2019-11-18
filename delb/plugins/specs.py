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

from typing import Union, Iterable, List

import pluggy  # type: ignore
from delb.typing import Loader


hookspec = pluggy.HookspecMarker("delb")


@hookspec
def configure_loaders(loaders: List[Loader]) -> None:
    """
    Configures the document loaders. Implementations are expected to manipulate
    the list that is provided to the hook.

    An example module that is specified as ``delb`` plugin for an IPFS loader might
    look like this:

    .. testcode::

        from types import SimpleNamespace
        from typing import Any, List

        import pluggy
        from delb.plugins.contrib.core_loaders import text_loader
        from delb.typing import Loader, LoaderResult


        def ipfs_loader(source: Any, config: SimpleNamespace) -> LoaderResult:
            if isinstance(source, str) and source.startswith("ipfs://"):
                # let's assume the document is loaded as string here:
                data = "<root/>"

                return text_loader(data, parser)

            # return nothing to indicate that this loader is not suited to load the
            # document:
            return None, {}


        hookimpl = pluggy.HookimplMarker("delb")


        @hookimpl
        def configure_loaders(loaders: List[Loader]):
            loaders.append(ipfs_loader)

    Note that the ``config`` argument that is passed to a loader function contains
    processed configuration data, it's the :attr:`delb.Document.config` property after
    :meth:`delb.DocumentExtensionHooks._init_config` has been processed.

    You might want to specify a loader to be considered before another one. Let's
    assume a loader shall figure out what to load from a remote XML resource that
    contains a reference to the actual document.
    That one would have to be considered before the one that loads XML documents from
    a URL into a :class:`delb.Document`:

    .. testcode::

        import pluggy
        from delb.plugins.contrib.https_loader import https_loader


        def mets_loader(source, config) -> LoaderResult:
            # loading logic here
            return None, {}


        hookimpl = pluggy.HookimplMarker("delb")


        @hookimpl
        def configure_loaders(loaders: List[Loader]):
            loaders.insert(loaders.index(https_loader), mets_loader)

    Admittedly it would be simpler to just specify the position as ``0``, but the point
    is to show that the position can be determined dynamically.
    """


@hookspec
def get_document_extensions() -> Union[type, Iterable]:
    """
    This hook returns document extension classes which are supposed to add additional
    attributes to a document, e.g. derived data or methods to interact with storage
    systems. The available hook methods that can be implemented by an extension are
    defined in :class:`delb.DocumentExtensionHooks`.

    Extension classes are *mixin classes* in Python OOP jargon.

    :return: Either a single class or an iterable of such that shall extend the
             :class:`delb.Document` class.
    """
