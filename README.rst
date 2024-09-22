delb
====

|latest-version| |rtd| |python-support| |license| |mypy| |black|

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
- XML DOM types are represented by distinct classes.
- A completely type-annotated API.
- Consistent design regarding names and callables' signatures.
- Shadows comments and processing instructions by default.
- Querying with XPath and CSS expressions.
- Serializations that may fulfil the promise of XML's well-readability to an
  unwitnessed degree and even don't mess up whitespace.


Development status
------------------

You're invited to submit tests that reflect desired use cases or are merely of
theoretical nature. Of course, any kind of proposals for or implementations of
improvements are welcome as well.


Related Projects & Testimonials
-------------------------------

snakesist_ is an eXist-db client that uses ``delb`` to expose database
resources.

Kurt Raschke `noted in 2010`_::

  In a DOM-based implementation, it would be relatively easy […]
  But lxml doesn't use text nodes; instead it uses [text] and [tail]
  properties to hold text content.


.. _snakesist: https://pypi.org/project/snakesist/
.. _noted in 2010: https://web.archive.org/web/20190316214219/https://kurtraschke.com/2010/09/lxml-inserting-elements-in-text/



.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square
   :alt: Black code style
   :target: https://black.readthedocs.io/
.. |latest-version| image:: https://img.shields.io/pypi/v/delb.svg?style=flat-square
   :alt: Latest version on PyPI
   :target: https://pypi.org/project/delb
.. |license| image:: https://img.shields.io/pypi/l/delb.svg?style=flat-square
   :alt: License
   :target: https://github.com/delb-xml/delb-py/blob/main/LICENSE.txt
.. |mypy| image:: https://img.shields.io/badge/mypy-checked-success.svg?style=flat-square
   :alt: mypy-checked
   :target: https://www.mypy-lang.org/
.. |python-support| image:: https://img.shields.io/pypi/pyversions/delb.svg?style=flat-square
   :alt: Python versions
.. |rtd| image:: https://img.shields.io/badge/RTD-Docs-informational.svg?style=flat-square
   :alt: Documentation
   :target: https://delb.readthedocs.io/
