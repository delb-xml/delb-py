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

from typing import Union, Iterable, List

import pluggy  # type: ignore
from delb.typing import Loader


hookspec = pluggy.HookspecMarker("delb")


@hookspec
def configure_loaders(loaders: List[Loader]) -> None:
    """
    Configures the document loaders. Implementations are expected to manipulate
    the list that is provided to the hook.
    """


@hookspec
def get_document_mixins() -> Union[type, Iterable]:
    """
    :return: Either a single class or an iterable of such that shall extend
             the :class:`delb.Document` class.
    """
