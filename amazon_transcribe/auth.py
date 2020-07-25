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
