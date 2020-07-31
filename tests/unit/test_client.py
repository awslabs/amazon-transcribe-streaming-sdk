import pytest

from amazon_transcribe.client import TranscribeStreamingClient


class TestClientSetup:
    def test_basic_client_setup(self):
        client = TranscribeStreamingClient(region="us-west-2")
        assert client.service_name == "transcribe"
        assert client.region == "us-west-2"
        assert client._endpoint_resolver is not None

    def test_client_setup_without_region(self):
        # The client must take a keyword `region`
        with pytest.raises(TypeError) as e:
            client = TranscribeStreamingClient()
