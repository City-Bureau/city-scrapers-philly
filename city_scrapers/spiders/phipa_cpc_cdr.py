from city_scrapers.mixins.phipa_cpc_cdr import PhipaCpcCdrSpiderMixin

spider_configs = [
    {
        "class_name": "PhipaCpcSpider",
        "name": "phipa_cpc",
        "agency": "Philadelphia City Planning Commission",
        "agency_name": "Philadelphia City Planning Commission and Civic Design Review Committee",  # noqa
    },
    {
        "class_name": "PhipaCdrSpider",
        "name": "phipa_cdr",
        "agency": "Civic Design Review Committee",
        "agency_name": "Philadelphia City Planning Commission and Civic Design Review Committee",  # noqa
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
            attrs = {k: v for k, v in config.items() if k != "class_name"}

            spider_class = type(
                class_name,
                (PhipaCpcCdrSpiderMixin,),
                attrs,
            )

            globals()[class_name] = spider_class


create_spiders()
