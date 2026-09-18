import threading
import time
from pathlib import Path

import schedule

import db
import scraper
import telegram_logic

CHECK_INTERVAL_MINUTES = 10
FETCH_DELAY_SECONDS = 5
LAST_CHECK_FILE = Path(__file__).with_name("last_check.txt")


def check_flats() -> None:
    _mark_checked()

    checked = 0
    alerts_sent = 0

    for index, (platform, url) in enumerate(scraper.SEARCHES):
        if index:
            time.sleep(FETCH_DELAY_SECONDS)

        flats = scraper.fetch_flats(platform, url)
        checked += len(flats)

        for flat in flats:
            listing_id = flat["id"]
            if db.is_seen(platform, listing_id):
                continue

            if telegram_logic.send_alert(flat):
                db.save_listing(platform, listing_id)
                alerts_sent += 1

    print(f"[main] checked {checked} flats, sent {alerts_sent} alerts")


def main() -> None:
    db.init_db()
    threading.Thread(target=telegram_logic.start_listener, daemon=True).start()

    if _seconds_since_last_check() >= CHECK_INTERVAL_MINUTES * 60:
        check_flats()
    else:
        print("[main] recent check found, waiting for the next scheduled run")

    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_flats)

    while True:
        schedule.run_pending()
        time.sleep(1)


def _seconds_since_last_check() -> float:
    try:
        last_check = float(LAST_CHECK_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return float("inf")
    return time.time() - last_check


def _mark_checked() -> None:
    LAST_CHECK_FILE.write_text(str(time.time()), encoding="utf-8")


if __name__ == "__main__":
    main()
