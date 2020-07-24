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


class HTTPException(SDKError):
    """Base error for HTTP related exceptions"""


class ServiceException(SDKError):
    """Errors returned by the service"""


class UnknownServiceException(ServiceException):
    def __init__(self, status_code, error_code, message):
        self.status_code: int = status_code
        self.error_code: int = error_code
        self.message: str = message


class BadRequestException(ServiceException):
    def __init__(self, message):
        self.message: str = message
        self.status_code: int = 400


class ConflictException(ServiceException):
    def __init__(self, message):
        self.message: str = message
        self.status_code = 409


class InternalFailureException(ServiceException):
    def __init__(self, message):
        self.message: str = message
        self.status_code: int = 500


class LimitExceededException(ServiceException):
    def __init__(self, message):
        self.message: str = message
        self.error: int = 429


class ServiceUnavailableException(ServiceException):
    def __init__(self, message):
        self.message: str = message
        self.status_code: int = 503


class ValidationException(SDKError):
    """Encountered an issue validating a given value"""


class SerializationException(SDKError):
    """Encountered an issue when seralizing a request or event"""


class CredentialsException(SDKError):
    """Encountered an issue while resolving or using credentials"""
