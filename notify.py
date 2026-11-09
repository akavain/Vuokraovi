"""Send the weekly "data updated" notification for the Vuokraovi dashboard.

Builds a short Finnish summary from data.csv + URL_Mapping.csv and POSTs it to the
Power Automate / Teams webhook in the NOTIFY_WEBHOOK_URL environment variable.
The payload carries both plain fields for an email (subject, html, text) and an
Adaptive Card (attachments) for a Teams post, so one flow can do either or both.

Usage:  python notify.py            # send
        python notify.py --dry-run  # print the payload, send nothing
"""
import csv
import json
import os
import sys
import urllib.request
from collections import defaultdict

DASHBOARD_URL = "https://akavain.github.io/Vuokraovi/"
CITIES = ["Helsinki", "Espoo", "Vantaa", "Turku", "Tampere"]
PKS = ["Helsinki", "Espoo", "Vantaa"]


def fi_num(v):
    return f"{v:,}".replace(",", " ")


def fi_signed(v):
    return ("+" if v > 0 else "−" if v < 0 else "±") + fi_num(abs(v))


def fi_date(iso):
    y, m, d = iso.split("-")
    return f"{int(d)}.{int(m)}.{y}"


def load():
    mapping = list(csv.DictReader(open("URL_Mapping.csv", encoding="utf-8")))
    by_date = defaultdict(dict)
    for r in csv.DictReader(open("data.csv", encoding="utf-8")):
        by_date[r["date"]][r["url"]] = int(r["vacancy"])
    return mapping, by_date, sorted(by_date)


def total(by_date, date, urls):
    row = by_date.get(date, {})
    if not urls or any(u not in row for u in urls):
        return None
    return sum(row[u] for u in urls)


def build():
    mapping, by_date, dates = load()
    last, prev = dates[-1], (dates[-2] if len(dates) > 1 else None)

    def urls(cities, tila="Kaikki", forms=("Vuokra",)):
        return [m["URL"] for m in mapping if m["Kaupunki"] in cities and m["Tila"] == tila and m["Asumismuoto"] in forms]

    def line(label, u):
        now = total(by_date, last, u)
        if now is None:
            return None
        before = total(by_date, prev, u) if prev else None
        chg = f"{fi_signed(now - before)} vs. {fi_date(prev)}" if before is not None else "ei vertailudataa"
        return label, fi_num(now), chg

    rows = [line("Pääkaupunkiseutu", urls(PKS))] + [line(c, urls([c])) for c in CITIES]
    rows.append(line("Asumisoikeus, kaikki kaupungit", urls(CITIES, forms=("Asumisoikeus",))))
    rows = [r for r in rows if r]

    subject = f"Vuokraovi-data päivitetty {fi_date(last)}"
    intro = f"Vuokraoven ilmoitusmäärät on päivitetty {fi_date(last)}. Luvut: kerrostalot, kaikki huoneluvut, vuokra-asunnot (Kaikki)."
    text = "\n".join([intro, ""] + [f"{a}: {b} ({c})" for a, b, c in rows] + ["", f"Dashboard: {DASHBOARD_URL}"])
    html_rows = "".join(
        f'<tr><td style="padding:3px 12px 3px 0">{a}</td><td style="padding:3px 12px;text-align:right"><b>{b}</b></td>'
        f'<td style="padding:3px 0;color:#6b766e">{c}</td></tr>' for a, b, c in rows)
    html = (f'<div style="font-family:Arial,sans-serif;font-size:14px">'
            f'<p>{intro}</p><table style="border-collapse:collapse">{html_rows}</table>'
            f'<p><a href="{DASHBOARD_URL}" style="color:#004722;font-weight:bold">Avaa dashboard</a></p></div>')
    card = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "type": "AdaptiveCard", "version": "1.4",
        "body": [{"type": "TextBlock", "text": subject, "weight": "Bolder", "size": "Medium", "wrap": True},
                 {"type": "TextBlock", "text": intro, "wrap": True, "isSubtle": True},
                 {"type": "FactSet", "facts": [{"title": a, "value": f"{b}  ({c})"} for a, b, c in rows]}],
        "actions": [{"type": "Action.OpenUrl", "title": "Avaa dashboard", "url": DASHBOARD_URL}],
    }
    return {"subject": subject, "html": html, "text": text, "date": last, "url": DASHBOARD_URL,
            "type": "message",
            "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "contentUrl": None, "content": card}]}


def main():
    payload = build()
    if "--dry-run" in sys.argv:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    url = os.environ.get("NOTIFY_WEBHOOK_URL")
    if not url:
        print("NOTIFY_WEBHOOK_URL not set; skipping notification")
        return
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"Notification sent for {payload['date']}: HTTP {r.status}")


if __name__ == "__main__":
    main()
