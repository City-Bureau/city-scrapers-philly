import re
from datetime import datetime, timezone
from html import unescape

from city_scrapers_core.constants import (
    ADVISORY_COMMITTEE,
    BOARD,
    CANCELLED,
    COMMITTEE,
    NOT_CLASSIFIED,
)
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from dateutil.parser import parse as dt_parser
from dateutil.relativedelta import relativedelta
from scrapy import Request

# Matches a listing line: "August 20, 2026, at noon: Committee Meeting".
LISTING_RE = re.compile(
    r"^\s*(?P<date>[A-Za-z]+ \d{1,2}, \d{4}),\s*at\s*"
    r"(?P<time>noon|midnight|\d{1,2}(?::\d{2})?\s*[ap]m)\s*:\s*"
    r"(?P<title>.+?)\s*$",
    re.IGNORECASE,
)
# Matches an empty "()" left over once a real tag next to it is removed.
EMPTY_PARENS_RE = re.compile(r"\(\s*\)\s*$")
# Matches a "(canceled)"/"(cancelled)" tag anywhere in the title; other
# tags, e.g. "(remote)", stay in the title text.
CANCELLED_TAG_RE = re.compile(r"\(\s*cancell?ed\s*\)\s*", re.IGNORECASE)
# Matches the "Month D, YYYY, at TIME" stamp in the detail page's summary
# paragraph ("SEPTA Board September 24, 2026, at 3:00 pm SEPTA Board Room...").
DETAIL_DATETIME_RE = re.compile(
    r"(?P<date>[A-Za-z]+ \d{1,2}, \d{4}),\s*at\s*"
    r"(?P<time>noon|midnight|\d{1,2}(?::\d{2})?\s*[ap]m)",
    re.IGNORECASE,
)
# Attachment extensions treated as meeting documents (vs. e.g. registration
# or video links, which stay in the description).
DOC_EXTS = (".pdf", ".docx", ".doc", ".xlsx")
# Matches a listing location that opens with a street number, meaning it
# has no venue name (e.g. "1234 Market St, Philadelphia").
STREET_ADDRESS_RE = re.compile(r"^\d+\s")
# Matches a "<Venue>, <street number> <rest of address>" listing location,
# the only shape we split into a name and an address.
VENUE_ADDRESS_RE = re.compile(r"^(?P<name>[^,]+?),\s*(?P<address>\d+\s+.+)$")


