from datetime import datetime
from os.path import dirname, join

from city_scrapers_core.constants import ADVISORY_COMMITTEE, BOARD, COMMITTEE
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.phipa_septa import PhipaSeptaSpider

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
bare_cfemail_detail_response = file_response(
    join(dirname(__file__), "files", "phipa_septa_detail_bare_cfemail.html"),
    url=BARE_CFEMAIL_URL,
)
DUP_LINK_URL = "https://wwww.septa.org/about/meetings/septa-board-regular-meeting-98/"
dup_link_detail_response = file_response(
    join(dirname(__file__), "files", "phipa_septa_detail_dup_link.html"),
    url=DUP_LINK_URL,
)
DUP_PDF_SUFFIX_URL = (
    "https://wwww.septa.org/about/meetings/service-plan-public-hearing-2/"
)
dup_pdf_suffix_detail_response = file_response(
    join(dirname(__file__), "files", "phipa_septa_detail_dup_pdf_suffix.html"),
    url=DUP_PDF_SUFFIX_URL,
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
        source=CAPITALIZED_URL,
    )
)

archive_requests = [req for req in spider.parse(archive_response)]

bare_cfemail_item = next(
    spider._parse_detail(
        bare_cfemail_detail_response,
        title="CAC Plenary Meeting",
        listing_start=datetime(2025, 10, 28, 17, 30),
        cancelled=False,
        source=BARE_CFEMAIL_URL,
    )
)

dup_link_item = next(
    spider._parse_detail(
        dup_link_detail_response,
        title="SEPTA Board Regular Meeting",
        listing_start=datetime(2023, 10, 26, 19, 0),
        cancelled=False,
        source=DUP_LINK_URL,
    )
)

dup_pdf_suffix_item = next(
    spider._parse_detail(
        dup_pdf_suffix_detail_response,
        title="SEPTA Annual Service Plan Public Hearing",
        listing_start=datetime(2026, 4, 15, 18, 0),
        cancelled=False,
        source=DUP_PDF_SUFFIX_URL,
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


def test_id():
    assert board_item["id"] == "phipa_septa/202609241500/x/septa_board_regular_meeting"


def test_status_cancelled():
    assert cancelled_request.cb_kwargs["cancelled"] is True
    assert cancelled_request.cb_kwargs["title"] == (
        "Administration & Operations Committees Meeting"
    )


def test_listing_text_multiple_status_tags():
    # SEPTA sometimes appends more than one trailing tag, e.g.
    # "Meeting Name (canceled) (remote)". Both must be stripped from the
    # title, and "canceled" must be detected no matter which position it's
    # in among them.
    title, start, cancelled = spider._parse_listing_text(
        " May 27, 2025, at 9:30 pm: CAC Plenary Meeting (canceled) (remote)"
    )
    assert title == "CAC Plenary Meeting"
    assert cancelled is True
    assert start == datetime(2025, 5, 27, 21, 30)


def test_status():
    assert board_item["status"] == "tentative"


def test_location():
    assert board_item["location"] == {
        "name": "SEPTA Board Room",
        "address": "1234 Market Street, Mezzanine Level, Philadelphia, PA 19107",
    }


def test_location_virtual():
    assert virtual_item["location"] == {"name": "Online via Teams", "address": ""}


def test_source():
    assert (
        board_item["source"]
        == "https://wwww.septa.org/about/meetings/septa-board-meeting-september-2026/"
    )


def test_links():
    assert board_item["links"] == [
        {
            "href": "https://wwww.septa.org/about/meetings/septa-board-meeting-september-2026/",  # noqa
            "title": "Meeting Details",
        }
    ]


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


def test_description():
    assert board_item["description"] == (
        "Organization: SEPTA Board\n"
        "Session Type: Open to the public\n"
        "Virtual: Webex"
    )


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
    assert board_item["time_notes"] == ""
    assert virtual_item["time_notes"] == (
        "Meetings are typically held on the first Tuesday of the month from "
        "5:30 pm to 7 pm online via Teams."
    )


def test_location_mixed_in_person_and_virtual():
    # CAC Plenary meetings use "In-person:"/"Online:" instead of the usual
    # "In person:"/"Virtual:", and only give a street/room, not a venue name.
    assert mixed_item["location"] == {
        "name": "1234 Market Street, Room 10A",
        "address": "",
    }


def test_description_keeps_in_person_registration_instructions():
    # The registration instructions that `_parse_location` strips out of
    # the venue name must still show up somewhere - here, in description -
    # rather than being silently dropped.
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


def test_location_in_person_capitalized_label():
    # SEPTA also spells this "In Person:" (capital P) on some older pages;
    # it must still be recognized as the same in-person label.
    assert capitalized_item["location"] == {
        "name": "SEPTA Board Room",
        "address": "1234 Market Street, Mezzanine Level, Philadelphia, PA 19107",
    }


def test_links_include_registration_video_and_documents():
    # Some detail pages - mostly archived ones - also publish a
    # registration link, a meeting video, and documents (notice, agenda,
    # minutes, transcript); all of it belongs in `links` alongside the
    # "Meeting Details" self-link, not just the page itself.
    assert capitalized_item["links"] == [
        {"href": CAPITALIZED_URL, "title": "Meeting Details"},
        {
            "href": "https://septaorg.webex.com/weblink/register/r78076d52130ab033e85c881befd37e7e",  # noqa
            "title": "Meeting Registration Link",
        },
        {
            "href": "https://vimeo.com/1041176055/a02878935a?share=copy",
            "title": "Meeting Video Link",
        },
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
    assert archive_item["title"] == "SEPTA Board Regular Meeting"
    assert archive_item["start"] == datetime(2023, 8, 24, 15, 0)
    assert archive_item["classification"] == BOARD
    assert archive_item["location"] == {"name": "Online via WebEx", "address": ""}
    # The real listing text for this one is "... (canceled) (remote)" - two
    # trailing status tags. It was genuinely cancelled, so status must say
    # so rather than falling back to "passed" just because the date is old.
    assert archive_item["status"] == "cancelled"


def test_links_deduplicated_by_href():
    # This page genuinely lists the same Vimeo link twice - once
    # (mislabeled) under "Register and Attend", again under "Links" - so
    # only the first occurrence should survive.
    hrefs = [link["href"] for link in dup_link_item["links"]]
    assert len(hrefs) == len(set(hrefs))
    assert "https://vimeo.com/880978025/9a476c7727?share=copy" in hrefs
    titles = [link["title"] for link in dup_link_item["links"]]
    assert "Meeting Link" in titles
    assert "Meeting Video Link" not in titles


def test_link_titles_collapse_duplicated_pdf_suffix():
    # SEPTA's own anchor text for these documents literally reads
    # "... (PDF) (PDF)"; collapse the doubled suffix down to one.
    titles = [link["title"] for link in dup_pdf_suffix_item["links"]]
    assert "Notice of Public Hearing (Spanish/Español) (PDF)" in titles
    assert not any(t.endswith("(PDF) (PDF)") for t in titles)
