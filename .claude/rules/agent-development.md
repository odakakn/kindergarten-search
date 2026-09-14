# ルール: エージェント開発

## ツールの追加手順（`app/agent/tools.py`）
1. `build_kg_server` 内で `@tool(name, description, input_schema)` を定義する。
   - **任意パラメータがある場合は「完全な JSON Schema」**（`{"type":"object","properties":{...},"required":[...]}`）
     を渡す。単純な `{"key": type}` 形式は **全項目 required** になる（SDK 仕様）。
   - ハンドラは `async def`。戻り値は `{"content": [{"type": "text", "text": ...}]}`。
     失敗時は `"is_error": True` を付ける。
   - データ操作は必ず束縛済み `user_id` を使う（引数の user_id は受け取らない）。
2. UI に構造化表示を出したい場合は `push({...})` で `ui_queue` にイベントを流す
   （`type` を決めたら frontend 側も対応させる）。
3. `create_sdk_mcp_server(..., tools=[...])` の配列と、モジュール末尾の `TOOL_NAMES` に追加する。
4. 使わせたいエージェントの許可に反映：
   - 司令塔は `runner._build_options` の `allowed_tools=TOOL_NAMES`（＋ `can_use_tool`）。
   - サブエージェントは `subagents.py` の該当 `AgentDefinition.tools` に
     `mcp__kg__<name>` を追加し、`mcpServers=["kg"]` を保つ。

## サブエージェントの追加（`app/agent/subagents.py`）
- `AgentDefinition(description, prompt, tools, mcpServers=["kg"], model=config.SUB_MODEL)` を
  `build_agents()` の dict に追加する。
- `description` は「いつ委譲すべきか」を司令塔が判断できるよう具体的に書く。
- プロンプトは `app/agent/prompts.py` に定義し、日本語で役割・使用ツール・出力形式を明示する。
- 司令塔プロンプト（`build_orchestrator_prompt`）にも新エージェントへの委譲方針を追記する。

## 命名・許可
- MCP ツールは常に `mcp__kg__<tool>`（サーバー名 `SERVER_NAME = "kg"`）。
- `runner._permission_gate` は許可リスト方式：`mcp__kg__*` と一部組み込み（WebSearch/WebFetch/Agent/Task）
  のみ許可、その他（Bash/Write 等）は拒否。新しく許可したい組み込みツールは `_ALLOWED_BUILTINS` に追加。

## ストリーム変換（`app/agent/runner.py`）
- 新しい `tool_use` のラベルは `_TOOL_LABELS` に追加。
- サブエージェント委譲は `Agent`/`Task` の tool_use で捕捉し、`parent_tool_use_id` で内部ツールに
  エージェント名を付与している。

## モデル
- 既定はエイリアス（`sonnet`）。`KG_MAIN_MODEL` / `KG_SUB_MODEL` で上書き可能。
