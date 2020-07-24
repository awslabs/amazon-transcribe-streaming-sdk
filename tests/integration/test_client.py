from io import BytesIO
import pytest

from transcribe.client import TranscribeStreamingClient
from transcribe.exceptions import BadRequestException


class TestClientStreaming:
    @pytest.fixture
    def client(self):
        return TranscribeStreamingClient("us-west-2")

    @pytest.mark.asyncio
    async def test_client_start_transcribe_stream(self, client):
        stream = await client.start_stream_transcription(
            language_code="en-US", media_sample_rate_hz=16000, media_encoding="pcm",
        )

        await stream.input_stream.send_audio_event(audio_chunk=b"test")
        await stream.input_stream.end_stream()

        async for event in stream.output_stream:
            pass

    @pytest.mark.asyncio
    async def test_client_start_transcribe_stream_bad_request(self, client):
        # The sample rate is too high
        with pytest.raises(BadRequestException):
            stream = await client.start_stream_transcription(
                language_code="en-US",
                media_sample_rate_hz=9999999,
                media_encoding="pcm",
            )
