from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import BOARD
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.phipa_health_board import PhipaHealthBoardSpider

test_response = file_response(
    join(dirname(__file__), "files", "phipa_health_board.html"),
    url="https://www.phila.gov/departments/board-of-health/",
)
spider = PhipaHealthBoardSpider()

freezer = freeze_time("2023-03-16")
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
    assert parsed_items[0]["title"] == "Philadelphia Board of Health Meeting"


# def test_description():
#     assert parsed_items[0]["description"] == "EXPECTED DESCRIPTION"


def test_start():
    assert parsed_items[0]["start"] == datetime(2023, 4, 13, 18, 30)


def test_end():
    assert parsed_items[0]["end"] == datetime(2023, 4, 13, 20, 0)


# def test_time_notes():
#     assert parsed_items[0]["time_notes"] == "EXPECTED TIME NOTES"


def test_id():
    assert (
        parsed_items[0]["id"]
        == "phipa_health_board/202304131830/x/philadelphia_board_of_health_meeting"
    )


# def test_status():
#     assert parsed_items[0]["status"] == "EXPECTED STATUS"


def test_location():
    assert parsed_items[0]["location"] == {
        "name": "Board Of Health",
        "address": "1101 Market Street, 9th Floor, Philadelphia, PA 19107",
    }


def test_source():
    assert (
        parsed_items[0]["source"]
        == "https://www.phila.gov/departments/board-of-health/"
    )


def test_links():
    assert parsed_items[0]["links"] == [
        {
            "href": "https://www.phila.gov/departments/board-of-health/#7h53224k7r7voudlmqh37pq3fh",  # noqa
            "title": "Meeting Information",
        }
    ]


def test_classification():
    assert parsed_items[0]["classification"] == BOARD


@pytest.mark.parametrize("item", parsed_items)
def test_all_day(item):
    assert item["all_day"] is False
