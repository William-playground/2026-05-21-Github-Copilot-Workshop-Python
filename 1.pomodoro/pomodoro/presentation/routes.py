from datetime import date, datetime
from typing import Any

from flask import Flask, jsonify, render_template, request

from pomodoro.infrastructure.db import get_db


VALID_SESSION_TYPES = ("focus", "break")
SETTING_FIELDS = (
    "focus_minutes",
    "short_break_minutes",
    "long_break_minutes",
    "long_break_interval",
)


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        # Accept trailing "Z" as UTC for convenience.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def register_routes(app: Flask) -> None:
    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/stats/today")
    def get_stats_today():
        db = get_db()
        today = date.today().isoformat()
        row = db.execute(
            """
            SELECT COUNT(*) AS completed_count,
                   COALESCE(SUM(duration_seconds), 0) AS focus_seconds_total
            FROM sessions
            WHERE session_type = 'focus'
              AND substr(completed_at, 1, 10) = ?
            """,
            (today,),
        ).fetchone()
        return jsonify(
            {
                "completed_count": int(row["completed_count"]),
                "focus_seconds_total": int(row["focus_seconds_total"]),
            }
        )

    @app.post("/api/sessions")
    def create_session():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "invalid JSON body"}), 400

        session_type = data.get("type")
        duration_seconds = data.get("duration_seconds")
        completed_at_raw = data.get("completed_at")

        if session_type not in VALID_SESSION_TYPES:
            return jsonify({"error": "invalid type"}), 400
        if not _is_non_negative_int(duration_seconds):
            return jsonify({"error": "invalid duration_seconds"}), 400
        if _parse_iso_datetime(completed_at_raw) is None:
            return jsonify({"error": "invalid completed_at"}), 400

        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO sessions (session_type, duration_seconds, completed_at)
            VALUES (?, ?, ?)
            """,
            (session_type, duration_seconds, completed_at_raw),
        )
        db.commit()
        return (
            jsonify(
                {
                    "id": cursor.lastrowid,
                    "type": session_type,
                    "duration_seconds": duration_seconds,
                    "completed_at": completed_at_raw,
                }
            ),
            201,
        )

    @app.get("/api/settings")
    def get_settings():
        db = get_db()
        row = db.execute(
            """
            SELECT focus_minutes,
                   short_break_minutes,
                   long_break_minutes,
                   long_break_interval
            FROM settings
            WHERE id = 1
            """
        ).fetchone()
        return jsonify({field: int(row[field]) for field in SETTING_FIELDS})

    @app.put("/api/settings")
    def update_settings():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "invalid JSON body"}), 400

        values: dict[str, int] = {}
        for field in SETTING_FIELDS:
            if field not in data:
                return jsonify({"error": f"missing {field}"}), 400
            value = data[field]
            if not _is_positive_int(value):
                return jsonify({"error": f"invalid {field}"}), 400
            values[field] = value

        db = get_db()
        db.execute(
            """
            UPDATE settings
            SET focus_minutes = ?,
                short_break_minutes = ?,
                long_break_minutes = ?,
                long_break_interval = ?
            WHERE id = 1
            """,
            (
                values["focus_minutes"],
                values["short_break_minutes"],
                values["long_break_minutes"],
                values["long_break_interval"],
            ),
        )
        db.commit()
        return jsonify(values)
