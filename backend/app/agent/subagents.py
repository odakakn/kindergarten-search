"""サブエージェント定義（学習用のマルチエージェント構成）。

司令塔（メイン）が Agent ツールで委譲する 2 体を定義する。
各サブエージェントはインプロセス MCP サーバー "kg" のツールを利用できる。
"""

from __future__ import annotations

from claude_agent_sdk import AgentDefinition

from .. import config
from .prompts import RECOMMENDER_PROMPT, VISIT_COORDINATOR_PROMPT
from .tools import SERVER_NAME


def build_agents() -> dict[str, AgentDefinition]:
    return {
        "recommender": AgentDefinition(
            description=(
                "希望条件とユーザー属性に基づき幼稚園を検索・ランク付けして提案する専門家。"
                "幼稚園を探す/比較する/おすすめを出す作業はこのエージェントに任せる。"
            ),
            prompt=RECOMMENDER_PROMPT,
            tools=[
                f"mcp__{SERVER_NAME}__search_kindergartens",
                f"mcp__{SERVER_NAME}__get_kindergarten",
                f"mcp__{SERVER_NAME}__get_user_profile",
                "WebSearch",
            ],
            mcpServers=[SERVER_NAME],
            model=config.SUB_MODEL,
            maxTurns=5,  # 過剰な再検索を防ぎ応答を速くする
        ),
        "visit-coordinator": AgentDefinition(
            description=(
                "お気に入り登録／解除と、幼稚園見学の申込手続きを代行する専門家。"
                "「お気に入りに入れて」「見学を申し込みたい」はこのエージェントに任せる。"
            ),
            prompt=VISIT_COORDINATOR_PROMPT,
            tools=[
                f"mcp__{SERVER_NAME}__get_kindergarten",
                f"mcp__{SERVER_NAME}__add_favorite",
                f"mcp__{SERVER_NAME}__remove_favorite",
                f"mcp__{SERVER_NAME}__list_favorites",
                f"mcp__{SERVER_NAME}__submit_visit_request",
                f"mcp__{SERVER_NAME}__list_visit_requests",
                f"mcp__{SERVER_NAME}__cancel_visit_request",
            ],
            mcpServers=[SERVER_NAME],
            model=config.SUB_MODEL,
            maxTurns=5,
        ),
    }
