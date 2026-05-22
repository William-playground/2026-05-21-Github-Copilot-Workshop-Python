from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, render_template, request

from ..application import services
from ..infrastructure.clock import Clock, SystemClock
from ..infrastructure.db import get_db
from ..infrastructure.repositories_sqlite import (
    SqliteSessionRepository,
    SqliteSettingsRepository,
)


def _parse_completed_at(raw: Any) -> datetime:
    if not isinstance(raw, str):
        raise services.ValidationError("completed_at must be an ISO 8601 string")
    try:
        # Accept trailing 'Z' as UTC.
        normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(normalized)
    except ValueError as e:
        raise services.ValidationError(f"completed_at not parseable: {raw!r}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def register_routes(app: Flask, *, clock: Clock | None = None) -> None:
    clock = clock or SystemClock()

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/stats/today")
    def stats_today() -> Any:
        repo = SqliteSessionRepository(get_db())
        stats = services.get_today_stats(repo, clock)
        return jsonify(
            {
                "completed_count": stats.completed_count,
                "focus_seconds_total": stats.focus_seconds_total,
            }
        )

    @app.post("/api/sessions")
    def create_session() -> Any:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "JSON object body required"}), 400
        try:
            completed_at = _parse_completed_at(payload.get("completed_at"))
            session = services.record_session(
                SqliteSessionRepository(get_db()),
                session_type=payload.get("type"),
                duration_seconds=payload.get("duration_seconds"),
                completed_at=completed_at,
            )
        except services.ValidationError:
            return jsonify({"error": "invalid request payload"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "invalid request payload"}), 400
        return (
            jsonify(
                {
                    "id": session.id,
                    "type": session.session_type,
                    "duration_seconds": session.duration_seconds,
                    "completed_at": session.completed_at.isoformat(),
                }
            ),
            201,
        )

    @app.get("/api/settings")
    def get_settings_route() -> Any:
        settings = services.get_settings(SqliteSettingsRepository(get_db()))
        return jsonify(
            {
                "focus_minutes": settings.focus_minutes,
                "short_break_minutes": settings.short_break_minutes,
                "long_break_minutes": settings.long_break_minutes,
                "long_break_interval": settings.long_break_interval,
            }
        )

    @app.put("/api/settings")
    def put_settings_route() -> Any:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "JSON object body required"}), 400
        try:
            settings = services.update_settings(
                SqliteSettingsRepository(get_db()),
                focus_minutes=payload.get("focus_minutes"),
                short_break_minutes=payload.get("short_break_minutes"),
                long_break_minutes=payload.get("long_break_minutes"),
                long_break_interval=payload.get("long_break_interval"),
            )
        except services.ValidationError:
            return jsonify({"error": "invalid request payload"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "invalid request payload"}), 400
        return jsonify(
            {
                "focus_minutes": settings.focus_minutes,
                "short_break_minutes": settings.short_break_minutes,
                "long_break_minutes": settings.long_break_minutes,
                "long_break_interval": settings.long_break_interval,
            }
        )
