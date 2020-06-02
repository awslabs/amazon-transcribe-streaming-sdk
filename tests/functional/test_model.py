import pytest

from transcribe import model


@pytest.fixture
def audio_stream():
    audio_chunk = model.AudioChunk(b"test")
    audio_event = model.AudioEvent(audio_chunk, True, True)
    return model.AudioStream(audio_event, True)


def test_StartStreamTranscriptionRequest_serialization(audio_stream):
    lang_code = model.LanguageCode("en-US")
    sample_rate = model.MediaSampleRateHertz(9000)
    encoding = model.MediaEncoding("pcm")
    req = model.StartStreamTranscriptionRequest(
        lang_code, sample_rate, encoding, audio_stream
    )
    headers, body = req.serialize()

    assert headers["x-amzn-transcribe-language-code"] == "en-US"
    assert headers["x-amzn-transcribe-sample-rate"] == 9000
    assert headers["x-amzn-transcribe-media-encoding"] == "pcm"
    assert headers["x-amzn-transcribe-session-id"] is None
    assert body == audio_stream
