import json
import re
from collections import defaultdict
from datetime import datetime

import pytz
from bs4 import BeautifulSoup
from city_scrapers_core.constants import CANCELLED, COMMISSION, COMMITTEE
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from dateutil.relativedelta import relativedelta
from scrapy import Request

DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)[\s_.-]+(\d{1,2})(?:st|nd|rd|th)?,?[\s_.-]+(\d{4})",
    re.IGNORECASE,
)


class PhipaCpcCdrSpiderMixin(CityScrapersSpider):
    timezone = "America/New_York"
    calendar_id = "do6kgfl3sslqvfq0iumt9eogto@group.calendar.google.com"
    source_url = "https://www.phila.gov/the-latest/all-events/?category=Philadelphia%20City%20Planning%20Commission"  # noqa
    documents_url = "https://www.phila.gov/departments/philadelphia-city-planning-commission/public-meetings/"  # noqa
    recordings_url = "https://www.phila.gov/departments/philadelphia-city-planning-commission/recordings-of-public-meetings/"  # noqa
    location = {
        "name": "One Parkway Building, Room 18-029",
        "address": "1515 Arch Street, 18th Floor, Philadelphia, PA 19102",
    }
    custom_settings = {"ROBOTSTXT_OBEY": False, "FEED_EXPORT_ENCODING": "utf-8"}

    def start_requests(self):
        api_key = self.settings.get("GOOGLE_CLOUD_API_KEY")
        if not api_key:
            raise ValueError("No GOOGLE_CLOUD_API_KEY provided")
        current_datetime = datetime.utcnow()
        min_time_val = (current_datetime - relativedelta(years=3)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        max_time_val = (current_datetime + relativedelta(years=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        url = (
            "https://www.googleapis.com/calendar/v3/calendars/"
            f"{self.calendar_id}/events?key={api_key}&singleEvents=true"
            "&orderBy=startTime&maxResults=2500"
            f"&timeMin={min_time_val}&timeMax={max_time_val}"
        )
        yield Request(url, callback=self.parse)

    def parse(self, response):
        data = json.loads(response.text)
        items = [item for item in data["items"] if "start" in item]
        yield Request(
            self.documents_url,
            callback=self._parse_documents,
            cb_kwargs={"items": items},
        )

    def _parse_documents(self, response, items):
        documents = self._new_link_index()
        for heading in response.xpath('//h3[@class="bmn"]'):
            body = self._body_from_id(heading.attrib.get("id", ""))
            if not body:
                continue
            table = heading.xpath(
                'following-sibling::div[contains(@class, "search-sort-table")][1]'
            )
            for row in table.css("tr.clickable-row"):
                href = row.attrib.get("data-href") or row.css("a::attr(href)").get()
                title = " ".join(row.css("span.title::text").getall()).strip()
                if not href or not title:
                    continue
                link = {"href": response.urljoin(href), "title": title}
                self._index_link(documents, body, title, link)
        yield Request(
            self.recordings_url,
            callback=self._parse_recordings,
            cb_kwargs={"items": items, "documents": documents},
        )

    def _parse_recordings(self, response, items, documents):
        recordings = self._new_link_index()
        for heading in response.xpath('//h2[@class="h4"]'):
            body = self._body_from_id(heading.attrib.get("id", ""))
            if not body:
                continue
            row = heading.xpath('ancestor::div[contains(@class, "grid-x")][1]')
            for li in row.css("div.resource-list li.clickable-row"):
                href = li.attrib.get("data-href") or li.css("a::attr(href)").get()
                text = li.css("a").xpath("string()").get("")
                if not href or not text:
                    continue
                self._index_link(
                    recordings,
                    body,
                    text,
                    {"href": href, "title": "Video Recording"},
                )

        for item in items:
            if self._item_body(item) != self._get_body():
                continue
            start = self._parse_datetime(item["start"])
            meeting = Meeting(
                title=self._parse_title(item),
                description=self._parse_description(item),
                classification=self._parse_classification(item),
                start=start,
                end=self._parse_datetime(item["end"]),
                all_day="date" in item["start"],
                time_notes="",
                location=self.location,
                links=self._parse_links(start, documents, recordings),
                source=self.source_url,
            )
            meeting["status"] = self._parse_status(item, meeting)
            meeting["id"] = self._get_id(meeting)
            yield meeting

    def _body_from_id(self, heading_id):
        """Map a heading's id/anchor text to a body key ("pcpc" or "cdr")."""
        heading_id = heading_id.lower()
        if "pcpc" in heading_id or "planning-commission" in heading_id:
            return "pcpc"
        if "cdr" in heading_id or "civic-design-review" in heading_id:
            return "cdr"
        return None

    def _new_link_index(self):
        """An index of links keyed by their exact date. Links whose source
        text only names a month (e.g. the CDR agenda) aren't indexed at all,
        since it can't be assumed which meeting in that month they belong
        to."""
        return {"by_date": defaultdict(list)}

    def _index_link(self, index, body, text, link):
        """File a link under its exact date if the source text names one;
        skip it otherwise."""
        exact_date = self._parse_exact_date_from_text(text)
        if exact_date:
            index["by_date"][(body, exact_date)].append(link)

    def _parse_exact_date_from_text(self, text):
        """Parse a full day-level date from free-form title text."""
        match = DATE_RE.search(text)
        if not match:
            return None
        month_str, day_str, year_str = match.groups()
        try:
            return (
                datetime.strptime(month_str, "%B")
                .replace(year=int(year_str), day=int(day_str))
                .date()
            )
        except ValueError:
            return None

    def _parse_title(self, item):
        return item.get("summary") or ""

    def _parse_description(self, item):
        if "description" not in item:
            return ""
        soup = BeautifulSoup(item["description"], "html.parser")
        return soup.get_text(separator=" ", strip=True)

    def _parse_classification(self, item):
        return COMMITTEE if self._item_body(item) == "cdr" else COMMISSION

    def _parse_datetime(self, datetime_dict):
        """Parse a Google Calendar datetime Dict into a naive datetime in the
        agency's local timezone."""
        if "date" in datetime_dict:
            return datetime.strptime(datetime_dict["date"], "%Y-%m-%d")
        dt_aware = datetime.strptime(datetime_dict["dateTime"], "%Y-%m-%dT%H:%M:%S%z")
        return dt_aware.astimezone(self._get_tz()).replace(tzinfo=None)

    def _parse_status(self, item, meeting):
        if item.get("status") == "cancelled":
            return CANCELLED
        return self._get_status(meeting)

    def _parse_links(self, start, documents, recordings):
        date_key = (self._get_body(), start.date())
        links = []
        for index in (documents, recordings):
            links.extend(index["by_date"].get(date_key, []))
        return links

    def _item_body(self, item):
        title = (item.get("summary") or "").lower()
        return "cdr" if "civic design review" in title else "pcpc"

    def _get_body(self):
        return "cdr" if "cdr" in self.name else "pcpc"

    def _get_tz(self):
        return pytz.timezone(self.timezone)
