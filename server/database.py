"""
Smart Classroom — SQLite Database
Zero-dependency (uses Python built-in sqlite3).
"""

import sqlite3
import os
from contextlib import contextmanager

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "smartclassroom.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    roll       TEXT NOT NULL UNIQUE,
    folder     TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT PRIMARY KEY,
    date          TEXT NOT NULL,
    start_time    TEXT,
    end_time      TEXT,
    duration_min  INTEGER NOT NULL,
    window_min    INTEGER NOT NULL,
    status        TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS attendance (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    student_id  TEXT NOT NULL REFERENCES students(id),
    entry_time  TEXT,
    status      TEXT NOT NULL DEFAULT 'absent',
    updated_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(session_id, student_id)
);

CREATE TABLE IF NOT EXISTS analytics (
    id            TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL REFERENCES sessions(id),
    student_id    TEXT NOT NULL REFERENCES students(id),
    attention_pct INTEGER DEFAULT 0,
    phone_count   INTEGER DEFAULT 0,
    updated_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(session_id, student_id)
);

CREATE TABLE IF NOT EXISTS iot_log (
    id         TEXT PRIMARY KEY,
    timestamp  TEXT DEFAULT (datetime('now')),
    device     TEXT NOT NULL,
    state      TEXT NOT NULL,
    trigger    TEXT NOT NULL
);
"""


def init_db():
    """Create database directory and tables."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


@contextmanager
def get_db():
    """Context manager that yields a sqlite3 connection with row_factory."""
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
