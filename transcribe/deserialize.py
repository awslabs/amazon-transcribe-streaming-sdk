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
from typing import Optional, Dict, Type, Any

from transcribe.model import StartStreamTranscriptionResponse
from transcribe.response import Response
from transcribe.exceptions import (
    ServiceException,
    BadRequestException,
    ConflictException,
    InternalFailureException,
    LimitExceededException,
    ServiceUnavailableException,
    UnknownServiceException,
)


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
        media_sample_rate_hz = self._raw_value_to_int(
            headers.get("x-amzn-transcribe-sample-rate")
        )

        parsed_response = StartStreamTranscriptionResponse(
            request_id=request_id,
            language_code=language_code,
            media_sample_rate_hz=media_sample_rate_hz,
            media_encoding=media_encoding,
            vocabulary_name=vocabulary_name,
            session_id=session_id,
            transcript_result_stream=None,
            vocab_filter_name=vocab_filter_name,
            vocab_filter_method=vocab_filter_method,
        )
        return parsed_response

    def _raw_value_to_int(self, value: Optional[str]) -> Optional[int]:
        if value:
            return int(value)
        return None
