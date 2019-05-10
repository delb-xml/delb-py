delb
====

Features
--------

- Designed to manipulate XML encoded text markup with ease.
- Loads documents from various sources.
- A completely type-annotated API.
- Shadows comments and processing instructions by default.
- …


Documentation
-------------

- API_
- Installation_
- Design_

.. _API: https://delb.readthedocs.io/en/latest/api.html
.. _Design: https://delb.readthedocs.io/en/latest/design.html
.. _Installation: https://delb.readthedocs.io/en/latest/installation.html


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
