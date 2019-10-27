API Documentation
=================

Documents
---------

.. autoclass:: delb.Document


.. _document-loaders:

Document loaders
----------------

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

Processing instruction
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: delb.ProcessingInstructionNode

Tag
~~~

.. autoclass:: delb.TagNode

Text
~~~~

.. autoclass:: delb.TextNode

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

.. autofunction:: delb.register_namespace

.. autofunction:: delb.tag


Exceptions
----------

.. autoexception:: delb.exceptions.InvalidCodePath

.. autoexception:: delb.exceptions.InvalidOperation
