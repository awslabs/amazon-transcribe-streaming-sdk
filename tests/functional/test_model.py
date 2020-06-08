import pytest

from transcribe import model


@pytest.fixture
def audio_stream():
    audio_event = model.AudioEvent(
        audio_chunk=b"test", event_payload=True, event=True
    )
    return model.AudioStream(audio_event, eventstream=True)


def test_StartStreamTranscriptionRequest_serialization(audio_stream):
    req = model.StartStreamTranscriptionRequest(
        language_code="en-US",
        media_sample_rate_hz=9000,
        media_encoding="pcm",
        audio_stream=audio_stream,
    )
    headers, body = req.serialize()

    assert headers["x-amzn-transcribe-language-code"] == "en-US"
    assert headers["x-amzn-transcribe-sample-rate"] == 9000
    assert headers["x-amzn-transcribe-media-encoding"] == "pcm"
    assert headers["x-amzn-transcribe-session-id"] is None
    assert body == audio_stream
