"""インメモリ・データストア（バックエンドに包含する簡易 DB）。

REST エンドポイントとエージェントの MCP ツールが同一の ``store`` インスタンスを
共有する。学習用のため永続化はしない（プロセス終了で消える）。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .security import hash_password, new_token, verify_password

SEED_PATH = Path(__file__).parent / "seed" / "kindergartens.json"


def _default_profile() -> dict[str, Any]:
    return {
        "child_name": None,
        "child_age": None,
        "home_area": None,
        "commute_method": None,
        "budget_max": None,
        "priorities": [],
        "desired_hours": None,
        "needs_bus": None,
        "siblings": None,
        "allergies": None,
        "notes": None,
    }


class Store:
    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}
        self._username_index: dict[str, str] = {}
        self.profiles: dict[str, dict[str, Any]] = {}
        self.favorites: dict[str, list[str]] = {}
        self.visit_requests: list[dict[str, Any]] = []
        self.tokens: dict[str, str] = {}
        self.kindergartens: dict[str, dict[str, Any]] = {}
        self.conversations: dict[str, dict[str, Any]] = {}
        self.user_conversations: dict[str, list[str]] = {}  # uid -> conv_id[]（新しい順）
        self._visit_seq = 0
        self._conv_seq = 0
        self._load_seed()
        self._seed_users()

    # ---- 初期化 ----
    def _load_seed(self) -> None:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        for kg in data:
            self.kindergartens[kg["id"]] = kg

    def _seed_users(self) -> None:
        self.create_user(
            "demo",
            "demo",
            "デモ ユーザー",
            profile={
                **_default_profile(),
                "child_name": "はな",
                "child_age": 4,
                "home_area": "世田谷区",
                "commute_method": "自転車",
                "budget_max": 40000,
                "priorities": ["英語教育", "預かり保育"],
                "desired_hours": "8:00-18:00",
                "needs_bus": False,
                "siblings": "第一子",
                "allergies": "卵アレルギー（軽度）",
                "notes": "共働きのため長時間の預かり保育を重視しています。",
            },
        )
        self.create_user(
            "taro",
            "taro",
            "太郎の保護者",
            profile={
                **_default_profile(),
                "child_age": 3,
                "home_area": "武蔵野市",
                "budget_max": 32000,
                "priorities": ["のびのび保育", "自然体験", "送迎バス"],
                "needs_bus": True,
            },
        )

    # ---- ユーザー / 認証 ----
    def create_user(
        self,
        username: str,
        password: str,
        display_name: str,
        profile: dict[str, Any] | None = None,
    ) -> str:
        uid = f"user-{len(self.users) + 1:03d}"
        self.users[uid] = {
            "id": uid,
            "username": username,
            "display_name": display_name,
            "password_hash": hash_password(password),
        }
        self._username_index[username] = uid
        self.profiles[uid] = profile or _default_profile()
        self.favorites[uid] = []
        return uid

    def authenticate(self, username: str, password: str) -> str | None:
        uid = self._username_index.get(username)
        if not uid:
            return None
        if not verify_password(password, self.users[uid]["password_hash"]):
            return None
        return uid

    def issue_token(self, uid: str) -> str:
        token = new_token()
        self.tokens[token] = uid
        return token

    def user_for_token(self, token: str) -> str | None:
        return self.tokens.get(token)

    def revoke_token(self, token: str) -> None:
        self.tokens.pop(token, None)

    def public_user(self, uid: str) -> dict[str, Any]:
        u = self.users[uid]
        return {"id": u["id"], "username": u["username"], "display_name": u["display_name"]}

    # ---- プロフィール ----
    def get_profile(self, uid: str) -> dict[str, Any]:
        return self.profiles.get(uid, _default_profile())

    def update_profile(self, uid: str, patch: dict[str, Any]) -> dict[str, Any]:
        prof = self.profiles.setdefault(uid, _default_profile())
        for key, value in patch.items():
            if value is not None:
                prof[key] = value
        return prof

    # ---- 幼稚園 ----
    def all_kindergartens(self) -> list[dict[str, Any]]:
        return list(self.kindergartens.values())

    def get_kindergarten(self, kid: str) -> dict[str, Any] | None:
        return self.kindergartens.get(kid)

    def search(self, filters: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        """条件に対する合致度でランク付けした幼稚園リストを返す。

        すべての条件は任意。指定が無ければ全件を弱いスコアで返す。
        """
        area = filters.get("area")
        max_fee = filters.get("max_fee")
        wanted_features = filters.get("features") or []
        child_age = filters.get("child_age")
        needs_bus = filters.get("needs_bus")
        education_style = filters.get("education_style")
        need_extended = filters.get("extended_care")
        keyword = (filters.get("keyword") or "").strip()

        scored: list[tuple[float, dict[str, Any]]] = []
        for kg in self.kindergartens.values():
            score = 0.0
            reasons: list[str] = []

            if area:
                if kg["area"] == area:
                    score += 4
                    reasons.append(f"エリア一致（{kg['area']}）")
                else:
                    score -= 2

            if isinstance(max_fee, int) and max_fee > 0:
                if kg["monthly_fee"] <= max_fee:
                    score += 2
                    reasons.append(f"予算内（月額{kg['monthly_fee']:,}円）")
                else:
                    score -= 3

            for feat in wanted_features:
                if feat in kg["features"]:
                    score += 2
                    reasons.append(f"希望条件「{feat}」に対応")

            if isinstance(child_age, int):
                if kg["min_age"] <= child_age <= kg["max_age"]:
                    score += 1
                else:
                    score -= 4

            if needs_bus is True:
                if kg["has_bus"]:
                    score += 2
                    reasons.append("送迎バスあり")
                else:
                    score -= 3

            if education_style and kg["education_style"] == education_style:
                score += 2
                reasons.append(f"教育方針「{education_style}」")

            if need_extended is True and kg["extended_care"]:
                score += 2
                reasons.append("預かり保育あり")

            if keyword:
                haystack = " ".join(
                    [kg["name"], kg["philosophy"], " ".join(kg["features"]), kg["area"]]
                )
                if keyword in haystack:
                    score += 2
                    reasons.append(f"キーワード「{keyword}」に合致")

            result = dict(kg)
            result["match_score"] = round(score, 1)
            result["match_reasons"] = reasons
            scored.append((score, result))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    # ---- お気に入り ----
    def list_favorites(self, uid: str) -> list[dict[str, Any]]:
        return [
            self.kindergartens[k] for k in self.favorites.get(uid, []) if k in self.kindergartens
        ]

    def add_favorite(self, uid: str, kid: str) -> bool:
        if kid not in self.kindergartens:
            return False
        fav = self.favorites.setdefault(uid, [])
        if kid not in fav:
            fav.append(kid)
        return True

    def remove_favorite(self, uid: str, kid: str) -> bool:
        fav = self.favorites.setdefault(uid, [])
        if kid in fav:
            fav.remove(kid)
            return True
        return False

    def is_favorite(self, uid: str, kid: str) -> bool:
        return kid in self.favorites.get(uid, [])

    # ---- 見学申込（外部送信せずローカル記録のみ） ----
    def add_visit_request(
        self,
        uid: str,
        kid: str,
        preferred_dates: list[str],
        applicant_note: str = "",
    ) -> dict[str, Any] | None:
        kg = self.kindergartens.get(kid)
        if not kg:
            return None
        self._visit_seq += 1
        record = {
            "confirmation_id": f"VR-{self._visit_seq:04d}",
            "user_id": uid,
            "kindergarten_id": kid,
            "kindergarten_name": kg["name"],
            "preferred_dates": preferred_dates,
            "applicant_note": applicant_note,
            "status": "received",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.visit_requests.append(record)
        return record

    def list_visit_requests(self, uid: str) -> list[dict[str, Any]]:
        return [r for r in self.visit_requests if r["user_id"] == uid]

    def find_visit_request(self, uid: str, confirmation_id: str) -> dict[str, Any] | None:
        for r in self.visit_requests:
            if r["confirmation_id"] == confirmation_id and r["user_id"] == uid:
                return r
        return None

    def cancel_visit_request(self, uid: str, confirmation_id: str) -> dict[str, Any] | None:
        """所有する見学申込を取消（status=cancelled）にする。未存在なら None。

        既に cancelled の場合はそのまま返す（冪等）。
        """
        rec = self.find_visit_request(uid, confirmation_id)
        if rec and rec["status"] == "received":
            rec["status"] = "cancelled"
        return rec

    # ---- 会話（チャット履歴） ----
    def create_conversation(self, uid: str, title: str = "新しいチャット") -> dict[str, Any]:
        self._conv_seq += 1
        cid = f"conv-{self._conv_seq:04d}"
        now = datetime.now(UTC).isoformat()
        conv = {
            "id": cid,
            "user_id": uid,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "session_id": None,
            "messages": [],
        }
        self.conversations[cid] = conv
        self.user_conversations.setdefault(uid, []).insert(0, cid)
        return conv

    def _owned_conversation(self, uid: str, cid: str) -> dict[str, Any] | None:
        conv = self.conversations.get(cid)
        return conv if conv and conv["user_id"] == uid else None

    def list_conversations(self, uid: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for cid in self.user_conversations.get(uid, []):
            conv = self.conversations.get(cid)
            if conv:
                out.append(
                    {
                        "id": conv["id"],
                        "title": conv["title"],
                        "updated_at": conv["updated_at"],
                        "message_count": len(conv["messages"]),
                    }
                )
        return out

    def get_conversation(self, uid: str, cid: str) -> dict[str, Any] | None:
        return self._owned_conversation(uid, cid)

    def save_conversation(
        self,
        uid: str,
        cid: str,
        messages: list[dict[str, Any]],
        title: str | None = None,
    ) -> dict[str, Any] | None:
        conv = self._owned_conversation(uid, cid)
        if not conv:
            return None
        conv["messages"] = messages
        if title:
            conv["title"] = title
        conv["updated_at"] = datetime.now(UTC).isoformat()
        # 直近更新を先頭へ
        lst = self.user_conversations.setdefault(uid, [])
        if cid in lst:
            lst.remove(cid)
        lst.insert(0, cid)
        return conv

    def delete_conversation(self, uid: str, cid: str) -> bool:
        conv = self._owned_conversation(uid, cid)
        if not conv:
            return False
        self.conversations.pop(cid, None)
        lst = self.user_conversations.get(uid, [])
        if cid in lst:
            lst.remove(cid)
        return True

    # 会話単位のエージェントセッション継続
    def get_conv_session(self, cid: str) -> str | None:
        conv = self.conversations.get(cid)
        return conv["session_id"] if conv else None

    def set_conv_session(self, cid: str, session_id: str) -> None:
        conv = self.conversations.get(cid)
        if conv:
            conv["session_id"] = session_id


# アプリ全体で共有する単一インスタンス
store = Store()
