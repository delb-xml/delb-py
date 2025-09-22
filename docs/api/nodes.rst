:tocdepth: 2

Nodes & Filters
===============

Comment
-------

.. autoclass:: delb.nodes.CommentNode
   :autosummary:
   :autosummary-nosignatures:

Processing instruction
----------------------

.. autoclass:: delb.nodes.ProcessingInstructionNode
   :autosummary:
   :autosummary-nosignatures:

Tag
---

.. autoclass:: delb.nodes.TagNode
   :autosummary:
   :autosummary-nosignatures:

Tag attribute
-------------

.. autoclass:: delb.nodes.Attribute


Text
----

.. autoclass:: delb.nodes.TextNode
   :autosummary:
   :autosummary-nosignatures:


Parsing
-------

.. autofunction:: delb.parse_tree

.. autofunction:: delb.parse_nodes


.. _contributed-filters:

Filters
-------

The following implementations are shipped with the library. Also see
:class:`delb.typing.Filter`.

Default filters
~~~~~~~~~~~~~~~

.. autofunction:: delb.filters.altered_default_filters

Contributed filters
~~~~~~~~~~~~~~~~~~~

.. autofunction:: delb.filters.any_of

.. autofunction:: delb.filters.is_comment_node

.. autofunction:: delb.filters.is_processing_instruction_node

.. autofunction:: delb.filters.is_tag_node

.. autofunction:: delb.filters.is_text_node

.. autofunction:: delb.filters.not_
