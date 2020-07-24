from urllib.parse import urlsplit
from typing import Dict, Union

from amazon_transcribe import __version__ as version
from amazon_transcribe.exceptions import ValidationException

HEADER_VALUE = Union[int, None, str]


def _add_required_headers(endpoint: str, headers: Dict[str, HEADER_VALUE]):
    urlparts = urlsplit(endpoint)
    if not urlparts.hostname:
        raise ValidationException(
            "Unexpected endpoint ({endpoint}) provided to serializer"
        )
    headers.update(
        {
            "user-agent": f"transcribe-streaming-sdk-{version}",
            "host": urlparts.hostname,
        }
    )
