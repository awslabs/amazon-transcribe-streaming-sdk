import asyncio
from typing import Optional

from awscrt.auth import AwsCredentialsProvider


class Credentials:
    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        session_token: Optional[str] = None,
    ):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token


class CredentialResolver:
    async def get_credentials(self) -> Optional[Credentials]:
        raise NotImplementedError("get_credentials")


class AwsCrtCredentialResolver(CredentialResolver):
    """Default Credential resolution chain provided by CRT."""

    def __init__(self, eventloop):
        self._crt_resolver = AwsCredentialsProvider.new_default_chain(eventloop)

    async def get_credentials(self) -> Optional[Credentials]:
        credentials = await asyncio.wrap_future(self._crt_resolver.get_credentials())
        return credentials


class StaticCredentialResolver(Credentials, CredentialResolver):
    """Hardcoded credentials provided from a static source."""

    async def get_credentials(self) -> Optional[Credentials]:
        return self
