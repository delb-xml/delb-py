:tocdepth: 2

Type aliases & semi-public classes
==================================

There are internally used classes and type aliases that can be of interest for
re-use in applications and extensions.

Filter functions are defined as:

.. autoclass:: delb.typing.Filter

Loaders are defined as:

.. autoclass:: delb.typing.Loader

The order of loaders is defined with help of (read:
``Loader | Iterable[Loader] | None``):

.. autoclass:: delb.typing.LoaderConstraint

Loaders may return a string that explains why it wouldn't successfully process
the given input to the user:

.. autoclass:: delb.typing.LoaderResult

Namespace to prefix mappings are formalized as:

.. autoclass:: delb.typing.NamespaceDeclarations

All node classes inherit from a common class:

.. class:: delb.NodeBase

Methods that add nodes to a tree take a variety of input data:

.. autoclass:: delb.typing.NodeSource

Definitions that are used for convenient tree building are held in:

.. autoclass:: _delb.nodes._TagDefinition
   :no-inherited-members:
