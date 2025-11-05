:tocdepth: 2

Changes
=======

    Every time I thought I'd got it made

    It seemed the taste was not so sweet


The listed updates resemble rather a Best Of than a full record of changes.
Intentionally.

.. NEVER USE NESTED LISTS IN THIS DOCUMENT!!

0.6-rc0 (2026-11-05)
--------------------

This release brings significant changes that evolve *delb* to a mature level,
namely:

- 🎇 All data keeping is now implemented natively without *lxml*, leading to
  remarkable performance improvements.
- 🎉 There's a new parser interface for extensiblity.
- 🪩 The API can be considered stable.

At least 99.5% of all code is guaranteed to be covered by tests.
The accompanying integration test corpora have been updated and extended.

News
~~~~

- ⚠️ For more clarity the symbols that are re-exported in the top-level module
  ``delb`` are greatly reduced. Instead they're to be imported from their
  domain specific modules :mod:`delb.filters`, :mod:`delb.names`,
  :mod:`delb.nodes` and :mod:`delb.utils` Some generally applicable ones will
  stay available for convenice though.
- There are new abstract base classes for each node type rooting from
  :class:`delb.typing.XMLNodeType` that should be used for type annotations.
- ⚠️ Functions to construct new node instances such as
  :func:`delb.nodes.new_tag_node` are deprecated. The corresponding, concrete
  node classes are now to be instantiated directly.
- A new parser interface allows the use of arbitrary parsing backends. Support
  for the standard library's ``expat`` interface and ``lxml`` are contributed.
  For details see :doc:`installation` and :class:`delb.parser.ParserOptions`.
- When a used parser backend supports DTDs, it can be instructed with the
  :attr:`delb.parser.ParserOptions.load_referenced_resources` option to consider
  these.
- New parsing related exceptions have been added:
  :exc:`delb.exceptions.ParsingError` bases
  :exc:`delb.exceptions.ParsingProcessingError` and
  :exc:`delb.exceptions.ParsingValidityError`.
- ⚠️ The :attr:`delb.parser.ParserOptions.resolve_entities` option has been
  removed entirely as delb's data model doesn't include any entities.
- The W3C's parser conformance test suite is included in delb's.
- ⚠️ :func:`delb.parse_tree` replaces :meth:`delb.TagNode.parse` to produce tag
  nodes from a serialized tree. The new :func:`delb.parse_nodes` produces an
  iterator over (sub-)trees (possibly an XML document fragment).
- ⚠️ The installation extra ``https-loader`` is renamed to ``web-loader``
- ⚠️ The ``parser_options`` must now be passed as keyword argument to a
  :class:`delb.Document`.
- A ``source_url`` can now be passed explicitly when instantiating a
  :class:`delb.Document`.
- ⚠️ The :attr:`delb.nodes.TagNode.prefix` attribute is gone.
- ⚠️ Support for Python 3.9 was removed and for Python 3.14 it's added.


0.5.1 (2025-01-08)
------------------

News
~~~~

Further deprecations that emit messages with hints to alternatives if available:

- :meth:`NodeBase.new_tag_node`
- Empty / null namespaces will generally be represented as empty strings in
  the future.
- :attr:`TagNode.parse`


0.5 (2025-01-01)
----------------

This iteration took quiet long to complete as it presumably solved the hardest
problem on the way to shed off the essential dependency on ``lxml``, also
resulting in human-friendly serializations that achieve unprecedented clarity.
The library's robustness is now proven with integration tests that are verified
against eleven diverse TEI encoded corpora that sum up to more than 360k
documents with a total volume of 3.33 GB.

News
~~~~

- *delb* is now autonomously serializing contents, the :doc:`api/serialization`
  chapter details current capabilities and interfaces.
- The `HTML documentation`_ received a big revision for pleasant discovery and
  reading.
- Methods that add nodes to a tree now return the added concrete nodes.
- The new :func:`delb.compare_trees` is available to compare nested
  contents.
- ⚠️ To align with Python standard behaviour, accessing a non-existing attribute
  with subscript notation now raises a :exc:`KeyError`.
- ⚠️ The use of namespace declarations (to prefixes) that were used in a parsed
  source stream is deprecated. Notably queries will not use them as fallback
  when invoked without the ``namespaces`` argument. Instead they *will* likely
  use the called-on node's namespace as default namespace.
- ⚠️ :attr:`delb.ParserOptions.collapse_whitespace` was renamed to
  :attr:`delb.ParserOptions.reduce_whitespace`, as there is now
  :meth:`delb.Document.reduce_whitespace` to reflect that they also trim
  excessive whitespace.
- ⚠️ The Xpath evaluation expressions of absolute paths on the child axis in the
  first location step is fixed. Consider to double check your usages.
- Comparing :class:`TagNode` instances is now de facto an identity check. The
  previous behaviour can be achieved by comparing :attr:`TagNode.universal_name`
  and :attr:`TagNode.attributes`.
- ⚠️ :attr:`delb.Document.head_nodes` was renamed to
  :attr:`delb.Document.prologue`, :attr:`delb.Document.tail_nodes` to
  :attr:`delb.Document.epilogue`.
