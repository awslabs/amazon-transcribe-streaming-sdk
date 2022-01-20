import asyncio
import json
import sys
# This example uses aiofile for asynchronous file reads.
# It's not a dependency of the project but can be installed
# with `pip install aiofile`.
import wave
from typing import Optional

import aiofile
from awscrt.auth import AwsCredentialsProvider

from amazon_transcribe import AWSCRTEventLoop
from amazon_transcribe.auth import CredentialResolver, Credentials
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent


class MyCustomCredentialResolver(CredentialResolver):
    def __init__(self, eventloop):
        self._crt_resolver = AwsCredentialsProvider.new_default_chain(eventloop)
        self.credentials = None

    async def get_credentials(self) -> Optional[Credentials]:
        if self.credentials is None:
            self.credentials = await asyncio.wrap_future(self._crt_resolver.get_credentials())
        return self.credentials


async def parse_int(file, byte_length=4):
    chunk = await file.read(byte_length)
    return int.from_bytes(chunk, 'little')


async def rate_limit(file, byte_rate):
    chunk = await file.read(byte_rate)
    loop = asyncio.get_event_loop()
    last_yield_time = -1.0  # -1 to allow the first yield immediately
    while chunk:
        time_since_last_yield = loop.time() - last_yield_time
        if time_since_last_yield < 1.0:
            # Only yield once per second at most, compensating for how long
            # between the last yield it's been
            await asyncio.sleep(1.0 - time_since_last_yield)
        last_yield_time = loop.time()
        yield chunk
        chunk = await file.read(byte_rate)


class MyEventHandler(TranscriptResultStreamHandler):
    """
    Here's an example of a custom event handler you can extend to
    process the returned transcription results as needed. This
    handler will simply print the text out to your interpreter.
    """
    
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        # This handler can be implemented to handle transcriptions as needed.
        # Here's an example to get started.
        results = transcript_event.transcript.results
        for result in results:
            if result.is_partial:
                # we only want final transcription for sentences
                continue
            for alt in result.alternatives:
                alternatives = result.alternatives[0]
                transcript = alternatives.transcript
                items = list(map(lambda x: {
                    "vocabulary_filter_match": x.vocabulary_filter_match,
                    "start_time": x.start_time,
                    "stable": x.stable,
                    "speaker": x.speaker,
                    "item_type": x.item_type,
                    "end_time": x.end_time,
                    "content": x.content,
                    "confidence": x.confidence
                }, alternatives.items))

                print(json.dumps({"alternatives": {"transcript": transcript, "items": items}}))


target_file = (len(sys.argv) > 1 and sys.argv[1]) or "tests/integration/assets/test.wav"

with wave.open(target_file, "rb") as wave_file:
    frames = wave_file.getnframes()
    sample_rate_hertz = wave_file.getframerate()
    bits_per_sample = wave_file.getsampwidth()
    num_channels = wave_file.getnchannels()
    duration = frames / float(sample_rate_hertz)
    byte_rate = int((sample_rate_hertz * bits_per_sample * num_channels) / 8)
    assert byte_rate == (sample_rate_hertz * bits_per_sample * num_channels) / 8

aws_event_loop = AWSCRTEventLoop().bootstrap


async def basic_transcribe(filepath):
    # Setup up our client with our chosen AWS region
    client = TranscribeStreamingClient(region="us-west-2",
                                       credential_resolver=MyCustomCredentialResolver(
                                           aws_event_loop))

    async def write_chunks(_stream, _f, _byte_rate):
        async for chunk in rate_limit(_f, _byte_rate):
            await _stream.input_stream.send_audio_event(audio_chunk=chunk)
        await _stream.input_stream.end_stream()

    async with aiofile.async_open(filepath, 'rb') as f:
        # Start transcription to generate our async stream
        stream = await client.start_stream_transcription(
            language_code="en-US",
            media_sample_rate_hz=sample_rate_hertz,
            media_encoding="pcm",
        )

        # Instantiate our handler and start processing events
        await asyncio.gather(
            write_chunks(stream, f, byte_rate),
            MyEventHandler(stream.output_stream).handle_events(),
        )


loop = asyncio.get_event_loop()
loop.run_until_complete(basic_transcribe(target_file))
loop.close()
