# Copyright (C) 2018-'22  Frank Sachsenheim
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


from __future__ import annotations

from io import IOBase
from types import SimpleNamespace
from typing import Any, Iterator, Optional

from _delb.plugins import plugin_manager
from _delb.plugins.core_loaders import buffer_loader, ftp_loader
from _delb.typing import LoaderResult


try:
    import httpx  # noqa: F401
except ImportError:
    __all__: tuple[str, ...] = ()
else:
    DEFAULT_CLIENT = httpx.Client(follow_redirects=True, http2=True)

    class HttpsStreamWrapper(IOBase):
        __slots__ = ("_generator", "_response")

        def __init__(self, response: httpx.Response):
            self._generator: Optional[Iterator[bytes]] = None
            self._response = response

        def read(self, size: int = 4096) -> bytes:
            if self._generator is None:
                self._generator = self._response.iter_bytes(chunk_size=size)

            try:
                return next(self._generator)
            except StopIteration:
                return b""

    @plugin_manager.register_loader(before=ftp_loader)
    def https_loader(
        data: Any, config: SimpleNamespace, client: httpx.Client = DEFAULT_CLIENT
    ) -> LoaderResult:
        """
        This loader loads a document from a URL with the ``http`` and ``https`` scheme.
        Redirects are followed. The default httpx_-client follows redirects and can
        partially be configured with `environment variables`_. The URL will be bound to
        the name ``source_url`` on the document's :attr:`Document.config` attribute.

        Loaders with specifically configured httpx-clients can build on this loader
        like so:

        .. testcode::

            import httpx
            from _delb.plugins import plugin_manager
            from _delb.plugins.https_loader import https_loader


            client = httpx.Client(follow_redirects=False, trust_env=False)

            @plugin_manager.register_loader(before=https_loader)
            def custom_https_loader(data, config):
                return https_loader(data, config, client=client)

        .. _environment variables: https://www.python-httpx.org/environment_variables/
        .. _httpx: https://www.python-httpx.org/
        """
        if isinstance(data, str) and data.lower().startswith(("http://", "https://")):
            with client.stream("get", url=data) as response:
                response.raise_for_status()
                result = buffer_loader(HttpsStreamWrapper(response), config)
                config.source_url = data
                return result
        return "The input value is not an URL with the http or https scheme."

    __all__ = (https_loader.__name__,)
