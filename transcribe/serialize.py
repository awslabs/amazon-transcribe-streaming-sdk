from io import BytesIO
from typing import Dict, List, Union
from urllib.parse import urlsplit

from transcribe import __version__ as version
from transcribe.model import StartStreamTranscriptionRequest
from transcribe.exceptions import ValidationException
from transcribe.request import PreparedRequest, Request

REQUEST_TYPE = Union[Request, PreparedRequest]


class Serializer:
    def __init__(self, endpoint, method, request_uri, request_shape):
        self.endpoint: str = endpoint
        self.method: str = method
        self.request_uri: str = request_uri
        self.request_shape: RequestShape = request_shape

    def serialize_to_request(self, prepare=True) -> REQUEST_TYPE:
        """Serialize parameters into an HTTP request."""
        raise NotImplementedError("serialize_to_request")

    def _add_required_headers(self, headers: Dict[str, str]):
        urlparts = urlsplit(self.endpoint)
        if not urlparts.hostname:
            raise ValidationException(
                "Unexpected endpoint ({self.endpoint}) provided to serializer"
            )
        headers.update(
            {
                "user-agent": f"transcribe-streaming-sdk-{version}",
                "host": urlparts.hostname,
            }
        )


class TranscribeStreamingRequestSerializer(Serializer):
    """Convert StartStreamTranscriptionRequest into a
    Request object for streaming to the Transcribe service.
    """

    def __init__(self, endpoint, transcribe_request):
        self.endpoint: str = endpoint
        self.method: str = "POST"
        self.request_uri: str = "/stream-transcription"
        self.request_shape: StartStreamTranscriptionRequest = transcribe_request

    def serialize_to_request(self, prepare=True) -> REQUEST_TYPE:
        headers = {
            "x-amzn-transcribe-language-code": self.request_shape.language_code,
            "x-amzn-transcribe-sample-rate": self.request_shape.media_sample_rate_hz,
            "x-amzn-transcribe-media-encoding": self.request_shape.media_encoding,
            "x-amzn-transcribe-vocabulary-name": self.request_shape.vocabulary_name,
            "x-amzn-transcribe-session-id": self.request_shape.session_id,
            "x-amzn-transcribe-vocabulary-filter-method": self.request_shape.vocab_filter_method,
        }
        self._add_required_headers(headers)

        # TODO: We need to resolve how the model goes from AudioStream ->
        # EventStream -> Bytes
        body = BytesIO(self.request_shape.audio_stream.audio_event.audio_chunk)

        request = Request(
            endpoint=self.endpoint,
            path=self.request_uri,
            method=self.method,
            headers=headers,
            body=body,
        )
        if prepare:
            return request.prepare()
        return request
