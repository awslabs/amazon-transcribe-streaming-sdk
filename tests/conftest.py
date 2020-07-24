import pytest

from amazon_transcribe import AWSCRTEventLoop


@pytest.fixture
def default_eventloop():
    return AWSCRTEventLoop().bootstrap
