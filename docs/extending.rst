Extending delb
==============

``delb`` uses pluggy_ to facilitate the extendability of a few of its mechanics.
A package that extends its functionality must `provide entrypoint metadata`_
with the name ``delb`` and paths that point to modules that contain hook
implementations.

See this project's ``pyproject.toml`` for an example to define an entrypoint /
plugin for poetry_.
See also the :mod:`delb.plugins.contrib.https_loader` as example for a plugin
module.

Authors are encouraged to prefix their package names with ``delb-`` in order to
increase discoverability.

There is one hook to configure loaders and one to register extension classes
for the :class:`delb.Document` class with these specifications that a hook
implementation must comply with:

.. automodule:: delb.plugins.specs

Document extension classes can implement methods that are called from builtin
:class:`delb.Document` methods:

.. autoclass:: delb.DocumentExtensionHooks
   :private-members:


.. _pluggy: https://pluggy.readthedocs.io/
.. _poetry: https://poetry.eustace.io/
.. _provide entrypoint metadata: https://packaging.python.org/guides/creating-and-discovering-plugins/#using-package-metadata
