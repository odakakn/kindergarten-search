"""エージェントが利用するツールを公開するインプロセス MCP サーバー。

``build_kg_server(user_id, ui_queue)`` はリクエスト単位で呼び出され、
各ツールのクロージャに「認証済み user_id」と「UI 用イベントキュー」を束縛する。
- user_id 束縛により、エージェントはログイン中ユーザーのデータしか操作できない
  （モデル入力に user_id を晒さない）。
- ui_queue には検索結果カードやお気に入り/見学申込の構造化イベントを流し、
  ランナーがチャットストリームへ差し込む（フロントのリッチ表示用）。
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from ..db import store

SERVER_NAME = "kg"


def _kg_summary(kg: dict[str, Any]) -> dict[str, Any]:
    """モデルに渡す用の主要フィールド（トークン節約のため要約）。"""
    return {
        "id": kg["id"],
        "name": kg["name"],
        "area": kg["area"],
        "nearest_station": kg["nearest_station"],
        "monthly_fee": kg["monthly_fee"],
        "age_range": f"{kg['min_age']}〜{kg['max_age']}歳",
        "features": kg["features"],
        "has_bus": kg["has_bus"],
        "extended_care": kg["extended_care"],
        "education_style": kg["education_style"],
        "match_score": kg.get("match_score"),
        "match_reasons": kg.get("match_reasons", []),
    }


def build_kg_server(user_id: str, ui_queue: "asyncio.Queue[dict[str, Any]]") -> McpSdkServerConfig:
    """user_id と ui_queue を束縛した MCP サーバー設定を生成する。"""

    def push(event: dict[str, Any]) -> None:
        try:
            ui_queue.put_nowait(event)
        except Exception:
            pass  # UI 通知は best-effort（失敗してもツール自体は成功させる）

    @tool(
        "search_kindergartens",
        "希望条件で幼稚園を検索し、条件との合致度でランク付けした候補を返す。すべての条件は任意。",
        {
            "type": "object",
            "properties": {
                "area": {"type": "string", "description": "エリア（例: 世田谷区）"},
                "max_fee": {"type": "integer", "description": "月額上限（円）"},
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "希望する特徴タグ（例: 英語教育, 預かり保育, 送迎バス, モンテッソーリ, 自然体験, 音楽教育 など）",
                },
                "child_age": {"type": "integer", "description": "子どもの年齢（歳）"},
                "needs_bus": {"type": "boolean", "description": "送迎バスが必要か"},
                "education_style": {
                    "type": "string",
                    "description": "教育方針（のびのび系 / お勉強系 / バランス型 / モンテッソーリ）",
                },
                "extended_care": {"type": "boolean", "description": "預かり保育が必要か"},
                "keyword": {"type": "string", "description": "フリーワード検索"},
                "limit": {"type": "integer", "description": "返す件数（デフォルト5）"},
            },
            "required": [],
        },
    )
    async def search_kindergartens(args: dict[str, Any]) -> dict[str, Any]:
        limit = int(args.get("limit") or 5)
        results = store.search(args, limit=limit)
        # UI 用カードには全フィールド（match_score/match_reasons 込み）を渡す。
        push({"type": "cards", "source": "search", "items": results})
        # モデルに返す本文は要約（トークン節約）。
        summaries = [_kg_summary(kg) for kg in results]
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"results": summaries}, ensure_ascii=False),
                }
            ]
        }

    @tool(
        "get_kindergarten",
        "指定した幼稚園の詳細情報を取得する。",
        {
            "type": "object",
            "properties": {"kindergarten_id": {"type": "string"}},
            "required": ["kindergarten_id"],
        },
    )
    async def get_kindergarten(args: dict[str, Any]) -> dict[str, Any]:
        kg = store.get_kindergarten(args["kindergarten_id"])
        if not kg:
            return {
                "content": [{"type": "text", "text": "指定された幼稚園が見つかりませんでした。"}],
                "is_error": True,
            }
        return {"content": [{"type": "text", "text": json.dumps(kg, ensure_ascii=False)}]}

    @tool(
        "get_user_profile",
        "現在のユーザー（ログイン中の保護者）の属性プロフィールを取得する。",
        {"type": "object", "properties": {}, "required": []},
    )
    async def get_user_profile(args: dict[str, Any]) -> dict[str, Any]:
        profile = store.get_profile(user_id)
        return {"content": [{"type": "text", "text": json.dumps(profile, ensure_ascii=False)}]}

    @tool(
        "add_favorite",
        "指定した幼稚園を現在のユーザーのお気に入りに登録する。",
        {
            "type": "object",
            "properties": {"kindergarten_id": {"type": "string"}},
            "required": ["kindergarten_id"],
        },
    )
    async def add_favorite(args: dict[str, Any]) -> dict[str, Any]:
        kid = args["kindergarten_id"]
        ok = store.add_favorite(user_id, kid)
        if not ok:
            return {
                "content": [{"type": "text", "text": "その幼稚園は見つかりませんでした。"}],
                "is_error": True,
            }
        kg = store.get_kindergarten(kid)
        name = kg["name"] if kg else kid
        push({"type": "favorite", "action": "added", "id": kid, "name": name})
        return {"content": [{"type": "text", "text": f"「{name}」をお気に入りに登録しました。"}]}

    @tool(
        "remove_favorite",
        "指定した幼稚園を現在のユーザーのお気に入りから削除する。",
        {
            "type": "object",
            "properties": {"kindergarten_id": {"type": "string"}},
            "required": ["kindergarten_id"],
        },
    )
    async def remove_favorite(args: dict[str, Any]) -> dict[str, Any]:
        kid = args["kindergarten_id"]
        store.remove_favorite(user_id, kid)
        kg = store.get_kindergarten(kid)
        name = kg["name"] if kg else kid
        push({"type": "favorite", "action": "removed", "id": kid, "name": name})
        return {"content": [{"type": "text", "text": f"「{name}」をお気に入りから削除しました。"}]}

    @tool(
        "list_favorites",
        "現在のユーザーのお気に入り幼稚園の一覧を取得する。",
        {"type": "object", "properties": {}, "required": []},
    )
    async def list_favorites(args: dict[str, Any]) -> dict[str, Any]:
        favs = [_kg_summary(kg) for kg in store.list_favorites(user_id)]
        return {"content": [{"type": "text", "text": json.dumps({"favorites": favs}, ensure_ascii=False)}]}

    @tool(
        "submit_visit_request",
        "見学申込をこのアプリ内に登録し、確認番号を発行する（外部送信はしない）。",
        {
            "type": "object",
            "properties": {
                "kindergarten_id": {"type": "string"},
                "preferred_dates": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "見学希望日（例: 2026-10-01）",
                },
                "applicant_note": {"type": "string", "description": "備考・伝達事項"},
            },
            "required": ["kindergarten_id", "preferred_dates"],
        },
    )
    async def submit_visit_request(args: dict[str, Any]) -> dict[str, Any]:
        record = store.add_visit_request(
            user_id,
            args["kindergarten_id"],
            list(args.get("preferred_dates") or []),
            str(args.get("applicant_note") or ""),
        )
        if not record:
            return {
                "content": [{"type": "text", "text": "その幼稚園は見つかりませんでした。"}],
                "is_error": True,
            }
        push(
            {
                "type": "visit",
                "confirmation_id": record["confirmation_id"],
                "id": record["kindergarten_id"],
                "name": record["kindergarten_name"],
                "preferred_dates": record["preferred_dates"],
                "applicant_note": record["applicant_note"],
            }
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "message": "見学申込を受け付けました（アプリ内のローカル記録です）。",
                            "confirmation_id": record["confirmation_id"],
                            "kindergarten_name": record["kindergarten_name"],
                            "preferred_dates": record["preferred_dates"],
                        },
                        ensure_ascii=False,
                    ),
                }
            ]
        }

    @tool(
        "list_visit_requests",
        "現在のユーザーの見学申込一覧（確認番号・園名・希望日・状態）を取得する。",
        {"type": "object", "properties": {}, "required": []},
    )
    async def list_visit_requests(args: dict[str, Any]) -> dict[str, Any]:
        items = [
            {
                "confirmation_id": r["confirmation_id"],
                "kindergarten_id": r["kindergarten_id"],
                "kindergarten_name": r["kindergarten_name"],
                "preferred_dates": r["preferred_dates"],
                "status": r["status"],
            }
            for r in store.list_visit_requests(user_id)
        ]
        return {"content": [{"type": "text", "text": json.dumps({"visit_requests": items}, ensure_ascii=False)}]}

    @tool(
        "cancel_visit_request",
        "指定した確認番号の見学申込を取り消す（status を cancelled にする）。",
        {
            "type": "object",
            "properties": {"confirmation_id": {"type": "string"}},
            "required": ["confirmation_id"],
        },
    )
    async def cancel_visit_request(args: dict[str, Any]) -> dict[str, Any]:
        rec = store.cancel_visit_request(user_id, args["confirmation_id"])
        if not rec:
            return {
                "content": [{"type": "text", "text": "その確認番号の見学申込が見つかりませんでした。"}],
                "is_error": True,
            }
        push(
            {
                "type": "visit_cancel",
                "confirmation_id": rec["confirmation_id"],
                "id": rec["kindergarten_id"],
                "name": rec["kindergarten_name"],
                "status": rec["status"],
            }
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "message": "見学申込を取り消しました。",
                            "confirmation_id": rec["confirmation_id"],
                            "kindergarten_name": rec["kindergarten_name"],
                            "status": rec["status"],
                        },
                        ensure_ascii=False,
                    ),
                }
            ]
        }

    return create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            search_kindergartens,
            get_kindergarten,
            get_user_profile,
            add_favorite,
            remove_favorite,
            list_favorites,
            submit_visit_request,
            list_visit_requests,
            cancel_visit_request,
        ],
    )


# allowed_tools / can_use_tool 用の完全修飾ツール名
TOOL_NAMES = [
    f"mcp__{SERVER_NAME}__search_kindergartens",
    f"mcp__{SERVER_NAME}__get_kindergarten",
    f"mcp__{SERVER_NAME}__get_user_profile",
    f"mcp__{SERVER_NAME}__add_favorite",
    f"mcp__{SERVER_NAME}__remove_favorite",
    f"mcp__{SERVER_NAME}__list_favorites",
    f"mcp__{SERVER_NAME}__submit_visit_request",
    f"mcp__{SERVER_NAME}__list_visit_requests",
    f"mcp__{SERVER_NAME}__cancel_visit_request",
]
