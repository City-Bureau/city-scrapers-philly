from urllib.parse import urljoin

from city_scrapers_core.constants import CITY_COUNCIL
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from dateutil.parser import parse


class PhipaCityCouncilSpider(CityScrapersSpider):
    name = "phipa_city_council"
    agency = "Philadelphia City Council"
    timezone = "America/New_York"
    start_urls = ["https://phila.legistar.com/Calendar.aspx"]

    def parse(self, response):
        """
        `parse` should always `yield` Meeting items.

        We are now parsing response as HTML with parse() method instead of JSON with parse_legistar() method. Something on their end changed. This spider handles the HTML reponse now.
        """

        for item in response.css(".rgMasterTable tbody tr"):
            # import pdb; pdb.set_trace()
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
        return item.css("td")[0].css('::text').getall()[1]

    def _parse_description(self, item):
        """Parse or generate meeting description."""
        return ""

    def _parse_classification(self, item):
        """Parse or generate classification from allowed options."""
        return CITY_COUNCIL

    def _parse_start(self, item):
        """Parse start datetime as a naive datetime object."""
        date = item.css("td")[1].css("::text").get()
        time_parts = item.css("td")[3].css('::text').getall()
        if date and len(time_parts) > 1:
            return parse(f"{date} {time_parts[1]}")
        else:
            return None

    def _parse_end(self, item):
        """Parse end datetime as a naive datetime object. Added by pipeline if None"""
        return None

    def _parse_time_notes(self, item):
        """Parse any additional notes on the timing of the meeting"""
        return ""

    def _parse_all_day(self, item):
        """Parse or generate all-day status. Defaults to False."""
        return False

    def _parse_location(self, item):
        """Parse or generate location."""
        address = "1400 John F Kennedy Blvd, Philadelphia, PA 19107"
        name = item.css('td')[4].css('::text').get()
        return {
            "address": address,
            "name": name,
        }

    def _parse_links(self, item):
        """Parse or generate links."""
        base_url = "https://phila.legistar.com/"
        path = item.css("td")[2].css("a::attr(href)").get()
        href = urljoin(base_url, path)
        return [{"href": href, "title": "Agenda"}]

    def _parse_source(self, response):
        """Parse or generate source."""
        return response.url
