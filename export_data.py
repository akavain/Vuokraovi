"""Export the Scraped_Data sheet to data.csv for the GitHub Pages dashboard.

Runs in GitHub Actions after the scraper. Reads the whole first tab of the
Google Sheet, normalizes dates to YYYY-MM-DD and values to integers, drops
duplicates and unparseable rows, and writes data.csv sorted by date.
"""
import csv
import json
import os
import re

SHEET_NAME = "Vuokraovi_Github"
CREDS_FILE = "credentials.json"
OUT_FILE = "data.csv"


def get_rows():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
    else:
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=scopes)
    sheet = gspread.authorize(creds).open(SHEET_NAME).sheet1
    return sheet.get_all_values()[1:]  # skip header


def to_iso(d):
    """'1.11.2026' / '01.11.2026' -> '2026-11-01'; returns None if unparseable."""
    m = re.fullmatch(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s*", str(d))
    if not m:
        return None
    day, month, year = m.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def to_int(v):
    s = str(v).replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return int(round(float(s)))
    except ValueError:
        return None


def clean(rows):
    out = {}
    skipped = 0
    for r in rows:
        if len(r) < 3:
            skipped += 1
            continue
        date, url, val = to_iso(r[0]), str(r[1]).strip(), to_int(r[2])
        if not date or not url.startswith("http") or val is None:
            skipped += 1
            continue
        out[(date, url)] = val  # later rows win on duplicates
    return sorted(out.items()), skipped


def write_csv(items, path=OUT_FILE):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "url", "vacancy"])
        for (date, url), val in items:
            w.writerow([date, url, val])


def main():
    items, skipped = clean(get_rows())
    write_csv(items)
    dates = sorted({d for (d, _), _ in items})
    print(f"Wrote {len(items)} rows, {len(dates)} dates ({dates[0]} .. {dates[-1]}), skipped {skipped}")


if __name__ == "__main__":
    main()
