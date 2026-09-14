# ルール: アーキテクチャ

## レイヤと依存方向
- `frontend/`（React/Vite/TS）→ REST + `/api/chat` ストリームで `backend` を呼ぶ。
- `backend/app/routers/*` → `auth` / `db.store` / `agent.runner` を利用。
- `backend/app/agent/*`（エージェント層）→ `db.store` と `config` に依存。
- **単一の `store`（`app/db.py`）**を REST と MCP ツールが共有する。これが「インプロセス MCP」を
  選んだ理由：ツールがインメモリ DB に直接アクセスでき、UI とデータの整合が自然に取れる。

## リクエスト毎の束縛
- `agent/tools.py: build_kg_server(user_id, ui_queue)` を **1 チャットリクエストごとに生成**する。
  各ツールはクロージャで `user_id`（認証済み）と `ui_queue` を束縛する。
- **モデル入力に user_id を渡さない**。ツールは常に「ログイン中ユーザー」のデータだけを操作する。

## チャットのストリーミングイベント契約（NDJSON）
`POST /api/chat` は `application/x-ndjson`（1 行 1 JSON）を返す。フロントは `fetch` +
`response.body.getReader()` で逐次パースする（`EventSource` は POST/Authorization 不可のため不使用）。

| type | 主なフィールド | UI 表現 |
|---|---|---|
| `text` | `text` | アシスタント吹き出し（連続する text は同一吹き出しに追記） |
| `tool_use` | `tool`, `label`, `agent?` | 稼働チップ（どのサブエージェント/ツールか） |
| `cards` | `items: Kindergarten[]` | 幼稚園カード群 |
| `favorite` | `action`, `id`, `name` | 登録/解除の通知 |
| `visit` | `confirmation_id`, `name`, `preferred_dates` | 見学申込 受付カード |
| `notice` | `text` | 補足メッセージ |
| `done` | `session_id`, `cost_usd`, `subtype` | ターン終了（session を保存） |
| `error` | `message`, `detail?` | エラー表示 |

- `cards` / `favorite` / `visit` は MCP ツールが `ui_queue` に push した構造化イベント。
  `runner.stream_chat` が各 SDK メッセージの後にキューを drain して差し込む。
- 追加・変更時は **backend(`runner.py`/`tools.py`) と frontend(`types.ts`/`ChatMessage.tsx`) の両方**を
  同期させること。

## セッション継続
- `store.get_session(user_id)` に前回の `session_id` を保持し、`ClaudeAgentOptions.resume` に渡す。
  `ResultMessage.session_id`（および init）で毎回更新する。
