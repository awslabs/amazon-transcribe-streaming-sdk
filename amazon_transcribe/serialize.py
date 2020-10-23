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


from io import BufferedIOBase
from typing import Dict, Tuple, Union

from amazon_transcribe.request import PreparedRequest, Request
from amazon_transcribe.structures import BufferableByteStream
from amazon_transcribe.utils import _add_required_headers
from amazon_transcribe.exceptions import SerializerException
from amazon_transcribe.model import (
    AudioEvent,
    StartStreamTranscriptionRequest,
    BaseEvent,
)

HEADER_VALUE = Union[int, None, str]


class Serializer:
    def __init__(self):
        raise NotImplementedError("Serializer")

    def serialize(self) -> Tuple[Dict[str, HEADER_VALUE], BufferedIOBase]:
        """Serialize out to payload and headers."""
        raise NotImplementedError("serialize")

    def serialize_to_request(self) -> PreparedRequest:
        """Serialize parameters into an HTTP request."""
        raise NotImplementedError("serialize_to_request")


class TranscribeStreamingRequestSerializer(Serializer):
    """Convert StartStreamTranscriptionRequest into a
    Request object for streaming to the Transcribe service.
    """

    def __init__(self, endpoint, transcribe_request):
        self.endpoint: str = endpoint
        self.method: str = "POST"
        self.request_uri: str = "/stream-transcription"
        self.request_shape: StartStreamTranscriptionRequest = transcribe_request

    def serialize(self) -> Tuple[Dict[str, HEADER_VALUE], BufferedIOBase]:
        headers = {
            "x-amzn-transcribe-language-code": self.request_shape.language_code,
            "x-amzn-transcribe-sample-rate": self.request_shape.media_sample_rate_hz,
            "x-amzn-transcribe-media-encoding": self.request_shape.media_encoding,
            "x-amzn-transcribe-vocabulary-name": self.request_shape.vocabulary_name,
            "x-amzn-transcribe-session-id": self.request_shape.session_id,
            "x-amzn-transcribe-vocabulary-filter-method": self.request_shape.vocab_filter_method,
            "x-amzn-transcribe-vocabulary-filter-name": self.request_shape.vocab_filter_name,
            "x-amzn-transcribe-show-speaker-label": self.request_shape.show_speaker_label,
            "x-amzn-transcribe-enable-channel-identification": self.request_shape.enable_channel_identification,
            "x-amzn-transcribe-number-of-channels": self.request_shape.number_of_channels,
        }

        _add_required_headers(self.endpoint, headers)

        body = BufferableByteStream()
        return headers, body

    def serialize_to_request(self) -> PreparedRequest:
        headers, body = self.serialize()
        request = Request(
            endpoint=self.endpoint,
            path=self.request_uri,
            method=self.method,
            headers=headers,
            body=body,
        )
        return request.prepare()


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
