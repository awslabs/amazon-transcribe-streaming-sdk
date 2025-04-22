import asyncio
import pytest

from amazon_transcribe.model import TranscriptEvent
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.exceptions import (
    BadRequestException,
    SerializationException,
)
from tests.integration import TEST_WAV_PATH, TEST_WAV_PII_PATH

request_options = [
    # plain request with a known language
    {"language_code": "en-US"},
    # language identification
    {
        "language_code": None,
        "identify_language": True,
        "language_options": ["en-US", "de-DE"],
        "preferred_language": "en-US",
    },
    # multiple language identification
    {
        "language_code": None,
        "identify_multiple_languages": True,
        "language_options": ["en-US", "de-DE"],
        "vocab_filter_names": ["english", "german"],
    },
    # PII identification
    {
        "language_code": "en-US",
        "pii_entity_types": ["NAME", "ADDRESS"],
        "content_identification_type": "PII",
    },
    # PII redaction
    {
        "language_code": "en-US",
        "pii_entity_types": ["ALL"],
        "content_redaction_type": "PII",
    },
]


class TestClientStreaming:
    @pytest.fixture
    def client(self):
        return TranscribeStreamingClient(region="us-west-2")

    def wav_bytes(self, audio_file: str):
        with open(audio_file, "rb") as f:
            raw_bytes = f.read()
        # This simulates reading bytes from some asynchronous source
        # This could be coming from an async file, microphone, etc

        async def byte_generator():
            chunk_size = 1024 * 4
            for i in range(0, len(raw_bytes), chunk_size):
                yield raw_bytes[i : i + chunk_size]
                await asyncio.sleep(0.1)

        return byte_generator()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("request_args", request_options)
    @pytest.mark.parametrize("audio_path", [TEST_WAV_PATH, TEST_WAV_PII_PATH])
    async def test_client_start_transcribe_stream(
        self, client, audio_path, request_args
    ):
        stream = await client.start_stream_transcription(
            media_sample_rate_hz=16000, media_encoding="pcm", **request_args
        )

        async for chunk in self.wav_bytes(audio_path):
            await stream.input_stream.send_audio_event(audio_chunk=chunk)
        await stream.input_stream.end_stream()

        last_transcript = ""
        is_pii_identification = "content_identification_type" in request_args
        is_pii_redaction = "content_redaction_type" in request_args
        is_pii = is_pii_identification or is_pii_redaction
        entities = []
        async for event in stream.output_stream:
            if not isinstance(event, TranscriptEvent):
                continue
            results = event.transcript.results
            for result in results:
                for alt in result.alternatives:
                    print(alt.transcript)
                    last_transcript = alt.transcript
                    if is_pii:
                        if alt.entities:
                            entities.append(alt.entities)
                    else:
                        assert alt.entities is None
                if "identify_multiple_languages" in request_args:
                    assert result.language_code in request_args["language_options"]
        # Assert that we got some words back as the service may change its response
        assert len(last_transcript.split(" ")) != 0
        if is_pii and audio_path == TEST_WAV_PII_PATH:
            assert entities  # at least one entity was found
            if is_pii_redaction:
                assert "[NAME]" in last_transcript  # then entity is redacted
            if is_pii_identification:
                assert "Steven" in last_transcript  # then entity is NOT redacted

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

    @pytest.mark.asyncio
    async def test_client_start_transcribe_stream_bad_request_pii_redaction(
        self, client
    ):
        # PII redaction AND identification cannot both be set in the same request
        with pytest.raises(BadRequestException):
            await client.start_stream_transcription(
                language_code="en-US",
                media_sample_rate_hz=16000,
                media_encoding="pcm",
                pii_entity_types=["ALL"],
                content_identification_type="PII",
                content_redaction_type="PII",
            )
