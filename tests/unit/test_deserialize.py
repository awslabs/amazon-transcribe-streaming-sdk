import json
import pytest
from unittest.mock import Mock

from amazon_transcribe.response import Response
from amazon_transcribe.deserialize import (
    TranscribeStreamingResponseParser,
    TranscribeStreamingEventParser,
)
from amazon_transcribe.eventstream import EventStreamMessage
from amazon_transcribe.exceptions import (
    ServiceException,
    BadRequestException,
    ConflictException,
    InternalFailureException,
    LimitExceededException,
    ServiceUnavailableException,
    UnknownServiceException,
)


@pytest.fixture
def parser():
    return TranscribeStreamingResponseParser()


def test_parse_start_stream_transcription_response_basic(parser):
    response = Response(
        headers={
            "x-amzn-request-id": "foo-request-id",
            "x-amzn-transcribe-language-code": "foo_language_code",
            "x-amzn-transcribe-sample-rate": "44100",
            "x-amzn-transcribe-media-encoding": "pcm",
            "x-amzn-transcribe-vocabulary-name": "foo_name",
            "x-amzn-transcribe-session-id": "foo_id",
            "x-amzn-transcribe-vocabulary-filter-name": "foo_filter_name",
            "x-amzn-transcribe-vocabulary-filter-method": "foo_filter_method",
            "x-amzn-transcribe-show-speaker-label": "true",
            "x-amzn-transcribe-enable-channel-identification": "false",
            "x-amzn-transcribe-number-of-channels": "0",
            "x-amzn-transcribe-enable-partial-results-stabilization": "true",
            "x-amzn-transcribe-partial-results-stability": "high",
        }
    )
    parsed = parser.parse_start_stream_transcription_response(response, None)
    assert parsed.request_id == "foo-request-id"
    assert parsed.language_code == "foo_language_code"
    assert parsed.media_sample_rate_hz == 44100
    assert parsed.media_encoding == "pcm"
    assert parsed.vocabulary_name == "foo_name"
    assert parsed.session_id == "foo_id"
    assert parsed.vocab_filter_name == "foo_filter_name"
    assert parsed.vocab_filter_method == "foo_filter_method"
    assert parsed.show_speaker_label is True
    assert parsed.enable_channel_identification is False
    assert parsed.number_of_channels == 0
    assert parsed.enable_partial_results_stabilization is True
    assert parsed.partial_results_stability == "high"


def test_parse_start_stream_transcription_response_missing_fields(parser):
    response = Response(headers={})
    parsed = parser.parse_start_stream_transcription_response(response, None)
    assert parsed.request_id is None
    assert parsed.language_code is None
    assert parsed.media_sample_rate_hz is None
    assert parsed.media_encoding is None
    assert parsed.vocabulary_name is None
    assert parsed.session_id is None
    assert parsed.vocab_filter_name is None
    assert parsed.vocab_filter_method is None
    assert parsed.show_speaker_label is None
    assert parsed.enable_channel_identification is None
    assert parsed.number_of_channels is None
    assert parsed.enable_partial_results_stabilization is None
    assert parsed.partial_results_stability is None


@pytest.mark.parametrize(
    "error_code, expected_exception_cls",
    [
        ("BadRequestException", BadRequestException),
        ("ConflictException", ConflictException),
        ("InternalFailureException", InternalFailureException),
        ("LimitExceededException", LimitExceededException),
        ("ServiceUnavailableException", ServiceUnavailableException),
        ("FooCode", UnknownServiceException),
    ],
)
def test_parses_bad_request_exception(error_code, expected_exception_cls, parser):
    response = Response(
        headers={
            "x-amzn-ErrorType": error_code,
        }
    )
    body_bytes = b'{"message": "exception message"}'
    exception = parser.parse_exception(response, body_bytes)
    assert isinstance(exception, expected_exception_cls)
    assert exception.message == "exception message"


def test_parses_exception_message(parser):
    response = Response(
        headers={
            "x-amzn-ErrorType": "BadRequestException",
        }
    )
    body_bytes = b'{"message": "exception message"}'
    exception = parser.parse_exception(response, body_bytes)
    assert exception.message == "exception message"

    body_bytes = b'{"Message": "exception message"}'
    exception = parser.parse_exception(response, body_bytes)
    assert exception.message == "exception message"


