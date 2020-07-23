import os
import re
from binascii import unhexlify

from transcribe import AWSCRTEventLoop
from transcribe.auth import AwsCrtCredentialResolver, CredentialResolver
from transcribe.endpoints import (
    BaseEndpointResolver,
    _TranscribeRegionEndpointResolver,
)
from transcribe.eventstream import EventStreamMessageSerializer
from transcribe.eventstream import EventSigner
from transcribe.exceptions import ValidationException
from transcribe.httpsession import AwsCrtHttpSessionManager
from transcribe.model import (
    AudioEvent,
    AudioStream,
    StartStreamTranscriptionRequest,
)
from transcribe.serialize import (
    AudioEventSerializer,
    Serializer,
    TranscribeStreamingRequestSerializer,
)
from transcribe.signer import SigV4RequestSigner


def create_client(region="us-east-2", endpoint_resolver=None):
    """Helper function for easy default client setup"""
    return TranscribeStreamingClient(region, endpoint_resolver)


# TODO unjank credentials
def create_default_event_signer(region: str) -> EventSigner:
    """Helper function for simple SigV4 signing"""
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    session_token = os.environ.get("AWS_SESSION_TOKEN")
    from collections import namedtuple

    Credentials = namedtuple(
        "Creds", ["access_key", "secret_key", "session_token"]
    )
    creds = Credentials(access_key, secret_key, session_token)
    return EventSigner("transcribe", region, creds)


class TranscribeStreamingClient:
    """High level client for orchestrating setup and transmission of audio
    streams to Amazon TranscribeStreaming service.
    """

    def __init__(
        self,
        region,
        endpoint_resolver=None,
        credential_resolver=None
    ):
        if endpoint_resolver is None:
            endpoint_resolver = _TranscribeRegionEndpointResolver()
        self._endpoint_resolver: BaseEndpointResolver = endpoint_resolver
        self.service_name: str = "transcribe"
        self.region: str = region
        self._event_signer: EventSigner = create_default_event_signer(self.region)
        self._eventloop = AWSCRTEventLoop().bootstrap
        if credential_resolver is None:
            credential_resolver = AwsCrtCredentialResolver(self._eventloop)
        self._credential_resolver = credential_resolver

    async def start_transcribe_stream(
        self,
        language_code: str = None,
        media_sample_rate_hz: int = None,
        media_encoding: str = None,
        vocabulary_name: str = None,
        session_id: str = None,
        vocab_filter_method: str = None,
    ):
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
        self._serializer = TranscribeStreamingRequestSerializer(
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

        # The audio stream is returned as output because it requires
        # the signature from the initial HTTP request to be useable
        audio_stream = self._create_audio_stream(signed_request)

        return audio_stream, response

    def _create_audio_stream(self, signed_request):
        initial_signature = self._extract_signature(signed_request)
        return AudioStream(
            input_stream=signed_request.body,
            event_serializer=AudioEventSerializer(),
            eventstream_serializer=EventStreamMessageSerializer(),
            event_signer=self._event_signer,
            initial_signature=initial_signature,
        )

    def _extract_signature(self, signed_request):
        auth = signed_request.headers.get("Authorization", "")
        auth = re.split("Signature=", auth)[-1]
        return unhexlify(auth)
