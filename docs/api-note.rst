.. note::

    There are actually two packages that are installed with *delb*:
    ``delb`` and ``_delb``. As the underscore indicates, the latter is exposing
    private parts of the API while the first is re-exposing what is deemed to
    be public from that one and additional contents.
    As a rule of thumb, use the public API in applications and the private API
    in *delb* extensions. By doing so, you can avoid circular dependencies if
    your extension (or other code that it depends on) uses contents from the
    ``_delb`` package.
