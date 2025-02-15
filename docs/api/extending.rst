:tocdepth: 2

Extending delb
==============

.. include:: api-note.rst

``delb`` offers a plugin system to facilitate the extendability of a few of its
mechanics with Python packages.
A package that extends its functionality must `provide entrypoint metadata`_
for an entrypoint group named ``delb`` that points to modules that contain
extensions. Some extensions have to be decorated with specific methods
of the plugin manager object. Authors are encouraged to prefix their package
names with ``delb-`` in order to increase discoverability.

These extension types are currently available:

.. grid:: 2

    .. grid-item-card:: Document loaders
       :link: custom-document-loaders
       :link-type: ref

       Loaders are functions that try to make sense of any given input value,
       and if they can they return a parsed document.

    .. grid-item-card:: Parser adapters
       :link: parser-adapters
       :link-type: ref

       Parser adapters can plug to XML parser implementations.

.. grid:: 1

    .. grid-item-card:: XPath functions
       :link: xpath-functions
       :link-type: ref

       Custom XPath functions can be used in XPath predicate expressions.

.. grid:: 2

    .. grid-item-card:: Document mixin classes
       :link: document-mixins
       :link-type: ref

       Mixins add functionality / information to :class:`delb.Document` (instead
       of inheriting from it). That allows applications to rely optionally on
       the availability of plugins and to combine various extensions.

    .. grid-item-card:: Document subclasses
       :link: document-subclasses
       :link-type: ref

       Subclasses can be used to provide distinct models of arbitrary aspects
       for contents that are represented by a specific encoding. They can
       optionally implement a test method to qualify themself as default class
       for recognized contents.

The designated means of communication between extensions is the ``config``
argument to the loader respectively the instance property of a document instance
with that name.

.. warning::

    A module that contains plugins and any module it is explicitly or implicitly
    importing **must not** import anything from the :mod:`delb` package, because
    that would initiate the collection of plugin implementations. And these
    wouldn't have been completely registered at that point. Import the required
    module members from the according path in the :mod:`_delb` package instead.

.. caution::

    Mind to re-install a package in development when its entrypoint
    specification changed.

There's a repository that outlines the mechanics as developer reference:
https://github.com/delb-xml/delb-py-reference-plugins

There's also the snakesist_ project that implements the loader and document
mixin plugin types to interact with eXist-db_ as storage.


.. _custom-document-loaders:

Document loaders
----------------

Loaders are registered with this decorator:

.. autofunction:: _delb.plugins.plugin_manager.register_loader


.. _parser-adapters:

Parser adapters
---------------

.. autoclass:: _delb.plugins.XMLEventParserInterface

The parsed contents are passed with such constructs:

.. autoclass:: _delb.parser.Event

.. autoenum:: _delb.parser.EventType
   :no-inherited-members:

.. autoclass:: _delb.parser.TagEventData
   :no-inherited-members:


.. _document-mixins:

Document mixin classes
----------------------

Document mixin classes are registered by subclassing them from this base class:

.. autoclass:: _delb.plugins.DocumentMixinBase
   :private-members:


.. _document-subclasses:

Document subclasses
-------------------

Of course one can simply subclass :class:`delb.Document` to add functionality.
Beside using a subclass directly, you can let :class:`delb.Document` figure out
which subclass is an appropriate representation of the content. Subclasses can
claim that by implementing a :func:`staticmethod` named ``__class_test__`` that
takes the document's root node and the configuration to return a boolean that
indicates the subclass is suited. The first class to return a ``True`` value
will immediately be chosen, so be aware of the possible ambiguity in complex
setups. It is only ensured that subclasses are considered before others that
they derive from.

Subclasses are registered by importing them into an application, they must not
be pointed to by entrypoint definitions.

Here's an example:

.. testcode::

    class TEIDocument(Document):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **{**kwargs, "collapse_whitespace": True})

        @staticmethod
        def __class_test__(root: TagNode, config: types.SimpleNamespace) -> bool:
            return root.universal_name == "{http://www.tei-c.org/ns/1.0}TEI"

        @property
        def title(self) -> str:
            return self.css_select('titleStmt title[type="main"]').first.full_text

    document = Document("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt>
    <title type="main">The Document's Title</title>
    </titleStmt></fileDesc></teiHeader></TEI>
    """)

    if isinstance(document, TEIDocument):
        print(document.title)
    else:
        print("Sorry, I don't know how to retrieve the document's title.")

.. testoutput::

    The Document's Title


The recommendations as laid out for :meth:`DocumentMixinHooks._init_config
<_delb.plugins.DocumentMixinHooks._init_config>` also apply for subclasses who
would process configuration arguments in their ``__init__`` method before
calling the super class' one.


.. _xpath-functions:

XPath functions
---------------

Custom XPath functions are registered with this decorator:

.. autofunction:: _delb.plugins.PluginManager.register_xpath_function


.. _eXist-db: https://exist-db.org/
.. _provide entrypoint metadata: https://packaging.python.org/guides/creating-and-discovering-plugins/#using-package-metadata
.. _snakesist: https://github.com/delb-xml/snakesist
