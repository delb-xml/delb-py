Glossary
========

.. glossary::

    filter
      Filter functions can be used as arguments with various methods on node
      instances that return other nodes. They are called with a node instance
      as only argument and they should return a :class:`bool` to indicate
      whether the node matches the filter. Have a look at the
      :ref:`contributed-filters` source code for examples.

    tag node
      Tag nodes are the equivalent to the DOM's `element node`_. Its name
      shall make it distinguishable from the ElementTree API and relates
      to the nodes' functionality of tagging text.


.. _element node: https://www.w3.org/TR/1998/REC-DOM-Level-1-19981001/level-one-core.html#ID-745549614
