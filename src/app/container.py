from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import AppConfig
from app.database import Database
from app.repositories import (
    ChannelNicknameRuleRepository,
    TemporaryVoiceCategoryRepository,
    TemporaryVoiceChannelRepository,
)
from app.services import TemporaryVoiceChannelService
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

    LOGGER.info("Discord アプリケーションの初期化を開始します。")
    database = Database(config.database.url, config.database.key)
    await database.connect()
    LOGGER.info("Supabase への接続が完了しました。")
    rule_repository = ChannelNicknameRuleRepository(database)
    temporary_category_repo = TemporaryVoiceCategoryRepository(database)
    temporary_channel_repo = TemporaryVoiceChannelRepository(database)
    temporary_voice_service = TemporaryVoiceChannelService(
        category_repo=temporary_category_repo,
        channel_repo=temporary_channel_repo,
    )
    client = BotClient(
        rule_store=rule_repository,
        temporary_voice_service=temporary_voice_service,
    )
    await register_commands(
        client,
        rule_store=rule_repository,
        temporary_voice_service=temporary_voice_service,
    )
    LOGGER.info("Discord クライアントの初期化が完了し、コマンドを登録しました。")
    return DiscordApplication(
        client=client, token=config.discord.token, database=database
    )


__all__ = ["DiscordApplication", "build_discord_app"]
