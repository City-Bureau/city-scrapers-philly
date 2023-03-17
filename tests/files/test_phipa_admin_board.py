from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import BOARD
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.phipa_admin_board import PhipaAdminBoardSpider

test_response = file_response(
    join(dirname(__file__), "files", "phipa_admin_board.html"),
    url="https://www.phila.gov/departments/administrative-board/",
)
spider = PhipaAdminBoardSpider()

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
    assert parsed_items[0]["title"] == "Administrative Board Virtual Hearing"


# def test_description():
#     assert parsed_items[0]["description"] == "EXPECTED DESCRIPTION"


def test_start():
    assert parsed_items[0]["start"] == datetime(2023, 4, 14, 10, 30)


def test_end():
    assert parsed_items[0]["end"] == datetime(2023, 4, 14, 11, 0)


# def test_time_notes():
#     assert parsed_items[0]["time_notes"] == "EXPECTED TIME NOTES"


def test_id():
    assert (
        parsed_items[0]["id"]
        == "phipa_admin_board/202304141030/x/administrative_board_virtual_hearing"
    )


# def test_status():
#     assert parsed_items[0]["status"] == "EXPECTED STATUS"


def test_location():
    assert parsed_items[0]["location"] == {
        "name": "City Hall - Room 215",
        "address": "1400 John F Kennedy Blvd, Philadelphia, PA 19107",
    }


def test_source():
    assert (
        parsed_items[0]["source"]
        == "https://www.phila.gov/departments/administrative-board/"
    )


def test_links():
    assert parsed_items[0]["links"] == [
        {
            "href": "https://www.phila.gov/departments/administrative-board/#2rtr08fuk6bq91ueaikb1dk8ii_20230414T143000Z",  # noqa
            "title": "Meeting Information",
        }
    ]


def test_classification():
    assert parsed_items[0]["classification"] == BOARD


@pytest.mark.parametrize("item", parsed_items)
def test_all_day(item):
    assert item["all_day"] is False
