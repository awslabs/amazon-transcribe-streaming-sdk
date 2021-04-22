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
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # We need to import this from _typeshed as this is not publicly exposed and
    # would otherwise require us to redefine this type to subclass
    # BufferedIOBase
    from _typeshed import ReadableBuffer


class BufferableByteStream(BufferedIOBase):
    """ BufferableByteStream will always be in non-blocking mode """

    def __init__(self):
        self._byte_chunks: list = []
        self.__done: bool = False
        self.__closed: bool = False

    def read(self, size=-1) -> Optional[bytes]:  # type: ignore
        if len(self._byte_chunks) < 1 and not self.__done:
            raise BlockingIOError("read")
        elif (self.__done and not self._byte_chunks) or self.closed:
            return b""

        temp_bytes = self._byte_chunks.pop(0)
        remaining_bytes = b""
        if size == -1:
            return temp_bytes
        elif size > 0:
            remaining_bytes = temp_bytes[size:]
            temp_bytes = temp_bytes[:size]
        else:
            remaining_bytes = temp_bytes
            temp_bytes = b""

        if len(remaining_bytes) > 0:
            self._byte_chunks.insert(0, remaining_bytes)
        return temp_bytes

    def read1(self, size=-1) -> Optional[bytes]:  # type: ignore
        return self.read(size)

    def readinto(self, b, read1=False):
        if not isinstance(b, memoryview):
            b = memoryview(b)
            b = b.cast("B")

        if read1:
            data = self.read1(len(b))
        else:
            data = self.read(len(b))

        if data is None:
            raise BlockingIOError("readinto")

        n = len(data)

        b[:n] = data

        return n

    def write(self, b: "ReadableBuffer") -> int:
        if not isinstance(b, bytes):
            type_ = type(b)
            raise ValueError(
                f"Unexpected value written to BufferableByteStream. "
                f"Only bytes are support but {type_} was provided."
            )

        if self.closed or self.__done:
            raise IOError("Stream is completed and doesn't support further writes.")

        if b:
            self._byte_chunks.append(b)

        return len(b)

    @property
    def closed(self) -> bool:
        return self.__closed

    def close(self):
        self._buffered_bytes_chunks = None
        self.__done = True
        self.__closed = True

    def end_stream(self):
        self.__done = True
