# City Scrapers Philly

[![CI build status](https://github.com/City-Bureau/city-scrapers-philly/workflows/CI/badge.svg)](https://github.com/City-Bureau/city-scrapers-template/actions?query=workflow%3ACI)
[![Cron build status](https://github.com/City-Bureau/city-scrapers-philly/workflows/Cron/badge.svg)](https://github.com/City-Bureau/city-scrapers-template/actions?query=workflow%3ACron)

Repo for the [City Scrapers](https://cityscrapers.org) project in Philadelphia, Pennsylvania.

See the [development documentation](https://cityscrapers.org/docs/development/) for info how to get started.

## Notes

Please note that to run the `phipa_boe` spider locally, you will need to do the following:

1) Get the `GOOGLE_CLOUD_API_KEY` from the City Bureau secrets manager or a City Bureau technology coordinator.
2) Create a `.env.development` file in the project root:
```
cp .env.development.example .env.development
```
3) Add the key to the file. Replace "<API-VALUE>" with the API key.
```
GOOGLE_CLOUD_API_KEY=<API-VALUE>
```
