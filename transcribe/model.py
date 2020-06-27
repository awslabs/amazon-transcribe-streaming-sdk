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

from collections import UserList
from io import BytesIO
from typing import Dict, Optional, Tuple, Union
import re

from transcribe.exceptions import ValidationException
from transcribe.eventstream import BaseEvent, BaseStream


class Alternative:
    def __init__(self, transcript, items):
        self.transcript: Transcript = transcript
        self.items: ItemList = items


class AlternativeList(UserList):
    def __init__(self, alternative_list):
        self._alternative_list: List[Alternative] = alternative_list

    def __getitem__(self, item):
        return self._alternative_list[item]


class AudioEvent(BaseEvent):
    def __init__(
        self,
        audio_chunk: Optional[bytes]
    ):
        super().__init__(payload=audio_chunk)

    @property
    def audio_chunk(self):
        return self.payload


class AudioStream(BaseStream):
    def __init__(self, event_serializer, eventstream_serializer=None):
        super().__init__(
            event_serializer=event_serializer,
            eventstream_serializer=eventstream_serializer,
        )

    def send_audio_event(self, audio_chunk: Optional[bytes]):
        audio_event = AudioEvent(audio_chunk)
        super().send_event(audio_event)


class Item:
    def __init__(
        self,
        start_time=None,
        end_time=None,
        item_type=None,
        content=None,
        is_vocabulary_filter_match=None,
    ):
        self.start_time: Optional[float] = start_time
        self.end_time: Optional[float] = end_time
        self.item_type: Optional[str] = item_type
        self.content: Optional[str] = content
        self.is_vocabulary_filter_match: Optional[
            bool
        ] = is_vocabulary_filter_match


class ItemList(UserList):
    def __init__(self, item_list):
        self._item_list: List[Item] = item_list

    def __getitem__(self, item):
        return self._item_list[item]


class Result:
    def __init__(
        self, result_id, start_time, end_time, is_partial, alternatives
    ):
        self.result_id: Optiona[str] = result_id
        self.start_time: Optional[float] = start_time
        self.end_time: Optional[float] = end_time
        self.is_partial: Optional[bool] = is_partial
        self.alternatives: Optional[AlternativeList] = alternatives


class ResultList(UserList):
    def __init__(self, result_list):
        self._result_list: List[Result] = result_list

    def __getitem__(self, item):
        return self._result_list[item]


class StartStreamTranscriptionRequest:
    def __init__(
        self,
        language_code=None,
        media_sample_rate_hz=None,
        media_encoding=None,
        audio_stream=None,
        vocabulary_name=None,
        session_id=None,
        vocab_filter_method=None,
    ):

        self.language_code: Optional[str] = language_code
        self.media_sample_rate_hz: Optional[int] = media_sample_rate_hz
        self.media_encoding: Optional[str] = media_encoding
        self.audio_stream: AudioStream = audio_stream
        self.vocabulary_name: Optional[str] = vocabulary_name
        self.session_id: Optional[str] = session_id
        self.vocab_filter_method: Optional[str] = vocab_filter_method


class StartStreamTranscriptionResponse:
    def __init__(
        self,
        request_id=None,
        language_code=None,
        media_sample_rate_hz=None,
        media_encoding=None,
        vocabulary_name=None,
        session_id=None,
        transcript_result_stream=None,
        vocab_filter_name=None,
        vocab_filter_method=None,
    ):
        self.request_id: Optional[str] = request_id
        self.language_code: Optional[str] = language_code
        self.media_sample_rate_hz: Optional[int] = media_sample_rate_hz
        self.media_encoding: Optional[str] = media_encoding
        self.vocabulary_name: Optional[str] = vocabulary_name
        self.session_id: Optional[str] = session_id
        self.transcript_result_stream: Optional[
            TranscriptResultStream
        ] = transcript_result_stream
        self.vocab_filter_name: Optional[str] = vocab_filter_name
        self.vocab_filter_method: Optional[str] = vocab_filter_method


class Transcript:
    def __init__(self, result_list):
        self.result_list: ResultList = result_list


class TranscriptEvent:
    def __init__(self, transcript):
        self.transcript: Transcript = transcript


class TranscriptResultStream:
    """ Throws::
        "BadRequestException"
        "LimitExceededException"
        "InternalFailureException"
        "ConflictException"
        "ServiceUnavailableException"
    """

    def __init__(self, transcript_event, eventstream=None):
        self.trancript_event: TranscriptEvent = transcript_event
        self.eventstream: Optional[bool] = eventstream
