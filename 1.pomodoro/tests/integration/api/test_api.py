"""API integration tests using Flask's test client and a temporary SQLite DB."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from pomodoro.infrastructure.clock import FixedClock


UTC = timezone.utc


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 1, 15, 12, 0, tzinfo=UTC))


@pytest.fixture
def app(tmp_path: Path, fixed_clock: FixedClock) -> Iterator[Flask]:
    db_path = tmp_path / "test.sqlite3"
    flask_app = create_app(
        config={"DATABASE": str(db_path), "TESTING": True},
        clock=fixed_clock,
    )
    yield flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


# --------------------------- GET /api/stats/today --------------------


class TestStatsToday:
    def test_empty_db_returns_zeros(self, client: FlaskClient) -> None:
        resp = client.get("/api/stats/today")
        assert resp.status_code == 200
        assert resp.get_json() == {"completed_count": 0, "focus_seconds_total": 0}

    def test_aggregates_recorded_focus_sessions(self, client: FlaskClient) -> None:
        for _ in range(3):
            r = client.post(
                "/api/sessions",
                json={
                    "type": "focus",
                    "duration_seconds": 1500,
                    "completed_at": "2026-01-15T09:00:00Z",
                },
            )
            assert r.status_code == 201
        # A break session must not affect the focus stats.
        client.post(
            "/api/sessions",
            json={
                "type": "break",
                "duration_seconds": 300,
                "completed_at": "2026-01-15T09:30:00Z",
            },
        )
        resp = client.get("/api/stats/today")
        assert resp.status_code == 200
        assert resp.get_json() == {
            "completed_count": 3,
            "focus_seconds_total": 4500,
        }


# --------------------------- POST /api/sessions ----------------------


class TestCreateSession:
    def test_happy_path(self, client: FlaskClient) -> None:
        resp = client.post(
            "/api/sessions",
            json={
                "type": "focus",
                "duration_seconds": 1500,
                "completed_at": "2026-01-15T09:00:00Z",
            },
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["type"] == "focus"
        assert body["duration_seconds"] == 1500
        assert isinstance(body["id"], int)

    @pytest.mark.parametrize(
        "payload",
        [
            {"type": "nap", "duration_seconds": 10, "completed_at": "2026-01-15T09:00:00Z"},
            {"type": "focus", "duration_seconds": -5, "completed_at": "2026-01-15T09:00:00Z"},
            {"type": "focus", "duration_seconds": 10, "completed_at": "not-a-date"},
            {"type": "focus", "duration_seconds": 10},  # missing completed_at
            {"duration_seconds": 10, "completed_at": "2026-01-15T09:00:00Z"},  # missing type
            {"type": "focus", "duration_seconds": "10", "completed_at": "2026-01-15T09:00:00Z"},
        ],
    )
    def test_invalid_payload_returns_400(
        self, client: FlaskClient, payload: dict
    ) -> None:
        resp = client.post("/api/sessions", json=payload)
        assert resp.status_code == 400
        assert "error" in (resp.get_json() or {})

    def test_non_json_body_returns_400(self, client: FlaskClient) -> None:
        resp = client.post(
            "/api/sessions", data="not json", content_type="text/plain"
        )
        assert resp.status_code == 400


# --------------------------- /api/settings ---------------------------


class TestSettings:
    def test_get_returns_defaults(self, client: FlaskClient) -> None:
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        assert resp.get_json() == {
            "focus_minutes": 25,
            "short_break_minutes": 5,
            "long_break_minutes": 15,
            "long_break_interval": 4,
        }

    def test_put_updates_settings(self, client: FlaskClient) -> None:
        resp = client.put(
            "/api/settings",
            json={
                "focus_minutes": 50,
                "short_break_minutes": 10,
                "long_break_minutes": 20,
                "long_break_interval": 3,
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["focus_minutes"] == 50
        # Verify it persisted.
        assert client.get("/api/settings").get_json()["focus_minutes"] == 50

    @pytest.mark.parametrize(
        "payload",
        [
            {"focus_minutes": 0, "short_break_minutes": 5, "long_break_minutes": 15,
             "long_break_interval": 4},
            {"focus_minutes": 25, "short_break_minutes": -1, "long_break_minutes": 15,
             "long_break_interval": 4},
            {"focus_minutes": 25, "short_break_minutes": 5, "long_break_minutes": 15},
            {},
        ],
    )
    def test_put_invalid_returns_400(self, client: FlaskClient, payload: dict) -> None:
        resp = client.put("/api/settings", json=payload)
        assert resp.status_code == 400


# --------------------------- date boundary at the API ----------------


class TestApiDateBoundary:
    def test_yesterday_session_is_excluded_from_today_stats(
        self, client: FlaskClient, fixed_clock: FixedClock
    ) -> None:
        # Fixed clock is 2026-01-15 12:00 UTC.
        # Insert one session yesterday (23:59:59) and one today (00:00:00).
        client.post(
            "/api/sessions",
            json={
                "type": "focus",
                "duration_seconds": 1500,
                "completed_at": "2026-01-14T23:59:59Z",
            },
        )
        client.post(
            "/api/sessions",
            json={
                "type": "focus",
                "duration_seconds": 600,
                "completed_at": "2026-01-15T00:00:00Z",
            },
        )
        body = client.get("/api/stats/today").get_json()
        assert body == {"completed_count": 1, "focus_seconds_total": 600}

        # Roll the clock forward to the next day; the previous "today" session
        # should now be excluded, and a freshly recorded one included.
        fixed_clock.set(datetime(2026, 1, 16, 0, 0, 1, tzinfo=UTC))
        client.post(
            "/api/sessions",
            json={
                "type": "focus",
                "duration_seconds": 1500,
                "completed_at": "2026-01-16T00:00:00Z",
            },
        )
        body = client.get("/api/stats/today").get_json()
        assert body == {"completed_count": 1, "focus_seconds_total": 1500}


# --------------------------- index page (smoke) ----------------------


class TestIndexPage:
    def test_index_renders(self, client: FlaskClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "ポモドーロ" in resp.get_data(as_text=True)