def test_handles_unknown_exception(parser):
    response = Response(
        status_code=404,
        headers={
            "x-amzn-ErrorType": "FooCode",
        },
    )
    body_bytes = b'{"message": "exception message"}'
    exception = parser.parse_exception(response, body_bytes)
    assert exception.status_code == 404
    assert exception.error_code == "FooCode"
    assert exception.message == "exception message"


def test_handles_missing_exception_fields(parser):
    response = Response(status_code=200, headers={})
    exception = parser.parse_exception(response, b"{}")
    assert exception.status_code == 200
    assert exception.error_code == "Unknown"
    assert "unknown" in exception.message


def test_handles_bad_body_json(parser):
    response = Response(
        headers={
            "x-amzn-ErrorType": "BadRequestException",
        }
    )
    exception = parser.parse_exception(response, b"not json")
    assert "unknown" in exception.message


@pytest.fixture
def event_parser():
    return TranscribeStreamingEventParser()


def test_parses_transcript_event(event_parser):
    mock_event = Mock(spec=EventStreamMessage)
    mock_event.headers = {
        ":event-type": "TranscriptEvent",
        ":content-type": "application/json",
        ":message-type": "event",
    }
    json_payload = {
        "Transcript": {
            "Results": [
                {
                    "Alternatives": [
                        {
                            "Items": [
                                {
                                    "Content": "Wanted",
                                    "EndTime": 0.45,
                                    "StartTime": 0.11,
                                    "Type": "pronunciation",
                                    "VocabularyFilterMatch": False,
                                    "Confidence": 0.82,
                                    "Stable": False,
                                },
                                {
                                    "Content": "Chief",
                                    "EndTime": 0.86,
                                    "StartTime": 0.55,
                                    "Type": "pronunciation",
                                    "VocabularyFilterMatch": False,
                                    "Confidence": 0.9,
                                    "Stable": True,
                                },
                            ],
                            "Transcript": "Wanted Chief",
                        }
                    ],
                    "EndTime": 0.86,
                    "IsPartial": True,
                    "ResultId": "foobar83-265d-4c95-9056-50d14db14710",
                    "StartTime": 0.11,
                }
            ]
        }
    }
    mock_event.payload = json.dumps(json_payload).encode("utf-8")
    event = event_parser.parse(mock_event)
    assert len(event.transcript.results) == 1
    result = event.transcript.results[0]
    assert result.end_time == 0.86
    assert result.start_time == 0.11
    assert result.is_partial
    assert result.result_id == "foobar83-265d-4c95-9056-50d14db14710"
    assert len(result.alternatives) == 1
    assert len(result.alternatives[0].items) == 2
    assert result.alternatives[0].transcript == "Wanted Chief"
    item_one = result.alternatives[0].items[0]
    assert item_one.content == "Wanted"
    assert item_one.start_time == 0.11
    assert item_one.end_time == 0.45
    assert item_one.item_type == "pronunciation"
    assert item_one.vocabulary_filter_match is False
    assert item_one.confidence == 0.82
    assert item_one.stable is False
    item_two = result.alternatives[0].items[1]
    assert item_two.content == "Chief"
    assert item_two.start_time == 0.55
    assert item_two.end_time == 0.86
    assert item_two.item_type == "pronunciation"
    assert item_two.vocabulary_filter_match is False
    assert item_two.confidence == 0.9
    assert item_two.stable is True


def test_parses_known_exception(event_parser):
    mock_event = Mock(spec=EventStreamMessage)
    mock_event.headers = {
        ":exception-type": "BadRequestException",
        ":content-type": "application/json",
        ":message-type": "exception",
    }
    mock_event.payload = b'{"Message": "The request was bad."}'
    with pytest.raises(BadRequestException):
        event_parser.parse(mock_event)


def test_parses_unknown_exception(event_parser):
    mock_event = Mock(spec=EventStreamMessage)
    mock_event.headers = {
        ":exception-type": "ServerOnFire",
        ":content-type": "application/json",
        ":message-type": "exception",
    }
    mock_event.payload = b""
    with pytest.raises(ServiceException):
        event_parser.parse(mock_event)
