# ポモドーロタイマー Webアプリケーション アーキテクチャ案

## 1. 目的と前提

本ドキュメントは、ポモドーロタイマーの UI モック（円形プログレス、開始/リセット、今日の進捗）をもとに、
Flask + HTML/CSS/JavaScript で実装するためのアーキテクチャ方針を整理したものです。

### 目的
- MVP を素早く実装する
- 後から機能追加しやすい構造にする
- ユニットテストしやすい構造にする

### 前提
- サーバーサイド: Python + Flask
- フロントエンド: HTML/CSS/JavaScript（1ページ構成）
- データ保存: SQLite（ローカル開発を想定）

---

## 2. 推奨アーキテクチャ（全体像）

### 方針
**「1ページSPA風 + Flask API」** を採用する。

- 表示とタイマー進行はフロントエンド（JavaScript）
- 永続化（統計・設定）はバックエンド（Flask + SQLite）
- セッション遷移ルール（作業/休憩）はサービス層で管理

### 構成イメージ
1. UI層（HTML/CSS）
2. フロントロジック層（JavaScript タイマーエンジン）
3. API層（Flask routes）
4. アプリケーション/ドメイン層（セッション遷移・統計ロジック）
5. インフラ層（Repository + SQLite）

---

## 3. レイヤ責務

## 3.1 Presentation（UI / API）
- `templates/index.html`, `static/css/style.css`, `static/js/*.js`
- `routes.py` は HTTP 入出力（JSON <-> DTO）に集中
- 画面描画、ボタン操作、表示更新を担当

## 3.2 Application（ユースケース）
- セッション完了記録
- 今日の進捗集計
- 設定取得/更新

## 3.3 Domain（ビジネスルール）
- ポモドーロ遷移ロジック（作業→短休憩→作業…4回目で長休憩）
- タイマー状態遷移（開始/停止/再開/リセット）

## 3.4 Infrastructure（永続化・時刻）
- SQLite 実装
- リポジトリ実装（SessionRepository, SettingsRepository）
- 時刻取得（Clock）

---

## 4. 推奨ディレクトリ構成

```text
2026-05-21-Github-Copilot-Workshop-Python/
  app.py
  architecture.md
  pomodoro/
    presentation/
      routes.py
    application/
      services.py
    domain/
      state_machine.py
      entities.py
    infrastructure/
      repositories_sqlite.py
      clock.py
      db.py
  templates/
    index.html
  static/
    css/
      style.css
    js/
      app.js
      timer_engine.js
    assets/
  tests/
    unit/
      domain/
      application/
    integration/
      api/
```

> 現在の最小構成（`app.py` 中心）から段階的に分割していく想定。

---

## 5. フロントエンド設計

## 5.1 タイマー管理
- `remainingSeconds` を毎秒デクリメントするだけでなく、
  **`endTimestamp` から逆算**して表示を更新する
- タブ非アクティブ時の遅延やズレを軽減する

## 5.2 円形プログレス表示
- SVG もしくは CSS でリングを描画
- 進捗率 `progress = 1 - remaining/total` からストロークを更新

## 5.3 ローカル復元
- 進行中セッション情報を `localStorage` に保存
- リロード後も表示復元

---

## 6. API設計（MVP）

## 6.1 統計
- `GET /api/stats/today`
  - response: `completed_count`, `focus_seconds_total`

## 6.2 セッション記録
- `POST /api/sessions`
  - request: `type` (`focus` | `break`), `duration_seconds`, `completed_at`

## 6.3 設定
- `GET /api/settings`
- `PUT /api/settings`
  - request: `focus_minutes`, `short_break_minutes`, `long_break_minutes`, `long_break_interval`

---

## 7. データモデル（SQLite）

## 7.1 sessions
- `id` (PK)
- `session_type` (`focus` / `break`)
- `duration_seconds`
- `completed_at` (timestamp)

## 7.2 settings
- `id` (PK, single row 運用)
- `focus_minutes`
- `short_break_minutes`
- `long_break_minutes`
- `long_break_interval`

---

## 8. 状態機械（State Machine）

状態の例:
- `idle`
- `running_focus`
- `paused_focus`
- `running_short_break`
- `running_long_break`
- `paused_break`

イベントの例:
- `START`
- `PAUSE`
- `RESUME`
- `RESET`
- `COMPLETE_SESSION`

遷移は **純粋関数** で実装する。

```text
next_state = transition(current_state, event, config, now)
```

これにより、状態遷移のユニットテストが容易になる。

---

## 9. ユニットテスト容易性のための設計強化点

以下は、テストしやすさを高めるための重要ポイント。

1. **ルートを薄くする**
   - Flask route は入出力変換のみ
   - ビジネスロジックは service/domain に集約

2. **状態遷移を純粋関数化**
   - 副作用を排除
   - 同じ入力に対して同じ出力

3. **Clock注入**
   - `datetime.now()` の直接呼び出しを避ける
   - `SystemClock` / `FixedClock` を使い分ける

4. **Repository分離**
   - DBアクセスを abstraction の背後に置く
   - ユニットテストでは Fake Repository を使用

5. **App Factory化**
   - `create_app(config)` パターン
   - テスト用設定（`TESTING=True`、テストDB）を容易に適用

6. **入力バリデーション層**
   - 不正入力（負値、未知 type、日時形式不正）を統一的に弾く

---

## 10. テスト戦略

推奨比率:
- ユニットテスト: 70%
- 統合テスト: 20%
- APIテスト: 10%

重点ケース:
1. focus 完了後に short break へ遷移
2. 4回目 focus 完了後に long break へ遷移
3. pause/resume で残り時間が破綻しない
4. reset で初期状態へ戻る
5. 今日の統計が当日分のみ集計される
6. 日付境界（23:59→00:00）の集計が正しい
7. 不正入力で 400 を返す

---

## 11. 実装ステップ（推奨）

1. UIモック再現（静的）
2. フロントのタイマーエンジン実装
3. Flask API（stats/settings/sessions）実装
4. フロントとAPI接続
5. 状態遷移/集計のユニットテスト追加
6. API統合テスト追加

---

## 12. 将来拡張

- 通知音・ブラウザ通知
- ユーザー認証
- 複数デバイス同期
- 週次/月次の統計表示
- タスク管理（何に集中したか）との連携

拡張時も、Domain/Application/Infrastructure の分離を維持することで、
機能追加とテスト追加がしやすい状態を保てる。