- ⚠️ :func:`delb.get_traverser` now only accepts keyword arguments.
- ⚠️ Support for Python 3.7 was removed.
- Support for Python 3.12 and 3.13 was added.
- ⚠️ The :func:`_delb.plugins.core_loaders.etree_loader` is marked as
  deprecated.

Previously deprecated contents have been removed.

.. _HTML documentation: https://delb.readthedocs.io/


0.4 (2022-11-02)
----------------

News
~~~~

- *delb* now uses its own XPath implementation, please investigate
  :mod:`_delb.xpath` for details.
- ⚠️ Many of the nodes' methods that relate to relative nodes have been renamed.
  Watch out for :class:`DeprecationWarning`\s!
- ⚠️ The method :meth:`delb.NodeBase.iterate_descendants` is added as a
  replacement for the former :meth:`delb.NodeBase.child_nodes` invoked with the
  now deprecated argument ``recurse``.
- ⚠️ The ``https-loader`` extension is now required for loading documents via
  plain and secured HTTP connections.
- Under the hood httpx_ is now employed as HTTP/S client.
- ⚠️ The contributed loader for FTP connections is marked as deprecated.
- ⚠️ The ``parser`` argument to :class:`delb.Document` and
  :meth:`delb.TagNode.parse` is deprecated and replaced by ``parser_options``.
- ⚠️ :meth:`delb.Document.xslt` is marked as deprecated.
- ⚠️ Evoked exceptions changed in various places.
- ⚠️ Document mixin extensions are now facilitated by subclassing
  :class:`_delb.plugins.DocumentMixinBase`. It replaces
  :class:`_delb.plugins.DocumentExtensionHooks` and
  :meth:`_delb.plugins.PluginManager.register_document_mixin` without a
  backward-compatible mechanic.
- Support for the very good Python 3.10 and the even better 3.11 is added.
- The code repository is now part of an umbrella namespace for related projects:
  https://github.com/delb-xml/
- A ``CITATION.cff`` is available in the repository and shipped with source
  distributions for researchers that are citing_ their employed software.

.. _citing: https://citation-file-format.github.io/
.. _httpx: https://www.python-httpx.org/


0.3 (2022-01-31)
----------------

News
~~~~

- Adds the :meth:`delb.TagNode.fetch_or_create_by_xpath` method.
    - ⚠️Because of that a pre-mature parser of XPath expressions has been
      implemented and you can expect some expressions to cause failures, e.g.
      with functions that take more than one argument.
- Subclasses of :class:`delb.Document` can claim to be the default class based
  on the evaluation of a document's content and configuration by implementing
  ``__class_test__``.
- ⚠️ :meth:`_delb.plugins.PluginManager._register_document_extension` is renamed
  to :meth:`_delb.plugins.PluginManager._register_document_mixin`.
- ⚠️ :meth:`_delb.plugins.DocumentExtensionHooks` is renamed to
  :meth:`_delb.plugins.DocumentMixinHooks`.
- ⚠️ :meth:`_delb.plugins.DocumentMixinHooks._init_config` is now a
  :func:`classmethod` and now also takes the config namespace as first argument.
- Adds :meth:`delb.Document.collapse_whitespace` and the initialization option
  for :class:`delb.Document` instances with the same name.
- Adds the ``retain_child_nodes`` argument to :meth:`delb.NodeBase.detach`.
- Adds the :attr:`delb.NodeBase.last_descendant` property.
- Adds the :attr:`delb.TagNode.id` property.
- Adds the :meth:`delb.TagNode.parse` method.
- ⚠️ :meth:`TagNode.qualified_name` is marked deprecated and the same property
  is now available as :meth:`TagNode.universal_name`.
- Adds support for Python 3.9 & 3.10.
- ⚠️ Drops support for Python 3.6
- Uses GitHub actions for CI checks.

Fixes
~~~~~

- Detached :class:`delb.TagNode` s now drop references to :class:`delb.TextNode`
  siblings.
- Ensures that :attr:`delb.TagNode.location_path` always consists of indexed
  steps (``/*[i]``) only.
- Avoids hitting the interpreter's recursion limit when iterating in stream
  dimension.


0.2 (2020-07-26)
----------------

News
~~~~

- Adds a logo. Gracious thanks to sm!
- Adds :doc:`plugin mechanics </api/extending>`. Graciae ad infinitum, TC!
- CSS and XPath query results are wrapped in :class:`delb.QueryResults`.
- Adds :attr:`delb.Document.head_nodes` and :attr:`delb.Document.tail_nodes`
  that allow access to the siblings of a root node.
- Adds the :attr:`delb.Document.source_url` property.
- Adds :func:`delb.get_traverser` and two traverser implementations that yield
  nodes related to a root node according to their defined order.
- Document loaders report back the reason why they would or could not load a
  document from the given object.
- Various documentation improvements, including table of contents for class
  members.


0.1.2 (2019-09-14)
------------------

There's nothing super-exciting to report here. It's just getting better.


0.1.1 (2019-08-15)
------------------

This was quiet boring, it serves updated dependencies for what it's worth.


0.1 (2019-05-26)
----------------

The initial release with a set and sound data model and API.
