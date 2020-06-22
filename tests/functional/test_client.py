import pytest

from transcribe.client import TranscribeStreamingClient, create_client
from transcribe.endpoints import StaticEndpointResolver
from transcribe.exceptions import ValidationException


class TestClient:
    @pytest.mark.asyncio
    async def test_start_transcribe_stream_without_stream(self):
        client = TranscribeStreamingClient("us-west-2")
        with pytest.raises(ValidationException):
            await client.start_transcribe_stream(
                language_code="US-en",
                media_sample_rate_hz=9000,
                media_encoding="pcm",
                audio_stream=None,
            )
