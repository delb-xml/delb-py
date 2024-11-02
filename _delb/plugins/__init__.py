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

from __future__ import annotations

import sys
from collections.abc import Iterable
from typing import TYPE_CHECKING, overload, Any

if sys.version_info < (3, 10):  # DROPWITH Python3.9
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


if TYPE_CHECKING:
    from types import SimpleNamespace
    from delb import Document
    from _delb.typing import (
        GenericDecorated,
        Loader,
        LoaderConstraint,
        SecondOrderDecorator,
        XPathFunction,
    )


class DocumentMixinBase:
    """
    By deriving a subclass from this one, a document extension class is registered as
    plugin. These are supposed to add additional attributes to a document, e.g. derived
    data or methods to interact with storage systems. All attributes of an extension
    should share a common prefix that terminates with an underscore, e.g.
    `storage_load`, `storage_save`, etc.

    This base class also acts as termination for methods that can be implemented by
    mixin classes. Any implementation of a method must call a base class' one, e.g.:

    .. code-block::

        from types import SimpleNamespace

        from _delb.plugins import DocumentMixinBase
        from magic_wonderland import play_disco


        class MyExtension(DocumentMixinBase):

            # this method can be implemented by any extension class
            @classmethod
            def _init_config(cls, config, kwargs):
                config.my_extension = SimpleNamespace(tonality=kwargs.pop(
                    "my_extension_tonality")
                )
                super()._init_config(config, kwargs)

            # this method is specific to this extension
            def my_extension_makes_magic(self):
                play_disco(self.config.my_extension.tonality)
    """

    def __init_subclass__(cls):
        # ensure it is a direct subclass
        if cls.__mro__[1] is DocumentMixinBase:
            plugin_manager.document_mixins.append(cls)

    @classmethod
    def _init_config(cls, config: SimpleNamespace, kwargs: dict[str, Any]):
        """
        The ``kwargs`` argument contains the additional keyword arguments that a
        :class:`Document` instance is called with. Extension classes that expect
        configuration data *must* process their specific arguments by clearing them
        from the ``kwargs`` dictionary, e.g. with :meth:`dict.pop`, and preferably
        storing the final configuration data in a :class:`types.SimpleNamespace` and
        adding it to the :class:`types.SimpleNamespace` passed as ``config`` with the
        extension's name. The initially mentioned keyword arguments *should* be prefixed
        with that name as well. This method is called before the loaders try to read and
        parse the given source for a document.
        """
        if kwargs:
            raise RuntimeError(
                "Not all configuration arguments have been processed. You either "
                "passed invalid arguments or an extension doesn't handle them "
                f"properly: {config}"
            )


class PluginManager:
    def __init__(self):
        self.document_mixins: list[type[DocumentMixinBase]] = []
        self.document_subclasses: list[type[Document]] = []
        self.loaders: list[Loader] = []
        self.xpath_functions: dict[str, XPathFunction] = {}

    @staticmethod
    def load_plugins():
        """
        Loads all modules that are registered as entrypoint in the ``delb`` group.
        """
        for entrypoint in entry_points().select(group="delb"):
            entrypoint.load()

    def register_loader(
        self, before: LoaderConstraint = None, after: LoaderConstraint = None
    ) -> SecondOrderDecorator:
        """
        Registers a document loader.

        An example module that is specified as ``delb`` plugin for an IPFS loader might
        look like this:

        .. testcode::

            from os import getenv
            from types import SimpleNamespace
            from typing import Any

            from _delb.plugins import plugin_manager
            from _delb.plugins.https_loader import https_loader
            from _delb.typing import LoaderResult


            IPFS_GATEWAY = getenv("IPFS_GATEWAY_PREFIX", "https://ipfs.io/ipfs/")


            @plugin_manager.register_loader()
            def ipfs_loader(source: Any, config: SimpleNamespace) -> LoaderResult:
                if isinstance(source, str) and source.startswith("ipfs://"):

                    config.source_url = source
                    config.ipfs_gateway_source_url = IPFS_GATEWAY + source[7:]

                    return https_loader(config.ipfs_gateway_source_url, config)

                # return an indication why this loader didn't attempt to load in order
                # to support debugging
                return "The input value is not an URL with the ipfs scheme."


        The ``source`` argument is what a :class:`Document` instance is initialized with
        as input data.

        Note that the ``config`` argument that is passed to a loader function contains
        configuration data, it's the :attr:`delb.Document.config` property after
        :meth:`_init_config <_delb.plugins.DocumentMixinHooks._init_config>` has
        been processed.

        Loaders that retrieve a document from an URL should add the origin as string to
        the ``config`` object as ``source_url``.

        You might want to specify a loader to be considered before or after another
        one. Let's assume a loader shall figure out what to load from a remote XML
        resource that contains a reference to the actual document.
        That one would have to be considered before the one that loads XML documents
        from a URL with the `https` scheme:

        .. testcode::

            from _delb.plugins import plugin_manager
            from _delb.plugins.https_loader import https_loader


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

        registered_loaders = self.loaders

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

    @overload
    def register_xpath_function(self, arg: str) -> SecondOrderDecorator: ...

    @overload
    def register_xpath_function(self, arg: GenericDecorated) -> GenericDecorated: ...

    def register_xpath_function(
        self, arg: str | GenericDecorated
    ) -> SecondOrderDecorator | GenericDecorated:
        """
        Custom XPath functions can be defined as shown in the following example. The
        first argument to a function is always an instance of
        :class:`_delb.xpath.EvaluationContext` followed by the expression's arguments.

        .. testcode::

            from delb import Document
            from _delb.plugins import plugin_manager
            from _delb.xpath import EvaluationContext


            @plugin_manager.register_xpath_function("is-last")
            def is_last(context: EvaluationContext) -> bool:
                return context.position == context.size

            @plugin_manager.register_xpath_function
            def lowercase(_, string: str) -> str:
                return string.lower()


            document = Document("<root><node/><node foo='BAR'/></root>")
            print(document.xpath("//*[is-last() and lowercase(@foo)='bar']").first)

        .. testoutput::

            <node foo="BAR"/>
        """
        if isinstance(arg, str):

            def wrapper(func: XPathFunction) -> XPathFunction:
                self.xpath_functions[arg] = func
                return func

            return wrapper

        if callable(arg):
            self.xpath_functions[arg.__name__] = arg
            return arg


plugin_manager = PluginManager()


__all__ = (DocumentMixinBase.__name__, "plugin_manager")
