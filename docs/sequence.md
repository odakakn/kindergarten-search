# シーケンス図: チャット受付〜応答完了

クライアントのメッセージ送信から応答完了までの、
**クライアント ⇔ バックエンド(Agent/REST) ⇔ Claude CLI ⇔ MCP ⇔ LLM** 間の通信フロー。

- **Backend と MCP(kg) は同一プロセス**（インプロセス MCP。`store` / `ui_queue` を共有）
- **Claude CLI（`claude.exe`）は別サブプロセス**（SDK が起動、stdio で通信）
- **Anthropic API（LLM）はリモート**（呼ぶのは CLI）

```mermaid
sequenceDiagram
    autonumber
    actor U as ユーザー
    participant C as クライアント<br/>(React ChatPage)
    participant B as バックエンド<br/>(FastAPI / runner.query)
    participant M as MCP "kg" ツール<br/>(インプロセス / tools.py)
    participant CLI as Claude CLI<br/>(claude.exe 別プロセス)
    participant LLM as Anthropic API (LLM)

    Note over B,M: B と M は同一プロセス<br/>(store / ui_queue を共有)

    U->>C: メッセージ送信
    opt currentId が無い(新規会話)
        C->>B: POST /api/conversations
        B->>B: store.create_conversation(uid)
        B-->>C: { id } = conversation_id
    end

    C->>B: POST /api/chat { message, conversation_id }<br/>(fetch: NDJSON ストリーム開始)
    B->>B: 会話の所有チェック / get_conv_session→resume
    B->>B: _build_options(system_prompt, agents,<br/>mcp_servers=kg, resume, model)
    B->>CLI: query(prompt, options) でサブプロセス起動<br/>(stdio・resume で過去履歴を投入)
    CLI-->>B: SystemMessage(init){session_id}
    B->>B: set_conv_session(cid, session_id)

    loop 応答が完了するまで(1〜複数ターン)
        CLI->>LLM: プロンプト＋ツール定義を送信
        LLM-->>CLI: assistant(text / tool_use) をストリーム

        alt テキスト
            CLI-->>B: AssistantMessage(TextBlock)
            B-->>C: {"type":"text"}  → 吹き出しに追記
        else サブエージェント委譲(Agent/Task)
            CLI-->>B: AssistantMessage(ToolUseBlock: Agent)
            B-->>C: {"type":"tool_use", agent}
            CLI->>LLM: recommender / visit-coordinator を実行(別LLMループ)
        else MCP ツール呼び出し(mcp__kg__*)
            Note over CLI,M: allowed_tools 済みの kg ツールは自動許可<br/>(許可外=Bash等は can_use_tool が拒否)
            CLI->>M: tools/call (SDK制御チャネル経由でインプロセスへブリッジ)
            M->>M: store を参照/更新
            M-->>B: ui_queue に cards/favorite/visit を push
            M-->>CLI: ツール結果(JSON) を返す
            B-->>C: {"type":"tool_use"} ＋ drain_queue で<br/>{"type":"cards"/"favorite"/"visit"}
            C->>C: 稼働チップ＋カードを描画
        end
    end

    CLI-->>B: ResultMessage(session_id, subtype=success)
    B->>B: set_conv_session(cid, session_id)
    B-->>C: {"type":"done"}
    C->>C: streaming=false(入力再開・チップを✓)
    B-->>C: HTTP ストリーム終了

    Note over C,B: ターン完了後にフロントが会話を保存
    C->>B: PUT /api/conversations/{id} { messages, title }
    B->>B: store.save_conversation(...)
    B-->>C: 200 → サイドバー(履歴)を更新
```

## 図の読みどころ（対応コード）

- **受付**: `C: runChat` → `POST /api/chat`（`frontend/src/api/chatStream.ts`）→ `backend/app/routers/chat.py` → `stream_chat`。
- **LLM 実行の起点**: `backend/app/agent/runner.py` の `async for msg in query(...)`。ここで CLI が起動し、CLI が LLM と会話する。私たちの Python は直接 API を叩かない。
- **MCP は CLI がクライアント**: `mcp__kg__*` は CLI が要求 → SDK 制御チャネルで **同一プロセス内** の `M`（`backend/app/agent/tools.py`）へブリッジ実行（ネットワーク無し）。`M` は `store` を直接操作し、`ui_queue` にカード等を push する。
- **2 系統の合流**: `B` は「SDK メッセージ（text/tool_use/done）」と「ui_queue（cards/favorite/visit）」を各メッセージ後の `drain_queue` で 1 本の NDJSON にまとめて `C` へ送出する（`.claude/rules/architecture.md` のストリーミング契約）。
- **セッション継続**: `init` と `ResultMessage` で `set_conv_session`。次ターンは `resume` で履歴を LLM に再投入する。
- **履歴保存**: 応答完了後に `C` が `PUT /api/conversations/{id}`（UI 用 `Msg[]`）で保存。これは**表示復元用**で、LLM の記憶は `resume`（session_id）側が担う、という二層構造。

## 補足

- サブエージェント（`recommender` / `visit-coordinator`）は CLI が内部で別の LLM ループとして実行する。その中の `mcp__kg__*` 実行も同じ `M` に届き、親ストリームへ転送されて `agent` ラベル付きの稼働チップとして `C` に表示される。
- `ResultMessage`（= `done`）は、サブエージェントのバックグラウンド継続により **1 リクエストで複数回**現れることがある。フロントは各 `done` で busy 状態を解除する。
