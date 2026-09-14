"""バックエンド起動ランチャー。

Windows で Claude Agent SDK が `claude` CLI を**サブプロセス起動**するには、
実行中の asyncio ループが **ProactorEventLoop** である必要がある
（SelectorEventLoop だと `NotImplementedError` となり
「Failed to start Claude Code」で失敗する）。そこで uvicorn を Proactor ループ上で動かす。

Python 3.14 では `set_event_loop_policy` / `*EventLoopPolicy` が非推奨のため、
ポリシーではなく `asyncio.run(..., loop_factory=ProactorEventLoop)` でループを直接指定する
（`loop_factory` は Python 3.12+）。

使い方（backend ディレクトリで）:
    python run.py
※ ホットリロードは未対応（Windows のループ制約のため）。コード変更は手動で再起動して反映。
"""
from __future__ import annotations

import asyncio
import os
import sys

import uvicorn


def main() -> None:
    port = int(os.environ.get("KG_PORT", "8000"))
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=port)
    server = uvicorn.Server(config)
    if sys.platform == "win32":
        # Proactor ループを明示生成（非推奨のポリシーAPIを避ける）。
        asyncio.run(server.serve(), loop_factory=asyncio.ProactorEventLoop)
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
