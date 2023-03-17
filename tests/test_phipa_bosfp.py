from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import BOARD
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.phipa_bosfp import PhipaBosfpSpider

test_response = file_response(
    join(dirname(__file__), "files", "phipa_bosfp.html"),
    url="https://www.phila.gov/departments/board-of-safety-and-fire-prevention/",
)
spider = PhipaBosfpSpider()

freezer = freeze_time("2023-03-17")
freezer.start()

parsed_items = [item for item in spider.parse(test_response)]

freezer.stop()


"""
Uncomment below
def test_tests():
    print("Please write some tests for this spider or at least disable this one.")
    assert False
"""


def test_title():
    assert parsed_items[0]["title"] == "Board of Safety and Fire Prevention"


# def test_description():
#     assert parsed_items[0]["description"] == "EXPECTED DESCRIPTION"


def test_start():
    assert parsed_items[0]["start"] == datetime(2023, 3, 28, 9, 0)


def test_end():
    assert parsed_items[0]["end"] == datetime(2023, 3, 28, 13, 0)


# def test_time_notes():
#     assert parsed_items[0]["time_notes"] == "EXPECTED TIME NOTES"


def test_id():
    assert (
        parsed_items[0]["id"]
        == "phipa_bosfp/202303280900/x/board_of_safety_and_fire_prevention"
    )


# def test_status():
#     assert parsed_items[0]["status"] == "EXPECTED STATUS"


def test_location():
    assert parsed_items[0]["location"] == {
        "name": "BOSFP Office",
        "address": "240 Spring Garden St., Philadelphia, PA 19123-2991",
    }


def test_source():
    assert (
        parsed_items[0]["source"]
        == "https://www.phila.gov/departments/board-of-safety-and-fire-prevention/"
    )


def test_links():
    assert parsed_items[0]["links"] == [
        {
            "href": "https://www.phila.gov/departments/board-of-safety-and-fire-prevention/#1sq8brmjg7gd3e47kepm2nuuk6_20230328T130000Z",  # noqa
            "title": "Meeting Information",
        }
    ]


def test_classification():
    assert parsed_items[0]["classification"] == BOARD


@pytest.mark.parametrize("item", parsed_items)
def test_all_day(item):
    assert item["all_day"] is False
