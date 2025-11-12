from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import AppConfig
from app.database import Database
from app.repositories import ChannelNicknameRuleRepository
from bot import BotClient, register_commands

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class DiscordApplication:
    """Discord クライアントとトークンをまとめた実行ラッパー。"""

    client: BotClient
    token: str
    database: Database

    async def run(self) -> None:
        """クライアントを起動する。"""

        try:
            async with self.client:
                await self.client.start(self.token)
        finally:
            await self.database.close()


async def build_discord_app(config: AppConfig) -> DiscordApplication:
    """Discord クライアントを初期化し、コマンド登録までを完了させる。"""

    database = Database(config.database.url)
    await database.connect()
    rule_repository = ChannelNicknameRuleRepository(database)

    client = BotClient(rule_store=rule_repository)
    await register_commands(client, rule_store=rule_repository)
    LOGGER.info("Discord クライアントの初期化が完了し、コマンドを登録しました。")
    return DiscordApplication(client=client, token=config.discord.token, database=database)


__all__ = ["DiscordApplication", "build_discord_app"]
