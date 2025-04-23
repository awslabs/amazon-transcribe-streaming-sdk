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
        if region.startswith('cn'):
            return f"https://transcribestreaming.{region}.amazonaws.com.cn"
        else:
            return f"https://transcribestreaming.{region}.amazonaws.com"
