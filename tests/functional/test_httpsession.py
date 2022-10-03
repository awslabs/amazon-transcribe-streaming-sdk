import unittest.mock as mock
import pytest

from io import BytesIO
from awscrt import http
from concurrent.futures import Future
from amazon_transcribe.exceptions import HTTPException
from amazon_transcribe.httpsession import AwsCrtHttpSessionManager


def get_new_connection():
    mock_stream = mock.Mock(spec=http.HttpClientStream)
    mock_stream.completion_future = Future()
    mock_connection = mock.Mock(spec=http.HttpClientConnection)
    mock_connection.version = http.HttpVersion.Http2
    mock_connection.request.return_value = mock_stream
    mock_connection.is_open.return_value = True
    mock_connection_future = Future()
    mock_connection_future.set_result(mock_connection)
    return mock_connection, mock_connection_future


@pytest.fixture
def mock_connection():
    return get_new_connection()[0]


@pytest.fixture
def mock_connection_cls(mock_connection):
    mock_cls = mock.Mock()
    connection_future = Future()
    connection_future.set_result(mock_connection)
    mock_cls.new.return_value = connection_future

    def limit_to_one(**kwargs):
        if mock_cls.new.call_count == 1:
            return mock.DEFAULT
        else:
            raise AssertionError("This mock constructor can only be invoked once")

    mock_cls.new.side_effect = limit_to_one
    return mock_cls


@pytest.fixture
def session_manager(mock_connection_cls, default_eventloop):
    session_manager = AwsCrtHttpSessionManager(default_eventloop)
    session_manager.HTTP_CONNECTION_CLS = mock_connection_cls
    return session_manager


def assert_request(connection, expected_request):
    actual_request = connection.request.call_args[0][0]
    assert dict(actual_request.headers) == dict(expected_request.headers)
    # TODO: Figure out how to compare bodies, the CRT wraps them and we have no
    # way to compare the contents of the body once it's passed to the request.
    # For now we're just asserting that both requests have bodies or not
    # assert actual_request.body_stream == expected_request.body_stream
    actual_body = actual_request.body_stream is None
    expected_body = expected_request.body_stream is None
    assert actual_body == expected_body
    assert actual_request.method == expected_request.method
    assert actual_request.path == expected_request.path


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url, request_kwargs, expected_request",
    [
        ("https://example.com", {}, http.HttpRequest("GET", "/")),
        ("https://example.com:4242", {}, http.HttpRequest("GET", "/")),
        ("https://example.com/api", {}, http.HttpRequest("GET", "/api")),
        (
            "https://example.com?foo=bar",
            {},
            http.HttpRequest("GET", "/?foo=bar"),
        ),
        (
            "https://example.com",
            {"method": "PUT"},
            http.HttpRequest("PUT", "/"),
        ),
        (
            "https://example.com/api?foo=bar",
            {},
            http.HttpRequest("GET", "/api?foo=bar"),
        ),
        (
            "https://example.com",
            {"body": b"foo"},
            http.HttpRequest("GET", "/", body_stream=BytesIO(b"foo")),
        ),
        (
            "https://example.com",
            {"body": BytesIO(b"foo")},
            http.HttpRequest("GET", "/", body_stream=BytesIO(b"foo")),
        ),
        (
            "https://example.com",
            {"headers": [("foo", "bar")]},
            http.HttpRequest(
                "GET",
                "/",
                headers=http.HttpHeaders([("foo", "bar")]),
            ),
        ),
    ],
)
async def test_make_request(
    url, request_kwargs, expected_request, session_manager, mock_connection
):
    await session_manager.make_request(url, **request_kwargs)
    assert_request(mock_connection, expected_request)


@pytest.mark.asyncio
async def test_make_request_reuses_connections(
    session_manager,
    mock_connection,
    mock_connection_cls,
):
    await session_manager.make_request("https://example.com")
    await session_manager.make_request("https://example.com")
    assert mock_connection_cls.new.call_count == 1
    assert mock_connection.request.call_count == 2


@pytest.mark.asyncio
async def test_make_request_does_not_reuse_stale_connections(
    session_manager,
    mock_connection,
    mock_connection_cls,
):
    new_mock_connection, new_mock_connection_future = get_new_connection()
    mock_connection_cls.new.side_effect = [mock.DEFAULT, new_mock_connection_future]

    await session_manager.make_request("https://example.com")

    mock_connection.is_open.return_value = False

    await session_manager.make_request("https://example.com")
    assert mock_connection.is_open.call_count == 2
    assert mock_connection_cls.new.call_count == 2
    assert mock_connection.request.call_count == 1
    assert new_mock_connection.request.call_count == 1


