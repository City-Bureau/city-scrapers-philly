import json
from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import (
    CANCELLED,
    COMMISSION,
    COMMITTEE,
    PASSED,
    TENTATIVE,
)
from city_scrapers_core.utils import file_response
from freezegun import freeze_time
from scrapy.http import TextResponse

from city_scrapers.spiders.phipa_city import PhipaCpcCdrSpider

FILES_DIR = join(dirname(__file__), "files")

EXPECTED_URL = "https://www.phila.gov/the-latest/all-events/?category=Philadelphia%20City%20Planning%20Commission"  # noqa


@pytest.fixture(scope="module")
def calendar_response():
    return file_response(
        join(FILES_DIR, "phipa_cpc_cdr.json"),
        url="https://www.googleapis.com/calendar/v3/calendars/do6kgfl3sslqvfq0iumt9eogto@group.calendar.google.com/events?key=test&singleEvents=true&orderBy=startTime&maxResults=2500&timeMin=2020-01-01T00:00:00Z&timeMax=2027-12-31T23:59:59Z",  # noqa
    )


@pytest.fixture(scope="module")
def documents_response():
    return file_response(
        join(FILES_DIR, "phipa_cpc_cdr_documents.html"),
        url="https://www.phila.gov/departments/philadelphia-city-planning-commission/public-meetings/",  # noqa
    )


@pytest.fixture(scope="module")
def recordings_response():
    return file_response(
        join(FILES_DIR, "phipa_cpc_cdr_recordings.html"),
        url="https://www.phila.gov/departments/philadelphia-city-planning-commission/recordings-of-public-meetings/",  # noqa
    )


@pytest.fixture(scope="module")
def items(calendar_response, documents_response, recordings_response):
    spider = PhipaCpcCdrSpider()
    documents_request = next(spider.parse(calendar_response))
    recordings_request = next(
        spider._parse_documents(documents_response, **documents_request.cb_kwargs)
    )
    with freeze_time("2026-08-12"):
        return list(
            spider._parse_recordings(
                recordings_response, **recordings_request.cb_kwargs
            )
        )


@pytest.fixture(scope="module")
def cdr_items(items):
    return [item for item in items if item["classification"] == COMMITTEE]


@pytest.fixture(scope="module")
def cpc_items(items):
    return [item for item in items if item["classification"] == COMMISSION]


def test_count(items, cdr_items, cpc_items):
    assert len(items) == 6
    assert len(cdr_items) == 3
    assert len(cpc_items) == 3


def test_title(cdr_items, cpc_items):
    assert cdr_items[0]["title"] == "Civic Design Review Committee"
    assert cpc_items[0]["title"] == "Philadelphia City Planning Commission Meeting"


def test_classification(cdr_items, cpc_items):
    assert all(m["classification"] == COMMITTEE for m in cdr_items)
    assert all(m["classification"] == COMMISSION for m in cpc_items)


def test_start(cdr_items, cpc_items):
    assert cdr_items[0]["start"] == datetime(2026, 7, 7, 13, 0)
    assert cpc_items[0]["start"] == datetime(2026, 7, 16, 13, 0)


def test_end(cdr_items):
    assert cdr_items[0]["end"] == datetime(2026, 7, 7, 17, 0)


def test_id(cdr_items, cpc_items):
    assert (
        cdr_items[0]["id"]
        == "phipa_cpc_cdr/202607071300/x/civic_design_review_committee"
    )
    assert (
        cpc_items[0]["id"]
        == "phipa_cpc_cdr/202607161300/x/philadelphia_city_planning_commission_meeting"
    )


def test_status(cdr_items, cpc_items):
    assert [m["status"] for m in cdr_items] == [PASSED, TENTATIVE, CANCELLED]
    assert [m["status"] for m in cpc_items] == [PASSED, TENTATIVE, CANCELLED]


def test_location(cdr_items):
    expected_location = {
        "name": "One Parkway Building, Room 18-029",
        "address": "1515 Arch Street, 18th Floor, Philadelphia, PA 19102",
    }
    assert cdr_items[0]["location"] == expected_location


def test_links(cdr_items, cpc_items):
    cdr_hrefs = {link["href"] for link in cdr_items[0]["links"]}
    assert any("CDR-LI-Findings-Letter" in href for href in cdr_hrefs)
    assert "https://youtu.be/QFTYhWM0ZpQ" in cdr_hrefs

    cpc_hrefs = {link["href"] for link in cpc_items[0]["links"]}
    assert any("PCPC-Agenda" in href for href in cpc_hrefs)
    assert "https://www.youtube.com/watch?v=PgmTf-qAnfI" in cpc_hrefs

    assert cdr_items[1]["links"] == []
    assert cdr_items[2]["links"] == []
    assert cpc_items[1]["links"] == []
    assert cpc_items[2]["links"] == []


def test_source(items):
    assert all(m["source"] == EXPECTED_URL for m in items)


def test_parse_calendar_api_error(caplog):
    """A Calendar API error response (e.g. expired/invalid API key, quota
    exceeded) has no "items" key. parse() should log and stop instead of
    raising KeyError and killing the crawl."""
    spider = PhipaCpcCdrSpider()
    error_response = TextResponse(
        url="https://www.googleapis.com/calendar/v3/calendars/x/events",
        body=json.dumps(
            {"error": {"code": 403, "message": "API key not valid."}}
        ).encode("utf-8"),
    )
    results = list(spider.parse(error_response))
    assert results == []
    assert "API key not valid" in caplog.text
