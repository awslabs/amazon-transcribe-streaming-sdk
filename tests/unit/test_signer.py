from io import BytesIO

from awscrt.auth import (
    AwsCredentialsProvider,
    AwsSigningAlgorithm,
    AwsSignatureType,
)

from awscrt.http import HttpRequest, HttpHeaders
import pytest

from transcribe.request import Request
from transcribe.signer import (
    CredentialsProvider,
    RequestSigner,
    SigV4RequestSigner,
    _convert_request,
)


def test_signing_config_creation():
    cred_provider = CredentialsProvider().get_provider(
        "test", "secret-123", "session-123"
    )
    assert isinstance(cred_provider, AwsCredentialsProvider)
    creds = cred_provider.get_credentials().result()
    assert creds.access_key_id == "test"
    assert creds.secret_access_key == "secret-123"
    assert creds.session_token == "session-123"


def test_convert_request():
    req = Request(
        endpoint="https://aws.amazon.com",
        path="/transcribe",
        method="HEAD",
        headers={"User-Agent": "test-transcribe-0.0.1"},
        body="Test body",
        params={"test": "value"},
    ).prepare()

    crt_req = _convert_request(req)
    assert isinstance(crt_req, HttpRequest)
    assert crt_req.method == "HEAD"
    assert crt_req.path == "/transcribe"
    assert dict(crt_req.headers) == dict(
        [("User-Agent", "test-transcribe-0.0.1")]
    )
    assert crt_req.body_stream is not None


@pytest.mark.asyncio
async def test_default_request_signer():
    cred_provider = CredentialsProvider().get_provider(
        "test", "secret-123", "session-123"
    )

    signer = RequestSigner("transcribe", "us-west-2", cred_provider)

    request = Request(
        endpoint="https://transcribestreaming.amazonaws.com",
        path="/transcribe",
        method="HEAD",
        headers={"x-test-header": "test-transcribe-0.0.1"},
        body=BytesIO(b"Test body"),
        params={"test": "value"},
    ).prepare()

    assert request.headers == {"x-test-header": "test-transcribe-0.0.1"}
    request = signer.sign(request)
    assert "Authorization" in request.headers
    assert "X-Amz-Date" in request.headers


@pytest.mark.asyncio
async def test_sigv4_request_signer():
    cred_provider = CredentialsProvider().get_provider(
        "test", "secret-123", "session-123"
    )

    signer = SigV4RequestSigner("transcribe", "us-west-2", cred_provider)
    assert signer.algorithm == AwsSigningAlgorithm.V4
    assert signer.signature_type == AwsSignatureType.HTTP_REQUEST_HEADERS

    request = Request(
        endpoint="https://transcribestreaming.amazonaws.com",
        path="/transcribe",
        method="HEAD",
        headers={"x-test-header": "test-transcribe-0.0.1"},
        body=BytesIO(b"Test body"),
        params={"test": "value"},
    ).prepare()

    assert request.headers == {"x-test-header": "test-transcribe-0.0.1"}
    request = signer.sign(request)
    assert "Authorization" in request.headers
    assert "X-Amz-Date" in request.headers
    assert "x-test-header" in request.headers
