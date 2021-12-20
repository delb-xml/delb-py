About the design
================

tl;dr
-----

lxml resp. libxml2 are powerful tools, but have an unergonomic data model to
work with encoded text. Let's build a DOM API inspired wrapper around it.


Aspects & Caveats
-----------------

The library is partly opinionated to encourage good practices and to be more
pythonic_. Therefore its behaviour deviates from lxml and ignores stuff:

- Serializations of documents are UTF-8 encoded by default and always start
  with an XML declaration.
- Comment and processing instruction nodes are shadowed by default, see
  :func:`delb.altered_default_filters` on how to make them accessible.
- CDATA nodes are not accessible at all, but are retained and appear in
  serializations; unless you **[DANGER ZONE]** manipulate the tree. Depending on
  your actions you might encounter no alterations or a complete loss of these
  nodes within the root node. **[/DANGER ZONE]**

If you need to apply bad practices anyway, you can fall back to tinker with the
lxml objects that are bound to :attr:`TagNode._etree_obj`.


.. _pythonic: https://zen-of-python.info/there-should-be-one-and-preferably-only-one-obvious-way-to-do-it.html#13


Reasoning
---------

XML can be used to encode text documents, examples for such uses would be the
`Open Document Format`_ and XML-TEI_. It's more prevalent use however is to
encode data that is to be consumed by algorithms as configuration, measurements,
application events, various metadata and so on.

Python is a high-level, general programming language with a vast ecosystem,
notably including diverse scientific communities and tools. As such it is well
suited to solve and cause problems in the humanities related field of Research
Software Engineering by programmers with diverse educational background and
expertise.

The commonly used Python library to parse and interact with a representation
of an XML document is lxml_. Other libraries like the
:mod:`xml.etree.ElementTree` module from the Python standard library shall not
be discussed due to their insignificance and shortcomings. It is notable that at
least these two share significant design aspects of Java APIs which is perceived
as weird and clumsy in Python code.
lxml is a wrapper around libxml2_ which was developed by the GNOME_ developers
for other data than text documents. Data that is strictly structured and
expectable. Text documents are different in these regards as natural languages
and variety of media allow and lead to unprecedented manifestations for which an
encoding mixes different abstracted encapsulations of text fragments. And they
are formulated and structured for human consumers, and often printing devices.

So, what's wrong with lxml? Not much, it's a rock-solid, fast API for XML
documents with known issues and known workarounds that represents the full glory
of what a full-fledged family of specification implies - of which a lot is not
of concern for the problems at hand and occasionally make solutions complicated.
The one aspect that's very wrong in the context of text processing is
unfortunately its central model of elements and data/text that is attached to it
in two different relations. In particular the notion of an element *tail* makes
the whole enchilada tricky to traverse / navigate. The existence of this
attribute is due to the insignificance of these fragments of an XML stream in
the aforementioned, common uses of XML.

Now it is time for an example, given this document snippet:

.. code-block:: xml

  <p rendition="#justify">
    <lb/>Nomadisme épique exploratori-
    <lb/><space dim="horizontal" quantity="2" units="chars"/>sme urbain <hi rendition="#b">Art des voya-
    <lb/><space dim="horizontal" quantity="2" units="chars"/>ges</hi> et des promenades
  </p>

Here's a graphical representation of the markup with etree's elements and their
text and tail attributes:

.. image:: images/etree-model-example.png

When thinking about a paragraph of text, a way to conceptualize it is as a
sequence of sentences, formed by a series of words, a sequence of graphemes,
and punctuation. That's a quite simple cascade of categories which can be very
well anticipated when processing text. With that mental model, line beginnings
would rather be considered to be on the same level as signs, but "Nomadisme …"
turns out *not* to be a sibling object of the object that represents the line
beginning and is *not* in direct relation with the paragraph. In lxml's model it
is rather an attribute ``tail`` assigned to that line beginning. The text
contents of the object that represents the ``hi`` element and its children give
a good impression how hairy simple tasks can become.

An algorithm that shall remove line beginnings, space representations and
concatenate broken words would need a function that removes the element objects
in question while preserving the text fragments in its meaningful sequence
attached to the ``text`` and ``tail`` properties. In case these have no content,
their value of ``None`` leads to different operations to concatenate strings.
Here's a working implementation from the inxs_ library for that data model:

