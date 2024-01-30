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
        language_code="en-US",
        media_sample_rate_hz=9000,
        media_encoding="pcm",
    )


@pytest.fixture
def multi_lid_request():
    return StartStreamTranscriptionRequest(
        language_code=None,
        media_sample_rate_hz=9000,
        media_encoding="pcm",
        identify_multiple_languages=True,
        language_options=["en-US", "de-DE"]
    )


request_serializer = TranscribeStreamingSerializer()

class TestStartStreamTransactionRequest:
    def test_serialization(self, request_shape):
        request = request_serializer.serialize_start_stream_transcription_request(
            endpoint="https://transcribe.aws.com",
            request_shape=request_shape,
        ).prepare()

        assert request.headers["x-amzn-transcribe-language-code"] == "en-US"
        assert request.headers["x-amzn-transcribe-sample-rate"] == "9000"
        assert request.headers["x-amzn-transcribe-media-encoding"] == "pcm"
        assert request.headers["host"] == "transcribe.aws.com"
        assert "user-agent" in request.headers
        assert isinstance(request.body, BufferableByteStream)

    def test_serialization_with_missing_endpoint(self, request_shape):
        with pytest.raises(ValidationException):
            request_serializer.serialize_start_stream_transcription_request(
                endpoint=None,
                request_shape=request_shape,
            )


    def test_serialization_with_multi_lid(self, multi_lid_request):
        request = request_serializer.serialize_start_stream_transcription_request(
            endpoint="https://transcribe.aws.com",
            request_shape=multi_lid_request,
        ).prepare()

        assert "x-amzn-transcribe-language-code" not in request.headers
        assert request.headers["x-amzn-transcribe-sample-rate"] == "9000"
        assert request.headers["x-amzn-transcribe-media-encoding"] == "pcm"
        assert request.headers["x-amzn-transcribe-identify-multiple-languages"] == "True"
        assert request.headers["x-amzn-transcribe-language-options"] == "en-US,de-DE"


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
