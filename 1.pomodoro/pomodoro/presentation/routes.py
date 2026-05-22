from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from ..application.gamification_service import (
    build_stats,
    build_summary,
    record_session,
)
from ..infrastructure.db import get_db


def register_routes(app: Flask) -> None:
    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.post("/api/sessions")
    def create_session():
        payload = request.get_json(silent=True) or {}
        try:
            new_id = record_session(
                get_db(),
                session_type=payload.get("session_type", ""),
                duration_seconds=int(payload.get("duration_seconds", -1)),
                completed_at=payload.get("completed_at"),
                status=payload.get("status", "completed"),
            )
        except (ValueError, TypeError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"id": new_id}), 201

    @app.get("/api/gamification/summary")
    def gamification_summary():
        return jsonify(build_summary(get_db()))

    @app.get("/api/gamification/stats")
    def gamification_stats():
        range_name = request.args.get("range", "week")
        try:
            data = build_stats(get_db(), range_name=range_name)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(data)
