API Documentation
=================

Documents
---------

.. autoclass:: delb.Document

   .. autoclasstoc::


.. _document-loaders:

Document loaders
----------------

If you want or need to manipulate the availability of or order in which loaders
are attempted, you can change the
:obj:`delb.plugins.plugin_manager.plugins.loaders` object which is a
:class:`list`. Its state is reflected in your whole application. Please refer to
`this issue`_ when you require finer controls over these aspects.

.. _this issue: https://github.com/funkyfuture/delb/issues/9

Core
~~~~

.. automodule:: delb.plugins.contrib.core_loaders

Extra
~~~~~

.. automodule:: delb.plugins.contrib.https_loader


Nodes
-----

Comment
~~~~~~~

.. autoclass:: delb.CommentNode

   .. autoclasstoc::

Processing instruction
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: delb.ProcessingInstructionNode

   .. autoclasstoc::

Tag
~~~

.. autoclass:: delb.TagNode

   .. autoclasstoc::

Text
~~~~

.. autoclass:: delb.TextNode

   .. autoclasstoc::

Node constructors
~~~~~~~~~~~~~~~~~

.. autofunction:: delb.new_comment_node

.. autofunction:: delb.new_processing_instruction_node

.. autofunction:: delb.new_tag_node


.. _contributed-filters:

Filters
-------

Default filters
~~~~~~~~~~~~~~~

.. autofunction:: delb.altered_default_filters


Contributed filters
~~~~~~~~~~~~~~~~~~~

.. autofunction:: delb.any_of

.. autofunction:: delb.is_comment_node

.. autofunction:: delb.is_processing_instruction_node

.. autofunction:: delb.is_tag_node

.. autofunction:: delb.is_text_node

.. autofunction:: delb.not_


Various helpers
---------------

.. autofunction:: delb.first

.. autofunction:: delb.get_traverser

.. autofunction:: delb.last

.. autofunction:: delb.register_namespace

.. autofunction:: delb.tag


Exceptions
----------

.. autoexception:: delb.exceptions.InvalidCodePath

.. autoexception:: delb.exceptions.InvalidOperation
