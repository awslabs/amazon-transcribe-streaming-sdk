import os

from transcribe.endpoints import (
    BaseEndpointResolver,
    _TranscribeRegionEndpointResolver,
)
from transcribe.exceptions import ValidationException
from transcribe.httpsession import AwsCrtHttpSessionManager
from transcribe.model import AudioEvent, StartStreamTranscriptionRequest
from transcribe.serialize import (
    Serializer,
    TranscribeStreamingRequestSerializer,
)
from transcribe.signer import CredentialsProvider, SigV4RequestSigner


def create_client(region="us-east-2", endpoint_resolver=None):
    """Helper function for easy default client setup"""
    return TranscribeStreamingClient(region, endpoint_resolver)


def create_default_signer(region):
    """Helper function for simple SigV4 signing"""
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    session_token = os.environ.get("AWS_SESSION_TOKEN")
    cred_provider = CredentialsProvider().get_provider(
        access_key, secret_key, session_token
    )

    return SigV4RequestSigner("transcribe", region, cred_provider)


class TranscribeStreamingClient:
    """High level client for orchestrating setup and transmission of audio
    streams to Amazon TranscribeStreaming service.
    """

    def __init__(
        self, region, endpoint_resolver=None, serializer=None, signer=None,
    ):
        if endpoint_resolver is None:
            endpoint_resolver = _TranscribeRegionEndpointResolver()
        self._endpoint_resolver: BaseEndpointResolver = endpoint_resolver
        self.service_name: str = "transcribe"
        self.region: str = region
        self._serializer: Optional[Serializer] = serializer
        self._signer: Optional[RequestSigner] = signer

    async def start_transcribe_stream(
        self,
        language_code: str = None,
        media_sample_rate_hz: int = None,
        media_encoding: str = None,
        audio_stream: str = None,
        vocabulary_name: str = None,
        session_id: str = None,
        vocab_filter_method: str = None,
    ):
        """Coordinate transcription settings and start stream."""
        if audio_stream is None:
            raise ValidationException(
                "Stream started without a valid AudioStream. Aborting."
            )

        transcribe_streaming_request = StartStreamTranscriptionRequest(
            language_code,
            media_sample_rate_hz,
            media_encoding,
            audio_stream,
            vocabulary_name,
            session_id,
            vocab_filter_method,
        )
        endpoint = await self._endpoint_resolver.resolve(self.region)
        if self._serializer is None:
            self._serializer = TranscribeStreamingRequestSerializer(
                endpoint=endpoint,
                transcribe_request=transcribe_streaming_request,
            )

        request = self._serializer.serialize_to_request()

        if self._signer is None:
            self._signer = create_default_signer(self.region)

        signed_request = self._signer.sign(request)

        session = AwsCrtHttpSessionManager()

        response = await session.make_request(
            signed_request.uri,
            method=signed_request.method,
            headers=signed_request.headers.as_list(),
            body=signed_request.body,
        )
        return response
