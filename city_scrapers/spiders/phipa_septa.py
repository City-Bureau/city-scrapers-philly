import re
from datetime import datetime
from html import unescape
from urllib.parse import urljoin

from city_scrapers_core.constants import (
    ADVISORY_COMMITTEE,
    BOARD,
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
# SEPTA sometimes appends more than one status tag, e.g.
# "Meeting Name (canceled) (remote)" - [^)]* (not +) also matches an empty
# "()" left over once a real tag next to it has been stripped.
STATUS_SUFFIX_RE = re.compile(r"\(([^)]*)\)\s*$")
DETAIL_TIME_RE = re.compile(
    r"Time and Date:\s*(?P<time>noon|midnight|\d{1,2}(?::\d{2})?\s*[ap]m)\s+"
    r"[A-Za-z]+,\s*(?P<date>[A-Za-z]+ \d{1,2}, \d{4})",
    re.IGNORECASE,
)
ORGANIZATION_RE = re.compile(
    r"Organization:\s*(?P<org>.+?)\s*Time and Date:", re.IGNORECASE
)
SESSION_TYPE_RE = re.compile(r"Session Type::?\s*(?P<session>.+)$", re.IGNORECASE)
TYPICAL_SCHEDULE_RE = re.compile(
    r"Meetings are typically held.*?(?:\.|$)", re.IGNORECASE
)
# SEPTA renders Cloudflare's email-obfuscation markup in two different
# shapes: an <a> wrapping a <span data-cfemail="...">, or a bare <a
# data-cfemail="..."> with no inner span. The first pattern below consumes
# the whole <a><span>...</span></a> wrapper so no stray tags are left for
# the later tag-stripping pass to turn into extra whitespace; the second
# catches whichever single tag (<a> or <span>) carries data-cfemail on its
# own.
CF_EMAIL_WRAPPED_RE = re.compile(
    r'<a\b[^>]*>\s*<span\b[^>]*\bdata-cfemail="(?P<hex>[0-9a-f]+)"[^>]*>'
    r"[^<]*</span>\s*</a>"
)
CF_EMAIL_RE = re.compile(
    r"<(?P<tag>a|span)\b[^>]*\bdata-cfemail=\"(?P<hex>[0-9a-f]+)\"[^>]*>"
    r"[^<]*</(?P=tag)>"
)


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
        cutoff = datetime.now() - relativedelta(years=self.archive_years)
        past_cutoff = False

        for item in response.css("li.entry-title"):
            link = item.css("div.entry-datetime a")
            href = link.attrib.get("href")
            listing_text = "".join(link.css("::text").getall())
            title, listing_start, cancelled = self._parse_listing_text(listing_text)
            listing_location = self._clean_text(item.css("div.entry-location"))
            # SEPTA also flags cancellations with a <div class="entry-canceled">
            # note (and an "entry-title canceled" class on the <li>) instead
            # of - or in addition to - a "(canceled)" title suffix; when that
            # div is present, the listing also omits entry-location entirely.
            if item.css("div.entry-canceled"):
                cancelled = True

            if not href or listing_start is None:
                continue
            if listing_start < cutoff:
                past_cutoff = True
                continue

            source = response.urljoin(href)
            yield Request(
                source,
                callback=self._parse_detail,
                cb_kwargs={
                    "title": title,
                    "listing_start": listing_start,
                    "cancelled": cancelled,
                    "source": source,
                    "listing_location": listing_location,
                },
            )

        next_href = response.css("div.wp-pagination a.next::attr(href)").get()
        if next_href and not past_cutoff:
            yield Request(urljoin(response.url, next_href), callback=self.parse)

    def _parse_detail(
        self, response, title, listing_start, cancelled, source, listing_location
    ):
        """Build a meeting from its authoritative detail notice."""
        detail_title = self._clean_text(response.css(".entry-header .entry-title"))
        is_cancelled = cancelled or "cancel" in detail_title.lower()

        meeting = Meeting(
            title=title,
            description=self._parse_description(response, source),
            classification=self._parse_classification(title),
            start=self._parse_detail_start(response) or listing_start,
            # SEPTA does not publish definitive end times.
            end=None,
            all_day=False,
            time_notes=self._parse_time_notes(response),
            location=self._parse_location(listing_location),
            # Only PDF documents belong in `links` - the
            # meeting-details page and any non-PDF attachment are folded
            # into the description instead (see `_parse_description`).
            links=self._parse_links(response),
            source=source,
        )
        meeting["status"] = "cancelled" if is_cancelled else self._get_status(meeting)
        meeting["id"] = self._get_id(meeting)
        yield meeting

    def _parse_listing_text(self, text):
        match = LISTING_RE.match(text)
        if not match:
            return text.strip(), None, False

        title = match.group("title")
        cancelled = False
        while True:
            status_match = STATUS_SUFFIX_RE.search(title)
            if not status_match:
                break
            if "cancel" in status_match.group(1).lower():
                cancelled = True
            title = title[: status_match.start()].strip()

        return (
            title,
            self._to_datetime(match.group("date"), match.group("time")),
            cancelled,
        )

    def _parse_detail_start(self, response):
        """Detail-page start time is more reliable than listing-widget time."""
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
        """Split the detail page's prose Location paragraph into an
        in-person part and a virtual/online part, normalizing SEPTA's
        "In-person:"/"In person:" and "Virtual:"/"Online:" label variants.
        Either part may be absent. This only feeds `_parse_description`
        now - the structured `location` field comes from the listing
        page's own <div class="entry-location"> instead (see
        `_parse_location`), so this is purely for surfacing extra detail
        (registration instructions, virtual platform) in the description.
        """
        text = self._clean_text(
            response.css(".entry-content .entry-column-1 p.meeting-location")
        )
        text = text.split("Location:", 1)[-1].strip()
        # SEPTA spells this "In person:", "In-person:", "In Person:", and
        # "In person :" (space before the colon) interchangeably depending
        # on the year/author.
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

    @staticmethod
    def _parse_location(listing_location):
        """The listing page's own <div class="entry-location"> is the
        authoritative source per QA feedback: empty for virtual-only
        meetings, absent entirely for canceled ones (both cases collapse
        to `listing_location` being falsy), and otherwise a clean
        "Venue Name, Street Address" pair."""
        if not listing_location:
            return {"name": "", "address": ""}

        name, _, address = listing_location.partition(",")
        return {"name": name.strip(), "address": address.strip()}

    @staticmethod
    def _parse_in_person_notes(block):
        """Any in-person text beyond the venue itself - e.g. registration
        or attendance instructions - for inclusion in the description."""
        in_person = block["in_person"]
        if not in_person:
            return ""
        match = re.search(r"\.\s*(To register\b.*)$", in_person, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _parse_description(self, response, source):
        info_text = self._clean_text(self._info_selector(response))
        location_block = self._parse_location_block(response)
        notes_text = self._parse_notes(response)
        time_notes = self._extract_time_notes(notes_text)

        if time_notes:
            notes_text = notes_text.replace(time_notes, "", 1).strip()

        parts = []

        org_match = ORGANIZATION_RE.search(info_text)
        if org_match:
            parts.append(f"Organization: {org_match.group('org').strip()}")

        session_match = SESSION_TYPE_RE.search(info_text)
        if session_match:
            parts.append(f"Session Type: {session_match.group('session').strip()}")

        in_person_notes = self._parse_in_person_notes(location_block)
        if in_person_notes:
            parts.append(f"In person: {in_person_notes}")

        if location_block["virtual"]:
            label = location_block["virtual_label"] or "Virtual"
            parts.append(f"{label}: {location_block['virtual']}")

        if notes_text:
            parts.append(notes_text)

        # `links` only keeps PDFs, so the meeting-details page
        # itself and any non-PDF attachment (registration link, video,
        # non-PDF document) are surfaced here instead of being dropped.
        link_notes = [f"Meeting Details: {source}"]
        link_notes += [
            f"{link['title']}: {link['href']}"
            for link in self._parse_attachment_links(response)
            if not link["href"].lower().endswith(".pdf")
        ]
        parts.append("\n".join(link_notes))

        return "\n".join(parts)

    def _parse_time_notes(self, response):
        return self._extract_time_notes(self._parse_notes(response))

    def _parse_notes(self, response):
        return " ".join(
            text
            for text in (
                self._clean_text(p)
                for p in response.css(".entry-content .entry-column-2 p")
            )
            if text
        )

    def _parse_attachment_links(self, response):
        """Some detail pages - mostly archived ones - publish a
        registration link, a meeting video, and/or documents (notice,
        agenda, minutes, transcript) as "<h2>...</h2><ul><li><a>" blocks
        after the location paragraph. `_parse_links` keeps only the PDFs
        from this; everything else is folded into the description by
        `_parse_description` instead, per QA feedback."""
        links = []
        seen_hrefs = set()
        for anchor in response.css(".entry-content .entry-column-1 ul li a"):
            href = anchor.attrib.get("href")
            if not href:
                continue
            href = response.urljoin(href)
            # SEPTA occasionally lists the exact same link (e.g. a meeting
            # video) under two different section headings.
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            title = self._clean_text(anchor) or href
            # A handful of SEPTA's own anchor texts double up their "(PDF)"
            # suffix, e.g. "Notice (Spanish) (PDF) (PDF)".
            title = re.sub(r"(\([^)]*\))\s*\1$", r"\1", title)
            links.append({"href": href, "title": title})
        return links

    def _parse_links(self, response):
        """`links` only holds PDF meeting documents (notice, agenda,
        minutes, transcript, etc.) per QA feedback."""
        return [
            link
            for link in self._parse_attachment_links(response)
            if link["href"].lower().endswith(".pdf")
        ]

    @staticmethod
    def _extract_time_notes(notes_text):
        match = TYPICAL_SCHEDULE_RE.search(notes_text)
        return match.group(0).strip() if match else ""

    @staticmethod
    def _info_selector(response):
        return response.css(".entry-content .entry-column-1 p:not(.meeting-location)")

    def _clean_text(self, sel):
        """Flatten HTML and decode Cloudflare-obfuscated email addresses."""
        html = "".join(sel.getall())
        html = CF_EMAIL_WRAPPED_RE.sub(self._decode_cf_email_match, html)
        html = CF_EMAIL_RE.sub(self._decode_cf_email_match, html)
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", unescape(text)).strip()

    def _decode_cf_email_match(self, match):
        hex_str = match.group("hex")
        key = int(hex_str[:2], 16)

        return "".join(
            chr(int(hex_str[i : i + 2], 16) ^ key) for i in range(2, len(hex_str), 2)
        )
