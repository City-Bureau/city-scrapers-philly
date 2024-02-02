from datetime import datetime
from os.path import dirname, join

import pytest # noqa
from city_scrapers_core.constants import PASSED
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

# Assuming the spider name is relevant to the content being parsed
from city_scrapers.spiders.phipa_trb import PhipaTrbSpider

test_response = file_response(
    join(dirname(__file__), "files", "phipa_trb.json"),
    url="https://go.boarddocs.com/in/indps/Board.nsf/XML-ActiveMeetings",
)
spider = PhipaTrbSpider()

freezer = freeze_time("2024-01-31")
freezer.start()

parsed_items = [item for item in spider.parse(test_response)]

freezer.stop()


def test_count():
    assert len(parsed_items) == 62  # Adjusted based on provided data


def test_title():
    assert parsed_items[0]["title"] == "WATER REVENUE MASTER HEARINGS"


def test_description():
    expected_description = (
        "Melissa Andre is inviting you to a scheduled Zoom meeting.\n\n"
        "Join Zoom Meeting\n"
        "https://us02web.zoom.us/j/88320834881?pwd=WFA3eG9hUGVVMEhyZWluYlNZbElhUT09\n\n"
        "Meeting ID: 883 2083 4881\n"
        "Passcode: 040668\n\n"
        "---\n\n"
        "One tap mobile\n"
        "+12678310333,,88320834881#,,,,*040668# US (Philadelphia) \n"
        "+13126266799,,88320834881#,,,,*040668# US (Chicago)\n\n"
        "---\n\n"
        "Dial by your location\n"
        "• +1 267 831 0333 US (Philadelphia)\n"
        "• +1 312 626 6799 US (Chicago)\n"
        "• +1 929 205 6099 US (New York)\n"
        "• +1 301 715 8592 US (Washington DC)\n"
        "• +1 346 248 7799 US (Houston)\n\n"
        "Meeting ID: 883 2083 4881\n"
        "Passcode: 040668\n\n"
        "Find your local number: https://us02web.zoom.us/u/kcwcXK28Kw\n\n"
    )
    assert parsed_items[0]["description"] == expected_description


def test_start():
    assert parsed_items[0]["start"] == datetime(2023, 12, 8, 9, 0)


def test_end():
    assert parsed_items[0]["end"] == datetime(2023, 12, 8, 11, 0)


def test_id():
    assert (
        parsed_items[0]["id"]
        == "phipa_trb/202312080900/x/water_revenue_master_hearings"
    )


def test_status():
    assert parsed_items[0]["status"] == PASSED


def test_location():
    expected_location = {
        "name": "Land Title Building",
        "address": "100 S. Broad Street - Suite 400, Philadelphia, Pennsylvania 19110-1099",  # noqa
    }
    assert parsed_items[0]["location"] == expected_location


def test_source():
    expected_url = "https://calendar.google.com/calendar/u/0/embed?src=taxreviewboard@gmail.com"  # noqa
    assert parsed_items[0]["source"] == expected_url
