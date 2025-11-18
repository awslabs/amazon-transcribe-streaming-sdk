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

"""Tests for BufferableByteStream threading behavior and CPU efficiency."""

import time
import threading
import pytest

from amazon_transcribe.structures import BufferableByteStream


class TestBufferableByteStreamThreading:
    """Tests to verify the threading.Event-based implementation prevents CPU spinning."""

    def test_read_timeout_prevents_busy_wait(self):
        """Test that read waits efficiently instead of spinning in a tight loop."""
        byte_stream = BufferableByteStream(read_timeout=0.1)
        
        start_time = time.time()
        with pytest.raises(BlockingIOError):
            byte_stream.read()
        elapsed = time.time() - start_time
        
        # Should wait close to the timeout period (within reasonable margin)
        assert 0.08 <= elapsed <= 0.15, f"Expected ~0.1s wait, got {elapsed}s"

    def test_blocking_read_with_none_timeout(self):
        """Test that None timeout creates a blocking read that waits indefinitely."""
        byte_stream = BufferableByteStream(read_timeout=None)
        
        def write_after_delay():
            time.sleep(0.2)
            byte_stream.write(b"delayed data")
        
        writer_thread = threading.Thread(target=write_after_delay)
        writer_thread.start()
        
        start_time = time.time()
        data = byte_stream.read()
        elapsed = time.time() - start_time
        
        writer_thread.join()
        
        assert data == b"delayed data"
        # Should have waited for the data (at least 0.2s)
        assert elapsed >= 0.19

    def test_immediate_return_when_data_available(self):
        """Test that read returns immediately when data is already available."""
        byte_stream = BufferableByteStream(read_timeout=1.0)
        byte_stream.write(b"immediate data")
        
        start_time = time.time()
        data = byte_stream.read()
        elapsed = time.time() - start_time
        
        assert data == b"immediate data"
        # Should return almost instantly (definitely less than timeout)
        assert elapsed < 0.1

    def test_event_signaling_on_write(self):
        """Test that writing data signals the event so waiting readers wake up."""
        byte_stream = BufferableByteStream(read_timeout=5.0)
        result = {"data": None, "elapsed": None}
        
        def reader():
            start = time.time()
            result["data"] = byte_stream.read()
            result["elapsed"] = time.time() - start
        
        reader_thread = threading.Thread(target=reader)
        reader_thread.start()
        
        # Give reader time to start waiting
        time.sleep(0.05)
        
        # Write data - should wake up the reader immediately
        byte_stream.write(b"signaled data")
        reader_thread.join(timeout=2.0)
        
        assert result["data"] == b"signaled data"
        # Reader should wake up quickly after write, not wait full timeout
        assert result["elapsed"] < 1.0

    def test_event_cleared_after_reading_all_data(self):
        """Test that the event is cleared when buffer becomes empty."""
        byte_stream = BufferableByteStream(read_timeout=0.1)
        
        # Write and read data
        byte_stream.write(b"test")
        byte_stream.read()
        
        # Event should be cleared now, so next read should wait/timeout
        start_time = time.time()
        with pytest.raises(BlockingIOError):
            byte_stream.read()
        elapsed = time.time() - start_time
        
        # Should have waited for the timeout
        assert elapsed >= 0.08

    def test_event_set_on_end_stream(self):
        """Test that ending stream signals waiting readers."""
        byte_stream = BufferableByteStream(read_timeout=5.0)
        result = {"data": None, "elapsed": None}
        
        def reader():
            start = time.time()
            try:
                result["data"] = byte_stream.read()
            except BlockingIOError:
                result["data"] = "blocked"
            result["elapsed"] = time.time() - start
        
        reader_thread = threading.Thread(target=reader)
        reader_thread.start()
        
        # Give reader time to start waiting
        time.sleep(0.05)
        
        # End stream - should wake up reader
        byte_stream.end_stream()
        reader_thread.join(timeout=2.0)
        
        assert result["data"] == b""
        # Reader should wake up quickly after end_stream
        assert result["elapsed"] < 1.0

    def test_event_set_on_close(self):
        """Test that closing stream signals waiting readers."""
        byte_stream = BufferableByteStream(read_timeout=5.0)
        result = {"data": None, "elapsed": None}
        
        def reader():
            start = time.time()
            try:
                result["data"] = byte_stream.read()
            except BlockingIOError:
                result["data"] = "blocked"
            result["elapsed"] = time.time() - start
        
        reader_thread = threading.Thread(target=reader)
        reader_thread.start()
        
        # Give reader time to start waiting
        time.sleep(0.05)
        
        # Close stream - should wake up reader
        byte_stream.close()
        reader_thread.join(timeout=2.0)
        
        assert result["data"] == b""
        # Reader should wake up quickly after close
        assert result["elapsed"] < 1.0

    def test_sequential_read_write_cycles(self):
        """Test that sequential read-write cycles work correctly (typical usage pattern)."""
        byte_stream = BufferableByteStream(read_timeout=0.5)
        results = []
        
        def writer():
            for i in range(3):
                time.sleep(0.1)
                byte_stream.write(f"data{i}".encode())
            byte_stream.end_stream()
        
        def reader():
            while True:
                try:
                    data = byte_stream.read()
                    if data == b"":
                        break
                    results.append(data)
                except BlockingIOError:
                    continue
        
        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)
        
        writer_thread.start()
        reader_thread.start()
        
        writer_thread.join(timeout=2.0)
        reader_thread.join(timeout=2.0)
        
        # All data should have been read
        assert len(results) == 3
        assert b"data0" in results
        assert b"data1" in results
        assert b"data2" in results

    def test_custom_timeout_configuration(self):
        """Test that custom timeout values work correctly."""
        # Test with very short timeout
        byte_stream_short = BufferableByteStream(read_timeout=0.05)
        start_time = time.time()
        with pytest.raises(BlockingIOError):
            byte_stream_short.read()
        elapsed = time.time() - start_time
        assert 0.04 <= elapsed <= 0.1
        
        # Test with longer timeout
        byte_stream_long = BufferableByteStream(read_timeout=0.3)
        start_time = time.time()
        with pytest.raises(BlockingIOError):
            byte_stream_long.read()
        elapsed = time.time() - start_time
        assert 0.25 <= elapsed <= 0.4

    def test_no_cpu_spin_under_continuous_polling(self):
        """
        Test that continuous polling doesn't cause excessive CPU usage.
        
        This simulates the original problem where tight loops would cause 100% CPU.
        With threading.Event, the CPU should remain low as threads wait efficiently.
        """
        byte_stream = BufferableByteStream(read_timeout=0.1)
        stop_flag = threading.Event()
        poll_count = {"count": 0}
        
        def continuous_poller():
            while not stop_flag.is_set():
                try:
                    byte_stream.read()
                except BlockingIOError:
                    poll_count["count"] += 1
        
        poller_thread = threading.Thread(target=continuous_poller)
        poller_thread.start()
        
        # Let it run for 0.5 seconds
        time.sleep(0.5)
        stop_flag.set()
        poller_thread.join(timeout=2.0)
        
        # With 0.1s timeout, we should get roughly 5 polls in 0.5s (not thousands)
        # Allow some variance due to timing
        assert 3 <= poll_count["count"] <= 8, \
            f"Expected ~5 polls, got {poll_count['count']}"

    def test_remaining_bytes_keeps_event_set(self):
        """Test that partial reads keep the event set when data remains."""
        byte_stream = BufferableByteStream(read_timeout=0.1)
        byte_stream.write(b"long data chunk")
        
        # Read only part of the data
        chunk1 = byte_stream.read(5)
        assert chunk1 == b"long "
        
        # Next read should return immediately (no timeout wait)
        start_time = time.time()
        chunk2 = byte_stream.read(5)
        elapsed = time.time() - start_time
        
        assert chunk2 == b"data "
        assert elapsed < 0.05  # Should be nearly instant

