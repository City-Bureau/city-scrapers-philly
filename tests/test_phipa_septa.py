from datetime import datetime
from os.path import dirname, join

from city_scrapers_core.constants import ADVISORY_COMMITTEE, BOARD, COMMITTEE
from city_scrapers_core.utils import file_response
from freezegun import freeze_time
from scrapy.http import HtmlResponse

from city_scrapers.spiders.phipa_septa import PhipaSeptaSpider

# Narrow, single-page HTML quirks are inlined here rather than saved as
# full downloaded pages under tests/files/ - the spider only ever selects
# within .entry-header/.entry-content, so a full ~180KB real page adds
# nothing a small literal snippet doesn't already cover.
BARE_CFEMAIL_PDF_URL = "https://wwww.septa.org/wp-content/uploads/meeting/cac/2025-1028-CAC-Plenary-Minutes-R1.pdf"  # noqa
DUP_LINK_VIMEO_URL = "https://vimeo.com/880978025/9a476c7727?share=copy"
DUP_LINK_SPECIAL_NOTICE_PDF_URL = "https://wwww.septa.org/wp-content/uploads/board/septa-board/special-notice.pdf"  # noqa
DUP_LINK_RECESSED_AGENDA_PDF_URL = "https://wwww.septa.org/wp-content/uploads/board/septa-board/recessed-agenda.pdf"  # noqa
DUP_PDF_SUFFIX_SPANISH_URL = "https://wwww.septa.org/wp-content/uploads/meeting/general/notice-spanish.pdf"  # noqa
DUP_PDF_SUFFIX_CHINESE_URL = "https://wwww.septa.org/wp-content/uploads/meeting/general/notice-chinese.pdf"  # noqa

BARE_CFEMAIL_HTML = f"""<html><body><article>
<header class="entry-header"><h1 class="entry-title">CAC Plenary Meeting</h1></header>
<div class="entry-content"><div class="flex entry-columns">
<div class="entry-column-1 no-border"><p><strong>Organization:</strong>
<a href="https://wwww.septa.org/about/partners/#cac">Citizen Advisory Committee</a><br>
<strong>Time and Date:</strong> 5:30 pm Tuesday, October 28, 2025<br>
<strong>Session Type::</strong> Open to the public<br></p>
<p class="meeting-location"><strong>Location:</strong><br>Online via Teams,
please email <a href="/cdn-cgi/l/email-protection" class="__cf_email__"
data-cfemail="5d1e1c1e1d2e382d293c73322f3a">[email&#160;protected]</a>
for the meeting link.</p>
<h2 id="documents">Meeting Documents</h2><ul><li>
<a href="{BARE_CFEMAIL_PDF_URL}" rel="nofollow">Minutes (PDF)</a></li></ul></div>
</div></div>
</article></body></html>""".encode("utf-8")

DUP_LINK_HTML = f"""<html><body><article>
<header class="entry-header">
<h1 class="entry-title">SEPTA Board Regular Meeting</h1></header>
<div class="entry-content"><div class="flex entry-columns">
<div class="entry-column-1 no-border"><p><strong>Organization:</strong>
<a href="https://wwww.septa.org/about/septa-board/">SEPTA Board</a><br>
<strong>Time and Date:</strong> 3:00 pm Thursday, October 26, 2023<br>
<strong>Session Type::</strong> Open to the public<br></p>
<p class="meeting-location"><strong>Location:</strong><br>
The regular SEPTA Board Meeting will be rescheduled to a date
that is to be determined.</p>
<h2 id="attend">Register and Attend</h2><ul><li>
<a href="{DUP_LINK_VIMEO_URL}" rel="nofollow">Meeting Link</a>
</li></ul>
<h2 id="links">Links</h2><ul><li>
<a href="{DUP_LINK_VIMEO_URL}">Meeting Video Link</a></li></ul>
<h2 id="documents">Meeting Documents</h2><ul>
<li><a href="https://wwww.septa.org/wp-content/uploads/board/septa-board/notice.pdf"
rel="nofollow">Meeting Notice (PDF)</a></li>
<li><a href="https://wwww.septa.org/wp-content/uploads/board/septa-board/agenda.pdf"
rel="nofollow">Agenda (PDF)</a></li>
<li><a href="https://wwww.septa.org/wp-content/uploads/board/septa-board/minutes.pdf"
rel="nofollow">Minutes (PDF)</a></li>
<li><a href="https://wwww.septa.org/wp-content/uploads/board/septa-board/transcript.pdf"
rel="nofollow">Transcript (PDF)</a></li></ul>
<h3>Additional Documents</h3><ul>
<li><a href="{DUP_LINK_SPECIAL_NOTICE_PDF_URL}">
Special Board Meeting Notice Recessed to 10/27 (PDF)</a></li>
<li><a href="{DUP_LINK_RECESSED_AGENDA_PDF_URL}">
Recessed October 2023 Board Meeting Agenda (PDF)</a></li></ul></div>
</div></div>
</article></body></html>""".encode("utf-8")

