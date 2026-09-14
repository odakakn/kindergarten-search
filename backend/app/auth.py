"""認証ユーティリティと FastAPI 依存関数。"""
from __future__ import annotations

from fastapi import Header, HTTPException, status

from .db import store


async def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    """``Authorization: Bearer <token>`` を検証し user_id を返す依存関数。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
        )
    token = authorization.split(" ", 1)[1].strip()
    uid = store.user_for_token(token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンが無効です",
        )
    return uid
