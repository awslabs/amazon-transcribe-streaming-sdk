import asyncio

import pytest

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.exceptions import BadRequestException, SerializationException
from amazon_transcribe.model import TranscriptEvent
from tests.integration import TEST_WAV_PATH


class TestClientStreaming:
    @pytest.fixture
    def client(self):
        return TranscribeStreamingClient(region="us-west-2")

    @pytest.fixture
    def wav_bytes(self):
        with open(TEST_WAV_PATH, "rb") as f:
            raw_bytes = f.read()
        # This simulates reading bytes from some asynchronous source
        # This could be coming from an async file, microphone, etc

        async def byte_generator():
            chunk_size = 1024 * 4
            for i in range(0, len(raw_bytes), chunk_size):
                yield raw_bytes[i : i + chunk_size]
                await asyncio.sleep(0.1)

        return byte_generator

    @pytest.mark.asyncio
    async def test_client_start_transcribe_stream(self, client, wav_bytes):
        stream = await client.start_stream_transcription(
            language_code="en-US",
            media_sample_rate_hz=16000,
            media_encoding="pcm",
        )

        async for chunk in wav_bytes():
            await stream.input_stream.send_audio_event(audio_chunk=chunk)
        await stream.input_stream.end_stream()

        last_transcript = ""
        async for event in stream.output_stream:
            if not isinstance(event, TranscriptEvent):
                continue
            results = event.transcript.results
            for result in results:
                for alt in result.alternatives:
                    last_transcript = alt.transcript
        # Assert that we got some words back as the service may change its response
        assert len(last_transcript.split(" ")) != 0

    @pytest.mark.asyncio
    async def test_client_start_transcribe_stream_bad_request(self, client):
        # The sample rate is too high
        with pytest.raises(BadRequestException):
            await client.start_stream_transcription(
                language_code="en-US",
                media_sample_rate_hz=9999999,
                media_encoding="pcm",
            )

    @pytest.mark.asyncio
    async def test_start_transcribe_stream_bad_boolean_show_speaker_lab(self, client):
        with pytest.raises(SerializationException):
            await client.start_stream_transcription(
                language_code="en-US",
                media_sample_rate_hz=16000,
                media_encoding="pcm",
                show_speaker_label="foo",
                enable_channel_identification=True,
            )
