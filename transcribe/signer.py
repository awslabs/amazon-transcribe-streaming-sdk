from io import BytesIO

from awscrt.http import HttpHeaders, HttpRequest
from awscrt.auth import (
    AwsCredentialsProvider,
    AwsSigningAlgorithm,
    AwsSigningConfig,
    AwsSignatureType,
    AwsSignedBodyValueType,
    AwsSignedBodyHeaderType,
    aws_sign_request,
)
from transcribe.request import PreparedRequest, HeadersDict


class CredentialsProvider:
    def __init__(self):
        self._provider = AwsCredentialsProvider

    def get_provider(
        self, access_key_id: str, secret_access_key: str, session_token=None
    ):
        return self._provider.new_static(
            access_key_id, secret_access_key, session_token
        )


class RequestSigner:
    """General implementation for Request signing"""

    def __init__(
        self, service_name, region, credentials, algorithm=0, signature_type=0
    ):
        self.service_name: str = service_name
        self.region: str = region
        self.credentials: CredentialProvider = credentials
        self.algorithm: int = algorithm
        self.signature_type: int = signature_type

    def sign(self, request: PreparedRequest) -> PreparedRequest:
        alg = AwsSigningAlgorithm(self.algorithm)
        sig_type = AwsSignatureType(self.signature_type)

        config = AwsSigningConfig(
            algorithm=alg,
            signature_type=sig_type,
            credentials_provider=self.credentials,
            region=self.region,
            service=self.service_name,
            signed_body_value_type=AwsSignedBodyValueType.EMPTY,
            signed_body_header_type=AwsSignedBodyHeaderType.NONE,
        )
        crt_request = _convert_request(request)
        signed_request = aws_sign_request(crt_request, config).result()
        request.headers = HeadersDict(dict(signed_request.headers))

        return request


class SigV4RequestSigner(RequestSigner):
    def __init__(self, service_name, region, credentials):
        super().__init__(service_name, region, credentials)
        self.algorithm: int = AwsSigningAlgorithm.V4
        self.signature_type: int = AwsSignatureType.HTTP_REQUEST_HEADERS


def _convert_request(request: PreparedRequest) -> HttpRequest:
    return HttpRequest(
        method=request.method,
        path=request.path,
        headers=HttpHeaders(request.headers.as_list()),
        body_stream=request.body,
    )