DUP_PDF_SUFFIX_HTML = f"""<html><body><article>
<header class="entry-header">
<h1 class="entry-title">SEPTA Annual Service Plan Public Hearing</h1></header>
<div class="entry-content"><div class="flex entry-columns">
<div class="entry-column-1 has-border"><p><strong>Organization:</strong>
General Public<br>
<strong>Time and Date:</strong> 5:00 pm Wednesday, April 15, 2026<br>
<strong>Session Type::</strong> Open to the public<br></p>
<p class="meeting-location"><strong>Location:</strong><br>
<b>In person</b>: SEPTA Board Room<br />
1234 Market Street, Mezzanine Level, Philadelphia, PA 19107<br />
<b>Virtual</b>: Webex</p>
<h2 id="attend">Register and Attend</h2><ul><li>
<a href="https://septaorg.webex.com/weblink/register/r88f3bc11554f03e65fd4c3b40c034f70"
rel="nofollow">Meeting Registration Link</a></li></ul>
<h2 id="documents">Meeting Documents</h2><ul><li>
<a href="https://wwww.septa.org/wp-content/uploads/meeting/general/notice-english.pdf"
rel="nofollow">Meeting Notice (PDF)</a></li></ul>
<h3>Additional Documents</h3><ul>
<li><a href="{DUP_PDF_SUFFIX_SPANISH_URL}">
Notice of Public Hearing (Spanish/Español) (PDF) (PDF)</a></li>
<li><a href="{DUP_PDF_SUFFIX_CHINESE_URL}">
Notice of Public Hearing (Simplified Chinese/简体中文) (PDF) (PDF)</a></li></ul></div>
</div></div>
</article></body></html>""".encode("utf-8")

test_response = file_response(
    join(dirname(__file__), "files", "phipa_septa.html"),
    url="https://wwww.septa.org/about/meetings/",
)
board_detail_response = file_response(
    join(dirname(__file__), "files", "phipa_septa_detail.html"),
    url="https://wwww.septa.org/about/meetings/septa-board-meeting-september-2026/",
)
VIRTUAL_URL = "https://wwww.septa.org/about/meetings/cac-regional-rail-subcommittee-september-2026/"  # noqa
virtual_detail_response = file_response(
    join(dirname(__file__), "files", "phipa_septa_detail_virtual.html"),
    url=VIRTUAL_URL,
)
MIXED_URL = "https://wwww.septa.org/about/meetings/cac-plenary-meeting-november-2026/"
mixed_detail_response = file_response(
    join(dirname(__file__), "files", "phipa_septa_detail_mixed.html"),
    url=MIXED_URL,
)
CAPITALIZED_URL = (
    "https://wwww.septa.org/about/meetings/septa-board-regular-meeting-123/"
)
capitalized_detail_response = file_response(
    join(dirname(__file__), "files", "phipa_septa_detail_capitalized.html"),
    url=CAPITALIZED_URL,
)
archive_response = file_response(
    join(dirname(__file__), "files", "phipa_septa_archive.html"),
    url="https://wwww.septa.org/about/meetings/page/11/?archive=1",
)
BARE_CFEMAIL_URL = "https://wwww.septa.org/about/meetings/cac-plenary-meeting-october/"
bare_cfemail_detail_response = HtmlResponse(
    url=BARE_CFEMAIL_URL, body=BARE_CFEMAIL_HTML, encoding="utf-8"
)
DUP_LINK_URL = "https://wwww.septa.org/about/meetings/septa-board-regular-meeting-98/"
dup_link_detail_response = HtmlResponse(
    url=DUP_LINK_URL, body=DUP_LINK_HTML, encoding="utf-8"
)
DUP_PDF_SUFFIX_URL = (
    "https://wwww.septa.org/about/meetings/service-plan-public-hearing-2/"
)
dup_pdf_suffix_detail_response = HtmlResponse(
    url=DUP_PDF_SUFFIX_URL, body=DUP_PDF_SUFFIX_HTML, encoding="utf-8"
)
cancelled_listing_response = file_response(
    join(dirname(__file__), "files", "phipa_septa_cancelled_listing.html"),
    url="https://wwww.septa.org/about/meetings/",
)
BOARD_ROOM_LISTING_LOCATION = (
    "SEPTA Board Room, 1234 Market Street, Mezzanine Level, Philadelphia, PA 19107"
)
spider = PhipaSeptaSpider()

