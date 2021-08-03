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
import json
from typing import Optional, Type, Any, List

import amazon_transcribe.exceptions as transcribe_exceptions
from amazon_transcribe.eventstream import BaseEvent
from amazon_transcribe.model import (
    StartStreamTranscriptionResponse,
    TranscriptResultStream,
    TranscriptEvent,
    Transcript,
    Result,
    Alternative,
    Item,
)
from amazon_transcribe.response import Response
from amazon_transcribe.exceptions import (
    ServiceException,
    BadRequestException,
    ConflictException,
    InternalFailureException,
    LimitExceededException,
    ServiceUnavailableException,
    UnknownServiceException,
    SerializationException,
)
from amazon_transcribe.utils import ensure_boolean


class TranscribeStreamingResponseParser:
    """Converts raw HTTP responses into modeled objects and exceptions.

    This class is not public and must not be consumed outside of this project.
    """

    def _get_error_code(self, http_response: Response) -> str:
        error_code = "Unknown"
        if "x-amzn-errortype" in http_response.headers:
            error_code = http_response.headers["x-amzn-errortype"]
            # Could be x-amzn-errortype: ValidationException:
            error_code = error_code.split(":")[0]
        return error_code

    def _get_error_message(self, body_bytes: bytes) -> str:
        error_message = "An unknown error was returned by the service"
        try:
            parsed_body = json.loads(body_bytes)
        except json.decoder.JSONDecodeError:
            return error_message
        if "Message" in parsed_body:
            error_message = parsed_body["Message"]
        elif "message" in parsed_body:
            error_message = parsed_body["message"]
        return error_message

    def parse_exception(
        self, http_response: Response, body_bytes: bytes
    ) -> ServiceException:
        error_code = self._get_error_code(http_response)
        error_message = self._get_error_message(body_bytes)
        if error_code == "BadRequestException":
            return BadRequestException(error_message)
        elif error_code == "ConflictException":
            return ConflictException(error_message)
        elif error_code == "InternalFailureException":
            return InternalFailureException(error_message)
        elif error_code == "LimitExceededException":
            return LimitExceededException(error_message)
        elif error_code == "ServiceUnavailableException":
            return ServiceUnavailableException(error_message)
        elif error_code == "SerializationException":
            return SerializationException(error_message)
        return UnknownServiceException(
            http_response.status_code, error_code, error_message,
        )

    def parse_start_stream_transcription_response(
        self, http_response: Response, body_stream: Any,
    ) -> StartStreamTranscriptionResponse:
        headers = http_response.headers
        request_id = headers.get("x-amzn-request-id")
        language_code = headers.get("x-amzn-transcribe-language-code")
        media_encoding = headers.get("x-amzn-transcribe-media-encoding")
        vocabulary_name = headers.get("x-amzn-transcribe-vocabulary-name")
        session_id = headers.get("x-amzn-transcribe-session-id")
        vocab_filter_name = headers.get("x-amzn-transcribe-vocabulary-filter-name")
        vocab_filter_method = headers.get("x-amzn-transcribe-vocabulary-filter-method")
        show_speaker_label = self._raw_value_to_bool(
            headers.get("x-amzn-transcribe-show-speaker-label")
        )
        enable_channel_identification = self._raw_value_to_bool(
            headers.get("x-amzn-transcribe-enable-channel-identification")
        )
        number_of_channels = self._raw_value_to_int(
            headers.get("x-amzn-transcribe-number-of-channels")
        )
        media_sample_rate_hz = self._raw_value_to_int(
            headers.get("x-amzn-transcribe-sample-rate")
        )

        transcript_result_stream = TranscriptResultStream(
            body_stream, TranscribeStreamingEventParser()
        )

        parsed_response = StartStreamTranscriptionResponse(
            transcript_result_stream=transcript_result_stream,
            request_id=request_id,
            language_code=language_code,
            media_sample_rate_hz=media_sample_rate_hz,
            media_encoding=media_encoding,
            vocabulary_name=vocabulary_name,
            session_id=session_id,
            vocab_filter_name=vocab_filter_name,
            vocab_filter_method=vocab_filter_method,
            show_speaker_label=show_speaker_label,
            enable_channel_identification=enable_channel_identification,
            number_of_channels=number_of_channels,
        )
        return parsed_response

    def _raw_value_to_int(self, value: Optional[str]) -> Optional[int]:
        if value:
            return int(value)
        return None

    def _raw_value_to_bool(self, value: Optional[str]) -> Optional[bool]:
        if value is not None:
            return ensure_boolean(value)
        return None


class TranscribeStreamingEventParser:
    def parse(self, raw_event) -> Optional[BaseEvent]:
        message_type = raw_event.headers.get(":message-type")
        if message_type in ["error", "exception"]:
            raise self._parse_event_exception(raw_event)
        elif message_type == "event":
            event_type = raw_event.headers.get(":event-type")
            raw_body = json.loads(raw_event.payload)
            if event_type == "TranscriptEvent":
                # TODO: Handle cases where the service returns an incorrect response
                return self._parse_transcript_event(raw_body)
        return None

    def _parse_transcript_event(self, current_node: Any) -> TranscriptEvent:
        transcript = self._parse_transcript(current_node.get("Transcript"))
        return TranscriptEvent(transcript)

    def _parse_transcript(self, current_node: Any) -> Transcript:
        results = self._parse_result_list(current_node.get("Results"))
        return Transcript(results)

    def _parse_result_list(self, current_node: Any) -> List[Result]:
        return [self._parse_result(e) for e in current_node]

    def _parse_result(self, current_node: Any) -> Result:
        alternatives = self._parse_alternative_list(current_node.get("Alternatives"))
        return Result(
            result_id=current_node.get("ResultId"),
            start_time=current_node.get("StartTime"),
            end_time=current_node.get("EndTime"),
            is_partial=current_node.get("IsPartial"),
            alternatives=alternatives,
            channel_id=current_node.get("ChannelId"),
        )

    def _parse_alternative_list(self, current_node: Any) -> List[Alternative]:
        return [self._parse_alternative(e) for e in current_node]

    def _parse_alternative(self, current_node: Any) -> Alternative:
        return Alternative(
            transcript=current_node.get("Transcript"),
            items=self._parse_item_list(current_node.get("Items")),
        )

    def _parse_item_list(self, current_node: Any) -> List[Item]:
        return [self._parse_item(e) for e in current_node]

    def _parse_item(self, current_node: Any) -> Item:
        return Item(
            start_time=current_node.get("StartTime"),
            end_time=current_node.get("EndTime"),
            item_type=current_node.get("Type"),
            content=current_node.get("Content"),
            vocabulary_filter_match=current_node.get("VocabularyFilterMatch"),
            speaker=current_node.get("Speaker"),
            confidence=current_node.get("Confidence"),
        )

    def _parse_event_exception(self, raw_event) -> ServiceException:
        exception_type: str = raw_event.headers.get(
            ":exception-type", "ServiceException"
        )
        exception_cls: Type[ServiceException] = getattr(
            transcribe_exceptions, exception_type, ServiceException
        )
        try:
            raw_body = json.loads(raw_event.payload)
        except ValueError:
            raw_body = {}
        exception_msg = raw_body.get("Message", "An unknown service exception occured")
        return exception_cls(exception_msg)
