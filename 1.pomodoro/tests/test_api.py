"""API integration tests for Phase 4 endpoints."""

from __future__ import annotations

from datetime import date

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    app = create_app({"DATABASE": str(db_path), "TESTING": True})
    with app.test_client() as client:
        yield client


# ---------- GET /api/stats/today ----------

def test_stats_today_returns_zero_when_empty(client):
    res = client.get("/api/stats/today")
    assert res.status_code == 200
    assert res.get_json() == {"completed_count": 0, "focus_seconds_total": 0}


def test_stats_today_counts_focus_sessions_for_today(client):
    today = date.today().isoformat()
    client.post(
        "/api/sessions",
        json={"type": "focus", "duration_seconds": 1500, "completed_at": f"{today}T10:00:00"},
    )
    client.post(
        "/api/sessions",
        json={"type": "focus", "duration_seconds": 1200, "completed_at": f"{today}T11:30:00"},
    )
    # break sessions and other-day sessions are excluded
    client.post(
        "/api/sessions",
        json={"type": "break", "duration_seconds": 300, "completed_at": f"{today}T10:30:00"},
    )
    client.post(
        "/api/sessions",
        json={"type": "focus", "duration_seconds": 1500, "completed_at": "2000-01-01T10:00:00"},
    )

    res = client.get("/api/stats/today")
    assert res.status_code == 200
    assert res.get_json() == {"completed_count": 2, "focus_seconds_total": 2700}


# ---------- POST /api/sessions ----------

def test_post_sessions_records_session(client):
    res = client.post(
        "/api/sessions",
        json={
            "type": "focus",
            "duration_seconds": 1500,
            "completed_at": "2026-05-22T03:00:00",
        },
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["type"] == "focus"
    assert body["duration_seconds"] == 1500
    assert body["completed_at"] == "2026-05-22T03:00:00"
    assert isinstance(body["id"], int)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"type": "invalid", "duration_seconds": 60, "completed_at": "2026-05-22T03:00:00"},
        {"type": "focus", "duration_seconds": -1, "completed_at": "2026-05-22T03:00:00"},
        {"type": "focus", "duration_seconds": "60", "completed_at": "2026-05-22T03:00:00"},
        {"type": "focus", "duration_seconds": 60, "completed_at": "not-a-date"},
        {"type": "focus", "duration_seconds": 60},
    ],
)
def test_post_sessions_rejects_invalid_input(client, payload):
    res = client.post("/api/sessions", json=payload)
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_post_sessions_rejects_non_json(client):
    res = client.post("/api/sessions", data="not-json", content_type="text/plain")
    assert res.status_code == 400


# ---------- GET/PUT /api/settings ----------

def test_get_settings_returns_defaults(client):
    res = client.get("/api/settings")
    assert res.status_code == 200
    assert res.get_json() == {
        "focus_minutes": 25,
        "short_break_minutes": 5,
        "long_break_minutes": 15,
        "long_break_interval": 4,
    }


def test_put_settings_updates_values(client):
    new_settings = {
        "focus_minutes": 50,
        "short_break_minutes": 10,
        "long_break_minutes": 20,
        "long_break_interval": 3,
    }
    res = client.put("/api/settings", json=new_settings)
    assert res.status_code == 200
    assert res.get_json() == new_settings

    res = client.get("/api/settings")
    assert res.get_json() == new_settings


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "focus_minutes": 0,
            "short_break_minutes": 5,
            "long_break_minutes": 15,
            "long_break_interval": 4,
        },
        {
            "focus_minutes": -1,
            "short_break_minutes": 5,
            "long_break_minutes": 15,
            "long_break_interval": 4,
        },
        {
            "focus_minutes": "25",
            "short_break_minutes": 5,
            "long_break_minutes": 15,
            "long_break_interval": 4,
        },
        {
            "focus_minutes": 25,
            "short_break_minutes": 5,
            "long_break_minutes": 15,
        },
    ],
)
def test_put_settings_rejects_invalid_input(client, payload):
    res = client.put("/api/settings", json=payload)
    assert res.status_code == 400
    assert "error" in res.get_json()
