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


__version__ = "0.6.0"

from awscrt.io import ClientBootstrap, DefaultHostResolver, EventLoopGroup


class AWSCRTEventLoop:
    def __init__(self):
        self.bootstrap = self._initialize_default_loop()

    def _initialize_default_loop(self):
        event_loop_group = EventLoopGroup(1)
        host_resolver = DefaultHostResolver(event_loop_group)
        return ClientBootstrap(
            event_loop_group,
            host_resolver,
        )
