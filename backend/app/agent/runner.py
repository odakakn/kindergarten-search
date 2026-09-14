"""エージェント実行（Claude Agent SDK）とチャットストリームの生成。

司令塔（メイン）+ 2 サブエージェントを起動し、SDK のメッセージストリームを
フロント向けの UI イベント（dict）へ変換して逐次 yield する。
インプロセス MCP ツールが push した構造化イベント（cards/favorite/visit）は、
各メッセージの後に ui_queue から取り出して差し込む。
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    CLINotFoundError,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    ServerToolUseBlock,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from .. import config
from ..db import store
from .prompts import build_orchestrator_prompt
from .subagents import build_agents
from .tools import SERVER_NAME, TOOL_NAMES, build_kg_server

# エージェントに許可するツール（これ以外は can_use_tool で拒否）
_ALLOWED_BUILTINS = {
    "WebSearch",
    "web_search",
    "WebFetch",
    "web_fetch",
    "Agent",
    "Task",
    "TaskOutput",
    "ToolSearch",  # 遅延ツールのスキーマ探索（読み取り専用・無害）
}

_TOOL_LABELS = {
    "search_kindergartens": "幼稚園を検索中",
    "get_kindergarten": "幼稚園の詳細を確認中",
    "get_user_profile": "プロフィールを参照中",
    "add_favorite": "お気に入りに登録中",
    "remove_favorite": "お気に入りから削除中",
    "list_favorites": "お気に入りを確認中",
    "submit_visit_request": "見学を申し込み中",
    "list_visit_requests": "見学申込を確認中",
    "cancel_visit_request": "見学申込を取消中",
}


def _is_allowed(tool_name: str) -> bool:
    return tool_name.startswith(f"mcp__{SERVER_NAME}__") or tool_name in _ALLOWED_BUILTINS


async def _permission_gate(
    tool_name: str, tool_input: dict[str, Any], context: Any
) -> PermissionResultAllow | PermissionResultDeny:
    """許可リスト方式のツール許可ハンドラ（ヘッドレスでプロンプト待ちにしない）。"""
    if _is_allowed(tool_name):
        return PermissionResultAllow()
    return PermissionResultDeny(
        message=f"このアプリでは「{tool_name}」の使用は許可されていません。"
    )


def _subagent_of(tool_input: dict[str, Any]) -> str | None:
    for key in ("subagent_type", "agent_type", "agent"):
        val = tool_input.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def _tool_activity(name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """ToolUseBlock を UI 用の tool_use イベントへ変換する。"""
    if name in ("Agent", "Task"):
        sub = _subagent_of(tool_input)
        label = f"{sub} エージェントに委譲中" if sub else "サブエージェントに委譲中"
        return {"type": "tool_use", "tool": name, "agent": sub, "label": label}
    if name in ("WebSearch", "web_search"):
        return {"type": "tool_use", "tool": name, "label": "Web検索中"}
    suffix = name.split("__")[-1]
    return {"type": "tool_use", "tool": name, "label": _TOOL_LABELS.get(suffix, suffix)}


def _build_options(
    user_id: str, conversation_id: str, ui_queue: "asyncio.Queue[dict[str, Any]]"
) -> ClaudeAgentOptions:
    profile = store.get_profile(user_id)
    server = build_kg_server(user_id, ui_queue)
    session_id = store.get_conv_session(conversation_id)
    opts = ClaudeAgentOptions(
        system_prompt=build_orchestrator_prompt(profile),
        mcp_servers={SERVER_NAME: server},
        agents=build_agents(),
        allowed_tools=TOOL_NAMES,  # 主要 MCP ツールは事前許可（残りは can_use_tool が判定）
        can_use_tool=_permission_gate,
        permission_mode="default",
        model=config.MAIN_MODEL,
        max_turns=config.MAX_TURNS,
    )
    if session_id:
        opts.resume = session_id
    if config.CLAUDE_CODE_PATH:
        opts.cli_path = config.CLAUDE_CODE_PATH
    return opts


async def stream_chat(
    user_id: str, conversation_id: str, message: str
) -> AsyncIterator[dict[str, Any]]:
    """1 回のユーザー発話に対するエージェント応答を UI イベントとして逐次生成する。"""
    ui_queue: "asyncio.Queue[dict[str, Any]]" = asyncio.Queue()
    options = _build_options(user_id, conversation_id, ui_queue)

    # Agent ツールの tool_use_id -> サブエージェント名（委譲先の作業ラベル付け用）
    agent_by_tool_use: dict[str, str] = {}

    def drain_queue() -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while not ui_queue.empty():
            events.append(ui_queue.get_nowait())
        return events

    try:
        async for msg in query(prompt=message, options=options):
            if isinstance(msg, SystemMessage):
                if msg.subtype == "init":
                    sid = msg.data.get("session_id")
                    if sid:
                        store.set_conv_session(conversation_id, sid)

            elif isinstance(msg, AssistantMessage):
                parent = msg.parent_tool_use_id
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text = block.text.strip()
                        if text:
                            yield {"type": "text", "text": block.text}
                    elif isinstance(block, ToolUseBlock):
                        if block.name in ("Agent", "Task"):
                            sub = _subagent_of(block.input)
                            if sub:
                                agent_by_tool_use[block.id] = sub
                        event = _tool_activity(block.name, block.input)
                        # 委譲先サブエージェント内のツール実行にラベルを付ける
                        if parent and parent in agent_by_tool_use and not event.get("agent"):
                            event["agent"] = agent_by_tool_use[parent]
                        yield event
                    elif isinstance(block, ServerToolUseBlock):
                        yield _tool_activity(block.name, dict(block.input))

            elif isinstance(msg, ResultMessage):
                store.set_conv_session(conversation_id, msg.session_id)
                if msg.is_error or (msg.subtype and msg.subtype != "success"):
                    yield {
                        "type": "notice",
                        "text": f"（処理が途中で終了しました: {msg.subtype}）",
                    }
                yield {
                    "type": "done",
                    "session_id": msg.session_id,
                    "cost_usd": msg.total_cost_usd,
                    "subtype": msg.subtype,
                }

            for ev in drain_queue():
                yield ev

        for ev in drain_queue():
            yield ev

    except CLINotFoundError as exc:
        yield {
            "type": "error",
            "message": (
                "エージェント実行ファイル（ネイティブ版 claude.exe）が見つかりません。"
                "README の手順でネイティブ版 Claude Code を導入するか、環境変数 "
                "CLAUDE_CODE_PATH に claude.exe のパスを設定してください。"
            ),
            "detail": str(exc),
        }
    except Exception as exc:  # noqa: BLE001 - ストリームにエラーを流して UI に伝える
        yield {
            "type": "error",
            "message": (
                "エージェント実行中にエラーが発生しました。ANTHROPIC_API_KEY が未設定、"
                "または Claude Code にログインしていない可能性があります。"
            ),
            "detail": str(exc),
        }
