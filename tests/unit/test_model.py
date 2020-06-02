import pytest

from transcribe.exceptions import ValidationException
from transcribe.model import (
    Item,
    ItemList,
    MediaSampleRateHertz,
    StringOption,
    ValidatedString,
)


class TestModel:
    @pytest.mark.parametrize("value", ["values", "here", ""])
    def test_StringOption_valid(self, value):
        enums = (
            "test",
            "values",
            "here",
            "",
        )
        string_opt = StringOption(enums, value)
        assert string_opt.value == value
        assert string_opt.enum_values == enums

    @pytest.mark.parametrize(
        "enums,value",
        [(("test",), "here"), (("test", "values"), None), (("test", "here"), "")],
    )
    def test_StringOption_invalid(self, enums, value):
        with pytest.raises(ValidationException):
            sopt = StringOption(enums, value)

    @pytest.mark.parametrize(
        "value,min_,max_,pattern",
        [
            ("", None, None, None),
            ("value", None, None, None),
            ("foobar", 1, None, None),
            ("foo", 1, 3, None),
            ("foo", None, 20, None),
            ("foo", 1, 3, r"[a-z]*"),
            ("foobar", None, None, r"[a-z]*"),
        ],
    )
    def test_ValidatedString_valid(self, min_, max_, pattern, value):
        val_str = ValidatedString(value, min_, max_, pattern)
        assert val_str.value == value

    @pytest.mark.parametrize(
        "value,min_,max_,pattern",
        [
            ("", 1, None, None),
            ("foobar", 1, 3, None),
            ("foo13ar", 1, 20, r"[a-z]*"),
            ("foob4r", None, None, r"[a-z]*"),
        ],
    )
    def test_ValidatedString_invalid(self, value, min_, max_, pattern):
        with pytest.raises(ValidationException):
            ValidatedString(value, min_, max_, pattern)

    def test_media_sample_rate_hertz_validation(self):
        sample_rate = MediaSampleRateHertz(9000)
        assert sample_rate.value == 9000

    def test_media_sample_rate_hertz_invalid(self):
        with pytest.raises(ValidationException):
            sample_rate = MediaSampleRateHertz(0)

    def test_custom_list_class(self):
        item_one = Item(50.1, 50.5, "pronunciation", "hi", False)
        item_two = Item(1000, 1001, "punctuation", "!", False)

        item_list = ItemList([item_one, item_two])
        assert item_list[0] == item_one
        assert item_list[1] == item_two
