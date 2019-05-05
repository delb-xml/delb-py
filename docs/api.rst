API Documentation
=================

Documents
---------

.. autoclass:: lxml_domesque.Document


.. _document-loaders:

Document loaders
----------------

.. automodule:: lxml_domesque.loaders


Nodes
-----

Comment
~~~~~~~

.. autoclass:: lxml_domesque.CommentNode

Processing instruction
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: lxml_domesque.ProcessingInstructionNode

Tag
~~~

.. autoclass:: lxml_domesque.TagNode

Text
~~~~

.. autoclass:: lxml_domesque.TextNode

Node constructors
~~~~~~~~~~~~~~~~~

.. autofunction:: lxml_domesque.new_comment_node

.. autofunction:: lxml_domesque.new_processing_instruction_node

.. autofunction:: lxml_domesque.new_tag_node


.. _contributed-filters:

Filters
-------

Default filters
~~~~~~~~~~~~~~~

.. autofunction:: lxml_domesque.altered_default_filters


Contributed filters
~~~~~~~~~~~~~~~~~~~

.. autofunction:: lxml_domesque.any_of

.. autofunction:: lxml_domesque.is_comment_node

.. autofunction:: lxml_domesque.is_processing_instruction_node

.. autofunction:: lxml_domesque.is_tag_node

.. autofunction:: lxml_domesque.is_text_node

.. autofunction:: lxml_domesque.not_


Exceptions
----------

.. autoexception:: lxml_domesque.exceptions.InvalidCodePath

.. autoexception:: lxml_domesque.exceptions.InvalidOperation
