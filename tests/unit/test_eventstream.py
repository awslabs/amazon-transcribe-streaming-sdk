# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Unit tests for the binary event stream decoder. """

import datetime
import uuid
from unittest.mock import Mock

import pytest

from amazon_transcribe.auth import Credentials
from amazon_transcribe.eventstream import (
    ChecksumMismatch,
    DecodeUtils,
    DuplicateHeader,
    EventSigner,
    EventStream,
    EventStreamBuffer,
    EventStreamHeaderParser,
    EventStreamMessage,
    EventStreamMessageSerializer,
    HeaderBytesExceedMaxLength,
    HeaderValueBytesExceedMaxLength,
    Int8HeaderValue,
    Int16HeaderValue,
    Int32HeaderValue,
    Int64HeaderValue,
    InvalidHeadersLength,
    InvalidHeaderValue,
    InvalidPayloadLength,
    MessagePrelude,
    PayloadBytesExceedMaxLength,
)

EMPTY_MESSAGE = (
    b"\x00\x00\x00\x10\x00\x00\x00\x00\x05\xc2H\xeb}\x98\xc8\xff",
    EventStreamMessage(
        prelude=MessagePrelude(
            total_length=0x10,
            headers_length=0,
            crc=0x05C248EB,
        ),
        headers={},
        payload=b"",
        crc=0x7D98C8FF,
    ),
)

INT8_HEADER = (
    (b"\x00\x00\x00\x17\x00\x00\x00\x07)\x86\x01X\x04" b"byte\x02\xff\xc2\xf8i\xdc"),
    EventStreamMessage(
        prelude=MessagePrelude(
            total_length=0x17,
            headers_length=0x7,
            crc=0x29860158,
        ),
        headers={"byte": -1},
        payload=b"",
        crc=0xC2F869DC,
    ),
)

INT16_HEADER = (
    (b"\x00\x00\x00\x19\x00\x00\x00\tq\x0e\x92>\x05" b"short\x03\xff\xff\xb2|\xb6\xcc"),
    EventStreamMessage(
        prelude=MessagePrelude(
            total_length=0x19,
            headers_length=0x9,
            crc=0x710E923E,
        ),
        headers={"short": -1},
        payload=b"",
        crc=0xB27CB6CC,
    ),
)

INT32_HEADER = (
    (
        b"\x00\x00\x00\x1d\x00\x00\x00\r\x83\xe3\xf0\xe7\x07"
        b"integer\x04\xff\xff\xff\xff\x8b\x8e\x12\xeb"
    ),
    EventStreamMessage(
        prelude=MessagePrelude(
            total_length=0x1D,
            headers_length=0xD,
            crc=0x83E3F0E7,
        ),
        headers={"integer": -1},
        payload=b"",
        crc=0x8B8E12EB,
    ),
)

INT64_HEADER = (
    (
        b"\x00\x00\x00\x1e\x00\x00\x00\x0e]J\xdb\x8d\x04"
        b"long\x05\xff\xff\xff\xff\xff\xff\xff\xffK\xc22\xda"
    ),
    EventStreamMessage(
        prelude=MessagePrelude(
            total_length=0x1E,
            headers_length=0xE,
            crc=0x5D4ADB8D,
        ),
        headers={"long": -1},
        payload=b"",
        crc=0x4BC232DA,
    ),
)

PAYLOAD_NO_HEADERS = (
    b"\x00\x00\x00\x1d\x00\x00\x00\x00\xfdR\x8cZ{'foo':'bar'}\xc3e96",
    EventStreamMessage(
        prelude=MessagePrelude(
            total_length=0x1D,
            headers_length=0,
            crc=0xFD528C5A,
        ),
        headers={},
        payload=b"{'foo':'bar'}",
        crc=0xC3653936,
    ),
)

PAYLOAD_ONE_STR_HEADER = (
    (
        b"\x00\x00\x00=\x00\x00\x00 \x07\xfd\x83\x96\x0ccontent-type\x07\x00\x10"
        b"application/json{'foo':'bar'}\x8d\x9c\x08\xb1"
    ),
    EventStreamMessage(
        prelude=MessagePrelude(
            total_length=0x3D,
            headers_length=0x20,
            crc=0x07FD8396,
        ),
        headers={"content-type": "application/json"},
        payload=b"{'foo':'bar'}",
        crc=0x8D9C08B1,
    ),
)

