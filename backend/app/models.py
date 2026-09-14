"""API の入出力に使う Pydantic モデル。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---- 認証 ----
class LoginRequest(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: str
    username: str
    display_name: str


class LoginResponse(BaseModel):
    token: str
    user: UserPublic


# ---- ユーザー属性（プロフィール） ----
class Profile(BaseModel):
    """幼稚園レコメンドのコンテキストとなるユーザー属性。すべて任意。"""

    child_name: Optional[str] = None
    child_age: Optional[int] = Field(default=None, description="子どもの年齢（歳）")
    home_area: Optional[str] = Field(default=None, description="居住エリア（例: 世田谷区）")
    commute_method: Optional[str] = Field(default=None, description="通園手段（徒歩/自転車/バス等）")
    budget_max: Optional[int] = Field(default=None, description="月額上限（円）")
    priorities: list[str] = Field(default_factory=list, description="重視する条件のタグ")
    desired_hours: Optional[str] = Field(default=None, description="希望する保育時間帯")
    needs_bus: Optional[bool] = Field(default=None, description="送迎バスが必要か")
    siblings: Optional[str] = Field(default=None, description="きょうだい構成など")
    allergies: Optional[str] = Field(default=None, description="アレルギー等の配慮事項")
    notes: Optional[str] = Field(default=None, description="その他自由記述")


class ProfileUpdate(Profile):
    """更新用（Profile と同一。None のフィールドは無視される）。"""


# ---- 幼稚園 ----
class Kindergarten(BaseModel):
    id: str
    name: str
    area: str
    address_rough: str
    nearest_station: str
    min_age: int
    max_age: int
    standard_hours: str
    extended_care: bool
    extended_hours: str = ""
    monthly_fee: int
    features: list[str] = Field(default_factory=list)
    capacity: int
    has_bus: bool
    lunch_type: str
    education_style: str
    philosophy: str
    url: Optional[str] = None


# ---- 見学申込 ----
class VisitRequestRecord(BaseModel):
    confirmation_id: str
    user_id: str
    kindergarten_id: str
    kindergarten_name: str
    preferred_dates: list[str] = Field(default_factory=list)
    applicant_note: str = ""
    status: str
    created_at: str


# ---- 会話（チャット履歴） ----
class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: str
    message_count: int


class ConversationDetail(BaseModel):
    id: str
    title: str
    messages: list[dict[str, Any]] = Field(default_factory=list)


class SaveConversationRequest(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)
    title: Optional[str] = None


# ---- チャット ----
class ChatRequest(BaseModel):
    message: str
    conversation_id: str
