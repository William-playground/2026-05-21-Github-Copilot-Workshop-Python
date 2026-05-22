import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g


def get_db() -> sqlite3.Connection:
    db = g.get("db")
    if db is None:
        database_path = Path(str(current_app.config["DATABASE"]))
        database_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(database_path)
        db.row_factory = sqlite3.Row
        g.db = db
    return db


def close_db(_: Any = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_type TEXT NOT NULL CHECK (session_type IN ('focus', 'break')),
            duration_seconds INTEGER NOT NULL CHECK (duration_seconds >= 0),
            completed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            focus_minutes INTEGER NOT NULL CHECK (focus_minutes > 0),
            short_break_minutes INTEGER NOT NULL CHECK (short_break_minutes > 0),
            long_break_minutes INTEGER NOT NULL CHECK (long_break_minutes > 0),
            long_break_interval INTEGER NOT NULL CHECK (long_break_interval > 0)
        );
        """
    )
    db.execute(
        """
        INSERT INTO settings (id, focus_minutes, short_break_minutes, long_break_minutes, long_break_interval)
        VALUES (1, 25, 5, 15, 4)
        ON CONFLICT(id) DO NOTHING
        """
    )
    db.commit()


def init_db_extension(app: Flask) -> None:
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()
