"""
SQLite database helpers.
Uses Python's built-in sqlite3 — no extra package needed.
"""

import sqlite3
from contextlib import contextmanager
from flask import Flask, current_app, g


# ── Connection helper ──────────────────────────────────────────────────────────

def get_db():
    """Return a per-request SQLite connection (stored in Flask's g)."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row  # rows behave like dicts
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def get_db_connection(db_path: str):
    """Standalone context manager (used outside request context, e.g. scripts)."""
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ─────────────────────────────────────────────────────────────────────

SCHEMA = """
-- Students table: registered students with face data
CREATE TABLE IF NOT EXISTS students (
    id        TEXT PRIMARY KEY,          -- UUID
    name      TEXT NOT NULL,
    roll      TEXT NOT NULL UNIQUE,
    image_path TEXT,                     -- relative path inside data/students/
    created_at TEXT DEFAULT (datetime('now'))
);

-- Sessions table: each class session
CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT PRIMARY KEY,
    date          TEXT NOT NULL,         -- ISO 8601 date (YYYY-MM-DD)
    start_time    TEXT,
    end_time      TEXT,
    duration_min  INTEGER NOT NULL,      -- configured class duration
    window_min    INTEGER NOT NULL,      -- attendance window
    status        TEXT DEFAULT 'active'  -- 'active' | 'ended'
);

-- Attendance table: per-student, per-session record
CREATE TABLE IF NOT EXISTS attendance (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    student_id  TEXT NOT NULL REFERENCES students(id),
    entry_time  TEXT,                    -- HH:MM when detected
    status      TEXT NOT NULL,           -- 'present' | 'late' | 'absent'
    updated_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(session_id, student_id)
);

-- Analytics table: attention + phone events per student per session
CREATE TABLE IF NOT EXISTS analytics (
    id            TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL REFERENCES sessions(id),
    student_id    TEXT NOT NULL REFERENCES students(id),
    attention_pct INTEGER DEFAULT 0,     -- 0-100
    phone_count   INTEGER DEFAULT 0,     -- number of phone-detected events
    updated_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(session_id, student_id)
);

-- IoT log: device state changes
CREATE TABLE IF NOT EXISTS iot_log (
    id         TEXT PRIMARY KEY,
    timestamp  TEXT DEFAULT (datetime('now')),
    device     TEXT NOT NULL,            -- 'lights' | 'fans'
    state      TEXT NOT NULL,            -- 'ON' | 'OFF'
    trigger    TEXT NOT NULL             -- 'auto' | 'manual'
);
"""


def init_db(app: Flask):
    """Create all tables and register teardown."""
    app.teardown_appcontext(close_db)

    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE_PATH"])
        db.executescript(SCHEMA)
        db.commit()
        db.close()