freezer = freeze_time("2026-08-14")
freezer.start()

requests = [req for req in spider.parse(test_response)]
board_url = "https://wwww.septa.org/about/meetings/septa-board-meeting-september-2026/"
board_request = next(req for req in requests if req.url == board_url)
board_item = next(
    spider._parse_detail(board_detail_response, **board_request.cb_kwargs)
)

virtual_request = next(req for req in requests if req.url == VIRTUAL_URL)
virtual_item = next(
    spider._parse_detail(virtual_detail_response, **virtual_request.cb_kwargs)
)

mixed_request = next(req for req in requests if req.url == MIXED_URL)
mixed_item = next(
    spider._parse_detail(mixed_detail_response, **mixed_request.cb_kwargs)
)

capitalized_item = next(
    spider._parse_detail(
        capitalized_detail_response,
        title="SEPTA Board Regular Meeting",
        listing_start=datetime(2024, 12, 19, 15, 0),
        cancelled=False,
        listing_location=BOARD_ROOM_LISTING_LOCATION,
        listing_session_type="Open to the public",
    )
)

archive_requests = [req for req in spider.parse(archive_response)]

bare_cfemail_item = next(
    spider._parse_detail(
        bare_cfemail_detail_response,
        title="CAC Plenary Meeting",
        listing_start=datetime(2025, 10, 28, 17, 30),
        cancelled=False,
        listing_location="",
        listing_session_type="Open to the public",
    )
)

dup_link_item = next(
    spider._parse_detail(
        dup_link_detail_response,
        title="SEPTA Board Regular Meeting",
        listing_start=datetime(2023, 10, 26, 19, 0),
        cancelled=False,
        listing_location="",
        listing_session_type="Open to the public",
    )
)

dup_pdf_suffix_item = next(
    spider._parse_detail(
        dup_pdf_suffix_detail_response,
        title="SEPTA Annual Service Plan Public Hearing",
        listing_start=datetime(2026, 4, 15, 18, 0),
        cancelled=False,
        listing_location=BOARD_ROOM_LISTING_LOCATION,
        listing_session_type="Open to the public",
    )
)

# Full end-to-end check for the old-meeting path: take a request the
# archive listing actually produced (not hand-built kwargs) and run it
# through the same detail-page parsing as any other meeting.
archive_detail_request = next(
    req
    for req in archive_requests
    if req.url
    == "https://wwww.septa.org/about/meetings/septa-board-regular-meeting-97/"
)
archive_detail_response = file_response(
    join(dirname(__file__), "files", "phipa_septa_archive_detail.html"),
    url=archive_detail_request.url,
)
archive_item = next(
    spider._parse_detail(archive_detail_response, **archive_detail_request.cb_kwargs)
)

cancelled_request = next(
    req
    for req in requests
    if req.url
    == "https://wwww.septa.org/about/meetings/septa-committee-meeting-august-2026/"
)

