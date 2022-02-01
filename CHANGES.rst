Changes
=======

    Every time I thought I'd got it made

    It seemed the taste was not so sweet


The listed updates resemble rather a Best Of than a full record of changes.
Intentionally.


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
- Adds :doc:`plugin mechanics <extending>`. Graciae ad infinitum, TC!
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

.. _fastcache: https://pypi.org/project/fastcache/

0.1.2 (2019-09-14)
------------------

There's nothing super-exciting to report here. It's just getting better.

0.1.1 (2019-08-15)
------------------

This was quiet boring, it serves updated dependencies for what it's worth.

0.1 (2019-05-26)
----------------

The initial release with a set and sound data model and API.
