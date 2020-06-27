from io import BytesIO
from unittest.mock import Mock

import pytest

from transcribe.exceptions import ValidationException
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


@pytest.fixture
def audio_stream():
    stream = AudioStream(event_serializer=AudioEventSerializer())
    stream.send_audio_event(b"test")
    return stream


@pytest.fixture
def request_serializer(audio_stream):
    req_shape = StartStreamTranscriptionRequest(
        language_code="en-US",
        media_sample_rate_hz=9000,
        media_encoding="pcm",
        audio_stream=audio_stream,
    )

    return TranscribeStreamingRequestSerializer(
        "https://transcribe.aws.com", req_shape
    )


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
        assert request.body.read() == (
            b"\x00\x00\x00f\x00\x00\x00R\xf65m\\\r:message_type\x07\x00\x05event\x0b:even"
            b"t_type\x07\x00\x04blob\r:content-type\x07\x00\x18application/octet-streamte"
            b"st\x8a\x9c\xb4Z"
        )

    def test_unprepared_serialization(self, request_serializer):
        request = request_serializer.serialize_to_request(prepare=False)

        assert request.headers["x-amzn-transcribe-language-code"] == "en-US"
        assert request.headers["x-amzn-transcribe-sample-rate"] == 9000
        assert request.headers["x-amzn-transcribe-media-encoding"] == "pcm"
        assert request.headers["x-amzn-transcribe-session-id"] is None
        assert request.headers["host"] == "transcribe.aws.com"
        assert "user-agent" in request.headers
        assert isinstance(request.body, BytesIO)
        assert request.body.read() == (
            b"\x00\x00\x00f\x00\x00\x00R\xf65m\\\r:message_type\x07\x00\x05event\x0b:even"
            b"t_type\x07\x00\x04blob\r:content-type\x07\x00\x18application/octet-streamte"
            b"st\x8a\x9c\xb4Z"
        )

    def test_serialization_with_missing_endpoint(self, request_serializer):
        request_serializer.endpoint = None
        with pytest.raises(ValidationException):
            request_serializer.serialize_to_request()