ALL_HEADERS_TYPES = (
    (
        b"\x00\x00\x00\x62\x00\x00\x00\x52\x03\xb5\xcb\x9c"
        b"\x010\x00\x011\x01\x012\x02\x02\x013\x03\x00\x03"
        b"\x014\x04\x00\x00\x00\x04\x015\x05\x00\x00\x00\x00\x00\x00\x00\x05"
        b"\x016\x06\x00\x05bytes\x017\x07\x00\x04utf8"
        b"\x018\x08\x00\x00\x00\x00\x00\x00\x00\x08\x019\x090123456789abcdef"
        b"\x63\x35\x36\x71"
    ),
    EventStreamMessage(
        prelude=MessagePrelude(
            total_length=0x62,
            headers_length=0x52,
            crc=0x03B5CB9C,
        ),
        headers={
            "0": True,
            "1": False,
            "2": 0x02,
            "3": 0x03,
            "4": 0x04,
            "5": 0x05,
            "6": b"bytes",
            "7": "utf8",
            "8": 0x08,
            "9": b"0123456789abcdef",
        },
        payload=b"",
        crc=0x63353671,
    ),
)

ERROR_EVENT_MESSAGE = (
    (
        b"\x00\x00\x00\x52\x00\x00\x00\x42\xbf\x23\x63\x7e"
        b"\x0d:message-type\x07\x00\x05error"
        b"\x0b:error-code\x07\x00\x04code"
        b"\x0e:error-message\x07\x00\x07message"
        b"\x6b\x6c\xea\x3d"
    ),
    EventStreamMessage(
        prelude=MessagePrelude(
            total_length=0x52,
            headers_length=0x42,
            crc=0xBF23637E,
        ),
        headers={
            ":message-type": "error",
            ":error-code": "code",
            ":error-message": "message",
        },
        payload=b"",
        crc=0x6B6CEA3D,
    ),
)

# Tuples of encoded messages and their expected decoded output
POSITIVE_CASES = [
    EMPTY_MESSAGE,
    INT8_HEADER,
    INT16_HEADER,
    INT32_HEADER,
    INT64_HEADER,
    PAYLOAD_NO_HEADERS,
    PAYLOAD_ONE_STR_HEADER,
    ALL_HEADERS_TYPES,
    ERROR_EVENT_MESSAGE,
]

CORRUPTED_HEADER_LENGTH = (
    (
        b"\x00\x00\x00=\xFF\x00\x01\x02\x07\xfd\x83\x96\x0ccontent-type\x07\x00"
        b"\x10application/json{'foo':'bar'}\x8d\x9c\x08\xb1"
    ),
    InvalidHeadersLength,
)

CORRUPTED_HEADERS = (
    (
        b"\x00\x00\x00=\x00\x00\x00 \x07\xfd\x83\x96\x0ccontent+type\x07\x00\x10"
        b"application/json{'foo':'bar'}\x8d\x9c\x08\xb1"
    ),
    ChecksumMismatch,
)

CORRUPTED_LENGTH = (
    b"\x01\x00\x00\x1d\x00\x00\x00\x00\xfdR\x8cZ{'foo':'bar'}\xc3e96",
    InvalidPayloadLength,
)

CORRUPTED_PAYLOAD = (
    b"\x00\x00\x00\x1d\x00\x00\x00\x00\xfdR\x8cZ{'foo':'bar'\x8d\xc3e96",
    ChecksumMismatch,
)

DUPLICATE_HEADER = (
    (
        b"\x00\x00\x00\x24\x00\x00\x00\x14\x4b\xb9\x82\xd0"
        b"\x04test\x04asdf\x04test\x04asdf\xf3\xf4\x75\x63"
    ),
    DuplicateHeader,
)

# Tuples of encoded messages and their expected exception
NEGATIVE_CASES = [
    CORRUPTED_LENGTH,
    CORRUPTED_PAYLOAD,
    CORRUPTED_HEADERS,
    CORRUPTED_HEADER_LENGTH,
    DUPLICATE_HEADER,
]


class IdentityParser:
    def parse(self, event):
        return event


def assert_message_equal(message_a, message_b):
    """Asserts all fields for two messages are equal."""
    assert message_a.prelude.total_length == message_b.prelude.total_length
    assert message_a.prelude.headers_length == message_b.prelude.headers_length
    assert message_a.prelude.crc == message_b.prelude.crc
    assert message_a.headers == message_b.headers
    assert message_a.payload == message_b.payload
    assert message_a.crc == message_b.crc


