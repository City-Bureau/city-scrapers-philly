from city_scrapers_core.constants import BOARD
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from dateutil.parser import parser


class PhipaCityCommissionerSpider(CityScrapersSpider):
    name = "phipa_city_commissioner"
    agency = "Philadelphia City Commissioners"
    timezone = "America/Chicago"
    start_urls = [
        "https://vote.phila.gov/resources-data/commissioner-meetings/commissioner-meetings/"  # noqa
    ]

    def parse(self, response):
        """
        `parse` should always `yield` Meeting items.

        Change the `_parse_title`, `_parse_start`, etc methods to fit your scraping
        needs.
        """
        for item in response.css("table tr td"):
            date = item.css("::text").get()
            if date is not None:
                meeting = Meeting(
                    title=self._parse_title(item),
                    description=self._parse_description(item),
                    classification=self._parse_classification(item),
                    start=self._parse_start(item),
                    end=self._parse_end(item),
                    all_day=self._parse_all_day(item),
                    time_notes=self._parse_time_notes(item),
                    location=self._parse_location(item),
                    links=self._parse_links(item),
                    source=self._parse_source(response),
                )

                meeting["status"] = self._get_status(meeting)
                meeting["id"] = self._get_id(meeting)

                yield meeting

    def _parse_title(self, item):
        """Parse or generate meeting title."""
        return "City Commissioners Board Meetings"

    def _parse_description(self, item):
        """Parse or generate meeting description."""
        return ""

    def _parse_classification(self, item):
        """Parse or generate classification from allowed options."""
        return BOARD

    def _parse_start(self, item):
        """Parse start datetime as a naive datetime object."""
        date_raw = item.css("::text").get()
        date = date_raw.split(" ")[1]
        time = "11:00:00"
        dt_obj = date + " " + time
        return parser().parse(dt_obj)

    def _parse_end(self, item):
        """Parse end datetime as a naive datetime object. Added by pipeline if None"""
        return None

    def _parse_time_notes(self, item):
        """Parse any additional notes on the timing of the meeting"""
        return "Please double check the web page for the meeting time noted at top of the page"  # noqa

    def _parse_all_day(self, item):
        """Parse or generate all-day status. Defaults to False."""
        return False

    def _parse_location(self, item):
        """Parse or generate location."""
        return {
            "address": "1400 JFK Boulevard Philadelphia, PA 19107",
            "name": "City Hall Room-202",
        }

    def _parse_links(self, item):
        """Parse or generate links."""
        return [{"href": item.css("a::attr(href)").get(), "title": "Agenda"}]

    def _parse_source(self, response):
        """Parse or generate source."""
        return response.url