# SEPTA also marks cancellations with a <div class="entry-canceled"> note
# (and an "entry-title canceled" class) instead of a "(canceled)" title
# suffix; that listing format also omits entry-location entirely.
cancelled_via_div_requests = [req for req in spider.parse(cancelled_listing_response)]

freezer.stop()


def test_request_count():
    # 20 meeting detail requests + 1 pagination request to page 2
    assert len(requests) == 21


def test_title():
    assert board_item["title"] == "SEPTA Board Regular Meeting"


def test_start():
    # The listing page text says 7:00 pm, but the detail page's own "Time
    # and Date:" field - the authoritative source - says 3:00 pm.
    assert board_item["start"] == datetime(2026, 9, 24, 15, 0)


def test_start_prefers_detail_page_over_listing():
    # Listing text for this meeting says 9:30 pm; the detail page says
    # 5:30 pm, which is what should win.
    assert virtual_item["start"] == datetime(2026, 9, 1, 17, 30)


def test_start_handles_bare_hour_time():
    # dateutil's parser handles "3pm"-style bare hours natively, with no
    # manual ":00" insertion needed first.
    _, start, _ = spider._parse_listing_text(
        " August 27, 2026, at 3pm: SEPTA Board Regular Meeting"
    )
    assert start == datetime(2026, 8, 27, 15, 0)


def test_to_datetime_logs_warning_on_unparseable_input(caplog):
    result = spider._to_datetime("Not a real month 2026", "3:00 pm")
    assert result is None
    assert "Could not parse datetime" in caplog.text


def test_id():
    assert board_item["id"] == "phipa_septa/202609241500/x/septa_board_regular_meeting"


def test_status_cancelled():
    assert cancelled_request.cb_kwargs["cancelled"] is True
    assert cancelled_request.cb_kwargs["title"] == (
        "Administration & Operations Committees Meeting"
    )


def test_status_cancelled_via_entry_canceled_div():
    canceled_urls = [
        "https://wwww.septa.org/about/meetings/septa-committee-meeting-august-2026/",
        "https://wwww.septa.org/about/meetings/septa-board-meeting-august-2026/",
    ]
    matched = [req for req in cancelled_via_div_requests if req.url in canceled_urls]
    assert len(matched) == 2
    assert all(req.cb_kwargs["cancelled"] is True for req in matched)
    # This listing format omits entry-location entirely for canceled
    # meetings, alongside skipping the "(canceled)" title suffix.
    assert all(req.cb_kwargs["listing_location"] == "" for req in matched)
    assert all(
        "canceled" not in req.cb_kwargs["title"].lower() for req in matched
    ), "title suffix stripping should be a no-op here since there is none"


def test_listing_text_multiple_status_tags():
    # SEPTA sometimes appends more than one trailing tag, e.g.
    # "Meeting Name (canceled) (remote)". Only the cancellation tag is
    # stripped from the title - "(remote)" is meaningful and stays -
    # and "canceled" must be detected no matter which position it's in.
    title, start, cancelled = spider._parse_listing_text(
        " May 27, 2025, at 9:30 pm: CAC Plenary Meeting (canceled) (remote)"
    )
    assert title == "CAC Plenary Meeting (remote)"
    assert cancelled is True
    assert start == datetime(2025, 5, 27, 21, 30)


def test_status():
    assert board_item["status"] == "tentative"


def test_location():
    # The listing page's own <div class="entry-location"> is the
    # authoritative source per QA feedback, not the detail page's prose.
    assert board_item["location"] == {
        "name": "SEPTA Board Room",
        "address": "1234 Market Street, Mezzanine Level, Philadelphia, PA 19107",
    }


def test_location_empty_for_virtual_meetings():
    # entry-location is blank for virtual-only meetings on the listing
    # page; the platform info still surfaces in the description instead
    # (see test_description_decodes_obfuscated_email).
    assert virtual_item["location"] == {"name": "", "address": ""}


