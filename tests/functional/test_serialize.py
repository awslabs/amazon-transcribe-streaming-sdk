import pytest

from amazon_transcribe.exceptions import ValidationException
from amazon_transcribe.model import (
    AudioEvent,
    StartStreamTranscriptionRequest,
)
from amazon_transcribe.serialize import (
    AudioEventSerializer,
    TranscribeStreamingSerializer,
)
from amazon_transcribe.structures import BufferableByteStream


@pytest.fixture
def request_shape():
    return StartStreamTranscriptionRequest(
        language_code="en-US", media_sample_rate_hz=9000, media_encoding="pcm",
    )


class TestStartStreamTransactionRequest:
    def test_serialization(self, request_shape):
        request_serializer = TranscribeStreamingSerializer()
        request = request_serializer.serialize_start_stream_transcription_request(
            endpoint="https://transcribe.aws.com", request_shape=request_shape,
        ).prepare()

        assert request.headers["x-amzn-transcribe-language-code"] == "en-US"
        assert request.headers["x-amzn-transcribe-sample-rate"] == "9000"
        assert request.headers["x-amzn-transcribe-media-encoding"] == "pcm"
        assert request.headers["host"] == "transcribe.aws.com"
        assert "user-agent" in request.headers
        assert isinstance(request.body, BufferableByteStream)

    def test_serialization_with_missing_endpoint(self, request_shape):
        request_serializer = TranscribeStreamingSerializer()
        with pytest.raises(ValidationException):
            request_serializer.serialize_start_stream_transcription_request(
                endpoint=None, request_shape=request_shape,
            )


class TestAudioEventSerializer:
    def test_serialization(self):
        audio_event = AudioEvent(audio_chunk=b"foo")
        event_serializer = AudioEventSerializer()
        headers, payload = event_serializer.serialize(audio_event)
        expected_headers = {
            ":message-type": "event",
            ":event-type": "AudioEvent",
            ":content-type": "application/octet-stream",
        }
        assert headers == expected_headers
        assert payload == b"foo"