def test_partial_message():
    """Ensure that we can receive partial payloads."""
    data = EMPTY_MESSAGE[0]
    event_buffer = EventStreamBuffer()
    # This mid point is an arbitrary break in the middle of the headers
    mid_point = 15
    event_buffer.add_data(data[:mid_point])
    messages = list(event_buffer)
    assert messages == []

    event_buffer.add_data(data[mid_point : len(data)])
    for message in event_buffer:
        assert_message_equal(message, EMPTY_MESSAGE[1])


def check_message_decodes(encoded, decoded):
    """Ensure the message decodes to what we expect."""
    event_buffer = EventStreamBuffer()
    event_buffer.add_data(encoded)
    messages = list(event_buffer)
    assert len(messages) == 1
    assert_message_equal(messages[0], decoded)


@pytest.mark.parametrize("encoded,decoded", POSITIVE_CASES)
def test_positive_cases(encoded, decoded):
    """Test that all positive cases decode how we expect."""
    check_message_decodes(encoded, decoded)


def test_all_positive_cases():
    """Test all positive cases can be decoded on the same buffer."""
    event_buffer = EventStreamBuffer()
    # add all positive test cases to the same buffer
    for (encoded, _) in POSITIVE_CASES:
        event_buffer.add_data(encoded)
    # collect all of the expected messages
    expected_messages = [decoded for (_, decoded) in POSITIVE_CASES]
    # collect all of the decoded messages
    decoded_messages = list(event_buffer)
    # assert all messages match what we expect
    for (expected, decoded) in zip(expected_messages, decoded_messages):
        assert_message_equal(expected, decoded)


@pytest.mark.parametrize("encoded,exception", NEGATIVE_CASES)
def test_negative_cases(encoded, exception):
    """Test that all negative cases raise the expected exception."""
    with pytest.raises(exception):
        check_message_decodes(encoded, None)


def test_header_parser():
    """Test that the header parser supports all header types."""
    headers_data = (
        b"\x010\x00\x011\x01\x012\x02\x02\x013\x03\x00\x03"
        b"\x014\x04\x00\x00\x00\x04\x015\x05\x00\x00\x00\x00\x00\x00\x00\x05"
        b"\x016\x06\x00\x05bytes\x017\x07\x00\x04utf8"
        b"\x018\x08\x00\x00\x00\x00\x00\x00\x00\x08\x019\x090123456789abcdef"
    )

    expected_headers = {
        "0": True,
        "1": False,
        "2": 0x02,
        "3": 0x03,
        "4": 0x04,
        "5": 0x05,
        "6": b"bytes",
        "7": "utf8",
        "8": 0x08,
        "9": b"0123456789abcdef",
    }

    parser = EventStreamHeaderParser()
    headers = parser.parse(headers_data)
    assert headers == expected_headers


def test_message_prelude_properties():
    """Test that calculated properties from the payload are correct."""
    # Total length: 40, Headers Length: 15, random crc
    prelude = MessagePrelude(40, 15, 0x00000000)
    assert prelude.payload_length == 9
    assert prelude.headers_end == 27
    assert prelude.payload_end == 36


def test_message_to_response_dict():
    response_dict = PAYLOAD_ONE_STR_HEADER[1].to_response_dict()
    assert response_dict["status_code"] == 200
    expected_headers = {"content-type": "application/json"}
    assert response_dict["headers"] == expected_headers
    assert response_dict["body"] == b"{'foo':'bar'}"


def test_message_to_response_dict_error():
    response_dict = ERROR_EVENT_MESSAGE[1].to_response_dict()
    assert response_dict["status_code"] == 400
    headers = {
        ":message-type": "error",
        ":error-code": "code",
        ":error-message": "message",
    }
    assert response_dict["headers"] == headers
    assert response_dict["body"] == b""


def test_unpack_uint8():
    (value, bytes_consumed) = DecodeUtils.unpack_uint8(b"\xDE")
    assert bytes_consumed == 1
    assert value == 0xDE


def test_unpack_uint32():
    (value, bytes_consumed) = DecodeUtils.unpack_uint32(b"\xDE\xAD\xBE\xEF")
    assert bytes_consumed == 4
    assert value == 0xDEADBEEF


def test_unpack_int8():
    (value, bytes_consumed) = DecodeUtils.unpack_int8(b"\xFE")
    assert bytes_consumed == 1
    assert value == -2


def test_unpack_int16():
    (value, bytes_consumed) = DecodeUtils.unpack_int16(b"\xFF\xFE")
    assert bytes_consumed == 2
    assert value == -2


