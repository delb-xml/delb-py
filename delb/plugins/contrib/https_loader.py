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


"""
If ``delb`` is installed with ``https-loader`` as extra, the required
dependencies for this loader are installed as well. See :doc:`installation`.
"""


from io import IOBase
from typing import Any, List

import pluggy  # type: ignore
from lxml import etree

from delb.plugins.contrib.core_loaders import buffer_loader, ftp_http_loader
from delb.typing import Loader, LoaderResult


hookimpl = pluggy.HookimplMarker("delb")


# TODO define as extra-depending plugin once this is solved:
#      https://github.com/sdispater/poetry/issues/1454
try:
    import requests
except ImportError:
    pass
else:

    class HttpsStreamWrapper(IOBase):
        def __init__(self, response: requests.Response):
            self._iterator = response.iter_content(
                chunk_size=None, decode_unicode=False
            )

        def read(self, _) -> bytes:
            try:
                return next(self._iterator)
            except StopIteration:
                return b""

    def https_loader(data: Any, parser: etree.XMLParser) -> LoaderResult:
        """
        This loader loads a document from a URL with the ``https`` scheme and is only
        available when requests_ is installed.

        .. _requests: http://python-requests.org
        """
        if isinstance(data, str) and data.lower().startswith("https://"):
            response = requests.get(data, stream=True)
            return buffer_loader(HttpsStreamWrapper(response), parser)
        return None, {}

    @hookimpl
    def configure_loaders(loaders: List[Loader]):
        loaders.insert(loaders.index(ftp_http_loader), https_loader)
