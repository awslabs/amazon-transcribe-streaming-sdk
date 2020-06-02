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


class SDKError(Exception):
    """Base Error for Amazon Transcribe Streaming SDK"""


class ModeledException(SDKError):
    """Error defined in provided service model"""


class BadRequestException(ModeledException):
    def __init__(self, message):
        self.message: str = message
        self.status_code: int = 400


class ConflictException(ModeledException):
    def __init__(self, message):
        self.message: str = message
        self.status_code = 409


class InternalFailureException(ModeledException):
    def __init__(self, message):
        self.message: str = message
        self.status_code: int = 500


class LimitExceededException(ModeledException):
    def __init__(self, message):
        self.message: str = message
        self.error: int = 429


class ServiceUnavailableException(ModeledException):
    def __init__(self, message):
        self.message: str = message
        self.status_code: int = 503


class ValidationException(SDKError):
    """Encountered an issue validating a given value"""
