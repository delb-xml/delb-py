# Copyright (C) 2019  Frank Sachsenheim
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
