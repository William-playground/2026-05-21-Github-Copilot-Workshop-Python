# API リファレンス

本ドキュメントは `pomodoro/presentation/routes.py` の実装をもとに記述しています。

---

## 現在実装済みのエンドポイント

### `GET /`

メインのHTMLページを返します。

**レスポンス:**

- ステータスコード: `200 OK`
- Content-Type: `text/html`
- ボディ: `templates/index.html` のレンダリング結果

**実装:**

```python
@app.get("/")
def index() -> str:
    return render_template("index.html")
```

---

## 未実装のエンドポイント（設計済み）

以下のエンドポイントは `architecture.md` に設計として記載されていますが、**現時点では未実装**です。

### `GET /api/stats/today`（未実装）

今日の統計を取得します。

- レスポンス予定: `completed_count`, `focus_seconds_total`

### `POST /api/sessions`（未実装）

セッション完了を記録します。

- リクエスト予定: `type`（`focus` または `break`）, `duration_seconds`, `completed_at`

### `GET /api/settings`（未実装）

タイマー設定を取得します。

### `PUT /api/settings`（未実装）

タイマー設定を更新します。

- リクエスト予定: `focus_minutes`, `short_break_minutes`, `long_break_minutes`, `long_break_interval`

---

## 注記

現在のアプリはMVP初期段階であり、フロントエンドとバックエンド間のAPI通信はまだ実装されていません。UIは静的なHTMLテンプレートとして提供されており、表示値はハードコードされています。
