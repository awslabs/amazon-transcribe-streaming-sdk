from io import BytesIO
import pytest

from transcribe.client import TranscribeStreamingClient
from transcribe.model import AudioEvent, AudioStream


async def json_from_body(response):
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

        audio_event = AudioEvent(
            audio_chunk=b"test", event_payload=True, event=True
        )
        audio_stream = AudioStream(audio_event, eventstream=True)

        response = await client.start_transcribe_stream(
            language_code="en-US",
            media_sample_rate_hz=9000,
            media_encoding="pcm",
            audio_stream=audio_stream,
        )
        body = await json_from_body(response)
        headers = await response.headers
        status = await response.status_code
        assert status == 200
        assert (
            "content-type",
            "application/vnd.amazon.eventstream",
        ) in headers

        # TODO: Remove this once EventStreaming is in place.
        # This will validate we're actually reaching the service
        # with proper H2.
        assert (
            b"signal was sent without the preceding empty frame" in body.read()
        )
