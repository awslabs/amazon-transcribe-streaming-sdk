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
from typing import Dict, Optional

from amazon_transcribe.request import HeadersDict


class Response:
    def __init__(self, status_code: int = 500, headers: Optional[Dict] = None):
        self.status_code = status_code
        if headers is None:
            headers = {}
        self.headers = HeadersDict(headers)
