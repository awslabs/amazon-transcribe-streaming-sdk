from collections.abc import MutableMapping
from io import BufferedIOBase, BytesIO
from typing import Dict, List, Optional, Tuple, Union
import json

from transcribe.exceptions import ValidationException


class Request:
    BODY_TYPE = Union[BytesIO, BufferedIOBase]

    def __init__(
        self, endpoint, path="/", method="GET", headers=None, body=None, params=None
    ):
        self.endpoint: str = endpoint
        self.path: str = path
        self.method: str = method
        self.headers: Dict = headers if headers is not None else {}
        self.params: Dict = params if params is not None else {}
        self.body = body

    def prepare(self):
        method: str = self.prepare_method()
        query_str: str = self.prepare_params()
        headers: HeadersDict = self.prepare_headers()
        body: BODY_TYPE = self.prepare_body()
        return PreparedRequest(
            self.endpoint, self.path, method, headers, body, query_str
        )

    def prepare_method(self) -> str:
        return self.method.upper()

    def prepare_params(self) -> str:
        """Converts dictionary of params into query string"""
        query_list = []
        for k, v in self.params.items():
            if v is None:
                # empty values should just apply the key
                # e.g. foo=None, bar=baz -> foo&bar=baz
                query_list.append(k)
            else:
                query_list.append(f"{k}={v}")
        return "&".join(query_list)

    def prepare_headers(self) -> "HeadersDict":
        prepared_headers = HeadersDict()
        prepared_headers.update(self.headers)
        return prepared_headers

    def prepare_body(self) -> BODY_TYPE:
        body = self.body
        if body is None:
            return BytesIO(b"")
        elif isinstance(body, str):
            return BytesIO(body.encode("utf-8"))
        elif isinstance(body, dict):
            body = json.dumps(self.body)
            return BytesIO(body.encode("utf-8"))
        elif isinstance(body, bytes):
            return BytesIO(body)
        elif not isinstance(body, BufferedIOBase):
            type_ = type(body)
            raise ValidationException(
                "Body provided is an unexpected type ({type_}). Request was "
                "expecting bytes, str, or file-like body."
            )

        return body


class PreparedRequest:
    def __init__(self, endpoint, path, method, headers, body, query_str):
        self.endpoint: str = endpoint
        self.path: str = path
        self.method: str = method
        self.headers: Dict = headers
        self.body: BytesIO = body
        self.query: str = query_str

    @property
    def uri(self) -> str:
        endpoint = self.endpoint.rstrip("/")
        path = self.path.lstrip("/")
        output_uri = "/".join([endpoint, path])
        if self.query:
            output_uri = "?".join([output_uri, self.query])
        return output_uri


class _HeaderKey:
    def __init__(self, key: str):
        self._key = key
        self._lower = key.lower()

    def __hash__(self):
        return hash(self._lower)

    def __eq__(self, other):
        return isinstance(other, _HeaderKey) and self._lower == other._lower

    def __str__(self):
        return self._key

    def __repr__(self):
        return repr(self._key)


class HeadersDict(MutableMapping):
    """A case-insenseitive dictionary to represent HTTP headers. """

    LIST_TYPE = Union[Tuple[str, ...], List[str]]
    HEADER_VALUE_TYPE = Union[str, LIST_TYPE]

    def __init__(self, *args, **kwargs):
        self._dict: Dict = {}
        self.update(*args, **kwargs)

    def __setitem__(self, key: str, value: HEADER_VALUE_TYPE):
        key, value = self._validate_header(key, value)
        self._dict[_HeaderKey(key)] = value

    def __getitem__(self, key: str):
        return self._dict[_HeaderKey(key)]

    def __delitem__(self, key: str):
        del self._dict[_HeaderKey(key)]

    def __iter__(self):
        return (str(key) for key in self._dict)

    def __len__(self):
        return len(self._dict)

    def __repr__(self):
        return repr(self._dict)

    def copy(self) -> "HeadersDict":
        return HeadersDict(self.items())

    def _validate_str(self, string: str) -> str:
        if string is None:
            return string
        # newline characters are prohibited in headers
        for seq in ("\r\n", "\r", "\n"):
            string = string.replace(seq, "")
        return string.strip(" ")

    def _validate_header_list(
        self, key: str, values: LIST_TYPE
    ) -> Tuple[str, HEADER_VALUE_TYPE]:
        value_list = [self._validate_str(v) for v in values if v is not None]
        return self._validate_str(key), ";".join(value_list)

    def _validate_header(
        self, key: str, value: HEADER_VALUE_TYPE
    ) -> Tuple[str, HEADER_VALUE_TYPE]:
        if key is None:
            raise ValidationException("Unexpected key (None) was provided in headers")
        if isinstance(value, (tuple, list)):
            return self._validate_header_list(key, value)
        return self._validate_str(key), self._validate_str(value)
