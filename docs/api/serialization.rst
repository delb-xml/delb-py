Serialization
=============

Overview
--------

*delb* allows users to produce well-readable, content-agnostic XML
serializations as well-readable as they can get.

The formatting options are controlled with the :class:`delb.PrettyFormatOptions`
that are either passed to serialization methods like :meth:`delb.Document.save`
and :meth:`delb.TagNode.serialize` or setting the class property
:obj:`delb.DefaultStringOptions.pretty_format_options` for any conversions of
documents and nodes to strings (e.g. with :func:`print` or :class:`str`) on the
general application level. Passing / Setting :obj:`None` lets the serializer
simply dump a tree's contents to an XML stream without any extra efforts.

The default "pretty formatting" is best suited to align structured data, it
adds newline and optional indentation to mark content nesting without adding or
removing (text encoding related) significant whitespace.

The provided text wrapping implementation also always assumes that a document
contains mixed content (i.e. both structured and text data) while it prefers a
continuous presentation of (possibly encoded) text over single tag elements per
line(s). It's currently quiet expensive to compute. It also doesn't account for
combining Unicode encodings so that wrapped text lengths are determined by the
number of Unicode codepoints, not the actually represented glyphs.

Serializations that alter whitespace for indentation or wrapping also apply a
general reduction of insignificant whitespace as recommended in this
`TEI recommendation`_. Furthermore it is guaranteed that a serialized stream
from a document that was normalized according to this set of rules [1]_
will be parsed back to the identical tree if these rules are applied again [2]_.

There is currently no plan to support the production of character or entity
references_, yet which extent that would cover.

As its stands custom serialization algorithms should be implemented as
standalone units, neither are the contributed implementations suited for
derivations nor is the architecture ready for extensions in that regard yet.


Example and comparison to other means of production
---------------------------------------------------

As an example this input is given:

.. dropdown:: Source stream

    .. literalinclude:: serialization-example-input.xml
       :language: xml
       :linenos:

Note that there's no indication of the document's type or schema.

delb
~~~~

Just indentation, no content wrapping and aligned attributes
............................................................

.. dropdown:: Production

    .. code-block::

        document.save(
          path,
          pretty_format_options = PrettyFormatOptions(
            align_attributes=True,
            indentation="  ",
            text_width=0
          )
        )

.. dropdown:: Product

    .. literalinclude:: serialization-example-delb-indented.xml
       :language: xml
       :linenos:

- l.2) namespace declarations are consolidated at the root node
- l.2) attribute values are contained by double quotes for better readability
- l.4) Unicode characters are produced where the input used an entity reference
- l.24-25) this is the ``align_attributes`` option in action


With text wrapping
..................

.. dropdown:: Production

    .. code-block::

        document.save(
          path,
          pretty_format_options = PrettyFormatOptions(
            align_attributes=False,
            indentation="  ",
            text_width=59
          )
        )

.. dropdown:: Product

    .. literalinclude:: serialization-example-delb-wrapped.xml
       :language: xml
       :linenos:

- l.8) lacking semantic knowledge, also structured data is placed onto one line
  when it fits
- l.26) nested content is kept on one line if it fits


lxml
~~~~

.. dropdown:: Production

    .. code-block::

        etree.indent(tree)
        with (p / "serialization-example-lxml.xml").open("bw") as f:
            tree.write(f, pretty_print=True)

.. dropdown:: Product

    .. literalinclude:: serialization-example-lxml.xml
       :language: xml
       :linenos:

- l.2-4) still defines an unused named entity
- l.6) a character reference is produced where Unicode could have been used
- l.20-33) there's no wrapping option
- l.21-33) broken indentation
- l.28) opening tag is kept on the started line though a newline would be a
  proper substitute for the preceding space in encoded text
- l.28-31) related content is spread over lines


Configuration interfaces
------------------------

.. autoclass:: delb.DefaultStringOptions

.. autoclass:: delb.PrettyFormatOptions
   :no-inherited-members:


.. [1] For example with :meth:`Document.reduce_whitespace`.
.. [2] With enabled :attr:`ParserOptions.reduce_whitespace`.


.. _references: https://www.w3.org/TR/REC-xml/#sec-references
.. _TEI recommendation: https://wiki.tei-c.org/index.php/XML_Whitespace
