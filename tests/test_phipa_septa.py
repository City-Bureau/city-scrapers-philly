from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import ADVISORY_COMMITTEE, BOARD, COMMITTEE
from city_scrapers_core.utils import file_response
from freezegun import freeze_time
from scrapy.http import HtmlResponse

from city_scrapers.spiders.phipa_septa import PhipaSeptaSpider

# Full downloaded pages live under tests/files/; the few HTML shapes the
# live site doesn't currently produce (non-PDF document links, a doubled
# "(PDF) (PDF)" suffix, a link repeated under two headings) are inlined
# here as minimal <p class="entry-docs"> snippets.
DOCS_BASE = "https://wwww.septa.org/wp-content/uploads/meeting/septa-board"


def _detail_html(entry_docs):
    return f"""<html><body><article>
<header class="entry-header"><h1 class="entry-title">SEPTA Board Regular Meeting</h1>
</header>
<div class="entry-content">
<p><strong>SEPTA Board</strong><br />May 28, 2026, at 3:00 pm<br />
SEPTA Board Room, 1234 Market Street, Mezzanine Level, Philadelphia, PA 19107<br />
Open to the public<br /></p>
<p class="entry-docs">{entry_docs}</p>
</div></article></body></html>""".encode(
        "utf-8"
    )


MULTI_EXT_DOCS = (
    f'<span><a href="{DOCS_BASE}/notice.pdf">Meeting Notice (PDF)</a></span>'
    f'<span><a href="{DOCS_BASE}/agenda.docx">Agenda (DOCX)</a></span>'
    f'<span><a href="{DOCS_BASE}/minutes.doc">Minutes (DOC)</a></span>'
    f'<span><a href="{DOCS_BASE}/financials.xlsx">Financials (XLSX)</a></span>'
    '<span><a href="https://vimeo.com/1041176055/a02878935a">Video</a></span>'
)
DUP_VIDEO_URL = "https://vimeo.com/880978025"
DUP_HREF_DOCS = (
    f'<span><a href="{DUP_VIDEO_URL}">Meeting Link</a></span>'
    f'<span><a href="{DUP_VIDEO_URL}">Meeting Video Link</a></span>'
    f'<span><a href="{DOCS_BASE}/notice.pdf">Meeting Notice (PDF)</a></span>'
)
DOUBLED_SUFFIX_DOCS = (
    f'<span><a href="{DOCS_BASE}/notice-es.pdf">'
    "Notice of Public Hearing (Spanish/Espa&#241;ol) (PDF) (PDF)</a></span>"
)

DETAIL_URL = "https://wwww.septa.org/about/meetings/septa-board-meeting-september-2026/"
MIXED_URL = "https://wwww.septa.org/about/meetings/pension-committee-meeting-september-2026/"  # noqa
VIRTUAL_URL = "https://wwww.septa.org/about/meetings/sac-meeting-sept/"
DOCS_URL = "https://wwww.septa.org/about/meetings/septa-board-meeting-may-2026/"
CANCELLED_DETAIL_URL = (
    "https://wwww.septa.org/about/meetings/septa-board-meeting-august-2026/"
)
ARCHIVE_DETAIL_URL = (
    "https://wwww.septa.org/about/meetings/septa-board-regular-meeting-97/"
)
BOARD_ROOM_LISTING_LOCATION = (
    "SEPTA Board Room, 1234 Market Street, Mezzanine Level, Philadelphia, PA 19107"
)


def _fixture(name, url):
    return file_response(join(dirname(__file__), "files", name), url=url)


spider = PhipaSeptaSpider()

freezer = freeze_time("2026-08-14")
freezer.start()

test_response = _fixture("phipa_septa.html", "https://wwww.septa.org/about/meetings/")
requests = [req for req in spider.parse(test_response)]

board_request = next(req for req in requests if req.url == DETAIL_URL)
board_item = next(
    spider._parse_detail(
        _fixture("phipa_septa_detail.html", DETAIL_URL), **board_request.cb_kwargs
    )
)

mixed_request = next(req for req in requests if req.url == MIXED_URL)
mixed_item = next(
    spider._parse_detail(
        _fixture("phipa_septa_detail_mixed.html", MIXED_URL), **mixed_request.cb_kwargs
    )
)

