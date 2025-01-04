:tocdepth: 3

Documents and Loaders
=====================

Documents
---------

.. autoclass:: delb.Document
   :autosummary:
   :autosummary-nosignatures:

.. _document-loaders:


Document loaders
----------------

If you want or need to manipulate the availability of or order in which loaders
are attempted, you can change the
:obj:`delb.plugins.plugin_manager.plugins.loaders` object which is a
:class:`list`. Its state is reflected in your whole application. Please refer to
`this issue`_ when you require finer controls over these aspects.

.. _this issue: https://github.com/delb-xml/delb-py/issues/9

Core
~~~~

.. automodule:: _delb.plugins.core_loaders

Extra
~~~~~

.. automodule:: _delb.plugins.web_loader


Parser options
--------------

.. autoclass:: delb.ParserOptions
   :no-inherited-members:
