import pytest
from io import BytesIO

from transcribe.model import AudioEvent, AudioStream, StartStreamTranscriptionRequest
from transcribe.serialize import TranscribeStreamingRequestSerializer


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


class TestStartStreamTransactionRequest:
    def test_serialization(self, request_serializer):
        request = request_serializer.serialize_to_request()

        assert request.headers["x-amzn-transcribe-language-code"] == "en-US"
        assert request.headers["x-amzn-transcribe-sample-rate"] == "9000"
        assert request.headers["x-amzn-transcribe-media-encoding"] == "pcm"
        assert request.headers["x-amzn-transcribe-session-id"] is None
        assert isinstance(request.body, BytesIO)
        assert request.body.read() == b"test"

    def test_unprepared_serialization(self, request_serializer):
        request = request_serializer.serialize_to_request(prepare=False)

        assert request.headers["x-amzn-transcribe-language-code"] == "en-US"
        assert request.headers["x-amzn-transcribe-sample-rate"] == 9000
        assert request.headers["x-amzn-transcribe-media-encoding"] == "pcm"
        assert request.headers["x-amzn-transcribe-session-id"] is None
        assert isinstance(request.body, BytesIO)
        assert request.body.read() == b"test"
