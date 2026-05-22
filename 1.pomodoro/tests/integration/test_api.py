"""API 統合テスト。"""
from __future__ import annotations

from datetime import datetime, timezone


def test_index_returns_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"<html" in res.data


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
    new = {
        "focus_minutes": 30,
        "short_break_minutes": 6,
        "long_break_minutes": 20,
        "long_break_interval": 3,
    }
    res = client.put("/api/settings", json=new)
    assert res.status_code == 200
    assert res.get_json() == new
    # 永続化されている
    assert client.get("/api/settings").get_json() == new


def test_put_settings_rejects_invalid(client):
    res = client.put(
        "/api/settings",
        json={
            "focus_minutes": 0,
            "short_break_minutes": 5,
            "long_break_minutes": 15,
            "long_break_interval": 4,
        },
    )
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_post_session_persists_and_stats_reflects(client):
    now = datetime.now(timezone.utc).isoformat()
    res = client.post(
        "/api/sessions",
        json={"type": "focus", "duration_seconds": 1500, "completed_at": now},
    )
    assert res.status_code == 201

    stats = client.get("/api/stats/today").get_json()
    assert stats == {"completed_count": 1, "focus_seconds_total": 1500}


def test_post_session_break_does_not_count_focus(client):
    now = datetime.now(timezone.utc).isoformat()
    client.post(
        "/api/sessions",
        json={"type": "break", "duration_seconds": 300, "completed_at": now},
    )
    stats = client.get("/api/stats/today").get_json()
    assert stats == {"completed_count": 0, "focus_seconds_total": 0}


def test_post_session_rejects_invalid_type(client):
    res = client.post(
        "/api/sessions",
        json={"type": "nope", "duration_seconds": 10},
    )
    assert res.status_code == 400


def test_post_session_rejects_negative_duration(client):
    res = client.post(
        "/api/sessions",
        json={"type": "focus", "duration_seconds": -1},
    )
    assert res.status_code == 400


def test_stats_excludes_other_day(client):
    # 昨日のデータを投入
    client.post(
        "/api/sessions",
        json={
            "type": "focus",
            "duration_seconds": 1500,
            "completed_at": "2000-01-01T12:00:00+00:00",
        },
    )
    stats = client.get("/api/stats/today").get_json()
    assert stats == {"completed_count": 0, "focus_seconds_total": 0}
