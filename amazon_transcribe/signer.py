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


from typing import Optional

from awscrt.http import HttpHeaders, HttpRequest
from awscrt.auth import (
    AwsCredentialsProvider,
    AwsSigningAlgorithm,
    AwsSigningConfig,
    AwsSignatureType,
    AwsSignedBodyValue,
    AwsSignedBodyHeaderType,
    aws_sign_request,
)
from amazon_transcribe.auth import Credentials
from amazon_transcribe.request import PreparedRequest, HeadersDict
from amazon_transcribe.exceptions import CredentialsException


class RequestSigner:
    """General implementation for Request signing"""

    def __init__(self, service_name, region, algorithm=0, signature_type=0):
        self.service_name: str = service_name
        self.region: str = region
        self.algorithm: int = algorithm
        self.signature_type: int = signature_type

    def sign(
        self, request: PreparedRequest, credentials: Optional[Credentials]
    ) -> PreparedRequest:
        if credentials is None:
            raise CredentialsException("Failed to resolve credentials")
        alg = AwsSigningAlgorithm(self.algorithm)
        sig_type = AwsSignatureType(self.signature_type)

        credential_provider = AwsCredentialsProvider.new_static(
            credentials.access_key_id,
            credentials.secret_access_key,
            credentials.session_token,
        )

        config = AwsSigningConfig(
            algorithm=alg,
            signature_type=sig_type,
            credentials_provider=credential_provider,
            region=self.region,
            service=self.service_name,
            signed_body_value=AwsSignedBodyValue.EMPTY_SHA256,
            signed_body_header_type=AwsSignedBodyHeaderType.NONE,
        )
        crt_request = _convert_request(request)
        signed_request = aws_sign_request(crt_request, config).result()
        request.headers = HeadersDict(dict(signed_request.headers))

        return request


class SigV4RequestSigner(RequestSigner):
    def __init__(self, service_name, region):
        super().__init__(service_name, region)
        self.algorithm: int = AwsSigningAlgorithm.V4
        self.signature_type: int = AwsSignatureType.HTTP_REQUEST_HEADERS


def _convert_request(request: PreparedRequest) -> HttpRequest:
    return HttpRequest(
        method=request.method,
        path=request.path,
        headers=HttpHeaders(request.headers.as_list()),
        body_stream=request.body,
    )
