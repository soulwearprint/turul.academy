"""SQLite storage. One file, no server needed."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    id          INTEGER PRIMARY KEY,
    slot        INTEGER NOT NULL UNIQUE CHECK (slot BETWEEN 1 AND 5),
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    key_salt    TEXT NOT NULL,
    wrapped_key TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    archived   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS years (
    year          INTEGER PRIMARY KEY,
    budget        TEXT NOT NULL DEFAULT '',
    exchange_date TEXT NOT NULL DEFAULT '',
    note          TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS year_participants (
    year      INTEGER NOT NULL REFERENCES years(year) ON DELETE CASCADE,
    member_id INTEGER NOT NULL REFERENCES members(id),
    PRIMARY KEY (year, member_id)
);

-- receiver is AES-GCM encrypted with the master key (see crypto.py)
CREATE TABLE IF NOT EXISTS pairings (
    year            INTEGER NOT NULL REFERENCES years(year) ON DELETE CASCADE,
    giver_id        INTEGER NOT NULL REFERENCES members(id),
    receiver_sealed TEXT NOT NULL,
    assigned_at     TEXT NOT NULL,
    notified_at     TEXT,
    notify_count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (year, giver_id)
);

-- symmetric "never draw each other" rule, e.g. couples (a_id < b_id)
CREATE TABLE IF NOT EXISTS exclusions (
    a_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    b_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    PRIMARY KEY (a_id, b_id),
    CHECK (a_id < b_id)
);

-- personal page links (token itself is never stored). receiver_sealed = '' for a
-- pre-draw wish-list invitation; a postcard link replaces it (one link per person per year).
CREATE TABLE IF NOT EXISTS participant_links (
    link_id         TEXT PRIMARY KEY,
    year            INTEGER NOT NULL REFERENCES years(year) ON DELETE CASCADE,
    member_id       INTEGER NOT NULL REFERENCES members(id),
    receiver_sealed TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    UNIQUE (year, member_id)
);

-- optional gift ideas: JSON list of {"text": ..., "url": ...}
CREATE TABLE IF NOT EXISTS wishes (
    year       INTEGER NOT NULL REFERENCES years(year) ON DELETE CASCADE,
    member_id  INTEGER NOT NULL REFERENCES members(id),
    items      TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (year, member_id)
);

-- "this giver has wish-list news": giver id sealed with the server key
CREATE TABLE IF NOT EXISTS digest_queue (
    year         INTEGER NOT NULL REFERENCES years(year) ON DELETE CASCADE,
    receiver_id  INTEGER NOT NULL REFERENCES members(id),
    giver_sealed TEXT NOT NULL,
    queued_at    TEXT NOT NULL,
    PRIMARY KEY (year, receiver_id)
);

-- pairs set by an admin before the random draw (e.g. Grandma -> little Peti)
CREATE TABLE IF NOT EXISTS fixed_pairs (
    year        INTEGER NOT NULL REFERENCES years(year) ON DELETE CASCADE,
    giver_id    INTEGER NOT NULL REFERENCES members(id),
    receiver_id INTEGER NOT NULL REFERENCES members(id),
    PRIMARY KEY (year, giver_id),
    UNIQUE (year, receiver_id),
    CHECK (giver_id != receiver_id)
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY,
    at         TEXT NOT NULL,
    admin_name TEXT NOT NULL,
    action     TEXT NOT NULL,
    detail     TEXT NOT NULL DEFAULT ''
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_path() -> Path:
    return Path(os.environ.get("SANTA_DB", Path(__file__).resolve().parent.parent / "data" / "santa.db"))


# Columns added after the first version: (table, column, definition).
# key_salt = '' on an admin means "no password, Google sign-in only".
MIGRATIONS = [
    ("admins", "google_email", "TEXT"),
    ("members", "lang", "TEXT NOT NULL DEFAULT 'hu'"),
    ("years", "avoid_repeat", "INTEGER NOT NULL DEFAULT 1"),
    # per-link key pair + this person's giver sealed to it (for "new gift idea" e-mails)
    ("participant_links", "public_key", "TEXT"),
    ("participant_links", "private_sealed", "TEXT"),
    ("participant_links", "giver_route", "TEXT"),
    ("wishes", "notified_texts", "TEXT NOT NULL DEFAULT '[]'"),
    # people without e-mail (small children, elderly): mail goes to this helper member
    ("members", "helper_id", "INTEGER REFERENCES members(id)"),
]


def init() -> None:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        for table, col, definition in MIGRATIONS:
            cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS admins_google_email ON admins (google_email COLLATE NOCASE)")


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                 (key, value))


@contextmanager
def connect():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def audit(conn: sqlite3.Connection, admin_name: str, action: str, detail: str = "") -> None:
    conn.execute(
        "INSERT INTO audit_log (at, admin_name, action, detail) VALUES (?, ?, ?, ?)",
        (now(), admin_name, action, detail),
    )
