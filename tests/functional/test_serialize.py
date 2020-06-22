from io import BytesIO
from unittest.mock import Mock

import pytest

from transcribe.exceptions import ValidationException
from transcribe.model import AudioEvent, AudioStream, StartStreamTranscriptionRequest
from transcribe.serialize import Serializer, TranscribeStreamingRequestSerializer


@pytest.fixture
def audio_stream():
    audio_event = AudioEvent(audio_chunk=b"test", event_payload=True, event=True)
    return AudioStream(audio_event, eventstream=True)


@pytest.fixture
def request_serializer(audio_stream):
    req_shape = StartStreamTranscriptionRequest(
        language_code="en-US",
        media_sample_rate_hz=9000,
        media_encoding="pcm",
        audio_stream=audio_stream,
    )

    return TranscribeStreamingRequestSerializer("https://transcribe.aws.com", req_shape)


@pytest.fixture
def default_serializer():
    request_shape = Mock()
    endpoint = "https://transcribe.aws.com"
    return Serializer(endpoint, "POST", "/", request_shape)


class TestSerializer:
    def test_serializer(self, default_serializer):
        assert default_serializer.endpoint == "https://transcribe.aws.com"
        assert default_serializer.method == "POST"
        assert default_serializer.request_uri == "/"
        assert default_serializer.request_shape is not None

    def test_serialize_to_request(self, default_serializer):
        with pytest.raises(NotImplementedError):
            default_serializer.serialize_to_request()


class TestStartStreamTransactionRequest:
    def test_serialization(self, request_serializer):
        request = request_serializer.serialize_to_request()

        assert request.headers["x-amzn-transcribe-language-code"] == "en-US"
        assert request.headers["x-amzn-transcribe-sample-rate"] == "9000"
        assert request.headers["x-amzn-transcribe-media-encoding"] == "pcm"
        assert request.headers["x-amzn-transcribe-session-id"] is None
        assert request.headers["host"] == "transcribe.aws.com"
        assert "user-agent" in request.headers
        assert isinstance(request.body, BytesIO)
        assert request.body.read() == b"test"

    def test_unprepared_serialization(self, request_serializer):
        request = request_serializer.serialize_to_request(prepare=False)

        assert request.headers["x-amzn-transcribe-language-code"] == "en-US"
        assert request.headers["x-amzn-transcribe-sample-rate"] == 9000
        assert request.headers["x-amzn-transcribe-media-encoding"] == "pcm"
        assert request.headers["x-amzn-transcribe-session-id"] is None
        assert request.headers["host"] == "transcribe.aws.com"
        assert "user-agent" in request.headers
        assert isinstance(request.body, BytesIO)
        assert request.body.read() == b"test"

    def test_serialization_with_missing_endpoint(self, request_serializer):
        request_serializer.endpoint = None
        with pytest.raises(ValidationException):
            request_serializer.serialize_to_request()
