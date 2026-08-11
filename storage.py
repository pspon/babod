"""Local SQLite storage for the workout tracker.

Everything the app needs lives in a single SQLite file on disk (on the
Raspberry Pi this is a bind-mounted volume), so the app works offline and the
data never leaves the box.

Configuration (environment variables):
    BABOD_DB_PATH    Path to the SQLite file.  Default: ./data/babod.db
    BABOD_TIMEZONE   Timezone used for timestamps.  Default: US/Eastern
    BABOD_SEED_FILE  JSON template used to seed an empty database.
                     Default: ./seed/template.json
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytz

SCHEMA_VERSION = 1

DEFAULT_DB_PATH = "data/babod.db"
DEFAULT_SEED_FILE = "seed/template.json"
DEFAULT_TIMEZONE = "US/Eastern"

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def db_path():
    """Absolute path of the SQLite file backing the app."""
    path = os.getenv("BABOD_DB_PATH", DEFAULT_DB_PATH)
    return os.path.abspath(path)


def timezone():
    return pytz.timezone(os.getenv("BABOD_TIMEZONE", DEFAULT_TIMEZONE))


def now_local():
    return datetime.now(timezone())


def today_str():
    return now_local().strftime("%Y-%m-%d")


@contextmanager
def connect():
    """Yield a connection, committing on success and always closing."""
    path = db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        # WAL keeps reads fast while a write is in flight, and cuts down on the
        # fsync churn that wears out SD cards.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(seed_if_empty=True):
    """Create the schema if needed and seed a starter template on first run."""
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS exercises (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                day         TEXT    NOT NULL,
                name        TEXT    NOT NULL,
                sets        TEXT    NOT NULL DEFAULT '3',
                reps        TEXT    NOT NULL DEFAULT '10',
                weight      REAL    NOT NULL DEFAULT 0,
                description TEXT    NOT NULL DEFAULT '',
                position    INTEGER NOT NULL DEFAULT 0,
                UNIQUE (day, name)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL,
                day         TEXT    NOT NULL DEFAULT '',
                exercise    TEXT    NOT NULL,
                sets        TEXT    NOT NULL DEFAULT '',
                reps        TEXT    NOT NULL DEFAULT '',
                weight      REAL    NOT NULL DEFAULT 0,
                completed   INTEGER NOT NULL DEFAULT 1,
                description TEXT    NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_timestamp
                ON sessions (timestamp);
            CREATE INDEX IF NOT EXISTS idx_sessions_exercise
                ON sessions (exercise);
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        empty = conn.execute("SELECT COUNT(*) FROM exercises").fetchone()[0] == 0

    if empty and seed_if_empty:
        seed_from_file()


def seed_from_file(path=None):
    """Load a template from JSON into an empty database.

    The file is a list of ``{"day", "name", "sets", "reps", "weight",
    "description"}`` objects.  Missing file is not an error: the app just
    starts empty and exercises can be added from the Plan page.
    """
    path = path or os.getenv("BABOD_SEED_FILE", DEFAULT_SEED_FILE)
    if not os.path.exists(path):
        return 0

    with open(path, "r", encoding="utf-8") as handle:
        rows = json.load(handle)

    for position, row in enumerate(rows):
        upsert_exercise(
            day=row["day"],
            name=row["name"],
            sets=row.get("sets", "3"),
            reps=row.get("reps", "10"),
            weight=row.get("weight", 0),
            description=row.get("description", ""),
            position=row.get("position", position),
        )
    return len(rows)


def _to_float(value, default=0.0):
    """Weights come from spreadsheets and humans, so 'BW' and '' show up."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# Workout plan (templates)
# --------------------------------------------------------------------------


def list_days():
    """Day names in plan order, e.g. ['Day 1', 'Day 2', 'Day 3']."""
    with connect() as conn:
        # Ordered by insertion, so newly added days land at the end.
        rows = conn.execute(
            "SELECT day, MIN(id) AS first_id "
            "FROM exercises GROUP BY day ORDER BY first_id"
        ).fetchall()
    return [row["day"] for row in rows]


def get_workouts(day=None):
    """Exercises for one day, or the whole plan when ``day`` is None."""
    query = "SELECT * FROM exercises"
    params = ()
    if day is not None:
        query += " WHERE day = ?"
        params = (day,)
    query += " ORDER BY position, id"

    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_exercise_weights():
    """Current working weight per exercise name (across all days)."""
    with connect() as conn:
        rows = conn.execute("SELECT name, weight FROM exercises").fetchall()
    return {row["name"]: row["weight"] for row in rows}


