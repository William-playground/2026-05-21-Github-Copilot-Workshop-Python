"""Phase 0 smoke tests.

Phase 0 の完了条件（DoD）を保証するスモークテスト。

- アプリが起動する（`create_app` が成功し、test_client が使える）
- DB 初期化が成功する（`sessions` / `settings` テーブルが作成される）
- トップ画面が表示される（`GET /` が 200 で `index.html` を返す）
"""
from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

# テスト実行時に 1.pomodoro/ 配下を import path に含める
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402


class Phase0SmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = ROOT / "instance" / "test_phase0.sqlite3"
        if self.db_path.exists():
            self.db_path.unlink()
        self.app = create_app({"DATABASE": str(self.db_path), "TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        if self.db_path.exists():
            self.db_path.unlink()

    def test_app_factory_creates_app(self) -> None:
        """create_app(config) が Flask アプリを返し、設定が反映されること。"""
        self.assertTrue(self.app.config["TESTING"])
        self.assertEqual(self.app.config["DATABASE"], str(self.db_path))

    def test_db_init_creates_sessions_and_settings_tables(self) -> None:
        """SQLite 初期化で sessions / settings テーブルが作成されること。"""
        self.assertTrue(self.db_path.exists())
        with sqlite3.connect(self.db_path) as con:
            tables = {
                row[0]
                for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertIn("sessions", tables)
        self.assertIn("settings", tables)

    def test_index_route_returns_top_page(self) -> None:
        """GET / が 200 を返し、index.html がレンダリングされること。"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("ポモドーロタイマー", body)


if __name__ == "__main__":
    unittest.main()
