Installation
============

From the Python Package Index
-----------------------------

To install *delb* manually, not as dependency,  use pip_::

    $ pip install delb


There are two extra features that can be selected to install their respective
dependencies.

To include `httpx` that is used to provide a document loader that fetches web
resources::

    $ pip install delb[web-loader]


`lxml` can be installed as optional parsing backend::

    $ pip install delb[lxml-parser]


Note that multiple extra features are specified by concatenating them with
commas::

    $ pip install delb[lxml-parser,web-loader]


From source
-----------

Prerequisites:

- A virtual environment of your project is activated.

Obtain the code with roughly one of:

- ``git clone git@github.com:delb-xml/delb-py.git``
- ``curl -LosS https://github.com/delb-xml/delb-py/archive/main.tar.gz | tar xzf -``

To install it regularly::

    …/delb-py $ pip install .

Again, to include the loading over *http(s)*::

    …/delb-py $ pip install .[web-loader]

For developing purposes of ``delb`` itself, the library should be installed in
editable_ mode::

    …/delb-py $ pip install --editable .


.. hint::

    Using git submodules is a great way to vendorize a lib for your project and
    to have a fork for your adjustments. Please offer the latter to upstream if
    done well.


Developer toolbox
-----------------

The repository includes configurations so that beside a suited Python
interpreter two tools need to be available globally.

just
~~~~

just_ is a task runner that executes a variety of common *recipes*. This gives a
list of all available ones::

    …/delb-py $ just --list

Before committing changes, run the complete suite of quality checks by invoking
the default recipe::

    …/delb-py $ just

Both, the recipes in the ``Justfile`` as well as various sections in the
``pyproject.toml``, are prescriptive how different aspects are to be applied or
tested.

pipx
~~~~

pipx_, often available from distributions' repositories, is required to invoke
various Python tools without explicitly installing them.


Development guidelines
----------------------

pytest
~~~~~~

You can skip some long running tests by invoking pytest in a context where the
environment variable ``SKIP_LONG_RUNNING_TESTS`` is defined.


.. _editable: https://packaging.python.org/guides/distributing-packages-using-setuptools/#working-in-development-mode
.. _just: https://just.systems/
.. _pip: https://pip.pypa.io/
.. _pipx: https://pipx.pypa.io/stable/
