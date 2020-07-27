import asyncio
from unittest.mock import Mock

import pytest

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.model import StartStreamTranscriptionEventStream
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from tests.integration import TEST_WAV_PATH


class TestEventHandler:
    CHUNK_SIZE = 10 * 1024

    class ExampleStreamHandler(TranscriptResultStreamHandler):
        def __init__(self, *args):
            super().__init__(*args)
            self.result_holder = []

        async def handle_transcript_event(self, transcript_event):
            self.result_holder.append(transcript_event)

    @pytest.fixture
    def chunks(self):
        wav_chunks = []
        with open(TEST_WAV_PATH, "rb") as f:
            chunk = f.read(self.CHUNK_SIZE)
            while chunk:
                wav_chunks.append(chunk)
                chunk = f.read(self.CHUNK_SIZE)
            assert len(wav_chunks) > 0
        return wav_chunks

    @pytest.mark.asyncio
    async def test_base_transcribe_handler(self, chunks):
        client = TranscribeStreamingClient(region="us-west-2")

        stream = await client.start_stream_transcription(
            language_code="en-US", media_sample_rate_hz=16000, media_encoding="pcm",
        )

        async def write_chunks():
            for chunk in chunks:
                await stream.input_stream.send_audio_event(audio_chunk=chunk)
            await stream.input_stream.end_stream()

        write_task = asyncio.ensure_future(write_chunks())
        handler = TranscriptResultStreamHandler(stream.output_stream)
        with pytest.raises(NotImplementedError):
            await asyncio.gather(handler.handle_events(), write_task)

    @pytest.mark.asyncio
    async def test_extended_transcribe_handler(self, chunks):
        client = TranscribeStreamingClient(region="us-west-2")

        stream = await client.start_stream_transcription(
            language_code="en-US", media_sample_rate_hz=16000, media_encoding="pcm",
        )

        async def write_chunks():
            for chunk in chunks:
                await stream.input_stream.send_audio_event(audio_chunk=chunk)
            await stream.input_stream.end_stream()

        write_task = asyncio.ensure_future(write_chunks())
        handler = self.ExampleStreamHandler(stream.output_stream)
        await asyncio.gather(handler.handle_events(), write_task)
        assert len(handler.result_holder) > 0
