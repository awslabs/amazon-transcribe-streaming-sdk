import pytest

from transcribe.endpoints import (
    BaseEndpointResolver,
    StaticEndpointResolver,
    _TranscribeRegionEndpointResolver,
)


class TestBaseEndpointResolver:
    @pytest.mark.asyncio
    async def test_resolve(self):
        with pytest.raises(NotImplementedError):
            endpoint = await BaseEndpointResolver().resolve("test-region")


class TestStaticEndpointResolver:
    @pytest.mark.parametrize(
        "endpoint",
        [
            "https://my-custom-endpoint.amazonaws.com",
            "https://transcribe-test.amazonaws.com",
            "https://localhost:8000",
        ],
    )
    @pytest.mark.asyncio
    async def test_resolve(self, endpoint):
        static = StaticEndpointResolver(endpoint)
        assert await static.resolve("us-west-2") == endpoint


class TestTranscribeRegionEndpointResolver:
    @pytest.mark.parametrize(
        "region", ["us-west-2", "eu-south-1", "af-south-1" "us-east-2"],
    )
    @pytest.mark.asyncio
    async def test_resolve(self, region):
        resolver = _TranscribeRegionEndpointResolver()
        expected = f"https://transcribestreaming.{region}.amazonaws.com"
        assert await resolver.resolve(region) == expected
