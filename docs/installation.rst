Installation
============

From the Python Package Index
-----------------------------

Not yet.


From source
-----------

Prerequisites:

- poetry_ is available (``pip install --user poetry`` should often work)
- a virtual environment of your project is activated
- that virtual environment houses an interpreter for Python 3.6 or later

Obtain the code with roughly one of:

- ``git clone git@github.com:funkyfuture/lxml-domesque.git``
- ``curl -L https://github.com/funkyfuture/lxml-domesque/archive/master.tar.gz | tar xzf -``

.. hint::

    Using git submodules is a great way to vendorize an unpublished lib for
    your project and to have a fork for your adjustments. Please offer the
    latter to upstream if done well.

And eventually install the lib::

    …/lxml-domesque $ poetry install

You may append ``--no-dev`` to that command in order to install no dependencies
that are needed to develop the library properly.

.. _poetry: https://poetry.eustace.io/docs/
