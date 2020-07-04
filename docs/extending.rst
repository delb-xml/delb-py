Extending delb
==============

.. include:: api-note.rst

``delb`` offers a plugin system to facilitate the extendability of a few of its
mechanics with Python packages.
A package that extends its functionality must `provide entrypoint metadata`_
for an entrypoint group named ``delb`` that points to modules that contain
extensions. The individual extensions have to be decorated with specific methods
of the plugin manager object (see the following sections).

There's a repository that outlines the mechanics as developer reference:
https://github.com/funkyfuture/delb-reference-plugins

Authors are encouraged to prefix their package names with ``delb-`` in order to
increase discoverability.

There are currently two distinct plugin types: *loaders* and *document extension
classes*. *Loaders* are functions that try to make sense of any given input
value, and if they can they return a parsed document. *Extension classes* add
functionality / attributes to the :class:`delb.Document` class as *mixin
classes* (instead of inheriting from it). That allows applications to rely
optionally on the availability of plugins. The designated means of communication
between these two extension types is the ``config`` argument to the loader
respectively the instance property of a document instance with that name.

.. warning::

    A module that contains plugins and any module it is explicitly or implicitly
    importing **must not** import anything from the :mod:`delb` module itself,
    because that would initiate the collection of plugin implementations. And
    these wouldn't have been completely registered at that point.

.. caution::

    Mind to re-install a package in development when its entrypoint
    specification changed.


Document loaders
----------------

Loaders are registered with this decorator:

.. autofunction:: _delb.plugins.plugin_manager.register_loader


Document extensions
-------------------

Document extension classes are registered with
:meth:`_delb.plugins.plugin_manager.register_document_extension`:

.. autofunction:: _delb.plugins.plugin_manager.register_document_extension

They can implement methods that are called from builtin :class:`delb.Document`
methods:

.. autoclass:: _delb.plugins.DocumentExtensionHooks
   :private-members:


.. _poetry: https://poetry.eustace.io/
.. _provide entrypoint metadata: https://packaging.python.org/guides/creating-and-discovering-plugins/#using-package-metadata
