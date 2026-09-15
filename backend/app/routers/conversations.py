"""チャット履歴（会話）の CRUD。会話はサーバ側インメモリに保持する。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user_id
from ..db import store
from ..models import ConversationDetail, ConversationSummary, SaveConversationRequest

router = APIRouter(prefix="/api", tags=["conversations"])


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(uid: str = Depends(get_current_user_id)) -> list[ConversationSummary]:
    return [ConversationSummary(**c) for c in store.list_conversations(uid)]


@router.post("/conversations", response_model=ConversationDetail)
async def create_conversation(uid: str = Depends(get_current_user_id)) -> ConversationDetail:
    conv = store.create_conversation(uid)
    return ConversationDetail(id=conv["id"], title=conv["title"], messages=conv["messages"])


@router.get("/conversations/{cid}", response_model=ConversationDetail)
async def get_conversation(cid: str, uid: str = Depends(get_current_user_id)) -> ConversationDetail:
    conv = store.get_conversation(uid, cid)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会話が見つかりません")
    return ConversationDetail(id=conv["id"], title=conv["title"], messages=conv["messages"])


@router.put("/conversations/{cid}", response_model=ConversationSummary)
async def save_conversation(
    cid: str,
    body: SaveConversationRequest,
    uid: str = Depends(get_current_user_id),
) -> ConversationSummary:
    conv = store.save_conversation(uid, cid, body.messages, body.title)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会話が見つかりません")
    return ConversationSummary(
        id=conv["id"],
        title=conv["title"],
        updated_at=conv["updated_at"],
        message_count=len(conv["messages"]),
    )


@router.delete("/conversations/{cid}")
async def delete_conversation(cid: str, uid: str = Depends(get_current_user_id)) -> dict:
    if not store.delete_conversation(uid, cid):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会話が見つかりません")
    return {"ok": True}
