# Vuokraovi Scraper

Automated weekly scraper that collects rental apartment vacancy counts from [vuokraovi.com](https://www.vuokraovi.com) and appends results to a Google Sheet for use in Power BI reporting.

## What it does

Every Monday at 6:00 AM Helsinki time (03:00 UTC), GitHub Actions runs `scrape_vuokraovi.py` which:
1. Visits 48 predefined search URLs on vuokraovi.com
2. Extracts the apartment count from the `#searchResultCount` element on each page
3. Appends a row per URL to a Google Sheet with columns: `QueryDate`, `URL`, `Vacancy`
4. If data has already been pulled from Vuokraovi, e.g. with a manual trigger, the script will not copy duplicates for the same day.

## URL structure

The 48 URLs represent combinations of:
- **Cities**: Helsinki, Espoo, Vantaa
- **Apartment sizes**: 1, 2, 3, 4+ rooms
- **Listing type**: Kaikki (all), Heti vapaa (immediately available), Asumisoikeus
- **Building type**: Kerrostalo (apartment block)

Each URL corresponds to a saved search on vuokraovi.com identified by a `haku=` parameter.

## Files

- `scrape_vuokraovi.py` — main Python scraper script
- `.github/workflows/scrape.yml` — GitHub Actions schedule (runs every Monday 07:00 UTC)

## Google Sheet

Results are written to a Google Sheet named **Vuokraovi_Github**. The first tab (Scraped_Data) receives new rows each week. The sheet also contains a mapping table linking each URL to its metadata (Kaupunki, Huoneita, Talotyyppi, Tila, Asumismuoto).

## Power BI

The Google Sheet is connected to a Power BI Desktop report. The scraped data is merged with the mapping table on the URL column to produce a full dataset with all metadata. The Power BI report is set to automatically refresh data at 8 AM on Mondays.

## Setup (for new environments)

### Requirements
- Python 3.11+
- Libraries: `requests`, `beautifulsoup4`, `gspread`, `google-auth`

### Google Sheets access
1. Create a Google Cloud project
2. Enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** and download the JSON credentials file
4. Share the Google Sheet with the service account email as Editor

### GitHub Actions secret
Add a repository secret named `GOOGLE_CREDENTIALS` containing the full contents of the service account JSON credentials file.

### Changing the schedule
Edit the cron expression in `.github/workflows/scrape.yml`:
```yaml
- cron: "0 7 * * 1"  # Every Monday at 07:00 UTC (09:00 Helsinki time)
```

### Adding or changing URLs

**Step 1: Find the URL**
1. Go to [vuokraovi.com](https://www.vuokraovi.com)
2. Use the search filters to set your desired criteria (city, number of rooms, building type, availability, etc.)
3. Once the search results load, copy the full URL from the browser address bar — it will contain a `haku=` parameter like `?haku=m2369410862`

**Step 2: Add to the scraper**
1. Open `scrape_vuokraovi.py` in GitHub (click the file → pencil icon to edit)
2. Find the `URLS` list and add your new URL as a new line following the same format:
```python
"https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=mXXXXXXXXX",
```
3. Make sure it has quotes around it, ends with a comma, and is inside the list brackets
4. Commit the changes

**Step 3: Add to the mapping table**
Add a new row to the mapping table in the Google Sheet (Vuokraovi_Github) with the URL and its corresponding metadata: Kaupunki, Huoneita, Talotyyppi, Tila, Asumismuoto. This ensures the new URL gets the correct labels in Power BI.

## Troubleshooting

- **SpreadsheetNotFound error** — check that the sheet name in `scrape_vuokraovi.py` matches exactly, and that the service account email has Editor access to the sheet
- **No data / None values** — vuokraovi.com may have changed the `#searchResultCount` element ID; inspect the page to verify
- **Workflow not triggering** — GitHub Actions scheduled workflows can occasionally be delayed by up to 1 hour
