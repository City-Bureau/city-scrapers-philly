from datetime import datetime
from os.path import dirname, join

from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.phipa_city_council import PhipaCityCouncilSpider

test_response = file_response(
    join(dirname(__file__), "files", "phipa_city_council.html"),
    url="https://phila.legistar.com/Calendar.aspx",
)
spider = PhipaCityCouncilSpider()

freezer = freeze_time("2025-04-08")
freezer.start()

parsed_items = [item for item in spider.parse(test_response)]

freezer.stop()


def test_count():
    assert len(parsed_items) == 20


def test_title():
    assert parsed_items[0]["title"] == "Committee of the Whole"
    assert parsed_items[2]["title"] == "CITY COUNCIL"


# def test_description():
#     assert parsed_items[0]["description"] == "EXPECTED DESCRIPTION"


def test_start():
    assert parsed_items[0]["start"] == datetime(2025, 4, 30, 10, 0)
    assert parsed_items[19]["start"] == datetime(2025, 4, 1, 10, 0)


# def test_end():
#     assert parsed_items[0]["end"] == datetime(2019, 1, 1, 0, 0)


# def test_time_notes():
#     assert parsed_items[0]["time_notes"] == "EXPECTED TIME NOTES"


def test_id():
    assert (
        parsed_items[0]["id"]
        == "phipa_city_council/202504301000/x/committee_of_the_whole"
    )


def test_status():
    assert parsed_items[0]["status"] == "tentative"


def test_location():
    assert parsed_items[0]["location"] == {
        "name": "Room 400, City Hall",
        "address": "1400 John F Kennedy Blvd, Philadelphia, PA 19107",
    }


def test_source():
    assert parsed_items[0]["source"] == "https://phila.legistar.com/Calendar.aspx"


def test_links():
    assert parsed_items[0]["links"] == [
        {
            "href": "https://phila.legistar.com/View.ashx?M=IC&ID=1290914&GUID=F25E14E7-E598-4087-A299-4181AA8A739D",  # noqa
            "title": "Agenda",
        }
    ]


def test_classification():
    assert parsed_items[0]["classification"] == "City Council"


# @pytest.mark.parametrize("item", parsed_items)
# def test_all_day(item):
#     assert item["all_day"] is False
