from city_scrapers_core.constants import BOARD
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from dateutil.parser import parser


class PhipaHealthBoardSpider(CityScrapersSpider):
    name = "phipa_health_board"
    agency = "Philadelphia Board Of Health"
    timezone = "America/Chicago"
    start_urls = ["https://www.phila.gov/departments/board-of-health/"]

    def parse(self, response):
        """
        `parse` should always `yield` Meeting items.

        Change the `_parse_title`, `_parse_start`, etc methods to fit your scraping
        needs.
        """
        for item in response.css(".simcal-events-list-container .simcal-event-details"):
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
        title = item.css("div div:nth-child(2) .title span::text").get()
        return title

    def _parse_description(self, item):
        """Parse or generate meeting description."""
        return ""

    def _parse_classification(self, item):
        """Parse or generate classification from allowed options."""
        return BOARD

    def _parse_start(self, item):
        """Parse start datetime as a naive datetime object."""

        date_raw = item.css(
            "div div:nth-child(2) .start-end span:nth-child(1)::attr(content)"
        ).get()
        date = date_raw.split("T")[0]

        time = item.css("div div:nth-child(2) .start-end span:nth-child(1)::text").get()

        dt_obj = date + " " + time

        return parser().parse(dt_obj)

    def _parse_end(self, item):
        """Parse start datetime as a naive datetime object."""

        date_raw = item.css(
            "div div:nth-child(2) .start-end span:nth-child(2)::attr(content)"
        ).get()
        date = date_raw.split("T")[0]

        time = item.css("div div:nth-child(2) .start-end span:nth-child(2)::text").get()

        dt_obj = date + " " + time

        return parser().parse(dt_obj)

    def _parse_time_notes(self, item):
        """Parse any additional notes on the timing of the meeting"""
        return ""

    def _parse_all_day(self, item):
        """Parse or generate all-day status. Defaults to False."""
        return False

    def _parse_location(self, item):
        """Parse or generate location."""
        return {
            "address": "1101 Market Street, 9th Floor, Philadelphia, PA 19107",
            "name": "Board Of Health",
        }

    def _parse_links(self, item):
        """Parse or generate links."""
        link = "https://www.phila.gov/departments/board-of-health/#"
        meetingID = item.css("div::attr(data-open)").get()

        return [{"href": link + meetingID, "title": "Meeting Information"}]

    def _parse_source(self, response):
        """Parse or generate source."""
        return response.url
