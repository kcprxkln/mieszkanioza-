import sqlite3
from contextlib import closing

DB_PATH = "flats.db"


def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        _migrate_legacy_table(conn)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS seen_flats ("
            "platform TEXT NOT NULL, "
            "listing_id TEXT NOT NULL, "
            "PRIMARY KEY (platform, listing_id))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS subscribers (chat_id INTEGER PRIMARY KEY)"
        )
        conn.commit()


def is_seen(platform: str, listing_id: str) -> bool:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_flats WHERE platform = ? AND listing_id = ?",
            (platform, listing_id),
        ).fetchone()
    return row is not None


def save_listing(platform: str, listing_id: str) -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_flats (platform, listing_id) VALUES (?, ?)",
            (platform, listing_id),
        )
        conn.commit()


def add_subscriber(chat_id: int) -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)", (chat_id,)
        )
        conn.commit()


def get_subscribers() -> list[int]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        rows = conn.execute("SELECT chat_id FROM subscribers").fetchall()
    return [row[0] for row in rows]


def _migrate_legacy_table(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'seen_flats'"
    ).fetchone()
    if not exists:
        return

    columns = [row[1] for row in conn.execute("PRAGMA table_info(seen_flats)")]
    if "platform" in columns:
        return

    conn.execute("ALTER TABLE seen_flats RENAME TO seen_flats_legacy")
    conn.execute(
        "CREATE TABLE seen_flats ("
        "platform TEXT NOT NULL, "
        "listing_id TEXT NOT NULL, "
        "PRIMARY KEY (platform, listing_id))"
    )
    # legacy rows predate OLX support, so they are all Gratka
    conn.execute(
        "INSERT INTO seen_flats (platform, listing_id) "
        "SELECT 'Gratka', listing_id FROM seen_flats_legacy"
    )
    conn.execute("DROP TABLE seen_flats_legacy")
    print("[db] migrated seen_flats to composite (platform, listing_id) key")
