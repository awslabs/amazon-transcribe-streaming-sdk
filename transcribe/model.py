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
from typing import Dict, Tuple
import re

from transcribe.exceptions import ValidationException


class StringOption:
    def __init__(self, enum_values, value):
        self.enum_values: Tuple[str] = enum_values
        self.value: str = self._validate_value(value)

    def _validate_value(self, value: str):
        if value in self.enum_values:
            return value
        else:
            raise ValidationException(
                f"Value ({value}) doesn't match expected "
                f"values ({self.enum_values})."
            )


class ValidatedString:
    def __init__(self, value, min_=None, max_=None, pattern=None):
        self.min: Optional[int] = min_
        self.max: Optional[int] = max_
        self.pattern: Optional[str] = pattern
        self.value: str = self._validate_value(value)

    def _validate_value(self, value: str):
        valid = []
        validations = []
        if self.min is not None:
            valid.append(self.min <= len(value))
            validations.append(f"{self.min} <= value")
        if self.max is not None:
            valid.append(len(value) <= self.max)
            validations.append(f"value <= {self.max}")
        if self.pattern is not None:
            match = re.fullmatch(self.pattern, value)
            valid.append(match is not None)
            validations.append("value matches {self.pattern}")

        if all(valid):
            return value
        else:
            validation_criteria = ", ".join(validations)
            raise ValidationException(
                f"Value ({value}) doesn't match expected "
                f"values ({validation_criteria})."
            )


class Alternative:
    def __init__(self, transcript, items):
        self.transcript: Transcript = transcript
        self.items: ItemList = items


class AlternativeList(UserList):
    def __init__(self, alternative_list):
        self._alternative_list: List[Alternative] = alternative_list

    def __getitem__(self, item):
        return self._alternative_list[item]


class AudioChunk:
    def __init__(self, value: bytes):
        self.value: bytes = value


class AudioEvent:
    def __init__(self, audio_chunk, event_payload, event):
        self.audio_chunk: AudioChunk = audio_chunk
        self.event_payload: bool = event_payload
        self.event: bool = event


class AudioStream:
    def __init__(self, audio_event, eventstream):
        self.audio_event: AudioEvent = audio_event
        self.eventstream: bool = eventstream


class Item:
    def __init__(
        self, start_time, end_time, item_type, content, is_vocabulary_filter_match
    ):
        self.start_time: float = start_time
        self.end_time: float = end_time
        self.item_type: ItemType = item_type
        self.content: str = content
        self.is_vocabulary_filter_match: bool = is_vocabulary_filter_match


class ItemList(UserList):
    def __init__(self, item_list):
        self._item_list: List[Item] = item_list

    def __getitem__(self, item):
        return self._item_list[item]


class ItemType(StringOption):
    def __init__(self, value: str):
        super().__init__(("pronunciation", "punctuation",), value)


class LanguageCode(StringOption):
    def __init__(self, value: str):
        super().__init__(("en-US", "en-GB", "es-US", "fr-CA", "fr-FR", "en-AU",), value)


class MediaEncoding(StringOption):
    def __init__(self, value: str):
        super().__init__(("pcm",), value)


class MediaSampleRateHertz:
    def __init__(self, value):
        self.max: int = 48000
        self.min: int = 8000
        self.value: int = self._validate_value(value)

    def _validate_value(self, value: int):
        if self.min <= value <= self.max:
            return value
        else:
            class_name = type(self).__name__
            raise ValidationException(
                f"{class_name} value ({value}) isn't within "
                f"expected range ({self.min}, {self.max})."
            )


class Result:
    def __init__(self, result_id, start_time, end_time, is_partial, alternatives):
        self.result_id: str = result_id
        self.start_time: float = start_time
        self.end_time: float = end_time
        self.is_partial: bool = is_partial
        self.alternatives: AlternativeList = alternatives


class ResultList(UserList):
    def __init__(self, result_list):
        self._result_list: List[Result] = result_list

    def __getitem__(self, item):
        return self._result_list[item]


class StartStreamTranscriptionRequest:
    def __init__(
        self,
        language_code,
        media_sample_rate_hz,
        media_encoding,
        audio_stream,
        vocabulary_name=None,
        session_id=None,
        vocab_filter_method=None,
    ):

        self.language_code: LanguageCode = language_code
        self.media_sample_rate_hz: MediaSampleRateHertz = media_sample_rate_hz
        self.media_encoding: MediaEncoding = media_encoding
        self.audio_stream: AudioStream = audio_stream
        self.vocabulary_name: Optional[VocabularyName] = vocabulary_name
        self.session_id: Optional[SessionId] = session_id
        self.vocab_filter_method: Optional[VocabularyFilterMethod] = vocab_filter_method

    def serialize(self) -> Tuple[Dict, AudioStream]:
        headers = {
            "x-amzn-transcribe-language-code": self.language_code.value,
            "x-amzn-transcribe-sample-rate": self.media_sample_rate_hz.value,
            "x-amzn-transcribe-media-encoding": self.media_encoding.value,
            "x-amzn-transcribe-vocabulary-name": self.vocabulary_name,
            "x-amzn-transcribe-session-id": self.session_id,
            "x-amzn-transcribe-vocabulary-filter-method": self.vocab_filter_method,
        }

        body = self.audio_stream
        return headers, body


class StartStreamTranscriptionResponse:
    def __init__(
        self,
        request_id,
        language_code,
        media_sample_rate_hz,
        media_encoding,
        vocabulary_name,
        session_id,
        trascript_result_stream,
        vocab_filter_name,
        vocab_filter_method,
    ):
        self.request_id: str = request_id
        self.language_code: LanguageCode = laguage_code
        self.media_sample_rate_hz: MediaSampleRateHertz = media_sample_rate_hz
        self.media_encoding: MediaEncoding = media_encoding
        self.vocabulary_name: VocabularyName = vocabulary_name
        self.session_id: SessionId = session_id
        self.transcript_result_stream: TranscriptResultStream = transcript_result_stream
        self.vocab_filter_name: VocabularyFilterName = vocab_filter_name
        self.vocab_filter_method: Optional[VocabularyFilterMethod] = vocab_filter_method

    def deserialize(self, Response):
        """
        x-amzn-transcribe-language-code -> LanguageCode
        x-amzn-transcribe-sample-rate -> MediaSampleRateHertz
        x-amzn-transcribe-media-encoding -> MediaEncoding
        x-amzn-transcribe-vocabulary-name -> VocabularyName
        x-amzn-transcribe-session-id -> SessionId
        x-amzn-transcribe-vocabulary-filter-name -> VocabularyNameFilter
        x-amzn-transcribe-vocabulary-filter-method -> VocabularyFilterMethod
        """
        raise NotImplemented


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

    def __init__(self, transcript_event, eventstream):
        self.trancript_event: TranscriptEvent = transcript_event
        self.eventstream: bool = eventstream


class VocabularyFilterMethod(StringOption):
    def __init__(self, value: str):
        super().__init__(("remove", "mask", "tag",), value)


class VocabularyFilterName(ValidatedString):
    def __init__(self, value: str):
        self.value: str = self._validate_value(value)
        self.min: int = 1
        self.max: int = 200
        self.pattern: str = r"^[0-9a-zA-Z._-]+"


class VocabularyName(ValidatedString):
    def __init__(self, value: str):
        self.value: str = self._validate_value(value)
        self.min: int = 1
        self.max: int = 200
        self.pattern: str = r"^[0-9a-zA-Z._-]+"
