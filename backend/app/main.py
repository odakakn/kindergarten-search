"""FastAPI アプリ本体。CORS 設定とルーター登録。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routers import auth, chat, conversations, favorites, users

app = FastAPI(title="幼稚園さがし API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(favorites.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.get("/api/health")
async def health() -> dict:
    """稼働確認。エージェント実行の準備状況の目安も返す。"""
    return {
        "status": "ok",
        "anthropic_api_key_set": bool(config.ANTHROPIC_API_KEY),
        "cli_path_override": bool(config.CLAUDE_CODE_PATH),
        "main_model": config.MAIN_MODEL,
        "sub_model": config.SUB_MODEL,
    }
