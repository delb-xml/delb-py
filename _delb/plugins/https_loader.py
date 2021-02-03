# Copyright (C) 2018-'21  Frank Sachsenheim
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
from types import SimpleNamespace
from typing import Any, Tuple

from _delb.plugins import plugin_manager
from _delb.plugins.core_loaders import buffer_loader, ftp_http_loader
from _delb.typing import LoaderResult


# TODO define as extra-depending plugin once this is solved:
#      https://github.com/sdispater/poetry/issues/1454
try:
    import requests
except ImportError:
    __all__: Tuple[str, ...] = ()
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

    @plugin_manager.register_loader(before=ftp_http_loader)
    def https_loader(data: Any, config: SimpleNamespace) -> LoaderResult:
        """
        This loader loads a document from a URL with the ``https`` scheme. The URL will
        be bound to ``source_url`` on the document's :attr:`Document.config` attribute.
        """
        if isinstance(data, str) and data.lower().startswith("https://"):
            response = requests.get(data, stream=True)
            config.source_url = response.url
            return buffer_loader(HttpsStreamWrapper(response), config)
        return "The input value is not an URL with the https scheme."

    __all__ = ("https_loader",)
