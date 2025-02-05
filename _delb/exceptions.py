# Copyright (C) 2018-'25  Frank Sachsenheim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""These are the specific delb exceptions."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from _delb.typing import Loader


class DelbBaseException(Exception):
    pass


class AmbiguousTreeError(DelbBaseException):
    """
    Raised when a single node shall be fetched or created by an XPath expression in a
    tree where the target position can't be clearly determined.
    """

    def __init__(self, message: str):
        super().__init__(message)


class FailedDocumentLoading(DelbBaseException):
    def __init__(self, source: Any, excuses: dict[Loader, str | Exception]):
        self.source = source
        self.excuses = excuses

    def __str__(self):
        return f"Couldn't load {self.source!r} with these loaders: {self.excuses}"


class InvalidCodePath(DelbBaseException, RuntimeError):
    """Raised when a code path that is not expected to be executed is reached."""

    def __init__(self):  # pragma: no cover
        super().__init__(
            "An unintended path was taken through the code. Please report this bug."
        )


class InvalidOperation(DelbBaseException):
    """Raised when an invalid operation is attempted by the client code."""

    pass


class ParsingError(DelbBaseException):
    pass


class ParsingProcessingError(ParsingError):
    pass


class ParsingValidityError(ParsingError):
    pass


class ParsingEmptyStream(ParsingProcessingError):
    def __init__(self):
        super().__init__("The input stream is empty.")


class XPathEvaluationError(DelbBaseException):
    def __init__(self, message: str):
        super().__init__(message)


class XPathParsingError(DelbBaseException):
    """Raised when an XPath expression can't be parsed."""

    def __init__(
        self,
        expression: Optional[str] = None,
        position: Optional[int] = None,
        message: Optional[str] = None,
    ):
        self.expression = expression
        self.position = position
        self.message = message

    def __str__(self):
        expression = self.expression
        assert expression is not None
        assert self.message is not None
        position = self.position
        assert self.position is not None

        expression_length = len(expression)
        snippet_end = min(position + 16, expression_length)

        if expression_length > snippet_end:
            snippet = f"`{expression[position:snippet_end]}…`"
        else:
            snippet = f"`{expression[position:snippet_end]}`"

        if len(snippet) > 2:
            return (
                f"XPath parsing error at character {position} ({snippet}): "
                f"{self.message}"
            )
        else:
            return f"XPath parsing error at character {position}: {self.message}"


class XPathUnsupportedStandardFeature(XPathParsingError):
    """Raised when an unsupported XPath expression feature is recognized."""

    def __init__(self, position: int, feature_description: str):
        super().__init__(
            position=position,
            message=f"{feature_description} is not supported with intention. "
            "Please consult the documentation regarding the XPath implementation.",
        )


__all__ = (
    AmbiguousTreeError.__name__,
    DelbBaseException.__name__,
    FailedDocumentLoading.__name__,
    InvalidCodePath.__name__,
    InvalidOperation.__name__,
    ParsingEmptyStream.__name__,
    ParsingError.__name__,
    ParsingProcessingError.__name__,
    ParsingValidityError.__name__,
    XPathEvaluationError.__name__,
    XPathParsingError.__name__,
    XPathUnsupportedStandardFeature.__name__,
)
