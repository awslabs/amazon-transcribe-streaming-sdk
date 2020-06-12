import pytest

from transcribe.request import HeadersDict
from transcribe.response import Response
from transcribe.deserialize import TranscribeStreamingResponseParser
from transcribe.exceptions import (
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


def test_parse_start_stream_transcription_response_missing_fields(parser):
    response = Response(headers={})
    parsed = parser.parse_start_stream_transcription_response(response, None)
    assert parsed.request_id == None
    assert parsed.language_code == None
    assert parsed.media_sample_rate_hz == None
    assert parsed.media_encoding == None
    assert parsed.vocabulary_name == None
    assert parsed.session_id == None
    assert parsed.vocab_filter_name == None
    assert parsed.vocab_filter_method == None


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
def test_parses_bad_request_exception(
    error_code, expected_exception_cls, parser
):
    response = Response(headers={"x-amzn-ErrorType": error_code,})
    body_bytes = b'{"message": "exception message"}'
    exception = parser.parse_exception(response, body_bytes)
    assert isinstance(exception, expected_exception_cls)
    assert exception.message == "exception message"


def test_parses_exception_message(parser):
    response = Response(headers={"x-amzn-ErrorType": "BadRequestException",})
    body_bytes = b'{"message": "exception message"}'
    exception = parser.parse_exception(response, body_bytes)
    assert exception.message == "exception message"

    body_bytes = b'{"Message": "exception message"}'
    exception = parser.parse_exception(response, body_bytes)
    assert exception.message == "exception message"


def test_handles_unknown_exception(parser):
    response = Response(
        status_code=404, headers={"x-amzn-ErrorType": "FooCode",}
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
    response = Response(headers={"x-amzn-ErrorType": "BadRequestException",})
    exception = parser.parse_exception(response, b"not json")
    assert "unknown" in exception.message