@pytest.mark.asyncio
async def test_make_request_pools_based_on_scheme(
    session_manager,
    mock_connection,
    mock_connection_cls,
):
    new_mock_connection, new_mock_connection_future = get_new_connection()
    mock_connection_cls.new.side_effect = [mock.DEFAULT, new_mock_connection_future]

    await session_manager.make_request("http://example.com")
    await session_manager.make_request("https://example.com")
    assert mock_connection_cls.new.call_count == 2
    assert mock_connection.request.call_count == 1
    assert new_mock_connection.request.call_count == 1


@pytest.mark.asyncio
async def test_make_request_pools_based_on_port(
    session_manager,
    mock_connection,
    mock_connection_cls,
):
    new_mock_connection, new_mock_connection_future = get_new_connection()
    mock_connection_cls.new.side_effect = [mock.DEFAULT, new_mock_connection_future]
    await session_manager.make_request("https://example.com")
    await session_manager.make_request("https://example.com:4343")
    assert mock_connection_cls.new.call_count == 2
    assert mock_connection.request.call_count == 1
    assert new_mock_connection.request.call_count == 1


@pytest.mark.asyncio
async def test_make_request_fails_if_connection_does_not_open(
    session_manager,
    mock_connection,
):
    mock_connection.is_open.return_value = False
    with pytest.raises(HTTPException):
        await session_manager.make_request("https://example.com")


@pytest.mark.asyncio
async def test_make_request_invalid_hostname(session_manager):
    with pytest.raises(HTTPException):
        await session_manager.make_request("not-a-host")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url, port",
    [
        ("https://example.com", 443),
        ("http://example.com", 80),
        ("https://example.com:4242", 4242),
        ("http://example.com:8080", 8080),
    ],
)
async def test_make_request_port(
    url,
    port,
    session_manager,
    mock_connection_cls,
):
    await session_manager.make_request(url)
    new_conn_kwargs = mock_connection_cls.new.call_args[1]
    assert new_conn_kwargs["port"] == port


@pytest.mark.asyncio
async def test_make_request_tls_options(session_manager, mock_connection_cls):
    _, new_mock_connection_future = get_new_connection()
    mock_connection_cls.new.side_effect = [mock.DEFAULT, new_mock_connection_future]
    await session_manager.make_request("https://example.com")
    new_conn_kwargs = mock_connection_cls.new.call_args[1]
    assert new_conn_kwargs["tls_connection_options"] is not None
    await session_manager.make_request("http://example.com")
    new_conn_kwargs = mock_connection_cls.new.call_args[1]
    assert new_conn_kwargs["tls_connection_options"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "version",
    [
        http.HttpVersion.Http1_0,
        http.HttpVersion.Http1_1,
    ],
)
async def test_make_request_refuses_http1(version, session_manager, mock_connection):
    mock_connection.version = version
    with pytest.raises(HTTPException):
        await session_manager.make_request("https://example.com")
    mock_connection.close.assert_called_with()


@pytest.mark.asyncio
async def test_response_headers(session_manager, mock_connection):
    response = await session_manager.make_request("https://example.com")
    headers_callback = mock_connection.request.call_args[0][1]
    # Simulate the CRT event loop responding
    headers_callback(status_code=200, headers=[("foo", "bar")])
    # Assert the response properties are available
    assert await response.status_code == 200
    assert await response.headers == [("foo", "bar")]


@pytest.mark.asyncio
async def test_response_get_chunk(
    session_manager,
    mock_connection,
):
    response = await session_manager.make_request("https://example.com")
    # Simulate the CRT event loop responding
    body_callback = mock_connection.request.call_args[0][2]
    # Test getting a chunk when one has already been set
    body_callback(chunk=b"some bytes")
    assert await response.get_chunk() == b"some bytes"
    # Test getting a chunk that's later fufilled
    future_chunk = response.get_chunk()
    body_callback(chunk=b"more bytes")
    assert await future_chunk == b"more bytes"
    # Test if the stream ends while waiting for a chunk empty bytes is returned
    future_chunk = response.get_chunk()
    mock_connection.request.return_value.completion_future.set_result(True)
    assert await future_chunk == b""
    # Test getting a chunk when the stream has ended and there are no chunks
    assert await response.get_chunk() == b""