class PhipaSeptaSpider(CityScrapersSpider):
    name = "phipa_septa"
    agency = "SEPTA"
    timezone = "America/New_York"
    start_urls = [
        "https://wwww.septa.org/about/meetings/",
        "https://wwww.septa.org/about/meetings/?archive=1",
    ]
    archive_years = 3

    def parse(self, response):
        """Follow each meeting notice and pagination link."""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - relativedelta(
            years=self.archive_years
        )
        past_cutoff = False

        for item in response.css("li.entry-title"):
            link = item.css("div.entry-datetime a")
            href = link.attrib.get("href")
            listing_text = "".join(link.css("::text").getall())
            title, listing_start, cancelled = self._parse_listing_text(listing_text)
            listing_location = self._clean_text(item.css("div.entry-location"))
            listing_session_type = self._clean_text(
                item.css("div.entry-details span:first-child")
            )
            # A <div class="entry-canceled"> note also marks a cancellation.
            # (The "entry-title canceled" class does not - SEPTA sets it on
            # most upcoming rows regardless of status.)
            if item.css("div.entry-canceled"):
                cancelled = True

            if not href or listing_start is None:
                continue
            if listing_start < cutoff:
                past_cutoff = True
                continue

            yield Request(
                response.urljoin(href),
                callback=self._parse_detail,
                cb_kwargs={
                    "title": title,
                    "listing_start": listing_start,
                    "cancelled": cancelled,
                    "listing_location": listing_location,
                    "listing_session_type": listing_session_type,
                },
            )

        next_href = response.css("div.wp-pagination a.next::attr(href)").get()
        if next_href and not past_cutoff:
            yield Request(response.urljoin(next_href), callback=self.parse)

    def _parse_detail(
        self,
        response,
        title,
        listing_start,
        cancelled,
        listing_location,
        listing_session_type,
    ):
        """Build a meeting from its authoritative detail notice."""
        detail_title = self._clean_text(response.css(".entry-header .entry-title"))
        is_cancelled = (
            cancelled
            or "cancel" in detail_title.lower()
            or bool(response.css(".entry-content .entry-canceled"))
        )

        meeting = Meeting(
            title=title,
            description=self._parse_description(response, listing_session_type),
            classification=self._parse_classification(title),
            start=self._parse_detail_start(response) or listing_start,
            # SEPTA does not publish definitive end times.
            end=None,
            all_day=False,
            # SEPTA labels each meeting "Closed session" or "Open to the
            # public"; Documenters can't attend closed ones.
            closed_to_public="closed" in (listing_session_type or "").lower(),
            time_notes="",
            location=self._parse_location(listing_location),
            # `links` holds only meeting documents (see `_parse_description`
            # for registration/video links).
            links=self._parse_links(response),
            source=response.url,
        )
        meeting["status"] = CANCELLED if is_cancelled else self._get_status(meeting)
        meeting["id"] = self._get_id(meeting)
        yield meeting

    def _parse_listing_text(self, text):
        """Split a listing line into (title, start datetime, cancelled)."""
        match = LISTING_RE.match(text)
        if not match:
            return text.strip(), None, False

        title = match.group("title")
        cancelled = bool(CANCELLED_TAG_RE.search(title))
        title = CANCELLED_TAG_RE.sub("", title).strip()
        title = EMPTY_PARENS_RE.sub("", title).strip()

        return (
            title,
            self._to_datetime(match.group("date"), match.group("time")),
            cancelled,
        )

    def _parse_detail_start(self, response):
        """Parse the start time from the detail page's summary paragraph."""
        match = DETAIL_DATETIME_RE.search(self._detail_summary_text(response))
        if not match:
            return None
        return self._to_datetime(match.group("date"), match.group("time"))

    def _to_datetime(self, date_str, time_str):
        time_str = time_str.strip().lower()

        if time_str == "noon":
            time_str = "12:00 pm"
        elif time_str == "midnight":
            time_str = "12:00 am"

        try:
            return dt_parser(f"{date_str} {time_str}")
        except ValueError:
            self.logger.warning(f"Could not parse datetime from: {date_str} {time_str}")
            return None

    def _parse_classification(self, title):
        lower_title = title.lower()

        if "advisory" in lower_title or "cac" in lower_title or "sac" in lower_title:
            return ADVISORY_COMMITTEE
        if "board" in lower_title:
            return BOARD
        if "committee" in lower_title:
            return COMMITTEE

        return NOT_CLASSIFIED

    def _parse_location(self, listing_location):
        """Build the location dict from the listing page's entry-location
        text. Only a "<Venue>, <street number> <address>" value is split
        into a name and an address; anything else (including a bare street
        address or free-form instructions) is kept whole rather than
        guessing a split that could turn prose into a false address."""
        value = (listing_location or "").strip()
        if not value:
            return {"name": "", "address": ""}
        if STREET_ADDRESS_RE.match(value):
            return {"name": "", "address": value}

        match = VENUE_ADDRESS_RE.match(value)
        if match:
            return {
                "name": match.group("name").strip(),
                "address": match.group("address").strip(),
            }
        return {"name": value, "address": ""}

    def _parse_description(self, response, listing_session_type):
        """Assemble the free-text description: organizing body, session
        type, online-attendance instructions, and the non-document links
        (meeting-details self-link, registration link, video)."""
        parts = []

        organization = self._clean_text(
            response.css(".entry-content > p:not(.entry-docs) strong")[:1]
        )
        if organization:
            parts.append(f"Organization: {organization}")

        if listing_session_type:
            parts.append(f"Session Type: {listing_session_type}")

        instructions = self._parse_meeting_instructions(response)
        if instructions:
            parts.append(instructions)

        link_notes = [f"Meeting Details: {response.url}"]
        link_notes += [
            f"{link['title']}: {link['href']}"
            for link in self._parse_attachment_links(response)
            if not link["href"].lower().endswith(DOC_EXTS)
        ]
        parts.append("\n".join(link_notes))

        return "\n".join(parts)

    def _parse_meeting_instructions(self, response):
        """Collect the Webex registration/meeting links and the trailing
        instruction note from <div class="meeting-instructions">. Links
        that have expired render as <span>, not <a>, and are skipped."""
        block = response.css("div.meeting-instructions")
        if not block:
            return ""

        lines = []
        seen = set()
        for anchor in block.css("a"):
            href = anchor.attrib.get("href")
            if not href or href in seen:
                continue
            seen.add(href)
            label = self._clean_text(anchor) or "Link"
            lines.append(f"{label}: {response.urljoin(href)}")

        for para in block.css("p"):
            if para.css("a") or para.css("span.expired"):
                continue
            note = self._clean_text(para)
            if note:
                lines.append(note)

        return "\n".join(lines)

    def _parse_attachment_links(self, response):
        """Collect every link from the detail page's <p class="entry-docs">
        block - documents, video, registration - deduplicated by href."""
        links = []
        seen_hrefs = set()
        for anchor in response.css(".entry-docs a"):
            href = anchor.attrib.get("href")
            if not href:
                continue
            href = response.urljoin(href)
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            # Anchor text without the nested screen-reader-only span.
            title = re.sub(
                r"\s+", " ", "".join(anchor.xpath("./text()").getall())
            ).strip()
            title = title or href
            # Collapses a doubled "(PDF) (PDF)" suffix down to one.
            title = re.sub(r"(\([^)]*\))\s*\1$", r"\1", title)
            links.append({"href": href, "title": title})
        return links

    def _parse_links(self, response):
        """Filter attachment links down to meeting documents."""
        return [
            link
            for link in self._parse_attachment_links(response)
            if link["href"].lower().endswith(DOC_EXTS)
        ]

    def _detail_summary_text(self, response):
        """Flattened text of the detail page's lead <p> - the block that
        carries the organizing body, date/time, location and session
        type on <br>-separated lines."""
        return self._clean_text(response.css(".entry-content > p:not(.entry-docs)")[:1])

    def _clean_text(self, sel):
        """Flatten a selection's HTML to collapsed plain text."""
        text = re.sub(r"<[^>]+>", " ", "".join(sel.getall()))
        return re.sub(r"\s+", " ", unescape(text)).strip()
