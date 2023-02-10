import json
from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import CITY_COUNCIL
from freezegun import freeze_time

from city_scrapers.spiders.phipa_city_council import PhipaCityCouncilSpider

freezer = freeze_time("2023-02-10")
freezer.start()

with open(join(dirname(__file__), "files", "phipa_city_council.json"), "r", encoding="utf-8") as f:
    test_response = json.load(f)

spider = PhipaCityCouncilSpider()
parsed_items = [item for item in spider.parse_legistar(test_response)]

freezer.stop()





"""
def test_tests():
    print("Please write some tests for this spider or at least disable this one.")
    assert False

Uncomment below
"""

def test_title():
    assert parsed_items[0]["title"] == "Committee on Rules"


# def test_description():
#     assert parsed_items[0]["description"] == "EXPECTED DESCRIPTION"


def test_start():
    assert parsed_items[0]["start"] == datetime(2023, 2, 28, 10, 0)


# def test_end():
#    assert parsed_items[0]["end"] == datetime(2023, 2, 28, 12, 0)


# def test_time_notes():
#     assert parsed_items[0]["time_notes"] == "EXPECTED TIME NOTES"


def test_id():
    assert parsed_items[0]["id"] == "phipa_city_council/202302281000/x/committee_on_rules"


def test_status():
    assert parsed_items[0]["status"] == "tentative"


def test_location():
    assert parsed_items[0]["location"] == {
        "label":        'a remote manner using Microsoft® Teams. This remote '
                        'hearing may be viewed on Xfinity Channel 64, Fios '
                        'Channel 40 or  '
                        'http://phlcouncil.com/watch-city-council/',
        "url": "http://phlcouncil.com/watch-city-council/"
    }


def test_source():
    assert parsed_items[0]["source"] == "https://phila.legistar.com/Calendar.aspx"


def test_links():
    assert parsed_items[0]["links"] == [{
      "href": "https://phila.legistar.com/View.ashx?M=A&ID=1081004&GUID=891E2F59-E00C-4630-805F-BF596E9C1522",
      "title": "Agenda"
    }]


def test_classification():
    assert parsed_items[0]["classification"] == "City Council"


# @pytest.mark.parametrize("item", parsed_items)
# def test_all_day(item):
#     assert item["all_day"] is False
