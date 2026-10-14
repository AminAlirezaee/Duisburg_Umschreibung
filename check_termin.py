"""
Duisburg Fahrerlaubnis-Termin Checker
Prueft die eTermin-API und schickt eine Telegram-Nachricht, wenn Termine frei sind.
Nur Standardbibliothek, keine Installation noetig.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

WEBID = "qterminstadtduisburgstva"
SERVICE_ID = "110023"  # Umschreibung auslaendische Drittstaats-Fahrerlaubnis (Nicht-EU)
BOOKING_URL = "https://www.etermin.net/qterminstadtduisburgstva"


def fetch_slots(date_str):
    params = {
        "date": date_str,
        "serviceid": SERVICE_ID,
        "rangesearch": "1",
        "caching": "false",
        "capacity": "1",
        "duration": "0",
        "cluster": "false",
        "slottype": "0",
        "fillcalendarstrategy": "0",
        "showavcap": "false",
        "appfuture": "14",
        "appdeadline": "15",
        "appdeadlinewm": "0",
        "oneoff": "null",
        "msdcm": "0",
        "calendarid": "",
    }
    url = "https://www.etermin.net/api/timeslots?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "accept": "application/json, text/plain",
            "content-type": "application/json",
            "referer": BOOKING_URL,
            "webid": WEBID,
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
            ),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("WARNUNG: TELEGRAM_TOKEN oder TELEGRAM_CHAT_ID fehlt, keine Nachricht gesendet.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30) as r:
        print("Telegram-Antwort:", r.status)


def has_slots(body):
    """Leere Antwort ([] / {} / null) = keine Termine. Alles andere = Termine."""
    data = json.loads(body)
    return bool(data)


def main():
    test_mode = "--test" in sys.argv
    today = datetime.now(ZoneInfo("Europe/Berlin")).date()
    dates = [today, today + timedelta(days=14)]

    found = False
    for d in dates:
        body = fetch_slots(d.isoformat())
        print(f"[{d}] Antwort (erste 300 Zeichen): {body[:300]!r}")
        if has_slots(body):
            found = True

    if found:
        send_telegram(f"Termin frei! Schnell buchen:\n{BOOKING_URL}")
        print("TERMINE GEFUNDEN - Nachricht gesendet.")
    else:
        print("Keine Termine frei.")

    if test_mode:
        send_telegram("Testnachricht: Der Termin-Checker funktioniert.")


if __name__ == "__main__":
    main()
