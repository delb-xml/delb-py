:tocdepth: 2

Typing & semi-public classes
============================

The :mod:`delb.typing` module contains abstract classes that define the
interfaces for XML node types, internally used classes and type aliases that
can be of interest for re-use in applications and extensions.


Node types
----------

These classes should be used in type annotations and can be used for type tests
with :func:`isinstance`.

.. py:class:: delb.typing.XMLNodeType
   :abstract:

   Defines the interfaces that all node type representations share. All node
   type implementations are a subclass of this one.

.. py:class:: delb.typing.ParentNodeType
   :abstract:

   Defines the interfaces for nodes that can contain further nodes.

.. py:class:: delb.typing.CommentNodeType
   :abstract:

   Defines the interfaces for :class:`delb.nodes.CommentNode`.

.. py:class:: delb.typing.ProcessingInstructionNodeType
   :abstract:

   Defines the interfaces for :class:`delb.nodes.ProcessingInstructionNode`.

.. py:class:: delb.typing.TagNodeType
   :abstract:

   Defines the interfaces for :class:`delb.nodes.TagNode`.

.. py:class:: delb.typing.TextNodeType
   :abstract:

   Defines the interfaces for :class:`delb.nodes.TextNode`.


Type aliases
------------

Internally attributes data is handled strictly as:

.. autoclass:: delb.typing._AttributesData

The dictionary's key type is actually defined as
:class:`delb.typing.QualifiedName`.

Filter functions are defined as:

.. autoclass:: delb.typing.Filter

Parseable input streams are:

.. autoclass:: delb.typing.InputStream

Loaders are defined as:

.. autoclass:: delb.typing.Loader

The order of loaders is defined with help of:

.. autoclass:: delb.typing.LoaderConstraint

Loaders may return a string that explains why it wouldn't successfully process
the given input to the user:

.. autoclass:: delb.typing.LoaderResult


Protocols
---------

XML parser adapters must be able to process that they fetch from a binary
stream reader's ``read`` method:

.. autoclass:: delb.typing.BinaryReader
   :undoc-members:


Semi-public classes
-------------------

Namespace to prefix mappings are formalized as:

.. autoclass:: delb.typing.NamespaceDeclarations

Methods that add nodes to a tree take a variety of input data:

.. autoclass:: delb.typing.NodeSource

XML names are simply kept as tuple of namespace and local name:

.. autoclass:: delb.typing.QualifiedName

Definitions that are used for convenient tree building are held in:

.. autoclass:: _delb.nodes._TagDefinition
   :no-inherited-members:
