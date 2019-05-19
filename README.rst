delb
====

|latest-version| |rtd| |python-support| |license| |black|

``delb`` is a library that provides an ergonomic model for XML encoded text
documents (e.g. TEI-XML_) for the Python programming language.
It fills a gap for the humanities-related field of software development towards
the excellent (scientific) communities in the Python ecosystem.

For a more elaborated discussion see the *Design* chapter of the documentation.

.. _TEI-XML: https://tei-c.org


Features
--------

- Loads documents from various source types. This is customizable and
  extensible.
- A completely type-annotated API.
- Consistent design regarding names and callables' signatures.
- Shadows comments and processing instructions by default.
- Querying with XPath and CSS expressions.
- Applying XSL Transformations.


Development status
------------------

This project is currently developed as proof-of-concept. If you happen to
depend on it, please notify me to consider this in future.

You're invited to submit tests that reflect desired use cases or are merely of
theoretical nature. Of course, any kind of proposals for or implementations of
improvements are welcome as well.


Testimonials
------------

Kurt Raschke `noted in 2010 <https://web.archive.org/web/20190316214219/https://kurtraschke.com/2010/09/lxml-inserting-elements-in-text/>`_::

  In a DOM-based implementation, it would be relatively easy […]
  But lxml doesn't use text nodes; instead it uses and properties to hold text
  content.


ROADMAPish
----------

- refactor ``inxs`` to use this lib
- gain insights from usage experience
- implement the API in Rust
- provide bindings for Python and Javascript to the Rust implementation, while
  nurturing the lxml-based implementation as reference for some time
- be finished before the Digital Humanities community realizes how to foster a
  viable software ecosystem and fund such efforts


.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square
   :alt: Black code style
   :target: https://black.readthedocs.io/
.. |latest-version| image:: https://img.shields.io/pypi/v/delb.svg?style=flat-square
   :alt: Latest version on PyPI
   :target: https://pypi.org/project/delb
.. |license| image:: https://img.shields.io/pypi/l/delb.svg?style=flat-square
   :alt: License
   :target: https://github.com/funkyfuture/delb/blob/master/LICENSE.txt
.. |python-support| image:: https://img.shields.io/pypi/pyversions/delb.svg?style=flat-square
   :alt: Python versions
.. |rtd| image:: https://img.shields.io/badge/RTD-Docs-informational.svg?style=flat-square
   :alt: Documentation
   :target: https://delb.readthedocs.io/
