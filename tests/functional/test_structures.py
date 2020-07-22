from io import BytesIO

import pytest

from transcribe.structures import BufferableByteStream


@pytest.fixture()
def byte_stream():
    return BufferableByteStream()


class TestBufferableByteStream:
    def test_byte_stream_write(self, byte_stream):
        size = byte_stream.write(b"test byte chunk")
        assert size == 15
        assert byte_stream._byte_chunks == [b"test byte chunk"]

        size = byte_stream.write(b"second chunk")
        assert size == 12
        assert byte_stream._byte_chunks == [
            b"test byte chunk",
            b"second chunk",
        ]

    @pytest.mark.parametrize(
        "test_input",
        [None, "test", BytesIO(b"test"), {"test": "chunk"}, ["test"]],
    )
    def test_byte_stream_write_nonbytes(self, test_input, byte_stream):
        with pytest.raises(ValueError):
            byte_stream.write(test_input)

    def test_byte_stream_write_closed(self, byte_stream):
        byte_stream.close()
        with pytest.raises(IOError):
            byte_stream.write(b"test")

    def test_byte_stream_write_done(self, byte_stream):
        byte_stream.end_stream()
        with pytest.raises(IOError):
            byte_stream.write(b"test")

    def test_byte_stream_write_empty_bytes(self, byte_stream):
        size = byte_stream.write(b"")
        assert size == 0
        assert byte_stream.read() is None

    def test_byte_stream_read(self, byte_stream):
        byte_stream.write(b"test")
        assert byte_stream.read() == b"test"

    def test_byte_stream_read_size(self, byte_stream):
        byte_stream.write(b"test byte chunk")
        byte_stream.write(b"second chunk")
        assert byte_stream.read(7) == b"test by"
        assert byte_stream.read(100) == b"te chunk"

    def test_byte_stream_read_empty(self, byte_stream):
        assert byte_stream.read() is None

    def test_byte_stream_read_closed(self, byte_stream):
        byte_stream.close()
        assert byte_stream.read() == b""

    def test_byte_stream_read_done(self, byte_stream):
        byte_stream.write(b"test")
        byte_stream.end_stream()
        assert byte_stream.read() == b"test"
        assert byte_stream.read() == b""

    def test_byte_stream_read1(self, byte_stream):
        byte_stream.write(b"test")
        assert byte_stream.read1() == b"test"

    def test_byte_stream_read1_size(self, byte_stream):
        byte_stream.write(b"test byte chunk")
        byte_stream.write(b"second chunk")
        assert byte_stream.read1(7) == b"test by"
        assert byte_stream.read1(100) == b"te chunk"

    def test_byte_stream_readinto(self, byte_stream):
        b = bytearray(10)
        byte_stream.write(b"test byte chunk")
        byte_stream.readinto(b)
        assert b == b"test byte "
        byte_stream.readinto(b)
        assert b == b"chunkbyte "

    def test_byte_stream_readinto1(self, byte_stream):
        b = bytearray(10)
        byte_stream.write(b"test byte chunk")
        byte_stream.readinto1(b)
        assert b == b"test byte "
        byte_stream.readinto1(b)
        assert b == b"chunkbyte "

    def test_byte_stream_read_write_after_empty(self, byte_stream):
        byte_stream.write(b"test")
        assert byte_stream.read() == b"test"
        byte_stream.write(b"chunk")
        assert byte_stream.read() == b"chunk"
        assert byte_stream.read() is None
        byte_stream.write(b"next")
        assert byte_stream.read() == b"next"
