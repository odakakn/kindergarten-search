"""ユーザー本人情報とプロフィール（属性）管理。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import get_current_user_id
from ..db import store
from ..models import Profile, ProfileUpdate, UserPublic

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def get_me(uid: str = Depends(get_current_user_id)) -> UserPublic:
    return UserPublic(**store.public_user(uid))


@router.get("/profile", response_model=Profile)
async def get_profile(uid: str = Depends(get_current_user_id)) -> Profile:
    return Profile(**store.get_profile(uid))


@router.put("/profile", response_model=Profile)
async def update_profile(
    body: ProfileUpdate, uid: str = Depends(get_current_user_id)
) -> Profile:
    # None のフィールドは更新対象外（部分更新）
    updated = store.update_profile(uid, body.model_dump(exclude_none=True))
    return Profile(**updated)
