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
    shown = sheet.get_all_values()  # as displayed: keeps text dates like "13.4.2026"
    try:
        # raw numbers, so a cell formatted as "1 555,00" or "1,555.00" still reads as 1555
        raw = sheet.get_all_values(value_render_option="UNFORMATTED_VALUE")
    except Exception as e:  # older gspread: fall back to parsing the displayed text
        print(f"Unformatted read failed ({e}); parsing displayed values")
        raw = shown
    rows = []
    for i, r in enumerate(shown[1:], start=1):  # skip header
        val = raw[i][2] if i < len(raw) and len(raw[i]) > 2 else (r[2] if len(r) > 2 else "")
        rows.append([r[0] if r else "", r[1] if len(r) > 1 else "", val])
    return rows


def to_iso(d):
    """'1.11.2026' / '01.11.2026' -> '2026-11-01'; returns None if unparseable."""
    m = re.fullmatch(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s*", str(d))
    if not m:
        return None
    day, month, year = m.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def to_int(v):
    """Read a listing count whatever the cell format: 1555, 1555.0, "1 555,00", "1,555.00", "1.555,00"."""
    if isinstance(v, (int, float)):
        return int(round(v))
    s = str(v).strip().replace("\xa0", "").replace("\u202f", "").replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:  # both present: the last one is the decimal separator
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):  # "1.555" = thousands (counts are whole numbers)
        s = s.replace(".", "")
    try:
        return int(round(float(s)))
    except ValueError:
        return None


def clean(rows):
    out = {}
    skipped = []
    for r in rows:
        if len(r) < 3 or not any(str(x).strip() for x in r):
            continue  # empty line
        date, url, val = to_iso(r[0]), str(r[1]).strip(), to_int(r[2])
        if not date or not url.startswith("http") or val is None:
            skipped.append(r)
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
    print(f"Wrote {len(items)} rows, {len(dates)} dates ({dates[0]} .. {dates[-1]})")
    if skipped:
        print(f"WARNING: skipped {len(skipped)} unreadable rows, first ones: {skipped[:5]}")


if __name__ == "__main__":
    main()
