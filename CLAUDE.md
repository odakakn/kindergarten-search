# CLAUDE.md

このリポジトリで作業する Claude Code / 開発者向けのガイドです。

## プロジェクト概要

「自分にピッタリの幼稚園を探す」ための**学習用 Web アプリ**。中核は Claude Agent SDK
（Python）による**チャット型マルチエージェント**で、保護者の属性・希望条件をもとに幼稚園を
レコメンドし、同一チャット内でお気に入り登録・見学申込まで代行する。ログイン／ユーザー属性
管理／お気に入り一覧も提供する。

学習目的として、**あえてマルチエージェント（Agent/Task ツールによる委譲）**を採用している。

## アーキテクチャ

```
[React (Vite+TS)  :5173]
   │  REST (/api/login, /api/profile, /api/favorites, /api/kindergartens,
   │        /api/visit-requests, /api/visit-requests/{id}/cancel, /api/conversations)
   │  ストリーミング (POST /api/chat {message, conversation_id}, NDJSON)  ※ dev は Vite プロキシで :8000 へ
   ▼
[FastAPI backend  :8000]
   ├─ インメモリ DB（app/db.py: users/profiles/favorites/visit_requests/kindergartens/conversations）
   └─ Agent 層（Claude Agent SDK）
        ├─ 司令塔（メイン, app/agent/runner.py の query()）
        ├─ subagent: recommender        … 検索・ランク付け・web補足
        ├─ subagent: visit-coordinator  … お気に入り登録・見学申込
        └─ インプロセス MCP サーバー "kg"（app/agent/tools.py, リクエスト毎に user_id 束縛）
```

- **DB はインメモリ**（バックエンドに包含、プロセス終了で消える）。REST とエージェントの
  MCP ツールは同一 `store` インスタンス（`app/db.py`）を共有する。
- **MCP はインプロセス方式**（`create_sdk_mcp_server`）。ツールは `build_kg_server(user_id, ui_queue)`
  で毎リクエスト生成し、クロージャに認証済み `user_id` と UI イベントキューを束縛する。
- **チャット履歴**は会話単位で保持（`store.conversations`、`routers/conversations.py`）。エージェントの
  セッション（`resume`）も**会話単位**（`get_conv_session`/`set_conv_session`）。フロントは各ターン完了後に
  会話の `messages`(Msg[]) を PUT 保存し、サイドバー一覧から選んで復元する。
- **見学申込のキャンセル**はソフト取消（`status="cancelled"`）。UI ボタン
  （`POST /api/visit-requests/{id}/cancel`）とチャット（`cancel_visit_request` ツール）の両対応。

## ディレクトリ

```
backend/
  app/
    main.py            FastAPI 本体・CORS・ルーター登録
    config.py          環境変数
    db.py              インメモリ store（seed 読込・検索スコアリング含む）
    models.py          Pydantic モデル
    security.py        パスワードハッシュ(pbkdf2)・トークン
    auth.py            認証依存（Bearer トークン）
    seed/kindergartens.json  架空の幼稚園データ(15件)
    agent/
      prompts.py       司令塔/各サブエージェントのシステムプロンプト
      tools.py         @tool 定義 + build_kg_server()（インプロセス MCP）
      subagents.py     AgentDefinition(recommender, visit-coordinator)
      runner.py        ClaudeAgentOptions 構築 + query() ストリーム変換
    routers/           auth / users / favorites / chat
  requirements.txt
frontend/
  src/
    api/{client.ts, chatStream.ts}   fetch ラッパ / NDJSON ストリーム読取
    auth/{AuthContext, LoginPage, RequireAuth}
    components/{Nav, KindergartenCard, ChatMessage}
    pages/{ChatPage, FavoritesPage, ProfilePage}
    App.tsx / main.tsx / styles.css / types.ts
.claude/rules/         開発ルール（アーキテクチャ / エージェント開発 / スコープ）
```

## 起動方法

### バックエンド（:8000）
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # PowerShell（bash は source .venv/Scripts/activate）
pip install -r requirements.txt
copy .env.example .env            # 値を編集（最低限 ANTHROPIC_API_KEY か CLAUDE_CODE_PATH）
python run.py                     # 起動ランチャー（Windowsでは必須。下記「重要」参照）
```

> **重要（Windows / イベントループ）**: 起動は `python run.py` を使う。`uvicorn ... --reload` で
> 直接起動すると、SDK が `claude` CLI をサブプロセス起動できず `CLIConnectionError:
> "Failed to start Claude Code:"`（実体は SelectorEventLoop での `NotImplementedError`）になる。
> Windows の asyncio サブプロセス生成には **ProactorEventLoop** が必要で、[run.py](backend/run.py) は
> `asyncio.run(server.serve(), loop_factory=asyncio.ProactorEventLoop)` で Proactor ループ上に
> uvicorn を載せる（Python 3.14 で非推奨の `set_event_loop_policy` を避けるため `loop_factory` を使用）。
> ホットリロードは未対応（同じループ制約）。コード変更は手動で再起動して反映する。

### フロントエンド（:5173）
```bash
cd frontend
npm install
npm run dev
```
ブラウザで http://localhost:5173 を開き、デモアカウント **`demo` / `demo`**（または `taro` / `taro`）でログイン。

## エージェント実行の前提（重要）

チャット（`/api/chat`）は Claude Agent SDK が Claude Code CLI をサブプロセスとして起動する。

- **実行バイナリ**: この SDK バージョンは Windows で npm の `claude.cmd` シムを拒否し、
  **ネイティブ `claude.exe`** を要求する。導入は PowerShell で
  `irm https://claude.ai/install.ps1 | iex`、または環境変数 `CLAUDE_CODE_PATH` に
  `claude.exe` のフルパスを設定する（`config.py` が `cli_path` へ渡す）。
