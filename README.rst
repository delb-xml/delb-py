delb
====

|latest-version| |rtd| |python-support| |license| |mypy| |black|

``delb`` is a library that provides an ergonomic model to process XML encoded
text documents (e.g. TEI-XML_) for the Python programming language.
It fills a gap for the humanities-related field of software development towards
the excellent (academic & scientific) communities in the Python ecosystem.

For a more elaborated discussion on the project's motivation see the *Design*
chapter of the documentation.

.. _TEI-XML: https://tei-c.org


Features & paradigms
--------------------

- XML DOM types are represented by distinct classes.
- A completely type-annotated API with consistent naming and callables'
  signatures.
- Loads documents from various source types.
- Easy, simply filterable traversing of a document in all directions staring
  from any node.
- Shadows comments and processing instructions by default.
- Querying with XPath and CSS expressions.
- Serializations that may fulfil the promise of XML's well-readability to an
  unwitnessed degree and even don't mess up whitespace.
- Optional whitespace handling per `TEI recommendation`_.
- Various customization opportunities (document loaders & representations, XML
  parser, XPath functions).
- It's well tested.

.. _TEI recommendation: https://wiki.tei-c.org/index.php/XML_Whitespace


Development status
------------------

While the software is still to be considered in beta phase, the interfaces are
mostly stable and the implementation is thoroughly tested.  Future changes shall
be introduced in a non-breaking fashion that allows gradual updates.  New
features will be marked as experimental until they've proven to be stable.
You're invited to submit tests that reflect desired use cases or are merely of
theoretical nature.  Of course, any kind of proposals for or implementations of
improvements are welcome as well.


Related Projects
----------------

- snakesist_ is an eXist-db client that uses ``delb`` to expose database
  resources.
- There's a repository with `integration tests`_ to test *delb* usage against a
  large, diverse set of TEI corpora.

.. _integration tests: https://github.com/delb-xml/delb-py-integration-tests
.. _snakesist: https://pypi.org/project/snakesist/


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
