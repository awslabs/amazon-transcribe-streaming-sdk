import pytest
from transcribe import exceptions

CLASSES = [
    (name, cls)
    for name, cls in vars(exceptions).items()
    if isinstance(cls, type) and name != "SDKError"
]


def test_classes_setup():
    assert len(CLASSES) > 1
    first_entry = CLASSES[0]
    assert isinstance(first_entry[0], str)
    assert issubclass(first_entry[1], Exception)


@pytest.mark.parametrize("name, cls", CLASSES)
def test_exceptions_all_sdk_errors(name, cls):
    assert issubclass(cls, exceptions.SDKError)
