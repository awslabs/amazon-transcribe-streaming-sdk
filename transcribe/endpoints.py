class BaseEndpointResolver:
    """Asynchronous endpoint resolver"""

    async def resolve(self, region: str) -> str:
        """This is currently stubbed out until we have a complete
        and async endpoint resolution implementation.
        """
        raise NotImplementedError


class StaticEndpointResolver(BaseEndpointResolver):
    def __init__(self, endpoint):
        self._endpoint: str = endpoint

    async def resolve(self, region: str) -> str:
        """We ignore the region and return our static endpoint."""
        return self._endpoint


class _TranscribeRegionEndpointResolver(BaseEndpointResolver):
    async def resolve(self, region: str) -> str:
        """Apply region to transcribe uri template."""
        return f"https://transcribestreaming.{region}.amazonaws.com"