def test_unpack_int32():
    (value, bytes_consumed) = DecodeUtils.unpack_int32(b"\xFF\xFF\xFF\xFE")
    assert bytes_consumed == 4
    assert value == -2


def test_unpack_int64():
    test_bytes = b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE"
    (value, bytes_consumed) = DecodeUtils.unpack_int64(test_bytes)
    assert bytes_consumed == 8
    assert value == -2


def test_unpack_array_short():
    test_bytes = b"\x00\x10application/json"
    (value, bytes_consumed) = DecodeUtils.unpack_byte_array(test_bytes)
    assert bytes_consumed == 18
    assert value == b"application/json"


def test_unpack_byte_array_int():
    (value, array_bytes_consumed) = DecodeUtils.unpack_byte_array(
        b"\x00\x00\x00\x10application/json", length_byte_size=4
    )
    assert array_bytes_consumed == 20
    assert value == b"application/json"


def test_unpack_utf8_string():
    length = b"\x00\x09"
    utf8_string = b"\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e"
    encoded = length + utf8_string
    (value, bytes_consumed) = DecodeUtils.unpack_utf8_string(encoded)
    assert bytes_consumed == 11
    assert value == utf8_string.decode("utf-8")


def test_unpack_prelude():
    data = b"\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x03"
    prelude = DecodeUtils.unpack_prelude(data)
    assert prelude == ((1, 2, 3), 12)


def create_mock_raw_stream(*data):
    raw_stream = Mock()

    async def chunks():
        for chunk in data:
            yield chunk
        yield b""

    raw_stream.chunks = chunks
    return raw_stream


@pytest.mark.asyncio
async def test_event_stream_wrapper_iteration():
    raw_stream = create_mock_raw_stream(
        b"\x00\x00\x00+\x00\x00\x00\x0e4\x8b\xec{\x08event-id\x04\x00",
        b"\x00\xa0\x0c{'foo':'bar'}\xd3\x89\x02\x85",
    )

    parser = IdentityParser()
    event_stream = EventStream(raw_stream, parser)
    events = []
    async for event in event_stream:
        events.append(event)
    assert len(events) == 1
    event = events[0]

    assert event.headers == {"event-id": 0x0000A00C}
    assert event.payload == b"{'foo':'bar'}"


SERIALIZATION_CASES = [
    # Empty headers and empty payload
    (b"\x00\x00\x00\x10\x00\x00\x00\x00\x05\xc2H\xeb}\x98\xc8\xff", {}, b""),
    # Empty headers with payload
    (
        b"\x00\x00\x00\x1c\x00\x00\x00\x00\xc02\xa5\xeatest payload\x076E\xf9",
        {},
        b"test payload",
    ),
    # Header true value, type 0
    (
        b"\x00\x00\x00\x16\x00\x00\x00\x06c\xe1\x18~\x04true\x00\xf1\xe7\xbc\xd7",
        {"true": True},
        b"",
    ),
    # Header false value, type 1
    (
        b"\x00\x00\x00\x17\x00\x00\x00\x07)\x86\x01X\x05false\x01R1~\xf4",
        {"false": False},
        b"",
    ),
    # Header byte, type 2
    (
        b"\x00\x00\x00\x17\x00\x00\x00\x07)\x86\x01X\x04byte\x02\xff\xc2\xf8i\xdc",
        {"byte": Int8HeaderValue(-1)},
        b"",
    ),
    # Header short, type 3
    (
        b"\x00\x00\x00\x19\x00\x00\x00\tq\x0e\x92>\x05short\x03\xff\xff\xb2|\xb6\xcc",
        {"short": Int16HeaderValue(-1)},
        b"",
    ),
    # Header integer, type 4
    (
        b"\x00\x00\x00\x1d\x00\x00\x00\r\x83\xe3\xf0\xe7\x07integer\x04\xff\xff\xff\xff\x8b\x8e\x12\xeb",
        {"integer": Int32HeaderValue(-1)},
        b"",
    ),
    # Header integer, by default integers will be serialized as 32bits
    (
        b"\x00\x00\x00\x1d\x00\x00\x00\r\x83\xe3\xf0\xe7\x07integer\x04\xff\xff\xff\xff\x8b\x8e\x12\xeb",
        {"integer": -1},
        b"",
    ),
    # Header long, type 5
    (
        b"\x00\x00\x00\x1e\x00\x00\x00\x0e]J\xdb\x8d\x04long\x05\xff\xff\xff\xff\xff\xff\xff\xffK\xc22\xda",
        {"long": Int64HeaderValue(-1)},
        b"",
    ),
    # Header bytes, type 6
    (
        b"\x00\x00\x00\x1d\x00\x00\x00\r\x83\xe3\xf0\xe7\x05bytes\x06\x00\x04\xde\xad\xbe\xef\x9a\xabK ",
        {"bytes": b"\xde\xad\xbe\xef"},
        b"",
    ),
    # Header string, type 7
    (
        b"\x00\x00\x00 \x00\x00\x00\x10\xb9T\xe0\t\x06string\x07\x00\x06foobarL\xc53(",
        {"string": "foobar"},
        b"",
    ),
    # Header timestamp, type 8
    (
        b"\x00\x00\x00#\x00\x00\x00\x13g\xfd\xcbc\ttimestamp\x08\x00\x00\x01r\xee\xbc'\xa6\xd4D^\x11",
        {
            "timestamp": datetime.datetime(
                2020,
                6,
                26,
                hour=3,
                minute=46,
                second=47,
                microsecond=846000,
                tzinfo=datetime.timezone.utc,
            )
        },
        b"",
    ),
    # Header UUID, type 9
    (
        b"\x00\x00\x00&\x00\x00\x00\x16\xdfw\xb0\x9c\x04uuid\t\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef\xb1g\xd4{",
        {"uuid": uuid.UUID("deadbeef-dead-beef-dead-beefdeadbeef")},
        b"",
    ),
]