.. code-block:: python

   def remove_elements(
       *elements: etree.ElementBase,
       keep_children=False,
       preserve_text=False,
       preserve_tail=False
    ) -> None:
       """ Removes the given elements from its tree. Unless ``keep_children`` is
           passed as ``True``, its children vanish with it into void. If
           ``preserve_text`` is ``True``, the text and tail of a deleted element
           will be preserved either in its left sibling's tail or its parent's
           text. """
       for element in elements:
           if preserve_text and element.text:
               previous = element.getprevious()
               if previous is None:

                   parent = element.getparent()
                   if parent.text is None:
                       parent.text = ''
                   parent.text += element.text
               else:
                   if previous.tail is None:
                       previous.tail = element.text
                   else:
                       previous.tail += element.text

           if preserve_tail and element.tail:
               if keep_children and len(element):
                   if element[-1].tail:
                       element[-1].tail += element.tail
                   else:
                       element[-1].tail = element.tail
               else:
                   previous = element.getprevious()
                   if previous is None:
                       parent = element.getparent()
                       if parent.text is None:
                           parent.text = ''
                       parent.text += element.tail
                   else:
                       if len(element):
                           if element[-1].tail is None:
                               element[-1].tail = element.tail
                           else:
                               element[-1].tail += element.tail
                       else:
                           if previous.tail is None:
                               previous.tail = ''
                           previous.tail += element.tail

           if keep_children:
               for child in element:
                   element.addprevious(child)
           element.getparent().remove(element)

That by itself is enough to simply remove the ``space`` elements, but also
considering word-breaking dashes to wrap everything up is a similar piece of
routine of its own. And these quirks come back to you steadily while actual
markup is regularly more complex.

Now obviously, the data model that lxml / libxml2 provides is not up to standard
Python ergonomics to solve text encoding problems at hand.

There must be a better way.

There is a notable other markup parser that wraps around lxml, BeautifulSoup4_.
It carries some interesting ideas, but is overall too opinionated and partly
ambiguous to implement a stringent data model. A notable specification of a
solid model for text documents is the `DOM API`_ that is even implemented in the
standard library's :mod:`xml.dom.minidom` module. But it lacks an XPath
interface and rumours say it's slow. To illustrate the more accessible model
with a better locatability, here's another graphical representation of the
markup example from above with text content in an emancipated, dedicated node
type:

.. image:: images/dom-model-example.png

Note that text containing attributes appear in document order which promises
an eased lookaround.
So, the obvious (?) idea is to wrap lxml in a layer that takes the DOM API as
paradigmatic inspiration, looks and behaves pythonic while keeping the wrapped
powers accessible.

Now with that API at hand, this is what an equivalent of the horribly
complicated function seen above would look like:

.. code-block:: python

   @altered_default_filters()
   def remove_nodes(*nodes: NodeBase, keep_children=False):
       """ Removes the given nodes from its tree. Unless ``keep_children`` is
            passed as ``True``, its children vanish with it into void. """
       for node in nodes:
           node.detach(retain_child_nodes=keep_children)


.. _BeautifulSoup4: https://www.crummy.com/software/BeautifulSoup/
.. _dom api: https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model
.. _gnome: https://www.gnome.org/
.. _inxs: http://inxs.readthedocs.org/
.. _libxml2: http://xmlsoft.org/
.. _lxml: http://lxml.de/
.. _open document format: http://opendocumentformat.org/
.. _xml-tei: http://tei-c.org


Frequently Asked Questions
--------------------------

Isn't XML an obsolete format for text encoding, invented by boomers and
cynically held up by their Generation X apologists? Why don't you put your
efforts in developing new approaches such as storing text in a graph database?

   We think that XML-based encodings are actually very well suited for long-term
   usable text representations with a broad potential for granularity of
   capturing and semantic annotations. Not only is the data format simple enough
   to hold a full artifact in a self-contained file, but we also consider the
   duality of a format that can be handled both as stream and as tree as a
   helpful feature to address the physical and logical dimensions of a text and
   its manifestation. That is advantageous over depending on a heavy-weight
   database system.
   We acknowledge unquestionably that the specifications in the XML universe are
   often over-engineered, partly stuck in the times of their genesis and thus
   (euphemistically put) `no fun`_. As a direct result of that the availability
   of implementations for contemporary development contexts and their ergonomics
   are poor, if available at all for a platform. That is what *delb* is
   addressing.


What are your long-term goals with this project?

   Currently we want to flesh out a concluded user interface that lets
   developers concentrate on their tasks and not on the shortcomings and
   idiosyncrasies of available tools in the Pythoniverse. Later we'd like to
   port the sound, settled data model and API to a Rust implementation (of which
   a proof-of-concept prototype exists) and replace the current *lxml* wrapper
   for Python with bindings to that as well as provide such for TypeScript.
   Currently that's the aim for a non-beta release.
   Eventually we'd like to re-conquer the world wide web and make unagitated,
   long texts and Stooges clips its predominant content again. On that occasion,
   fuck you Mark, fuck off Jeff, go fuck yourself Peter and all the other
   fucknut character masks. What a disgusting misery it is that the capital
   created from Tim's ideas.


Why is your XPath support so poor?

   While exploring the potential extent of the API we got excited about the
   :meth:`_delb.TagNode.fetch_or_create_by_xpath` feature. In order to include
   it, we had to implement a native XPath expression parser. As a release was
   overdue and we don't know yet to which extent the XPath specification shall
   be supported eventually, we opted for releasing a shaky solution. Figuring
   out a fitting one for *delb*  will be the main piece of the next release,
   so watch and get involved if that interests you.


.. _no fun: https://www.youtube.com/watch?v=5sSKH0iXWo8
