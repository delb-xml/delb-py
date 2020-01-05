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

from inspect import isclass
from types import SimpleNamespace
from typing import Callable, Iterable, Type, Union

import pkg_resources

from delb.typing import Loader


LoaderConstraint = Union[Loader, Iterable[Loader], None]


class PluginManager:
    def __init__(self):
        self.plugins = SimpleNamespace(document_extensions=[], loaders=[],)

    @staticmethod
    def load_plugins():
        """
        Loads all modules that are registered as entrypoint in the ``delb`` group.
        """
        for entrypoint in pkg_resources.iter_entry_points("delb"):
            entrypoint.load()

    def register_document_extension(self, extension: Type) -> Type:
        """
        This decorator registers document extension classes which are supposed to add
        additional attributes to a document, e.g. derived data or methods to interact
        with storage systems. All attributes of an extension should share a common
        prefix that terminates with an underscore, e.g. `storage_load`, `storage_save`,
        etc.

        There are hook methods that an extension can implement, they are declared in
        :class:`delb.DocumentExtensionHooks`.

        Extension classes are *mixin classes* in Python OOP jargon.
        """

        assert isclass(extension)
        self.plugins.document_extensions.append(extension)
        return extension

    def register_loader(
        self, before: LoaderConstraint = None, after: LoaderConstraint = None
    ) -> Callable:
        """
        Registers a document loader.

        An example module that is specified as ``delb`` plugin for an IPFS loader might
        look like this:

        .. testcode::

            from types import SimpleNamespace
            from typing import Any

            from delb.plugins import plugin_manager
            from delb.plugins.contrib.core_loaders import text_loader
            from delb.typing import LoaderResult


            @plugin_manager.register_loader()
            def ipfs_loader(source: Any, config: SimpleNamespace) -> LoaderResult:
                if isinstance(source, str) and source.startswith("ipfs://"):
                    # let's assume the document is loaded as string here:
                    data = "<root/>"

                    return text_loader(data, config)

                # return an indication why this loader didn't attempt to load in order
                # to support debugging
                return "The input value is not an URL with the ipfs scheme."


        Note that the ``config`` argument that is passed to a loader function contains
        configuration data, it's the :attr:`delb.Document.config` property after
        :meth:`delb.DocumentExtensionHooks._init_config` has been processed.

        You might want to specify a loader to be considered before or after another
        one. Let's assume a loader shall figure out what to load from a remote XML
        resource that contains a reference to the actual document.
        That one would have to be considered before the one that loads XML documents
        from a URL into a :class:`delb.Document`:

        .. testcode::

            from delb.plugins import plugin_manager
            from delb.plugins.contrib.https_loader import https_loader


            @plugin_manager.register_loader(before=https_loader)
            def mets_loader(source, config) -> LoaderResult:
                # loading logic here
                pass
        """

        if before is not None and after is not None:
            raise NotImplementedError(
                "Loaders may only define one constraint atm. Please open an issue with "
                "a use-case description if you need to define both."
            )

        registered_loaders = self.plugins.loaders

        if before is not None:
            if not isinstance(before, Iterable):
                before = (before,)
            index = min(registered_loaders.index(x) for x in before)

        elif after is not None:
            if not isinstance(after, Iterable):
                after = (after,)
            index = max(registered_loaders.index(x) for x in after) + 1

        else:
            index = len(registered_loaders)

        def registrar(loader: Loader) -> Loader:
            assert callable(loader)
            registered_loaders.insert(index, loader)
            return loader

        return registrar


plugin_manager = PluginManager()
