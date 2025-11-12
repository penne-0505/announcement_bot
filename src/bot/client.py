from __future__ import annotations

import logging

import discord

from app.repositories import ChannelNicknameRuleStore
from bot.handlers import enforce_nickname_and_role

LOGGER = logging.getLogger(__name__)


class BotClient(discord.Client):
    """Discord Client 拡張。コマンド登録と同期を担当する。"""

    def __init__(
        self,
        *,
        intents: discord.Intents | None = None,
        rule_store: ChannelNicknameRuleStore,
    ) -> None:
        super().__init__(intents=intents or discord.Intents.all())
        self.tree = discord.app_commands.CommandTree(self)
        self.rule_store = rule_store

    async def on_ready(self) -> None:
        if self.user is None:
            LOGGER.warning("クライアントユーザー情報を取得できませんでした。")
            return

        LOGGER.info("ログイン完了: %s (ID: %s)", self.user, self.user.id)
        await self.tree.sync()
        LOGGER.info("アプリケーションコマンドの同期が完了しました。")
        LOGGER.info("準備完了。")

    async def on_message(self, message: discord.Message) -> None:
        """監視対象チャンネルでの投稿を処理する。"""

        if message.guild is None or message.author.bot:
            return

        rule = await self.rule_store.get_rule_for_channel(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
        )
        if rule is None:
            return

        try:
            await enforce_nickname_and_role(message, rule)
        except Exception:  # pragma: no cover - 想定外の例外通知
            LOGGER.exception("ニックネーム同期処理でエラーが発生しました。")


__all__ = ["BotClient"]
