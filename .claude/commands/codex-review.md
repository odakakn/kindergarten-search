---
description: 現在の変更を OpenAI Codex CLI でコードレビューする
argument-hint: "[対象: 省略=未コミット変更 / base=<ブランチ> / commit=<SHA>]"
allowed-tools: Bash(codex:*), Bash(git status:*), Bash(git diff:*)
---

OpenAI Codex CLI の `review` サブコマンドで、現在の変更を別モデルの独立した目でレビューします。

対象指定: $ARGUMENTS （空なら未コミットの変更 = staged/unstaged/untracked すべて）

## 手順

1. `git status --short` で変更範囲を確認する。変更が無ければ「レビュー対象の変更がありません」と伝えて終了。

2. 次を実行してレビューを取得する。`review` サブコマンドは既定でサンドボックス実行され、
   コードを書き換えない。カスタム観点（ルーブリック）を PROMPT で渡すと、対象は既定で
   **未コミット変更（staged/unstaged/untracked）**になる:

   ```bash
   codex exec review "$(cat .claude/codex-review-prompt.md)"
   ```

   - 重要: `--uncommitted` / `--base` / `--commit` はカスタム PROMPT と**併用できない**
     （`error: the argument '--uncommitted' cannot be used with '[PROMPT]'`）。
     このため通常はフラグ無しで PROMPT のみを渡す（＝未コミット変更が対象）。
   - `$ARGUMENTS` で対象を変えたい場合（ルーブリックは Codex 組み込みのレビュー観点に切替）:
     - `base=<ブランチ>` → `codex exec review --base <ブランチ>`
     - `commit=<SHA>` → `codex exec review --commit <SHA>`
   - 認証エラーで失敗する場合は、ユーザーに `codex login`（ChatGPT サインイン）を促す。
     `codex` が未検出の場合は `npm install -g @openai/codex` を促す。

3. Codex の出力（深刻度別の指摘）をそのままユーザーに提示する。
   Critical / High の指摘があれば要約し、修正方針を添える。指摘なしならその旨を明確に伝える。

## 注意
- Codex 実行は OpenAI 側の利用枠/課金を消費する。
- このコマンドはレビューのみ。コードの修正は Codex ではなくメインスレッド（Claude）が行う。
- 前提: `git` 管理下であること、`codex login` 済みであること。
