"""ログイン / ログアウト。"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from ..db import store
from ..models import LoginRequest, LoginResponse

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    uid = store.authenticate(body.username, body.password)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
        )
    token = store.issue_token(uid)
    return LoginResponse(token=token, user=store.public_user(uid))  # type: ignore[arg-type]


@router.post("/logout")
async def logout(authorization: str | None = Header(default=None)) -> dict:
    if authorization and authorization.lower().startswith("bearer "):
        store.revoke_token(authorization.split(" ", 1)[1].strip())
    return {"ok": True}
