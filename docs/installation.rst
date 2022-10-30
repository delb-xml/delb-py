Installation
============

From the Python Package Index
-----------------------------

To install *delb* manually, not as dependency,  use pip_::

    $ pip install delb


At the moment there's only one optional dependency to enable document loading
via `http` and `https`, to include it use::

    $ pip install delb[https-loader]


From source
-----------

Prerequisites:

- A virtual environment of your project is activated.
- That virtual environment houses an interpreter for Python 3.7 or later.

Obtain the code with roughly one of:

- ``git clone git@github.com:delb-xml/delb-py.git``
- ``curl -LosS https://github.com/delb-xml/delb-py/archive/main.tar.gz | tar xzf -``

To install it regularly::

    …/delb-py $ pip install .

Again, to include the loading over *http(s)*::

    …/delb-py $ pip install .[https-loader]

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
interpreter three tools need to be available globally. pipx_ is the recommended
facilitation to install the Python implemented tools *black* and *hatch*.

just
~~~~

just_ is a task runner that executes a variety of common *recipes*. This gives a
list of all available ones::

    …/delb-py $ just --list

Before committing changes, run the complete suite of quality checks by invoking
the default recipe::

    …/delb-py $ just

black
~~~~~

It's recommended to configure the used editors and IDEs to enforce black_'s code
style, but it can also be applied with::

    …/delb-py $ just black

hatch
~~~~~

Many other of the *just* recipes rely on hatch_.


.. _black: https://black.readthedocs.io/
.. _editable: https://packaging.python.org/guides/distributing-packages-using-setuptools/#working-in-development-mode
.. _hatch: https://hatch.pypa.io/
.. _just: https://just.systems/
.. _pip: https://pip.pypa.io/
.. _pipx: https://pypa.github.io/pipx/
