import threading
import time

import schedule

import db
import scraper
import telegram_logic

CHECK_INTERVAL_MINUTES = 10


def check_flats() -> None:
    checked = 0
    alerts_sent = 0

    for platform, url in scraper.SEARCHES:
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
    check_flats()

    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_flats)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
