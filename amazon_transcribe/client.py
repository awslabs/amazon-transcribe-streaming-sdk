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


import re
from binascii import unhexlify
from typing import Optional

from amazon_transcribe import AWSCRTEventLoop
from amazon_transcribe.auth import AwsCrtCredentialResolver, CredentialResolver
from amazon_transcribe.endpoints import (
    BaseEndpointResolver,
    _TranscribeRegionEndpointResolver,
)
from amazon_transcribe.eventstream import EventStreamMessageSerializer
from amazon_transcribe.eventstream import EventSigner
from amazon_transcribe.httpsession import AwsCrtHttpSessionManager
from amazon_transcribe.model import (
    AudioStream,
    StartStreamTranscriptionRequest,
    StartStreamTranscriptionEventStream,
)
from amazon_transcribe.serialize import (
    AudioEventSerializer,
    Serializer,
    TranscribeStreamingRequestSerializer,
)
from amazon_transcribe.deserialize import TranscribeStreamingResponseParser
from amazon_transcribe.signer import SigV4RequestSigner


def create_client(region="us-east-2", endpoint_resolver=None):
    """Helper function for easy default client setup"""
    return TranscribeStreamingClient(region=region, endpoint_resolver=endpoint_resolver)


class TranscribeStreamingClient:
    """High level client for orchestrating setup and transmission of audio
    streams to Amazon TranscribeStreaming service.
    """

    def __init__(self, *, region, endpoint_resolver=None, credential_resolver=None):
        if endpoint_resolver is None:
            endpoint_resolver = _TranscribeRegionEndpointResolver()
        self._endpoint_resolver: BaseEndpointResolver = endpoint_resolver
        self.service_name: str = "transcribe"
        self.region: str = region
        self._event_signer: EventSigner = EventSigner(self.service_name, self.region)
        self._eventloop = AWSCRTEventLoop().bootstrap
        if credential_resolver is None:
            credential_resolver = AwsCrtCredentialResolver(self._eventloop)
        self._credential_resolver: CredentialResolver = credential_resolver
        self._response_parser = TranscribeStreamingResponseParser()

    async def start_stream_transcription(
        self,
        *,
        language_code: str,
        media_sample_rate_hz: int,
        media_encoding: str,
        vocabulary_name: Optional[str] = None,
        session_id: Optional[str] = None,
        vocab_filter_method: Optional[str] = None,
    ) -> StartStreamTranscriptionEventStream:
        """Coordinate transcription settings and start stream."""
        transcribe_streaming_request = StartStreamTranscriptionRequest(
            language_code,
            media_sample_rate_hz,
            media_encoding,
            vocabulary_name,
            session_id,
            vocab_filter_method,
        )
        endpoint = await self._endpoint_resolver.resolve(self.region)
        self._serializer: Serializer = TranscribeStreamingRequestSerializer(
            endpoint=endpoint, transcribe_request=transcribe_streaming_request,
        )
        request = self._serializer.serialize_to_request()

        creds = await self._credential_resolver.get_credentials()
        signer = SigV4RequestSigner("transcribe", self.region)
        signed_request = signer.sign(request, creds)

        session = AwsCrtHttpSessionManager(self._eventloop)

        response = await session.make_request(
            signed_request.uri,
            method=signed_request.method,
            headers=signed_request.headers.as_list(),
            body=signed_request.body,
        )
        resolved_response = await response.resolve_response()

        status_code = resolved_response.status_code
        if status_code >= 400:
            # We need to close before we can consume the body or this will hang
            signed_request.body.close()
            body_bytes = await response.consume_body()
            raise self._response_parser.parse_exception(resolved_response, body_bytes)
        elif status_code != 200:
            raise RuntimeError("Unexpected status code encountered: %s" % status_code)

        parsed_response = self._response_parser.parse_start_stream_transcription_response(
            resolved_response, response,
        )

        # The audio stream is returned as output because it requires
        # the signature from the initial HTTP request to be useable
        audio_stream = self._create_audio_stream(signed_request)
        return StartStreamTranscriptionEventStream(audio_stream, parsed_response)

    def _create_audio_stream(self, signed_request):
        initial_signature = self._extract_signature(signed_request)
        return AudioStream(
            input_stream=signed_request.body,
            event_serializer=AudioEventSerializer(),
            eventstream_serializer=EventStreamMessageSerializer(),
            event_signer=self._event_signer,
            initial_signature=initial_signature,
            credential_resolver=self._credential_resolver,
        )

    def _extract_signature(self, signed_request):
        auth = signed_request.headers.get("Authorization", "")
        auth = re.split("Signature=", auth)[-1]
        return unhexlify(auth)
