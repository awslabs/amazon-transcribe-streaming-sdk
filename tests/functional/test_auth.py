import pytest

from transcribe.auth import StaticCredentialResolver


class TestCredentialResolvers:
    @pytest.mark.asyncio
    async def test_static_resolver_setup(self):
        cred_resolver = StaticCredentialResolver("test_id", "53cr37", "session_1")
        creds = await cred_resolver.get_credentials()
        assert creds is not None
        assert creds.access_key_id == "test_id"
        assert creds.secret_access_key == "53cr37"
        assert creds.session_token == "session_1"
