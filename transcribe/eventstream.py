# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Binary Event Stream Decoding """
import uuid
import datetime
from typing import Any, Callable, Dict, Generator, Optional, Tuple, Union, Type

from binascii import crc32
from io import BytesIO
from struct import unpack, pack

# byte length of the prelude (total_length + header_length + prelude_crc)
_PRELUDE_LENGTH = 12
_MAX_HEADERS_LENGTH = 128 * 1024  # 128 Kb
_MAX_HEADER_VALUE_BYTE_LENGTH = 32 * 1024 - 1
_MAX_PAYLOAD_LENGTH = 16 * 1024 ** 2  # 16 Mb

HEADER_VALUE = Union[bool, bytes, int, str]


class ParserError(Exception):
    """Base binary flow encoding parsing exception."""


class DuplicateHeader(ParserError):
    """Duplicate header found in the event."""

    def __init__(self, header: str):
        message = 'Duplicate header present: "%s"' % header
        super(DuplicateHeader, self).__init__(message)


class InvalidHeadersLength(ParserError):
    """Headers length is longer than the maximum."""

    def __init__(self, length: int):
        message = "Header length of %s exceeded the maximum of %s" % (
            length,
            _MAX_HEADERS_LENGTH,
        )
        super().__init__(message)


class InvalidPayloadLength(ParserError):
    """Payload length is longer than the maximum."""

    def __init__(self, length: int):
        message = "Payload length of %s exceeded the maximum of %s" % (
            length,
            _MAX_PAYLOAD_LENGTH,
        )
        super().__init__(message)


class ChecksumMismatch(ParserError):
    """Calculated checksum did not match the expected checksum."""

    def __init__(self, expected: int, calculated: int):
        message = "Checksum mismatch: expected 0x%08x, calculated 0x%08x" % (
            expected,
            calculated,
        )
        super().__init__(message)


class NoInitialResponseError(ParserError):
    """An event of type initial-response was not received.

    This exception is raised when the event stream produced no events or
    the first event in the stream was not of the initial-response type.
    """

    def __init__(self):
        message = "First event was not of the initial-response type"
        super().__init__(message)


class EventStreamError(Exception):
    """Error with the event stream process."""


class SerializationError(Exception):
    """Base binary flow encoding serialization exception."""


class InvalidHeaderValue(SerializationError):
    def __init__(self, value):
        message = f"Invalid header value type: {type(value)}"
        super(InvalidHeaderValue, self).__init__(message)
        self.value = value


class HeaderBytesExceedMaxLength(SerializationError):
    def __init__(self, length):
        message = (
            f"Headers exceeded max serialization "
            f"length of 128 KiB at {length} bytes"
        )
        super(HeaderBytesExceedMaxLength, self).__init__(message)


class HeaderValueBytesExceedMaxLength(SerializationError):
    def __init__(self, length):
        message = (
            f"Header bytes value exceeds max serialization "
            f"length of (32 KiB - 1) at {length} bytes"
        )
        super(HeaderValueBytesExceedMaxLength, self).__init__(message)


class PaylodBytesExceedMaxLength(SerializationError):
    def __init__(self, length):
        message = (
            f"Payload exceeded max serialization "
            f"length of 16 MiB at {length} bytes"
        )
        super(PaylodBytesExceedMaxLength, self).__init__(message)


