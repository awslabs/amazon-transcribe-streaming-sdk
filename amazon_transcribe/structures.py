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
import threading

if TYPE_CHECKING:
    # We need to import this from _typeshed as this is not publicly exposed and
    # would otherwise require us to redefine this type to subclass
    # BufferedIOBase
    from _typeshed import ReadableBuffer


class BufferableByteStream(BufferedIOBase):
    """BufferableByteStream will always be in non-blocking mode
    
    This class uses threading.Event to efficiently signal when data is available,
    avoiding busy-wait loops that cause high CPU usage.
    """

    def __init__(self, read_timeout: Optional[float] = 0.1):
        """Initialize the BufferableByteStream.
        
        Args:
            read_timeout: Timeout in seconds for read operations when no data
                is available. Set to None for blocking reads, or a float value
                for the maximum time to wait. Default is 0.1 seconds.
        """
        self._byte_chunks: list = []
        self.__done: bool = False
        self.__closed: bool = False
        self._data_available = threading.Event()
        self._read_timeout = read_timeout

    def read(self, size=-1) -> Optional[bytes]:  # type: ignore
        # If no data is available and stream is not done, wait for data
        if len(self._byte_chunks) < 1 and not self.__done:
            # Wait for data to become available or stream to complete
            data_ready = self._data_available.wait(timeout=self._read_timeout)
            
            # After waiting, check again if data is available
            if len(self._byte_chunks) < 1 and not self.__done:
                raise BlockingIOError("read")
        
        # Stream is done and no more data
        if (self.__done and not self._byte_chunks) or self.closed:
            return b""

        temp_bytes = self._byte_chunks.pop(0)
        
        # Clear the event if no more data is available
        if len(self._byte_chunks) == 0 and not self.__done:
            self._data_available.clear()
        
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
            # Data is still available, keep event set
            self._data_available.set()
        
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
            # Signal that data is now available
            self._data_available.set()

        return len(b)

    @property
    def closed(self) -> bool:
        return self.__closed

    def close(self):
        self._buffered_bytes_chunks = None
        self.__done = True
        self.__closed = True
        # Signal that stream is done so readers can exit
        self._data_available.set()

    def end_stream(self):
        self.__done = True
        # Signal that stream is done so readers can exit
        self._data_available.set()
