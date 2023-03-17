from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import NOT_CLASSIFIED
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.phipa_csc import PhipaCscSpider

test_response = file_response(
    join(dirname(__file__), "files", "phipa_csc.html"),
    url="https://www.phila.gov/departments/civil-service-commission/",
)
spider = PhipaCscSpider()

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
    assert parsed_items[0]["title"] == "CSC Virtual Hearing"


# def test_description():
#     assert parsed_items[0]["description"] == "EXPECTED DESCRIPTION"


def test_start():
    assert parsed_items[0]["start"] == datetime(2023, 3, 21, 10, 0)


def test_end():
    assert parsed_items[0]["end"] == datetime(2023, 3, 21, 12, 0)


# def test_time_notes():
#     assert parsed_items[0]["time_notes"] == "EXPECTED TIME NOTES"


def test_id():
    assert parsed_items[0]["id"] == "phipa_csc/202303211000/x/csc_virtual_hearing"


# def test_status():
#     assert parsed_items[0]["status"] == "EXPECTED STATUS"


def test_location():
    assert parsed_items[0]["location"] == {
        "name": "Municipal Services Building ",
        "address": "1401 John F. Kennedy Blvd., 16th Floor Philadelphia, PA 19102",
    }


def test_source():
    assert (
        parsed_items[0]["source"]
        == "https://www.phila.gov/departments/civil-service-commission/"
    )  # noqa


def test_links():
    assert parsed_items[0]["links"] == [
        {
            "href": "https://www.phila.gov/departments/civil-service-commission/#45up2rclqpsodh333nh2fob1fv_20230321T140000Z",  # noqa
            "title": "Meeting Information",
        }
    ]


def test_classification():
    assert parsed_items[0]["classification"] == NOT_CLASSIFIED


@pytest.mark.parametrize("item", parsed_items)
def test_all_day(item):
    assert item["all_day"] is False
