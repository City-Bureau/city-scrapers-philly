from datetime import datetime
from os.path import dirname, join

import pytest  # noqa
from city_scrapers_core.constants import BOARD, PASSED
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.phipa_boe import PhipaBoeSpider

test_response = file_response(
    join(dirname(__file__), "files", "phipa_boe.json"),
    url="https://www.googleapis.com/calendar/v3/calendars/philasd.org_ovber5hm1nvmarvnn1vk3fj00g@group.calendar.google.com/events?key=AIzaSyCMycHXGV6oDkQSJPvyMOnv5OIumKg-hXo&maxResults=1000&timeMin=2023-12-03T17:21:34Z",  # noqa
)
spider = PhipaBoeSpider()

freezer = freeze_time("2024-01-31")
freezer.start()

parsed_items = [item for item in spider.parse(test_response)]

freezer.stop()


def test_count():
    assert len(parsed_items) == 29


def test_title():
    assert parsed_items[0]["title"] == "Monthly Action Meeting"


def test_description():
    expected_description = (
        "Registered speakers will be permitted to attend either in-person or remotely via the Zoom video conferencing platform. "  # noqa
        "If you wish to view our full speakers procedures please visit: https://www.philasd.org/schoolboard/wp-content/uploads/sites/892/2021/08/005-Admin-Procedures-Aug-2021.pdf "  # noqa
        "Meeting Location: Remote Video Conference; Livestream available: https://www.philasd.org/pstv/watch/ "  # noqa
        "Meeting materials can be found here . Contact Information: Phone: 215-400-5959 Email: schoolboard@philasd.org"  # noqa
    )
    assert parsed_items[0]["description"] == expected_description


def test_start():
    assert parsed_items[0]["start"] == datetime(2023, 12, 7, 16, 0)


def test_end():
    assert parsed_items[0]["end"] == datetime(2023, 12, 7, 19, 0)


def test_id():
    assert parsed_items[0]["id"] == "phipa_boe/202312071600/x/monthly_action_meeting"


def test_status():
    assert parsed_items[0]["status"] == PASSED


def test_location():
    expected_location = {
        "name": "School District of Philadelphia",
        "address": "440 N Broad St, Philadelphia, PA 19130",
    }
    assert parsed_items[0]["location"] == expected_location


def test_source():
    expected_url = "https://calendar.google.com/calendar/u/0/embed?src=philasd.org_ovber5hm1nvmarvnn1vk3fj00g@group.calendar.google.com"  # noqa
    assert parsed_items[0]["source"] == expected_url


def test_classification():
    assert parsed_items[0]["classification"] == BOARD


def test_all_day():
    assert parsed_items[0]["all_day"] is False
