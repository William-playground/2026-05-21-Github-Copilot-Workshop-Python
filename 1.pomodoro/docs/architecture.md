# アーキテクチャ概要

## 現在の実装状態

本ドキュメントは `1.pomodoro/` 配下の実装コードをもとに記述しています（設計案ではなく実際の実装を反映）。

---

## 全体構成

```
1.pomodoro/
├── app.py                          # Flaskアプリケーションファクトリ
├── pomodoro/                       # メインパッケージ
│   ├── __init__.py
│   ├── domain/                     # ドメイン層（現在は空）
│   │   └── __init__.py
│   ├── application/                # アプリケーション層（現在は空）
│   │   └── __init__.py
│   ├── infrastructure/             # インフラ層
│   │   ├── __init__.py
│   │   └── db.py                   # SQLiteデータベース初期化・接続管理
│   └── presentation/               # プレゼンテーション層
│       ├── __init__.py
│       └── routes.py               # Flaskルート定義
├── static/
│   ├── assets/
│   │   └── pomodoro.png
│   └── css/
│       └── style.css               # スタイルシート
└── templates/
    └── index.html                  # メインHTMLテンプレート
```

---

## レイヤ構成

### Presentation層（`pomodoro/presentation/`）

- `routes.py`：Flaskルート登録
- 現在は `GET /` のみ実装（`index.html` を返す）

### Application層（`pomodoro/application/`）

- **現在は未実装**（`__init__.py` のみ）

### Domain層（`pomodoro/domain/`）

- **現在は未実装**（`__init__.py` のみ）

### Infrastructure層（`pomodoro/infrastructure/`）

- `db.py`：SQLite接続管理、スキーマ初期化
  - `get_db()`：リクエストスコープのDB接続取得（Flask `g` オブジェクト利用）
  - `close_db()`：リクエスト終了時にDB接続をクローズ
  - `init_db()`：テーブル作成と初期データ投入
  - `init_db_extension(app)`：Flaskアプリへの拡張登録

---

## アプリケーションファクトリ（`app.py`）

```python
def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE="instance/pomodoro.sqlite3",
        TESTING=False,
    )
    if config:
        app.config.update(config)
    init_db_extension(app)
    register_routes(app)
    return app
```

- `DATABASE`：SQLiteファイルのパス（デフォルト: `instance/pomodoro.sqlite3`）
- `TESTING`：テスト実行時に `True` を指定可能
- テスト用設定の注入は `config` 引数で行う

---

## データベース初期化フロー

1. `create_app()` 呼び出し時に `init_db_extension(app)` が実行される
2. アプリコンテキスト内で `init_db()` が呼ばれる
3. `sessions` テーブルと `settings` テーブルが `CREATE TABLE IF NOT EXISTS` で作成される
4. `settings` テーブルにデフォルト値（フォーカス25分、短休憩5分、長休憩15分、インターバル4回）が `ON CONFLICT(id) DO NOTHING` で挿入される

---

## 現在の実装スコープ（MVP段階）

| コンポーネント | 状態 |
|---|---|
| Flaskアプリファクトリ | ✅ 実装済み |
| DBスキーマ初期化 | ✅ 実装済み |
| `GET /` ルート | ✅ 実装済み |
| 静的UIテンプレート | ✅ 実装済み（ハードコード値） |
| REST APIエンドポイント | ❌ 未実装 |
| ドメイン層・アプリケーション層 | ❌ 未実装 |
| フロントエンドJavaScript | ❌ 未実装 |
| リポジトリパターン | ❌ 未実装 |
| テスト | ❌ 未実装 |
