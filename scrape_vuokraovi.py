import requests
from bs4 import BeautifulSoup
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import time

# --- CONFIG ---
SHEET_NAME = "Vuokraovi Data"  # Change to your Google Sheet name
CREDS_FILE = "credentials.json"  # Google service account credentials

URLS = [
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2369410862",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2369410781",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2369410692",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2369410550",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2369409887",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2369409516",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2369410032",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2369410232",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2369411385",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2369411482",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2369411562",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2369411676",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2380408729",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2380487133",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2380487724",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2380487902",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2380488061",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2380488134",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2380488251",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2380488385",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2380488525",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2380488617",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2380488692",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2380488799",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2380489949",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2380490060",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2380490145",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2380490213",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2380490596",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2380490664",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2380490757",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2380490829",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2380490952",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2380491012",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2380491106",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2380491199",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2395886022",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2395886403",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2395886577",
    "https://www.vuokraovi.com/vuokra-asunnot/helsinki?haku=m2395886750",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2395886917",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2395887087",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2395887592",
    "https://www.vuokraovi.com/vuokra-asunnot/espoo?haku=m2395889130",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2395889360",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2395889464",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2395889614",
    "https://www.vuokraovi.com/vuokra-asunnot/vantaa?haku=m2395889757",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def scrape_count(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.find(id="searchResultCount")
        if element:
            # Remove spaces (Finnish number formatting uses spaces as thousands separator)
            return element.text.strip().replace("\xa0", "").replace(" ", "")
        return None
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # In GitHub Actions, credentials are stored as a secret and written to a file
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet


def main():
    today = date.today().strftime("%d.%m.%Y")
    print(f"Running scrape for {today}")

    sheet = get_sheet()

    # Add header row if sheet is empty
    if sheet.row_count == 0 or sheet.cell(1, 1).value is None:
        sheet.append_row(["QueryDate", "URL", "Vacancy"])

    rows = []
    for url in URLS:
        count = scrape_count(url)
        print(f"{url} -> {count}")
        rows.append([today, url, count])
        time.sleep(1)  # Be polite, don't hammer the server

    sheet.append_rows(rows)
    print(f"Done! Appended {len(rows)} rows.")


if __name__ == "__main__":
    main()
