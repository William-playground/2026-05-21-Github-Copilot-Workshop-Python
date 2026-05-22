"""Integration tests for the gamification HTTP API."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

from app import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path):
	app = create_app(
		{"DATABASE": str(tmp_path / "test.sqlite3"), "TESTING": True}
	)
	with app.test_client() as c:
		yield c


def test_summary_empty_db_returns_initial_state(client) -> None:
	res = client.get("/api/gamification/summary")
	assert res.status_code == 200
	body = res.get_json()
	assert body["xp"]["level"] == 1
	assert body["xp"]["xp"] == 0
	assert body["streak_days"] == 0
	assert body["total_focus_sessions"] == 0
	assert body["success_rate"] == 0.0
	earned_ids = {b["id"] for b in body["badges"] if b["earned"]}
	assert earned_ids == set()


def test_post_session_records_focus_and_summary_reflects_xp(client) -> None:
	for _ in range(3):
		res = client.post(
			"/api/sessions",
			json={
				"session_type": "focus",
				"duration_seconds": 1500,
				"completed_at": "2026-05-21T10:00:00",
			},
		)
		assert res.status_code == 201, res.get_data(as_text=True)

	summary = client.get("/api/gamification/summary").get_json()
	assert summary["total_focus_sessions"] == 3
	assert summary["xp"]["xp"] == 30
	assert summary["xp"]["level"] == 1
	# At least the "first_focus" badge should be earned
	earned_ids = {b["id"] for b in summary["badges"] if b["earned"]}
	assert "first_focus" in earned_ids


def test_post_session_rejects_invalid_type(client) -> None:
	res = client.post(
		"/api/sessions",
		json={"session_type": "nope", "duration_seconds": 100},
	)
	assert res.status_code == 400


def test_post_session_rejects_negative_duration(client) -> None:
	res = client.post(
		"/api/sessions",
		json={"session_type": "focus", "duration_seconds": -10},
	)
	assert res.status_code == 400


def test_aborted_session_lowers_success_rate(client) -> None:
	client.post(
		"/api/sessions",
		json={
			"session_type": "focus",
			"duration_seconds": 1500,
			"completed_at": "2026-05-21T10:00:00",
			"status": "completed",
		},
	)
	client.post(
		"/api/sessions",
		json={
			"session_type": "focus",
			"duration_seconds": 600,
			"completed_at": "2026-05-21T11:00:00",
			"status": "aborted",
		},
	)
	summary = client.get("/api/gamification/summary").get_json()
	assert summary["total_focus_sessions"] == 1
	assert summary["success_rate"] == pytest.approx(0.5)


def test_stats_week_returns_seven_days(client) -> None:
	res = client.get("/api/gamification/stats?range=week")
	assert res.status_code == 200
	body = res.get_json()
	assert body["range"] == "week"
	assert len(body["daily"]) == 7
	assert body["totals"]["focus_count"] == 0


def test_stats_invalid_range_returns_400(client) -> None:
	res = client.get("/api/gamification/stats?range=year")
	assert res.status_code == 400