virtual_request = next(req for req in requests if req.url == VIRTUAL_URL)
virtual_item = next(
    spider._parse_detail(
        _fixture("phipa_septa_detail_virtual.html", VIRTUAL_URL),
        **virtual_request.cb_kwargs,
    )
)

# The May board meeting: its detail page has several PDF documents plus a
# (non-document) video link, and its Webex links have expired. It isn't on
# the upcoming listing, so its listing kwargs are supplied directly.
docs_item = next(
    spider._parse_detail(
        _fixture("phipa_septa_detail_docs.html", DOCS_URL),
        title="SEPTA Board Regular Meeting",
        listing_start=datetime(2026, 5, 28, 15, 0),
        cancelled=False,
        listing_location=BOARD_ROOM_LISTING_LOCATION,
        listing_session_type="Open to the public",
    )
)

cancelled_detail_item = next(
    spider._parse_detail(
        _fixture("phipa_septa_detail_cancelled.html", CANCELLED_DETAIL_URL),
        title="SEPTA Board Regular Meeting",
        listing_start=datetime(2026, 8, 27, 15, 0),
        cancelled=False,
        listing_location=BOARD_ROOM_LISTING_LOCATION,
        listing_session_type="Open to the public",
    )
)

archive_response = _fixture(
    "phipa_septa_archive.html",
    "https://wwww.septa.org/about/meetings/page/11/?archive=1",
)
archive_requests = [req for req in spider.parse(archive_response)]

# End-to-end old-meeting path: take a request the archive listing actually
# produced and run it through the same detail parsing as any other meeting.
archive_detail_request = next(
    req for req in archive_requests if req.url == ARCHIVE_DETAIL_URL
)
archive_item = next(
    spider._parse_detail(
        _fixture("phipa_septa_archive_detail.html", ARCHIVE_DETAIL_URL),
        **archive_detail_request.cb_kwargs,
    )
)

# SEPTA also marks a cancellation with a <div class="entry-canceled"> note
# (that listing format omits entry-location/entry-details entirely) rather
# than a "(canceled)" title suffix.
cancelled_via_div_response = _fixture(
    "phipa_septa_cancelled_listing.html",
    "https://wwww.septa.org/about/meetings/?archive=1",
)
cancelled_via_div_requests = [req for req in spider.parse(cancelled_via_div_response)]

freezer.stop()


def _detail_response(entry_docs, url=DETAIL_URL):
    return HtmlResponse(url=url, body=_detail_html(entry_docs), encoding="utf-8")


def _parse_inline(entry_docs):
    return next(
        spider._parse_detail(
            _detail_response(entry_docs),
            title="SEPTA Board Regular Meeting",
            listing_start=datetime(2026, 5, 28, 15, 0),
            cancelled=False,
            listing_location=BOARD_ROOM_LISTING_LOCATION,
            listing_session_type="Open to the public",
        )
    )


def test_request_count():
    # 20 meeting detail requests + 1 pagination request to page 2.
    assert len(requests) == 21


def test_title():
    assert board_item["title"] == "SEPTA Board Regular Meeting"


def test_start():
    assert board_item["start"] == datetime(2026, 9, 24, 15, 0)


def test_start_read_from_detail_summary_paragraph():
    # The detail page's own "... September 24, 2026, at 3:00 pm ..." line
    # is parsed independently of the listing time.
    detail = _fixture("phipa_septa_detail.html", DETAIL_URL)
    assert spider._parse_detail_start(detail) == datetime(2026, 9, 24, 15, 0)


def test_detail_start_is_none_when_summary_has_no_date_stamp():
    detail = HtmlResponse(
        url=DETAIL_URL,
        body=b"<html><body><div class='entry-content'></div></body></html>",
        encoding="utf-8",
    )
    assert spider._parse_detail_start(detail) is None


def test_start_handles_bare_hour_time():
    # dateutil's parser handles "3pm"-style bare hours natively.
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


def test_status_tentative():
    assert board_item["status"] == "tentative"


