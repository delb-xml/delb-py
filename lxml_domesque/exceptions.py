class InvalidCodePath(RuntimeError):
    """
    Raised when a code path that is not expected to be executed is reached.
    """
    def __init__(self):  # pragma: no cover
        super().__init__(
            "An unintended path was taken through the code. Please report this bug."
        )


class InvalidOperation(Exception):
    """
    Raised when an invalid operation is attempted by the client code.
    """
    pass


__all__ = (InvalidCodePath.__name__, InvalidOperation.__name__)
