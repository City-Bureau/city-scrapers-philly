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
DETAIL_TIME_RE = re.compile(
    r"Time and Date:\s*(?P<time>noon|midnight|\d{1,2}(?::\d{2})?\s*[ap]m)\s+"
    r"[A-Za-z]+,\s*(?P<date>[A-Za-z]+ \d{1,2}, \d{4})",
    re.IGNORECASE,
)
ORGANIZATION_RE = re.compile(
    r"Organization:\s*(?P<org>.+?)\s*Time and Date:", re.IGNORECASE
)
# Matches Cloudflare's email-obfuscation markup: an <a> wrapping a
# <span data-cfemail="...">.
CF_EMAIL_WRAPPED_RE = re.compile(
    r'<a\b[^>]*>\s*<span\b[^>]*\bdata-cfemail="(?P<hex>[0-9a-f]+)"[^>]*>'
    r"[^<]*</span>\s*</a>"
)
# Matches a bare <a> or <span> tag carrying data-cfemail directly, with no
# inner wrapper.
CF_EMAIL_RE = re.compile(
    r"<(?P<tag>a|span)\b[^>]*\bdata-cfemail=\"(?P<hex>[0-9a-f]+)\"[^>]*>"
    r"[^<]*</(?P=tag)>"
)
# Attachment extensions treated as meeting documents (vs. e.g. registration
# or video links, which stay in the description).
DOC_EXTS = (".pdf", ".docx", ".doc", ".xlsx")
# Matches a listing location that opens with a street number, meaning it
# has no venue name (e.g. "1234 Market St, Philadelphia").
STREET_ADDRESS_RE = re.compile(r"^\d+\s")


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
        is_cancelled = cancelled or "cancel" in detail_title.lower()

        meeting = Meeting(
            title=title,
            description=self._parse_description(response, listing_session_type),
            classification=self._parse_classification(title),
            start=self._parse_detail_start(response) or listing_start,
            # SEPTA does not publish definitive end times.
            end=None,
            all_day=False,
            time_notes="",
            location=self._parse_location(listing_location),
            # `links` holds only meeting documents (see `_parse_description`
            # for other attachment links).
            links=self._parse_links(response),
            source=response.url,
        )
        meeting["status"] = CANCELLED if is_cancelled else self._get_status(meeting)
        meeting["id"] = self._get_id(meeting)
        yield meeting

    def _parse_listing_text(self, text):
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
        """Parses the meeting start time from the detail page's
        "Time and Date:" field."""
        text = self._clean_text(self._info_selector(response))
        match = DETAIL_TIME_RE.search(text)

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

    def _parse_location_block(self, response):
        """Splits the detail page's Location paragraph into an in-person
        part and a virtual/online part, normalizing "In person:" and
        "Virtual:"/"Online:" labels. Either part may be absent."""
        text = self._clean_text(
            response.css(".entry-content .entry-column-1 p.meeting-location")
        )
        text = text.split("Location:", 1)[-1].strip()
        # Normalizes "In person:", "In-person:", "In Person:", and
        # "In person :" label spellings.
        text = re.sub(r"In[\s-]?[Pp]erson\s*:", "In person:", text)

        if "In person:" not in text:
            return {"in_person": None, "virtual": text or None, "virtual_label": None}

        in_person = text.split("In person:", 1)[1]
        virtual = None
        virtual_label = None
        virtual_match = re.search(r"\b(Online|Virtual)\s*:", in_person, re.IGNORECASE)
        if virtual_match:
            virtual_label = virtual_match.group(1).capitalize()
            virtual = in_person[virtual_match.end() :].strip()
            in_person = in_person[: virtual_match.start()].strip()

        return {
            "in_person": in_person.strip(),
            "virtual": virtual,
            "virtual_label": virtual_label,
        }

    def _parse_location(self, listing_location):
        """Builds the location dict from the listing page's entry-location
        text, splitting it into a venue name and an address. A value that
        opens with a street number (e.g. "1234 Market St, Philadelphia")
        has no venue name, so it's kept together as the address instead of
        splitting off the street as a false name."""
        if not listing_location:
            return {"name": "", "address": ""}

        if STREET_ADDRESS_RE.match(listing_location):
            return {"name": "", "address": listing_location.strip()}

        name, _, address = listing_location.partition(",")
        return {"name": name.strip(), "address": address.strip()}

    def _parse_in_person_notes(self, block):
        """Extracts registration or attendance instructions from the
        in-person text."""
        in_person = block["in_person"]
        if not in_person:
            return ""
        match = re.search(r"\.\s*(To register\b.*)$", in_person, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _parse_description(self, response, listing_session_type):
        info_text = self._clean_text(self._info_selector(response))
        location_block = self._parse_location_block(response)
        notes_text = self._parse_notes(response)

        parts = []

        org_match = ORGANIZATION_RE.search(info_text)
        if org_match:
            parts.append(f"Organization: {org_match.group('org').strip()}")

        if listing_session_type:
            parts.append(f"Session Type: {listing_session_type}")

        in_person_notes = self._parse_in_person_notes(location_block)
        if in_person_notes:
            parts.append(f"In person: {in_person_notes}")

        if location_block["virtual"]:
            label = location_block["virtual_label"] or "Virtual"
            parts.append(f"{label}: {location_block['virtual']}")

        if notes_text:
            parts.append(notes_text)

        # Includes the meeting-details link and any non-document attachment
        # links.
        link_notes = [f"Meeting Details: {response.url}"]
        link_notes += [
            f"{link['title']}: {link['href']}"
            for link in self._parse_attachment_links(response)
            if not link["href"].lower().endswith(DOC_EXTS)
        ]
        parts.append("\n".join(link_notes))

        return "\n".join(parts)

    def _parse_notes(self, response):
        texts = (
            self._clean_text(p)
            for p in response.css(".entry-content .entry-column-2 p")
        )
        return " ".join(filter(None, texts))

    def _parse_attachment_links(self, response):
        """Collects registration, video, and document links from the
        detail page's "<h2>...</h2><ul><li><a>" blocks."""
        links = []
        seen_hrefs = set()
        for anchor in response.css(".entry-content .entry-column-1 ul li a"):
            href = anchor.attrib.get("href")
            if not href:
                continue
            href = response.urljoin(href)
            # Skips a link once its href has already been added.
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            title = self._clean_text(anchor) or href
            # Collapses a doubled "(PDF) (PDF)" suffix down to one.
            title = re.sub(r"(\([^)]*\))\s*\1$", r"\1", title)
            links.append({"href": href, "title": title})
        return links

    def _parse_links(self, response):
        """Filters attachment links down to meeting documents."""
        return [
            link
            for link in self._parse_attachment_links(response)
            if link["href"].lower().endswith(DOC_EXTS)
        ]

    def _info_selector(self, response):
        return response.css(".entry-content .entry-column-1 p:not(.meeting-location)")

    def _clean_text(self, sel):
        """Flatten HTML and decode Cloudflare-obfuscated email addresses."""
        html = "".join(sel.getall())
        html = CF_EMAIL_WRAPPED_RE.sub(self._decode_cf_email_match, html)
        html = CF_EMAIL_RE.sub(self._decode_cf_email_match, html)
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", unescape(text)).strip()

    def _decode_cf_email_match(self, match):
        raw = bytes.fromhex(match.group("hex"))
        key = raw[0]

        return bytes(b ^ key for b in raw[1:]).decode()