def test_status_cancelled_via_title_suffix():
    # A "(canceled)" suffix in the listing line flags the meeting and is
    # stripped from the stored title.
    title, _, cancelled = spider._parse_listing_text(
        " August 20, 2026, at noon: Administration & Operations Committee (canceled)"
    )
    assert cancelled is True
    assert title == "Administration & Operations Committee"


def test_status_cancelled_via_entry_canceled_div_on_listing():
    canceled_urls = {
        "https://wwww.septa.org/about/meetings/septa-board-meeting-august-2026/",
        "https://wwww.septa.org/about/meetings/septa-committee-meeting-august-2026/",
    }
    matched = [req for req in cancelled_via_div_requests if req.url in canceled_urls]
    assert len(matched) == 2
    assert all(req.cb_kwargs["cancelled"] is True for req in matched)
    # This listing format drops entry-location for canceled meetings.
    assert all(req.cb_kwargs["listing_location"] == "" for req in matched)


def test_status_cancelled_via_entry_canceled_note_on_detail_page():
    # The listing kwargs say cancelled=False here; the "Canceled: ..." note
    # inside the detail page's .entry-content is what flips it.
    assert cancelled_detail_item["status"] == "cancelled"


def test_listing_text_multiple_status_tags():
    # "Meeting Name (canceled) (remote)": only the cancellation tag is
    # stripped - "(remote)" stays - and "canceled" is detected wherever
    # it sits.
    title, start, cancelled = spider._parse_listing_text(
        " May 27, 2025, at 9:30 pm: CAC Plenary Meeting (canceled) (remote)"
    )
    assert title == "CAC Plenary Meeting (remote)"
    assert cancelled is True
    assert start == datetime(2025, 5, 27, 21, 30)


def test_location_split_into_name_and_address():
    assert board_item["location"] == {
        "name": "SEPTA Board Room",
        "address": "1234 Market Street, Mezzanine Level, Philadelphia, PA 19107",
    }


def test_location_comes_from_listing_not_detail_page():
    # The detail page only says "Remote meeting" / a bare address line; the
    # listing's <div class="entry-location"> is the authoritative source.
    assert mixed_item["location"] == {
        "name": "SEPTA Board Room",
        "address": "1234 Market Street, Mezzanine Level, Philadelphia, PA 19107",
    }


def test_location_empty_for_virtual_meetings():
    assert virtual_item["location"] == {"name": "", "address": ""}


def test_location_bare_street_address_has_no_name():
    assert spider._parse_location("1234 Market St, Philadelphia, PA 19107") == {
        "name": "",
        "address": "1234 Market St, Philadelphia, PA 19107",
    }


def test_location_nonstandard_text_kept_whole_as_name():
    # Regression: a comma in free-form text must not be treated as a
    # name/address boundary (CodeRabbit finding). The suffix here is an
    # instruction, not an address, so the whole value stays in `name`.
    assert spider._parse_location(
        "Room 108, please sign in at the front desk on arrival"
    ) == {
        "name": "Room 108, please sign in at the front desk on arrival",
        "address": "",
    }


def test_source():
    assert board_item["source"] == DETAIL_URL


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


def test_end():
    # SEPTA publishes no authoritative end time.
    assert board_item["end"] is None


def test_time_notes():
    assert board_item["time_notes"] == ""
    assert virtual_item["time_notes"] == ""


def test_links_hold_meeting_documents():
    assert board_item["links"] == [
        {
            "href": "https://wwww.septa.org/wp-content/uploads/meeting/septa-board/september-2026-committee-meetings-and-board-meeting-notice.pdf",  # noqa
            "title": "Meeting Notice (PDF)",
        }
    ]


def test_links_multiple_documents():
    assert docs_item["links"] == [
        {
            "href": "https://wwww.septa.org/wp-content/uploads/meeting/septa-board/may-2026-committee-meetings-and-board-meeting-notice.pdf",  # noqa
            "title": "Meeting Notice (PDF)",
        },
        {
            "href": "https://wwww.septa.org/wp-content/uploads/meeting/septa-board/may-28-2026-board-meeting-agenda-financials-website.pdf",  # noqa
            "title": "Agenda (PDF)",
        },
        {
            "href": "https://wwww.septa.org/wp-content/uploads/meeting/septa-board/may-28-2026-board-meeting-transcript.pdf",  # noqa
            "title": "Transcript (PDF)",
        },
    ]


