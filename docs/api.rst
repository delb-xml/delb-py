API Documentation
=================

The Document class
------------------

.. autoclass:: lxml_domesque.Document

Node classes
------------

.. autoclass:: lxml_domesque.TagNode

.. autoclass:: lxml_domesque.TextNode

Contributed document loaders
----------------------------

.. autofunction:: lxml_domesque.loaders.buffer_loader

.. autofunction:: lxml_domesque.loaders.etree_loader

.. autofunction:: lxml_domesque.loaders.ftp_http_loader

.. autofunction:: lxml_domesque.loaders.https_loader

.. autofunction:: lxml_domesque.loaders.path_loader

.. autofunction:: lxml_domesque.loaders.tag_node_loader

.. autofunction:: lxml_domesque.loaders.text_loader


Contributed filters
-------------------

.. autofunction:: lxml_domesque.any_of

.. autofunction:: lxml_domesque.is_tag_node

.. autofunction:: lxml_domesque.is_text_node

.. autofunction:: lxml_domesque.not_


Exceptions
----------

.. autoexception:: lxml_domesque.exceptions.InvalidCodePath

.. autoexception:: lxml_domesque.exceptions.InvalidOperation
