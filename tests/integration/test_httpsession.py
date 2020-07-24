import asyncio
import json
import pytest

from io import BytesIO
from transcribe.httpsession import AwsCrtHttpSessionManager


async def json_from_body(response):
    response_body = BytesIO()
    while True:
        chunk = await response.get_chunk()
        if chunk:
            response_body.write(chunk)
        else:
            break
    response_body.seek(0)
    response_json = json.load(response_body)
    return response_json


@pytest.mark.asyncio
async def test_make_request(default_eventloop):
    session = AwsCrtHttpSessionManager(default_eventloop)
    url = "https://httpbin.org/anything"
    headers = [
        ("host", "httpbin.org"),
        ("user-agent", "aws-crt-python 0.1"),
    ]
    body = BytesIO(b"foo body")
    response = await session.make_request(
        url, method="PUT", headers=headers, body=body,
    )
    assert await response.status_code == 200
    assert await response.headers

    response_json = await json_from_body(response)
    assert response_json.get("method") == "PUT"
    assert response_json.get("data") == "foo body"
    sent_headers = response_json.get("headers")
    assert sent_headers["Host"] == "httpbin.org"
    assert sent_headers["User-Agent"] == "aws-crt-python 0.1"

    assert await response.done
