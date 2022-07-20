# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


from urllib.parse import urlsplit
from typing import AsyncIterable, Dict

from amazon_transcribe import __version__ as version
from amazon_transcribe.exceptions import ValidationException
from amazon_transcribe.model import StartStreamTranscriptionEventStream

import asyncio
import time


def _add_required_headers(endpoint: str, headers: Dict[str, str]):
    urlparts = urlsplit(endpoint)
    if not urlparts.hostname:
        raise ValidationException(
            "Unexpected endpoint ({endpoint}) provided to serializer"
        )
    headers.update(
        {
            "user-agent": f"transcribe-streaming-sdk-{version}",
            "host": urlparts.hostname,
        }
    )


def ensure_boolean(val):
    if isinstance(val, bool):
        return val
    else:
        return val.lower() == "true"


async def apply_realtime_delay(
    stream: StartStreamTranscriptionEventStream,
    reader: AsyncIterable,
    bytes_per_sample: int,
    sample_rate: float,
    channel_nums: int,
) -> None:
    """Applies a delay when reading an audio file steam to simulate a real-time delay."""
    start_time = time.time()
    elapsed_audio_time = 0.0
    async for chunk in reader:
        await stream.input_stream.send_audio_event(audio_chunk=chunk)
        elapsed_audio_time += len(chunk) / (
            bytes_per_sample * sample_rate * channel_nums
        )
        # sleep to simulate real-time streaming
        wait_time = start_time + elapsed_audio_time - time.time()
        await asyncio.sleep(wait_time)
