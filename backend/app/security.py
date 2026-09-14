"""パスワードハッシュとトークン生成（標準ライブラリのみ・学習用の簡易実装）。

本番強度の認証ではない点に注意。bcrypt 等のネイティブ依存を避けるため
hashlib.pbkdf2_hmac を用いている（Python 3.14 でも追加ビルド不要）。
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """パスワードを ``algo$iters$salt$hash`` 形式の文字列に変換する。"""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """平文パスワードが保存済みハッシュと一致するか検証する。"""
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def new_token() -> str:
    """URL セーフな不透明トークンを発行する。"""
    return secrets.token_urlsafe(32)
