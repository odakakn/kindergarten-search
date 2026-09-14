# 🌷 幼稚園さがしコンシェルジュ

自分にピッタリの幼稚園を探すための、チャット型 AI エージェント Web アプリ（学習用）。

- **相談チャット**: 希望条件を伝えると、マルチエージェントが幼稚園をレコメンドし、
  そのままお気に入り登録・見学申込まで代行します。**左サイドバーで過去の会話を保存・切替**でき、
  リロードしても履歴から戻れます（「＋ 新しいチャット」で新規開始）。
- **お気に入り**: 気に入った園をリストで管理。見学申込の履歴も確認でき、**「キャンセル」ボタンで取消**できます
  （チャットで「〇〇の見学を取り消して」と依頼してもOK）。
- **プロフィール**: ユーザー属性を登録。レコメンドのコンテキストとして使われます。
- **ログイン**: 簡易な ID/PW 認証。

## 技術スタック

| レイヤ | 技術 |
|---|---|
| フロントエンド | React + Vite + TypeScript（:5173） |
| バックエンド | Python + FastAPI（:8000）、DB はインメモリ |
| エージェント | Claude Agent SDK（司令塔 + サブエージェント 2 体、Agent/Task ツールで委譲） |
| ツール公開 | インプロセス MCP サーバー（`create_sdk_mcp_server`）＋ 組み込み `WebSearch` |

詳細な設計は [CLAUDE.md](CLAUDE.md) と [.claude/rules/](.claude/rules/) を参照。

## セットアップ

### 1. バックエンド（:8000）
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # bash の場合: source .venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env               # 値を編集
python run.py                        # ← uvicorn --reload では起動しないこと（下記参照）
```

> **重要（Windows）**: 起動は必ず `python run.py` を使ってください。`uvicorn app.main:app --reload`
> だと、エージェントが `claude` CLI をサブプロセス起動できず「Failed to start Claude Code」で
> 失敗します。原因は asyncio のイベントループで、Windows のサブプロセス生成には
> **ProactorEventLoop** が必要ですが `--reload` 時は SelectorEventLoop になり得るためです。
> `run.py` は Proactor ループ上で uvicorn を起動します。
> なお **ホットリロードは未対応**（同じループ制約のため）なので、コードを変更したら手動で
> 再起動してください。

### 2. フロントエンド（:5173）
```bash
cd frontend
npm install
npm run dev
```

### 3. アクセス
http://localhost:5173 を開き、デモアカウントでログイン:

- `demo` / `demo`（プロフィール設定済み）
- `taro` / `taro`

## エージェントを動かすための前提

相談チャットは Claude Agent SDK が Claude Code CLI をサブプロセスとして起動します。次のいずれかが必要です。

1. `backend/.env` に `ANTHROPIC_API_KEY` を設定する、**または**
2. ネイティブ版 Claude Code にログイン済みであること。

さらに **Windows ではネイティブ `claude.exe`** が必要です（npm の `claude.cmd` シムは SDK に拒否されます）。
未導入の場合は PowerShell で:
```powershell
irm https://claude.ai/install.ps1 | iex
```
別の場所の `claude.exe` を使う場合は `backend/.env` の `CLAUDE_CODE_PATH` にフルパスを設定します。

> これらが未設定でも、**ログイン／プロフィール／お気に入り／幼稚園データの閲覧**は動作します。
> チャットのみ、実行できない場合はエラーメッセージを表示します（ハングしません）。

## 使い方の例

1. プロフィールでお子さんの年齢・エリア・予算・重視点を設定。
2. 相談チャットで「世田谷区で英語教育に力を入れている園を、月4万円まで探して」などと入力。
3. `recommender` エージェントが候補カードを提示（おすすめ理由つき）。
4. 気に入った園の ♡ でお気に入り登録、または「見学を相談する」から見学申込。
5. 見学申込は司令塔が内容を確認してから `visit-coordinator` が受付（**ローカル記録のみ・外部送信なし**）。
6. お気に入りページで登録済みの園と見学申込履歴を確認。

## 注意（学習用のスコープ）

- 幼稚園データは**架空**（`backend/app/seed/kindergartens.json`）。
- DB は**インメモリ**（再起動で初期化）。
- 見学申込は**シミュレーション**（外部送信しない）。
- 認証は簡易実装で**本番強度ではありません**。
