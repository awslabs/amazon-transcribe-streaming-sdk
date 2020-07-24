import pytest

from mock import Mock
from transcribe.auth import StaticCredentialResolver
from transcribe.model import AudioStream
from transcribe.serialize import AudioEventSerializer
from transcribe.structures import BufferableByteStream
from transcribe.eventstream import EventSigner, EventStreamBuffer


@pytest.fixture
def request_body():
    return BufferableByteStream()


@pytest.fixture
def default_credential_resolver():
    return StaticCredentialResolver("test", "53cr37", "12345")


@pytest.fixture
def event_signer():
    return EventSigner("signing-name", "region-name")


@pytest.fixture
def audio_stream(request_body, event_signer, default_credential_resolver):
    return AudioStream(
        input_stream=request_body,
        event_serializer=AudioEventSerializer(),
        event_signer=event_signer,
        initial_signature=b"firstsig",
        credential_resolver=default_credential_resolver,
    )


class TestAudioStream:
    @pytest.mark.asyncio
    async def test_audio_stream_writes_to_body(
        self, audio_stream, request_body
    ):
        await audio_stream.send_audio_event(audio_chunk=b"notaudio")
        buffer = EventStreamBuffer()
        # Assert the 'outer' signed event looks right
        buffer.add_data(request_body.read())
        signed_event = next(buffer)
        assert ":date" in signed_event.headers
        assert ":chunk-signature" in signed_event.headers
        # Assert the 'inner' raw event sent looks right
        buffer.add_data(signed_event.payload)
        audio_event = next(buffer)
        assert audio_event.payload == b"notaudio"
        assert audio_event.headers[":event-type"] == "AudioEvent"
        assert audio_event.headers[":message-type"] == "event"
        assert (
            audio_event.headers[":content-type"] == "application/octet-stream"
        )
