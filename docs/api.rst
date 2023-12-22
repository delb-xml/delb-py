API Documentation
=================

.. include:: api-note.rst


Documents
---------

.. autoclass:: delb.Document


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

.. automodule:: _delb.plugins.https_loader


Parser options
--------------

.. autoclass:: delb.ParserOptions


Nodes
-----

Comment
~~~~~~~

.. autoclass:: delb.CommentNode


Processing instruction
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: delb.ProcessingInstructionNode

Tag
~~~

.. autoclass:: delb.TagNode

Tag attribute
~~~~~~~~~~~~~

.. autoclass:: delb.nodes.Attribute
   :exclude-members: data


Text
~~~~

.. autoclass:: delb.TextNode
   :exclude-members: data, maketrans

Node constructors
~~~~~~~~~~~~~~~~~

.. autofunction:: delb.new_comment_node

.. autofunction:: delb.new_processing_instruction_node

.. autofunction:: delb.new_tag_node

Queries with XPath & CSS
------------------------

.. automodule:: _delb.xpath


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


Transformations
---------------

.. automodule:: delb.transform


String serialization
--------------------

.. autoclass:: delb.DefaultStringOptions


Various helpers
---------------

.. autofunction:: delb.compare_trees

.. autofunction:: delb.first

.. autofunction:: delb.get_traverser

.. autofunction:: delb.last

.. autofunction:: delb.tag


Exceptions
----------

.. automodule:: delb.exceptions
