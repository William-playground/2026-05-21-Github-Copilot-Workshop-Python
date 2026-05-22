# データモデル仕様

本ドキュメントは `pomodoro/infrastructure/db.py` に定義されているSQLiteスキーマをもとに記述しています。

---

## テーブル一覧

### `sessions` テーブル

ポモドーロセッション（作業・休憩）の完了記録を保存するテーブル。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | セッションID |
| `session_type` | TEXT | NOT NULL, CHECK (`'focus'` または `'break'`) | セッション種別 |
| `duration_seconds` | INTEGER | NOT NULL, CHECK (>= 0) | セッション継続時間（秒） |
| `completed_at` | TEXT | NOT NULL | 完了日時（ISO 8601形式のテキスト） |

**DDL:**

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_type TEXT NOT NULL CHECK (session_type IN ('focus', 'break')),
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds >= 0),
    completed_at TEXT NOT NULL
);
```

---

### `settings` テーブル

タイマー設定を保存するテーブル。常に1行のみ（`id = 1`）。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY, CHECK (id = 1) | 固定ID（シングルロウ運用） |
| `focus_minutes` | INTEGER | NOT NULL, CHECK (> 0) | 作業セッション時間（分） |
| `short_break_minutes` | INTEGER | NOT NULL, CHECK (> 0) | 短休憩時間（分） |
| `long_break_minutes` | INTEGER | NOT NULL, CHECK (> 0) | 長休憩時間（分） |
| `long_break_interval` | INTEGER | NOT NULL, CHECK (> 0) | 長休憩までの作業セッション回数 |

**DDL:**

```sql
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    focus_minutes INTEGER NOT NULL CHECK (focus_minutes > 0),
    short_break_minutes INTEGER NOT NULL CHECK (short_break_minutes > 0),
    long_break_minutes INTEGER NOT NULL CHECK (long_break_minutes > 0),
    long_break_interval INTEGER NOT NULL CHECK (long_break_interval > 0)
);
```

**デフォルト値:**

```sql
INSERT INTO settings (id, focus_minutes, short_break_minutes, long_break_minutes, long_break_interval)
VALUES (1, 25, 5, 15, 4)
ON CONFLICT(id) DO NOTHING;
```

| カラム | デフォルト値 |
|---|---|
| `focus_minutes` | 25 |
| `short_break_minutes` | 5 |
| `long_break_minutes` | 15 |
| `long_break_interval` | 4 |

---

## データベースファイル

- パス: `instance/pomodoro.sqlite3`（`app.config["DATABASE"]` で設定）
- `instance/` ディレクトリはアプリ起動時に自動作成される
- Flask の `row_factory` に `sqlite3.Row` を使用しており、カラム名でのアクセスが可能
