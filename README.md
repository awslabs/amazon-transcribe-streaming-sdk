## Amazon Transcribe Streaming SDK

The Amazon Transcribe Streaming SDK allows users to directly interface with
the Amazon Transcribe Streaming service and their Python programs. The goal of
the project is to enable users to integrate directly with Amazon Transcribe
without needing anything more than a stream of audio bytes and a basic handler.

This project is still in early alpha so the interface is still subject to change
and may see rapid iteration. It's highly advised to pin to strict dependencies
if using this outside of local testing. Please note awscrt is a dependency shared
with botocore (the core module of AWS CLI and boto3). You may need to keep
amazon-transcribe at the latest version when installed in the same environment.


## Installation

To install from pip:
````bash
python -m pip install amazon-transcribe
````

To install from Github:
````bash
git clone https://github.com/awslabs/amazon-transcribe-streaming-sdk.git
cd amazon-transcribe-streaming-sdk
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

### Prerequisites
If you don't already have local credentials setup for your AWS account, you can follow
this [guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
for configuring them using the AWS CLI.

In essence you'll need one of these authentication configurations setup in order for
the SDK to successfully resolve your API keys:

1. Set the `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and optionally the
`AWS_SESSION_TOKEN` environment variables
2. Set the `AWS_PROFILE` pointing to your AWS profile directory
3. Configure the `[default]` profile in `~/.aws/credentials`

For more details on the AWS shared configuration file and credential provider
usage, check the following developer guides:

* [Shared Config Overview](https://docs.aws.amazon.com/sdkref/latest/guide/creds-config-files.html)
* [Shared Config Format](https://docs.aws.amazon.com/sdkref/latest/guide/file-format.html)
* [Example Credential Setups](https://docs.aws.amazon.com/sdkref/latest/guide/usage-examples.html)

### Quick Start
Setup for this SDK will require either live or prerecorded audio. Full details
on the audio input requirements can be found in the [Amazon Transcribe Streaming
documentation](https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html).


Here's an example app to get started:
```python
import asyncio
import time

# This example uses aiofile for asynchronous file reads.
# It's not a dependency of the project but can be installed
# with `pip install aiofile`.
import aiofile

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from amazon_transcribe.utils import apply_realtime_delay

"""
Here's an example of a custom event handler you can extend to
process the returned transcription results as needed. This
handler will simply print the text out to your interpreter.
"""


SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CHANNEL_NUMS = 1

# An example file can be found at tests/integration/assets/test.wav
AUDIO_PATH = "tests/integration/assets/test.wav"
CHUNK_SIZE = 1024 * 8

REGION = "us-west-2"


class MyEventHandler(TranscriptResultStreamHandler):
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        # This handler can be implemented to handle transcriptions as needed.
        # Here's an example to get started.
        results = transcript_event.transcript.results
        for result in results:
            for alt in result.alternatives:
                print(alt.transcript)


async def basic_transcribe():
    # Setup up our client with our chosen AWS region
    client = TranscribeStreamingClient(region=REGION)

    # Start transcription to generate our async stream
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=SAMPLE_RATE,
        media_encoding="pcm",
    )

    async def write_chunks():
        # NOTE: For pre-recorded files longer than 5 minutes, the sent audio
        # chunks should be rate limited to match the realtime bitrate of the
        # audio stream to avoid signing issues.
        async with aiofile.AIOFile(AUDIO_PATH, "rb") as afp:
            reader = aiofile.Reader(afp, chunk_size=CHUNK_SIZE)
            await apply_realtime_delay(
                stream, reader, BYTES_PER_SAMPLE, SAMPLE_RATE, CHANNEL_NUMS
            )
        await stream.input_stream.end_stream()

    # Instantiate our handler and start processing events
    handler = MyEventHandler(stream.output_stream)
    await asyncio.gather(write_chunks(), handler.handle_events())


loop = asyncio.get_event_loop()
loop.run_until_complete(basic_transcribe())
loop.close()
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
