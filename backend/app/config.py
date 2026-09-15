"""環境変数から読み込むアプリ設定。"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    # backend/.env を読み込む（存在しなければ何もしない）
    load_dotenv()
except Exception:  # python-dotenv 未導入でも動作させる
    pass


# エージェント（Claude Agent SDK）が利用する API キー。未設定だと /api/chat は 503 を返す。
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")

# SDK が Claude Code 実行バイナリを見つけられない場合に明示指定する（任意）。
CLAUDE_CODE_PATH: str | None = os.environ.get("CLAUDE_CODE_PATH")

# 使用モデル（エイリアス推奨: sonnet / opus / haiku）。
MAIN_MODEL: str = os.environ.get("KG_MAIN_MODEL", "sonnet")
SUB_MODEL: str = os.environ.get("KG_SUB_MODEL", "sonnet")

# CORS 許可オリジン（カンマ区切り）。
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("KG_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(
        ","
    )
    if o.strip()
]

# エージェントの 1 リクエストあたり最大ターン数（暴走防止）。
MAX_TURNS: int = int(os.environ.get("KG_MAX_TURNS", "20"))
