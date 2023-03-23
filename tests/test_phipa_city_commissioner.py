from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import BOARD
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.phipa_city_commissioner import PhipaCityCommissionerSpider

test_response = file_response(
    join(dirname(__file__), "files", "phipa_city_commissioner.html"),
    url="https://vote.phila.gov/resources-data/commissioner-meetings/commissioner-meetings/",  # noqa
)
spider = PhipaCityCommissionerSpider()

freezer = freeze_time("2023-03-22")
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
    assert parsed_items[0]["title"] == "City Commissioners Board Meetings"


# def test_description():
#     assert parsed_items[0]["description"] == "EXPECTED DESCRIPTION"


def test_start():
    assert parsed_items[0]["start"] == datetime(2023, 3, 15, 11, 0)


# def test_end():
#    assert parsed_items[0]["end"] == datetime(2023, 3, 15, 13, 0)


def test_time_notes():
    assert (
        parsed_items[0]["time_notes"]
        == "Please double check the web page for the meeting time noted at top of the page"  # noqa
    )  # noqa


def test_id():
    assert (
        parsed_items[0]["id"]
        == "phipa_city_commissioner/202303151100/x/city_commissioners_board_meetings"  # noqa
    )  # noqa


# def test_status():
#     assert parsed_items[0]["status"] == "EXPECTED STATUS"


def test_location():
    assert parsed_items[0]["location"] == {
        "name": "City Hall Room-202",
        "address": "1400 JFK Boulevard Philadelphia, PA 19107",
    }


def test_source():
    assert (
        parsed_items[0]["source"]
        == "https://vote.phila.gov/resources-data/commissioner-meetings/commissioner-meetings/"  # noqa
    )  # noqa


def test_links():
    assert parsed_items[0]["links"] == [
        {
            "href": "https://vote.phila.gov/media/Agenda_for_3-15-2023.pdf",
            "title": "Agenda",
        }
    ]


def test_classification():
    assert parsed_items[0]["classification"] == BOARD


@pytest.mark.parametrize("item", parsed_items)
def test_all_day(item):
    assert item["all_day"] is False
