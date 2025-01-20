:tocdepth: 2

Nodes & Filters
===============

Comment
-------

.. autoclass:: delb.CommentNode
   :autosummary:
   :autosummary-nosignatures:

Processing instruction
----------------------

.. autoclass:: delb.ProcessingInstructionNode
   :autosummary:
   :autosummary-nosignatures:

Tag
---

.. autoclass:: delb.TagNode
   :autosummary:
   :autosummary-nosignatures:

Tag attribute
-------------

.. autoclass:: delb.nodes.Attribute


Text
----

.. autoclass:: delb.TextNode
   :autosummary:
   :autosummary-nosignatures:

Node constructors
-----------------

.. autofunction:: delb.new_comment_node

.. autofunction:: delb.new_processing_instruction_node

.. autofunction:: delb.new_tag_node


Parsing
-------

.. autofunction:: delb.parse_tree

.. autofunction:: delb.parse_nodes


.. _contributed-filters:

Filters
-------

The following implementations are shipped with the library. Also see
:class:`delb.typing.Filter`

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
