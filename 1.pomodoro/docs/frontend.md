# フロントエンド ドキュメント

本ドキュメントは `templates/` および `static/` 配下の実装をもとに記述しています。

---

## 現在の実装状態

フロントエンドはMVP初期段階です。現時点では静的なHTMLテンプレートとCSSのみが実装されており、JavaScriptによるタイマーロジックはまだ実装されていません。

---

## ファイル構成

```
static/
├── assets/
│   └── pomodoro.png            # アセット画像
└── css/
    └── style.css               # スタイルシート
templates/
└── index.html                  # メインHTMLテンプレート
```

---

## `templates/index.html`

メインのHTMLテンプレートです。Flaskの `render_template()` で返されます。

**言語設定:** `lang="ja"`（日本語）

**UI構成:**

| セクション | 説明 |
|---|---|
| `.title-bar` | タイトル「ポモドーロタイマー」とウィンドウ操作風アイコン |
| `.status` | 現在の状態テキスト（現在は「作業中」にハードコード） |
| `.progress-area` | 円形プログレスリングと残り時間表示 |
| `.actions` | 「開始」「リセット」ボタン |
| `.summary` | 今日の進捗（完了数・集中時間） |

**アクセシビリティ対応:**
- `aria-live="polite"` でステータス変化を読み上げ可能
- `role="img"` と `aria-label` でプログレスリングにラベル付け

**現在のハードコード値:**
- 残り時間: `25:00`
- 進捗: `72%`
- 完了数: `4`
- 集中時間: `1時間40分`

> これらの値はJavaScript実装後に動的に更新される予定です。

---

## `static/css/style.css`

CSS カスタムプロパティ（変数）を使用したスタイルシートです。

**カラーパレット（CSS変数）:**

| 変数名 | 値 | 用途 |
|---|---|---|
| `--bg-top` | `#6f6bd6` | 背景グラデーション上端 |
| `--bg-bottom` | `#655bc9` | 背景グラデーション下端 |
| `--card-bg` | `#f4f4f8` | カード背景色 |
| `--panel-bg` | `#e8e8f2` | パネル背景色 |
| `--text-main` | `#30313b` | 主テキスト色 |
| `--text-muted` | `#626478` | サブテキスト色 |
| `--accent` | `#6a77e8` | アクセントカラー |
| `--ring-base` | `#e1e2e8` | プログレスリング未達部分の色 |
| `--shadow` | `0 20px 40px rgba(40, 38, 96, 0.25)` | カードシャドウ |

**フォント:**
```css
font-family: "Noto Sans JP", "Hiragino Kaku Gothic ProN", "Yu Gothic", system-ui, -apple-system, sans-serif;
```

**レスポンシブ対応:**
- カード幅: `min(400px, 100%)`（最大400px、モバイルで全幅）
- フォントサイズ: `clamp()` を使用したレスポンシブ設定
- ブレークポイント: `max-width: 480px`（スマートフォン向けレイアウト調整）

**プログレスリング実装:**
- CSS `conic-gradient` でリングを描画
- 現在は静的に72%の進捗を表示
- 外側リング：`conic-gradient(var(--accent) 0 72%, var(--ring-base) 72% 100%)`
- 内側円（`.ring-inner`）でドーナツ型を実現

**ボタンスタイル:**
- `.btn-primary`：グラデーション背景（`#6f7beb` → `#644db8`）、白テキスト
- `.btn-outline`：透明背景、アクセントカラーのボーダー

---

## 未実装のJavaScriptモジュール（設計済み）

以下のJavaScriptモジュールは設計済みですが、**現時点では未実装**です。

| モジュール | 説明 |
|---|---|
| タイマーエンジン | `endTimestamp` からの逆算でタイマー管理、タブ非アクティブ時の精度維持 |
| プログレスリング更新 | `conic-gradient` の動的更新 |
| API連携 | バックエンドAPIとの通信（セッション記録、統計取得、設定管理） |
| `localStorage` 復元 | ページリロード後のセッション状態復元 |
