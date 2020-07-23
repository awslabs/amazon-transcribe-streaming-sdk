import asyncio
from typing import Optional

from awscrt.auth import AwsCredentials, AwsCredentialsProvider


class Credentials(AwsCredentials):
    """Wrapper for CRT Credentials internals"""

    pass


class CredentialResolver:
    async def get_credentials(self) -> Optional[Credentials]:
        raise NotImplementedError("get_credentials")


class AwsCrtCredentialResolver(CredentialResolver):
    """Default Credential resolution chain provided by CRT."""

    def __init__(self, eventloop):
        self._crt_resolver = AwsCredentialsProvider.new_default_chain(
            eventloop
        )

    async def get_credentials(self) -> Optional[Credentials]:
        credentials = await asyncio.wrap_future(
            self._crt_resolver.get_credentials()
        )
        return credentials


class StaticCredentialResolver(Credentials, CredentialResolver):
    """Hardcoded credentials provided from a static source."""

    async def get_credentials(self) -> Optional[Credentials]:
        return self
