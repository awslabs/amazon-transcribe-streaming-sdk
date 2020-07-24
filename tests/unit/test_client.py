from amazon_transcribe.client import TranscribeStreamingClient, create_client


class TestClientSetup:
    def test_basic_client_setup(self):
        client = TranscribeStreamingClient("us-west-2")
        assert client.service_name == "transcribe"
        assert client.region == "us-west-2"
        assert client._endpoint_resolver is not None

    def test_create_default_client(self):
        client = create_client()
        assert client.service_name == "transcribe"
        assert client.region == "us-east-2"
        assert client._endpoint_resolver is not None

    def test_create_client_with_region(self):
        client = create_client("eu-south-1")
        assert client.service_name == "transcribe"
        assert client.region == "eu-south-1"
        assert client._endpoint_resolver is not None
