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


from typing import Any, Dict, Tuple, Optional

from amazon_transcribe.request import Request
from amazon_transcribe.structures import BufferableByteStream
from amazon_transcribe.utils import _add_required_headers
from amazon_transcribe.exceptions import SerializerException
from amazon_transcribe.model import (
    AudioEvent,
    StartStreamTranscriptionRequest,
    BaseEvent,
)


class TranscribeStreamingSerializer:
    """Convert StartStreamTranscriptionRequest into a
    Request object for streaming to the Transcribe service.
    """

    def _serialize_header(
        self,
        header: str,
        value: Any,
        prefix: str = "x-amzn-transcribe-",
    ) -> Dict[str, str]:
        if value is None:
            return {}
        else:
            return {f"{prefix}{header}": str(value)}

    def _serialize_str_header(
        self, header: str, value: Optional[str]
    ) -> Dict[str, str]:
        return self._serialize_header(header, value)

    def _serialize_int_header(
        self, header: str, value: Optional[int]
    ) -> Dict[str, str]:
        return self._serialize_header(header, value)

    def _serialize_bool_header(
        self, header: str, value: Optional[bool]
    ) -> Dict[str, str]:
        return self._serialize_header(header, value)

    def serialize_start_stream_transcription_request(
        self, endpoint: str, request_shape: StartStreamTranscriptionRequest
    ) -> Request:

        method = "POST"
        request_uri = "/stream-transcription"

        headers: Dict[str, str] = {}
        headers.update(
            self._serialize_str_header("language-code", request_shape.language_code)
        )
        headers.update(
            self._serialize_int_header(
                "sample-rate", request_shape.media_sample_rate_hz
            )
        )
        headers.update(
            self._serialize_str_header("media-encoding", request_shape.media_encoding)
        )
        headers.update(
            self._serialize_str_header("vocabulary-name", request_shape.vocabulary_name)
        )
        headers.update(
            self._serialize_str_header("session-id", request_shape.session_id)
        )
        headers.update(
            self._serialize_str_header(
                "vocabulary-filter-method",
                request_shape.vocab_filter_method,
            )
        )
        headers.update(
            self._serialize_str_header(
                "vocabulary-filter-name",
                request_shape.vocab_filter_name,
            )
        )
        headers.update(
            self._serialize_bool_header(
                "show-speaker-label",
                request_shape.show_speaker_label,
            )
        )
        headers.update(
            self._serialize_bool_header(
                "enable-channel-identification",
                request_shape.enable_channel_identification,
            )
        )
        headers.update(
            self._serialize_int_header(
                "number-of-channels",
                request_shape.number_of_channels,
            )
        )
        headers.update(
            self._serialize_bool_header(
                "enable-partial-results-stabilization",
                request_shape.enable_partial_results_stabilization,
            )
        )
        headers.update(
            self._serialize_str_header(
                "partial-results-stability",
                request_shape.partial_results_stability,
            )
        )
        headers.update(
            self._serialize_str_header(
                "language-model-name",
                request_shape.language_model_name,
            )
        )

        _add_required_headers(endpoint, headers)

        body = BufferableByteStream()

        request = Request(
            endpoint=endpoint,
            path=request_uri,
            method=method,
            headers=headers,
            body=body,
        )
        return request


SERIALIZED_EVENT = Tuple[Dict, bytes]


class EventSerializer:
    def serialize(self, audio_event: BaseEvent) -> SERIALIZED_EVENT:
        raise NotImplementedError("serialize")


class AudioEventSerializer(EventSerializer):
    """Convert AudioEvent objects into payload and header outputs for eventstreams"""

    def serialize(self, event: BaseEvent) -> SERIALIZED_EVENT:
        if isinstance(event, AudioEvent):
            return self._serialize_audio_event(event)
        raise SerializerException(f'Unexpected event type encountered: "{type(event)}"')

    def _serialize_audio_event(self, audio_event: AudioEvent):
        headers = {
            ":message-type": "event",
            ":event-type": "AudioEvent",
            ":content-type": "application/octet-stream",
        }
        return headers, audio_event.payload
