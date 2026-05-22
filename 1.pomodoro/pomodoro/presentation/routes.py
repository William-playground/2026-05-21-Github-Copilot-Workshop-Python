"""HTTP ルーティング（入出力変換のみ）。"""
from __future__ import annotations

from datetime import timezone
from typing import Any

from flask import Flask, jsonify, render_template, request

from pomodoro.application.services import (
    SessionService,
    SettingsService,
    ValidationError,
)
from pomodoro.domain.entities import CompletedSession, Settings, TodayStats
from pomodoro.infrastructure.db import get_db
from pomodoro.infrastructure.repositories_sqlite import (
    SessionRepository,
    SettingsRepository,
)


def _settings_to_dict(settings: Settings) -> dict[str, int]:
    return {
        "focus_minutes": settings.focus_minutes,
        "short_break_minutes": settings.short_break_minutes,
        "long_break_minutes": settings.long_break_minutes,
        "long_break_interval": settings.long_break_interval,
    }


def _stats_to_dict(stats: TodayStats) -> dict[str, int]:
    return {
        "completed_count": stats.completed_count,
        "focus_seconds_total": stats.focus_seconds_total,
    }


def _session_to_dict(session: CompletedSession) -> dict[str, Any]:
    completed_at = session.completed_at
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)
    return {
        "type": session.session_type,
        "duration_seconds": session.duration_seconds,
        "completed_at": completed_at.astimezone(timezone.utc).isoformat(),
    }


def register_routes(app: Flask) -> None:
    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/stats/today")
    def get_stats_today():
        service = SessionService(SessionRepository(get_db()))
        return jsonify(_stats_to_dict(service.today_stats()))

    @app.post("/api/sessions")
    def post_sessions():
        payload = request.get_json(silent=True)
        try:
            service = SessionService(SessionRepository(get_db()))
            session = service.record(payload or {})
        except ValidationError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(_session_to_dict(session)), 201

    @app.get("/api/settings")
    def get_settings():
        service = SettingsService(SettingsRepository(get_db()))
        return jsonify(_settings_to_dict(service.get()))

    @app.put("/api/settings")
    def put_settings():
        payload = request.get_json(silent=True)
        try:
            service = SettingsService(SettingsRepository(get_db()))
            settings = service.update(payload or {})
        except ValidationError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(_settings_to_dict(settings))
