"""
This file dynamically creates spider classes for the spider factory mixin
that agencies use.
"""

from urllib.parse import quote

from city_scrapers_core.constants import COMMISSION, COMMITTEE

from city_scrapers.mixins.phipa_cpc_cdr import PhipaCpcCdrSpiderMixin

spider_configs = [
    {
        "class_name": "PhipaCpcCdrSpider",
        "name": "phipa_cpc_cdr",
        "agency": "Philadelphia City Planning Commission and Civic Design Review Committee",  # noqa
        "category": "Philadelphia City Planning Commission",
        "calendar_id": "do6kgfl3sslqvfq0iumt9eogto@group.calendar.google.com",
        "documents_url": "https://www.phila.gov/departments/philadelphia-city-planning-commission/public-meetings/",  # noqa
        "recordings_url": "https://www.phila.gov/departments/philadelphia-city-planning-commission/recordings-of-public-meetings/",  # noqa
        "location": {
            "name": "One Parkway Building, Room 18-029",
            "address": "1515 Arch Street, 18th Floor, Philadelphia, PA 19102",
        },
        # Each heading_match value matches heading ids from a different page:
        # "pcpc"/"cdr" from documents_url, "planning-commission"/
        # "civic-design-review" from recordings_url.
        "bodies": [
            {
                "id": "pcpc",
                "classification": COMMISSION,
                "keyword": None,
                "heading_match": ["pcpc", "planning-commission"],
            },
            {
                "id": "cdr",
                "classification": COMMITTEE,
                "keyword": "civic design review",
                "heading_match": ["cdr", "civic-design-review"],
            },
        ],
    },
    {
        "class_name": "PhipaFairHousingCommissionSpider",
        "name": "phipa_fair_housing_commission",
        "agency": "Fair Housing Commission",
        "category": "Fair Housing Commission",
        "calendar_id": "phila.fairhousingcommission@gmail.com",
        "documents_url": "https://www.phila.gov/documents/fair-housing-commission-meeting-agendas/",  # noqa
        "recordings_url": None,
        "location": {
            "name": "",
            "address": "",
        },
        "no_description_text": (
            "Please visit https://www.phila.gov/departments/fair-housing-commission/ for more information about accessing our meetings."  # noqa
        ),
        "bodies": [
            {
                "id": "executive_session",
                "classification": COMMISSION,
                "keyword": "executive",
                "heading_match": [],
            },
            {
                "id": "public_hearing",
                "classification": COMMISSION,
                "keyword": None,
                "heading_match": [],
            },
        ],
    },
]


def create_spiders():
    """
    Dynamically create spider classes using the spider_configs list
    and register them in the global namespace.
    """
    for config in spider_configs:
        class_name = config["class_name"]

        if class_name not in globals():
            # Build attributes dict without class_name to avoid duplication.
            # We make sure that the class_name is not already in the global namespace
            # Because some scrapy CLI commands like `scrapy list` will inadvertently
            # declare the spider class more than once otherwise
            attrs = {k: v for k, v in config.items() if k != "class_name"}
            attrs["source_url"] = (
                "https://www.phila.gov/the-latest/all-events/"
                f"?category={quote(config['category'])}"
            )

            # Dynamically create the spider class
            spider_class = type(
                class_name,
                (PhipaCpcCdrSpiderMixin,),
                attrs,
            )

            globals()[class_name] = spider_class


# Create all spider classes at module load
create_spiders()
