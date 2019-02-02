class InvalidCodePath(RuntimeError):
    def __init__(self):
        super().__init__(
            "An unintended path was taken through the code. Please report this bug."
        )


class InvalidOperation(Exception):
    pass


__all__ = (InvalidCodePath.__name__, InvalidOperation.__name__)
