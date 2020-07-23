import pytest

from transcribe import AWSCRTEventLoop

@pytest.fixture
def default_eventloop():
    return AWSCRTEventLoop().bootstrap