def test_links_empty_when_no_documents():
    assert virtual_item["links"] == []


@pytest.mark.parametrize(
    "filename,title",
    [
        ("notice.pdf", "Meeting Notice (PDF)"),
        ("agenda.docx", "Agenda (DOCX)"),
        ("minutes.doc", "Minutes (DOC)"),
        ("financials.xlsx", "Financials (XLSX)"),
    ],
)
def test_links_include_every_document_extension(filename, title):
    # DOC_EXTS covers .pdf/.docx/.doc/.xlsx - each must land in `links`.
    item = _parse_inline(MULTI_EXT_DOCS)
    assert {"href": f"{DOCS_BASE}/{filename}", "title": title} in item["links"]


def test_non_document_links_excluded_from_links_and_kept_in_description():
    item = _parse_inline(MULTI_EXT_DOCS)
    assert all(
        not link["href"].endswith("vimeo.com/1041176055/a02878935a")
        for link in item["links"]
    )
    assert "Video: https://vimeo.com/1041176055/a02878935a" in item["description"]


def test_description_includes_organization_and_session_type():
    assert "Organization: SEPTA Board" in board_item["description"]
    assert "Session Type: Open to the public" in board_item["description"]


def test_description_includes_meeting_details_link():
    assert f"Meeting Details: {DETAIL_URL}" in board_item["description"]


def test_description_includes_online_attendance_instructions():
    # The Webex registration link and the "register by 9 am" note from
    # <div class="meeting-instructions"> must survive into the description.
    assert (
        "Registration Link: https://septaorg.webex.com/weblink/register/"
        "r580ac69c9ebaebb10c32ab1fe5948a06" in board_item["description"]
    )
    assert "Register online by 9 am" in board_item["description"]


def test_description_skips_expired_webex_links():
    # On the May board page the Webex links are rendered as <span
    # class="expired">, not <a>, so nothing from that block is emitted.
    assert "webex.com" not in docs_item["description"]
    assert "expired" not in docs_item["description"].lower()


def test_description_video_link_included():
    assert "Video: https://vimeo.com/1198073899/f79ee7f4e6" in docs_item["description"]


def test_links_deduplicated_by_href():
    item = _parse_inline(DUP_HREF_DOCS)
    # The video link appears twice in the markup under different text; only
    # the first survives, and only once in the description.
    assert item["description"].count(DUP_VIDEO_URL) == 1
    assert f"Meeting Link: {DUP_VIDEO_URL}" in item["description"]
    assert item["links"] == [
        {"href": f"{DOCS_BASE}/notice.pdf", "title": "Meeting Notice (PDF)"}
    ]


def test_link_title_collapses_doubled_pdf_suffix():
    item = _parse_inline(DOUBLED_SUFFIX_DOCS)
    titles = [link["title"] for link in item["links"]]
    assert "Notice of Public Hearing (Spanish/Español) (PDF)" in titles
    assert not any(t.endswith("(PDF) (PDF)") for t in titles)


def test_archive_cutoff_filters_old_meetings():
    # Page 11 of the archive spans both sides of the 3-year cutoff
    # (2023-08-14, relative to the frozen "today"); only the 15 meetings at
    # or after the cutoff become detail requests.
    detail_requests = [r for r in archive_requests if "/page/" not in r.url]
    assert len(detail_requests) == 15
    assert all(
        req.cb_kwargs["listing_start"] >= datetime(2023, 8, 14)
        for req in detail_requests
    )


def test_archive_cutoff_stops_pagination():
    assert not any("/page/" in req.url for req in archive_requests)


def test_archive_item_end_to_end():
    # Built from the real archive listing (not hand-made kwargs). The
    # listing text is "... (canceled) (remote)": only the cancellation tag
    # is stripped, and the meeting is genuinely cancelled, so status must
    # say so rather than falling back to "passed" on age alone.
    assert archive_item["title"] == "SEPTA Board Regular Meeting (remote)"
    assert archive_item["start"] == datetime(2023, 8, 24, 15, 0)
    assert archive_item["classification"] == BOARD
    assert archive_item["location"] == {"name": "", "address": ""}
    assert archive_item["status"] == "cancelled"
