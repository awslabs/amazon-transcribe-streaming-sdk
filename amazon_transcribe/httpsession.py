# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


import asyncio
from concurrent.futures import Future
from io import BytesIO
from threading import Lock
from typing import AsyncGenerator, Awaitable, List, Optional, Tuple, Union
from urllib.parse import ParseResult, urlparse

from awscrt import http, io

from amazon_transcribe.exceptions import HTTPException
from amazon_transcribe.response import Response

HeadersList = List[Tuple[str, str]]


class AwsCrtHttpResponse:
    def __init__(self):
        self._stream = None
        self._status_code_future: Future[int] = Future()
        self._headers_future: Future[HeadersList] = Future()
        self._chunk_futures: List[Future[bytes]] = []
        self._received_chunks: List[bytes] = []
        self._chunk_lock: Lock = Lock()

    async def resolve_response(self) -> Response:
        return Response(
            status_code=await self.status_code,
            headers=dict(await self.headers),
        )

    async def consume_body(self) -> bytes:
        body = b""
        async for chunk in self.chunks():
            body += chunk
        return body

    def _set_stream(self, stream: http.HttpClientStream):
        if self._stream is not None:
            raise HTTPException("Stream already set on AwsCrtHttpResponse object")
        self._stream = stream
        self._stream.completion_future.add_done_callback(self._on_complete)
        self._stream.activate()

    @property
    def status_code(self) -> Awaitable[int]:
        return asyncio.wrap_future(self._status_code_future)

    @property
    def headers(self) -> Awaitable[HeadersList]:
        return asyncio.wrap_future(self._headers_future)

    @property
    def done(self) -> Awaitable[bool]:
        return asyncio.wrap_future(self._stream.completion_future)

    def get_chunk(self) -> Awaitable[bytes]:
        with self._chunk_lock:
            future: Future[bytes] = Future()
            # TODO: update backpressure window
            if self._received_chunks:
                chunk = self._received_chunks.pop(0)
                future.set_result(chunk)
            elif self._stream.completion_future.done():
                future.set_result(b"")
            else:
                self._chunk_futures.append(future)
            return asyncio.wrap_future(future)

    async def chunks(self) -> AsyncGenerator[bytes, None]:
        while True:
            chunk = await self.get_chunk()
            if chunk:
                yield chunk
            else:
                break

    def _on_headers(self, status_code: int, headers: HeadersList, **kwargs):
        self._status_code_future.set_result(status_code)
        self._headers_future.set_result(headers)

    def _on_body(self, chunk: bytes, **kwargs):
        with self._chunk_lock:
            # TODO: update back pressure window
            if self._chunk_futures:
                future = self._chunk_futures.pop(0)
                future.set_result(chunk)
            else:
                self._received_chunks.append(chunk)

    def _on_complete(self, completion_future):
        with self._chunk_lock:
            if self._chunk_futures:
                future = self._chunk_futures.pop(0)
                future.set_result(b"")


class AwsCrtHttpSessionManager:
    _HTTP_PORT = 80
    _HTTPS_PORT = 443
    HTTP_CONNECTION_CLS = http.HttpClientConnection

    def __init__(self, eventloop):
        # TODO: accept an AWSEventLoop object or similar
        self._client_bootstrap = eventloop
        self._tls_ctx = io.ClientTlsContext(io.TlsContextOptions())
        self._socket_options = io.SocketOptions()
        self._connections = {}

    async def _create_connection(
        self, parsed_url: ParseResult
    ) -> http.HttpClientConnection:
        if parsed_url.scheme == "http":
            port = self._HTTP_PORT
            tls_connection_options = None
        else:
            port = self._HTTPS_PORT
            tls_connection_options = self._tls_ctx.new_connection_options()
            tls_connection_options.set_server_name(parsed_url.hostname)
            tls_connection_options.set_alpn_list(["h2"])
        if parsed_url.port is not None:
            port = parsed_url.port
        connect_future = self.HTTP_CONNECTION_CLS.new(
            bootstrap=self._client_bootstrap,
            host_name=parsed_url.hostname,
            port=port,
            socket_options=self._socket_options,
            tls_connection_options=tls_connection_options,
        )
        connection = await asyncio.wrap_future(connect_future)
        if connection.version is not http.HttpVersion.Http2:
            connection.close()
            raise HTTPException(
                "HTTP/2 could not be negotiated: %s" % connection.version
            )
        return connection

    async def _get_connection(
        self,
        parsed_url: ParseResult,
    ) -> http.HttpClientConnection:
        # TODO: Use CRT connection pooling instead of this basic kind
        if not parsed_url.hostname:
            raise HTTPException("Invalid host name: %s" % parsed_url.hostname)
        connection_key = (
            parsed_url.scheme,
            parsed_url.hostname,
            parsed_url.port,
        )
        if connection_key in self._connections:
            return self._connections[connection_key]
        else:
            connection = await self._create_connection(parsed_url)
            self._connections[connection_key] = connection
            return connection

    def _get_path(self, parsed_url: ParseResult) -> str:
        path = parsed_url.path
        if not path:
            path = "/"
        if parsed_url.query:
            path = path + "?" + parsed_url.query
        return path

    async def make_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[HeadersList] = None,
        body: Union[bytes, BytesIO, None] = None,
    ) -> AwsCrtHttpResponse:
        if isinstance(headers, list):
            headers = http.HttpHeaders(headers)
        if isinstance(body, bytes):
            body = BytesIO(body)

        parsed_url = urlparse(url)
        request = http.HttpRequest(
            method=method,
            path=self._get_path(parsed_url),
            headers=headers,
            body_stream=body,
        )

        connection = await self._get_connection(parsed_url)
        response = AwsCrtHttpResponse()
        stream = connection.request(
            request,
            response._on_headers,
            response._on_body,
        )
        response._set_stream(stream)
        return response