def set_exercise_weight(name, weight):
    """Set the working weight for every occurrence of an exercise."""
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE exercises SET weight = ? WHERE name = ?",
            (_to_float(weight), name),
        )
    return cursor.rowcount


def upsert_exercise(day, name, sets="3", reps="10", weight=0,
                    description="", position=None):
    """Insert an exercise, or update it if that (day, name) already exists."""
    with connect() as conn:
        if position is None:
            position = conn.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM exercises WHERE day = ?",
                (day,),
            ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO exercises (day, name, sets, reps, weight, description, position)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (day, name) DO UPDATE SET
                sets        = excluded.sets,
                reps        = excluded.reps,
                weight      = excluded.weight,
                description = excluded.description,
                position    = excluded.position
            """,
            (day, str(name).strip(), str(sets), str(reps), _to_float(weight),
             description or "", position),
        )


def delete_exercise(day, name):
    with connect() as conn:
        conn.execute("DELETE FROM exercises WHERE day = ? AND name = ?", (day, name))


# --------------------------------------------------------------------------
# Logged sessions
# --------------------------------------------------------------------------


def log_workout(exercise, sets="", reps="", weight=0, description="", day="",
                timestamp=None):
    """Record a completed exercise."""
    timestamp = timestamp or now_local().strftime(TIMESTAMP_FORMAT)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO sessions
                (timestamp, day, exercise, sets, reps, weight, completed, description)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (timestamp, day or "", exercise, str(sets), str(reps),
             _to_float(weight), description or ""),
        )
    return cursor.lastrowid


def unlog_workout(exercise, on_date=None):
    """Remove an exercise logged on a given day — the fat-finger undo."""
    on_date = on_date or today_str()
    with connect() as conn:
        cursor = conn.execute(
            "DELETE FROM sessions WHERE exercise = ? AND timestamp LIKE ?",
            (exercise, f"{on_date}%"),
        )
    return cursor.rowcount


def completed_on(on_date=None):
    """Map of exercise name -> time of day it was logged (HH:MM)."""
    on_date = on_date or today_str()
    with connect() as conn:
        rows = conn.execute(
            "SELECT exercise, MAX(timestamp) AS timestamp FROM sessions "
            "WHERE timestamp LIKE ? GROUP BY exercise",
            (f"{on_date}%",),
        ).fetchall()
    return {row["exercise"]: row["timestamp"][11:16] for row in rows}


def recent_sessions(days=30, limit=1000):
    """Logged sessions from the last N days, newest first."""
    since = (now_local() - timedelta(days=days)).strftime("%Y-%m-%d")
    with connect() as conn:
        rows = conn.execute(
            "SELECT timestamp, day, exercise, sets, reps, weight, description "
            "FROM sessions WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
            (since, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def all_sessions():
    with connect() as conn:
        rows = conn.execute(
            "SELECT timestamp, day, exercise, sets, reps, weight, completed, description "
            "FROM sessions ORDER BY timestamp"
        ).fetchall()
    return [dict(row) for row in rows]


def streak_days(max_lookback=365):
    """Consecutive days (ending today or yesterday) with at least one log."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT substr(timestamp, 1, 10) AS day FROM sessions "
            "ORDER BY day DESC LIMIT ?",
            (max_lookback,),
        ).fetchall()
    logged = {row["day"] for row in rows}
    if not logged:
        return 0

    cursor = now_local().date()
    if cursor.strftime("%Y-%m-%d") not in logged:
        cursor -= timedelta(days=1)

    streak = 0
    while cursor.strftime("%Y-%m-%d") in logged and streak < max_lookback:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def stats():
    """Small summary used by the History page."""
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS logs, COUNT(DISTINCT substr(timestamp, 1, 10)) AS days, "
            "MIN(timestamp) AS first_log FROM sessions"
        ).fetchone()
    size = os.path.getsize(db_path()) if os.path.exists(db_path()) else 0
    return {
        "logs": row["logs"],
        "days": row["days"],
        "first_log": row["first_log"],
        "db_path": db_path(),
        "db_size_kb": round(size / 1024, 1),
    }
