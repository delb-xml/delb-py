Installation
============

From the Python Package Index
-----------------------------

Before you install the library manually you might consider to use a project
management tool like pipenv_ or poetry_, or still use pip_::

    pip install delb


At the moment there's only one optional dependency to enable document loading
via `https`, to include it use::

    pip install delb[https-loader]
    # in a poetry managed project
    poetry add --extras=https-loader delb


From source
-----------

Prerequisites:

- a virtual environment of your project is activated
- that virtual environment houses an interpreter for Python 3.7 or later

Obtain the code with roughly one of:

- ``git clone git@github.com:delb-xml/delb-py.git``
- ``curl -LosS https://github.com/delb-xml/delb-py/archive/main.tar.gz | tar xzf -``

To install it regularly::

    …/delb $ pip install .

For developing purposes of ``delb`` itself, poetry_ (we recommend installing it
with pipx_, but ``pip install --user poetry`` should often work too) should be
used which install the library in editable_ mode and all employed development
tools::

    …/delb $ poetry install


.. hint::

    Using git submodules is a great way to vendorize a lib for your project and
    to have a fork for your adjustments. Please offer the latter to upstream if
    done well.


.. _editable: https://packaging.python.org/guides/distributing-packages-using-setuptools/#working-in-development-mode
.. _pip: https://pypi.org/project/pip/
.. _pipx: https://pypa.github.io/pipx/
.. _pipenv: https://pypi.org/project/pipenv/
.. _poetry: https://poetry.eustace.io/docs/
