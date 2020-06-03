import pytest

from transcribe.model import Item, ItemList


class TestModel:

    def test_custom_list_class(self):
        item_one = Item(50.1, 50.5, "pronunciation", "hi", False)
        item_two = Item(1000, 1001, "punctuation", "!", False)

        item_list = ItemList([item_one, item_two])
        assert item_list[0] == item_one
        assert item_list[1] == item_two
