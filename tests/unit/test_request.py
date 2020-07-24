from io import BytesIO
import pytest

from amazon_transcribe.request import Request, PreparedRequest, HeadersDict


class TestRequest:
    def test_minimal_request(self):
        req = Request(endpoint="https://aws.amazon.com")
        assert req.endpoint == "https://aws.amazon.com"
        assert req.path == "/"
        assert req.method == "GET"
        assert req.headers == HeadersDict()
        assert req.body is None
        assert req.params == {}

    def test_request_with_basic_args(self):
        req = Request(
            endpoint="https://aws.amazon.com",
            path="/transcribe",
            method="HEAD",
            headers={"User-Agent": "test-transcribe-0.0.1"},
            body="Test body",
            params={"test": "value"},
        )
        assert req.endpoint == "https://aws.amazon.com"
        assert req.path == "/transcribe"
        assert req.method == "HEAD"
        assert req.headers == {"User-Agent": "test-transcribe-0.0.1"}
        assert req.body == "Test body"
        assert req.params == {"test": "value"}

    def test_request_preparation(self):
        req = Request(
            endpoint="https://aws.amazon.com",
            path="/transcribe",
            method="hEaD",
            headers={"User-Agent": "test-transcribe-0.0.1"},
            body="Test body",
            params={"test": "value"},
        )
        prep = req.prepare()
        assert prep.endpoint == "https://aws.amazon.com"
        assert prep.path == "/transcribe"
        assert prep.uri == "https://aws.amazon.com/transcribe?test=value"
        assert prep.method == "HEAD"
        assert prep.headers == HeadersDict({"User-Agent": "test-transcribe-0.0.1"})
        assert prep.body.read() == BytesIO(b"Test body").read()
        assert prep.query == "test=value"

    @pytest.mark.parametrize(
        "endpoint,path,params,expected",
        [
            (
                "https://example.com",
                "/",
                {"test": "test"},
                "https://example.com/?test=test",
            ),
            (
                "https://example.com/",
                "/transcribe",
                None,
                "https://example.com/transcribe",
            ),
            (
                "https://example.com",
                "transcribe",
                None,
                "https://example.com/transcribe",
            ),
            (
                "https://example.com",
                "/",
                {"a": "b", "c": "d"},
                "https://example.com/?a=b&c=d",
            ),
            ("https://example.com", "", None, "https://example.com/"),
        ],
    )
    def test_prepared_request_uri(self, endpoint, path, params, expected):
        if params is None:
            params = {}
        req = Request(endpoint=endpoint, path=path, params=params)
        prep = req.prepare()
        assert prep.uri == expected


class TestHeadersDict:
    def test_header_dict_creation(self):
        hdict = HeadersDict({"test": "header"})
        assert hdict["test"] == "header"

    def test_header_dict_assignment(self):
        hdict = HeadersDict()
        hdict["test"] = "header"
        assert hdict["test"] == "header"

    def test_headers_dict_update(self):
        headers = {
            "user-agent": "test-0.0.1",
            "content-type": "application/json",
            "notAReal": "heaDer",
        }
        hdict = HeadersDict()
        hdict.update(headers)
        for key in headers.keys():
            assert headers[key] == hdict[key]

    @pytest.mark.parametrize(
        "key,value,expected_key,expected_value",
        [
            ("header", "test", "header", "test"),
            (" header", "test", "header", "test"),
            ("header", " test ", "header", "test"),
            ("header\r\n", "\ntest\r", "header", "test"),
        ],
    )
    def test_headers_dict_validation(self, key, value, expected_key, expected_value):
        hdict = HeadersDict()
        hdict[key] = value
        assert hdict[expected_key] == expected_value