class HeaderValue:
    """A wrapper class for explicit header serialization."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError


class Int8HeaderValue(HeaderValue):
    """Value that should be explicitly serialized as an int8."""

    def __init__(self, value: int):
        self.value = value


class Int16HeaderValue(HeaderValue):
    """Value that should be explicitly serialized as an int16"""

    def __init__(self, value: int):
        self.value = value


class Int32HeaderValue(HeaderValue):
    """Value that should be explicitly serialized as an int32"""

    def __init__(self, value: int):
        self.value = value


class Int64HeaderValue(HeaderValue):
    """Value that should be explicitly serialized as an int64"""

    def __init__(self, value: int):
        self.value = value


# Possible types for serializing headers differs from possible types returned when decoding
HEADER_SERIALIZATION_VALUE = Union[
    bool, bytes, int, str, uuid.UUID, datetime.datetime, HeaderValue
]
HEADERS_SERIALIZATION_DICT = Dict[str, HEADER_SERIALIZATION_VALUE]


class EventStreamMessageSerializer:
    DEFAULT_INT_TYPE: Type[HeaderValue] = Int32HeaderValue

    def serialize(
        self, headers: HEADERS_SERIALIZATION_DICT, payload: bytes
    ) -> bytes:
        # TODO: Investigate preformance of this once we can make requests
        if len(payload) > _MAX_PAYLOAD_LENGTH:
            raise PaylodBytesExceedMaxLength(len(payload))
        # The encoded headers are variable length and this length
        # is required to generate the prelude, generate the headers first
        encoded_headers = self._encode_headers(headers)
        if len(encoded_headers) > _MAX_HEADERS_LENGTH:
            raise HeaderBytesExceedMaxLength(len(encoded_headers))
        prelude_bytes = self._encode_prelude(encoded_headers, payload)
        # Calculate the prelude_crc and it's byte representation
        prelude_crc = self._calculate_checksum(prelude_bytes)
        prelude_crc_bytes = pack("!I", prelude_crc)
        messages_bytes = prelude_crc_bytes + encoded_headers + payload
        # Calculate the checksum continuing from the prelude crc
        final_crc = self._calculate_checksum(messages_bytes, crc=prelude_crc)
        final_crc_bytes = pack("!I", final_crc)
        return prelude_bytes + messages_bytes + final_crc_bytes

    def _encode_headers(self, headers: HEADERS_SERIALIZATION_DICT) -> bytes:
        encoded = b""
        for key, val in headers.items():
            encoded += self._encode_header_key(key)
            encoded += self._encode_header_val(val)
        return encoded

    def _encode_header_key(self, key: str) -> bytes:
        enc = key.encode("utf-8")
        return pack("B", len(enc)) + enc

    def _encode_header_val(self, val: HEADER_SERIALIZATION_VALUE) -> bytes:
        # Handle booleans first to avoid being viewed as ints
        if val is True:
            return b"\x00"
        elif val is False:
            return b"\x01"

        if isinstance(val, int):
            val = self.DEFAULT_INT_TYPE(val)

        if isinstance(val, Int8HeaderValue):
            return b"\x02" + pack("!b", val.value)
        elif isinstance(val, Int16HeaderValue):
            return b"\x03" + pack("!h", val.value)
        elif isinstance(val, Int32HeaderValue):
            return b"\x04" + pack("!i", val.value)
        elif isinstance(val, Int64HeaderValue):
            return b"\x05" + pack("!q", val.value)
        elif isinstance(val, bytes):
            # Byte arrays are prefaced with a 16bit length, but are restricted
            # to a max length of 2**15 - 1, enforce this explicitly
            if len(val) > _MAX_HEADER_VALUE_BYTE_LENGTH:
                raise HeaderValueBytesExceedMaxLength(len(val))
            return b"\x06" + pack("!H", len(val)) + val
        elif isinstance(val, str):
            utf8_string = val.encode("utf-8")
            # Strings are prefaced with a 16bit length, but are restricted
            # to a max length of 2**15 - 1, enforce this explicitly
            if len(utf8_string) > _MAX_HEADER_VALUE_BYTE_LENGTH:
                raise HeaderValueBytesExceedMaxLength(len(utf8_string))
            return b"\x07" + pack("!H", len(utf8_string)) + utf8_string
        elif isinstance(val, datetime.datetime):
            ms_timestamp = int(val.timestamp() * 1000)
            return b"\x08" + pack("!q", ms_timestamp)
        elif isinstance(val, uuid.UUID):
            return b"\x09" + val.bytes
        raise InvalidHeaderValue(val)

    def _encode_prelude(self, encoded_headers: bytes, payload: bytes) -> bytes:
        header_length = len(encoded_headers)
        payload_length = len(payload)
        total_length = header_length + payload_length + 16
        return pack("!II", total_length, header_length)

    def _calculate_checksum(self, data: bytes, crc: int = 0) -> int:
        return crc32(data, crc) & 0xFFFFFFFF


class DecodeUtils:
    """Unpacking utility functions used in the decoder.

    All methods on this class take raw bytes and return  a tuple containing
    the value parsed from the bytes and the number of bytes consumed to parse
    that value.
    """

    UINT8_BYTE_FORMAT = "!B"
    UINT16_BYTE_FORMAT = "!H"
    UINT32_BYTE_FORMAT = "!I"
    INT8_BYTE_FORMAT = "!b"
    INT16_BYTE_FORMAT = "!h"
    INT32_BYTE_FORMAT = "!i"
    INT64_BYTE_FORMAT = "!q"
    PRELUDE_BYTE_FORMAT = "!III"

    # uint byte size to unpack format
    UINT_BYTE_FORMAT = {
        1: UINT8_BYTE_FORMAT,
        2: UINT16_BYTE_FORMAT,
        4: UINT32_BYTE_FORMAT,
    }

    @staticmethod
    def unpack_true(data: bytes) -> Tuple[bool, int]:
        """This method consumes none of the provided bytes and returns True"""
        return True, 0

    @staticmethod
    def unpack_false(data: bytes) -> Tuple[bool, int]:
        """This method consumes none of the provided bytes and returns False."""
        return False, 0

    @staticmethod
    def unpack_uint8(data: bytes) -> Tuple[int, int]:
        """Parse an unsigned 8-bit integer from the bytes."""
        value = unpack(DecodeUtils.UINT8_BYTE_FORMAT, data[:1])[0]
        return value, 1

    @staticmethod
    def unpack_uint32(data: bytes) -> Tuple[int, int]:
        """Parse an unsigned 32-bit integer from the bytes."""
        value = unpack(DecodeUtils.UINT32_BYTE_FORMAT, data[:4])[0]
        return value, 4

    @staticmethod
    def unpack_int8(data):
        """Parse a signed 8-bit integer from the bytes.

        :type data: bytes
        :param data: The bytes to parse from.

        :rtype: (int, int)
        :returns: A tuple containing the (parsed integer value, bytes consumed)
        """
        value = unpack(DecodeUtils.INT8_BYTE_FORMAT, data[:1])[0]
        return value, 1

    @staticmethod
    def unpack_int16(data: bytes) -> Tuple[int, int]:
        """Parse a signed 16-bit integer from the bytes."""
        value = unpack(DecodeUtils.INT16_BYTE_FORMAT, data[:2])[0]
        return value, 2

    @staticmethod
    def unpack_int32(data: bytes) -> Tuple[int, int]:
        """Parse a signed 32-bit integer from the bytes."""
        value = unpack(DecodeUtils.INT32_BYTE_FORMAT, data[:4])[0]
        return value, 4

    @staticmethod
    def unpack_int64(data: bytes) -> Tuple[int, int]:
        """Parse a signed 64-bit integer from the bytes."""
        value = unpack(DecodeUtils.INT64_BYTE_FORMAT, data[:8])[0]
        return value, 8

    @staticmethod
    def unpack_byte_array(
        data: bytes, length_byte_size=2
    ) -> Tuple[bytes, int]:
        """Parse a variable length byte array from the bytes.

        The bytes are expected to be in the following format:
            [ length ][0 ... length bytes]
        where length is an unsigned integer represented in the smallest number
        of bytes to hold the maximum length of the array.
        """
        uint_byte_format = DecodeUtils.UINT_BYTE_FORMAT[length_byte_size]
        length = unpack(uint_byte_format, data[:length_byte_size])[0]
        bytes_end = length + length_byte_size
        array_bytes = data[length_byte_size:bytes_end]
        return array_bytes, bytes_end

    @staticmethod
    def unpack_utf8_string(data: bytes, length_byte_size=2) -> Tuple[str, int]:
        """Parse a variable length utf-8 string from the bytes.

        The bytes are expected to be in the following format:
            [ length ][0 ... length bytes]
        where length is an unsigned integer represented in the smallest number
        of bytes to hold the maximum length of the array and the following
        bytes are a valid utf-8 string.
        """
        array_bytes, consumed = DecodeUtils.unpack_byte_array(
            data, length_byte_size
        )
        return array_bytes.decode("utf-8"), consumed

    @staticmethod
    def unpack_uuid(data: bytes) -> Tuple[bytes, int]:
        """Parse a 16-byte uuid from the bytes."""
        return data[:16], 16

    @staticmethod
    def unpack_prelude(data: bytes) -> Tuple[Tuple[Any, ...], int]:
        """Parse the prelude for an event stream message from the bytes.

        The prelude for an event stream message has the following format:
            [total_length][header_length][prelude_crc]
        where each field is an unsigned 32-bit integer.
        """
        return (unpack(DecodeUtils.PRELUDE_BYTE_FORMAT, data), _PRELUDE_LENGTH)


def _validate_checksum(data: bytes, checksum: int, crc=0):
    # To generate the same numeric value across all Python versions and
    # platforms use crc32(data) & 0xffffffff.
    computed_checksum = crc32(data, crc) & 0xFFFFFFFF
    if checksum != computed_checksum:
        raise ChecksumMismatch(checksum, computed_checksum)


class MessagePrelude:
    """Represents the prelude of an event stream message. """

    def __init__(self, total_length: int, headers_length: int, crc: int):
        self.total_length = total_length
        self.headers_length = headers_length
        self.crc = crc

    @property
    def payload_length(self) -> int:
        """Calculates the total payload length.

        The extra minus 4 bytes is for the message CRC.
        """
        return self.total_length - self.headers_length - _PRELUDE_LENGTH - 4

    @property
    def payload_end(self) -> int:
        """Calculates the byte offset for the end of the message payload.

        The extra minus 4 bytes is for the message CRC.
        """
        return self.total_length - 4

    @property
    def headers_end(self) -> int:
        """Calculates the byte offset for the end of the message headers."""
        return _PRELUDE_LENGTH + self.headers_length


class EventStreamMessage:
    """Represents an event stream message. """

    def __init__(self, prelude, headers, payload, crc):
        self.prelude: MessagePrelude = prelude
        self.headers: Dict = headers
        self.payload: BytesIO = payload
        self.crc: int = crc

    def to_response_dict(self, status_code=200) -> Dict[str, Any]:
        message_type = self.headers.get(":message-type")
        if message_type == "error" or message_type == "exception":
            status_code = 400
        return {
            "status_code": status_code,
            "headers": self.headers,
            "body": self.payload,
        }


class EventStreamHeaderParser:
    """ Parses the event headers from an event stream message.

    Expects all of the header data upfront and creates a dictionary of headers
    to return. This object can be reused multiple times to parse the headers
    from multiple event stream messages.
    """

    # Maps header type to appropriate unpacking function
    # These unpacking functions return the value and the amount unpacked
    _HEADER_TYPE_MAP: Dict[
        int, Callable[[bytes], Tuple[HEADER_VALUE, int]]
    ] = {
        # boolean_true
        0: DecodeUtils.unpack_true,
        # boolean_false
        1: DecodeUtils.unpack_false,
        # byte
        2: DecodeUtils.unpack_int8,
        # short
        3: DecodeUtils.unpack_int16,
        # integer
        4: DecodeUtils.unpack_int32,
        # long
        5: DecodeUtils.unpack_int64,
        # byte_array
        6: DecodeUtils.unpack_byte_array,
        # string
        7: DecodeUtils.unpack_utf8_string,
        # timestamp
        8: DecodeUtils.unpack_int64,
        # uuid
        9: DecodeUtils.unpack_uuid,
    }

    def __init__(self):
        self._data = None

    def parse(self, data: bytes) -> Dict[str, HEADER_VALUE]:
        """Parses the event stream headers from an event stream message."""
        self._data = data
        return self._parse_headers()

    def _parse_headers(self) -> Dict[str, HEADER_VALUE]:
        headers = {}
        while self._data:
            name, value = self._parse_header()
            if name in headers:
                raise DuplicateHeader(name)
            headers[name] = value
        return headers

    def _parse_header(self) -> Tuple[str, HEADER_VALUE]:
        name = self._parse_name()
        value = self._parse_value()
        return name, value

    def _parse_name(self) -> str:
        name, consumed = DecodeUtils.unpack_utf8_string(self._data, 1)
        self._advance_data(consumed)
        return name

    def _parse_type(self) -> int:
        type, consumed = DecodeUtils.unpack_uint8(self._data)
        self._advance_data(consumed)
        return type

    def _parse_value(self) -> HEADER_VALUE:
        header_type = self._parse_type()
        value_unpacker = self._HEADER_TYPE_MAP[header_type]
        value, consumed = value_unpacker(self._data)
        self._advance_data(consumed)
        return value

    def _advance_data(self, consumed):
        self._data = self._data[consumed:]


class EventStreamBuffer:
    """Streaming based event stream buffer

    A buffer class that wraps bytes from an event stream providing parsed
    messages as they become available via an iterable interface.
    """

    def __init__(self):
        self._data: bytes = b""
        self._prelude = None
        self._header_parser = EventStreamHeaderParser()

    def add_data(self, data: bytes):
        """Add data to the buffer."""
        self._data += data

    def _validate_prelude(self, prelude: MessagePrelude):
        if prelude.headers_length > _MAX_HEADERS_LENGTH:
            raise InvalidHeadersLength(prelude.headers_length)

        if prelude.payload_length > _MAX_PAYLOAD_LENGTH:
            raise InvalidPayloadLength(prelude.payload_length)

    def _parse_prelude(self) -> MessagePrelude:
        prelude_bytes = self._data[:_PRELUDE_LENGTH]
        raw_prelude, _ = DecodeUtils.unpack_prelude(prelude_bytes)
        prelude = MessagePrelude(*raw_prelude)
        self._validate_prelude(prelude)
        # The minus 4 removes the prelude crc from the bytes to be checked
        _validate_checksum(prelude_bytes[: _PRELUDE_LENGTH - 4], prelude.crc)
        return prelude

    def _parse_headers(self) -> Dict[str, str]:
        header_bytes = self._data[_PRELUDE_LENGTH : self._prelude.headers_end]
        return self._header_parser.parse(header_bytes)

    def _parse_payload(self) -> bytes:
        prelude = self._prelude
        payload_bytes = self._data[prelude.headers_end : prelude.payload_end]
        return payload_bytes

    def _parse_message_crc(self) -> int:
        prelude = self._prelude
        crc_bytes = self._data[prelude.payload_end : prelude.total_length]
        message_crc, _ = DecodeUtils.unpack_uint32(crc_bytes)
        return message_crc

    def _parse_message_bytes(self) -> bytes:
        # The minus 4 includes the prelude crc to the bytes to be checked
        message_bytes = self._data[
            _PRELUDE_LENGTH - 4 : self._prelude.payload_end
        ]
        return message_bytes

    def _validate_message_crc(self) -> int:
        message_crc = self._parse_message_crc()
        message_bytes = self._parse_message_bytes()
        _validate_checksum(message_bytes, message_crc, crc=self._prelude.crc)
        return message_crc

    def _parse_message(self) -> EventStreamMessage:
        crc = self._validate_message_crc()
        headers = self._parse_headers()
        payload = self._parse_payload()
        message = EventStreamMessage(self._prelude, headers, payload, crc)
        self._prepare_for_next_message()
        return message

    def _prepare_for_next_message(self):
        # Advance the data and reset the current prelude
        self._data = self._data[self._prelude.total_length :]
        self._prelude = None

    def next(self) -> EventStreamMessage:
        """Provides the next available message parsed from the stream"""
        if len(self._data) < _PRELUDE_LENGTH:
            raise StopIteration()

        if self._prelude is None:
            self._prelude = self._parse_prelude()

        if len(self._data) < self._prelude.total_length:
            raise StopIteration()

        return self._parse_message()

    def __next__(self):
        return self.next()

    def __iter__(self):
        return self


class EventStream:
    """Wrapper class for an event stream body.

    This wraps the underlying streaming body, parsing it for individual events
    and yielding them as they come available through the iterator interface.
    """

    def __init__(self, raw_stream, parser):
        self._raw_stream = raw_stream
        self._parser = parser
        self._event_generator: Generator = self._create_raw_event_generator()

    def __iter__(self):
        for event in self._event_generator:
            parsed_event = self._parse_event(event)
            if parsed_event:
                yield parsed_event

    def _create_raw_event_generator(self) -> Generator:
        event_stream_buffer = EventStreamBuffer()
        for chunk in self._raw_stream.stream():
            event_stream_buffer.add_data(chunk)
            for event in event_stream_buffer:
                yield event

    def _parse_event(self, event: EventStreamMessage) -> Dict:
        response_dict = event.to_response_dict()
        parsed_response = self._parser.parse(response_dict)
        if response_dict["status_code"] == 200:
            return parsed_response
        else:
            raise EventStreamError(parsed_response)

    def get_initial_response(self) -> EventStreamMessage:
        try:
            initial_event = next(self._event_generator)
            event_type = initial_event.headers.get(":event-type")
            if event_type == "initial-response":
                return initial_event
        except StopIteration:
            pass
        raise NoInitialResponseError()

    def close(self):
        """Closes the underlying streaming body. """
        self._raw_stream.close()