- **認証**: `ANTHROPIC_API_KEY` を設定するか、ネイティブ CLI にログイン済みであること。
- 未設定でもチャット**以外**（ログイン／プロフィール／お気に入り／幼稚園データ）は動作する。
  チャットは失敗時に `error` イベントを UI に返す（ハングしない）。

## 環境変数（backend/.env）

| 変数 | 既定 | 説明 |
|---|---|---|
| `ANTHROPIC_API_KEY` | （なし） | エージェント用 API キー |
| `CLAUDE_CODE_PATH` | （なし） | ネイティブ `claude.exe` のパス（任意・上記の代替） |
| `KG_MAIN_MODEL` | `sonnet` | 司令塔のモデル（`opus` 等も可） |
| `KG_SUB_MODEL` | `sonnet` | サブエージェントのモデル |
| `KG_CORS_ORIGINS` | `http://localhost:5173,...` | CORS 許可オリジン |
| `KG_MAX_TURNS` | `20` | 1 リクエストの最大ターン数 |

モデルはエイリアス（`sonnet`/`opus`/`haiku`）推奨。参考の完全 ID: `claude-opus-5` /
`claude-sonnet-5` / `claude-haiku-4-5-20251001`。

## マルチエージェント設計

- **司令塔（メイン）**: 会話・ヒアリングを行い、Agent ツールで 2 体のサブエージェントへ委譲。
  検索/申込の実務は自分で行わず委譲する。見学申込のような確定操作は**実行前にユーザーへ確認**。
- **recommender**: `search_kindergartens` などで候補を取得し、ランク付けして返す。`WebSearch` 併用可。
- **visit-coordinator**: `add_favorite` / `submit_visit_request` などでお気に入り・見学申込を実行。
- サブエージェントの内部ツール実行は SDK により親ストリームへ転送され、UI に稼働状況チップとして表示される。

## ストリーミングイベント契約（NDJSON, 1 行 1 JSON）

`text` / `tool_use`(label,agent) / `cards`(items:Kindergarten[]) / `favorite`(action,id,name) /
`visit`(confirmation_id,...) / `notice`(text) / `done`(session_id,cost_usd) / `error`(message)。
`cards`/`favorite`/`visit` は MCP ツールが `ui_queue` に push した構造化イベント。

## エージェントが使えるツール（`mcp__kg__*`）

`search_kindergartens` / `get_kindergarten` / `get_user_profile` / `add_favorite` /
`remove_favorite` / `list_favorites` / `submit_visit_request`。加えて組み込みの `WebSearch` を許可。
`can_use_tool`（`runner.py`）が許可リスト外（Bash/Write 等）を拒否する。

## 重要ルール（詳細は .claude/rules/）

- UI・エージェント応答は**日本語**を既定とする。
- **DB はインメモリ**。永続化しない（再起動で seed に戻る）。
- **見学申込は外部送信しない**。`visit_requests` へのローカル記録＋確認番号発行のみ（シミュレーション）。
- 認証は**簡易**（学習用）。本番強度ではない。
- 秘密情報（`.env`）はコミットしない。
- ツール/サブエージェントの追加手順は `.claude/rules/agent-development.md` を参照。

## レビュー運用（Codex）

実装は Claude Code（メインスレッド）が行い、**品質ゲートとして OpenAI Codex CLI にレビューを委ねる**。

- 実行: Claude Code で `/codex-review` を実行（未コミット変更をレビュー。`base=<ブランチ>` /
  `commit=<SHA>` で対象指定も可）。
- 中身: `.claude/commands/codex-review.md` が `codex exec review --uncommitted` を呼び、
  レビュー観点は `.claude/codex-review-prompt.md`（＋ `CLAUDE.md` / `.claude/rules/*`）を渡す。
  特に**ストリーミング契約(NDJSON)の backend↔frontend 同期崩れ**を重点検出する。
- 前提: `git` 管理下であること、Codex CLI 導入（`npm install -g @openai/codex`）＋
  `codex login`（ChatGPT サインイン）済みであること。Codex はレビューのみで、修正は Claude が行う。