def test_location_comes_from_listing_not_detail_page():
    # This meeting's detail page describes the venue as "In-person at 1234
    # Market Street, Room 10A" with no formal name, but the listing page's
    # entry-location gives the fuller "SEPTA Headquarters, 1234 Market
    # Street, Room 10A, Philadelphia" - the listing wins now.
    assert mixed_item["location"] == {
        "name": "SEPTA Headquarters",
        "address": "1234 Market Street, Room 10A, Philadelphia",
    }


def test_source():
    assert (
        board_item["source"]
        == "https://wwww.septa.org/about/meetings/septa-board-meeting-september-2026/"
    )


def test_links_empty_when_no_attachments():
    # This detail page has no <ul><li><a> attachment section at all.
    assert board_item["links"] == []


def test_classification():
    assert board_item["classification"] == BOARD


def test_classification_committee():
    assert (
        spider._parse_classification("Administration & Operations Committees Meeting")
        == COMMITTEE
    )


def test_classification_advisory():
    assert (
        spider._parse_classification(
            "SEPTA's Advisory Committee for Accessible Transportation (SAC) Meeting"
        )
        == ADVISORY_COMMITTEE
    )


def test_all_day():
    assert board_item["all_day"] is False


def test_description_includes_meeting_details_link():
    # QA feedback: the "Meeting Details" self-link no longer lives in
    # `links` - it's folded into the description instead.
    assert f"Meeting Details: {board_url}" in board_item["description"]


def test_description_decodes_obfuscated_email():
    # SEPTA obfuscates the mailto address on this page via Cloudflare's
    # email-protection scramble; it should be decoded to plain text rather
    # than left as an unreadable placeholder.
    assert "Organization: CAC Regional Rail Subcommittee" in virtual_item["description"]
    assert "Session Type: Closed session" in virtual_item["description"]
    assert "CAC@septa.org" in virtual_item["description"]
    assert "cfemail" not in virtual_item["description"]
    assert "[email" not in virtual_item["description"]


def test_end():
    # SEPTA doesn't publish an authoritative end time, so `end` is left for
    # the Meeting pipeline to default to two hours after `start`.
    assert board_item["end"] is None


def test_time_notes():
    # SEPTA does not publish a reliable "typical schedule" note, so
    # `time_notes` is always empty.
    assert board_item["time_notes"] == ""
    assert virtual_item["time_notes"] == ""


def test_description_keeps_in_person_registration_instructions():
    # The registration instructions that don't belong in the structured
    # `location` field must still show up somewhere - here, in
    # description - rather than being silently dropped.
    assert (
        "In person: To register for in-person meetings, send an email to "
        "CAC@SEPTA.org. Remember to bring your ID, and arrive a few minutes "
        "early to be escorted upstairs." in mixed_item["description"]
    )
    assert (
        "Online: Via Microsoft Teams. For a meeting link, email CAC@SEPTA.org."
        in mixed_item["description"]
    )
    assert "cfemail" not in mixed_item["description"]
    assert "[email" not in mixed_item["description"]


def test_description_normalizes_capitalized_in_person_label():
    # SEPTA also spells this "In Person:" (capital P) on some older pages;
    # it must still be recognized so the "Virtual: Webex" note in the
    # description is isolated correctly rather than swallowing the whole
    # location paragraph.
    assert "Virtual: Webex" in capitalized_item["description"]


def test_links_pdf_only():
    # QA feedback: `links` only holds PDF documents. The registration link
    # and meeting video from this page belong in the description instead.
    assert capitalized_item["links"] == [
        {
            "href": "https://wwww.septa.org/wp-content/uploads/meeting/septa-board/december-2024-committee-meetings-board-meeting-notice_001.pdf",  # noqa
            "title": "Meeting Notice (PDF)",
        },
        {
            "href": "https://wwww.septa.org/wp-content/uploads/meeting/septa-board/december-2024-board-agenda-financials-revised-resolutions-website.pdf",  # noqa
            "title": "Agenda (PDF)",
        },
        {
            "href": "https://wwww.septa.org/wp-content/uploads/meeting/septa-board/december-19-2024-board-meeting-minutes-final.pdf",  # noqa
            "title": "Minutes (PDF)",
        },
        {
            "href": "https://wwww.septa.org/wp-content/uploads/meeting/septa-board/december-19-2024-board-meeting-transcript.pdf",  # noqa
            "title": "Transcript (PDF)",
        },
    ]


