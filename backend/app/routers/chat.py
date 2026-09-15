"""幼稚園検索〜見学申込エージェントのチャットエンドポイント（ストリーミング）。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ..agent.runner import stream_chat
from ..auth import get_current_user_id
from ..db import store
from ..models import ChatRequest

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(body: ChatRequest, uid: str = Depends(get_current_user_id)) -> StreamingResponse:
    """ユーザー発話を受け取り、エージェントの応答を NDJSON で逐次ストリームする。

    各行は 1 つの JSON イベント:
    ``text`` / ``tool_use`` / ``cards`` / ``favorite`` / ``visit`` / ``visit_cancel`` /
    ``notice`` / ``done`` / ``error``。
    """
    if not store.get_conversation(uid, body.conversation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会話が見つかりません")

    async def generate():
        async for event in stream_chat(uid, body.conversation_id, body.message):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
