API Documentation
=================

Documents
---------

.. autoclass:: lxml_domesque.Document


.. _contributed-loaders:

Contributed document loaders
----------------------------

.. autofunction:: lxml_domesque.loaders.buffer_loader

.. autofunction:: lxml_domesque.loaders.etree_loader

.. autofunction:: lxml_domesque.loaders.ftp_http_loader

.. autofunction:: lxml_domesque.loaders.https_loader

.. autofunction:: lxml_domesque.loaders.path_loader

.. autofunction:: lxml_domesque.loaders.tag_node_loader

.. autofunction:: lxml_domesque.loaders.text_loader


Nodes
-----

.. autoclass:: lxml_domesque.TagNode

.. autoclass:: lxml_domesque.TextNode

.. autofunction:: lxml_domesque.new_tag_node


.. _contributed-filters:

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
