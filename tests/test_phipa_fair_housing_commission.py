from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import COMMISSION, PASSED, TENTATIVE
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.phipa_cpc_cdr import PhipaFairHousingCommissionSpider

FILES_DIR = join(dirname(__file__), "files")

EXPECTED_URL = "https://www.phila.gov/the-latest/all-events/?category=Fair%20Housing%20Commission"  # noqa


@pytest.fixture(scope="module")
def calendar_response():
    return file_response(
        join(FILES_DIR, "phipa_fair_housing_commission.json"),
        url="https://www.googleapis.com/calendar/v3/calendars/phila.fairhousingcommission@gmail.com/events?key=test&singleEvents=true&orderBy=startTime&maxResults=2500&timeMin=2020-01-01T00:00:00Z&timeMax=2027-12-31T23:59:59Z",  # noqa
    )


@pytest.fixture(scope="module")
def documents_response():
    return file_response(
        join(FILES_DIR, "phipa_fair_housing_commission_documents.html"),
        url="https://www.phila.gov/documents/fair-housing-commission-meeting-agendas/",  # noqa
    )


@pytest.fixture(scope="module")
def items(calendar_response, documents_response):
    spider = PhipaFairHousingCommissionSpider()
    documents_request = next(spider.parse(calendar_response))
    with freeze_time("2026-08-12"):
        return list(
            spider._parse_documents(documents_response, **documents_request.cb_kwargs)
        )


@pytest.fixture(scope="module")
def past_item(items):
    """Executive session that has already passed, with an agenda posted for
    its exact date (July 15, 2026)."""
    return next(m for m in items if m["start"] == datetime(2026, 7, 15, 8, 30))


@pytest.fixture(scope="module")
def today_item(items):
    """Executive session occurring on the same date the test is frozen to
    (August 12, 2026), with an agenda posted for that same date."""
    return next(m for m in items if m["start"] == datetime(2026, 8, 12, 8, 30))


@pytest.fixture(scope="module")
def hearing_item(items):
    """Public hearing that hasn't happened yet, with no agenda posted."""
    return next(m for m in items if m["start"] == datetime(2026, 9, 1, 9, 0))


def test_count(items):
    assert len(items) == 3


def test_title(past_item, today_item, hearing_item):
    assert past_item["title"] == "FAIR HOUSING EXECUTIVE SESSION"
    assert today_item["title"] == "FAIR HOUSING EXECUTIVE SESSION"
    assert hearing_item["title"] == "FAIR HOUSING PUBLIC HEARINGS"


def test_classification(past_item, today_item, hearing_item):
    assert past_item["classification"] == COMMISSION
    assert today_item["classification"] == COMMISSION
    assert hearing_item["classification"] == COMMISSION


def test_start(past_item, today_item, hearing_item):
    assert past_item["start"] == datetime(2026, 7, 15, 8, 30)
    assert today_item["start"] == datetime(2026, 8, 12, 8, 30)
    assert hearing_item["start"] == datetime(2026, 9, 1, 9, 0)


def test_end(past_item, today_item, hearing_item):
    assert past_item["end"] == datetime(2026, 7, 15, 9, 0)
    assert today_item["end"] == datetime(2026, 8, 12, 9, 0)
    assert hearing_item["end"] == datetime(2026, 9, 1, 11, 30)


def test_id(past_item, today_item, hearing_item):
    assert (
        past_item["id"]
        == "phipa_fair_housing_commission/202607150830/x/fair_housing_executive_session"  # noqa
    )
    assert (
        today_item["id"]
        == "phipa_fair_housing_commission/202608120830/x/fair_housing_executive_session"  # noqa
    )
    assert (
        hearing_item["id"]
        == "phipa_fair_housing_commission/202609010900/x/fair_housing_public_hearings"  # noqa
    )


def test_status(past_item, today_item, hearing_item):
    assert past_item["status"] == PASSED
    assert today_item["status"] == TENTATIVE
    assert hearing_item["status"] == TENTATIVE


def test_location(past_item, today_item, hearing_item):
    expected_location = {
        "name": "Fair Housing Commission",
        "address": "601 Walnut Street, Suite 300 South, Philadelphia, PA 19106",
    }
    assert past_item["location"] == expected_location
    assert today_item["location"] == expected_location
    assert hearing_item["location"] == expected_location


def test_links(past_item, today_item, hearing_item):
    past_hrefs = {link["href"] for link in past_item["links"]}
    assert any(
        "FHC-Executive-Session-Agenda-July-15-2026" in href for href in past_hrefs
    )

    today_hrefs = {link["href"] for link in today_item["links"]}
    assert any(
        "FHC-Executive-Session-Agenda-August-12-2026" in href for href in today_hrefs
    )

    assert hearing_item["links"] == []


def test_source(items):
    assert all(m["source"] == EXPECTED_URL for m in items)
