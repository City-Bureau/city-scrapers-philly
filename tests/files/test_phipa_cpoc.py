from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import NOT_CLASSIFIED
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.phipa_cpoc import PhipaCpocSpider

test_response = file_response(
    join(dirname(__file__), "files", "phipa_cpoc.html"),
    url="https://www.phila.gov/departments/citizens-police-oversight-commission/",
)
spider = PhipaCpocSpider()

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
    assert parsed_items[0]["title"] == "CPOC March Virtual Town Hall"


# def test_description():
#     assert parsed_items[0]["description"] == "EXPECTED DESCRIPTION"


def test_start():
    assert parsed_items[0]["start"] == datetime(2023, 3, 21, 18, 0)


def test_end():
    assert parsed_items[0]["end"] == datetime(2023, 3, 21, 19, 30)


# def test_time_notes():
#     assert parsed_items[0]["time_notes"] == "EXPECTED TIME NOTES"


def test_id():
    assert (
        parsed_items[0]["id"]
        == "phipa_cpoc/202303211800/x/cpoc_march_virtual_town_hall"
    )


# def test_status():
#     assert parsed_items[0]["status"] == "EXPECTED STATUS"


def test_location():
    assert parsed_items[0]["location"] == {
        "name": "CPOC Offices",
        "address": "1515 Arch St. 11th Floor, Philadelphia, PA 19102",
    }


def test_source():
    assert (
        parsed_items[0]["source"]
        == "https://www.phila.gov/departments/citizens-police-oversight-commission/"
    )


def test_links():
    assert parsed_items[0]["links"] == [
        {
            "href": "https://www.phila.gov/departments/citizens-police-oversight-commission/#4oo8n06glnmbujl19dcklrfa85",  # noqa
            "title": "Meeting Information",
        }
    ]


def test_classification():
    assert parsed_items[0]["classification"] == NOT_CLASSIFIED


@pytest.mark.parametrize("item", parsed_items)
def test_all_day(item):
    assert item["all_day"] is False
