"""
Duisburg Fahrerlaubnis-Termin Checker
Prueft ALLE Tage der naechsten Wochen und schickt eine Telegram-Nachricht,
wenn irgendwo ein Termin frei ist. Nur Standardbibliothek.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

WEBID = "qterminstadtduisburgstva"
SERVICE_ID = "110023"  # Umschreibung auslaendische Drittstaats-Fahrerlaubnis (Nicht-EU)
BOOKING_URL = "https://www.etermin.net/qterminstadtduisburgstva"
DAYS_TO_SCAN = 21  # Die Stadt gibt nur ~14 Tage frei; 21 = Sicherheitsreserve


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
    return bool(json.loads(body))


def main():
    test_mode = "--test" in sys.argv
    today = datetime.now(ZoneInfo("Europe/Berlin")).date()

    found_dates = set()
    sample = None
    errors = 0

    for i in range(DAYS_TO_SCAN):
        d = today + timedelta(days=i)
        try:
            body = fetch_slots(d.isoformat())
            slots = has_slots(body)
        except Exception as e:
            errors += 1
            print(f"[{d}] FEHLER: {e}")
            continue

        if slots:
            print(f"[{d}] TERMINE! Antwort (erste 300 Zeichen): {body[:300]!r}")
            found_dates |= set(re.findall(r"\d{4}-\d{2}-\d{2}", body))
            if sample is None:
                sample = body
        else:
            print(f"[{d}] leer")
        time.sleep(0.5)  # freundlich zum Server

    if errors == DAYS_TO_SCAN:
        print("Alle Anfragen sind fehlgeschlagen.")
        sys.exit(1)

    if sample is not None:
        msg = "Termin frei! Schnell buchen:\n" + BOOKING_URL
        if found_dates:
            msg += "\n\nFreie Tage:\n" + "\n".join(sorted(found_dates))
        else:
            msg += "\n\nAntwort der Seite (Auszug):\n" + sample[:500]
        send_telegram(msg)
        print("TERMINE GEFUNDEN - Nachricht gesendet.")
    else:
        print(f"Keine Termine frei ({DAYS_TO_SCAN} Tage geprueft).")

    if test_mode:
        send_telegram("Testnachricht: Der Termin-Checker funktioniert.")


if __name__ == "__main__":
    main()
