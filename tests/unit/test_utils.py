import pytest

from amazon_transcribe.utils import ensure_boolean


class TestEnsureBoolean:
    @pytest.mark.parametrize(
        "val,expected_val",
        [
            (True, True),
            (False, False),
            ("True", True),
            ("False", False),
            ("true", True),
            ("false", False),
            ("TrUe", True),
            ("foo", False),
        ],
    )
    def test_ensure_boolean(self, val, expected_val):
        assert ensure_boolean(val) == expected_val
