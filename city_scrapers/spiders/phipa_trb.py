import json
from datetime import datetime, timedelta

import pytz
from city_scrapers_core.constants import BOARD, CANCELLED
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from scrapy import Request


class PhipaTrbSpider(CityScrapersSpider):
    name = "phipa_trb"
    agency = "Philadelphia Tax Review Board"
    timezone = "America/New_York"
    calendar_id = "taxreviewboard@gmail.com"
    calendar_website = (
        f"https://calendar.google.com/calendar/u/0/embed?src={calendar_id}"
    )
    location = {
        "name": "Land Title Building",
        "address": "100 S. Broad Street - Suite 400, Philadelphia, Pennsylvania 19110-1099",  # noqa
    }
    agendas_link = {
        "title": "Agenda page",
        "href": "https://www.phila.gov/documents/tax-review-board-agendas/",
    }

    def start_requests(self):
        api_key = self.settings.get("GOOGLE_CLOUD_API_KEY")
        if not api_key:
            raise ValueError("No GOOGLE_CLOUD_API_KEY provided")

        # calculate the date two months ago
        current_datetime = datetime.utcnow()
        two_months_prior = current_datetime - timedelta(days=60)
        minTimeVal = two_months_prior.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Construct the URL with query parameters
        url = f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events?key={api_key}&maxResults=500&timeMin={minTimeVal}"  # noqa
        yield Request(url, self.parse)

    def parse(self, response):
        """
        Parse the response from the Google Calendar API and yield Meeting items.
        """
        data = json.loads(response.text)
        for item in data["items"]:
            all_day = True if "date" in item["start"] else False
            meeting = Meeting(
                title=self._parse_title(item),
                description=self._parse_description(item),
                classification=BOARD,
                start=self._parse_datetime(item["start"]),
                end=self._parse_datetime(item["end"]),
                all_day=all_day,
                time_notes=None,
                location=self.location,
                links=self._parse_links(item),
                source=self.calendar_website,
            )
            meeting["status"] = self._get_status(meeting)
            meeting["id"] = self._get_id(meeting)
            yield meeting

    def _parse_title(self, item):
        """Parse meeting title."""
        return item.get("summary") or ""

    def _parse_description(self, item):
        """Parse meeting description."""
        return item.get("description") or ""

    def _parse_datetime(self, datetime_dict):
        """Parse a Google Calendar datetime Dict. Note that "dateTime"
        strings include a timezone. To account for the way city-scraper spiders
        handle timezones, we convert the datetime to America/New_York time and
        then remove the tz info.
        """
        # handle all day event
        if "date" in datetime_dict:
            return datetime.strptime(datetime_dict["date"], "%Y-%m-%d")
        # handle event with a specific time
        datetime_str = datetime_dict["dateTime"]
        dt_aware = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S%z")
        target_tz = pytz.timezone(self.timezone)
        dt_target_tz = dt_aware.astimezone(target_tz)
        dt_naive = dt_target_tz.replace(tzinfo=None)
        return dt_naive

    def _parse_status(self, item, meeting):
        """Parse status from item. For this agency, the title is generally a better
        indicator of cancellation status than the "status" field, but this method checks
        both."""
        if "cancelled" in item["status"]:
            return CANCELLED
        return self._get_status(meeting)

    def _parse_links(self, item):
        """Parse or generate links."""
        links = [self.agendas_link]
        if item["htmlLink"]:
            links.append(
                {
                    "href": item["htmlLink"],
                    "title": "Google Calendar Event",
                }
            )
        if item["location"] and item["location"].startswith("https://us02web.zoom.us"):
            links.append(
                {
                    "href": item["location"],
                    "title": "Zoom Link",
                }
            )
        return links

    def _parse_source(self):
        """Generate link to public Google Calendar site."""
        return f"https://calendar.google.com/calendar/u/0/embed?src={self.calendar_id}"
