"""お気に入り一覧と、参照用の幼稚園エンドポイント。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user_id
from ..db import store
from ..models import Kindergarten, VisitRequestRecord

router = APIRouter(prefix="/api", tags=["favorites"])


@router.get("/kindergartens", response_model=list[Kindergarten])
async def list_kindergartens() -> list[Kindergarten]:
    return [Kindergarten(**kg) for kg in store.all_kindergartens()]


@router.get("/kindergartens/{kid}", response_model=Kindergarten)
async def get_kindergarten(kid: str) -> Kindergarten:
    kg = store.get_kindergarten(kid)
    if not kg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見つかりません")
    return Kindergarten(**kg)


@router.get("/favorites", response_model=list[Kindergarten])
async def list_favorites(uid: str = Depends(get_current_user_id)) -> list[Kindergarten]:
    return [Kindergarten(**kg) for kg in store.list_favorites(uid)]


@router.post("/favorites/{kid}")
async def add_favorite(kid: str, uid: str = Depends(get_current_user_id)) -> dict:
    if not store.add_favorite(uid, kid):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見つかりません")
    return {"ok": True, "favorite": True}


@router.delete("/favorites/{kid}")
async def remove_favorite(kid: str, uid: str = Depends(get_current_user_id)) -> dict:
    store.remove_favorite(uid, kid)
    return {"ok": True, "favorite": False}


@router.get("/visit-requests", response_model=list[VisitRequestRecord])
async def list_visit_requests(
    uid: str = Depends(get_current_user_id),
) -> list[VisitRequestRecord]:
    return [VisitRequestRecord(**r) for r in store.list_visit_requests(uid)]


@router.post("/visit-requests/{confirmation_id}/cancel", response_model=VisitRequestRecord)
async def cancel_visit_request(
    confirmation_id: str, uid: str = Depends(get_current_user_id)
) -> VisitRequestRecord:
    rec = store.cancel_visit_request(uid, confirmation_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見学申込が見つかりません")
    return VisitRequestRecord(**rec)
