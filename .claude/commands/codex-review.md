---
description: OpenAI Codex CLI でコードレビューする（変更差分 or プロジェクト全体）
argument-hint: "[省略=未コミット変更 / all=全体 / base=<ブランチ> / commit=<SHA>]"
allowed-tools: Bash(codex:*), Bash(git status:*), Bash(git diff:*)
---

OpenAI Codex CLI で、コードを別モデルの独立した目でレビューします。
対象は `$ARGUMENTS` で切り替えます（省略時は未コミット変更）。

## モードの判定（$ARGUMENTS）

- 空 → **変更モード**（未コミット変更 = staged/unstaged/untracked）
- `all` / `full` / `project` → **全体モード**（リポジトリ全体のソース）
- `base=<ブランチ>` → 指定ブランチとの差分（Codex 組み込み観点）
- `commit=<SHA>` → 指定コミットの変更（Codex 組み込み観点）

## 手順

### A. 変更モード（既定）

1. `git status --short` で変更範囲を確認。変更が無ければ「レビュー対象の変更がありません」と伝えて終了。
2. 次を実行（`review` は既定でサンドボックス実行・コードを書き換えない。カスタム観点を PROMPT で
   渡すと対象は既定で未コミット変更になる）:

   ```bash
   codex exec review "$(cat .claude/codex-review-prompt.md)"
   ```

   - 重要: `--uncommitted` / `--base` / `--commit` はカスタム PROMPT と**併用できない**
     （`error: the argument '--uncommitted' cannot be used with '[PROMPT]'`）。
     通常はフラグ無しで PROMPT のみを渡す。
   - `base=<ブランチ>` / `commit=<SHA>` 指定時は `codex exec review --base <ブランチ>` /
     `--commit <SHA>`（この場合カスタムルーブリックは付かず、Codex 組み込み観点になる）。

### B. 全体モード（`all` / `full` / `project`）

差分ではなくリポジトリ全体を対象にする。`review` サブコマンドは差分特化なので、読み取り専用の
`codex exec` でリポジトリを読ませる:

```bash
codex exec --sandbox read-only "リポジトリ全体をレビュー対象とする。backend/app 配下(Python/FastAPI)と frontend/src 配下(React/TS)の主要ソースを網羅的に読み、下記の観点でレビューせよ。__pycache__ / .venv / node_modules / dist / *.pyc / package-lock.json などの生成物・依存物は対象外。

$(cat .claude/codex-review-prompt.md)"
```

## 共通

- 認証エラーで失敗する場合は `codex login`（ChatGPT サインイン）を、`codex` 未検出の場合は
  `npm install -g @openai/codex` をユーザーに促す。
- Codex の出力（深刻度別の指摘）をそのまま提示し、Critical / High があれば要約して修正方針を添える。
  指摘なしならその旨を明確に伝える。
- 全体モードは読み込むファイルが多く、時間と OpenAI 利用枠を多めに消費する点に留意する。

## 注意
- Codex 実行は OpenAI 側の利用枠/課金を消費する。
- このコマンドはレビューのみ。コードの修正は Codex ではなくメインスレッド（Claude）が行う。
- 前提: `git` 管理下であること、`codex login` 済みであること。
