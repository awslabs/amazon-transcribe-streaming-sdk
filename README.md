## Amazon Transcribe Streaming SDK

The Amazon Transcribe Streaming SDK allows users to directly interface with
the Amazon Transcribe Streaming service and their Python programs. The goal of
the project is to enable users to integrate directly with Amazon Transcribe
without needing anything more than a stream of audio bytes and a basic handler.

This project is still in early alpha so the interface is still subject to change
and may see rapid iteration. It's highly advised to pin to strict dependencies
if using this outside of local testing.


## Installation

To install from pip:
````bash
python -m pip install amazon-transcribe
````

To install from Github:
````bash
git clone https://github.com/awslabs/amazon-transcribe-streaming-sdk.git
cd amazon-transcribe-streaming-sdk
git submodule update --init
python -m pip install .
````

To use from your Python application, add `amazon-transcribe` as a dependency in your `requirements.txt` file.

NOTE: This SDK is built on top of the
[AWS Common Runtime (CRT)](https://github.com/awslabs/aws-crt-python), a collection of
C libraries we interact with through bindings. The CRT is available on PyPI
([awscrt](https://pypi.org/project/awscrt/)) as precompiled wheels for common platforms
(Linux, macOS, Windows). Non-standard operating systems may need to compile these
libraries themselves.

## Usage

Setup for this SDK will require either live or prerecorded audio. Full details
on the audio input requirements can be found in the [Amazon Transcribe Streaming
documentation](https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html).

Here's an example to get started:
```python
import asyncio
# This example uses aiofile for asynchronous file reads.
# It's not a dependency of the project but can be installed
# with `pip install aiofile`.
import aiofile

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

"""
Here's an example of a custom event handler you can extend to
process the returned transcription results as needed. This
handler will simply print the text out to your interpreter.
"""
class MyEventHandler(TranscriptResultStreamHandler):
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        # This handler can be implemented to handle audio as needed.
        # Here's an example to get started.
        results = transcript_event.transcript.results
        for result in results:
            for alt in result.alternatives:
                print(alt.transcript)


async def basic_transcribe():
    # Setup up our client with our chosen AWS region
    client = TranscribeStreamingClient("us-west-2")

    # Start transcription to generate our async stream
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )

    async def write_chunks():
        # An example file can be found at tests/integration/assets/test.wav
        async with aiofile.AIOFile('tests/integration/assets/test.wav', 'rb') as afp:
            reader = aiofile.Reader(afp, chunk_size=1024 * 16)
            async for chunk in reader:
                await stream.input_stream.send_audio_event(audio_chunk=chunk)
        await stream.input_stream.end_stream()

    asyncio.ensure_future(write_chunks())

    # Instantiae our handler and start processing events
    handler = MyEventHandler(stream.output_stream)
    await handler.handle_events()

loop = asyncio.get_event_loop()
loop.run_until_complete(basic_transcribe())
loop.close()
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