class TestEventStreamMessageSerializer:
    @pytest.fixture
    def serializer(self):
        return EventStreamMessageSerializer()

    @pytest.mark.parametrize("expected, headers, payload", SERIALIZATION_CASES)
    def test_serialized_message(self, serializer, expected, headers, payload):
        serialized = serializer.serialize(headers, payload)
        assert expected == serialized

    def test_encode_headers(self, serializer):
        headers = {"foo": "bar"}
        encoded_headers = serializer.encode_headers(headers)
        assert b"\x03foo\x07\x00\x03bar" == encoded_headers

    def test_invalid_header_value(self, serializer):
        # Str header value len are stored in a uint16 but cannot be larger
        # than 2 ** 15 - 1
        headers = {
            "foo": 2.0,
        }
        with pytest.raises(InvalidHeaderValue):
            serializer.serialize(headers, b"")

    def test_header_str_too_long(self, serializer):
        # Str header value len are stored in a uint16 but cannot be larger
        # than 2 ** 15 - 1
        headers = {
            "foo": "a" * (2**16 - 1),
        }
        with pytest.raises(HeaderValueBytesExceedMaxLength):
            serializer.serialize(headers, b"")

    def test_header_bytes_too_long(self, serializer):
        # Bytes header value len are stored in a uint16 but cannot be larger
        # than 2 ** 15 - 1
        headers = {
            "foo": b"a" * (2**16 - 1),
        }
        with pytest.raises(HeaderValueBytesExceedMaxLength):
            serializer.serialize(headers, b"")

    def test_headers_too_long(self, serializer):
        # These headers are rougly 150k bytes, more than 128 KiB max
        long_header_value = b"a" * 30000
        headers = {
            "a": long_header_value,
            "b": long_header_value,
            "c": long_header_value,
            "d": long_header_value,
            "e": long_header_value,
        }
        with pytest.raises(HeaderBytesExceedMaxLength):
            serializer.serialize(headers, b"")

    def test_payload_too_long(self, serializer):
        # 18 MiB payaload, larger than the max of 16 MiB
        payload = b"abcdefghijklmnopqr" * (1024**2)
        with pytest.raises(PayloadBytesExceedMaxLength):
            serializer.serialize({}, payload)


class TestEventSigner:
    @pytest.fixture
    def credentials(self):
        return Credentials("foo", "bar", None)

    @pytest.fixture
    def event_signer(self):
        return EventSigner(
            "signing-name",
            "region-name",
            utc_now=self.utc_now,
        )

    def utc_now(self):
        return datetime.datetime(
            2020, 7, 23, 22, 39, 55, 29943, tzinfo=datetime.timezone.utc
        )

    def test_basic_event_signature(self, event_signer, credentials):
        signed_headers = event_signer.sign(b"message", b"prior", credentials)
        assert signed_headers[":date"] == self.utc_now()
        expected_signature = (
            b"\x0e\xf5n\xbf\x8cW\x0b>\xf3\xdc\x9fA\x99^\xd17\xcd"
            b"\x86\x9c\xdb\xa0Y\x18\x88+\x9b\x10p{n$e"
        )
        assert signed_headers[":chunk-signature"] == expected_signature
