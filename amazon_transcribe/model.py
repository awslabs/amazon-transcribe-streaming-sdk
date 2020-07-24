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

import re
from typing import Dict, Optional, Tuple, Union, List

from amazon_transcribe.exceptions import ValidationException
from amazon_transcribe.eventstream import BaseEvent, BaseStream, EventStream


class Alternative:
    def __init__(self, transcript, items):
        self.transcript: str = transcript
        self.items: List[Item] = items


class AudioEvent(BaseEvent):
    def __init__(self, audio_chunk: Optional[bytes]):
        super().__init__(payload=audio_chunk)

    @property
    def audio_chunk(self):
        return self.payload


class AudioStream(BaseStream):
    async def send_audio_event(self, audio_chunk: Optional[bytes]):
        audio_event = AudioEvent(audio_chunk)
        await super().send_event(audio_event)


class Item:
    def __init__(
        self,
        start_time=None,
        end_time=None,
        item_type=None,
        content=None,
        vocabulary_filter_match=None,
    ):
        self.start_time: Optional[float] = start_time
        self.end_time: Optional[float] = end_time
        self.item_type: Optional[str] = item_type
        self.content: Optional[str] = content
        self.vocabulary_filter_match: Optional[bool] = vocabulary_filter_match


class Result:
    def __init__(self, result_id, start_time, end_time, is_partial, alternatives):
        self.result_id: Optiona[str] = result_id
        self.start_time: Optional[float] = start_time
        self.end_time: Optional[float] = end_time
        self.is_partial: Optional[bool] = is_partial
        self.alternatives: Optional[List[Alternative]] = alternatives


class StartStreamTranscriptionRequest:
    def __init__(
        self,
        language_code=None,
        media_sample_rate_hz=None,
        media_encoding=None,
        vocabulary_name=None,
        session_id=None,
        vocab_filter_method=None,
    ):

        self.language_code: Optional[str] = language_code
        self.media_sample_rate_hz: Optional[int] = media_sample_rate_hz
        self.media_encoding: Optional[str] = media_encoding
        self.vocabulary_name: Optional[str] = vocabulary_name
        self.session_id: Optional[str] = session_id
        self.vocab_filter_method: Optional[str] = vocab_filter_method


class StartStreamTranscriptionResponse:
    def __init__(
        self,
        transcript_result_stream,
        request_id=None,
        language_code=None,
        media_sample_rate_hz=None,
        media_encoding=None,
        vocabulary_name=None,
        session_id=None,
        vocab_filter_name=None,
        vocab_filter_method=None,
    ):
        self.request_id: Optional[str] = request_id
        self.language_code: Optional[str] = language_code
        self.media_sample_rate_hz: Optional[int] = media_sample_rate_hz
        self.media_encoding: Optional[str] = media_encoding
        self.vocabulary_name: Optional[str] = vocabulary_name
        self.session_id: Optional[str] = session_id
        self.transcript_result_stream: TranscriptResultStream = transcript_result_stream
        self.vocab_filter_name: Optional[str] = vocab_filter_name
        self.vocab_filter_method: Optional[str] = vocab_filter_method


class Transcript:
    def __init__(self, results):
        self.results: List[Result] = results


class TranscriptEvent(BaseEvent):
    def __init__(self, transcript):
        self.transcript: Transcript = transcript


class TranscriptResultStream(EventStream):
    """ Throws::
        "BadRequestException"
        "LimitExceededException"
        "InternalFailureException"
        "ConflictException"
        "ServiceUnavailableException"
    """


class StartStreamTranscriptionEventStream:
    def __init__(self, audio_stream: AudioStream, response):
        self._response = response
        self._audio_stream = audio_stream

    @property
    def response(self) -> StartStreamTranscriptionResponse:
        return self._response

    @property
    def input_stream(self) -> AudioStream:
        return self._audio_stream

    @property
    def output_stream(self) -> TranscriptResultStream:
        return self.response.transcript_result_stream
