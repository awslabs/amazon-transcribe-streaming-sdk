from io import BytesIO

from awscrt.auth import (
    AwsSigningAlgorithm,
    AwsSignatureType,
)

from awscrt.http import HttpRequest
import pytest

from amazon_transcribe.auth import StaticCredentialResolver
from amazon_transcribe.request import Request
from amazon_transcribe.signer import (
    RequestSigner,
    SigV4RequestSigner,
    _convert_request,
)
from amazon_transcribe.exceptions import CredentialsException


@pytest.fixture
def default_credential_resolver():
    return StaticCredentialResolver("test", "53cr37", "12345")


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
    assert dict(crt_req.headers) == dict([("User-Agent", "test-transcribe-0.0.1")])
    assert crt_req.body_stream is not None


def test_default_request_signer(default_credential_resolver):
    signer = RequestSigner("transcribe", "us-west-2")

    request = Request(
        endpoint="https://transcribestreaming.amazonaws.com",
        path="/transcribe",
        method="HEAD",
        headers={"x-test-header": "test-transcribe-0.0.1"},
        body=BytesIO(b"Test body"),
        params={"test": "value"},
    ).prepare()

    assert request.headers == {"x-test-header": "test-transcribe-0.0.1"}
    request = signer.sign(request, default_credential_resolver)
    assert "Authorization" in request.headers
    assert "X-Amz-Date" in request.headers


def test_sigv4_request_signer(default_credential_resolver):
    signer = SigV4RequestSigner("transcribe", "us-west-2")
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
    request = signer.sign(request, default_credential_resolver)
    assert "Authorization" in request.headers
    assert "X-Amz-Date" in request.headers
    assert "x-test-header" in request.headers


def test_sigv4_request_signer_handles_no_credentials():
    signer = SigV4RequestSigner("transcribe", "us-west-2")
    request = Request(
        endpoint="https://transcribestreaming.amazonaws.com",
    ).prepare()
    with pytest.raises(CredentialsException):
        signer.sign(request, None)
