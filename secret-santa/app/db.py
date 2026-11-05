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


def init() -> None:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)


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