def test_description_includes_non_pdf_links():
    # The registration link and meeting video filtered out of `links`
    # still appear in the description, so nothing is lost.
    assert (
        "Meeting Registration Link: https://septaorg.webex.com/weblink/register/"
        "r78076d52130ab033e85c881befd37e7e" in capitalized_item["description"]
    )
    assert (
        "Meeting Video Link: https://vimeo.com/1041176055/a02878935a?share=copy"
        in capitalized_item["description"]
    )
    assert f"Meeting Details: {CAPITALIZED_URL}" in capitalized_item["description"]


def test_archive_cutoff_filters_old_meetings():
    # This archive page's 20 meetings span both sides of the 3-year cutoff
    # (2023-08-14, relative to the frozen "today" of 2026-08-14); only the
    # 12 at or after the cutoff should turn into detail requests.
    assert len(archive_requests) == 12
    assert all(
        req.cb_kwargs["listing_start"] >= datetime(2023, 8, 14)
        for req in archive_requests
    )


def test_archive_cutoff_stops_pagination():
    # Once a page's listing crosses the cutoff, there's no reason to
    # request the next (even older) archive page.
    assert not any(
        req.url.startswith("https://wwww.septa.org/about/meetings/page/")
        for req in archive_requests
    )


def test_description_decodes_bare_anchor_cfemail():
    # Some pages put class="__cf_email__" and data-cfemail directly on the
    # <a> tag with no inner <span>, a second obfuscation shape SEPTA uses
    # alongside the <a><span>...</span></a> one covered by the other test.
    assert "CAC@septa.org" in bare_cfemail_item["description"]
    assert "cfemail" not in bare_cfemail_item["description"]
    assert "[email" not in bare_cfemail_item["description"]
    # No stray space should be left where the wrapper tags were removed.
    assert " ." not in bare_cfemail_item["description"]


def test_archive_item_end_to_end():
    # This meeting's request came from parsing the real archive listing
    # (not hand-built kwargs), and its start time again shows the listing
    # page disagreeing with the detail page (7:00 pm vs 3:00 pm) - the
    # same bug, confirmed present in the archive too, not just upcoming
    # meetings.
    # The real listing text for this one is "... (canceled) (remote)" -
    # only the cancellation tag is stripped, so "(remote)" stays.
    assert archive_item["title"] == "SEPTA Board Regular Meeting (remote)"
    assert archive_item["start"] == datetime(2023, 8, 24, 15, 0)
    assert archive_item["classification"] == BOARD
    # This archived meeting's listing entry has an empty entry-location.
    assert archive_item["location"] == {"name": "", "address": ""}
    # It was genuinely cancelled, so status must say so rather than
    # falling back to "passed" just because the date is old.
    assert archive_item["status"] == "cancelled"


def test_links_deduplicated_by_href():
    # This page genuinely lists the same non-PDF video link twice - once
    # (mislabeled) under "Register and Attend", again under "Links" - so
    # only the first occurrence should survive, and it should only ever
    # show up once in the description too.
    assert (
        dup_link_item["description"].count(
            "https://vimeo.com/880978025/9a476c7727?share=copy"
        )
        == 1
    )
    assert "Meeting Link: https://vimeo.com/880978025/9a476c7727?share=copy" in (
        dup_link_item["description"]
    )
    # The PDFs on this page are unaffected and all land in `links`.
    assert len(dup_link_item["links"]) == 6
    assert all(link["href"].lower().endswith(".pdf") for link in dup_link_item["links"])


def test_link_titles_collapse_duplicated_pdf_suffix():
    # SEPTA's own anchor text for these documents literally reads
    # "... (PDF) (PDF)"; collapse the doubled suffix down to one.
    titles = [link["title"] for link in dup_pdf_suffix_item["links"]]
    assert "Notice of Public Hearing (Spanish/Español) (PDF)" in titles
    assert not any(t.endswith("(PDF) (PDF)") for t in titles)
