from io import BytesIO
import pytest

from transcribe.client import TranscribeStreamingClient


async def exhaust_body(response, stream):
    response_body = BytesIO()
    while True:
        chunk = await response.get_chunk()
        if chunk:
            response_body.write(chunk)
        else:
            break
    response_body.seek(0)
    return response_body


class TestClientStreaming:
    @pytest.mark.asyncio
    async def test_client_start_transcribe_stream(self):
        client = TranscribeStreamingClient("us-west-2")

        audio_stream, response = await client.start_transcribe_stream(
            language_code="en-US", media_sample_rate_hz=16000, media_encoding="pcm",
        )

        await audio_stream.send_audio_event(audio_chunk=b"test")
        await audio_stream.end_stream()

        body = await exhaust_body(response, audio_stream)
        headers = await response.headers
        status = await response.status_code
        assert status == 200
        assert ("content-type", "application/vnd.amazon.eventstream",) in headers

        # The stream should have returned no events and end cleanly
        assert not body.read()
